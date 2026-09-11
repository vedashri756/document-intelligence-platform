"""
OCR / Parsing layer (spec section 3 & 9).

Responsible ONLY for turning a validated PDF/JPG/PNG into plain text,
per page, with nothing else attached. It does not try to understand or
structure the content — that is the Extraction layer's job. Keeping OCR
and Extraction as separate stages is what lets each extracted field later
carry a page number + source text snippet for the grounding requirement.

Strategy:
  1. If it's a PDF with a real text layer (native/digital PDF), extract
     text directly via pypdf - fast, free, perfectly accurate.
  2. If the PDF has no text layer (a scan, like the financial statements
     in this assignment's dataset) or it's a JPG/PNG, rasterize each page
     to an image and run Tesseract OCR on it.
"""
import io
from dataclasses import dataclass

from pdf2image import convert_from_bytes
from PIL import Image
from pypdf import PdfReader
import pytesseract

from app.config import settings
from app.exceptions import OCRError
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PageText:
    page_number: int
    text: str
    source: str  # "native_pdf_text" or "ocr"


def extract_text(filename: str, content: bytes, extension: str) -> list[PageText]:
    """Returns a list of PageText, one per page (images are always 1 page)."""
    try:
        if extension == ".pdf":
            return _extract_from_pdf(content)
        else:
            return _extract_from_image(content)
    except OCRError:
        raise
    except Exception as exc:
        logger.error(f"OCR failed for {filename}: {exc}")
        raise OCRError(
            "Failed to extract text from document.",
            {"filename": filename, "error": str(exc)},
        )


def _extract_from_pdf(content: bytes) -> list[PageText]:
    reader = PdfReader(io.BytesIO(content))
    native_pages = []
    has_text = False

    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if len(text) > 20:  # meaningful text present
            has_text = True
        native_pages.append(PageText(page_number=i, text=text, source="native_pdf_text"))

    if has_text:
        logger.info("PDF has a native text layer - using direct extraction.")
        return native_pages

    logger.info("PDF has no usable text layer - falling back to OCR rasterization.")
    return _ocr_pdf_pages(content)


def _ocr_pdf_pages(content: bytes) -> list[PageText]:
    try:
        images = convert_from_bytes(content, dpi=settings.OCR_DPI)
    except Exception as exc:
        raise OCRError("Could not rasterize PDF pages for OCR.", {"error": str(exc)})

    pages = []
    for i, image in enumerate(images, start=1):
        text = pytesseract.image_to_string(image)
        pages.append(PageText(page_number=i, text=text.strip(), source="ocr"))
    return pages


def _extract_from_image(content: bytes) -> list[PageText]:
    try:
        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image)
    except Exception as exc:
        raise OCRError("Could not OCR image.", {"error": str(exc)})
    return [PageText(page_number=1, text=text.strip(), source="ocr")]
