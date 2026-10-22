-- table[0] 各年缴库金额（口径：缴库明细 amt，按缴库日期 build_date 年分组，单位元）
SELECT date_trunc('year', "fiscal_treasury__build_date_month") "fiscal_treasury_view__build_date_year", sum("fiscal_treasury__amt") "fiscal_treasury_view__amt" 
FROM  dev_pre_aggregations.fiscal_treasury_main  AS "fiscal_treasury__main"
WHERE ("fiscal_treasury__build_date_month" >= CAST(? as TIMESTAMP) AND "fiscal_treasury__build_date_month" <= CAST(? as TIMESTAMP))
GROUP BY 1
ORDER BY  1  ASC
LIMIT 1002022-01-01T00:00:00.0002026-12-31T23:59:59.999