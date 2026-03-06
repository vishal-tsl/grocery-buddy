"""
Admin tracking: capture usage events (input, output, location from IP) and purge by retention.
Non-intrusive: location from server-side IP geolocation only.
"""
import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
TABLE_EVENTS = "tracking_events"


def _ip_hash(ip: str) -> str:
    if not ip:
        return ""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _supabase_client():
    from supabase import create_client
    s = get_settings()
    if not s.supabase_url or not s.supabase_service_role_key:
        return None
    return create_client(s.supabase_url, s.supabase_service_role_key)


async def geo_from_ip(ip: str) -> dict[str, str | None]:
    """Non-intrusive: resolve country/region/city from IP. No browser permission."""
    if not ip or ip in ("127.0.0.1", "::1"):
        return {"country": None, "region": None, "city": None}
    url = get_settings().ip_geo_provider_url.format(ip=ip)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "fail":
                return {"country": None, "region": None, "city": None}
            return {
                "country": data.get("country") or None,
                "region": data.get("regionName") or data.get("region") or None,
                "city": data.get("city") or None,
            }
    except Exception as e:
        logger.warning("geo_from_ip failed for %s: %s", ip, e)
        return {"country": None, "region": None, "city": None}


def capture_event_sync(
    *,
    request_id: str,
    client_ip: str,
    country: str | None,
    region: str | None,
    city: str | None,
    user_agent: str | None,
    endpoint: str,
    raw_input: str,
    output_json: list[dict[str, Any]] | None,
    status: str,
    latency_ms: float,
) -> None:
    """Write one tracking event to Supabase (sync, call from sync context or thread)."""
    s = get_settings()
    if not s.tracking_enabled or not s.supabase_url or not s.supabase_service_role_key:
        return
    try:
        sb = _supabase_client()
        if not sb:
            return
        row = {
            "request_id": request_id,
            "client_ip": client_ip,
            "ip_hash": _ip_hash(client_ip),
            "country": country,
            "region": region,
            "city": city,
            "user_agent": user_agent or "",
            "endpoint": endpoint,
            "raw_input": raw_input,
            "output_json": output_json,
            "status": status,
            "latency_ms": round(latency_ms, 2),
        }
        sb.table(TABLE_EVENTS).insert(row).execute()
    except Exception as e:
        logger.warning("tracking capture_event failed: %s", e)


async def capture_event(
    *,
    client_ip: str,
    user_agent: str | None,
    endpoint: str,
    raw_input: str,
    output_json: list[dict[str, Any]] | None,
    status: str,
    latency_ms: float,
) -> None:
    """Capture one usage event: resolve geo from IP then insert into Supabase."""
    s = get_settings()
    if not s.tracking_enabled:
        return
    request_id = str(uuid.uuid4())
    geo = await geo_from_ip(client_ip)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: capture_event_sync(
            request_id=request_id,
            client_ip=client_ip,
            country=geo.get("country"),
            region=geo.get("region"),
            city=geo.get("city"),
            user_agent=user_agent,
            endpoint=endpoint,
            raw_input=raw_input,
            output_json=output_json,
            status=status,
            latency_ms=latency_ms,
        ),
    )


def purge_old_events() -> int:
    """Delete events older than tracking_retention_days. Returns count deleted."""
    s = get_settings()
    if not s.tracking_enabled or not s.supabase_url or not s.supabase_service_role_key:
        return 0
    try:
        sb = _supabase_client()
        if not sb:
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=s.tracking_retention_days)).isoformat()
        # Supabase/PostgREST: delete with filter
        r = sb.table(TABLE_EVENTS).delete().lt("created_at", cutoff).execute()
        return len(r.data) if r.data is not None else 0
    except Exception as e:
        logger.warning("purge_old_events failed: %s", e)
        return 0
