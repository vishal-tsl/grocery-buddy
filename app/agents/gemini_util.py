"""Lazy Gemini client — avoids crashing process boot when GEMINI_API_KEY is unset (e.g. Render)."""

from __future__ import annotations

from google import genai

from app.config import get_settings


def gemini_api_key_configured() -> bool:
    return bool((get_settings().gemini_api_key or "").strip())


def require_genai_client() -> genai.Client:
    key = (get_settings().gemini_api_key or "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it in your host's environment variables "
            "(Render: Dashboard → Environment → GEMINI_API_KEY)."
        )
    return genai.Client(api_key=key)
