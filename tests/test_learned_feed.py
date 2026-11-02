from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.feed import router
from app.db.database import init_db
from app.feed.repository import FeedRepository
from app.feed.service import FeedService


def test_learned_feed_returns_model_scores():
    init_db()
    app = FastAPI()
    app.include_router(router)
    app.state.feed_service = FeedService(FeedRepository())

    response = TestClient(app).get("/feed?user_id=1&limit=3&strategy=learned")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) <= 3
    assert all("score" in result for result in results)
    assert all(0 <= result["score"] <= 1 for result in results)
