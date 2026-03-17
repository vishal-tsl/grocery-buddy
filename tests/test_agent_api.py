import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import NormalizedItem

@pytest.fixture
def client():
    return TestClient(app)

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

def test_agent_parse(client):
    response = client.post(
        "/api/v1/agents/parse",
        json={"text": "I need some milk 2% and a loaf of bread"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    items = data["items"]
    
    # Parser should extract the core items
    assert len(items) >= 2
    assert any("milk" in i.lower() for i in items)
    assert any("bread" in i.lower() for i in items)


def test_agent_normalize(client):
    response = client.post(
        "/api/v1/agents/normalize",
        json={"items": ["milk 2%", "whole wheat bread 1 loaf", "Häagen-Dazs vanilla bean ice cream 1 pint"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    items = data["items"]
    
    assert len(items) == 3
    
    # Check branded extraction
    ice_cream = next(i for i in items if "ice cream" in i["normalized_product_name"].lower())
    assert ice_cream["has_brand"] is True
    assert "häagen-dazs" in ice_cream["normalized_product_name"].lower()
    
    # Check generic extraction
    milk = next(i for i in items if "milk" in i["normalized_product_name"].lower())
    assert milk["has_brand"] is False
    assert "2%" in [m.lower() for m in milk.get("modifiers", [])]


@pytest.mark.asyncio
async def test_agent_resolve(async_client):
    # Mock some normalized items
    items = [
        NormalizedItem(
            normalized_product_name="milk",
            quantity=1,
            unit="gallon",
            modifiers=["2%"],
            has_brand=False,
            original_text="milk 2%"
        ).model_dump()
    ]
    
    response = await async_client.post(
        "/api/v1/agents/resolve",
        json={"items": items}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    
    # The resolver should have added structured attributes (even without mocking Autocomplete, 
    # the fallback/AI behavior will map something)
    structured_items = data["items"]
    assert len(structured_items) == 1
    assert structured_items[0]["product_name"] is not None
