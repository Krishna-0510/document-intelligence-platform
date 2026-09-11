"""
Financial calculation validation (spec section 4.4).

Each check function returns a ValidationCheck-shaped dict. If a required
input field is missing, status is NOT_APPLICABLE — never guess a value.

A small numerical tolerance absorbs rounding; document your chosen
tolerance in the README as the spec requires.
"""
from app.core.logging import get_logger

logger = get_logger(__name__)

TOLERANCE = 0.01  # 1% relative tolerance — tune and document in README


def _get(extracted: dict, field: str):
    entry = extracted.get(field)
    return entry.get("value") if isinstance(entry, dict) else entry


def _check(name: str, formula: str, operands: dict, calculated, reported) -> dict:
    if calculated is None or reported is None:
        return {
            "name": name, "formula": formula, "operands": operands,
            "calculated_value": calculated, "reported_value": reported,
            "variance": None, "status": "NOT_APPLICABLE",
        }
    variance = round(calculated - reported, 2)
    within_tolerance = abs(variance) <= max(abs(reported) * TOLERANCE, 0.01)
    return {
        "name": name, "formula": formula, "operands": operands,
        "calculated_value": calculated, "reported_value": reported,
        "variance": variance, "status": "PASS" if within_tolerance else "FAIL",
    }


def validate_invoice(extracted: dict) -> list[dict]:
    subtotal = _get(extracted, "subtotal")
    tax = _get(extracted, "tax_amount")
    discount = _get(extracted, "discount") or 0
    total = _get(extracted, "total_amount")

    checks = []
    if subtotal is not None and tax is not None and total is not None:
        calculated = round(subtotal + tax - discount, 2)
        checks.append(_check(
            "invoice_total_check", "subtotal + tax_amount - discount",
            {"subtotal": subtotal, "tax_amount": tax, "discount": discount},
            calculated, total,
        ))
    else:
        checks.append(_check(
            "invoice_total_check", "subtotal + tax_amount - discount",
            {"subtotal": subtotal, "tax_amount": tax, "discount": discount}, None, total,
        ))

    line_items = extracted.get("line_items") or []
    if line_items:
        calc_sum = round(sum((li.get("amount") or 0) for li in line_items), 2)
        checks.append(_check(
            "line_items_sum_check", "sum(line_item.amount)",
            {"line_item_count": len(line_items)}, calc_sum, subtotal,
        ))
    return checks


def validate_balance_sheet(extracted: dict) -> list[dict]:
    assets = _get(extracted, "total_assets")
    liabilities = _get(extracted, "total_liabilities")
    equity = _get(extracted, "total_equity")
    calculated = (liabilities + equity) if (liabilities is not None and equity is not None) else None
    return [_check(
        "balance_sheet_equation", "total_liabilities + total_equity ≈ total_assets",
        {"total_liabilities": liabilities, "total_equity": equity}, calculated, assets,
    )]


def validate_profit_and_loss(extracted: dict) -> list[dict]:
    revenue = _get(extracted, "revenue")
    cogs = _get(extracted, "cost_of_sales")
    gross_profit = _get(extracted, "gross_profit")
    opex = _get(extracted, "operating_expenses")
    operating_profit = _get(extracted, "operating_profit")

    checks = []
    calc_gp = (revenue - cogs) if (revenue is not None and cogs is not None) else None
    checks.append(_check(
        "gross_profit_check", "revenue - cost_of_sales",
        {"revenue": revenue, "cost_of_sales": cogs}, calc_gp, gross_profit,
    ))
    calc_op = (gross_profit - opex) if (gross_profit is not None and opex is not None) else None
    checks.append(_check(
        "operating_profit_check", "gross_profit - operating_expenses",
        {"gross_profit": gross_profit, "operating_expenses": opex}, calc_op, operating_profit,
    ))
    return checks


def validate_cash_flow_statement(extracted: dict) -> list[dict]:
    ocf = _get(extracted, "operating_cash_flow")
    icf = _get(extracted, "investing_cash_flow")
    fcf = _get(extracted, "financing_cash_flow")
    opening = _get(extracted, "opening_cash")
    net_change = _get(extracted, "net_change_in_cash")
    closing = _get(extracted, "closing_cash")

    checks = []
    calc_net_change = (
        (ocf + icf + fcf) if None not in (ocf, icf, fcf) else None
    )
    checks.append(_check(
        "net_change_in_cash_check",
        "operating_cash_flow + investing_cash_flow + financing_cash_flow",
        {"operating_cash_flow": ocf, "investing_cash_flow": icf, "financing_cash_flow": fcf},
        calc_net_change, net_change,
    ))
    calc_closing = (opening + net_change) if (opening is not None and net_change is not None) else None
    checks.append(_check(
        "closing_cash_check", "opening_cash + net_change_in_cash",
        {"opening_cash": opening, "net_change_in_cash": net_change}, calc_closing, closing,
    ))
    return checks


VALIDATORS = {
    "invoice": validate_invoice,
    "balance_sheet": validate_balance_sheet,
    "profit_and_loss": validate_profit_and_loss,
    "cash_flow_statement": validate_cash_flow_statement,
}


def run_validation(document_type: str, extracted: dict) -> dict:
    checks = VALIDATORS[document_type](extracted)
    statuses = {c["status"] for c in checks}
    if "FAIL" in statuses:
        overall = "FAIL"
    elif statuses == {"NOT_APPLICABLE"}:
        overall = "NOT_APPLICABLE"
    else:
        overall = "PASS"
    issues = [c["name"] for c in checks if c["status"] == "FAIL"]
    return {"checks": checks, "overall_status": overall, "issues": issues}
