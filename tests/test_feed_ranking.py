from datetime import datetime, timezone

from app.domain.models import Post
from app.feed.ranking import FeedSignals, FeedWeights, rank_feed


def test_rank_feed_uses_score_then_ascending_id_without_mutating_inputs():
    posts = [
        Post(id=3, user_id=1, content="third"),
        Post(id=1, user_id=1, content="first"),
        Post(id=2, user_id=1, content="second"),
    ]
    original = list(posts)
    signals = {
        1: FeedSignals(1, 0, 0),
        2: FeedSignals(1, 0, 0),
        3: FeedSignals(0, 0, 0),
    }

    results = rank_feed(
        posts,
        signals,
        datetime.now(timezone.utc),
        FeedWeights(freshness=1, affinity=0, popularity=0),
        limit=2,
    )

    assert [result.post.id for result in results] == [1, 2]
    assert posts == original
    assert list(signals) == [1, 2, 3]
