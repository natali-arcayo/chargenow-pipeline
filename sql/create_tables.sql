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
CREATE TABLE IF NOT EXISTS run_registry (
    run_id         VARCHAR,
    run_date       DATE,
    mode           VARCHAR,
    status         VARCHAR,
    rows_loaded    BIGINT,
    finished_at    TIMESTAMPTZ,
    error_message  VARCHAR
);