-- Response stability for specific prompts over time
-- Parameters: brand_id (UUID), days (Int)
SELECT
    prompt_id,
    any(prompt_text) AS prompt_text_sample,
    count() AS runs,
    sum(brand_mentioned) AS mentions,
    round(sum(brand_mentioned) / count() * 100, 1) AS mention_rate_pct,
    min(toDate(created_at)) AS first_run,
    max(toDate(created_at)) AS last_run
FROM answers
WHERE brand_id = {brand_id:UUID}
  AND created_at >= now() - INTERVAL {days:Int32} DAY
  AND status = 'success'
GROUP BY prompt_id
ORDER BY runs DESC;
