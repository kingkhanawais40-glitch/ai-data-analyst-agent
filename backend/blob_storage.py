
import os
from pathlib import Path

from dotenv import load_dotenv
from vercel.blob.sync import (
    delete_blob,
    get_blob,
    put_blob,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _ensure_blob_token() -> None:
    """Ensure private Blob operations have configured credentials."""
    if not os.getenv("BLOB_READ_WRITE_TOKEN"):
        raise RuntimeError(
            "BLOB_READ_WRITE_TOKEN is not configured."
        )


# ============================================================
# UPLOAD
# ============================================================

def upload_blob_bytes(
    pathname: str,
    content: bytes,
    content_type: str,
) -> str:
    """Upload bytes to private Vercel Blob and return its pathname."""
    _ensure_blob_token()

    if not pathname or not pathname.strip():
        raise ValueError("Blob pathname cannot be empty.")

    if not isinstance(content, bytes):
        raise TypeError("Blob content must be bytes.")

    if not content_type or not content_type.strip():
        raise ValueError("Content type cannot be empty.")

    result = put_blob(
        pathname,
        content,
        access="private",
        content_length=len(content),
        content_type=content_type,
        add_random_suffix=True,
        allow_overwrite=False,
    )

    return result.pathname


# ============================================================
# DOWNLOAD
# ============================================================

def download_blob_bytes(pathname: str) -> bytes:
    """Retrieve bytes from a private Vercel Blob."""
    _ensure_blob_token()

    if not pathname or not pathname.strip():
        raise ValueError("Blob pathname cannot be empty.")

    result = get_blob(
        pathname,
        access="private",
    )

    return result.body


# ============================================================
# DELETE
# ============================================================

def delete_blob_object(pathname: str) -> None:
    """Delete a private Blob object by pathname."""
    _ensure_blob_token()

    if not pathname or not pathname.strip():
        raise ValueError("Blob pathname cannot be empty.")

    delete_blob(pathname)
