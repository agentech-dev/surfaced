CREATE TABLE IF NOT EXISTS providers
(
    id UUID,
    name String,
    provider_type String,
    execution_mode Enum8('api' = 1, 'cli' = 2),
    model String,
    config String DEFAULT '{}',
    rate_limit_rpm UInt32 DEFAULT 60,
    is_active UInt8 DEFAULT 1,
    created_at DateTime64(3) DEFAULT now64(3),
    updated_at DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id;
