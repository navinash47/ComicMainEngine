"""Analytics: categorize calls, recommend models from logs, image quality checks."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from comicengine.config import OUTPUTS, ROOT, USAGE_DB_PATH

RECO_PATH = ROOT / "data" / "model_recommendations.json"

IMAGE_PURPOSE_HINTS = {
    "image",
    "phase1_single",
    "style_grid",
    "panel",
    "cover",
    "thumbnail",
}


def categorize(purpose: str = "", model: str = "", meta: dict[str, Any] | None = None) -> str:
    meta = meta or {}
    purpose_l = (purpose or "").lower()
    model_l = (model or "").lower()
    if meta.get("category"):
        return str(meta["category"])
    if purpose_l in IMAGE_PURPOSE_HINTS or "image" in purpose_l or "style" in purpose_l:
        return "image"
    if meta.get("out_path") or meta.get("image_quality"):
        return "image"
    if "image" in model_l or "nano" in model_l or "flux" in model_l:
        return "image"
    if purpose_l in {"hello", "script_episode", "fact_check", "narrative"}:
        return "text"
    if purpose_l in {"usage_sync", "cost_report"}:
        return "usage"
    return "text"


def check_image_quality(path: str | Path) -> dict[str, Any]:
    """Lightweight local QA — existence, dimensions, file size, blank/near-blank heuristic."""
    p = Path(path)
    result: dict[str, Any] = {
        "path": str(p),
        "exists": p.is_file(),
        "score": 0.0,
        "checks": {},
        "verdict": "fail",
    }
    if not p.is_file():
        result["checks"]["exists"] = False
        return result

    size = p.stat().st_size
    result["checks"]["exists"] = True
    result["checks"]["bytes"] = size
    result["checks"]["min_size"] = size >= 8_000

    try:
        from PIL import Image, ImageStat

        with Image.open(p) as im:
            im = im.convert("RGB")
            w, h = im.size
            result["checks"]["width"] = w
            result["checks"]["height"] = h
            result["checks"]["min_dims"] = w >= 512 and h >= 512
            stat = ImageStat.Stat(im)
            # mean brightness / channel variance — catch blank/near-solid frames
            means = stat.mean
            vars_ = stat.var
            mean_b = sum(means) / 3.0
            var_b = sum(vars_) / 3.0
            result["checks"]["mean_brightness"] = round(mean_b, 2)
            result["checks"]["variance"] = round(var_b, 2)
            result["checks"]["not_blank"] = var_b > 80.0
            result["checks"]["not_pure_white"] = mean_b < 250
            result["checks"]["not_pure_black"] = mean_b > 5
    except Exception as e:  # noqa: BLE001
        result["checks"]["pillow_error"] = str(e)
        result["verdict"] = "unknown"
        result["score"] = 0.3
        return result

    flags = [
        result["checks"].get("min_size"),
        result["checks"].get("min_dims"),
        result["checks"].get("not_blank"),
        result["checks"].get("not_pure_white"),
        result["checks"].get("not_pure_black"),
    ]
    passed = sum(1 for f in flags if f)
    result["score"] = round(passed / len(flags), 2)
    result["verdict"] = "pass" if result["score"] >= 0.8 else ("warn" if result["score"] >= 0.6 else "fail")
    return result


def _parse_meta(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    meta = _parse_meta(row.get("meta_json")) if "meta_json" in row else (row.get("meta") or {})
    cat = categorize(row.get("purpose") or "", row.get("model") or "", meta)
    iq = meta.get("image_quality")
    out = {
        **{k: v for k, v in row.items() if k != "meta_json"},
        "category": cat,
        "status": "ok" if row.get("ok") else "error",
        "meta": meta,
        "image_quality_score": (iq or {}).get("score") if isinstance(iq, dict) else None,
        "image_quality_verdict": (iq or {}).get("verdict") if isinstance(iq, dict) else None,
    }
    return out


class Analytics:
    def __init__(self, db_path: Path | None = None) -> None:
        self.path = Path(db_path or USAGE_DB_PATH)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def calls(
        self,
        *,
        limit: int = 200,
        category: str | None = None,
        phase: str | None = None,
        provider: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id, ts, phase, provider, model, purpose,
                   input_tokens, output_tokens, image_tokens,
                   cost_usd, latency_ms, ok, error, meta_json
            FROM api_call
            ORDER BY id DESC
            LIMIT ?
        """
        with self.connect() as conn:
            rows = [dict(r) for r in conn.execute(sql, (max(1, min(limit, 2000)),)).fetchall()]
        enriched = [enrich_row(r) for r in rows]
        if category and category != "all":
            enriched = [r for r in enriched if r["category"] == category]
        if phase:
            enriched = [r for r in enriched if (r.get("phase") or "") == phase]
        if provider:
            enriched = [r for r in enriched if provider in (r.get("provider") or "")]
        return enriched

    def stats(self, calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        calls = calls if calls is not None else self.calls(limit=1000)
        by_cat: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "ok": 0, "errors": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "image_tokens": 0, "latency_ms_sum": 0}
        )
        for c in calls:
            b = by_cat[c["category"]]
            b["calls"] += 1
            if c.get("ok"):
                b["ok"] += 1
            else:
                b["errors"] += 1
            b["cost_usd"] += float(c.get("cost_usd") or 0)
            b["input_tokens"] += int(c.get("input_tokens") or 0)
            b["output_tokens"] += int(c.get("output_tokens") or 0)
            b["image_tokens"] += int(c.get("image_tokens") or 0)
            b["latency_ms_sum"] += int(c.get("latency_ms") or 0)

        categories = []
        for name, b in sorted(by_cat.items(), key=lambda kv: -kv[1]["cost_usd"]):
            n = max(b["calls"], 1)
            categories.append(
                {
                    "category": name,
                    "calls": b["calls"],
                    "ok": b["ok"],
                    "errors": b["errors"],
                    "cost_usd": round(b["cost_usd"], 6),
                    "input_tokens": b["input_tokens"],
                    "output_tokens": b["output_tokens"],
                    "image_tokens": b["image_tokens"],
                    "avg_latency_ms": int(b["latency_ms_sum"] / n),
                    "success_rate": round(b["ok"] / n, 3),
                }
            )

        image_qa = [
            {
                "id": c["id"],
                "model": c.get("model"),
                "phase": c.get("phase"),
                "score": c.get("image_quality_score"),
                "verdict": c.get("image_quality_verdict"),
                "path": (c.get("meta") or {}).get("out_path"),
            }
            for c in calls
            if c["category"] == "image" and c.get("image_quality_verdict")
        ]

        return {
            "by_category": categories,
            "image_quality": image_qa[:50],
            "totals": {
                "calls": len(calls),
                "cost_usd": round(sum(float(c.get("cost_usd") or 0) for c in calls), 6),
                "errors": sum(1 for c in calls if not c.get("ok")),
            },
        }

    def recommendations(self, calls: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """From successful history: suggest cheapest & fastest model per category/purpose."""
        calls = calls if calls is not None else self.calls(limit=1000)
        buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for c in calls:
            if not c.get("ok"):
                continue
            key = (c.get("category") or "text", c.get("purpose") or "unknown")
            buckets[key].append(c)

        recs: list[dict[str, Any]] = []
        for (category, purpose), items in sorted(buckets.items()):
            by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for it in items:
                mid = f"{it.get('provider')}::{it.get('model')}"
                by_model[mid].append(it)

            scored = []
            for mid, rows in by_model.items():
                if len(rows) < 1:
                    continue
                avg_cost = sum(float(r.get("cost_usd") or 0) for r in rows) / len(rows)
                avg_lat = sum(int(r.get("latency_ms") or 0) for r in rows) / len(rows)
                # Prefer lower cost, then lower latency; quality score for images
                q_scores = [r.get("image_quality_score") for r in rows if r.get("image_quality_score") is not None]
                avg_q = sum(q_scores) / len(q_scores) if q_scores else None
                scored.append(
                    {
                        "model_key": mid,
                        "provider": rows[0].get("provider"),
                        "model": rows[0].get("model"),
                        "samples": len(rows),
                        "avg_cost_usd": round(avg_cost, 6),
                        "avg_latency_ms": int(avg_lat),
                        "avg_quality": round(avg_q, 2) if avg_q is not None else None,
                    }
                )

            if not scored:
                continue
            cheapest = sorted(scored, key=lambda x: (x["avg_cost_usd"], x["avg_latency_ms"]))[0]
            fastest = sorted(scored, key=lambda x: (x["avg_latency_ms"], x["avg_cost_usd"]))[0]
            best_q = None
            with_q = [s for s in scored if s["avg_quality"] is not None]
            if with_q:
                best_q = sorted(with_q, key=lambda x: (-(x["avg_quality"] or 0), x["avg_cost_usd"]))[0]

            # Optimal pick: for images prefer quality* then cost; for text prefer cost then speed
            if category == "image" and best_q:
                optimal = best_q
                reason = "highest avg image QA score, then lowest cost"
            else:
                optimal = cheapest
                reason = "lowest avg cost among successful calls"

            recs.append(
                {
                    "category": category,
                    "purpose": purpose,
                    "optimal": optimal,
                    "cheapest": cheapest,
                    "fastest": fastest,
                    "best_quality": best_q,
                    "reason": reason,
                    "note": "Recommendation only — scripts do not auto-switch yet.",
                }
            )

        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "recommendations": recs,
        }
        RECO_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECO_PATH.write_text(json.dumps(payload, indent=2))
        return recs

    def rescan_image_quality(self) -> dict[str, Any]:
        """Re-run QA on image outputs found under outputs/ and recent call metas."""
        updated = 0
        scanned = 0
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, meta_json FROM api_call
                ORDER BY id DESC LIMIT 500
                """
            ).fetchall()
            for row in rows:
                meta = _parse_meta(row["meta_json"])
                path = meta.get("out_path")
                if not path:
                    continue
                scanned += 1
                qa = check_image_quality(path)
                meta["image_quality"] = qa
                meta["category"] = "image"
                conn.execute(
                    "UPDATE api_call SET meta_json=? WHERE id=?",
                    (json.dumps(meta), row["id"]),
                )
                updated += 1
            conn.commit()

        # Also scan orphan images in outputs/
        orphans = 0
        if OUTPUTS.exists():
            for img in OUTPUTS.rglob("*.png"):
                orphans += 1
                check_image_quality(img)

        return {"scanned_calls": scanned, "updated_calls": updated, "files_seen": orphans}

    def dashboard(self, *, limit: int = 200, category: str | None = None) -> dict[str, Any]:
        calls = self.calls(limit=limit, category=category)
        # If category filter applied, stats for filtered set; recommendations use wider window
        wide = self.calls(limit=1000)
        stats = self.stats(calls)
        recs = self.recommendations(wide)
        return {
            "calls": calls,
            "stats": stats,
            "recommendations": recs,
            "filters": {"limit": limit, "category": category or "all"},
            "server_time": datetime.now(timezone.utc).isoformat(),
        }


analytics = Analytics()
