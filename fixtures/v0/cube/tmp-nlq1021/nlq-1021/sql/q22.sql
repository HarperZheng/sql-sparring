-- table[0] 缴库报文：已确认入库 vs 待国库确认（enter_status 分组，全量）
SELECT `fiscal_treasury`.`fenterstatus` `fiscal_treasury_view__enter_status`, sum(`fiscal_treasury`.`famt`) `fiscal_treasury_view__amt`, count(*) `fiscal_treasury_view__count`, COUNT(DISTINCT `fiscal_treasury`.`ftransno`) `fiscal_treasury_view__bill_count` 
FROM  (SELECT * FROM (
  SELECT fid,
         any(fpid) AS fpid, any(ftransno) AS ftransno,
         any(fsubcode) AS fsubcode, any(fsubname) AS fsubname,
         any(fsublevel) AS fsublevel, any(fsublevelname) AS fsublevelname,
         any(fstatus) AS fstatus, any(fenterstatus) AS fenterstatus,
         any(freconcilestatus) AS freconcilestatus, any(fsharerate) AS fsharerate,
         any(fchgrgncode) AS fchgrgncode, any(frecrgncode) AS frecrgncode,
         any(fchgagencode) AS fchgagencode,
         any(fpayacctname) AS fpayacctname, any(frecacctname) AS frecacctname,
         any(fdate) AS fdate, any(fenterdate) AS fenterdate,
         any(freconciledate) AS freconciledate,
         any(famt) AS famt, any(ftotalamt) AS ftotalamt
  FROM fne_treasury_transfer_new
  GROUP BY fid
) t
LEFT JOIN (SELECT fsubcode,
                  arrayStringConcat(arraySort(groupUniqArray(fsubname)), ' / ') AS sub_name_canon
           FROM fne_treasury_transfer_new WHERE fsubcode != '' GROUP BY fsubcode) s
ON t.fsubcode = s.fsubcode
)  AS `fiscal_treasury`
GROUP BY 1
ORDER BY  2  DESC
LIMIT 100