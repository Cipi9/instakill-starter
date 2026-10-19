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
