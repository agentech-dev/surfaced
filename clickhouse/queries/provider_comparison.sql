-- Compare brand visibility across providers
-- Parameters: brand_id (UUID), days (Int)
SELECT
    provider_name,
    model,
    prompt_branded,
    count() AS total_runs,
    sum(brand_mentioned) AS mentions,
    round(sum(brand_mentioned) / count() * 100, 1) AS mention_rate_pct,
    round(avg(latency_ms)) AS avg_latency_ms,
    round(avg(input_tokens + output_tokens)) AS avg_tokens
FROM answers
WHERE brand_id = {brand_id:UUID}
  AND created_at >= now() - INTERVAL {days:Int32} DAY
  AND status = 'success'
GROUP BY provider_name, model, prompt_branded
ORDER BY mention_rate_pct DESC;
