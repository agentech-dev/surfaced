-- Alignment rate over time by provider and canonical position
-- Parameters: brand_id (UUID), days (Int)
SELECT
    toDate(a.created_at) AS day,
    a.provider_name,
    a.model,
    a.alignment_position_id,
    p.topic,
    countIf(a.alignment_status IN ('aligned', 'partial', 'misaligned', 'silent')) AS judged_answers,
    countIf(a.alignment_status = 'aligned') AS aligned_answers,
    countIf(a.alignment_status = 'partial') AS partial_answers,
    countIf(a.alignment_status = 'misaligned') AS misaligned_answers,
    countIf(a.alignment_status = 'silent') AS silent_answers,
    countIf(a.alignment_status = 'judge_failed') AS judge_failed_answers,
    round(
        countIf(a.alignment_status = 'aligned')
        / greatest(countIf(a.alignment_status IN ('aligned', 'partial', 'misaligned', 'silent')), 1)
        * 100,
        1
    ) AS alignment_rate_pct
FROM answers AS a
LEFT JOIN canonical_positions AS p ON p.id = a.alignment_position_id
WHERE a.brand_id = {brand_id:UUID}
  AND a.created_at >= now() - INTERVAL {days:Int32} DAY
  AND a.status = 'success'
  AND a.alignment_status != 'not_applicable'
GROUP BY day, a.provider_name, a.model, a.alignment_position_id, p.topic
ORDER BY day, a.provider_name, p.topic;
