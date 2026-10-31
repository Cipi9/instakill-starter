"""Pure, deterministic ranking for the personalised feed."""
from dataclasses import dataclass
from datetime import datetime
import heapq
from math import exp
from typing import Mapping, Sequence

from app.domain.models import Post


@dataclass(frozen=True)
class FeedSignals:
    freshness: float
    affinity: float
    popularity: float


@dataclass(frozen=True)
class FeedWeights:
    freshness: float = 0.5
    affinity: float = 0.3
    popularity: float = 0.2


@dataclass(frozen=True)
class RankedPost:
    post: Post
    score: float


def freshness_signal(created_at: datetime, now: datetime) -> float:
    age_hours = max(0.0, (now - created_at).total_seconds() / 3600)
    return exp(-age_hours / 24)


def rank_feed(
    candidates: Sequence[Post],
    signals: Mapping[int, FeedSignals],
    now: datetime,
    weights: FeedWeights = FeedWeights(),
    limit: int = 20,
) -> list[RankedPost]:
    """Return top-k posts without changing candidates or signals.

    The score is a weighted sum of freshness, author affinity, and popularity.
    ``now`` is explicit so this function remains deterministic and testable.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")

    del now  # Signal values are supplied by the orchestration boundary.
    heap: list[tuple[float, int, RankedPost]] = []
    for post in candidates:
        if post.id is None:
            raise ValueError("feed candidates must have ids")
        post_signals = signals[post.id]
        score = (
            weights.freshness * post_signals.freshness
            + weights.affinity * post_signals.affinity
            + weights.popularity * post_signals.popularity
        )
        ranked = RankedPost(post, float(score))
        entry = (ranked.score, -post.id, ranked)
        if len(heap) < limit:
            heapq.heappush(heap, entry)
        elif entry[:2] > heap[0][:2]:
            heapq.heapreplace(heap, entry)

    return [
        entry[2]
        for entry in sorted(heap, key=lambda item: (-item[0], -item[1]))
    ]
