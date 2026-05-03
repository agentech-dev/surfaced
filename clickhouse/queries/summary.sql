-- Overall dashboard metrics for a brand
-- Parameters: brand_id (UUID), days (Int)
SELECT
    count() AS total_runs,
    sum(brand_mentioned) AS total_mentions,
    round(sum(brand_mentioned) / count() * 100, 1) AS overall_mention_rate_pct,
    countIf(prompt_branded) AS branded_runs,
    countIf(NOT prompt_branded) AS unbranded_runs,
    round(sumIf(brand_mentioned, prompt_branded) / greatest(countIf(prompt_branded), 1) * 100, 1) AS branded_mention_rate_pct,
    round(sumIf(brand_mentioned, NOT prompt_branded) / greatest(countIf(NOT prompt_branded), 1) * 100, 1) AS unbranded_mention_rate_pct,
    countIf(recommendation_status IN ('recommended', 'neutral', 'negative')) AS judged_mentions,
    countIf(recommendation_status = 'recommended') AS recommended_mentions,
    countIf(recommendation_status = 'neutral') AS neutral_mentions,
    countIf(recommendation_status = 'negative') AS negative_mentions,
    countIf(recommendation_status = 'judge_failed') AS judge_failed_mentions,
    round(
        countIf(recommendation_status = 'recommended')
        / greatest(countIf(recommendation_status IN ('recommended', 'neutral', 'negative')), 1)
        * 100,
        1
    ) AS recommendation_rate_pct,
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
