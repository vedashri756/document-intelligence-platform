"""
Response models for the public API (spec section 5.2 - mandatory
structured response). Kept separate from app/extraction/schemas.py:
those are the LLM's internal output shape, these are the contract the
client actually sees, including validation results and metadata.
"""
import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.extraction.schemas import ExtractedField, ExtractedTable, DocumentType
from app.financial_validation.validators import ValidationCheck


class FileValidationInfo(BaseModel):
    filename: str
    extension: str
    page_count: int
    size_bytes: int


class ProcessingMetadata(BaseModel):
    ocr_source: str  # "native_pdf_text" or "ocr" or "mixed"
    model_used: str
    processing_time_ms: int


class DocumentProcessResponse(BaseModel):
    document_name: str
    document_type: DocumentType
    status: str  # SUCCESS | FAILED
    file_validation: FileValidationInfo
    extracted_fields: List[ExtractedField]
    extracted_tables: List[ExtractedTable]
    validations: List[ValidationCheck]
    processing_metadata: ProcessingMetadata
    processed_at: datetime.datetime


class DocumentListItem(BaseModel):
    document_name: str
    document_type: str
    status: str
    processed_at: datetime.datetime


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict] = None
