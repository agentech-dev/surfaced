-- Recommendation rate for tracked brand mentions
-- Parameters: brand_id (UUID), days (Int)
SELECT
    toDate(created_at) AS day,
    prompt_branded,
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
    ) AS recommendation_rate_pct
FROM answers
WHERE brand_id = {brand_id:UUID}
  AND created_at >= now() - INTERVAL {days:Int32} DAY
  AND status = 'success'
GROUP BY day, prompt_branded
ORDER BY day, prompt_branded;
