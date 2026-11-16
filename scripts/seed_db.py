"""Seed a deterministic, time-aware database for the API and evaluator."""
from datetime import datetime, timedelta, timezone

from app.db.database import get_connection, init_db

USERS = ["alice", "bob", "carol", "dave", "erin"]
BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def seed() -> None:
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM like")
        conn.execute("DELETE FROM follow")
        conn.execute("DELETE FROM post")
        conn.execute("DELETE FROM user")
        conn.executemany(
            "INSERT INTO user (id, username, created_at) VALUES (?, ?, ?)",
            [
                (index, username, (BASE_TIME - timedelta(days=30)).isoformat())
                for index, username in enumerate(USERS, start=1)
            ],
        )
        posts = []
        for offset in range(25):
            author_id = offset % len(USERS) + 1
            created_at = BASE_TIME + timedelta(days=offset)
            posts.append(
                (
                    offset + 1,
                    author_id,
                    f"post {offset + 1} from {USERS[author_id - 1]}",
                    created_at.isoformat(),
                )
            )
        conn.executemany(
            "INSERT INTO post (id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
            posts,
        )
        follows = [
            (1, 2), (1, 3), (2, 1), (2, 4), (3, 4), (3, 5), (4, 5), (5, 1)
        ]
        conn.executemany(
            "INSERT INTO follow (follower_id, followed_id, created_at) VALUES (?, ?, ?)",
            [
                (*pair, (BASE_TIME + timedelta(days=9)).isoformat())
                for pair in follows
            ],
        )
        likes = []
        for user_id in range(1, len(USERS) + 1):
            for post_id in range(1, 16):
                if (post_id - 1) % len(USERS) + 1 == user_id:
                    continue
                likes.append(
                    (
                        user_id,
                        post_id,
                        (BASE_TIME + timedelta(days=15 + user_id)).isoformat(),
                    )
                )
        for user_id in range(1, len(USERS) + 1):
            for post_id in range(16, 26):
                if (post_id - 1) % len(USERS) + 1 == user_id:
                    continue
                likes.append(
                    (
                        user_id,
                        post_id,
                        (BASE_TIME + timedelta(days=25 + user_id)).isoformat(),
                    )
                )
        conn.executemany(
            "INSERT INTO like (user_id, post_id, created_at) VALUES (?, ?, ?)",
            likes,
        )
        conn.commit()
    print(f"Seeded {len(USERS)} users and {len(posts)} posts.")


if __name__ == "__main__":
    seed()
