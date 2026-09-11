"""SQLAlchemy ORM model for a processed document result."""
import datetime as dt

from sqlalchemy import JSON, Column, DateTime, Integer, String

from app.core.database import Base


class ProcessedDocument(Base):
    __tablename__ = "processed_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, index=True, nullable=False)
    document_type = Column(String, nullable=False)
    processing_status = Column(String, nullable=False)  # PASS | FAILED

    # Full structured response (file_validation, extracted_data, validation,
    # processing_metadata) stored as JSON so the exact API shape round-trips
    # without a rigid column-per-field schema.
    result_json = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)
