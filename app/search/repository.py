"""Database access for searchable posts."""
from collections.abc import Sequence

from app.db.database import get_connection
from app.domain.models import Post


class PostRepository:
    """Reads posts without exposing SQLite details to search logic."""

    def list_posts(self) -> Sequence[Post]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT id, user_id, content, created_at FROM post ORDER BY id"
            ).fetchall()

        return [
            Post(
                id=row["id"],
                user_id=row["user_id"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
