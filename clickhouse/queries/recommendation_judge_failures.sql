-- Recent recommendation judge failures with raw output and error detail
-- Parameters: brand_id (UUID), days (Int)
SELECT
    j.created_at,
    j.judge_model,
    j.recommendation_status,
    j.raw_output,
    j.error_message,
    j.latency_ms,
    a.provider_name,
    a.prompt_category,
    a.prompt_text,
    a.response_text
FROM recommendation_judgments AS j
INNER JOIN answers AS a ON a.id = j.answer_id
WHERE j.brand_id = {brand_id:UUID}
  AND j.created_at >= now() - INTERVAL {days:Int32} DAY
  AND j.recommendation_status = 'judge_failed'
ORDER BY j.created_at DESC;
