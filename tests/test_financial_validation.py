from app.extraction.schemas import ExtractedField
from app.financial_validation.validators import (
    _parse_number,
    validate_balance_sheet,
    validate_invoice,
    validate_profit_and_loss,
    validate_cash_flow,
)


def f(name, value):
    return ExtractedField(name=name, value=value, page=1, source_text=None)


def test_parse_number_handles_commas_and_currency():
    assert _parse_number("4,030,194.26") == 4030194.26
    assert _parse_number("$138.90") == 138.90
    assert _parse_number("(1,234.00)") == -1234.00
    assert _parse_number(None) is None
    assert _parse_number("-") is None


def test_balance_sheet_pass():
    fields = [f("total_assets", "4,030,194.26"), f("total_capital_and_liabilities", "4,030,194.26")]
    checks = validate_balance_sheet(fields)
    assert checks[0].status == "PASS"


def test_balance_sheet_fail():
    fields = [f("total_assets", "100.00"), f("total_capital_and_liabilities", "90.00")]
    checks = validate_balance_sheet(fields)
    assert checks[0].status == "FAIL"
    assert checks[0].variance == 10.00


def test_balance_sheet_not_applicable_when_missing():
    fields = [f("some_other_field", "1.00")]
    checks = validate_balance_sheet(fields)
    assert checks[0].status == "NOT_APPLICABLE"


def test_profit_and_loss_pass():
    fields = [f("total_income", "1000"), f("total_expenses", "600"), f("net_profit", "400")]
    checks = validate_profit_and_loss(fields)
    assert checks[0].status == "PASS"


def test_invoice_gross_worth_check():
    fields = [f("net_worth", "126.27"), f("vat_amount", "12.63"), f("gross_worth", "138.90")]
    checks = validate_invoice(fields)
    assert checks[0].status == "PASS"


def test_invoice_gross_worth_fail_on_mismatch():
    fields = [f("net_worth", "100.00"), f("vat_amount", "10.00"), f("gross_worth", "999.00")]
    checks = validate_invoice(fields)
    assert checks[0].status == "FAIL"


def test_cash_flow_not_applicable_when_missing_fields():
    fields = [f("opening_cash_balance", "100")]
    checks = validate_cash_flow(fields)
    assert checks[0].status == "NOT_APPLICABLE"


def test_cash_flow_pass():
    fields = [
        f("opening_cash_balance", "100"),
        f("net_cash_from_operating_activities", "50"),
        f("net_cash_from_investing_activities", "-20"),
        f("net_cash_from_financing_activities", "10"),
        f("closing_cash_balance", "140"),
    ]
    checks = validate_cash_flow(fields)
    assert checks[0].status == "PASS"
