"""
User feedback endpoint: batch and per-item thumbs up/down + comment.
Stores in Supabase feedback table when configured; no-op otherwise.
"""
import hashlib
import logging
from typing import Literal

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger(__name__)
TABLE_FEEDBACK = "feedback"


def _client_ip(req: Request) -> str:
    forwarded = req.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if req.client:
        return req.client.host or ""
    return ""


def _ip_hash(ip: str) -> str:
    if not ip:
        return ""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _supabase_headers() -> dict[str, str] | None:
    s = get_settings()
    if not s.supabase_url or not s.supabase_service_role_key:
        return None
    return {
        "apikey": s.supabase_service_role_key,
        "Authorization": f"Bearer {s.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _supabase_url(table: str) -> str | None:
    s = get_settings()
    if not s.supabase_url:
        return None
    return f"{s.supabase_url.rstrip('/')}/rest/v1/{table}"


class FeedbackRequest(BaseModel):
    """Request body for POST /feedback."""

    type: Literal["batch", "item"]
    positive: bool = Field(..., description="thumbs up = true, thumbs down = false")
    comment: str | None = None

    # For type="batch"
    raw_input: str | None = None
    item_count: int | None = None

    # For type="item"
    item_id: str | None = None
    product_name: str | None = None
    sku: str | None = None
    match_source: str | None = None


router = APIRouter()


@router.post("/feedback")
async def submit_feedback(request: Request, body: FeedbackRequest) -> dict:
    """
    Submit user feedback (batch or per-item).
    Public, no auth. Persists to Supabase when configured; returns 200 either way.
    """
    client_ip = _client_ip(request)

    headers = _supabase_headers()
    url = _supabase_url(TABLE_FEEDBACK)
    if headers and url:
        try:
            row = {
                "type": body.type,
                "positive": body.positive,
                "comment": body.comment or None,
                "raw_input": body.raw_input,
                "item_count": body.item_count,
                "item_id": body.item_id,
                "product_name": body.product_name,
                "sku": body.sku,
                "match_source": body.match_source,
                "client_ip": client_ip or None,
                "ip_hash": _ip_hash(client_ip) or None,
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(url, json=row, headers=headers)
                r.raise_for_status()
        except Exception as e:
            logger.warning("feedback insert failed: %s", e)

    return {"ok": True}
