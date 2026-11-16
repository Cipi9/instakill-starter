"""Offline, time-split evaluation of InstaKill feed strategies."""
from __future__ import annotations

import argparse
import base64
import gc
import hashlib
import io
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.db.database import DB_PATH, init_db
from app.feed.repository import FeedRepository
from app.feed.service import FeedService

STRATEGIES = ("chronological", "popularity", "for_you", "learned")
BASELINES = ("chronological", "popularity", "for_you")
GROUP_ORDER = ("new (<10 likes)", "casual (10-49)", "regular (50-199)", "power (200+)")
DAY = 86400


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def effective_like_timestamp(row: sqlite3.Row) -> str:
    return row["like_created_at"] or row["post_created_at"]


def choose_cutoff(db_path: Path, cutoff: str | None) -> datetime:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT l.created_at AS like_created_at, p.created_at AS post_created_at "
            "FROM like l JOIN post p ON p.id = l.post_id"
        ).fetchall()
    if not rows:
        raise ValueError("the database contains no likes to evaluate")
    values = sorted(parse_timestamp(row[0] or row[1]) for row in rows)
    if cutoff:
        return parse_timestamp(cutoff)
    return values[min(len(values) - 1, int(np.ceil(len(values) * 0.8)) - 1)]


def make_snapshot(db_path: Path, cutoff: datetime) -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    snapshot = Path(handle.name)
    shutil.copy2(db_path, snapshot)
    cutoff_text = cutoff.isoformat(sep=" ")
    with sqlite3.connect(snapshot) as connection:
        connection.execute(
            "DELETE FROM like WHERE post_id IN ("
            "SELECT p.id FROM post p WHERE p.created_at >= ?"
            ") OR COALESCE(created_at, ("
            "SELECT p.created_at FROM post p WHERE p.id = like.post_id"
            ")) >= ?",
            (cutoff_text, cutoff_text),
        )
        connection.execute("DELETE FROM post WHERE created_at >= ?", (cutoff_text,))
        follow_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(follow)")
        }
        if "created_at" in follow_columns:
            connection.execute("DELETE FROM follow WHERE created_at >= ?", (cutoff_text,))
        connection.commit()
    return snapshot


def user_groups(db_path: Path, cutoff: datetime) -> dict[int, str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT l.user_id, COUNT(*) FROM like l JOIN post p ON p.id = l.post_id "
            "WHERE COALESCE(l.created_at, p.created_at) < ? GROUP BY l.user_id",
            (cutoff.isoformat(sep=" "),),
        ).fetchall()
    groups = {}
    for user_id, count in rows:
        group = (
            "new (<10 likes)" if count < 10 else
            "casual (10-49)" if count < 50 else
            "regular (50-199)" if count < 200 else "power (200+)"
        )
        groups[int(user_id)] = group
    return groups


def evaluation_users(db_path: Path, cutoff: datetime) -> dict[int, set[int]]:
    cutoff_text = cutoff.isoformat(sep=" ")
    with sqlite3.connect(db_path) as connection:
        before = connection.execute(
            "SELECT l.user_id, COUNT(*) FROM like l JOIN post p ON p.id = l.post_id "
            "WHERE COALESCE(l.created_at, p.created_at) < ? GROUP BY l.user_id "
            "HAVING COUNT(*) >= 3",
            (cutoff_text,),
        ).fetchall()
        after = connection.execute(
            "SELECT l.user_id, l.post_id FROM like l JOIN post p ON p.id = l.post_id "
            "WHERE COALESCE(l.created_at, p.created_at) >= ? AND p.created_at < ?",
            (cutoff_text, cutoff_text),
        ).fetchall()
    eligible = {int(user_id) for user_id, _ in before}
    relevant: dict[int, set[int]] = {user_id: set() for user_id in eligible}
    for user_id, post_id in after:
        if user_id in relevant:
            relevant[user_id].add(int(post_id))
    return {user_id: posts for user_id, posts in relevant.items() if posts}


