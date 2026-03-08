-- Overall dashboard metrics for a brand
-- Parameters: brand_id (UUID), days (Int)
SELECT
    count() AS total_runs,
    sum(brand_mentioned) AS total_mentions,
    round(sum(brand_mentioned) / count() * 100, 1) AS overall_mention_rate_pct,
    uniq(prompt_id) AS unique_prompts,
    uniq(provider_name) AS providers_used,
    round(avg(latency_ms)) AS avg_latency_ms,
    min(created_at) AS earliest_run,
    max(created_at) AS latest_run,
    length(arrayDistinct(arrayFlatten(groupArray(competitors_mentioned)))) AS unique_competitors_mentioned
FROM answers
WHERE brand_id = {brand_id:UUID}
  AND created_at >= now() - INTERVAL {days:Int32} DAY
  AND status = 'success';
