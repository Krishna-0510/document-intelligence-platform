"""
AI-based field & table extraction (spec section 4.2).

Sends OCR'd/extracted text to an LLM with a strict, document-type-specific
prompt and parses the JSON it returns. Uses the OpenAI-compatible chat
completions API by default (works with OpenAI directly, and with any
OpenAI-compatible endpoint) — swap `_call_llm` for a different provider's
SDK if you prefer Gemini/Anthropic/etc.

The API key is never hardcoded: it comes from settings.llm_api_key, which
pydantic-settings reads from the environment (see core/config.py).
"""
import json
import re

from app.core.config import get_settings
from app.core.exceptions import ExtractionError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Minimum required fields per document type (spec section 2) — the prompt
# also instructs the model to capture *every other visible field*, not just
# these; this list only sets the floor.
REQUIRED_FIELDS = {
    "invoice": [
        "invoice_number", "invoice_date", "vendor_name", "customer_name",
        "currency", "subtotal", "tax_amount", "discount", "total_amount",
    ],
    "balance_sheet": ["total_assets", "total_liabilities", "total_equity"],
    "profit_and_loss": [
        "revenue", "cost_of_sales", "gross_profit", "operating_expenses",
        "operating_profit", "tax", "net_profit",
    ],
    "cash_flow_statement": [
        "operating_cash_flow", "investing_cash_flow", "financing_cash_flow",
        "opening_cash", "net_change_in_cash", "closing_cash",
    ],
}

_SYSTEM_PROMPT = """You are a financial document data-extraction engine.
You will be given OCR/parsed text from a {doc_type} and a minimum list of
required fields. Return ONLY a single valid JSON object - no prose, no
markdown fences.

Rules:
- Extract EVERY meaningful field visible in the text, not just the minimum
  list: header info, dates, parties, currency, all line items, all
  financial statement line items, and comparative-period values.
- For each scalar field, return an object: {{"value": <number-or-string-or-null>,
  "page_number": <int-or-null>, "source_text": "<verbatim snippet supporting
  the value, or null>"}}.
- If a field is not present in the text, its value MUST be null. Never
  invent, infer, or guess a value.
- For invoices, include a "line_items" array of
  {{"description", "quantity", "unit_price", "amount"}} objects (numbers,
  not strings, for numeric sub-fields).
- Treat parenthesised numbers like "(500)" as negative values.
- Minimum required fields for this document type: {required_fields}
{doc_type_guidance}"""

_BALANCE_SHEET_GUIDANCE = """
- Balance sheets are not always laid out with a single line item literally
  labeled "Total Liabilities" or "Total Equity" (e.g. bank-style statements
  under headings like "Capital and Liabilities" / "Assets"). If no single
  matching line exists, derive the value by summing the sub-line items that
  belong to that category (e.g. Capital + Reserves and Surplus + Minority
  Interest => total_equity; Deposits + Borrowings + Other Liabilities and
  Provisions => total_liabilities), and set source_text to a short note
  listing which line items were summed. If you cannot confidently determine
  which sub-items belong to a category, return null rather than guessing.
"""

_USER_PROMPT = """Document text (OCR/extracted, may contain minor OCR noise):
---
{raw_text}
---
Return the JSON object now."""


def extract_fields(document_type: str, raw_text: str) -> dict:
    """Returns extracted_data dict: {field_name: {value, page_number,
    source_text}, ..., "line_items": [...]}"""
    if document_type not in REQUIRED_FIELDS:
        raise ExtractionError(f"Unsupported document_type '{document_type}'.")

    if not raw_text or not raw_text.strip():
        raise ExtractionError("No text could be extracted from the document to send for extraction.")

    system_prompt = _SYSTEM_PROMPT.format(
        doc_type=document_type.replace("_", " "),
        required_fields=", ".join(REQUIRED_FIELDS[document_type]),
        doc_type_guidance=_BALANCE_SHEET_GUIDANCE if document_type == "balance_sheet" else "",
    )
    user_prompt = _USER_PROMPT.format(raw_text=raw_text[:15000])  # guard against runaway token usage

    try:
        raw_response = _call_llm(system_prompt, user_prompt)
        return _parse_json_response(raw_response)
    except ExtractionError:
        raise
    except Exception as exc:
        logger.exception("Field extraction failed for document_type=%s", document_type)
        raise ExtractionError("Field extraction failed while calling the LLM.") from exc


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """OpenAI-compatible chat completion. Requires LLM_API_KEY in the environment."""
    if not settings.llm_api_key:
        raise ExtractionError(
            "LLM_API_KEY is not configured. Set it as an environment variable "
            "(see .env.example) before processing documents."
        )

    from openai import OpenAI  # imported lazily so the app can boot without the package configured

    client = OpenAI(api_key=settings.llm_api_key, base_url="https://api.groq.com/openai/v1")
    completion = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return completion.choices[0].message.content


def _parse_json_response(raw_response: str) -> dict:
    cleaned = raw_response.strip()
    cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned non-JSON output: %s", cleaned[:500])
        raise ExtractionError("The extraction model returned an invalid response.") from exc
