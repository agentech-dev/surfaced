CREATE TABLE IF NOT EXISTS answers
(
    id UUID,
    run_id UUID,
    prompt_id UUID,
    provider_id UUID,
    brand_id UUID,
    prompt_text String,
    prompt_category LowCardinality(String),
    prompt_branded Bool DEFAULT false,
    response_text String,
    model String,
    provider_name String,
    latency_ms UInt32,
    input_tokens UInt32 DEFAULT 0,
    output_tokens UInt32 DEFAULT 0,
    status Enum8('success' = 1, 'error' = 2, 'timeout' = 3),
    error_message String DEFAULT '',
    brand_mentioned UInt8 DEFAULT 0,
    recommendation_status Enum8(
        'not_mentioned' = 1,
        'not_judged' = 2,
        'recommended' = 3,
        'neutral' = 4,
        'negative' = 5,
        'judge_failed' = 6
    ) DEFAULT 'not_mentioned',
    alignment_status Enum8(
        'not_applicable' = 1,
        'aligned' = 2,
        'partial' = 3,
        'misaligned' = 4,
        'silent' = 5,
        'judge_failed' = 6
    ) DEFAULT 'not_applicable',
    alignment_position_id UUID DEFAULT '00000000-0000-0000-0000-000000000000',
    alignment_rationale String DEFAULT '',
    competitors_mentioned Array(String) DEFAULT [],
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (brand_id, toDate(created_at));
