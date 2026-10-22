-- table[0] 汇缴缴款明细（bus_type=2，前 100 行，按缴款日期倒序）
SELECT `fiscal_collection`.`fpaycode` `fiscal_collection_view__pay_code`, toTimeZone(toDateTime64(toDateOrNull(`fiscal_collection`.`fdate`), 0), 'UTC') `fiscal_collection_view__pay_date`, `fiscal_collection`.`fchgagencode` `fiscal_collection_view__chg_agency_code`, `fiscal_collection`.chg_agency_name_canon `fiscal_collection_view__chg_agency_name`, `fiscal_collection`.`fsubcode` `fiscal_collection_view__sub_code`, `fiscal_collection`.sub_name_canon `fiscal_collection_view__sub_name`, count(*) `fiscal_collection_view__count`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt` 
FROM  (SELECT * FROM (
  SELECT * FROM (
    SELECT * FROM (
      SELECT * FROM (
        SELECT t.*, c.chg_agency_name_canon FROM fne_paybook_full_high t
        LEFT JOIN (SELECT fchgagencode,
                          arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS chg_agency_name_canon
                   FROM fne_paybook_full_high GROUP BY fchgagencode) c ON t.fchgagencode = c.fchgagencode
      ) x1
      LEFT JOIN (SELECT frecrgncode,
                        arrayStringConcat(arraySort(groupUniqArray(frecrgnname)), ' / ') AS rec_rgn_name_canon
                 FROM fne_paybook_full_high WHERE frecrgncode != '' GROUP BY frecrgncode) r ON x1.frecrgncode = r.frecrgncode
    ) x2
    LEFT JOIN (SELECT fitemcode,
                      arrayStringConcat(arraySort(groupUniqArray(fitemname)), ' / ') AS item_name_canon
               FROM fne_paybook_full_high WHERE fitemcode != '' GROUP BY fitemcode) i ON x2.fitemcode = i.fitemcode
  ) x3
  LEFT JOIN (SELECT fsubcode,
                    arrayStringConcat(arraySort(groupUniqArray(fsubname)), ' / ') AS sub_name_canon
             FROM fne_paybook_full_high WHERE fsubcode != '' GROUP BY fsubcode) s ON x3.fsubcode = s.fsubcode
) x4
LEFT JOIN (SELECT frecsubcode,
                  arrayStringConcat(arraySort(groupUniqArray(frecsubname)), ' / ') AS rec_sub_name_canon
           FROM fne_paybook_full_high WHERE frecsubcode != '' GROUP BY frecsubcode) rs ON x4.frecsubcode = rs.frecsubcode
)  AS `fiscal_collection`
WHERE (`fiscal_collection`.`fbustype` = ?)
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY  2  DESC
LIMIT 1002

-- table[1] 汇缴缴款汇总（bus_type=2，全量单行聚合）
SELECT count(*) `fiscal_collection_view__count`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt` 
FROM  (SELECT * FROM (
  SELECT * FROM (
    SELECT * FROM (
      SELECT * FROM (
        SELECT t.*, c.chg_agency_name_canon FROM fne_paybook_full_high t
        LEFT JOIN (SELECT fchgagencode,
                          arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS chg_agency_name_canon
                   FROM fne_paybook_full_high GROUP BY fchgagencode) c ON t.fchgagencode = c.fchgagencode
      ) x1
      LEFT JOIN (SELECT frecrgncode,
                        arrayStringConcat(arraySort(groupUniqArray(frecrgnname)), ' / ') AS rec_rgn_name_canon
                 FROM fne_paybook_full_high WHERE frecrgncode != '' GROUP BY frecrgncode) r ON x1.frecrgncode = r.frecrgncode
    ) x2
    LEFT JOIN (SELECT fitemcode,
                      arrayStringConcat(arraySort(groupUniqArray(fitemname)), ' / ') AS item_name_canon
               FROM fne_paybook_full_high WHERE fitemcode != '' GROUP BY fitemcode) i ON x2.fitemcode = i.fitemcode
  ) x3
  LEFT JOIN (SELECT fsubcode,
                    arrayStringConcat(arraySort(groupUniqArray(fsubname)), ' / ') AS sub_name_canon
             FROM fne_paybook_full_high WHERE fsubcode != '' GROUP BY fsubcode) s ON x3.fsubcode = s.fsubcode
) x4
LEFT JOIN (SELECT frecsubcode,
                  arrayStringConcat(arraySort(groupUniqArray(frecsubname)), ' / ') AS rec_sub_name_canon
           FROM fne_paybook_full_high WHERE frecsubcode != '' GROUP BY frecsubcode) rs ON x4.frecsubcode = rs.frecsubcode
)  AS `fiscal_collection`
WHERE (`fiscal_collection`.`fbustype` = ?)
LIMIT 1002