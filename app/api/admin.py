"""
Admin panel API: login with shared password, list events, metrics.
All admin routes require valid session token from POST /admin/login.
"""
import base64
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

import httpx
from app.config import get_settings
from app.services.tracking import TABLE_EVENTS, _supabase_headers, _supabase_url, purge_old_events


router = APIRouter(prefix="/admin", tags=["admin"])

TOKEN_TTL_SECONDS = 86400  # 24 hours


def _make_token(password: str) -> str:
    expiry = int((datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)).timestamp())
    payload = f"{expiry}:admin"
    sig = hmac.new(password.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    raw = f"{expiry}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _verify_token(token: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token + "==")
        s = raw.decode()
        expiry_str, sig = s.split(":", 1)
        expiry = int(expiry_str)
        if datetime.now(timezone.utc).timestamp() > expiry:
            return False
        password = get_settings().admin_panel_password
        payload = f"{expiry}:admin"
        expected = hmac.new(password.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


def _admin_auth(authorization: str | None = None) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization")
    token = authorization[7:].strip()
    if not token or not _verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int


@router.post("/login", response_model=LoginResponse)
async def admin_login(body: LoginRequest) -> LoginResponse:
    """Validate admin email (allowlist) and password; return session token. Only the configured email may sign in."""
    settings = get_settings()
    if not settings.admin_allowed_email or not settings.admin_panel_password:
        raise HTTPException(status_code=503, detail="Admin not configured")
    email_ok = body.email.strip().lower() == settings.admin_allowed_email.strip().lower()
    password_ok = hmac.compare_digest(body.password, settings.admin_panel_password)
    if not email_ok or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = _make_token(settings.admin_panel_password)
    return LoginResponse(token=token, expires_in=TOKEN_TTL_SECONDS)


@router.get("/events")
async def admin_events(
    request: Request,
    date_from: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    country: str | None = Query(None),
    endpoint: str | None = Query(None),
    status: str | None = Query(None),
    query_text: str | None = Query(None, alias="q"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List tracking events with filters. Requires admin token."""
    _admin_auth(request.headers.get("authorization"))

    headers = _supabase_headers()
    url = _supabase_url(TABLE_EVENTS)
    if not headers or not url:
        raise HTTPException(status_code=503, detail="Tracking not configured")

    # Build PostgREST query: ?select=* &created_at=gte.ISO &country=eq.XXX ...
    fetch_params: dict[str, str] = {"select": "*"}
    if date_from:
        fetch_params["created_at"] = f"gte.{date_from}T00:00:00Z"
    if date_to:
        fetch_params["created_at"] = f"lte.{date_to}T23:59:59.999Z"
    if country:
        fetch_params["country"] = f"eq.{country}"
    if endpoint:
        fetch_params["endpoint"] = f"eq.{endpoint}"
    if status:
        fetch_params["status"] = f"eq.{status}"
    if query_text:
        fetch_params["raw_input"] = f"ilike.*{query_text}*"
    
    # Sort
    fetch_params["order"] = "created_at.desc"
    
    # Range header for pagination: 0-99
    range_header = f"{offset}-{offset + limit - 1}"
    headers["Range"] = range_header
    headers["Prefer"] = "count=exact"

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=fetch_params, headers=headers)
        r.raise_for_status()
        data = r.json()
        
        # Get count from Content-Range header: "0-99/1234"
        content_range = r.headers.get("Content-Range", "")
        total_count = 0
        if "/" in content_range:
            try:
                total_count = int(content_range.split("/")[-1])
            except ValueError:
                total_count = len(data)
        else:
            total_count = len(data)

    return {
        "data": data,
        "count": total_count,
    }


@router.get("/metrics")
async def admin_metrics(
    request: Request,
    days: int = Query(7, ge=1, le=90),
) -> dict[str, Any]:
    """Aggregate metrics for dashboard. Requires admin token."""
    _admin_auth(request.headers.get("authorization"))

    headers = _supabase_headers()
    url = _supabase_url(TABLE_EVENTS)
    if not headers or not url:
        raise HTTPException(status_code=503, detail="Tracking not configured")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    # PostgREST: filter and select columns
    metric_params = {
        "select": "id,client_ip,country,status,latency_ms,created_at",
        "created_at": f"gte.{cutoff}"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=metric_params, headers=headers)
        r.raise_for_status()
        rows = r.json() or []

    total = len(rows)
    errors = sum(1 for x in rows if x.get("status") == "error")
    unique_ips = len({x.get("client_ip") or "" for x in rows})
    countries: dict[str, int] = {}
    for x in rows:
        c = x.get("country") or "unknown"
        countries[c] = countries.get(c, 0) + 1
    latencies = [x.get("latency_ms") for x in rows if isinstance(x.get("latency_ms"), (int, float))]
    avg_latency_ms = round(sum(latencies) / len(latencies), 2) if latencies else None

    return {
        "days": days,
        "total_requests": total,
        "unique_ips": unique_ips,
        "error_count": errors,
        "error_rate": round(errors / total, 4) if total else 0,
        "avg_latency_ms": avg_latency_ms,
        "by_country": dict(sorted(countries.items(), key=lambda t: -t[1])[:20]),
    }


@router.post("/purge")
async def admin_purge(request: Request) -> dict[str, Any]:
    """Run retention purge (delete events older than configured days). Requires admin token."""
    _admin_auth(request.headers.get("authorization"))
    deleted = purge_old_events()
    return {"deleted": deleted}
