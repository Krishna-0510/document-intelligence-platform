# Document Intelligence Platform

Intelligent document extraction, validation & API platform for invoices, balance sheets, profit & loss statements, and cash flow statements.

## 1. Solution Overview & Architecture

This application accepts a PDF/JPG/PNG financial document, extracts all visible fields and tables using OCR + an LLM, runs financial validation checks (e.g. subtotal + tax = total), stores the result in a database, and displays it on a dashboard.

**Flow:** Upload → File Validation → OCR (Tesseract) → Field Extraction (LLM) → Financial Validation → Store in DB → Display on Dashboard

**Architecture:**
```
Frontend (HTML/CSS/JS, Jinja2 templates)
        │
        ▼
FastAPI Backend
  ├── routes/documents.py        → REST API endpoints
  ├── services/document_validation_service.py  → file checks
  ├── services/ocr_service.py    → Tesseract OCR + PyMuPDF text extraction
  ├── services/extraction_service.py → LLM field/table extraction
  ├── services/financial_validation_service.py → calculation checks
  ├── repositories/document_repository.py → DB access
  └── models/document.py         → SQLAlchemy model
        │
        ▼
SQLite Database
```

## 2. Technology Stack

| Component | Technology | Reason |
|---|---|---|
| Backend | FastAPI | Async, built-in Swagger/OpenAPI docs, Pydantic validation |
| Database | SQLite (via SQLAlchemy) | Zero-config, sufficient for evaluation scope |
| OCR | Tesseract (pytesseract) + PyMuPDF | Free, local, no API limits |
| LLM | Groq (OpenAI-compatible API) | Free tier, fast inference |
| Frontend | HTML/CSS/JS + Jinja2 | Meets "no separate JS framework required" spec |
| Testing | Pytest | Standard Python testing |

## 3. Local Setup Instructions

```
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME/backend
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Edit `.env` and add your own `LLM_API_KEY`. Then:
```
pytest -q
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000/` for the dashboard and `http://localhost:8000/docs` for Swagger UI.

## 4. Environment Variables (see `.env.example`)

```
APP_NAME="Document Intelligence Platform"
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite:///./document_intelligence.db
LLM_PROVIDER=groq
LLM_API_KEY=            # your own key — never commit a real value
LLM_MODEL=openai/gpt-oss-120b
OCR_ENGINE=tesseract
OCR_API_KEY=
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

## 5. Deployed URLs

- **Frontend / Dashboard:** _TODO — add after deployment_
- **Backend API base URL:** _TODO_
- **Swagger / OpenAPI docs:** _TODO — e.g. https://your-app.onrender.com/docs_
- **Public GitHub Repository:** _TODO_

## 6. API Request Examples

**POST — process a document**
```
curl -X POST "https://your-app.onrender.com/api/v1/documents/process" \
  -F "file=@invoice.jpg" \
  -F "document_type=invoice"
```

**GET — retrieve latest result by document name**
```
curl "https://your-app.onrender.com/api/v1/documents/{document_name}"
```

**GET — list all processed documents (dashboard data)**
```
curl "https://your-app.onrender.com/api/v1/documents"
```

## 7. OCR / LLM Services Used

- **OCR:** Tesseract (local, open-source) via `pytesseract`, with PyMuPDF for native PDF text extraction.
- **LLM:** Groq API (free tier), model `openai/gpt-oss-120b`, used for structured field/table extraction with JSON mode.

## 8. Confidence Scoring

_Not implemented — optional per spec._

## 9. Financial Validation Rules & Tolerance

- Tolerance: 1% relative difference (`TOLERANCE = 0.01` in `financial_validation_service.py`)
- **Invoice:** `subtotal + tax - discount == total_amount`; line items sum check
- **Balance Sheet:** `total_liabilities + total_equity == total_assets`
- **P&L:** `revenue - cost_of_sales == gross_profit`; `gross_profit - operating_expenses == operating_profit`
- **Cash Flow:** `operating + investing + financing == net_change_in_cash`; `opening + net_change == closing_cash`
- If a required field is missing, the check returns `NOT_APPLICABLE` instead of guessing.

## 10. Database / Persistence

SQLite database (`document_intelligence.db`), accessed via SQLAlchemy ORM. Each processed document is stored with its name, type, status, and full result JSON. Fetching by name returns the most recent record for that name.

## 11. Known Limitations

- SQLite is file-based — not ideal for concurrent multi-user production use.
- No authentication/authorization on the API.
- Confidence scoring not implemented.
- OCR accuracy depends on scan quality; no manual correction UI.

## 12. What I'd Change for Production

- Move to PostgreSQL for concurrent access and durability.
- Add authentication (API keys or OAuth) on endpoints.
- Add retry/backoff logic and rate-limit handling for LLM calls.
- Add structured confidence scoring based on OCR quality + LLM agreement.
- Add async/background job processing for large batches instead of synchronous requests.

## 13. AI Coding Assistants Used

Claude (Anthropic) was used to help scaffold the backend structure, debug environment/dependency setup issues (Python version, Tesseract, Groq API integration), and write this README.
