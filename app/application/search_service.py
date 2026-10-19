"""Application service coordinating semantic post search."""
from dataclasses import dataclass

from app.search.encoder import TextEncoder
from app.search.repository import PostRepository
from app.search.retrieval import IndexedPost, ScoredPost, top_k_by_cosine


@dataclass(frozen=True)
class SearchResponse:
    query: str
    results: list[ScoredPost]


class SearchService:
    """Coordinates encoding, post retrieval, and pure vector ranking."""

    def __init__(self, repository: PostRepository, encoder: TextEncoder):
        self._repository = repository
        self._encoder = encoder
        self._index: list[IndexedPost] | None = None

    def search(self, query: str, limit: int) -> SearchResponse:
        if not query.strip():
            raise ValueError("q must not be empty")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")

        index = self._get_index()
        query_vector = self._encoder.encode([query])[0]
        return SearchResponse(
            query=query,
            results=top_k_by_cosine(query_vector, index, limit),
        )

    def _get_index(self) -> list[IndexedPost]:
        if self._index is None:
            posts = self._repository.list_posts()
            vectors = self._encoder.encode([post.content for post in posts])
            self._index = [
                IndexedPost(post, vector) for post, vector in zip(posts, vectors)
            ]
        return self._index
