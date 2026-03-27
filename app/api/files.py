import asyncio
import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.config import get_settings
from app.services import gcs_storage

router = APIRouter()
logger = logging.getLogger(__name__)

# Cloud Run request body limit is separate; this caps memory use per upload.
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def _require_gcs_bucket() -> str:
    settings = get_settings()
    name = (settings.gcs_bucket or "").strip()
    if not name:
        raise HTTPException(
            status_code=503,
            detail="File storage is not configured (set GCS_BUCKET).",
        )
    return name


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict[str, str]:
    bucket_name = _require_gcs_bucket()
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    file_id = str(uuid.uuid4())
    object_name = f"uploads/{file_id}"
    content_type = file.content_type
    try:
        await asyncio.to_thread(
            gcs_storage.upload_bytes,
            bucket_name,
            object_name,
            data,
            content_type,
        )
    except Exception:
        logger.exception("GCS upload failed for %s", object_name)
        raise HTTPException(status_code=502, detail="Upload failed") from None
    return {
        "id": file_id,
        "gcs_uri": f"gs://{bucket_name}/{object_name}",
    }


@router.get("/file/{file_id}")
async def get_file(file_id: str) -> Response:
    try:
        UUID(file_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid file id") from e
    bucket_name = _require_gcs_bucket()
    object_name = f"uploads/{file_id}"
    try:
        body, content_type = await asyncio.to_thread(
            gcs_storage.download_bytes,
            bucket_name,
            object_name,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="File not found") from e
    except Exception:
        logger.exception("GCS download failed for %s", object_name)
        raise HTTPException(status_code=502, detail="Download failed") from None
    media_type = content_type or "application/octet-stream"
    return Response(content=body, media_type=media_type)
