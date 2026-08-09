"""LLM structured script engine — CJP (phase0.5) + general Phase 4 stories."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

from comicengine.config import (
    USE_OMNIROUTE,
    env,
    omniroute_anthropic_base,
    omniroute_api_key,
    routing_label,
)
from comicengine.characters_caesar import (
    CHARACTERS as CAESAR_CHARS,
    SYSTEM_CAESAR,
    TOPIC_ET_TU_BRUTUS,
)
from comicengine.characters_cjp import CHARACTERS as CJP_CHARS, TOPIC_CJP_ORIGIN
from comicengine.characters_hitler import (
    CHARACTERS as HITLER_CHARS,
    SYSTEM_HITLER,
    TOPIC_HITLER_WARNING,
)
from comicengine.episode_schema import Character, Episode
from comicengine.pricing import llm_cost_usd
from comicengine.usage import ApiCall, TimedCall, UsageDB


DEFAULT_BEDTIME_SYSTEM = """You write warm bedtime comics for a Dad reading to his Daughter.
Keep language simple, hopeful, and age-appropriate (about 7–10).
Never invent criminal acts or cruel private quotes for named real politicians.
Named leaders may appear briefly and respectfully as people who hear citizens.
This is a dramatized educational test episode.
Call submit_episode exactly once with the full episode."""


@dataclass(frozen=True)
class StorySpec:
    key: str
    file_stem: str
    topic_label: str
    voice: str
    system: str
    briefing: str
    characters: Sequence[Character]
    user_extra: str = ""


STORIES: dict[str, StorySpec] = {
    "cjp": StorySpec(
        key="cjp",
        file_stem="episode_cjp_origin",
        topic_label="How the CJP student protest started (test episode)",
        voice="dad_to_daughter_bedtime",
        system=DEFAULT_BEDTIME_SYSTEM,
        briefing=TOPIC_CJP_ORIGIN,
        characters=CJP_CHARS,
        user_extra=(
            "Open with Dad & Daughter at bedtime; end with gentle hope about fairness. "
            "Include Abhijeet Dipke, students, and brief respectful moments with Modiji and Amit Shah."
        ),
    ),
    "et_tu_brutus": StorySpec(
        key="et_tu_brutus",
        file_stem="episode_et_tu_brutus",
        topic_label="Et tu, Brute? — Julius Caesar and the fragile Roman Republic",
        voice="dad_to_daughter_teen_history",
        system=SYSTEM_CAESAR,
        briefing=TOPIC_ET_TU_BRUTUS,
        characters=CAESAR_CHARS,
        user_extra=(
            "Write through character lenses (Caesar, Brutus, Cassius, Antony, People) then Dad analogies. "
            "Include modern lessons on fragile democracy and why assassination is not a fix."
        ),
    ),
    "hitler_warning": StorySpec(
        key="hitler_warning",
        file_stem="episode_hitler_warning",
        topic_label="Hitler, propaganda, and how democracy can die — teen warning episode",
        voice="dad_to_daughter_teen_history",
        system=SYSTEM_HITLER,
        briefing=TOPIC_HITLER_WARNING,
        characters=HITLER_CHARS,
        user_extra=(
            "Rotate perspectives including Hitler/Goebbels/Eichmann ONLY to expose ideology; "
            "always counter with Jewish teen voice, resistors, or Dad. "
            "Connect patterns to current-world propaganda and minority hate without naming living leaders as criminals."
        ),
    ),
}


def _normalize_verdict(raw: Any) -> str:
    s = str(raw or "simplified").strip().lower()
    if s in {"supported", "disputed", "simplified", "dramatized"}:
        return s
    if s in {"true", "yes", "accurate", "correct", "historical", "fact"}:
        return "supported"
    if s in {"false", "partly false", "misleading", "myth", "lie", "propaganda"}:
        return "disputed"
    if "dramat" in s or "legend" in s or "shakespeare" in s:
        return "dramatized"
    return "simplified"


def _flatten_dialogue(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                speaker = item.get("speaker") or item.get("name") or item.get("id") or ""
                line = item.get("line") or item.get("text") or item.get("dialogue") or ""
                if speaker and line:
                    parts.append(f"{speaker}: {line}")
                elif line:
                    parts.append(str(line))
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if isinstance(raw, dict):
        return _flatten_dialogue([raw])
    return str(raw)


def _normalize_episode_payload(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    checks = []
    for item in out.get("fact_checks") or []:
        if not isinstance(item, dict):
            continue
        checks.append(
            {
                "claim": str(item.get("claim") or item.get("statement") or ""),
                "verdict": _normalize_verdict(item.get("verdict")),
                "source_note": str(item.get("source_note") or item.get("note") or ""),
            }
        )
    out["fact_checks"] = checks

    panels = []
    for i, panel in enumerate(out.get("panels") or [], start=1):
        if not isinstance(panel, dict):
            continue
        p = dict(panel)
        scene = (
            p.get("scene_description")
            or p.get("scene")
            or p.get("description")
            or p.get("caption")
            or ""
        )
        art = p.get("art_prompt") or p.get("visual") or scene
        chars = p.get("characters") or []
        if isinstance(chars, str):
            chars = [c.strip() for c in chars.split(",") if c.strip()]
        panels.append(
            {
                "index": int(p.get("index") or i),
                "scene_description": str(scene),
                "characters": list(chars),
                "dialogue": _flatten_dialogue(p.get("dialogue")),
                "caption": str(p.get("caption") or ""),
                "art_prompt": str(art),
                "emotion": str(p.get("emotion") or "serious"),
            }
        )
    out["panels"] = panels
    return out


def _episode_tool_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "topic": {"type": "string"},
            "season": {"type": "integer"},
            "episode_no": {"type": "integer"},
            "voice": {"type": "string"},
            "disclaimer": {"type": "string"},
            "fact_sheet": {"type": "array", "items": {"type": "string"}},
            "fact_checks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "claim": {"type": "string"},
                        "verdict": {
                            "type": "string",
                            "enum": ["supported", "disputed", "simplified", "dramatized"],
                        },
                        "source_note": {"type": "string"},
                    },
                    "required": ["claim", "verdict", "source_note"],
                },
            },
            "narrative_summary": {"type": "string"},
            "panels": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "index": {"type": "integer"},
                        "scene_description": {"type": "string"},
                        "characters": {"type": "array", "items": {"type": "string"}},
                        "dialogue": {"type": "string"},
                        "caption": {"type": "string"},
                        "art_prompt": {"type": "string"},
                        "emotion": {"type": "string"},
                    },
                    "required": [
                        "index",
                        "scene_description",
                        "characters",
                        "dialogue",
                        "caption",
                        "art_prompt",
                        "emotion",
                    ],
                },
            },
        },
        "required": [
            "title",
            "topic",
            "season",
            "episode_no",
            "voice",
            "disclaimer",
            "fact_sheet",
            "fact_checks",
            "narrative_summary",
            "panels",
        ],
    }


def _anthropic_client() -> tuple[Any, str]:
    import anthropic

    if USE_OMNIROUTE:
        key = omniroute_api_key()
        if not key:
            raise RuntimeError(
                "OmniRoute enabled but no OMNIROUTE_API_KEY "
                "(use same key as Cursor Models → OpenAI API Key for :20128/v1)."
            )
        return anthropic.Anthropic(api_key=key, base_url=omniroute_anthropic_base()), "omniroute:anthropic"
    key = env("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing in .env")
    return anthropic.Anthropic(api_key=key), "anthropic"


def generate_episode(
    story_key: str,
    *,
    panel_count: int = 16,
    model: str | None = None,
    phase: str = "phase4",
    db: UsageDB | None = None,
) -> Episode:
    """Generate a validated Episode for a registered story key."""
    if story_key not in STORIES:
        raise KeyError(f"unknown story {story_key!r}; choose from {sorted(STORIES)}")
    spec = STORIES[story_key]
    db = db or UsageDB()
    model = model or (env("OMNIROUTE_SCRIPT_MODEL") if USE_OMNIROUTE else None) or (
        "auto" if USE_OMNIROUTE else "claude-haiku-4-5"
    )
    client, provider = _anthropic_client()

    char_json = json.dumps([c.model_dump() for c in spec.characters], indent=2)
    user = f"""Write an educational comic episode for story key={spec.key}.

