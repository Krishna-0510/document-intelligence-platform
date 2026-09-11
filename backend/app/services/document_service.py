"""
Orchestrates the full pipeline (spec section 1 flow diagram):
validate -> OCR -> extract -> financial validation -> persist -> respond.

Each stage is logged and failures raise a specific AppError, which the
global handler in main.py converts to the spec's error JSON shape.
"""
import time
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories import document_repository
from app.services import (
    document_validation_service,
    extraction_service,
    financial_validation_service,
    ocr_service,
)

logger = get_logger(__name__)


def process_document(db: Session, file: UploadFile, document_type: str, content: bytes) -> dict:
    start = time.time()
    logger.info("Processing '%s' as document_type=%s", file.filename, document_type)

    # 1. Validate
    file_validation = document_validation_service.validate_upload(file, content)

    # 2. OCR / text extraction
    raw_text, ocr_used = ocr_service.extract_text(file.content_type, content)

    # 3. AI field & table extraction
    extracted_data = extraction_service.extract_fields(document_type, raw_text)

    # 4. Financial validation
    validation_result = financial_validation_service.run_validation(document_type, extracted_data)

    processing_status = "PASS" if validation_result["overall_status"] != "FAIL" else "FAILED"

    response = {
        "document_name": file.filename,
        "document_type": document_type,
        "processing_status": processing_status,
        "file_validation": file_validation.model_dump(),
        "extracted_data": extracted_data,
        "validation": validation_result,
        "processing_metadata": {
            "ocr_used": ocr_used,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": int((time.time() - start) * 1000),
        },
    }

    # 5. Persist (so it shows up in the dashboard + GET-by-name)
    document_repository.save_result(
        db, document_name=file.filename, document_type=document_type,
        processing_status=processing_status, result_json=response,
    )

    logger.info("Finished processing '%s' -> status=%s", file.filename, processing_status)
    return response
