-- table[0] 清分金额 2022 年同比（pay_date 年度轴，分入/划拨双口径）
 WITH 
cte_0 AS (  SELECT toDateTime64(toStartOfYear(toTimeZone(toDateTime64(toDateOrNull(`fiscal_allocation`.`fdate`), 0), 'UTC'), 'UTC'), 0, 'UTC') `fiscal_allocation_view__pay_date_year`, sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation__im_amt` 
  FROM  (SELECT * FROM (
    SELECT * FROM (
      SELECT * FROM (
        SELECT t.*, c.chg_agency_name_canon FROM fne_funddivide_transfer t
        LEFT JOIN (SELECT fchgagencode,
                          arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS chg_agency_name_canon
                   FROM fne_funddivide_transfer GROUP BY fchgagencode) c ON t.fchgagencode = c.fchgagencode
      ) x1
      LEFT JOIN (SELECT frecrgncode,
                        arrayStringConcat(arraySort(groupUniqArray(frecrgnname)), ' / ') AS rec_rgn_name_canon
                 FROM fne_funddivide_transfer WHERE frecrgncode != '' GROUP BY frecrgncode) r ON x1.frecrgncode = r.frecrgncode
    ) x2
    LEFT JOIN (SELECT fitemcode,
                      arrayStringConcat(arraySort(groupUniqArray(fitemname)), ' / ') AS item_name_canon
               FROM fne_funddivide_transfer WHERE fitemcode != '' GROUP BY fitemcode) i ON x2.fitemcode = i.fitemcode
  ) x3
  LEFT JOIN (SELECT frecsubcode,
                    arrayStringConcat(arraySort(groupUniqArray(frecsubname)), ' / ') AS rec_sub_name_canon
             FROM fne_funddivide_transfer WHERE frecsubcode != '' GROUP BY frecsubcode) rs ON x3.frecsubcode = rs.frecsubcode
  )  AS `fiscal_allocation`
  WHERE (toDateOrNull(`fiscal_allocation`.`fdate`) >= parseDateTimeBestEffort(?) AND toDateOrNull(`fiscal_allocation`.`fdate`) <= parseDateTimeBestEffort(?))
  GROUP BY 1
  ORDER BY  1  ASC),
cte_1 AS (  SELECT toDateTime64(toStartOfYear(toTimeZone(toDateTime64(((toDateOrNull(`fiscal_allocation`.`fdate`) + INTERVAL 1 YEAR)), 0), 'UTC'), 'UTC'), 0, 'UTC') `fiscal_allocation_view__pay_date_year`, sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation__im_amt` 
  FROM  (SELECT * FROM (
    SELECT * FROM (
      SELECT * FROM (
        SELECT t.*, c.chg_agency_name_canon FROM fne_funddivide_transfer t
        LEFT JOIN (SELECT fchgagencode,
                          arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS chg_agency_name_canon
                   FROM fne_funddivide_transfer GROUP BY fchgagencode) c ON t.fchgagencode = c.fchgagencode
      ) x1
      LEFT JOIN (SELECT frecrgncode,
                        arrayStringConcat(arraySort(groupUniqArray(frecrgnname)), ' / ') AS rec_rgn_name_canon
                 FROM fne_funddivide_transfer WHERE frecrgncode != '' GROUP BY frecrgncode) r ON x1.frecrgncode = r.frecrgncode
    ) x2
    LEFT JOIN (SELECT fitemcode,
                      arrayStringConcat(arraySort(groupUniqArray(fitemname)), ' / ') AS item_name_canon
               FROM fne_funddivide_transfer WHERE fitemcode != '' GROUP BY fitemcode) i ON x2.fitemcode = i.fitemcode
  ) x3
  LEFT JOIN (SELECT frecsubcode,
                    arrayStringConcat(arraySort(groupUniqArray(frecsubname)), ' / ') AS rec_sub_name_canon
             FROM fne_funddivide_transfer WHERE frecsubcode != '' GROUP BY frecsubcode) rs ON x3.frecsubcode = rs.frecsubcode
  )  AS `fiscal_allocation`
  WHERE (((toDateOrNull(`fiscal_allocation`.`fdate`) + INTERVAL 1 YEAR)) >= parseDateTimeBestEffort(?) AND ((toDateOrNull(`fiscal_allocation`.`fdate`) + INTERVAL 1 YEAR)) <= parseDateTimeBestEffort(?))
  GROUP BY 1
  ORDER BY  1  ASC),
