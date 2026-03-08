CREATE TABLE IF NOT EXISTS brand_mention_daily
(
    day Date,
    brand_id UUID,
    provider_name String,
    prompt_category Enum8(
        'brand_query' = 1,
        'competitor_comparison' = 2,
        'industry_query' = 3,
        'feature_query' = 4,
        'problem_solving' = 5
    ),
    total_runs UInt64,
    mentions UInt64,
    avg_latency_ms Float64
)
ENGINE = SummingMergeTree
ORDER BY (day, brand_id, provider_name, prompt_category);

CREATE MATERIALIZED VIEW IF NOT EXISTS brand_mention_daily_mv
TO brand_mention_daily
AS
SELECT
    toDate(created_at) AS day,
    brand_id,
    provider_name,
    prompt_category,
    count() AS total_runs,
    sum(brand_mentioned) AS mentions,
    avg(latency_ms) AS avg_latency_ms
FROM answers
WHERE status = 'success'
GROUP BY day, brand_id, provider_name, prompt_category;
