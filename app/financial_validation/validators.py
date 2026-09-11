"""
Financial Validation layer (spec section 4.4).

Deliberately pure Python / rule-based, not LLM-based: these are arithmetic
checks, and an LLM has no business "deciding" whether a balance sheet
balances. Every check:
  - looks up the fields it needs from the extracted field list (by keyword
    match against field names, since labels vary by company/document)
  - if any required field is missing -> returns NOT_APPLICABLE (never
    guesses or assumes a value)
  - otherwise computes the check and returns PASS/FAIL with the variance

A small numeric tolerance is allowed for rounding differences.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from app.extraction.schemas import ExtractedField

TOLERANCE = 1.0  # absolute tolerance, in the document's reporting units


@dataclass
class ValidationCheck:
    check_name: str
    formula: str
    inputs: dict = field(default_factory=dict)
    calculated_value: Optional[float] = None
    reported_value: Optional[float] = None
    variance: Optional[float] = None
    status: str = "NOT_APPLICABLE"  # PASS | FAIL | NOT_APPLICABLE
    note: Optional[str] = None


def _parse_number(raw: Optional[str]) -> Optional[float]:
    """Parses financial-statement-style numbers: '4,030,194.26', '(1,234.00)'
    (accounting negative), '$138.90', '12,63' (comma decimal in some invoices)."""
    if raw is None:
        return None
    s = raw.strip()
    if s == "" or s == "-":
        return None
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    s = re.sub(r"[^\d.,\-]", "", s)
    if s.startswith("-"):
        negative = True
        s = s[1:]
    if not s:
        return None
    # Handle "1.234,56" (comma as decimal) vs "1,234.56" (comma as thousands)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # Ambiguous: if exactly 2 digits after the last comma, treat as decimal
        parts = s.split(",")
        if len(parts[-1]) == 2:
            s = s.replace(",", ".", s.count(",") - 1).replace(",", "")
            s = ".".join(parts[:-1]).replace(",", "") + "." + parts[-1] if len(parts) > 1 else s
            s = re.sub(r"\.(?=.*\.)", "", s)  # keep only last dot
        else:
            s = s.replace(",", "")
    try:
        val = float(s)
    except ValueError:
        return None
    return -val if negative else val


def _find_field(fields: list[ExtractedField], *keyword_groups: list[str]) -> Optional[ExtractedField]:
    """Finds the first field whose name contains ALL keywords in a keyword
    group, trying groups in order (most specific first)."""
    for group in keyword_groups:
        for f in fields:
            name = f.name.lower().replace(" ", "_")
            if all(k in name for k in group):
                if f.value is not None:
                    return f
    return None


def _formula_labels(formula: str) -> tuple[str, str, str]:
    """Extracts readable field names from a formula string like
    'net_worth + vat_amount == gross_worth' -> ('net_worth', 'vat_amount', 'gross_worth').
    Falls back to generic labels if the formula doesn't match the expected shape."""
    try:
        left, right = formula.split("==")
        expected_label = right.strip()
        match = re.match(r"\s*([a-zA-Z0-9_]+)\s*[+\-]\s*([a-zA-Z0-9_]+)\s*", left)
        if match:
            return match.group(1), match.group(2), expected_label
    except ValueError:
        pass
    return "value_a", "value_b", "expected_value"


def _check(name: str, formula: str, a: Optional[ExtractedField], b: Optional[ExtractedField],
           expected: Optional[ExtractedField], op) -> ValidationCheck:
    a_label, b_label, expected_label = _formula_labels(formula)
    if a is None or b is None or expected is None:
        missing = [label for label, x in [(a_label, a), (b_label, b), (expected_label, expected)] if x is None]
        return ValidationCheck(
            check_name=name, formula=formula, status="NOT_APPLICABLE",
            note=f"Required field(s) not present in document: {missing}",
        )

    va, vb, ve = _parse_number(a.value), _parse_number(b.value), _parse_number(expected.value)
    if va is None or vb is None or ve is None:
        return ValidationCheck(
            check_name=name, formula=formula, status="NOT_APPLICABLE",
            note="A required value could not be parsed as a number.",
        )

    calculated = op(va, vb)
    variance = round(calculated - ve, 2)
    status = "PASS" if abs(variance) <= TOLERANCE else "FAIL"
    return ValidationCheck(
        check_name=name, formula=formula,
        inputs={a.name: va, b.name: vb, expected.name: ve},
        calculated_value=round(calculated, 2), reported_value=ve,
        variance=variance, status=status,
    )


