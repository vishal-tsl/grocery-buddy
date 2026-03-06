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

from app.config import get_settings
from app.services.tracking import TABLE_EVENTS, _supabase_client, purge_old_events


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

    sb = _supabase_client()
    if not sb:
        raise HTTPException(status_code=503, detail="Tracking not configured")

    q = sb.table(TABLE_EVENTS).select("*", count="exact")
    if date_from:
        q = q.gte("created_at", f"{date_from}T00:00:00Z")
    if date_to:
        q = q.lte("created_at", f"{date_to}T23:59:59.999Z")
    if country:
        q = q.eq("country", country)
    if endpoint:
        q = q.eq("endpoint", endpoint)
    if status:
        q = q.eq("status", status)
    if query_text:
        q = q.ilike("raw_input", f"%{query_text}%")
    q = q.order("created_at", desc=True).range(offset, offset + limit - 1)
    r = q.execute()

    return {
        "data": r.data or [],
        "count": r.count if hasattr(r, "count") and r.count is not None else len(r.data or []),
    }


@router.get("/metrics")
async def admin_metrics(
    request: Request,
    days: int = Query(7, ge=1, le=90),
) -> dict[str, Any]:
    """Aggregate metrics for dashboard. Requires admin token."""
    _admin_auth(request.headers.get("authorization"))

    sb = _supabase_client()
    if not sb:
        raise HTTPException(status_code=503, detail="Tracking not configured")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    r = sb.table(TABLE_EVENTS).select("id", "client_ip", "country", "status", "latency_ms", "created_at").gte("created_at", cutoff).execute()
    rows = r.data or []

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
