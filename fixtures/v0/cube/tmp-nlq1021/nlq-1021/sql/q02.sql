-- table[0] 非税缴款金额按月 + 月环比（pay_date 月粒度，全量 57 个月）
 WITH 
cte_0 AS (  SELECT date_trunc('month', "fiscal_collection__pay_date_month") "fiscal_collection_view__pay_date_month", sum("fiscal_collection__amt") "fiscal_collection__amt" 
  FROM  dev_pre_aggregations.fiscal_collection_main__usage_2  AS "fiscal_collection__main"
  GROUP BY 1
  ORDER BY  1  ASC),
cte_1 AS (  SELECT date_trunc('month', ("fiscal_collection__pay_date_month" + interval '1 month')) "fiscal_collection_view__pay_date_month", sum("fiscal_collection__amt") "fiscal_collection__amt" 
  FROM  dev_pre_aggregations.fiscal_collection_main__usage_1  AS "fiscal_collection__main"
  GROUP BY 1
  ORDER BY  1  ASC),
cte_2 AS (  SELECT "fk_aggregate"."fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month", sum("fk_aggregate"."fiscal_collection__amt") "fiscal_collection__amt_lm" 
  FROM  cte_1  AS "fk_aggregate"
  GROUP BY 1
  ORDER BY  1  ASC),
cte_3 AS (  SELECT "fk_aggregate_keys"."fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month", "q_0"."fiscal_collection__amt" - "q_1"."fiscal_collection__amt_lm" "fiscal_collection__amt_mom_diff" 
  FROM (SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
  FROM (SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
  FROM  cte_0  AS "cte_0"
   UNION ALL 
  SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
  FROM  cte_2  AS "cte_2") AS "fk_aggregate_keys_source") AS "fk_aggregate_keys"
  LEFT JOIN  cte_0  AS "q_0" ON (("fk_aggregate_keys"."fiscal_collection_view__pay_date_month" IS NOT DISTINCT FROM "q_0"."fiscal_collection_view__pay_date_month"))
  LEFT JOIN  cte_2  AS "q_1" ON (("fk_aggregate_keys"."fiscal_collection_view__pay_date_month" IS NOT DISTINCT FROM "q_1"."fiscal_collection_view__pay_date_month"))),
cte_4 AS (  SELECT "fk_aggregate_keys"."fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month", 100.0 * ("q_0"."fiscal_collection__amt" - "q_1"."fiscal_collection__amt_lm") / NULLIF("q_1"."fiscal_collection__amt_lm", 0) "fiscal_collection__amt_mom_rate" 
  FROM (SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
  FROM (SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
  FROM  cte_0  AS "cte_0"
   UNION ALL 
  SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
  FROM  cte_2  AS "cte_2") AS "fk_aggregate_keys_source") AS "fk_aggregate_keys"
  LEFT JOIN  cte_0  AS "q_0" ON (("fk_aggregate_keys"."fiscal_collection_view__pay_date_month" IS NOT DISTINCT FROM "q_0"."fiscal_collection_view__pay_date_month"))
  LEFT JOIN  cte_2  AS "q_1" ON (("fk_aggregate_keys"."fiscal_collection_view__pay_date_month" IS NOT DISTINCT FROM "q_1"."fiscal_collection_view__pay_date_month"))),
cte_5 AS (  SELECT date_trunc('month', "fiscal_collection__pay_date_month") "fiscal_collection_view__pay_date_month", sum("fiscal_collection__amt") "fiscal_collection__amt" 
  FROM  dev_pre_aggregations.fiscal_collection_main__usage_0  AS "fiscal_collection__main"
  GROUP BY 1)
SELECT "fk_aggregate_keys"."fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month", "q_2"."fiscal_collection__amt" "fiscal_collection_view__amt", "q_0"."fiscal_collection__amt_mom_diff" "fiscal_collection_view__amt_mom_diff", "q_1"."fiscal_collection__amt_mom_rate" "fiscal_collection_view__amt_mom_rate" 
FROM (SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
FROM (SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
FROM  cte_3  AS "cte_3"
 UNION ALL 
SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
FROM  cte_4  AS "cte_4"
 UNION ALL 
SELECT DISTINCT "fiscal_collection_view__pay_date_month" "fiscal_collection_view__pay_date_month" 
FROM  cte_5  AS "cte_5") AS "fk_aggregate_keys_source") AS "fk_aggregate_keys"
LEFT JOIN  cte_3  AS "q_0" ON (("fk_aggregate_keys"."fiscal_collection_view__pay_date_month" IS NOT DISTINCT FROM "q_0"."fiscal_collection_view__pay_date_month"))
LEFT JOIN  cte_4  AS "q_1" ON (("fk_aggregate_keys"."fiscal_collection_view__pay_date_month" IS NOT DISTINCT FROM "q_1"."fiscal_collection_view__pay_date_month"))
LEFT JOIN  cte_5  AS "q_2" ON (("fk_aggregate_keys"."fiscal_collection_view__pay_date_month" IS NOT DISTINCT FROM "q_2"."fiscal_collection_view__pay_date_month"))
ORDER BY  1  ASC
LIMIT 100