def validate_balance_sheet(fields: list[ExtractedField]) -> list[ValidationCheck]:
    assets = _find_field(fields, ["total_assets"], ["total", "assets"])
    liab = _find_field(fields, ["total_capital_and_liabilities"], ["total", "liabilit"])
    if assets is None or liab is None:
        return [ValidationCheck(
            check_name="Assets = Capital & Liabilities",
            formula="total_assets == total_capital_and_liabilities",
            status="NOT_APPLICABLE",
            note="total_assets or total_capital_and_liabilities not found in document.",
        )]
    va, vl = _parse_number(assets.value), _parse_number(liab.value)
    if va is None or vl is None:
        return [ValidationCheck(
            check_name="Assets = Capital & Liabilities",
            formula="total_assets == total_capital_and_liabilities",
            status="NOT_APPLICABLE", note="Values present but not parseable as numbers.",
        )]
    variance = round(va - vl, 2)
    status = "PASS" if abs(variance) <= TOLERANCE else "FAIL"
    return [ValidationCheck(
        check_name="Assets = Capital & Liabilities",
        formula="total_assets == total_capital_and_liabilities",
        inputs={assets.name: va, liab.name: vl},
        calculated_value=va, reported_value=vl, variance=variance, status=status,
    )]


def validate_profit_and_loss(fields: list[ExtractedField]) -> list[ValidationCheck]:
    income = _find_field(fields, ["total_income"], ["total", "income"])
    expenses = _find_field(fields, ["total_expenses"], ["total", "expens"])
    net_profit = _find_field(fields, ["net_profit"], ["profit", "loss"], ["profit", "period"])
    return [_check(
        "Net Profit = Total Income - Total Expenses",
        "total_income - total_expenses == net_profit",
        income, expenses, net_profit, lambda a, b: a - b,
    )]


def validate_cash_flow(fields: list[ExtractedField]) -> list[ValidationCheck]:
    opening = _find_field(fields, ["opening_cash_balance"], ["opening", "cash"], ["cash", "beginning"])
    op_cf = _find_field(fields, ["net_cash_from_operating_activities"], ["operating", "activ"])
    inv_cf = _find_field(fields, ["net_cash_from_investing_activities"], ["investing", "activ"])
    fin_cf = _find_field(fields, ["net_cash_from_financing_activities"], ["financing", "activ"])
    closing = _find_field(fields, ["closing_cash_balance"], ["closing", "cash"], ["cash", "end"])

    if not all([opening, op_cf, inv_cf, fin_cf, closing]):
        missing = [n for n, v in [("opening", opening), ("operating_cf", op_cf),
                                   ("investing_cf", inv_cf), ("financing_cf", fin_cf),
                                   ("closing", closing)] if v is None]
        return [ValidationCheck(
            check_name="Closing Balance = Opening + Net Cash Flows",
            formula="opening_cash_balance + operating_cf + investing_cf + financing_cf == closing_cash_balance",
            status="NOT_APPLICABLE",
            note=f"Required field(s) not found: {missing}",
        )]

    vals = [_parse_number(x.value) for x in (opening, op_cf, inv_cf, fin_cf, closing)]
    if any(v is None for v in vals):
        return [ValidationCheck(
            check_name="Closing Balance = Opening + Net Cash Flows",
            formula="opening_cash_balance + operating_cf + investing_cf + financing_cf == closing_cash_balance",
            status="NOT_APPLICABLE", note="A required value could not be parsed as a number.",
        )]

    v_open, v_op, v_inv, v_fin, v_close = vals
    calculated = v_open + v_op + v_inv + v_fin
    variance = round(calculated - v_close, 2)
    status = "PASS" if abs(variance) <= TOLERANCE else "FAIL"
    return [ValidationCheck(
        check_name="Closing Balance = Opening + Net Cash Flows",
        formula="opening_cash_balance + operating_cf + investing_cf + financing_cf == closing_cash_balance",
        inputs={opening.name: v_open, op_cf.name: v_op, inv_cf.name: v_inv, fin_cf.name: v_fin},
        calculated_value=round(calculated, 2), reported_value=v_close,
        variance=variance, status=status,
    )]


def validate_invoice(fields: list[ExtractedField]) -> list[ValidationCheck]:
    net = _find_field(fields, ["net_worth"], ["net", "worth"], ["subtotal"])
    vat = _find_field(fields, ["vat_amount"], ["vat"], ["tax"])
    gross = _find_field(fields, ["gross_worth"], ["gross", "worth"], ["total"])
    checks = [_check(
        "Gross Worth = Net Worth + VAT",
        "net_worth + vat_amount == gross_worth",
        net, vat, gross, lambda a, b: a + b,
    )]
    return checks


VALIDATORS = {
    "BALANCE_SHEET": validate_balance_sheet,
    "PROFIT_AND_LOSS": validate_profit_and_loss,
    "CASH_FLOW": validate_cash_flow,
    "INVOICE": validate_invoice,
}


def run_financial_validation(document_type: str, fields: list[ExtractedField]) -> list[ValidationCheck]:
    validator = VALIDATORS.get(document_type)
    if validator is None:
        return []
    return validator(fields)
