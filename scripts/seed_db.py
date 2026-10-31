"""Seeds the InstaKill database with a handful of synthetic users and posts."""
from app.db.database import get_connection, init_db

USERS = ["alice", "bob", "carol", "dave", "erin"]
POSTS = [
    (1, "hello world, this is my first post"),
    (1, "does anyone else think the feed is chronological only? boring"),
    (2, "just shipped a cosine similarity search, feels great"),
    (3, "spam spam spam buy now click here"),
    (4, "benchmarking my ranker against popularity baseline today"),
    (5, "red-team week is going to be brutal, good luck everyone"),
]


def seed() -> None:
    init_db()
    with get_connection() as conn:
        for username in USERS:
            conn.execute(
                "INSERT OR IGNORE INTO user (username) VALUES (?)", (username,)
            )
        for user_id, content in POSTS:
            conn.execute(
                "INSERT INTO post (user_id, content) VALUES (?, ?)", (user_id, content)
            )
        conn.executemany(
            "INSERT OR IGNORE INTO follow (follower_id, followed_id) VALUES (?, ?)",
            [(1, 2), (1, 3), (2, 1), (3, 4), (4, 5)],
        )
        post_ids = conn.execute(
            "SELECT id, user_id FROM post ORDER BY id"
        ).fetchall()
        likes = [
            (1, row["id"])
            for row in post_ids
            if row["user_id"] == 2 and row["id"] % 2 == 0
        ]
        likes.extend(
            (2, row["id"])
            for row in post_ids
            if row["user_id"] in {1, 4} and row["id"] % 2 == 1
        )
        conn.executemany(
            "INSERT OR IGNORE INTO like (user_id, post_id) VALUES (?, ?)", likes
        )
        conn.commit()
    print(f"Seeded {len(USERS)} users and {len(POSTS)} posts.")


if __name__ == "__main__":
    seed()
