-- table[0] 收入侧资金性质×缴款金额（全量，无时间过滤）
SELECT `fiscal_collection`.`frecfundsnaturecode` `fiscal_collection_view__rec_funds_nature_code`, `fiscal_collection`.`frecfundsnaturename` `fiscal_collection_view__rec_funds_nature_name`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt`, count(*) `fiscal_collection_view__count` 
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
GROUP BY 1, 2
ORDER BY  3  DESC
LIMIT 100