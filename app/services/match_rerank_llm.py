"""Optional Gemini re-rank: pick best 1-based index among top-N autocomplete candidates."""

import asyncio
import json

from app.agents.gemini_util import gemini_api_key_configured, require_genai_client
from app.models.schemas import AutocompleteProduct, NormalizedItem, SuggestionType


RERANK_PROMPT = """You pick the single best grocery catalog match for the user's line.

Rules:
- Prefer exact or near-exact wording for brands and product names; never invent spellings.
- If the user was generic (e.g. "eggs"), prefer a generic category/keyword-style row over a specific brand if both appear.
- Use the optional RECIPE_CONTEXT only to disambiguate (e.g. taco vs pasta shells).

Return ONLY JSON: {"choice": <1-based index integer>, "reason": "<short>"}

USER_LINE: {user_line}
ORIGINAL: {original_text}
CONTEXT: {context}

CANDIDATES (1-based index, name, category, type):
{candidates}
"""


async def pick_best_candidate_sku(
    item: NormalizedItem,
    candidates: list[AutocompleteProduct],
) -> str | None:
    if not candidates:
        return None
    if not gemini_api_key_configured():
        return None
    client = require_genai_client()
    lines = []
    for i, c in enumerate(candidates, start=1):
        typ = "keyword" if c.suggestion_type == SuggestionType.KEYWORD else "product"
        lines.append(f'{i}. name="{c.name}" category="{c.category or ""}" type={typ}')
    prompt = RERANK_PROMPT.format(
        user_line=item.normalized_product_name,
        original_text=item.original_text or item.normalized_product_name,
        context=item.prompt_context or "(none)",
        candidates="\n".join(lines),
    )
    def _call() -> str:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"temperature": 0},
        )
        return (response.text or "").strip()

    text = await asyncio.to_thread(_call)
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    idx = int(data.get("choice", 0))
    if 1 <= idx <= len(candidates):
        return candidates[idx - 1].sku
    return None
