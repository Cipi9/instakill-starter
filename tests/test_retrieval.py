import numpy as np

from app.domain.models import Post
from app.search.retrieval import IndexedPost, top_k_by_cosine


def test_top_k_by_cosine_orders_by_score_then_post_id():
    posts = [
        IndexedPost(Post(id=3, user_id=1, content="third"), np.array([1, 0])),
        IndexedPost(Post(id=1, user_id=1, content="first"), np.array([1, 0])),
        IndexedPost(Post(id=2, user_id=1, content="second"), np.array([0, 1])),
    ]

    results = top_k_by_cosine(np.array([1, 0]), posts, limit=3)

    assert [result.post.id for result in results] == [1, 3, 2]
    assert results[0].score == results[1].score == 1.0
