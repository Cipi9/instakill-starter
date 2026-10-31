"""HTTP adapter for the personalised feed."""
from fastapi import APIRouter, HTTPException, Query, Request

from app.feed.service import FeedService, UnknownUserError

router = APIRouter()


@router.get("/feed")
def feed(
    request: Request,
    user_id: int = Query(...),
    limit: int = Query(20, ge=1, le=50),
    strategy: str = Query("for_you"),
) -> dict:
    service: FeedService = request.app.state.feed_service
    try:
        results = service.get_feed(user_id, limit, strategy)
    except UnknownUserError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    serialized = []
    for result in results:
        post = result.post if hasattr(result, "post") else result
        item = {
            "post_id": post.id,
            "user_id": post.user_id,
            "content": post.content,
            "created_at": post.created_at,
        }
        if hasattr(result, "score"):
            item["score"] = result.score
        serialized.append(item)
    return {"user_id": user_id, "strategy": strategy, "results": serialized}