cte_2 AS (  SELECT `fk_aggregate`.`fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year`, sum(`fk_aggregate`.`fiscal_allocation__im_amt`) `fiscal_allocation__im_amt_ly` 
  FROM  cte_1  AS `fk_aggregate`
  GROUP BY 1
  ORDER BY  1  ASC),
cte_3 AS (  SELECT `fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year`, `q_0`.`fiscal_allocation__im_amt` - `q_1`.`fiscal_allocation__im_amt_ly` `fiscal_allocation__im_amt_yoy_diff` 
  FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM  cte_0  AS `cte_0`
   UNION ALL 
  SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM  cte_2  AS `cte_2`) AS `fk_aggregate_keys_source`) AS `fk_aggregate_keys`
  LEFT JOIN  cte_0  AS `q_0` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_0`.`fiscal_allocation_view__pay_date_year`))
  LEFT JOIN  cte_2  AS `q_1` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_1`.`fiscal_allocation_view__pay_date_year`))),
cte_4 AS (  SELECT `fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year`, 100.0 * (`q_0`.`fiscal_allocation__im_amt` - `q_1`.`fiscal_allocation__im_amt_ly`) / NULLIF(`q_1`.`fiscal_allocation__im_amt_ly`, 0) `fiscal_allocation__im_amt_yoy_rate` 
  FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM  cte_0  AS `cte_0`
   UNION ALL 
  SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM  cte_2  AS `cte_2`) AS `fk_aggregate_keys_source`) AS `fk_aggregate_keys`
  LEFT JOIN  cte_0  AS `q_0` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_0`.`fiscal_allocation_view__pay_date_year`))
  LEFT JOIN  cte_2  AS `q_1` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_1`.`fiscal_allocation_view__pay_date_year`))),
cte_5 AS (  SELECT toDateTime64(toStartOfYear(toTimeZone(toDateTime64(toDateOrNull(`fiscal_allocation`.`fdate`), 0), 'UTC'), 'UTC'), 0, 'UTC') `fiscal_allocation_view__pay_date_year`, sum(`fiscal_allocation`.`ftransamt`) `fiscal_allocation__trans_amt` 
  FROM  (SELECT * FROM (
    SELECT * FROM (
      SELECT * FROM (
        SELECT t.*, c.chg_agency_name_canon FROM fne_funddivide_transfer t
        LEFT JOIN (SELECT fchgagencode,
                          arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS chg_agency_name_canon
                   FROM fne_funddivide_transfer GROUP BY fchgagencode) c ON t.fchgagencode = c.fchgagencode
      ) x1
      LEFT JOIN (SELECT frecrgncode,
                        arrayStringConcat(arraySort(groupUniqArray(frecrgnname)), ' / ') AS rec_rgn_name_canon
                 FROM fne_funddivide_transfer WHERE frecrgncode != '' GROUP BY frecrgncode) r ON x1.frecrgncode = r.frecrgncode
    ) x2
    LEFT JOIN (SELECT fitemcode,
                      arrayStringConcat(arraySort(groupUniqArray(fitemname)), ' / ') AS item_name_canon
               FROM fne_funddivide_transfer WHERE fitemcode != '' GROUP BY fitemcode) i ON x2.fitemcode = i.fitemcode
  ) x3
  LEFT JOIN (SELECT frecsubcode,
                    arrayStringConcat(arraySort(groupUniqArray(frecsubname)), ' / ') AS rec_sub_name_canon
             FROM fne_funddivide_transfer WHERE frecsubcode != '' GROUP BY frecsubcode) rs ON x3.frecsubcode = rs.frecsubcode
  )  AS `fiscal_allocation`
  WHERE (toDateOrNull(`fiscal_allocation`.`fdate`) >= parseDateTimeBestEffort(?) AND toDateOrNull(`fiscal_allocation`.`fdate`) <= parseDateTimeBestEffort(?))
  GROUP BY 1
  ORDER BY  1  ASC),
