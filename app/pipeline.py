"""
Orchestrates the full processing pipeline for a single uploaded document.
Each stage is implemented in its own module (validation / ocr / extraction /
financial_validation / db) - this file just wires them together in order
and is the only place that knows the overall sequence.
"""
import time

from sqlalchemy.orm import Session

from app.db import crud
from app.extraction.llm_extractor import extract_structured_data
from app.financial_validation.validators import run_financial_validation
from app.logging_config import get_logger
from app.ocr.ocr_service import extract_text
from app.validation.file_validation import validate_upload

logger = get_logger(__name__)


def process_document(db: Session, document_name: str, document_type: str, content: bytes):
    start = time.time()

    # Stage 1: file validation (raises FileValidationError on failure - caller/API
    # layer is responsible for catching and turning into a 4xx response; nothing
    # is saved to the DB for a failed validation, since no document was processed)
    validation_result = validate_upload(document_name, content)

    # Stage 2: OCR / text extraction
    pages = extract_text(document_name, content, validation_result.extension)
    ocr_source = "native_pdf_text" if all(p.source == "native_pdf_text" for p in pages) else \
                 "ocr" if all(p.source == "ocr" for p in pages) else "mixed"

    # Stage 3: LLM structured extraction
    extraction = extract_structured_data(document_type, pages)

    # Stage 4: financial validation (deterministic, rule-based)
    validations = run_financial_validation(document_type, extraction.fields)

    elapsed_ms = int((time.time() - start) * 1000)

    # Stage 5: persist
    record = crud.upsert_document(
        db,
        document_name=document_name,
        document_type=document_type,
        status="SUCCESS",
        file_validation={
            "filename": validation_result.filename,
            "extension": validation_result.extension,
            "page_count": validation_result.page_count,
            "size_bytes": validation_result.size_bytes,
        },
        extracted_data={
            "fields": [f.model_dump() for f in extraction.fields],
            "tables": [t.model_dump() for t in extraction.tables],
        },
        validations=[v.__dict__ for v in validations],
        processing_metadata={
            "ocr_source": ocr_source,
            "model_used": "gemini",
            "processing_time_ms": elapsed_ms,
        },
        error=None,
    )
    logger.info(f"Processed '{document_name}' in {elapsed_ms}ms, status=SUCCESS")
    return record
