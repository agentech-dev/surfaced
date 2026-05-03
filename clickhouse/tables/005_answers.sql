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
    competitors_mentioned Array(String) DEFAULT [],
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (brand_id, toDate(created_at));
