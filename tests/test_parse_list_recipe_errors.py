"""Recipe path on /parse-list must not return empty 200 when extraction fails."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_parse_list_recipe_url_empty_ingredients_returns_422():
    mock_recipe = MagicMock()
    mock_recipe.is_url = lambda text: text.strip().startswith("http")
    mock_recipe.extract_from_url = AsyncMock(
        return_value={
            "ingredients": [],
            "error": "Failed to fetch URL: connection refused",
            "recipe_name": "Unknown",
            "source_url": "https://example.com/r",
        }
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.api.routes.get_recipe_agent", return_value=mock_recipe):
            r = await client.post(
                "/api/v1/parse-list",
                json={"text": "https://example.com/r"},
            )
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body
    assert "fetch" in body["detail"].lower() or "ingredient" in body["detail"].lower()


def test_merge_line_items_with_llm_adds_missing_lines():
    from app.agents.parser import merge_line_items_with_llm

    llm = ["eggs", "milk"]
    lines = ["eggs", "milk", "cheese"]
    assert merge_line_items_with_llm(llm, lines) == ["eggs", "milk", "cheese"]


@pytest.mark.asyncio
async def test_parser_checkbox_prefix_stripped():
    from app.agents.parser import _CHECKBOX_LINE

    raw = "[x] taco shells\n[ ] beef\n[x]cheese"
    stripped = "\n".join(_CHECKBOX_LINE.sub("", line) for line in raw.splitlines())
    assert "[x]" not in stripped
    assert "taco shells" in stripped
    assert "beef" in stripped
    assert "cheese" in stripped
