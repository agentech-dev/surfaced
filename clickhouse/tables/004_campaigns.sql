CREATE TABLE IF NOT EXISTS campaigns
(
    id UUID,
    name String,
    status Enum8('running' = 1, 'completed' = 2, 'failed' = 3, 'cancelled' = 4),
    filters String DEFAULT '{}',
    total_prompts UInt32 DEFAULT 0,
    completed_prompts UInt32 DEFAULT 0,
    started_at DateTime64(3) DEFAULT now64(3),
    finished_at DateTime64(3) DEFAULT toDateTime64('1970-01-01 00:00:00.000', 3),
    created_at DateTime64(3) DEFAULT now64(3),
    updated_at DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id;
