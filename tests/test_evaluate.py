import math
import gc
import sqlite3
from datetime import datetime, timezone

from app.db.database import SCHEMA
from scripts.evaluate import make_snapshot, ndcg_at_10, run_evaluation


def test_ndcg_at_10_hand_made_rankings():
    assert ndcg_at_10([], {9}) == 0
    assert ndcg_at_10([9, 1, 2], {9}) == 1
    assert ndcg_at_10([1, 2, 9], {9}) == 1 / math.log2(4)


def test_snapshot_removes_future_events(tmp_path):
    source = tmp_path / "source.db"
    connection = sqlite3.connect(source)
    connection.executescript(SCHEMA)
    connection.executemany(
        "INSERT INTO user (id, username, created_at) VALUES (?, ?, ?)",
        [(1, "alice", "2020-01-01 00:00:00"), (2, "bob", "2020-01-01 00:00:00")],
    )
    connection.executemany(
        "INSERT INTO post (id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
        [
            (1, 2, "old", "2020-01-01 00:00:00"),
            (2, 2, "future", "2020-01-03 00:00:00"),
        ],
    )
    connection.executemany(
        "INSERT INTO like (user_id, post_id, created_at) VALUES (?, ?, ?)",
        [(1, 1, "2020-01-01 00:00:00"), (1, 2, "2020-01-03 00:00:00")],
    )
    connection.commit()
    connection.close()

    snapshot = make_snapshot(
        source, datetime(2020, 1, 2, tzinfo=timezone.utc)
    )
    checked = sqlite3.connect(snapshot)
    try:
        assert checked.execute("SELECT COUNT(*) FROM post").fetchone()[0] == 1
        assert checked.execute("SELECT COUNT(*) FROM like").fetchone()[0] == 1
        assert checked.execute(
            "SELECT COUNT(*) FROM like WHERE created_at >= '2020-01-02'"
        ).fetchone()[0] == 0
    finally:
        checked.close()
        gc.collect()
        snapshot.unlink(missing_ok=True)


def test_evaluation_is_deterministic(tmp_path):
    source = tmp_path / "source.db"
    connection = sqlite3.connect(source)
    connection.executescript(SCHEMA)
    connection.executemany(
        "INSERT INTO user (id, username, created_at) VALUES (?, ?, ?)",
        [(1, "alice", "2020-01-01 00:00:00"), (2, "bob", "2020-01-01 00:00:00")],
    )
    connection.executemany(
        "INSERT INTO post (id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
        [(n, 2, str(n), f"2020-01-0{n} 00:00:00") for n in range(1, 6)],
    )
    connection.executemany(
        "INSERT INTO like (user_id, post_id, created_at) VALUES (1, ?, ?)",
        [(n, f"2020-01-0{min(n, 4)} 00:00:00") for n in range(1, 6)],
    )
    connection.commit()
    connection.close()
    cutoff = datetime(2020, 1, 4, tzinfo=timezone.utc)
    assert run_evaluation(source, cutoff, 42).equals(
        run_evaluation(source, cutoff, 42)
    )