Canonical character ids (use ONLY these ids in panel.characters):
{char_json}

Topic briefing:
{spec.briefing}

Extra requirements:
{spec.user_extra}

Must:
- Exactly {panel_count} panels, indices 1..{panel_count}
- Open with Dad & Daughter framing; end with Dad & Daughter takeaway
- Rotate character perspectives in dialogue/captions as briefed
- Keep art_prompt short (1-2 sentences) + Korean manhwa webtoon style
- Include at least 4 fact_sheet bullets and 3 fact_checks
- Submit via the submit_episode tool only
"""

    tools = [
        {
            "name": "submit_episode",
            "description": "Submit the finished comic episode JSON.",
            "input_schema": _episode_tool_schema(),
        }
    ]

    max_attempts = 3
    data: dict[str, Any] | None = None
    last_err = ""
    for attempt in range(1, max_attempts + 1):
        use_tools = attempt < max_attempts
        call = ApiCall(
            provider=provider,
            model=model,
            purpose="script_episode",
            phase=phase,
            meta={
                "panel_count": panel_count,
                "topic": story_key,
                "mode": "tool_use" if use_tools else "json_only",
                "route": routing_label(),
                "category": "text",
                "attempt": attempt,
            },
        )
        with TimedCall(db, call):
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": 16000,
                "system": spec.system,
                "messages": [
                    {
                        "role": "user",
                        "content": user
                        if use_tools
                        else (
                            user
                            + "\n\nIMPORTANT: Tools unavailable. Reply with ONLY one JSON object "
                            "(no markdown fences) matching the submit_episode schema fields: "
                            "title, topic, season, episode_no, voice, disclaimer, fact_sheet, "
                            "fact_checks, narrative_summary, panels."
                        ),
                    }
                ],
            }
            if use_tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = {"type": "tool", "name": "submit_episode"}
            msg = client.messages.create(**kwargs)
            call.input_tokens = int(msg.usage.input_tokens)
            call.output_tokens = int(msg.usage.output_tokens)
            call.cost_usd = llm_cost_usd(model, call.input_tokens, call.output_tokens)

            for block in msg.content:
                if getattr(block, "type", "") == "tool_use" and block.name == "submit_episode":
                    data = dict(block.input)
                    break
            if data is None:
                texts = [
                    getattr(b, "text", "")
                    for b in msg.content
                    if getattr(b, "type", "") == "text"
                ]
                blob = "\n".join(texts).strip()
                if blob.startswith("```"):
                    blob = blob.strip("`")
                    if blob.startswith("json"):
                        blob = blob[4:].strip()
                if blob:
                    try:
                        start = blob.find("{")
                        end = blob.rfind("}")
                        if start >= 0 and end > start:
                            data = json.loads(blob[start : end + 1])
                    except json.JSONDecodeError as e:
                        last_err = f"stop={getattr(msg, 'stop_reason', None)} json={e}"
                else:
                    last_err = (
                        f"stop={getattr(msg, 'stop_reason', None)} "
                        f"blocks={[getattr(b, 'type', None) for b in msg.content]}"
                    )
            if data is not None:
                break
            last_err = last_err or "model did not call submit_episode"

    if data is None:
        raise RuntimeError(last_err or "model did not call submit_episode")

    chars = list(spec.characters)
    data = _normalize_episode_payload(data)
    episode = Episode.model_validate({**data, "characters": [c.model_dump() for c in chars]})
    episode.characters = chars
    episode.topic = spec.topic_label
    episode.voice = spec.voice
    return episode


def generate_cjp_test_episode(
    *,
    panel_count: int = 12,
    model: str | None = None,
    phase: str = "phase0.5",
    db: UsageDB | None = None,
) -> Episode:
    """Backward-compatible CJP generator used by phase0_5_script.py."""
    return generate_episode("cjp", panel_count=panel_count, model=model, phase=phase, db=db)
