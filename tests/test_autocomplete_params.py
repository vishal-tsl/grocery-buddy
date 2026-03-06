"""Test that autocomplete API is called with the expected query params."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_search_uses_expected_params():
    """Verify search() sends: query, limit=20, lat/lng, excludeSubcategory=false, excludeProductNames=true, includeProducts=true, includeImages=true, enrichKeyword=true."""
    from app.services.autocomplete import AutocompleteClient

    with patch("app.services.autocomplete.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            autocomplete_base_url="https://api.example.com/suggest",
            autocomplete_auth_token="test-token",
            app_name="grocery-buddy",
            app_version="1.0",
            autocomplete_lat=44.8828,
            autocomplete_lng=-93.2007,
        )
        client = AutocompleteClient()

    response_json = {
        "content": {
            "suggests": [
                {"id": 123, "type": "Product", "name": "Milk", "category": "Dairy", "imageUrl": None}
            ]
        }
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_get = AsyncMock()
        mock_get.return_value.raise_for_status = MagicMock()
        mock_get.return_value.json = MagicMock(return_value=response_json)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = mock_get
        mock_client_cls.return_value = mock_client

        await client.search("milk")

    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args
    assert call_kwargs[1]["params"]["query"] == "milk"
    assert call_kwargs[1]["params"]["limit"] == "20"
    assert call_kwargs[1]["params"]["latitude"] == "44.8828"
    assert call_kwargs[1]["params"]["longitude"] == "-93.2007"
    assert call_kwargs[1]["params"]["excludeSubcategory"] == "false"
    assert call_kwargs[1]["params"]["excludeProductNames"] == "true"
    assert call_kwargs[1]["params"]["includeProducts"] == "true"
    assert call_kwargs[1]["params"]["includeImages"] == "true"
    assert call_kwargs[1]["params"]["enrichKeyword"] == "true"


@pytest.mark.asyncio
async def test_search_returns_up_to_20_items_with_keywords_and_products():
    """Backend should return up to 20 items with a combination of keywords and products when API does."""
    from app.services.autocomplete import AutocompleteClient
    from app.models.schemas import SuggestionType

    with patch("app.services.autocomplete.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            autocomplete_base_url="https://api.example.com/suggest",
            autocomplete_auth_token="test-token",
            app_name="grocery-buddy",
            app_version="1.0",
            autocomplete_lat=44.8828,
            autocomplete_lng=-93.2007,
        )
        client = AutocompleteClient()

    # Simulate API returning 20 items: 10 keyword (Type) and 10 product (Product with id)
    suggests = []
    for i in range(10):
        suggests.append({
            "id": None,
            "type": "Type",
            "typeId": 100 + i,
            "typeName": f"Milk Type {i}",
            "name": f"Milk Type {i}",
            "category": "Dairy & Eggs",
            "brandId": None,
            "brandName": None,
            "imageUrl": None,
            "size": None,
        })
    for i in range(10):
        suggests.append({
            "id": 20000 + i,
            "type": "Product",
            "name": f"Brand Milk {i}",
            "category": "Dairy & Eggs",
            "typeId": 854,
            "typeName": "Milk",
            "brandId": 100,
            "brandName": "Test Brand",
            "imageUrl": f"https://images.basketsavings.com/img{i}.jpg",
            "size": "1 gal",
        })

    response_json = {"content": {"suggests": suggests}}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_get = AsyncMock()
        mock_get.return_value.raise_for_status = MagicMock()
        mock_get.return_value.json = MagicMock(return_value=response_json)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = mock_get
        mock_client_cls.return_value = mock_client

        result = await client.search("milk")

    assert len(result) == 20, "Backend should return 20 items when API returns 20"
    keyword_count = sum(1 for p in result if p.suggestion_type == SuggestionType.KEYWORD)
    product_count = sum(1 for p in result if p.suggestion_type == SuggestionType.PRODUCT)
    assert keyword_count >= 1, "Should have at least one keyword suggestion"
    assert product_count >= 1, "Should have at least one product suggestion"
    assert keyword_count + product_count == 20, "All 20 items should be either keyword or product"
