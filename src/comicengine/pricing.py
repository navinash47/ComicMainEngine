"""Point-in-time 2026 rates for local cost estimates. Re-check provider pages before budget commits."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenRates:
    input_per_m: float
    output_per_m: float


# USD per million tokens
LLM_RATES: dict[str, TokenRates] = {
    "claude-sonnet-4-6": TokenRates(3.0, 15.0),
    "claude-opus-4-8": TokenRates(5.0, 25.0),
    "claude-haiku-4-5": TokenRates(1.0, 5.0),
    "gpt-5.4": TokenRates(2.5, 15.0),
    "gpt-4.1": TokenRates(2.0, 8.0),
    "gpt-4.1-mini": TokenRates(0.4, 1.6),
    "gemini-3-pro": TokenRates(2.0, 12.0),
    "gemini-3.1-flash-lite": TokenRates(0.1, 0.4),
    "gemini-3.5-flash": TokenRates(0.3, 2.5),
    "gemini-3.6-flash": TokenRates(0.3, 2.5),
    "gemini-2.5-flash": TokenRates(0.3, 2.5),
}

# Gemini image: published token counts × image output rate (~$0.00012/token at 1K-2K)
GEMINI_IMAGE_COST = {
    "gemini-3-pro-image-preview": {"1K": 0.134, "2K": 0.134, "4K": 0.24},
    "gemini-3.1-flash-image-preview": {"default": 0.039},
    "gemini-2.5-flash-image": {"default": 0.039},
    "gemini-2.0-flash-preview-image-generation": {"default": 0.039},
}


def llm_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = LLM_RATES.get(model)
    if not rates:
        # conservative fallback estimate
        return (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
    return (input_tokens * rates.input_per_m + output_tokens * rates.output_per_m) / 1_000_000


def gemini_image_cost_usd(model: str, size: str = "2K", image_tokens: int | None = None) -> float:
    table = GEMINI_IMAGE_COST.get(model, {})
    if size in table:
        return float(table[size])
    if "default" in table:
        return float(table["default"])
    if image_tokens:
        return image_tokens * 0.00012
    return 0.134


# fal FLUX point-in-time estimates (re-check fal pricing page)
FAL_IMAGE_COST = {
    "fal-ai/flux/schnell": 0.003,
    "fal-ai/flux-1/schnell": 0.003,
    "fal-ai/flux-pro/kontext": 0.04,
}


def fal_image_cost_usd(model: str, num_images: int = 1) -> float:
    unit = FAL_IMAGE_COST.get(model, 0.003)
    return float(unit) * max(1, num_images)
