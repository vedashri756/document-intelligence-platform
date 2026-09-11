import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.extraction.schemas import ExtractedField, ExtractionResult, DocumentType


@pytest.fixture
def client(monkeypatch):
    # Mock the LLM extraction call so tests don't need a real Gemini API key
    # or network access - this test targets the API/pipeline wiring, not
    # Gemini's extraction quality (that's evaluated via sample_outputs/).
    def fake_extract(document_type, pages):
        return ExtractionResult(
            document_type=DocumentType(document_type),
            fields=[
                ExtractedField(name="net_worth", value="100.00", page=1, source_text="Net worth 100.00"),
                ExtractedField(name="vat_amount", value="10.00", page=1, source_text="VAT 10.00"),
                ExtractedField(name="gross_worth", value="110.00", page=1, source_text="Total 110.00"),
            ],
            tables=[],
        )

    import app.pipeline as pipeline_module
    monkeypatch.setattr(pipeline_module, "extract_structured_data", fake_extract)

    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_process_document_flow(client):
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    res = client.post(
        "/api/v1/documents/process",
        data={"document_type": "INVOICE"},
        files={"file": ("test_invoice.png", buf, "image/png")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["document_name"] == "test_invoice.png"
    assert body["status"] == "SUCCESS"
    assert any(v["status"] == "PASS" for v in body["validations"])

    # GET by name should return the same result
    res2 = client.get("/api/v1/documents/test_invoice.png")
    assert res2.status_code == 200
    assert res2.json()["document_name"] == "test_invoice.png"

    # List endpoint should include it
    res3 = client.get("/api/v1/documents")
    names = [d["document_name"] for d in res3.json()]
    assert "test_invoice.png" in names


def test_get_nonexistent_document_returns_404(client):
    res = client.get("/api/v1/documents/does_not_exist.pdf")
    assert res.status_code == 404
    assert res.json()["error_code"] == "DOCUMENT_NOT_FOUND"


def test_unsupported_file_type_returns_clean_error(client):
    res = client.post(
        "/api/v1/documents/process",
        data={"document_type": "INVOICE"},
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert res.status_code == 415
    assert res.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"
