"""
File Validation layer (spec section 4.1).

This is purely an input-control gate: is the upload a readable PDF/JPG/PNG,
non-empty, non-corrupted, and within the page limit? It does NOT try to
classify or understand the document's contents — that happens later in
OCR/extraction. Keeping this separate means a bad upload fails fast and
cheaply, before any OCR or LLM cost is spent.
"""
import os
from dataclasses import dataclass

from pypdf import PdfReader
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.exceptions import FileValidationError, UnsupportedFileTypeError
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class FileValidationResult:
    filename: str
    extension: str
    page_count: int
    size_bytes: int
    is_valid: bool = True
    reason: str | None = None


def _get_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def validate_upload(filename: str, content: bytes) -> FileValidationResult:
    """
    Validates an uploaded file's bytes before any downstream processing.
    Raises FileValidationError / UnsupportedFileTypeError on failure so the
    API layer can turn it into a clean 4xx response.
    """
    logger.info(f"Validating upload: {filename} ({len(content)} bytes)")

    if not content:
        raise FileValidationError("Uploaded file is empty.", {"filename": filename})

    ext = _get_extension(filename)
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext}'. Allowed: PDF, JPG, PNG.",
            {"filename": filename, "extension": ext},
        )

    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise FileValidationError(
            f"File exceeds max size of {settings.MAX_FILE_SIZE_MB}MB.",
            {"filename": filename, "size_mb": round(size_mb, 2)},
        )

    if ext == ".pdf":
        page_count = _validate_pdf(filename, content)
    else:
        page_count = _validate_image(filename, content)

    if page_count > settings.MAX_PAGES:
        raise FileValidationError(
            f"Document has {page_count} pages; max allowed is {settings.MAX_PAGES}.",
            {"filename": filename, "page_count": page_count},
        )

    logger.info(f"Validation passed: {filename}, pages={page_count}")
    return FileValidationResult(
        filename=filename,
        extension=ext,
        page_count=page_count,
        size_bytes=len(content),
    )


def _validate_pdf(filename: str, content: bytes) -> int:
    import io

    try:
        reader = PdfReader(io.BytesIO(content))
        if len(reader.pages) == 0:
            raise FileValidationError(
                "PDF is corrupted or has no pages.", {"filename": filename}
            )
        return len(reader.pages)
    except FileValidationError:
        raise
    except Exception as exc:
        logger.warning(f"Corrupted PDF rejected: {filename} ({exc})")
        raise FileValidationError(
            "PDF file is corrupted or unreadable.",
            {"filename": filename, "error": str(exc)},
        )


def _validate_image(filename: str, content: bytes) -> int:
    import io

    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        return 1  # single-page image
    except UnidentifiedImageError as exc:
        raise FileValidationError(
            "Image file is corrupted or unreadable.",
            {"filename": filename, "error": str(exc)},
        )
    except Exception as exc:
        raise FileValidationError(
            "Image file is corrupted or unreadable.",
            {"filename": filename, "error": str(exc)},
        )
