CREATE TABLE IF NOT EXISTS prompt_runs
(
    id UUID,
    campaign_id UUID,
    prompt_id UUID,
    provider_id UUID,
    brand_id UUID,
    prompt_text String,
    prompt_category Enum8(
        'brand_query' = 1,
        'competitor_comparison' = 2,
        'industry_query' = 3,
        'feature_query' = 4,
        'problem_solving' = 5
    ),
    response_text String,
    model String,
    provider_name String,
    latency_ms UInt32,
    input_tokens UInt32 DEFAULT 0,
    output_tokens UInt32 DEFAULT 0,
    status Enum8('success' = 1, 'error' = 2, 'timeout' = 3),
    error_message String DEFAULT '',
    brand_mentioned UInt8 DEFAULT 0,
    competitors_mentioned Array(String) DEFAULT [],
    created_at DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_at)
ORDER BY (created_at, brand_id, provider_id, prompt_id);
