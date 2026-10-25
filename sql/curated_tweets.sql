-- Curated tweets for one day: one row per tweet, the 7 requested fields.
-- Raw is read with a DECLARED schema: missing optional fields become NULL.

WITH raw AS (
    SELECT response
    FROM read_json(
        'data/raw/date=2026-10-20/response.json',
        columns = {
            response: 'STRUCT(
                data STRUCT(
                    id VARCHAR,
                    created_at TIMESTAMPTZ,
                    author_id VARCHAR,
                    entities STRUCT(hashtags STRUCT(tag VARCHAR)[]),
                    referenced_tweets STRUCT("type" VARCHAR, id VARCHAR)[]
                )[],
                includes STRUCT(
                    users STRUCT(
                        id VARCHAR,
                        location VARCHAR,
                        public_metrics STRUCT(followers_count BIGINT, tweet_count BIGINT)
                    )[]
                ),
                meta STRUCT(result_count BIGINT)
            )'
        }
    )
),

tweets AS (
    SELECT
        t.id                AS tweet_id,
        t.created_at        AS created_at,
        t.author_id         AS author_id,
        t.entities.hashtags AS hashtag_list,
        t.referenced_tweets AS referenced_tweets
    FROM (SELECT unnest(response.data) AS t FROM raw)
),

users AS (
    SELECT
        u.id                             AS user_id,
        u.location                       AS location,
        u.public_metrics.followers_count AS follower_count,
        u.public_metrics.tweet_count     AS tweet_count
    FROM (SELECT unnest(response.includes.users) AS u FROM raw)
)

SELECT
    tweets.tweet_id,
    sha256($anon_key || tweets.author_id) AS anonymized_user_id,
    tweets.created_at,
    users.location,
    users.follower_count,
    users.tweet_count,
    coalesce(list_transform(tweets.hashtag_list, lambda h: h.tag), []) AS hashtags,
    coalesce(list_contains(list_transform(tweets.referenced_tweets, lambda r: r."type"), 'retweeted'), false) AS is_retweet
FROM tweets
LEFT JOIN users ON users.user_id = tweets.author_id
ORDER BY tweets.created_at;