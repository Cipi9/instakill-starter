"""HTTP adapter for semantic search."""
from fastapi import APIRouter, HTTPException, Query, Request

from app.application.search_service import SearchService

router = APIRouter()


@router.get("/search")
def search(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=20),
) -> dict:
    if not q.strip():
        raise HTTPException(status_code=422, detail="q must not be empty")

    service: SearchService = request.app.state.search_service
    try:
        response = service.search(q, limit)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
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
