"""Pydantic episode schema for ComicEngine scripts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Character(BaseModel):
    id: str
    display_name: str
    role: str
    look: str = ""
    notes: str = ""


class FactCheckItem(BaseModel):
    claim: str
    verdict: Literal["supported", "disputed", "simplified", "dramatized"] = "simplified"
    source_note: str = ""


class Panel(BaseModel):
    index: int = Field(ge=1)
    scene_description: str
    characters: list[str] = Field(default_factory=list)
    dialogue: str = ""
    caption: str = ""
    art_prompt: str = ""
    emotion: str = "warm"
    # Phase 5 render metadata (optional)
    image_path: str | None = None
    image_method: str | None = None
    image_qa: str | None = None
    composed_image_path: str | None = None


class Episode(BaseModel):
    title: str
    topic: str
    season: int = 0
    episode_no: int = 1
    voice: str = "dad_to_daughter_bedtime"
    disclaimer: str = (
        "Dramatized educational comic for pipeline testing. "
        "Based on publicly reported events; simplified for a young listener."
    )
    characters: list[Character]
    fact_sheet: list[str] = Field(default_factory=list)
    fact_checks: list[FactCheckItem] = Field(default_factory=list)
    narrative_summary: str = ""
    panels: list[Panel]
    webtoon_path: str | None = None
    pdf_path: str | None = None
    webtoon_image_only_path: str | None = None
    pdf_image_only_path: str | None = None

    @field_validator("panels")
    @classmethod
    def ordered_panels(cls, panels: list[Panel]) -> list[Panel]:
        if not panels:
            raise ValueError("episode needs panels")
        return panels