def ndcg_at_10(ranked_ids: list[int], relevant_ids: set[int]) -> float:
    if not relevant_ids:
        return 0.0
    dcg = sum(
        1 / np.log2(index + 2)
        for index, post_id in enumerate(ranked_ids[:10])
        if post_id in relevant_ids
    )
    ideal_hits = min(10, len(relevant_ids))
    ideal = sum(1 / np.log2(index + 2) for index in range(ideal_hits))
    return float(dcg / ideal) if ideal else 0.0


def bootstrap_interval(
    values: np.ndarray, seed: int, samples: int = 2000
) -> tuple[float, float, float]:
    if len(values) == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(values), size=(samples, len(values)))
    means = values[draws].mean(axis=1)
    return float(values.mean()), float(np.quantile(means, 0.025)), float(
        np.quantile(means, 0.975)
    )


def service_post_ids(service: FeedService, user_id: int, strategy: str, cutoff: datetime) -> list[int]:
    results = service.get_feed(user_id, 10, strategy, now=cutoff)
    return [result.post.id if hasattr(result, "post") else result.id for result in results]


def popularity_post_ids(
    repository: FeedRepository, user_id: int, limit: int = 10
) -> list[int]:
    liked = repository.liked_post_ids(user_id)
    followed = repository.followed_author_ids(user_id)
    candidates = repository.list_candidates(user_id, followed, liked)
    counts = repository.like_counts([post.id for post in candidates if post.id is not None])
    return [
        post.id
        for post in sorted(
            candidates,
            key=lambda post: (-counts.get(post.id, 0), post.id or 0),
        )[:limit]
        if post.id is not None
    ]


def run_evaluation(
    db_path: Path,
    cutoff: datetime,
    seed: int,
    source_db_path: Path | None = None,
) -> pd.DataFrame:
    source_db_path = source_db_path or db_path
    groups = user_groups(source_db_path, cutoff)
    relevant = evaluation_users(source_db_path, cutoff)
    repository = FeedRepository(str(db_path))
    service = FeedService(repository)
    rows = []
    for user_id in sorted(relevant):
        for strategy in STRATEGIES:
            ranked = (
                popularity_post_ids(repository, user_id)
                if strategy == "popularity"
                else service_post_ids(service, user_id, strategy, cutoff)
            )
            rows.append(
                {
                    "user_id": user_id,
                    "strategy": strategy,
                    "ndcg_at_10": ndcg_at_10(ranked, relevant[user_id]),
                    "n_relevant": len(relevant[user_id]),
                    "user_group": groups.get(user_id, "new (<10 likes)"),
                }
            )
    columns = ["user_id", "strategy", "ndcg_at_10", "n_relevant", "user_group"]
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["user_id", "strategy"]
    ).reset_index(drop=True)


def verdict(value: float, low: float, high: float) -> str:
    return "wins" if low > 0 else "loses" if high < 0 else "unclear"


def baseline_markdown(
    results: pd.DataFrame, cutoff: datetime, seed: int, db_path: Path
) -> str:
    lines = ["# Feed evaluation", "", "| strategy | mean NDCG@10 | 95% interval | users |", "|---|---:|---:|---:|"]
    for strategy in STRATEGIES:
        mean, low, high = bootstrap_interval(
            results.loc[results.strategy == strategy, "ndcg_at_10"].to_numpy(),
            seed + STRATEGIES.index(strategy),
        )
        count = (results.strategy == strategy).sum()
        lines.append(f"| {strategy} | {mean:.4f} | [{low:.4f}, {high:.4f}] | {count} |")
    lines += ["", "## learned minus best baseline", "", "| slice | diff | 95% interval | verdict |", "|---|---:|---:|---|"]
    for group in ["overall", *GROUP_ORDER]:
        subset = results if group == "overall" else results[results.user_group == group]
        if subset.empty:
            continue
        pivot = subset.pivot(index="user_id", columns="strategy", values="ndcg_at_10")
        best = pivot[list(BASELINES)].max(axis=1)
        diff = (pivot["learned"] - best).to_numpy()
        mean, low, high = bootstrap_interval(diff, seed + 100 + len(lines))
        lines.append(f"| {group} | {mean:+.4f} | [{low:+.4f}, {high:+.4f}] | {verdict(mean, low, high)} |")
    fingerprint = hashlib.sha256(db_path.read_bytes()).hexdigest()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip() or "unknown"
    lines += [
        "",
        "## Run metadata",
        f"- cut-off: `{cutoff.isoformat()}`",
        f"- seed: `{seed}`",
        f"- users: `{results.user_id.nunique()}`",
        f"- database fingerprint: `{fingerprint}`",
        f"- git commit: `{commit}`",
    ]
    return "\n".join(lines) + "\n"


