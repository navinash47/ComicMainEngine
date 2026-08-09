"""Warm painterly storybook style lock (Phase 2)."""

STYLE_SUFFIX = (
    "warm painterly children's-storybook illustration, soft gouache textures, "
    "golden bedtime lighting, gentle rounded shapes, cinematic picture-book composition, "
    "NOT anime, NOT manga, NOT photorealistic"
)

NEGATIVE_PROMPT = (
    "anime, manga, cel shading, photorealistic, 3d render, uncanny, horror, gore, text artifacts"
)


def build_prompt(scene: str, *, characters: str | None = None, negative: bool = False) -> str:
    parts = [scene.strip()]
    if characters:
        parts.append(f"Characters: {characters.strip()}")
    parts.append(STYLE_SUFFIX)
    text = ". ".join(parts)
    if negative:
        text = f"{text}. Avoid: {NEGATIVE_PROMPT}"
    return text
