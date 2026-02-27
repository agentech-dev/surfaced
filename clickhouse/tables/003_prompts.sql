CREATE TABLE IF NOT EXISTS prompts
(
    id UUID,
    text String,
    category Enum8(
        'brand_query' = 1,
        'competitor_comparison' = 2,
        'industry_query' = 3,
        'feature_query' = 4,
        'problem_solving' = 5
    ),
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
