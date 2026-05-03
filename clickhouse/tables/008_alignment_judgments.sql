CREATE TABLE IF NOT EXISTS alignment_judgments
(
    id UUID,
    answer_id UUID,
    run_id UUID,
    prompt_id UUID,
    provider_id UUID,
    brand_id UUID,
    alignment_position_id UUID,
    judge_model LowCardinality(String),
    alignment_status Enum8(
        'aligned' = 1,
        'partial' = 2,
        'misaligned' = 3,
        'silent' = 4,
        'judge_failed' = 5
    ),
    rationale String DEFAULT '',
    raw_output String DEFAULT '',
    error_message String DEFAULT '',
    latency_ms UInt32 DEFAULT 0,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (brand_id, toDate(created_at), alignment_position_id, answer_id);
