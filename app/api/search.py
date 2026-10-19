"""HTTP adapter for semantic search."""
from fastapi import APIRouter, Query, Request

from app.application.search_service import SearchService

router = APIRouter()


@router.get("/search")
def search(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=20),
) -> dict:
    service: SearchService = request.app.state.search_service
    response = service.search(q, limit)
    return {
        "query": response.query,
        "results": [
            {
                "post_id": result.post.id,
                "user_id": result.post.user_id,
                "content": result.post.content,
                "score": result.score,
            }
            for result in response.results
        ],
    }
