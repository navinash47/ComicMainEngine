"""Phase 0.5 — Anthropic structured script engine (cost-tracked)."""

from __future__ import annotations

import json
from typing import Any

from comicengine.characters_cjp import CHARACTERS, TOPIC_CJP_ORIGIN
from comicengine.config import env
from comicengine.episode_schema import Episode
from comicengine.pricing import llm_cost_usd
from comicengine.usage import ApiCall, TimedCall, UsageDB


SYSTEM = """You write warm bedtime comics for a Dad reading to his Daughter.
Keep language simple, hopeful, and age-appropriate (about 7–10).
Never invent criminal acts or cruel private quotes for named real politicians.
Named leaders may appear briefly and respectfully as people who hear citizens.
This is a dramatized educational test episode.
Call submit_episode exactly once with the full episode."""


def _episode_tool_schema() -> dict[str, Any]:
    # Keep schema lean so Haiku fills it reliably
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


def generate_cjp_test_episode(
    *,
    panel_count: int = 12,
    model: str = "claude-haiku-4-5",
    phase: str = "phase0.5",
    db: UsageDB | None = None,
) -> Episode:
    import anthropic

    db = db or UsageDB()
    key = env("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing in .env")

    client = anthropic.Anthropic(api_key=key)
    char_json = json.dumps([c.model_dump() for c in CHARACTERS], indent=2)
    user = f"""Write a bedtime comic episode that explains how the CJP (Cockroach Janta Party) student protest started in India.

Canonical character ids (use these ids in panel.characters):
{char_json}

Topic briefing:
{TOPIC_CJP_ORIGIN}

Requirements:
- Exactly {panel_count} panels, indices 1..{panel_count}
- Open with Dad & Daughter at bedtime; end with gentle hope about fairness
- Include Abhijeet Dipke, students, and brief respectful moments with Modiji and Amit Shah as leaders who hear the public
- Keep art_prompt short (1-2 sentences) + painterly children's-storybook style
- Submit via the submit_episode tool only
"""

    tools = [
        {
            "name": "submit_episode",
            "description": "Submit the finished bedtime comic episode JSON.",
            "input_schema": _episode_tool_schema(),
        }
    ]

    call = ApiCall(
        provider="anthropic",
        model=model,
        purpose="script_episode",
        phase=phase,
        meta={"panel_count": panel_count, "topic": "cjp_origin", "mode": "tool_use"},
    )
    with TimedCall(db, call):
        msg = client.messages.create(
            model=model,
            max_tokens=6000,
            system=SYSTEM,
            tools=tools,
            tool_choice={"type": "tool", "name": "submit_episode"},
            messages=[{"role": "user", "content": user}],
        )
        call.input_tokens = int(msg.usage.input_tokens)
        call.output_tokens = int(msg.usage.output_tokens)
        call.cost_usd = llm_cost_usd(model, call.input_tokens, call.output_tokens)

        data: dict[str, Any] | None = None
        for block in msg.content:
            if getattr(block, "type", "") == "tool_use" and block.name == "submit_episode":
                data = dict(block.input)
                break
        if data is None:
            raise RuntimeError("model did not call submit_episode")

    episode = Episode.model_validate({**data, "characters": [c.model_dump() for c in CHARACTERS]})
    episode.characters = CHARACTERS
    episode.topic = "How the CJP student protest started (test episode)"
    episode.voice = "dad_to_daughter_bedtime"
    return episode
