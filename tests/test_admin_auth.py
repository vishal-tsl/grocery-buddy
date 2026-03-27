"""Tests for admin API: login, auth required for events/metrics, parse-list tracking."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.schemas import NormalizedItem, StructuredItem


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def admin_password():
    return "test-admin-secret"


@pytest.fixture
def admin_email():
    return "admin@test.example"


def _mock_admin_settings(admin_password, admin_email):
    return MagicMock(admin_panel_password=admin_password, admin_allowed_email=admin_email)


def test_admin_login_rejects_wrong_password(client, admin_password, admin_email):
    with patch("app.api.admin.get_settings") as mock_settings:
        mock_settings.return_value = _mock_admin_settings(admin_password, admin_email)
        r = client.post(
            "/api/v1/admin/login",
            json={"email": admin_email, "password": "wrong"},
        )
    assert r.status_code == 401


def test_admin_login_rejects_wrong_email(client, admin_password, admin_email):
    with patch("app.api.admin.get_settings") as mock_settings:
        mock_settings.return_value = _mock_admin_settings(admin_password, admin_email)
        r = client.post(
            "/api/v1/admin/login",
            json={"email": "other@example.com", "password": admin_password},
        )
    assert r.status_code == 401


def test_admin_login_accepts_correct_email_and_password(client, admin_password, admin_email):
    with patch("app.api.admin.get_settings") as mock_settings:
        mock_settings.return_value = _mock_admin_settings(admin_password, admin_email)
        r = client.post(
            "/api/v1/admin/login",
            json={"email": admin_email, "password": admin_password},
        )
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["expires_in"] > 0


def test_admin_events_requires_auth(client):
    r = client.get("/api/v1/admin/events")
    assert r.status_code == 401


def test_admin_events_accepts_valid_token(client, admin_password, admin_email):
    mock_settings = _mock_admin_settings(admin_password, admin_email)
    with patch("app.api.admin.get_settings", return_value=mock_settings):
        login_r = client.post(
            "/api/v1/admin/login",
            json={"email": admin_email, "password": admin_password},
        )
        token = login_r.json()["token"]
        with patch("app.api.admin._supabase_client") as mock_sb:
            chain = MagicMock()
            chain.select.return_value = chain
            chain.gte.return_value = chain
            chain.lte.return_value = chain
            chain.eq.return_value = chain
            chain.ilike.return_value = chain
            chain.order.return_value = chain
            chain.range.return_value = chain
            chain.execute.return_value = MagicMock(data=[], count=0)
            mock_sb.return_value.table.return_value = chain
            r = client.get("/api/v1/admin/events", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "data" in r.json()


def test_admin_metrics_requires_auth(client):
    r = client.get("/api/v1/admin/metrics")
    assert r.status_code == 401


def test_admin_metrics_accepts_valid_token(client, admin_password, admin_email):
    mock_settings = _mock_admin_settings(admin_password, admin_email)
    with patch("app.api.admin.get_settings", return_value=mock_settings):
        login_r = client.post(
            "/api/v1/admin/login",
            json={"email": admin_email, "password": admin_password},
        )
        token = login_r.json()["token"]
        with patch("app.api.admin._supabase_client") as mock_sb:
            mock_sb.return_value.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
                data=[
                    {"client_ip": "1.2.3.4", "country": "US", "status": "success", "latency_ms": 100},
                    {"client_ip": "5.6.7.8", "country": "US", "status": "success", "latency_ms": 200},
                ]
            )
            r = client.get("/api/v1/admin/metrics?days=7", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["total_requests"] == 2
    assert data["unique_ips"] == 2
    assert data["by_country"]["US"] == 2


def test_admin_purge_requires_auth(client):
    r = client.post("/api/v1/admin/purge")
    assert r.status_code == 401


def test_admin_purge_accepts_valid_token(client, admin_password, admin_email):
    mock_settings = _mock_admin_settings(admin_password, admin_email)
    with patch("app.api.admin.get_settings", return_value=mock_settings):
        login_r = client.post(
            "/api/v1/admin/login",
            json={"email": admin_email, "password": admin_password},
        )
        token = login_r.json()["token"]
        with patch("app.api.admin.purge_old_events", return_value=5):
            r = client.post("/api/v1/admin/purge", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["deleted"] == 5


def test_parse_list_calls_capture_event_on_success(client):
    """POST /parse-list should call capture_event with input, output, status, latency."""
    recipe_agent = MagicMock()
    recipe_agent.is_url = MagicMock(return_value=False)
    parser = MagicMock()
    parser.parse = MagicMock(return_value=["milk"])
    normalizer = MagicMock()
    normalizer.normalize_batch = MagicMock(
        return_value=[NormalizedItem(normalized_product_name="milk", original_text="milk")]
    )
    with patch("app.api.routes.gemini_api_key_configured", return_value=True):
        with patch("app.api.routes.get_recipe_agent", return_value=recipe_agent):
            with patch("app.api.routes.get_parser_agent", return_value=parser):
                with patch("app.api.routes.get_normalizer_agent", return_value=normalizer):
                    with patch("app.api.routes.get_resolver") as mock_resolver:
                        resolver = MagicMock()
                        resolver.resolve_batch = AsyncMock(
                            return_value=[
                                StructuredItem(
                                    product_name="Milk", sku=None, quantity=None, unit=None
                                ),
                            ]
                        )
                        mock_resolver.return_value = resolver
                        with patch(
                            "app.api.routes.capture_event", new_callable=AsyncMock
                        ) as mock_capture:
                            r = client.post(
                                "/api/v1/parse-list",
                                json={"text": "milk"},
                                headers={
                                    "x-forwarded-for": "10.0.0.1",
                                    "user-agent": "test-agent",
                                },
                            )
                            assert r.status_code == 200
                            mock_capture.assert_called_once()
                            call_kw = mock_capture.call_args[1]
                            assert call_kw["raw_input"] == "milk"
                            assert call_kw["status"] == "success"
                            assert len(call_kw["output_json"]) == 1
                            assert call_kw["output_json"][0]["product_name"] == "Milk"
                            assert "latency_ms" in str(call_kw)


def test_parse_list_calls_capture_event_on_error_path(client):
    """When parse/normalize fails, fallback path should still call capture_event with status=error."""
    recipe_agent = MagicMock()
    recipe_agent.is_url = MagicMock(return_value=False)
    parser = MagicMock()
    parser.parse = MagicMock(side_effect=Exception("LLM error"))
    with patch("app.api.routes.gemini_api_key_configured", return_value=True):
        with patch("app.api.routes.get_recipe_agent", return_value=recipe_agent):
            with patch("app.api.routes.get_parser_agent", return_value=parser):
                with patch("app.api.routes.capture_event", new_callable=AsyncMock) as mock_capture:
                    r = client.post(
                        "/api/v1/parse-list",
                        json={"text": "milk, eggs"},
                        headers={"x-forwarded-for": "10.0.0.2"},
                    )
                    assert r.status_code == 200
                    assert len(r.json()["items"]) == 2  # fallback split by comma
                    mock_capture.assert_called_once()
                    call_kw = mock_capture.call_args[1]
                    assert call_kw["raw_input"] == "milk, eggs"
                    assert call_kw["status"] == "error"
                    assert len(call_kw["output_json"]) == 2
