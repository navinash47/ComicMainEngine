"""Tracked API clients — every call writes tokens + estimated USD into SQLite.

When USE_OMNIROUTE=1 (default), Anthropic/OpenAI traffic goes through local OmniRoute
at OMNIROUTE_BASE_URL (http://127.0.0.1:20128).
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from comicengine.config import (
    USE_OMNIROUTE,
    env,
    omniroute_anthropic_base,
    omniroute_api_key,
    omniroute_openai_base,
    routing_label,
)
from comicengine.pricing import gemini_image_cost_usd, llm_cost_usd
from comicengine.usage import ApiCall, TimedCall, UsageDB


class TrackedClients:
    def __init__(self, db: UsageDB | None = None, phase: str = "") -> None:
        self.db = db or UsageDB()
        self.phase = phase
        self._anthropic = None
        self._openai = None
        self._genai = None

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    def _provider_tag(self, native: str) -> str:
        return f"omniroute:{native}" if USE_OMNIROUTE else native

    def _anthropic_client(self):
        import anthropic

        if self._anthropic is not None:
            return self._anthropic
        if USE_OMNIROUTE:
            key = omniroute_api_key()
            if not key:
                raise RuntimeError(
                    "OmniRoute enabled but no key found. Set OMNIROUTE_API_KEY "
                    "(same value as Cursor Models → OpenAI API Key for :20128/v1)."
                )
            self._anthropic = anthropic.Anthropic(
                api_key=key,
                base_url=omniroute_anthropic_base(),
            )
        else:
            key = env("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError("ANTHROPIC_API_KEY missing in .env")
            self._anthropic = anthropic.Anthropic(api_key=key)
        return self._anthropic

    def _openai_client(self):
        from openai import OpenAI

        if self._openai is not None:
            return self._openai
        if USE_OMNIROUTE:
            key = omniroute_api_key()
            if not key:
                raise RuntimeError(
                    "OmniRoute enabled but no key found. Set OMNIROUTE_API_KEY "
                    "(same value as Cursor Models → OpenAI API Key for :20128/v1)."
                )
            self._openai = OpenAI(api_key=key, base_url=omniroute_openai_base())
        else:
            key = env("OPENAI_API_KEY")
            if not key:
                raise RuntimeError("OPENAI_API_KEY missing in .env")
            self._openai = OpenAI(api_key=key)
        return self._openai

    # --- Anthropic (cheap hello / later scripts) ---
    def anthropic_hello(self, model: str | None = None) -> str:
        model = model or (env("OMNIROUTE_ANTHROPIC_MODEL") or "auto/cheap")
        client = self._anthropic_client()

        call = ApiCall(
            provider=self._provider_tag("anthropic"),
            model=model,
            purpose="hello",
            phase=self.phase,
            meta={"route": routing_label(), "category": "text"},
        )
        with TimedCall(self.db, call):
            msg = client.messages.create(
                model=model,
                max_tokens=32,
                messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            )
            call.input_tokens = int(msg.usage.input_tokens)
            call.output_tokens = int(msg.usage.output_tokens)
            call.cost_usd = llm_cost_usd(model, call.input_tokens, call.output_tokens)
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            call.meta = {**(call.meta or {}), "preview": text[:80]}
            return text

    # --- OpenAI hello ---
    def openai_hello(self, model: str | None = None) -> str:
        model = model or (env("OMNIROUTE_OPENAI_MODEL") or "auto/cheap")
        client = self._openai_client()

        call = ApiCall(
            provider=self._provider_tag("openai"),
            model=model,
            purpose="hello",
            phase=self.phase,
            meta={"route": routing_label(), "category": "text"},
        )
        with TimedCall(self.db, call):
            resp = client.chat.completions.create(
                model=model,
                max_tokens=16,
                messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            )
            usage = resp.usage
            call.input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            call.output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
            call.cost_usd = llm_cost_usd(model, call.input_tokens, call.output_tokens)
            text = (resp.choices[0].message.content or "").strip()
            call.meta = {**(call.meta or {}), "preview": text[:80]}
            return text

    # --- Gemini image (Nano Banana) ---
    def gemini_image(
        self,
        prompt: str,
        *,
        out_path: Path,
        model: str = "gemini-3.1-flash-image-preview",
        purpose: str = "image",
        size_hint: str = "2K",
    ) -> Path:
        from google import genai
        from google.genai import types

        if self._genai is None:
            key = env("GOOGLE_API_KEY")
            if not key:
                raise RuntimeError("GOOGLE_API_KEY missing in .env")
            # Image generation ALWAYS uses direct GOOGLE_API_KEY from .env — never OmniRoute.
            self._genai = genai.Client(api_key=key)

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        call = ApiCall(
            provider="google",
            model=model,
            purpose=purpose,
            phase=self.phase,
            meta={"prompt_chars": len(prompt), "route": "direct"},
        )
        with TimedCall(self.db, call):
            resp = self._genai.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )
            um = getattr(resp, "usage_metadata", None)
            if um:
                call.input_tokens = int(getattr(um, "prompt_token_count", 0) or 0)
                call.output_tokens = int(getattr(um, "candidates_token_count", 0) or 0)
                call.image_tokens = int(getattr(um, "candidates_token_count", 0) or 0)

            saved = False
            for part in resp.candidates[0].content.parts:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    data = inline.data
                    if isinstance(data, str):
                        data = base64.b64decode(data)
                    out_path.write_bytes(data)
                    saved = True
                    break
            if not saved:
                raise RuntimeError("Gemini returned no image bytes")

            call.cost_usd = gemini_image_cost_usd(
                model, size=size_hint, image_tokens=call.image_tokens or None
            )
            from comicengine.analytics import check_image_quality

            qa = check_image_quality(out_path)
            call.meta["out_path"] = str(out_path)
            call.meta["category"] = "image"
            call.meta["image_quality"] = qa
            if qa.get("verdict") == "fail":
                call.meta["quality_warning"] = True
            return out_path

    def gemini_hello(self, model: str | None = None) -> str:
        """Direct Google only — OmniRoute is for coding/LLM text (Anthropic/OpenAI paths)."""
        from google import genai

        model = model or "gemini-3.1-flash-lite"
        if self._genai is None:
            key = env("GOOGLE_API_KEY")
            if not key:
                raise RuntimeError("GOOGLE_API_KEY missing in .env")
            self._genai = genai.Client(api_key=key)

        call = ApiCall(
            provider="google",
            model=model,
            purpose="hello",
            phase=self.phase,
            meta={"route": "direct", "category": "text"},
        )
        with TimedCall(self.db, call):
            resp = self._genai.models.generate_content(model=model, contents="Reply with exactly: ok")
            um = getattr(resp, "usage_metadata", None)
            if um:
                call.input_tokens = int(getattr(um, "prompt_token_count", 0) or 0)
                call.output_tokens = int(getattr(um, "candidates_token_count", 0) or 0)
            call.cost_usd = llm_cost_usd(model, call.input_tokens, call.output_tokens)
            text = (resp.text or "").strip()
            call.meta = {"preview": text[:80], "route": "direct"}
            return text


def ping_all(phase: str = "phase0") -> dict[str, Any]:
    """Cheap connectivity checks (~cents). Does NOT generate images."""
    c = TrackedClients(phase=phase)
    results: dict[str, Any] = {"route": routing_label(), "base": omniroute_openai_base() if USE_OMNIROUTE else "direct"}
    for name, fn in [
        ("anthropic", c.anthropic_hello),
        ("openai", c.openai_hello),
        ("google", c.gemini_hello),
    ]:
        try:
            results[name] = {"ok": True, "text": fn()}
        except Exception as e:  # noqa: BLE001 — surface to CLI
            results[name] = {"ok": False, "error": str(e)}
    return results
