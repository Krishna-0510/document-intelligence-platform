"""
Persistence layer. Nothing above this layer should touch SQLAlchemy
directly — keeps the DB swappable and the services testable.
"""
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseError, DocumentNotFoundError
from app.core.logging import get_logger
from app.models.document import ProcessedDocument

logger = get_logger(__name__)


def save_result(db: Session, document_name: str, document_type: str,
                 processing_status: str, result_json: dict) -> ProcessedDocument:
    try:
        record = ProcessedDocument(
            document_name=document_name,
            document_type=document_type,
            processing_status=processing_status,
            result_json=result_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info("Saved processing result for '%s' (status=%s)", document_name, processing_status)
        return record
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save processing result for '%s'", document_name)
        raise DatabaseError(f"Could not save result for '{document_name}'.") from exc


def get_latest_by_name(db: Session, document_name: str) -> ProcessedDocument:
    record = (
        db.query(ProcessedDocument)
        .filter(ProcessedDocument.document_name == document_name)
        .order_by(desc(ProcessedDocument.created_at))
        .first()
    )
    if not record:
        raise DocumentNotFoundError(f"No processed document found with name '{document_name}'.")
    return record


def list_all(db: Session, limit: int = 100) -> list[ProcessedDocument]:
    return (
        db.query(ProcessedDocument)
        .order_by(desc(ProcessedDocument.created_at))
        .limit(limit)
        .all()
    )
