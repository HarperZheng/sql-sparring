-- table[0] 划拨金额：划入区划×划入单位（清分流向）
SELECT `fiscal_allocation`.`frecrgncode` `fiscal_allocation_view__rec_rgn_code`, `fiscal_allocation`.rec_rgn_name_canon `fiscal_allocation_view__rec_rgn_name`, `fiscal_allocation`.`frecagenidcode` `fiscal_allocation_view__rec_agency_code`, sum(`fiscal_allocation`.`ftransamt`) `fiscal_allocation_view__trans_amt`, count(*) `fiscal_allocation_view__count` 
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
GROUP BY 1, 2, 3
ORDER BY  4  DESC
LIMIT 100