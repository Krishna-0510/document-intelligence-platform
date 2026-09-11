"""
Pydantic schemas matching the case study's mandatory JSON shapes
(sections 4.1, 4.3, 5.2, 5.3).
"""
from typing import Any, Literal

from pydantic import BaseModel


class FileValidation(BaseModel):
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: int
    status: Literal["PASS", "FAILED"]


class ExtractedField(BaseModel):
    value: Any = None
    confidence: float | None = None  # OPTIONAL per spec
    page_number: int | None = None
    source_text: str | None = None


class ValidationCheck(BaseModel):
    name: str
    formula: str
    operands: dict[str, Any]
    calculated_value: float | None = None
    reported_value: float | None = None
    variance: float | None = None
    status: Literal["PASS", "FAIL", "NOT_APPLICABLE"]


class ValidationResult(BaseModel):
    checks: list[ValidationCheck]
    overall_status: Literal["PASS", "FAIL", "NOT_APPLICABLE"]
    issues: list[str] = []


class ProcessingMetadata(BaseModel):
    ocr_used: bool
    processed_at: str
    processing_time_ms: int


class DocumentProcessResponse(BaseModel):
    document_name: str
    document_type: str
    processing_status: Literal["PASS", "FAILED"]
    overall_confidence: float | None = None  # OPTIONAL
    file_validation: FileValidation
    extracted_data: dict[str, Any]
    validation: ValidationResult
    processing_metadata: ProcessingMetadata


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
