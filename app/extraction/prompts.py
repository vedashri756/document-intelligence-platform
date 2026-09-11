"""
Prompt templates for the Extraction layer.

Each document type gets a short list of "well-known" field names to
standardize when present. This is NOT a restriction on what can be
extracted - the model is always told to extract everything - it's a
naming convention so the downstream Financial Validation layer can
reliably locate the handful of summary figures it needs to run its
formula checks, without the model ever inventing a value that isn't
actually in the document.
"""

BASE_INSTRUCTIONS = """You are a financial document extraction engine. You will be given
OCR'd text from a {doc_type} document, page by page.

Rules (follow exactly):
1. Extract EVERY meaningful field, label, date, party name, currency, amount, and table visible
   in the text - not just a fixed short list. Be exhaustive.
2. If a value is unreadable, ambiguous, or simply not present, set it to null. NEVER invent,
   guess, or infer a value that is not supported by the text.
3. For each field, include the page number it appears on and a short verbatim snippet of the
   source text that supports the value (for evidence/grounding).
4. Where the document contains one of the "standard fields" listed below for this document type,
   use EXACTLY that name (snake_case) for the corresponding field, in addition to extracting it
   naturally. If a standard field is genuinely not present in the document, simply omit it - do
   not fabricate it.
5. Extract tables (financial statement line items, invoice line items) into the tables array with
   their column headers and rows, preserving row order.
6. Numeric values should be extracted as they appear in the source (keep original formatting,
   e.g. "4,030,194.26" or "(1,234.00)" for negatives) - do not do any math yourself.

Standard field names for this document type (use these exact snake_case names when the
corresponding line item is present):
{standard_fields}

OCR TEXT (page by page):
{ocr_text}
"""

STANDARD_FIELDS = {
    "BALANCE_SHEET": """
- total_capital_and_liabilities (the "Total" under Capital and Liabilities)
- total_assets (the "Total" under Assets)
- as_at_date
""",
    "PROFIT_AND_LOSS": """
- total_income
- total_expenses
- net_profit (profit/loss for the period)
- period_end_date
""",
    "CASH_FLOW": """
- opening_cash_balance
- closing_cash_balance
- net_cash_from_operating_activities
- net_cash_from_investing_activities
- net_cash_from_financing_activities
- period_end_date
""",
    "INVOICE": """
- invoice_number
- invoice_date
- seller_name
- client_name
- net_worth (subtotal before tax)
- vat_amount (total tax/VAT)
- gross_worth (grand total including tax)
""",
}


def build_extraction_prompt(document_type: str, ocr_text: str) -> str:
    return BASE_INSTRUCTIONS.format(
        doc_type=document_type,
        standard_fields=STANDARD_FIELDS.get(document_type, ""),
        ocr_text=ocr_text,
    )
