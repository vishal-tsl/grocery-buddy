"""Google Cloud Storage helpers using Application Default Credentials (Cloud Run service account)."""

from functools import lru_cache

from google.cloud import storage


@lru_cache
def get_client() -> storage.Client:
    return storage.Client()


def upload_bytes(
    bucket_name: str,
    object_name: str,
    data: bytes,
    content_type: str | None = None,
) -> None:
    bucket = get_client().bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(data, content_type=content_type)


def download_bytes(bucket_name: str, object_name: str) -> tuple[bytes, str | None]:
    bucket = get_client().bucket(bucket_name)
    blob = bucket.blob(object_name)
    if not blob.exists():
        raise FileNotFoundError(object_name)
    return blob.download_as_bytes(), blob.content_type
