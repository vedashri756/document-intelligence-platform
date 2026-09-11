"""
Persistence access. By design, saving a document with a name that already
exists overwrites/updates that row (spec: "GET-by-name should return the
latest result; retaining prior versions is optional" - we chose the
simpler update-in-place approach).
"""
from sqlalchemy.orm import Session

from app.db.models import ProcessedDocument
from app.exceptions import DatabaseError, DocumentNotFoundError
from app.logging_config import get_logger

logger = get_logger(__name__)


def upsert_document(db: Session, document_name: str, **fields) -> ProcessedDocument:
    try:
        existing = (
            db.query(ProcessedDocument)
            .filter(ProcessedDocument.document_name == document_name)
            .first()
        )
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated existing record for '{document_name}'")
            return existing

        record = ProcessedDocument(document_name=document_name, **fields)
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Created new record for '{document_name}'")
        return record
    except Exception as exc:
        db.rollback()
        logger.error(f"DB upsert failed for '{document_name}': {exc}")
        raise DatabaseError("Failed to save processed document.", {"error": str(exc)})


def get_by_name(db: Session, document_name: str) -> ProcessedDocument:
    record = (
        db.query(ProcessedDocument)
        .filter(ProcessedDocument.document_name == document_name)
        .first()
    )
    if record is None:
        raise DocumentNotFoundError(f"No processed document named '{document_name}'.")
    return record


def list_documents(db: Session, limit: int = 100, offset: int = 0):
    return (
        db.query(ProcessedDocument)
        .order_by(ProcessedDocument.processed_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
