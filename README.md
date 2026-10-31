# InstaKill — Starter Repo

Mini social-media platform. Mandatory backend: Python + FastAPI + SQLite (default) / PostgreSQL (allowed). See the full brief and grading rubric in `masterplan.md` (course root).

What the instructor provides (this starter):

- `app/main.py` — FastAPI hello-world with `GET /health`
- `app/db/database.py` — SQLite bootstrap (creates tables on startup)
- `app/domain/models.py` — `User` / `Post` schema
- `scripts/seed_db.py` — 5-10 synthetic users/posts
- `tests/test_health.py` — test skeleton

What it does **not** provide: the feed, ranking, ML models, search. Those are the team's work, in the following weeks.

## Running it

```bash
pip install -e .
uvicorn app.main:app --reload
# other terminal:
curl localhost:8000/health

python scripts/seed_db.py
pytest
```

## Semantic search

Week 3 adds `GET /search?q=<query>&limit=<1..20>`. Run the seed script before
searching if the database does not already contain posts:

```bash
python scripts/seed_db.py
```

The first search lazily loads `sentence-transformers/all-MiniLM-L6-v2`, reads
the posts through the repository boundary, and builds an in-memory embedding
index. New posts will require an explicit index refresh; a future CRUD service
can provide that refresh rather than coupling SQLite writes to retrieval.

## Feed (Week 4)

`GET /feed?user_id=<int>&limit=<1..50>&strategy=for_you|chronological`
returns a deterministic feed. `for_you` excludes the user's own and already
liked posts, then ranks posts using:

```text
score = 0.5 * freshness + 0.3 * affinity + 0.2 * popularity
freshness = exp(-age_hours / 24)
affinity = 1 when the author is followed, otherwise 0
popularity = log(1 + like_count), normalized within the candidates
```

Users who follow nobody get all posts from other authors as candidates. The
chronological strategy uses newest `created_at`; ties use ascending `post_id`.
The feed's ranker uses a heap, so one request costs `O(C log k)` time and
`O(k)` ranking memory for `C` candidates and limit `k` (candidate reads and
signal calculation add `O(C)`). Like counts would be the first part to
precompute for a larger database.

## Milestones (see masterplan.md for full details)

W1 Repo+API → W3 CRUD+DB → W4 Feed v0 → W7 Baseline+eval plan → W9 ML+pretrained feature → W11 Profile+optimize → W13 Feature freeze+E2E → W14 Red-team+Demo Day.

At the end of each week: a demonstrable commit/tag.