cte_6 AS (  SELECT toDateTime64(toStartOfYear(toTimeZone(toDateTime64(((toDateOrNull(`fiscal_allocation`.`fdate`) + INTERVAL 1 YEAR)), 0), 'UTC'), 'UTC'), 0, 'UTC') `fiscal_allocation_view__pay_date_year`, sum(`fiscal_allocation`.`ftransamt`) `fiscal_allocation__trans_amt` 
  FROM  (SELECT * FROM (
    SELECT * FROM (
      SELECT * FROM (
        SELECT t.*, c.chg_agency_name_canon FROM fne_funddivide_transfer t
        LEFT JOIN (SELECT fchgagencode,
                          arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS chg_agency_name_canon
                   FROM fne_funddivide_transfer GROUP BY fchgagencode) c ON t.fchgagencode = c.fchgagencode
      ) x1
      LEFT JOIN (SELECT frecrgncode,
                        arrayStringConcat(arraySort(groupUniqArray(frecrgnname)), ' / ') AS rec_rgn_name_canon
                 FROM fne_funddivide_transfer WHERE frecrgncode != '' GROUP BY frecrgncode) r ON x1.frecrgncode = r.frecrgncode
    ) x2
    LEFT JOIN (SELECT fitemcode,
                      arrayStringConcat(arraySort(groupUniqArray(fitemname)), ' / ') AS item_name_canon
               FROM fne_funddivide_transfer WHERE fitemcode != '' GROUP BY fitemcode) i ON x2.fitemcode = i.fitemcode
  ) x3
  LEFT JOIN (SELECT frecsubcode,
                    arrayStringConcat(arraySort(groupUniqArray(frecsubname)), ' / ') AS rec_sub_name_canon
             FROM fne_funddivide_transfer WHERE frecsubcode != '' GROUP BY frecsubcode) rs ON x3.frecsubcode = rs.frecsubcode
  )  AS `fiscal_allocation`
  WHERE (((toDateOrNull(`fiscal_allocation`.`fdate`) + INTERVAL 1 YEAR)) >= parseDateTimeBestEffort(?) AND ((toDateOrNull(`fiscal_allocation`.`fdate`) + INTERVAL 1 YEAR)) <= parseDateTimeBestEffort(?))
  GROUP BY 1
  ORDER BY  1  ASC),
cte_7 AS (  SELECT `fk_aggregate`.`fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year`, sum(`fk_aggregate`.`fiscal_allocation__trans_amt`) `fiscal_allocation__trans_amt_ly` 
  FROM  cte_6  AS `fk_aggregate`
  GROUP BY 1
  ORDER BY  1  ASC),
cte_8 AS (  SELECT `fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year`, `q_0`.`fiscal_allocation__trans_amt` - `q_1`.`fiscal_allocation__trans_amt_ly` `fiscal_allocation__trans_amt_yoy_diff` 
  FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM  cte_5  AS `cte_5`
   UNION ALL 
  SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM  cte_7  AS `cte_7`) AS `fk_aggregate_keys_source`) AS `fk_aggregate_keys`
  LEFT JOIN  cte_5  AS `q_0` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_0`.`fiscal_allocation_view__pay_date_year`))
  LEFT JOIN  cte_7  AS `q_1` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_1`.`fiscal_allocation_view__pay_date_year`))),
cte_9 AS (  SELECT `fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year`, 100.0 * (`q_0`.`fiscal_allocation__trans_amt` - `q_1`.`fiscal_allocation__trans_amt_ly`) / NULLIF(`q_1`.`fiscal_allocation__trans_amt_ly`, 0) `fiscal_allocation__trans_amt_yoy_rate` 
  FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM  cte_5  AS `cte_5`
   UNION ALL 
  SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
  FROM  cte_7  AS `cte_7`) AS `fk_aggregate_keys_source`) AS `fk_aggregate_keys`
  LEFT JOIN  cte_5  AS `q_0` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_0`.`fiscal_allocation_view__pay_date_year`))
  LEFT JOIN  cte_7  AS `q_1` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_1`.`fiscal_allocation_view__pay_date_year`))),
