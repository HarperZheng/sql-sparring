-- table[0] 2022年非税缴款合计（收入类别三类口径，pay_date）
SELECT sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count` 
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
WHERE (toDateOrNull(`fiscal_collection`.`fdate`) >= parseDateTimeBestEffort(?) AND toDateOrNull(`fiscal_collection`.`fdate`) <= parseDateTimeBestEffort(?))
ORDER BY  1  DESC
LIMIT 1002022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z