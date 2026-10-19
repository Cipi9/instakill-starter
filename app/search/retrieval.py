"""Pure vector retrieval operations."""
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from app.domain.models import Post


@dataclass(frozen=True)
class IndexedPost:
    post: Post
    vector: NDArray[np.float32]


@dataclass(frozen=True)
class ScoredPost:
    post: Post
    score: float


def top_k_by_cosine(
    query_vector: NDArray[np.float32],
    indexed_posts: list[IndexedPost],
    limit: int,
) -> list[ScoredPost]:
    """Return the deterministic top-k posts ranked by cosine similarity."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    query_norm = float(np.linalg.norm(query_vector))
    scored: list[ScoredPost] = []
    for indexed_post in indexed_posts:
        post_norm = float(np.linalg.norm(indexed_post.vector))
        score = 0.0
        if query_norm and post_norm:
            score = float(
                np.dot(query_vector, indexed_post.vector) / (query_norm * post_norm)
            )
        scored.append(ScoredPost(indexed_post.post, score))

    scored.sort(key=lambda item: (-item.score, item.post.id or 0))
    return scored[:limit]
