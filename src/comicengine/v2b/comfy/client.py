"""ComfyUI HTTP /prompt client. Local only — never OmniRoute."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE = "http://127.0.0.1:8188"


class ComfyError(RuntimeError):
    pass


def _req(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 60) -> bytes:
    h = {"User-Agent": "comicengine-v2b"}
    if headers:
        h.update(headers)
    request = Request(url, data=data, headers=h)
    with urlopen(request, timeout=timeout) as resp:
        return resp.read()


def wait_until_up(base: str = DEFAULT_BASE, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        try:
            _req(f"{base.rstrip('/')}/system_stats", timeout=5)
            return
        except Exception as exc:
            last = str(exc)
            time.sleep(1.0)
    raise ComfyError(f"ComfyUI not reachable at {base}: {last}")


def upload_image(path: Path, base: str = DEFAULT_BASE) -> str:
    path = Path(path)
    boundary = uuid.uuid4().hex
    filename = path.name
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    raw = _req(
        f"{base.rstrip('/')}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=120,
    )
    payload = json.loads(raw.decode())
    name = payload.get("name")
    if not name:
        raise ComfyError(f"upload did not return a name: {payload}")
    return str(name)


def queue_prompt(workflow: dict[str, Any], base: str = DEFAULT_BASE, client_id: str | None = None) -> str:
    payload = {"prompt": workflow, "client_id": client_id or uuid.uuid4().hex}
    raw = _req(
        f"{base.rstrip('/')}/prompt",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    data = json.loads(raw.decode())
    if data.get("error"):
        raise ComfyError(f"ComfyUI rejected prompt: {data}")
    pid = data.get("prompt_id")
    if not pid:
        raise ComfyError(f"no prompt_id: {data}")
    return str(pid)


def wait_history(prompt_id: str, base: str = DEFAULT_BASE, timeout_s: float = 600.0) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    url = f"{base.rstrip('/')}/history/{prompt_id}"
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = json.loads(_req(url, timeout=30).decode() or "{}")
        entry = last.get(prompt_id) or last
        if isinstance(entry, dict) and entry.get("outputs"):
            status = (entry.get("status") or {}).get("status_str")
            if status in {None, "success"}:
                return entry
            if status == "error":
                raise ComfyError(f"ComfyUI execution error: {entry.get('status')}")
        time.sleep(1.0)
    raise ComfyError(f"timed out waiting for {prompt_id}: {last}")


def fetch_first_image(history: dict[str, Any], dest: Path, base: str = DEFAULT_BASE) -> Path:
    outputs = history.get("outputs") or {}
    for node in outputs.values():
        images = node.get("images") or []
        if not images:
            continue
        img = images[0]
        qs = urlencode(
            {
                "filename": img["filename"],
                "subfolder": img.get("subfolder") or "",
                "type": img.get("type") or "output",
            }
        )
        blob = _req(f"{base.rstrip('/')}/view?{qs}", timeout=120)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        return dest
    raise ComfyError(f"no images in history outputs: {list(outputs)}")
