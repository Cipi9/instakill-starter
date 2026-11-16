"""SQLite bootstrap for InstaKill. Uses the stdlib sqlite3 module (see R11)."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "instakill.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS follow (
    follower_id INTEGER NOT NULL REFERENCES user(id),
    followed_id INTEGER NOT NULL REFERENCES user(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (follower_id, followed_id),
    CHECK (follower_id != followed_id)
);

CREATE TABLE IF NOT EXISTS like (
    user_id INTEGER NOT NULL REFERENCES user(id),
    post_id INTEGER NOT NULL REFERENCES post(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, post_id)
);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(like)").fetchall()
        }
        if "created_at" not in columns:
            conn.execute(
                "ALTER TABLE like ADD COLUMN created_at TEXT"
            )
        follow_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(follow)").fetchall()
        }
        if "created_at" not in follow_columns:
            conn.execute(
                "ALTER TABLE follow ADD COLUMN created_at TEXT"
            )
        conn.execute(
            "UPDATE like SET created_at = COALESCE(created_at, "
            "(SELECT created_at FROM post WHERE post.id = like.post_id)) "
            "WHERE created_at IS NULL"
        )
        conn.execute(
            "UPDATE follow SET created_at = COALESCE(created_at, "
            "(SELECT created_at FROM user WHERE user.id = follow.follower_id)) "
            "WHERE created_at IS NULL"
        )


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
