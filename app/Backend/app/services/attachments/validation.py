import hashlib
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, status

from app.core.config import settings

ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "application/pdf",
    "text/plain",
}

# Magic signatures
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
PDF_MAGIC = b"%PDF"


def sanitize_filename(filename: str | None) -> str:
    """Safely normalize and sanitize uploaded filename, preventing path traversal."""
    if not filename:
        return "unnamed_attachment"
    # Extract just file name, stripping paths
    name = Path(filename).name
    # Replace any potentially dangerous path characters
    name = name.replace("..", "_").replace("/", "_").replace("\\", "_").strip()
    return name if name else "unnamed_attachment"


def calculate_sha256(data: bytes | BinaryIO) -> str:
    """Calculate SHA-256 hex digest for data."""
    hasher = hashlib.sha256()
    if isinstance(data, (bytes, bytearray)):
        hasher.update(data)
    else:
        current_pos = data.tell() if hasattr(data, "tell") else 0
        while chunk := data.read(65536):
            hasher.update(chunk)
        if hasattr(data, "seek"):
            data.seek(current_pos)
    return hasher.hexdigest()


def validate_file_content(
    content: bytes,
    original_filename: str,
    declared_content_type: str | None,
) -> tuple[str, str]:
    """Validate file content, size, declared MIME, and magic bytes.

    Returns (sanitized_filename, validated_content_type).
    Raises HTTPException(400) on validation failures.
    """
    sanitized_name = sanitize_filename(original_filename)

    # 1. Size check (empty & max limit)
    size = len(content)
    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File cannot be empty.",
        )

    if size > settings.MAX_ATTACHMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "File exceeds maximum allowed size of "
                f"{settings.MAX_ATTACHMENT_SIZE_BYTES} bytes."
            ),
        )

    # 2. Content type check
    content_type = (declared_content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_MIME_TYPES:
        allowed_str = ", ".join(sorted(ALLOWED_MIME_TYPES))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: {content_type}. "
                f"Allowed types: {allowed_str}"
            ),
        )

    # 3. Magic byte signature verification
    if content_type == "image/png":
        if not content.startswith(PNG_MAGIC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PNG file signature.",
            )
    elif content_type == "image/jpeg":
        if not content.startswith(JPEG_MAGIC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JPEG file signature.",
            )
    elif content_type == "image/webp":
        if not (
            content.startswith(b"RIFF")
            and len(content) >= 12
            and content[8:12] == b"WEBP"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid WEBP file signature.",
            )
    elif content_type == "application/pdf":
        if not content.startswith(PDF_MAGIC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file signature.",
            )
    elif content_type == "text/plain":
        # Check that it's readable text without NUL bytes (executable binary)
        if b"\x00" in content[:1024]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Binary content detected in text file.",
            )

    return sanitized_name, content_type
