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

# Library-facing overrides after visual review (score alone can prefer too-dark beats).
HERO_OVERRIDES = {
    "episode_cjp_origin": 5,  # Abhijeet gathering students
    "episode_et_tu_brutus": 11,  # “Et tu” climax
    "episode_hitler_warning": 1,  # night study / warning frame (not Kristallnacht)
}

REASONS = {
    "episode_cjp_origin": "Clear hero + action beat; highest score among positive campaign panels.",
    "episode_et_tu_brutus": "Instantly recognizable climax with strong contrast and faces.",
    "episode_hitler_warning": "Framed as cautionary study; suitable library card vs violent spectacle panels.",
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


def main() -> None:
    stories = json.loads(STORIES.read_text(encoding="utf-8")).get("stories") or []
    meta: dict = {}
    for s in stories:
        sid = s["id"]
        folder = COMICS / sid
        if not folder.is_dir():
            continue
        ranked = []
        for p in s.get("panels") or []:
            idx = int(p.get("index") or 0)
            fp = folder / f"panel_{idx:02d}.png"
            if fp.is_file():
                ranked.append((score_panel(fp), idx, fp))
        ranked.sort(reverse=True)
        idx = HERO_OVERRIDES.get(sid) or (ranked[0][1] if ranked else 1)
        src = folder / f"panel_{idx:02d}.png"
        if not src.is_file() and ranked:
            idx, src = ranked[0][1], ranked[0][2]
        dest = folder / "thumbnail.jpg"
        if src.is_file():
            make_thumb(src, dest)
            meta[sid] = {
                "source_panel": idx,
                "thumbnail": f"/comics/{sid}/thumbnail.jpg",
                "score_ranked": [r[1] for r in ranked[:5]],
                "reason": REASONS.get(sid, "Highest heuristic score among available panels."),
                "bytes": dest.stat().st_size,
            }
    OUT_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    # inject into stories.json
    for s in stories:
        sid = s["id"]
        if sid in meta:
            s["thumbnail"] = meta[sid]["thumbnail"]
            s["thumbnail_panel"] = meta[sid]["source_panel"]
    STORIES.write_text(json.dumps({"stories": stories, "count": len(stories)}, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "thumbnails": meta}, indent=2))


if __name__ == "__main__":
    main()
