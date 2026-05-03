-- Brand mention rate over time
-- Parameters: brand_id (UUID), days (Int)
SELECT
    toDate(created_at) AS day,
    prompt_branded,
    count() AS total_runs,
    sum(brand_mentioned) AS mentions,
    round(sum(brand_mentioned) / count() * 100, 1) AS mention_rate_pct
FROM answers
WHERE brand_id = {brand_id:UUID}
  AND created_at >= now() - INTERVAL {days:Int32} DAY
  AND status = 'success'
GROUP BY day, prompt_branded
ORDER BY day, prompt_branded;
