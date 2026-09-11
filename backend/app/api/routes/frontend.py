"""
HTML page routes — serves the upload page, dashboard, and document result
page. Kept separate from api/routes/documents.py, which returns JSON only.
"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "frontend" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["frontend"])


@router.get("/", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/document/{document_name}", response_class=HTMLResponse)
def document_result_page(request: Request, document_name: str):
    return templates.TemplateResponse(
        "document_result.html", {"request": request, "document_name": document_name}
    )
