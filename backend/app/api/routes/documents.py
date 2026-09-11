"""
Mandatory REST endpoints (spec section 5):
POST /api/v1/documents/process
GET  /api/v1/documents/{document_name}
GET  /api/v1/documents
(/api/v1/health lives in main.py)
"""
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.repositories import document_repository
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)

DocumentType = Literal["invoice", "balance_sheet", "profit_and_loss", "cash_flow_statement"]


@router.post("/process")
async def process_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    result = document_service.process_document(db, file, document_type, content)
    return result


@router.get("/{document_name}")
def get_document(document_name: str, db: Session = Depends(get_db)):
    record = document_repository.get_latest_by_name(db, document_name)
    return record.result_json


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    records = document_repository.list_all(db)
    return [
        {
            "document_name": r.document_name,
            "document_type": r.document_type,
            "processing_status": r.processing_status,
            "processed_at": r.created_at.isoformat(),
        }
        for r in records
    ]
