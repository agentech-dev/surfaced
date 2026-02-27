CREATE TABLE IF NOT EXISTS brands
(
    id UUID,
    name String,
    domain String DEFAULT '',
    description String DEFAULT '',
    aliases Array(String) DEFAULT [],
    competitors Array(String) DEFAULT [],
    is_active UInt8 DEFAULT 1,
    created_at DateTime64(3) DEFAULT now64(3),
    updated_at DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id;
