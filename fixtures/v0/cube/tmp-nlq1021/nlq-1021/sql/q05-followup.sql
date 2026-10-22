-- table[0] 口径A：全库累计清分 vs 缴款总额（清分率）
SELECT sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation_view__im_amt`, sum(`fiscal_allocation`.`ftransamt`) `fiscal_allocation_view__trans_amt`, count(*) `fiscal_allocation_view__count` 
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
ORDER BY  1  DESC
LIMIT 1