def dashboard_html(results: pd.DataFrame, cutoff: datetime, seed: int) -> str:
    colors = {"chronological": "#4472c4", "popularity": "#70ad47", "for_you": "#ed7d31", "learned": "#a64d79"}
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    means = [results.loc[results.strategy == s, "ndcg_at_10"].mean() for s in STRATEGIES]
    intervals = [bootstrap_interval(results.loc[results.strategy == s, "ndcg_at_10"].to_numpy(), seed + i)[1:] for i, s in enumerate(STRATEGIES)]
    axes[0].bar(STRATEGIES, means, color=[colors[s] for s in STRATEGIES], yerr=np.array(means) - np.array([x[0] for x in intervals]), capsize=4)
    axes[0].set(title="Which strategy has the highest NDCG@10?", ylabel="mean NDCG@10")
    axes[0].set_ylim(bottom=0)
    slice_rows = []
    for group in GROUP_ORDER:
        subset = results[results.user_group == group]
        if subset.empty:
            continue
        pivot = subset.pivot(index="user_id", columns="strategy", values="ndcg_at_10")
        diff = pivot["learned"] - pivot[list(BASELINES)].max(axis=1)
        slice_rows.append((group, diff.mean()))
    axes[1].bar([x[0] for x in slice_rows], [x[1] for x in slice_rows], color=["#c0504d" if x[1] < 0 else "#8064a2" for x in slice_rows])
    axes[1].axhline(0, color="black", linewidth=1)
    axes[1].set(title="Where does learned beat the best baseline?", ylabel="NDCG difference")
    axes[1].tick_params(axis="x", rotation=35)
    axes[2].scatter(results[results.strategy == "learned"]["n_relevant"], results[results.strategy == "learned"]["ndcg_at_10"], color=colors["learned"])
    axes[2].set(title="Does performance change with relevance count?", xlabel="relevant posts after cut-off", ylabel="NDCG@10")
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>InstaKill evaluation</title>"
        "<style>body{font-family:system-ui;margin:2rem}img{max-width:100%}</style></head><body>"
        f"<h1>InstaKill feed evaluation</h1><p>Cut-off: {cutoff.isoformat()} · seed: {seed}</p>"
        f"<img alt='Evaluation charts' src='data:image/png;base64,{encoded}'></body></html>"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--cutoff")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("reports"))
    args = parser.parse_args()
    if args.db.resolve() == DB_PATH.resolve():
        init_db()
    cutoff = choose_cutoff(args.db, args.cutoff)
    snapshot = make_snapshot(args.db, cutoff)
    try:
        results = run_evaluation(snapshot, cutoff, args.seed, args.db)
    finally:
        gc.collect()
        snapshot.unlink(missing_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.out / "eval_results.csv", index=False, lineterminator="\n")
    (args.out / "baseline_table.md").write_text(
        baseline_markdown(results, cutoff, args.seed, args.db), encoding="utf-8"
    )
    (args.out / "dashboard.html").write_text(
        dashboard_html(results, cutoff, args.seed), encoding="utf-8"
    )
    print(f"cut-off: {cutoff.isoformat()}")
    print(f"evaluated {results.user_id.nunique()} users; reports written to {args.out}")


if __name__ == "__main__":
    main()
