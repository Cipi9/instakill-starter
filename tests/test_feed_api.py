from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.feed import router
from app.db.database import init_db
from app.feed.repository import FeedRepository
from app.feed.service import FeedService


def test_feed_api_returns_seeded_feed():
    init_db()
    app = FastAPI()
    app.include_router(router)
    app.state.feed_service = FeedService(FeedRepository())

    response = TestClient(app).get("/feed?user_id=1&limit=3&strategy=for_you")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 1
    assert body["strategy"] == "for_you"
    assert len(body["results"]) <= 3
    assert all("score" in result for result in body["results"])
