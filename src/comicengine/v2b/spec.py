"""Versioned 2B location + panel specs. Do not put these on episode_schema.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from comicengine.config import ROOT

SPECS = ROOT / "data" / "v2b" / "specs"
B5_RUN = SPECS / "himym_ep01_b5.json"
LOCATIONS = SPECS / "locations"


class CameraSpec(BaseModel):
    location: tuple[float, float, float]
    lens: float
    target: tuple[float, float, float]


class LightSpec(BaseModel):
    name: str
    kind: str = "AREA"
    location: tuple[float, float, float]
    energy: float
    color: tuple[float, float, float]
    size: float = 0.4
    target: tuple[float, float, float] | None = None


class PrimitiveSpec(BaseModel):
    name: str
    scale: tuple[float, float, float]
    loc: tuple[float, float, float]
    color: tuple[float, float, float]
    roughness: float = 0.55


class CharacterPlacement(BaseModel):
    id: str
    pose: str = "seated"
    loc: tuple[float, float, float]
    scale: float = 1.0


class LocationSpec(BaseModel):
    id: str
    version: int = 1
    display_name: str
    look: str
    world_color: tuple[float, float, float] = (0.10, 0.09, 0.08)
    world_strength: float = 0.25
    primitives: list[PrimitiveSpec]
    lights: list[LightSpec]
    cameras: dict[str, CameraSpec]
    characters: list[CharacterPlacement] = Field(default_factory=list)


class PanelSpec(BaseModel):
    id: str
    location_id: str
    camera: str
    characters: list[str] = Field(default_factory=list)
    character_lora: str | None = None
    seed: int = 42
    positive: str | None = None


class B5Run(BaseModel):
    id: str = "himym_ep01_b5"
    locations: list[str]
    panels: list[PanelSpec]


def load_location(location_id: str) -> LocationSpec:
    path = LOCATIONS / f"{location_id}.json"
    return LocationSpec.model_validate_json(path.read_text())


def load_b5_run(path: Path | None = None) -> B5Run:
    return B5Run.model_validate_json(Path(path or B5_RUN).read_text())


def dump_location_json(spec: LocationSpec) -> dict[str, Any]:
    return json.loads(spec.model_dump_json())
