CREATE TABLE IF NOT EXISTS prompts
(
    id UUID,
    text String,
    category LowCardinality(String),
    branded Bool DEFAULT false,
    recommendation_enabled Bool DEFAULT true,
    alignment_enabled Bool DEFAULT false,
    alignment_position_id UUID DEFAULT '00000000-0000-0000-0000-000000000000',
    tags Array(String) DEFAULT [],
    brand_id UUID,
    is_template UInt8 DEFAULT 0,
    variables Array(String) DEFAULT [],
    is_active UInt8 DEFAULT 1,
    created_at DateTime64(3) DEFAULT now64(3),
    updated_at DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id;
