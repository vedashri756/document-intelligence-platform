"""
Structured-output schemas for the Extraction layer.

Design choice: rather than a fixed, hardcoded list of fields per document
type (which would fail the "extract ALL meaningful information" requirement
the moment a document has an unexpected line item), fields are a flexible
LIST of {name, value, page, source_text} objects. This keeps the JSON
machine-readable and schema-valid (Gemini structured output needs fixed
object shapes, not arbitrary dynamic dict keys) while still letting the
model return as many or as few fields as the document actually contains.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    BALANCE_SHEET = "BALANCE_SHEET"
    PROFIT_AND_LOSS = "PROFIT_AND_LOSS"
    CASH_FLOW = "CASH_FLOW"
    INVOICE = "INVOICE"


class ExtractedField(BaseModel):
    name: str = Field(description="Field label, e.g. 'total_assets', 'invoice_number'")
    value: Optional[str] = Field(default=None, description="Extracted value as text, or null if not present")
    page: Optional[int] = Field(default=None, description="1-indexed page number the value came from")
    source_text: Optional[str] = Field(default=None, description="Short verbatim snippet supporting this value")


class ExtractedTable(BaseModel):
    table_name: str
    page: Optional[int] = None
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Optional[str]]] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    document_type: DocumentType
    fields: List[ExtractedField] = Field(default_factory=list)
    tables: List[ExtractedTable] = Field(default_factory=list)
