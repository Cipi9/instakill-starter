# InstaKill offline evaluation protocol

## Question

We measure which feed strategy places posts that a user later likes in its top 10,
how large the difference is, and whether the result changes for users with
different activity levels. The evaluated strategies are `chronological`,
`popularity`, `for_you`, and `learned`.

## Cut-off and snapshot

The default cut-off is the timestamp at which 80% of recorded likes have
happened; `--cutoff` can provide an explicit ISO timestamp. The evaluator copies
the database and removes likes, posts, and timestamped follows at or after the
cut-off. Every feed request is then made against that historical snapshot with
`now` set to the cut-off, so future data cannot affect the ranking.

## Users

We evaluate users with at least three likes before the cut-off and at least one
later like on a post that existed in the snapshot. Each user contributes one
question per strategy.

## Candidates and strategies

Candidates come from the same `FeedService` used by `GET /feed`: followed
authors, or all other authors for a cold-start user, excluding the user's own
posts and posts already liked before the cut-off. `popularity` is an
evaluation-only scorer over that same candidate set; it is not added to the API.

## Relevance and metric

Relevant posts are the snapshot posts the user liked after the cut-off. We use
NDCG@10: `DCG = sum(relevance / log2(position + 2))`, divided by the ideal DCG
for all relevant posts in the first ten positions. Scores are between zero and
one.

## Uncertainty and slices

The reports use a fixed-seed bootstrap over users. Slice results use the
activity groups `new (<10 likes)`, `casual (10-49)`, `regular (50-199)`, and
`power (200+)`. The learned strategy is compared with the best baseline for
each slice using a paired bootstrap interval.

## Known limitations

The learned model may have seen future data: it was trained on MovieLens likes
through its lab validation cut-off, while this database uses the same ratings.
The report's database and cut-off metadata make the overlap auditable, but the
learned score may therefore be optimistic.

MovieLens is not InstaKill's population: it contains mostly old movies rated
years later, while a social feed is dominated by posts from the last few days.
The activity slices show which strategy works in this proxy population, not
which strategy will win on a production social network.

These results are not comparable to the Week 5/7 lab scores: the lab hides one
like among 99 sampled candidates, while this evaluation ranks the complete
candidate set and counts every later relevant like.
