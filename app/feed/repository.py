"""SQLite reads used by the feed service."""
from collections.abc import Sequence

from app.db.database import get_connection
from app.domain.models import Post


class FeedRepository:
    def user_exists(self, user_id: int) -> bool:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM user WHERE id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def liked_post_ids(self, user_id: int) -> set[int]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT post_id FROM like WHERE user_id = ?", (user_id,)
            ).fetchall()
        return {row["post_id"] for row in rows}

    def followed_author_ids(self, user_id: int) -> set[int]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT followed_id FROM follow WHERE follower_id = ?", (user_id,)
            ).fetchall()
        return {row["followed_id"] for row in rows}

    def list_candidates(
        self, user_id: int, followed_ids: set[int], liked_post_ids: set[int]
    ) -> Sequence[Post]:
        with get_connection() as connection:
            if followed_ids:
                placeholders = ",".join("?" for _ in followed_ids)
                query = (
                    "SELECT id, user_id, content, created_at FROM post "
                    f"WHERE user_id IN ({placeholders}) ORDER BY id"
                )
                rows = connection.execute(query, tuple(followed_ids)).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, user_id, content, created_at FROM post "
                    "WHERE user_id != ? ORDER BY id",
                    (user_id,),
                ).fetchall()
        return [
            Post(
                id=row["id"],
                user_id=row["user_id"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in rows
            if row["id"] not in liked_post_ids
        ]

    def like_counts(self, post_ids: Sequence[int]) -> dict[int, int]:
        if not post_ids:
            return {}
        placeholders = ",".join("?" for _ in post_ids)
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT post_id, COUNT(*) AS count FROM like "
                f"WHERE post_id IN ({placeholders}) GROUP BY post_id",
                tuple(post_ids),
            ).fetchall()
        return {row["post_id"]: row["count"] for row in rows}
