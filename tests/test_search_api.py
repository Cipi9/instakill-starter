from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.search import router


def test_search_rejects_whitespace_only_query():
    app = FastAPI()
    app.include_router(router)
    app.state.search_service = object()

    response = TestClient(app).get("/search?q=%20%20")

    assert response.status_code == 422
    assert response.json()["detail"] == "q must not be empty"
