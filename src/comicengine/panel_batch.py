"""Phase 5 — episode JSON → panel images with gemini_ref + retries."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from comicengine.analytics import check_image_quality
from comicengine.clients import TrackedClients
from comicengine.config import OUTPUTS, ROOT
from comicengine.episode_schema import Character, Episode
from comicengine.style import build_prompt

PHASE3_REFS = OUTPUTS / "phase3" / "refs"
PHASE5 = OUTPUTS / "phase5"
REFS_DIR = PHASE5 / "refs"

# Prefer refs for individuals; crowds often text-only fallback
CROWD_IDS = {
    "students",
    "roman_people",
    "senate",
    "german_neighbor",
    "weimar_citizen",
}


def _media_href(path: Path) -> str:
    rel = path.resolve().relative_to(OUTPUTS.resolve()).as_posix()
    return f"/media/{rel}"


def load_episode(path: Path) -> Episode:
    return Episode.model_validate(json.loads(path.read_text()))


def char_lookup(episode: Episode) -> dict[str, Character]:
    return {c.id: c for c in episode.characters}


def ensure_ref(
    clients: TrackedClients,
    char: Character,
    *,
    skip_existing: bool = True,
) -> Path | None:
    """Ensure a reference sheet PNG exists under phase5/refs (copy phase3 if present)."""
    REFS_DIR.mkdir(parents=True, exist_ok=True)
    dest = REFS_DIR / f"{char.id}_ref.png"
    if skip_existing and dest.is_file() and dest.stat().st_size > 1000:
        return dest

    src = PHASE3_REFS / f"{char.id}_ref.png"
    if src.is_file() and src.stat().st_size > 1000:
        shutil.copy2(src, dest)
        return dest

    look = f"{char.display_name} ({char.look})" if char.look else char.display_name
    anti_hero = ""
    if char.id in {"adolf_hitler", "joseph_goebbels", "adolf_eichmann", "heinrich_himmler"}:
        anti_hero = (
            " documentary historical reference only, NEVER heroic or glamorous lighting, "
            "no propaganda poster energy, subdued serious mood"
        )
    scene = (
        f"character reference sheet for {char.display_name}: clean front three-quarter portrait, "
        f"neutral soft studio backdrop, clear face and outfit for identity lock, "
        f"single character only, comic production bible plate{anti_hero}"
    )
    prompt = build_prompt(scene, characters=look)
    clients.fal_flux_image(
        prompt,
        out_path=dest,
        purpose="char_ref",
        image_size="square_hd",
    )
    qa = check_image_quality(dest)
    if qa.get("verdict") == "fail":
        return None
    return dest


def _looks_line(episode: Episode, char_ids: list[str]) -> str:
    lookup = char_lookup(episode)
    parts: list[str] = []
    for cid in char_ids:
        c = lookup.get(cid)
        if not c:
            parts.append(cid)
            continue
        parts.append(f"{c.display_name} ({c.look})" if c.look else c.display_name)
    return "; ".join(parts)


def _pick_refs(char_ids: list[str], refs: dict[str, Path], *, limit: int = 3) -> list[Path]:
    ordered = [c for c in char_ids if c not in CROWD_IDS] + [c for c in char_ids if c in CROWD_IDS]
    out: list[Path] = []
    for cid in ordered:
        p = refs.get(cid)
        if p and p.is_file():
            out.append(p)
        if len(out) >= limit:
            break
    return out


def panel_prompt(episode: Episode, panel_index: int) -> str:
    panel = next(p for p in episode.panels if p.index == panel_index)
    scene = panel.art_prompt or panel.scene_description
    emotion = panel.emotion or ""
    if emotion:
        scene = f"{scene}. Mood: {emotion}"
    return build_prompt(scene, characters=_looks_line(episode, panel.characters) or None)


def render_panel(
    clients: TrackedClients,
    episode: Episode,
    panel_index: int,
    *,
    out_path: Path,
    refs: dict[str, Path],
    skip_existing: bool = True,
    max_retries: int = 2,
    prompt_override: str | None = None,
) -> dict[str, Any]:
    panel = next(p for p in episode.panels if p.index == panel_index)
    row: dict[str, Any] = {
        "index": panel_index,
        "characters": list(panel.characters),
        "path": str(out_path),
        "status": "pending",
    }
    if skip_existing and out_path.is_file() and out_path.stat().st_size > 1000:
        qa = check_image_quality(out_path)
        row.update(
            {
                "status": "skipped_existing",
                "method": panel.image_method or "existing",
                "qa": qa,
                "href": _media_href(out_path),
            }
        )
        return row

    if prompt_override and prompt_override.strip():
        # User-edited art direction from Phase 8.5 editor
        scene = prompt_override.strip()
        emotion = panel.emotion or ""
        if emotion and "Mood:" not in scene:
            scene = f"{scene}. Mood: {emotion}"
        prompt = build_prompt(scene, characters=_looks_line(episode, panel.characters) or None)
    else:
        prompt = panel_prompt(episode, panel_index)
    ref_paths = _pick_refs(panel.characters, refs, limit=3)
    attempts: list[dict[str, Any]] = []

    methods: list[tuple[str, Any]] = []
    if ref_paths:
        methods.append(("gemini_ref", lambda prompt=prompt: clients.gemini_image_with_refs(
            prompt,
            out_path=out_path,
            reference_paths=ref_paths,
            purpose="panel_batch",
        )))
        primary = next((c for c in panel.characters if c not in CROWD_IDS and c in refs), None)
        if primary:
            methods.append(("flux_kontext", lambda p=refs[primary], prompt=prompt: clients.fal_kontext_edit(
                prompt,
                reference_path=p,
                out_path=out_path,
                purpose="panel_batch_retry",
            )))
    methods.append(("text_only_fal", lambda prompt=prompt: clients.fal_flux_image(
        prompt,
        out_path=out_path,
        purpose="panel_batch",
        image_size="landscape_4_3",
    )))

    # Limit method attempts
    tried = 0
    for method, fn in methods:
        if tried >= max_retries + 1:
            break
        tried += 1
        try:
            fn()
            qa = check_image_quality(out_path)
            attempts.append({"method": method, "qa": qa.get("verdict"), "ok": True})
            if qa.get("verdict") != "fail":
                row.update(
                    {
                        "status": "ok",
                        "method": method,
                        "qa": qa,
                        "attempts": attempts,
                        "href": _media_href(out_path),
                        "refs_used": [str(p) for p in ref_paths] if method == "gemini_ref" else [],
                    }
                )
                return row
        except Exception as e:  # noqa: BLE001
            attempts.append({"method": method, "ok": False, "error": str(e)[:400]})

    row.update({"status": "error", "attempts": attempts, "error": "all methods failed"})
    return row


def render_episode(
    story_path: Path,
    *,
    story_id: str | None = None,
    phase: str = "phase5",
    skip_existing: bool = True,
    panel_limit: int | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    episode = load_episode(story_path)
    sid = story_id or story_path.stem
    out_dir = PHASE5 / sid
    out_dir.mkdir(parents=True, exist_ok=True)
    clients = TrackedClients(phase=phase)

    # Refs for every cast id appearing in panels (and episode cast)
    needed = {c.id for c in episode.characters}
    for p in episode.panels:
        needed.update(p.characters)
    refs: dict[str, Path] = {}
    ref_rows: list[dict[str, Any]] = []
    lookup = char_lookup(episode)
    for cid in sorted(needed):
        char = lookup.get(cid) or Character(id=cid, display_name=cid, role="unknown")
        try:
            path = ensure_ref(clients, char, skip_existing=skip_existing)
            if path:
                refs[cid] = path
                ref_rows.append({"char_id": cid, "path": str(path), "status": "ok"})
            else:
                ref_rows.append({"char_id": cid, "status": "qa_fail"})
        except Exception as e:  # noqa: BLE001
            ref_rows.append({"char_id": cid, "status": "error", "error": str(e)[:400]})

    panels_out: list[dict[str, Any]] = []
    panels = sorted(episode.panels, key=lambda p: p.index)
    if panel_limit is not None:
        panels = panels[:panel_limit]

    for panel in panels:
        out_path = out_dir / f"panel_{panel.index:02d}.png"
        print(f"[{sid}] panel {panel.index}/{panels[-1].index} …")
        row = render_panel(
            clients,
            episode,
            panel.index,
            out_path=out_path,
            refs=refs,
            skip_existing=skip_existing,
            max_retries=max_retries,
        )
        panels_out.append(row)
        print(f"  → {row.get('status')} method={row.get('method')} qa={(row.get('qa') or {}).get('verdict')}")

        # Persist into episode panel fields
        if row.get("status") in {"ok", "skipped_existing"} and out_path.is_file():
            panel.image_path = str(out_path.relative_to(ROOT))
            panel.image_method = str(row.get("method") or "")
            panel.image_qa = str((row.get("qa") or {}).get("verdict") or "")

    # Rewrite episode JSON with image paths (same source path)
    story_path.write_text(episode.model_dump_json(indent=2))

    manifest = {
        "story_id": sid,
        "source": str(story_path.relative_to(ROOT)),
        "title": episode.title,
        "panel_count": len(panels_out),
        "ok": sum(1 for r in panels_out if r.get("status") in {"ok", "skipped_existing"}),
        "errors": sum(1 for r in panels_out if r.get("status") == "error"),
        "refs": ref_rows,
        "panels": panels_out,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
