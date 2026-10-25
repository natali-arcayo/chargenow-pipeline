CREATE TABLE IF NOT EXISTS curated_tweets (
    day                 DATE,
    run_id              VARCHAR,
    tweet_id            VARCHAR,
    anonymized_user_id  VARCHAR,
    created_at          TIMESTAMPTZ,
    location            VARCHAR,
    follower_count      BIGINT,
    tweet_count         BIGINT,
    hashtags            VARCHAR[],
    is_retweet          BOOLEAN
);