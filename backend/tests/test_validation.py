"""Basic tests for file validation and financial validation logic."""
import io

import pytest
from fastapi import UploadFile

from app.core.exceptions import EmptyOrCorruptedFileError, UnsupportedFileTypeError
from app.services import document_validation_service, financial_validation_service


def _upload(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content), headers={"content-type": content_type})


def test_rejects_unsupported_file_type():
    file = _upload("data.txt", "text/plain", b"hello")
    with pytest.raises(UnsupportedFileTypeError):
        document_validation_service.validate_upload(file, b"hello")


def test_rejects_empty_file():
    file = _upload("empty.pdf", "application/pdf", b"")
    with pytest.raises(EmptyOrCorruptedFileError):
        document_validation_service.validate_upload(file, b"")


def test_invoice_total_check_passes_within_tolerance():
    extracted = {
        "subtotal": {"value": 12500.00},
        "tax_amount": {"value": 625.00},
        "discount": {"value": 0.00},
        "total_amount": {"value": 13125.00},
        "line_items": [],
    }
    result = financial_validation_service.run_validation("invoice", extracted)
    assert result["overall_status"] == "PASS"


def test_invoice_total_check_fails_on_mismatch():
    extracted = {
        "subtotal": {"value": 12500.00},
        "tax_amount": {"value": 625.00},
        "discount": {"value": 0.00},
        "total_amount": {"value": 99999.00},
        "line_items": [],
    }
    result = financial_validation_service.run_validation("invoice", extracted)
    assert result["overall_status"] == "FAIL"


def test_balance_sheet_not_applicable_when_fields_missing():
    result = financial_validation_service.run_validation("balance_sheet", {})
    assert result["overall_status"] == "NOT_APPLICABLE"