cte_10 AS (  SELECT toDateTime64(toStartOfYear(toTimeZone(toDateTime64(toDateOrNull(`fiscal_allocation`.`fdate`), 0), 'UTC'), 'UTC'), 0, 'UTC') `fiscal_allocation_view__pay_date_year`, sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation__im_amt`, sum(`fiscal_allocation`.`ftransamt`) `fiscal_allocation__trans_amt` 
  FROM  (SELECT * FROM (
    SELECT * FROM (
      SELECT * FROM (
        SELECT t.*, c.chg_agency_name_canon FROM fne_funddivide_transfer t
        LEFT JOIN (SELECT fchgagencode,
                          arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS chg_agency_name_canon
                   FROM fne_funddivide_transfer GROUP BY fchgagencode) c ON t.fchgagencode = c.fchgagencode
      ) x1
      LEFT JOIN (SELECT frecrgncode,
                        arrayStringConcat(arraySort(groupUniqArray(frecrgnname)), ' / ') AS rec_rgn_name_canon
                 FROM fne_funddivide_transfer WHERE frecrgncode != '' GROUP BY frecrgncode) r ON x1.frecrgncode = r.frecrgncode
    ) x2
    LEFT JOIN (SELECT fitemcode,
                      arrayStringConcat(arraySort(groupUniqArray(fitemname)), ' / ') AS item_name_canon
               FROM fne_funddivide_transfer WHERE fitemcode != '' GROUP BY fitemcode) i ON x2.fitemcode = i.fitemcode
  ) x3
  LEFT JOIN (SELECT frecsubcode,
                    arrayStringConcat(arraySort(groupUniqArray(frecsubname)), ' / ') AS rec_sub_name_canon
             FROM fne_funddivide_transfer WHERE frecsubcode != '' GROUP BY frecsubcode) rs ON x3.frecsubcode = rs.frecsubcode
  )  AS `fiscal_allocation`
  WHERE (toDateOrNull(`fiscal_allocation`.`fdate`) >= parseDateTimeBestEffort(?) AND toDateOrNull(`fiscal_allocation`.`fdate`) <= parseDateTimeBestEffort(?))
  GROUP BY 1)
SELECT `fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year`, `q_4`.`fiscal_allocation__im_amt` `fiscal_allocation_view__im_amt`, `q_0`.`fiscal_allocation__im_amt_yoy_diff` `fiscal_allocation_view__im_amt_yoy_diff`, `q_1`.`fiscal_allocation__im_amt_yoy_rate` `fiscal_allocation_view__im_amt_yoy_rate`, `q_4`.`fiscal_allocation__trans_amt` `fiscal_allocation_view__trans_amt`, `q_2`.`fiscal_allocation__trans_amt_yoy_diff` `fiscal_allocation_view__trans_amt_yoy_diff`, `q_3`.`fiscal_allocation__trans_amt_yoy_rate` `fiscal_allocation_view__trans_amt_yoy_rate` 
FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
FROM (SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
FROM  cte_3  AS `cte_3`
 UNION ALL 
SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
FROM  cte_4  AS `cte_4`
 UNION ALL 
SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
FROM  cte_8  AS `cte_8`
 UNION ALL 
SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
FROM  cte_9  AS `cte_9`
 UNION ALL 
SELECT DISTINCT `fiscal_allocation_view__pay_date_year` `fiscal_allocation_view__pay_date_year` 
FROM  cte_10  AS `cte_10`) AS `fk_aggregate_keys_source`) AS `fk_aggregate_keys`
LEFT JOIN  cte_3  AS `q_0` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_0`.`fiscal_allocation_view__pay_date_year`))
LEFT JOIN  cte_4  AS `q_1` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_1`.`fiscal_allocation_view__pay_date_year`))
LEFT JOIN  cte_8  AS `q_2` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_2`.`fiscal_allocation_view__pay_date_year`))
LEFT JOIN  cte_9  AS `q_3` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_3`.`fiscal_allocation_view__pay_date_year`))
LEFT JOIN  cte_10  AS `q_4` ON ((`fk_aggregate_keys`.`fiscal_allocation_view__pay_date_year`) = (`q_4`.`fiscal_allocation_view__pay_date_year`))
LIMIT 102022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z2022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z2022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z2022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z2022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z