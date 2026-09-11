"""
Input-control layer (spec section 4.1) — NOT document-type classification.

Checks, before any OCR/AI spend: supported type, readable, not empty/corrupt,
within the page limit. Raises a specific AppError subclass on failure so the
global handler in main.py turns it into the spec's error JSON automatically.
"""
import io

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import get_settings
from app.core.exceptions import (
    EmptyOrCorruptedFileError,
    PageLimitExceededError,
    UnsupportedFileTypeError,
)
from app.core.logging import get_logger
from app.schemas.document import FileValidation

logger = get_logger(__name__)
settings = get_settings()


def validate_upload(file: UploadFile, content: bytes) -> FileValidation:
    if not content:
        raise EmptyOrCorruptedFileError("The uploaded file is empty.")

    mime_type = file.content_type
    if mime_type not in settings.allowed_mime_types:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{mime_type}'. Only PDF / JPG / PNG are supported."
        )

    page_count = _get_page_count(mime_type, content)

    if page_count > settings.max_pages:
        raise PageLimitExceededError(
            f"Document has {page_count} pages; maximum allowed is {settings.max_pages}."
        )

    logger.info(
        "File validation PASS for '%s' (type=%s, pages=%s)", file.filename, mime_type, page_count
    )
    return FileValidation(
        file_type=mime_type,
        is_supported=True,
        is_readable=True,
        page_count=page_count,
        status="PASS",
    )


def _get_page_count(mime_type: str, content: bytes) -> int:
    try:
        if mime_type == "application/pdf":
            reader = PdfReader(io.BytesIO(content))
            if len(reader.pages) == 0:
                raise EmptyOrCorruptedFileError("PDF has no readable pages.")
            return len(reader.pages)
        else:  # jpg / png
            Image.open(io.BytesIO(content)).verify()
            return 1
    except (PdfReadError, UnidentifiedImageError) as exc:
        logger.warning("File failed integrity check: %s", exc)
        raise EmptyOrCorruptedFileError("The file is corrupted or unreadable.") from exc
