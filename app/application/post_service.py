
"""Application behavior for composing posts from existing domain models."""
from datetime import datetime, timezone

from app.domain.models import Post, User


def create_post(
    user: User,
    content: str,
    *,
    created_at: datetime | None = None,
) -> Post:
    """Create a validated post value for a persisted user.

    Persistence is deliberately left to a future adapter or endpoint layer.
    """
    if user.id is None:
        raise ValueError("A post author must have a persisted user id.")
    if not content.strip():
        raise ValueError("Post content must not be blank.")

    return Post(
        user_id=user.id,
        content=content,
        created_at=created_at or datetime.now(timezone.utc),
    )
