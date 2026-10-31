# API contract

## Semantic post search

`GET /search?q=<non-empty query>&limit=<1..20>`

The endpoint searches the seeded posts using embeddings from the pretrained
`sentence-transformers/all-MiniLM-L6-v2` encoder.

### Successful response

Status: `200 OK`

```json
{
  "query": "similarity search",
  "results": [
    {
      "post_id": 2,
      "user_id": 1,
      "content": "does anyone else think the feed is chronological only? boring",
      "score": 0.7312
    }
  ]
}
```

Results contain at most `limit` posts, are ordered by descending cosine
similarity, and use ascending `post_id` to break equal scores.

### Validation and error cases

- `422 Unprocessable Entity`: `q` is missing or empty, or `limit` is not an
  integer from `1` through `20`.
- `500 Internal Server Error`: an unexpected database or encoder failure. The
  response must not expose implementation details.

The HTTP adapter only parses parameters and formats responses. SQLite access is
in `app/search/repository.py`, encoding is behind
`SentenceTransformerEncoder`, and ranking is the pure `top_k_by_cosine`
function in `app/search/retrieval.py`.

## Feed

`GET /feed?user_id=<int>&limit=<1..50>&strategy=for_you|chronological`

`user_id` is required. `limit` defaults to `20`; `strategy` defaults to
`for_you`. `for_you` returns posts from followed authors, or all other authors
when the user follows nobody, excluding the user's own and already-liked
posts. It includes a numeric `score` based on freshness, followed-author
affinity, and normalized like popularity. `chronological` uses the same
candidate policy and orders by newest `created_at`; equal timestamps use
ascending `post_id`.

### Successful response

```json
{
  "user_id": 1,
  "strategy": "for_you",
  "results": [
    {
      "post_id": 3,
      "user_id": 2,
      "content": "just shipped a cosine similarity search, feels great",
      "created_at": "2026-10-26T17:00:00",
      "score": 0.83
    }
  ]
}
```

Unknown users return `404`. Missing or invalid parameters return `422`.
