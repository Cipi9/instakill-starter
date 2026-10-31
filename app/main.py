from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.search import router as search_router
from app.api.feed import router as feed_router
from app.application.search_service import SearchService
from app.db.database import init_db
from app.feed.repository import FeedRepository
from app.feed.service import FeedService
from app.search.encoder import SentenceTransformerEncoder
from app.search.repository import PostRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.search_service = SearchService(
        repository=PostRepository(),
        encoder=SentenceTransformerEncoder(),
    )
    app.state.feed_service = FeedService(repository=FeedRepository())
    yield


app = FastAPI(title="InstaKill", lifespan=lifespan)
app.include_router(search_router)
app.include_router(feed_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
