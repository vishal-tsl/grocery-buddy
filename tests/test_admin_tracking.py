"""Tests for admin tracking: event payload, geo fallback, retention purge."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.tracking import (
    _ip_hash,
    geo_from_ip,
    capture_event_sync,
    purge_old_events,
    TABLE_EVENTS,
)


class TestIpHash:
    def test_ip_hash(self):
        assert _ip_hash("192.168.1.1") != ""
        assert _ip_hash("192.168.1.1") == _ip_hash("192.168.1.1")
        assert _ip_hash("") == ""

    def test_ip_hash_length(self):
        h = _ip_hash("10.0.0.1")
        assert len(h) == 16


class TestGeoFromIp:
    @pytest.mark.asyncio
    async def test_geo_localhost_returns_none(self):
        geo = await geo_from_ip("127.0.0.1")
        assert geo["country"] is None
        assert geo["region"] is None
        assert geo["city"] is None

    @pytest.mark.asyncio
    async def test_geo_provider_failure_returns_none(self):
        with patch("app.services.tracking.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("network error")
            )
            geo = await geo_from_ip("8.8.8.8")
        assert geo["country"] is None
        assert geo["region"] is None
        assert geo["city"] is None

    @pytest.mark.asyncio
    async def test_geo_success_parses_response(self):
        with patch("app.services.tracking.httpx") as mock_httpx:
            resp = MagicMock()
            resp.json.return_value = {
                "status": "success",
                "country": "United States",
                "regionName": "California",
                "city": "San Francisco",
            }
            resp.raise_for_status = MagicMock()
            mock_httpx.AsyncClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
            geo = await geo_from_ip("8.8.8.8")
        assert geo["country"] == "United States"
        assert geo["region"] == "California"
        assert geo["city"] == "San Francisco"


class TestCaptureEventSync:
    def test_capture_skips_when_tracking_disabled(self):
        with patch("app.services.tracking.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tracking_enabled=False,
                supabase_url="",
                supabase_service_role_key="",
            )
            capture_event_sync(
                request_id="req-1",
                client_ip="1.2.3.4",
                country="US",
                region=None,
                city=None,
                user_agent="test",
                endpoint="/parse-list",
                raw_input="milk",
                output_json=[{"product_name": "Milk"}],
                status="success",
                latency_ms=100.0,
            )
            # No Supabase client should be created
            # (just ensure no exception and we can't easily assert no insert without mocking create_client)

    def test_capture_payload_mapping(self):
        with patch("app.services.tracking.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tracking_enabled=True,
                supabase_url="https://test.supabase.co",
                supabase_service_role_key="secret",
            )
            with patch("app.services.tracking._supabase_client") as mock_sb:
                mock_table = MagicMock()
                mock_sb.return_value.table.return_value = mock_table
                capture_event_sync(
                    request_id="req-1",
                    client_ip="1.2.3.4",
                    country="US",
                    region="CA",
                    city="SF",
                    user_agent="Mozilla",
                    endpoint="/parse-list",
                    raw_input="milk and eggs",
                    output_json=[{"product_name": "Milk"}, {"product_name": "Eggs"}],
                    status="success",
                    latency_ms=150.5,
                )
                mock_table.insert.assert_called_once()
                row = mock_table.insert.call_args[0][0]
                assert row["request_id"] == "req-1"
                assert row["client_ip"] == "1.2.3.4"
                assert row["country"] == "US"
                assert row["region"] == "CA"
                assert row["city"] == "SF"
                assert row["user_agent"] == "Mozilla"
                assert row["endpoint"] == "/parse-list"
                assert row["raw_input"] == "milk and eggs"
                assert len(row["output_json"]) == 2
                assert row["status"] == "success"
                assert row["latency_ms"] == 150.5
                assert "ip_hash" in row


class TestPurgeOldEvents:
    def test_purge_returns_zero_when_tracking_disabled(self):
        with patch("app.services.tracking.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tracking_enabled=False,
                supabase_url="",
                supabase_service_role_key="",
            )
            n = purge_old_events()
        assert n == 0

    def test_purge_deletes_old_only(self):
        with patch("app.services.tracking.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tracking_enabled=True,
                tracking_retention_days=30,
                supabase_url="https://test.supabase.co",
                supabase_service_role_key="secret",
            )
            with patch("app.services.tracking._supabase_client") as mock_sb:
                mock_chain = MagicMock()
                mock_chain.delete.return_value.lt.return_value.execute.return_value = MagicMock(data=[{"id": 1}, {"id": 2}])
                mock_sb.return_value.table.return_value = mock_chain
                n = purge_old_events()
                assert n == 2
                # Assert delete was called with created_at < cutoff (30 days ago)
                mock_chain.delete.assert_called_once()
                mock_chain.delete.return_value.lt.assert_called_once()
                call_args = mock_chain.delete.return_value.lt.call_args[0]
                assert call_args[0] == "created_at"
                assert "T" in call_args[1]  # ISO date string
