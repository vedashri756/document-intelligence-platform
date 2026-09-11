from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.exceptions import DatabaseError
from app.extraction.schemas import DocumentType
from app.logging_config import get_logger
from app.pipeline import process_document

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)


@router.post("/process")
async def process_document_endpoint(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Uploads and synchronously processes a document.
    document_type is supplied by the caller (frontend) as request metadata -
    automated document-type classification is explicitly out of scope per
    the case study.
    """
    content = await file.read()
    record = process_document(db, file.filename, document_type.value, content)
    return _serialize(record)


@router.get("/{document_name}")
def get_document(document_name: str, db: Session = Depends(get_db)):
    """Returns the latest processed result for a document name."""
    record = crud.get_by_name(db, document_name)
    return _serialize(record)


@router.get("")
def list_documents(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """Returns all processed documents - backs the dashboard list view."""
    records = crud.list_documents(db, limit=limit, offset=offset)
    return [
        {
            "document_name": r.document_name,
            "document_type": r.document_type,
            "status": r.status,
            "processed_at": r.processed_at.isoformat(),
        }
        for r in records
    ]


def _serialize(record) -> dict:
    return {
        "document_name": record.document_name,
        "document_type": record.document_type,
        "status": record.status,
        "file_validation": record.file_validation,
        "extracted_data": record.extracted_data,
        "validations": record.validations,
        "processing_metadata": record.processing_metadata,
        "error": record.error,
        "processed_at": record.processed_at.isoformat(),
    }
