CREATE TABLE IF NOT EXISTS recommendation_judgments
(
    id UUID,
    answer_id UUID,
    run_id UUID,
    prompt_id UUID,
    provider_id UUID,
    brand_id UUID,
    judge_model LowCardinality(String),
    recommendation_status Enum8(
        'recommended' = 1,
        'neutral' = 2,
        'negative' = 3,
        'judge_failed' = 4
    ),
    raw_output String DEFAULT '',
    error_message String DEFAULT '',
    latency_ms UInt32 DEFAULT 0,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (brand_id, toDate(created_at), answer_id);
