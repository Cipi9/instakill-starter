"""Application orchestration for feed strategies."""
from datetime import datetime, timezone
from math import log1p

from app.domain.models import Post
from app.feed.ranking import (
    FeedSignals,
    FeedWeights,
    RankedPost,
    freshness_signal,
    rank_feed,
)
from app.feed.repository import FeedRepository


class UnknownUserError(ValueError):
    """Raised when a feed user does not exist."""


class FeedService:
    def __init__(self, repository: FeedRepository):
        self._repository = repository

    def get_feed(
        self, user_id: int, limit: int, strategy: str
    ) -> list[RankedPost | Post]:
        if not self._repository.user_exists(user_id):
            raise UnknownUserError("user_id does not exist")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        if strategy not in {"for_you", "chronological"}:
            raise ValueError("strategy must be for_you or chronological")

        liked_ids = self._repository.liked_post_ids(user_id)
        followed_ids = self._repository.followed_author_ids(user_id)
        candidates = list(
            self._repository.list_candidates(user_id, followed_ids, liked_ids)
        )
        if strategy == "chronological":
            return sorted(
                candidates,
                key=lambda post: (-self._created_at(post).timestamp(), post.id or 0),
            )[:limit]

        now = datetime.now(timezone.utc)
        counts = self._repository.like_counts([post.id for post in candidates])
        signals = {
            post.id: FeedSignals(
                freshness=freshness_signal(self._created_at(post), now),
                affinity=1.0 if post.user_id in followed_ids else 0.0,
                popularity=log1p(counts.get(post.id, 0)),
            )
            for post in candidates
            if post.id is not None
        }
        max_popularity = max(
            (signal.popularity for signal in signals.values()), default=0.0
        )
        if max_popularity:
            signals = {
                post_id: FeedSignals(
                    signal.freshness,
                    signal.affinity,
                    signal.popularity / max_popularity,
                )
                for post_id, signal in signals.items()
            }
        return rank_feed(candidates, signals, now, FeedWeights(), limit)

    @staticmethod
    def _created_at(post: Post) -> datetime:
        if post.created_at is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if isinstance(post.created_at, datetime):
            value = post.created_at
        else:
            value = datetime.fromisoformat(str(post.created_at))
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
