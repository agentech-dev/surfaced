CREATE TABLE IF NOT EXISTS canonical_positions
(
    id UUID,
    brand_id UUID,
    topic LowCardinality(String),
    statement String,
    is_active UInt8 DEFAULT 1,
    created_at DateTime64(3) DEFAULT now64(3),
    updated_at DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree
ORDER BY (brand_id, id);
