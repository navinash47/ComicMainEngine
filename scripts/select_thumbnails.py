#!/usr/bin/env python3
"""Pick + generate library thumbnails for each story (heuristic + manual hero overrides)."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[1]
COMICS = ROOT / "feedback-beta" / "public" / "comics"
STORIES = ROOT / "feedback-beta" / "public" / "stories.json"
OUT_META = ROOT / "feedback-beta" / "public" / "thumbnail_picks.json"
PHASE4 = ROOT / "outputs" / "phase4"
PHASE5 = ROOT / "outputs" / "phase5"

# Library-facing overrides after visual review (score alone can prefer too-dark beats).
HERO_OVERRIDES = {
    "episode_cjp_origin": 5,  # Abhijeet gathering students
    "episode_et_tu_brutus": 11,  # “Et tu” climax
    "episode_hitler_warning": 1,  # night study / warning frame (not Kristallnacht)
    # Bubble-free Phase 5 two-shot: Rohan + Elena lobby first sight
    "episode_how_i_met_your_mother_ep1": 7,
}

# For these stories, only consider panels that include all listed character ids
PAIR_FILTER: dict[str, set[str]] = {
    "episode_how_i_met_your_mother_ep1": {"rohan", "elena"},
}

# Prefer raw Phase 5 art (no speech-bubble compose) when present
PREFER_PHASE5_NO_BUBBLES = {
    "episode_how_i_met_your_mother_ep1",
}

REASONS = {
    "episode_cjp_origin": "Clear hero + action beat; highest score among positive campaign panels.",
    "episode_et_tu_brutus": "Instantly recognizable climax with strong contrast and faces.",
    "episode_hitler_warning": "Framed as cautionary study; suitable library card vs violent spectacle panels.",
    "episode_how_i_met_your_mother_ep1": (
        "Bubble-free Phase 5 two-shot of Rohan + Elena (lobby first sight); "
        "best clean library card among main-cast panels."
    ),
}

W, H = 960, 640


def score_panel(path: Path) -> float:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    thumb = im.resize((280, max(1, int(280 * h / w))), Image.Resampling.LANCZOS)
    rs, gs, bs = ImageStat.Stat(thumb).stddev
    sat = (rs + gs + bs) / 3
    gray = thumb.convert("L")
    contrast = ImageStat.Stat(gray).stddev[0]
    mean = ImageStat.Stat(gray).mean[0]
    mid_bias = 1.0 - abs(mean - 115) / 115
    edge = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0]
    cw, ch = gray.size
    crop = gray.crop((cw // 4, ch // 6, 3 * cw // 4, 5 * ch // 6))
    center = ImageStat.Stat(crop).stddev[0]
    return 0.35 * contrast + 0.25 * sat + 0.2 * edge + 0.15 * center + 25 * max(0.0, mid_bias)


def make_thumb(src: Path, dest: Path) -> None:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    target_ratio = W / H
    r = w / h
    if r > target_ratio:
        nw = int(h * target_ratio)
        left = (w - nw) // 2
        im = im.crop((left, 0, left + nw, h))
    else:
        nh = int(w / target_ratio)
        top = min(max(0, int(h * 0.12)), max(0, h - nh))
        im = im.crop((0, top, w, top + nh))
    im.resize((W, H), Image.Resampling.LANCZOS).save(dest, "JPEG", quality=86, optimize=True)


def panel_path(sid: str, idx: int, folder: Path) -> Path | None:
    """Prefer Phase 5 raw art (no compose bubbles) when configured."""
    name = f"panel_{idx:02d}.png"
    if sid in PREFER_PHASE5_NO_BUBBLES:
        p5 = PHASE5 / sid / name
        if p5.is_file():
            return p5
    comic = folder / name
    if comic.is_file():
        return comic
    p5 = PHASE5 / sid / name
    if p5.is_file():
        return p5
    return None


def allowed_indices(sid: str, story_panels: list[dict]) -> set[int] | None:
    need = PAIR_FILTER.get(sid)
    if not need:
        return None
    # Prefer episode JSON cast membership if available
    ep_path = PHASE4 / f"{sid}.json"
    if ep_path.is_file():
        try:
            ep = json.loads(ep_path.read_text(encoding="utf-8"))
            out = set()
            for p in ep.get("panels") or []:
                chars = set(p.get("characters") or [])
                if need.issubset(chars):
                    out.add(int(p.get("index") or 0))
            return {i for i in out if i}
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    # Fallback: allow all if no episode schema nearby
    return {int(p.get("index") or 0) for p in story_panels if p.get("index")}


def main() -> None:
    catalog = json.loads(STORIES.read_text(encoding="utf-8"))
    stories = catalog.get("stories") or []
    meta: dict = {}
    for s in stories:
        sid = s["id"]
        folder = COMICS / sid
        if not folder.is_dir() and sid not in PREFER_PHASE5_NO_BUBBLES:
            continue
        folder.mkdir(parents=True, exist_ok=True)

        allow = allowed_indices(sid, s.get("panels") or [])
        ranked = []
        for p in s.get("panels") or []:
            idx = int(p.get("index") or 0)
            if not idx:
                continue
            if allow is not None and idx not in allow:
                continue
            fp = panel_path(sid, idx, folder)
            if fp and fp.is_file():
                ranked.append((score_panel(fp), idx, fp))
        ranked.sort(reverse=True)

        idx = HERO_OVERRIDES.get(sid)
        src = panel_path(sid, idx, folder) if idx else None
        if not src or not src.is_file():
            if ranked:
                idx, src = ranked[0][1], ranked[0][2]
            else:
                continue

        dest = folder / "thumbnail.jpg"
        make_thumb(src, dest)
        # Also keep a bubble-free panel copy in comics for thumb source clarity
        clean_copy = folder / f"thumb_source_panel_{idx:02d}.png"
        if src.resolve() != clean_copy.resolve():
            try:
                Image.open(src).save(clean_copy)
            except OSError:
                pass
        meta[sid] = {
            "source_panel": idx,
            "source_path": str(src.relative_to(ROOT)),
            "bubble_free": sid in PREFER_PHASE5_NO_BUBBLES,
            "pair_filter": sorted(PAIR_FILTER.get(sid) or []),
            "thumbnail": f"/comics/{sid}/thumbnail.jpg",
            "score_ranked": [r[1] for r in ranked[:5]],
            "reason": REASONS.get(sid, "Highest heuristic score among available panels."),
            "bytes": dest.stat().st_size,
        }

    OUT_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    # inject into stories.json — preserve genres/tags/sort fields
    for s in stories:
        sid = s["id"]
        if sid in meta:
            s["thumbnail"] = meta[sid]["thumbnail"]
            s["thumbnail_panel"] = meta[sid]["source_panel"]
    STORIES.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "thumbnails": meta}, indent=2))


if __name__ == "__main__":
    main()
