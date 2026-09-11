"""Basic API flow tests."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # Context-manager form triggers FastAPI startup/shutdown events,
    # which is what creates the DB tables (see app/core/database.init_db).
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_unknown_document_returns_404(client):
    response = client.get("/api/v1/documents/does-not-exist.pdf")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_list_documents_returns_list(client):
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
