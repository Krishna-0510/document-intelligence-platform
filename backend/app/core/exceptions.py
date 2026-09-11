"""
Custom exception hierarchy.

Code-quality rule (mandatory):
'Implement proper exception handling for invalid files, OCR failures,
model/API failures, timeouts, database failures and unexpected processing
errors. The application must fail gracefully without exposing stack traces
or secrets to end users.'

Every exception here maps to a stable error `code` + safe `message`, which
main.py's exception handlers turn into the spec's error JSON shape:
    {"error": {"code": "...", "message": "..."}}
"""


class AppError(Exception):
    """Base class for all controlled application errors."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str, code: str | None = None, http_status: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status


class UnsupportedFileTypeError(AppError):
    code = "UNSUPPORTED_FILE_TYPE"
    http_status = 400


class EmptyOrCorruptedFileError(AppError):
    code = "INVALID_FILE"
    http_status = 400


class PageLimitExceededError(AppError):
    code = "PAGE_LIMIT_EXCEEDED"
    http_status = 400


class OCRProcessingError(AppError):
    code = "OCR_FAILED"
    http_status = 502


class ExtractionError(AppError):
    code = "EXTRACTION_FAILED"
    http_status = 502


class DocumentNotFoundError(AppError):
    code = "DOCUMENT_NOT_FOUND"
    http_status = 404


class DatabaseError(AppError):
    code = "DATABASE_ERROR"
    http_status = 500
