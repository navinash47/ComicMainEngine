"""Korean manhwa / webtoon style lock (Phase 2)."""

STYLE_NAME = "korean_manhwa"

STYLE_SUFFIX = (
    "Korean manhwa webtoon illustration style, clean ink line art, soft cel shading, "
    "expressive eyes, polished digital comic coloring, warm cinematic lighting, "
    "vertical webtoon panel composition, all-ages gentle mood, "
    "NOT photorealistic, NOT western cartoon, NOT chibi, NOT horror"
)

NEGATIVE_PROMPT = (
    "photorealistic, 3d render, uncanny, horror, gore, excessive violence, "
    "blurry, low quality, text artifacts, watermark, deformed hands"
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
