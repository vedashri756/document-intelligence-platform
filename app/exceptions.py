"""
Custom exception hierarchy.

Every exception the application raises deliberately is a subclass of
DocIntelError, so the FastAPI exception handler (see app/main.py) can
catch them centrally and return a clean, consistent JSON error response
instead of leaking stack traces to the client.
"""


class DocIntelError(Exception):
    """Base class for all application-raised errors."""
    status_code = 500
    error_code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class FileValidationError(DocIntelError):
    """Raised when an uploaded file fails validation (bad type, too many
    pages, corrupted, empty, etc.)."""
    status_code = 422
    error_code = "FILE_VALIDATION_FAILED"


class UnsupportedFileTypeError(FileValidationError):
    status_code = 415
    error_code = "UNSUPPORTED_FILE_TYPE"


class OCRError(DocIntelError):
    """Raised when text/OCR extraction from a valid file fails."""
    status_code = 502
    error_code = "OCR_FAILED"


class ExtractionError(DocIntelError):
    """Raised when the LLM extraction step fails or returns invalid data."""
    status_code = 502
    error_code = "EXTRACTION_FAILED"


class DocumentNotFoundError(DocIntelError):
    status_code = 404
    error_code = "DOCUMENT_NOT_FOUND"


class DatabaseError(DocIntelError):
    status_code = 500
    error_code = "DATABASE_ERROR"
