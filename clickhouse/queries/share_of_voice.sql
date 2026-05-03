-- Brand vs competitor mention share by category
-- Parameters: brand_id (UUID), days (Int)
SELECT
    prompt_category,
    prompt_branded,
    count() AS total_runs,
    sum(brand_mentioned) AS brand_mentions,
    round(sum(brand_mentioned) / count() * 100, 1) AS brand_mention_pct,
    length(arrayFilter(x -> x != '', arrayFlatten(groupArray(competitors_mentioned)))) AS competitor_mentions
FROM answers
WHERE brand_id = {brand_id:UUID}
  AND created_at >= now() - INTERVAL {days:Int32} DAY
  AND status = 'success'
GROUP BY prompt_category, prompt_branded
ORDER BY total_runs DESC;
