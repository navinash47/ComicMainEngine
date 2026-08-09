#!/usr/bin/env python3
"""Download free Wikimedia Commons refs for the CJP bedtime test comic."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comicengine.config import OUTPUTS

UA = "ComicMainEngine/0.1 (educational local comic pipeline; contact: local-dev)"

# Curated free files — places/atmosphere for the story (avoid disputed likeness downloads).
CURATED = [
    {
        "id": "jantar_mantar",
        "role": "protest_place",
        "title": "Jantar Mantar, New Delhi",
        "file": "Jantar Mantar New Delhi.jpg",
        "note": "CJP gatherings were reported at Jantar Mantar — location reference.",
    },
    {
        "id": "jantar_mantar_detail",
        "role": "protest_place",
        "title": "Jantar Mantar detail",
        "file": "Jantar Mantar Bird.jpg",
        "note": "Architectural detail for scene mood.",
    },
    {
        "id": "india_gate",
        "role": "delhi_atmosphere",
        "title": "India Gate, New Delhi",
        "file": "India Gate.jpg",
        "note": "Delhi civic backdrop for the bedtime retelling.",
    },
    {
        "id": "delhi_tricolour",
        "role": "public_mood",
        "title": "Delhi tricolour lamppost",
        "file": "Delhi protests-Lamppost, with Indian tricolour.jpg",
        "note": "Public protest atmosphere (Commons CC). Educational reference only.",
    },
    {
        "id": "students_library",
        "role": "students_study",
        "title": "Jamia Millia Islamia reading hall",
        "file": "Ibn-e-Sina Library Reading Hall, Jamia Millia Islamia, New Delhi.jpg",
        "note": "Students preparing / studying — soft bedtime framing (Commons CC).",
    },
]


def commons_info(filename: str) -> dict:
    title = filename if filename.startswith("File:") else f"File:{filename}"
    api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime",
            "iiurlwidth": 1024,
        }
    )
    req = urllib.request.Request(api, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.load(resp)
    pages = (data.get("query") or {}).get("pages") or {}
    page = next(iter(pages.values()))
    if "missing" in page:
        raise FileNotFoundError(title)
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata") or {}
    artist = re.sub("<[^<]+?>", "", (meta.get("Artist") or {}).get("value", ""))[:160]
    license_ = (meta.get("LicenseShortName") or {}).get("value", "")
    return {
        "url": info.get("thumburl") or info.get("url"),
        "original": info.get("url"),
        "license": license_,
        "artist": artist.strip(),
        "commons_url": info.get("descriptionurl"),
        "mime": info.get("mime"),
    }


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as resp:
        dest.write_bytes(resp.read())


def main() -> None:
    out_dir = OUTPUTS / "phase0.5" / "refs"
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for item in CURATED:
        dest_guess = list(out_dir.glob(f"{item['id']}.*"))
        if dest_guess:
            # reuse already-downloaded
            existing = dest_guess[0]
            print(f"have {existing.name}")
            # still need metadata — soft fail to re-fetch info only
        try:
            info = commons_info(item["file"])
            time.sleep(1.2)
        except Exception as e:  # noqa: BLE001
            print(f"skip {item['id']}: {e}")
            continue
        ext = ".jpg"
        mime = info.get("mime") or ""
        if "png" in mime:
            ext = ".png"
        elif "webp" in mime:
            ext = ".webp"
        dest = out_dir / f"{item['id']}{ext}"
        if not dest.exists():
            print(f"fetch {item['id']} …")
            try:
                download(info["url"], dest)
                time.sleep(1.5)
            except Exception as e:  # noqa: BLE001
                print(f"skip download {item['id']}: {e}")
                continue
        else:
            print(f"keep {dest.name}")
        saved.append(
            {
                **item,
                "local_path": dest.relative_to(ROOT).as_posix(),
                "license": info["license"],
                "artist": info["artist"],
                "commons_url": info["commons_url"],
                "source_url": info["url"],
            }
        )
        print(f"  -> {dest.name} ({info['license']})")

    manifest = {
        "story": "cjp_origin",
        "note": "Free Wikimedia Commons references for educational test comic atmosphere.",
        "images": saved,
    }
    man = out_dir / "manifest.json"
    man.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {man} ({len(saved)} images)")


if __name__ == "__main__":
    main()
