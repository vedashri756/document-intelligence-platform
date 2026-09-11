"""
Extraction layer: takes OCR'd page text and turns it into structured,
schema-validated JSON via Gemini's structured-output mode (response is
constrained to the ExtractionResult JSON schema, so we don't have to
trust free-form model text).
"""
import json
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from app.config import settings
from app.exceptions import ExtractionError
from app.extraction.prompts import build_extraction_prompt
from app.extraction.schemas import ExtractionResult
from app.logging_config import get_logger
from app.ocr.ocr_service import PageText

logger = get_logger(__name__)

_client = None

_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 5


def _get_client():
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise ExtractionError("GEMINI_API_KEY is not configured on the server.")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _format_ocr_text(pages: list[PageText]) -> str:
    return "\n\n".join(f"--- PAGE {p.page_number} ---\n{p.text}" for p in pages)


# JSON schema Gemini must conform to (mirrors app.extraction.schemas.ExtractionResult)
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string"},
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string", "nullable": True},
                    "page": {"type": "integer", "nullable": True},
                    "source_text": {"type": "string", "nullable": True},
                },
                "required": ["name"],
            },
        },
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "page": {"type": "integer", "nullable": True},
                    "columns": {"type": "array", "items": {"type": "string"}},
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string", "nullable": True},
                        },
                    },
                },
                "required": ["table_name"],
            },
        },
    },
    "required": ["document_type", "fields", "tables"],
}


def _call_with_retry(client, prompt: str):
    """Calls Gemini with exponential backoff on transient errors (429 rate
    limit, 503 overloaded). Does NOT retry on other errors (e.g. bad request,
    auth failure) - those won't be fixed by waiting."""
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_RESPONSE_SCHEMA,
                    temperature=0,
                ),
            )
        except (ClientError, ServerError) as exc:
            status = getattr(exc, "code", None)
            if status not in (429, 503) or attempt == _MAX_RETRIES:
                raise
            delay = _BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.warning(f"Gemini call got {status}, retrying in {delay}s (attempt {attempt}/{_MAX_RETRIES})")
            time.sleep(delay)
            last_exc = exc
    raise last_exc


def extract_structured_data(document_type: str, pages: list[PageText]) -> ExtractionResult:
    client = _get_client()
    ocr_text = _format_ocr_text(pages)
    prompt = build_extraction_prompt(document_type, ocr_text)

    logger.info(f"Calling Gemini ({settings.GEMINI_MODEL}) for extraction, doc_type={document_type}")

    try:
        response = _call_with_retry(client, prompt)
        raw = response.text
    except Exception as exc:
        logger.error(f"Gemini extraction call failed: {exc}")
        raise ExtractionError("LLM extraction call failed.", {"error": str(exc)})

    try:
        data = json.loads(raw)
        data["document_type"] = document_type  # enforce, don't trust model to echo correctly
        result = ExtractionResult.model_validate(data)
    except Exception as exc:
        logger.error(f"Failed to parse/validate LLM output: {exc}")
        raise ExtractionError(
            "LLM returned data that did not match the required schema.",
            {"error": str(exc)},
        )

    logger.info(f"Extraction succeeded: {len(result.fields)} fields, {len(result.tables)} tables")
    return result