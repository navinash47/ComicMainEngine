"""Invoke Blender as a subprocess. Not MCP."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from comicengine.config import ROOT

SCRIPT = Path(__file__).resolve().parent / "himym_p1.py"
TURNTABLE = Path(__file__).resolve().parent / "dad_turntable.py"
BUILD_SCENE = Path(__file__).resolve().parent / "build_scene.py"

CANDIDATES = (
    os.environ.get("BLENDER_BIN"),
    "/opt/homebrew/bin/blender",
    "/Applications/Blender.app/Contents/MacOS/Blender",
    shutil.which("blender"),
)

DEFAULT_CAMERAS = ("a", "b", "c")


def blender_bin() -> Path:
    for raw in CANDIDATES:
        if not raw:
            continue
        p = Path(raw)
        if p.is_file():
            return p
    raise FileNotFoundError(
        "Blender not found. Install with `brew install --cask blender` "
        "or set BLENDER_BIN to the binary."
    )


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return proc


def _raise_if_failed(proc: subprocess.CompletedProcess[str], cmd: list[str], expected: Path) -> None:
    if proc.returncode != 0 or not expected.is_file():
        raise RuntimeError(
            "Blender render failed.\n"
            f"cmd: {cmd}\n"
            f"exit: {proc.returncode}\n"
            f"stdout:\n{proc.stdout[-4000:]}\n"
            f"stderr:\n{proc.stderr[-4000:]}"
        )


def render_himym_p1(out_png: Path) -> Path:
    """B1 compat: Cycles beauty for camera A."""
    out_png = Path(out_png)
    out_dir = out_png.parent
    render_himym_p1_aovs(out_dir, cameras=("a",))
    beauty = out_dir / "cam_a" / "beauty_01.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(beauty.read_bytes())
    return out_png


def render_himym_p1_aovs(
    out_dir: Path,
    cameras: tuple[str, ...] = DEFAULT_CAMERAS,
    samples: int | None = None,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(blender_bin()),
        "--background",
        "--factory-startup",
        "--python",
        str(SCRIPT),
        "--",
        "--out-dir",
        str(out_dir),
        "--cameras",
        ",".join(cameras),
    ]
    if samples is not None:
        cmd.extend(["--samples", str(samples)])
    proc = _run(cmd)
    paths = {cam: out_dir / f"cam_{cam}" for cam in cameras}
    expected = paths[cameras[0]] / "beauty_01.png"
    _raise_if_failed(proc, cmd, expected)
    missing = [
        str(folder / name)
        for folder in paths.values()
        for name in ("beauty_01.png", "depth_01.png", "lineart_01.png", "normal_01.png", "index_01.png")
        if not (folder / name).is_file()
    ]
    if missing:
        raise RuntimeError("Blender AOVs missing:\n" + "\n".join(missing) + f"\nstdout:\n{proc.stdout[-2000:]}")
    return paths


def render_turntable(
    out_dir: Path,
    *,
    character: str = "dad",
    quick: bool = False,
    samples: int | None = None,
    mesh: Path | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(blender_bin()),
        "--background",
        "--factory-startup",
        "--python",
        str(TURNTABLE),
        "--",
        "--out-dir",
        str(out_dir),
        "--character",
        character,
    ]
    if mesh is not None:
        cmd.extend(["--mesh", str(Path(mesh).resolve())])
    if quick:
        cmd.append("--quick")
    if samples is not None:
        cmd.extend(["--samples", str(samples)])
    proc = _run(cmd)
    expected = None
    for child in sorted(out_dir.iterdir()) if out_dir.is_dir() else []:
        beauty = child / "beauty_01.png"
        if beauty.is_file():
            expected = beauty
            break
    if expected is None:
        expected = out_dir / "missing.png"
    _raise_if_failed(proc, cmd, expected)
    return out_dir


def render_from_spec(
    location_json: Path,
    out_dir: Path,
    *,
    cameras: tuple[str, ...],
    characters: tuple[str, ...] = (),
    samples: int | None = None,
    mesh_dir: Path | None = None,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(blender_bin()),
        "--background",
        "--factory-startup",
        "--python",
        str(BUILD_SCENE),
        "--",
        "--location",
        str(Path(location_json).resolve()),
        "--out-dir",
        str(out_dir),
        "--cameras",
        ",".join(cameras),
        "--characters",
        ",".join(characters),
    ]
    if mesh_dir is not None:
        cmd.extend(["--mesh-dir", str(Path(mesh_dir).resolve())])
    if samples is not None:
        cmd.extend(["--samples", str(samples)])
    proc = _run(cmd)
    paths = {cam: out_dir / f"cam_{cam}" for cam in cameras}
    expected = paths[cameras[0]] / "beauty_01.png"
    _raise_if_failed(proc, cmd, expected)
    missing = [
        str(folder / name)
        for folder in paths.values()
        for name in ("beauty_01.png", "depth_01.png", "lineart_01.png", "index_01.png")
        if not (folder / name).is_file()
    ]
    if missing:
        raise RuntimeError("Blender AOVs missing:\n" + "\n".join(missing) + f"\nstdout:\n{proc.stdout[-2000:]}")
    return paths
