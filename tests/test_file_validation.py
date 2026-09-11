import io

import pytest
from PIL import Image
from pypdf import PdfWriter

from app.exceptions import FileValidationError, UnsupportedFileTypeError
from app.validation.file_validation import validate_upload


def _make_blank_pdf(num_pages=1) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_png() -> bytes:
    img = Image.new("RGB", (50, 50), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_empty_file_rejected():
    with pytest.raises(FileValidationError):
        validate_upload("empty.pdf", b"")


def test_unsupported_extension_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload("doc.txt", b"hello world")


def test_valid_pdf_passes():
    result = validate_upload("doc.pdf", _make_blank_pdf(1))
    assert result.is_valid
    assert result.page_count == 1


def test_pdf_exceeding_page_limit_rejected():
    with pytest.raises(FileValidationError):
        validate_upload("doc.pdf", _make_blank_pdf(4))


def test_corrupted_pdf_rejected():
    with pytest.raises(FileValidationError):
        validate_upload("doc.pdf", b"%PDF-1.4 not a real pdf body")


def test_valid_png_passes():
    result = validate_upload("receipt.png", _make_png())
    assert result.is_valid
    assert result.page_count == 1


def test_corrupted_image_rejected():
    with pytest.raises(FileValidationError):
        validate_upload("receipt.png", b"not-an-image-at-all")
