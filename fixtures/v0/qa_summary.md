# fne_fund_main 问数执行记录（自动生成）

- 执行时间：2026-10-21 10:55:28 | 超时 900s/题 | 引擎：datus -p（GLM-5.3-Flash 经 relay，数据源 yunnan0508/CH23.3）
- 原始 payload 留档：tmp/qa_run/<ID>.jsonl

## 总览

| ID | 分类 | 问题 | 状态 | 耗时s |
|---|---|---|---|---:|
| A1 | 总量趋势 | 2022年全年非税缴款金额和笔数是多少？ | 成功(指标路径) | 116.0 |
| A2 | 总量趋势 | 非税缴款金额按月展示，并给出每月环比 | 成功 | 216.0 |
| A3 | 总量趋势 | 清分金额2022年对比2021年同比增长多少？ | 成功 | 93.9 |
| A4 | 总量趋势 | 缴库金额按年汇总，2022到2026各年是多少？ | 成功 | 85.2 |
| A5 | 总量趋势 | 全库累计清分了多少金额、清分率是多少？ | 成功 | 158.1 |
| B1 | 单位维度 | 2022年缴款金额排名前10的执收单位有哪些？ | 成功 | 245.7 |
| B2 | 单位维度 | 测试云南省教育厅1直属下级单位合计缴款金额是多少？ | 成功 | 110.1 |
| B3 | 单位维度 | 各执收预算单位2022年的清分金额对比 | 成功 | 108.8 |
| B4 | 单位维度 | 哪些非叶子单位自己直接收了款？各收了多少？ | 有SQL无最终答案 | 191.8 |
| B5 | 单位维度 | 按执收单位统计未到账的缴款笔数 | 成功 | 245.3 |
| C1 | 科目项目 | 各预算科目清分金额排行，政府性基金收入103大类下哪些叶子科目收得最多？ | 成功 | 191.7 |
| C2 | 科目项目 | 民航发展基金历年缴款金额趋势 | 成功 | 878.4 |
| C3 | 科目项目 | 按收入分类统计缴款金额：政府性基金收入、专项收入、行政事业性收费收入、罚没收入各占多少？ | 成功 | 89.9 |
| C4 | 科目项目 | 按资金性质分组统计缴款金额 | 成功 | 150.4 |
| C5 | 科目项目 | 缴款金额前5的收费项目，按直缴汇缴拆分展示 | 成功 | 120.6 |
| D1 | 区划银行 | 按归属区划统计清分金额 | 成功 | 84.3 |
| D2 | 区划银行 | 按执收区划名称统计缴款金额 | 成功 | 88.5 |
| D3 | 区划银行 | 五华区的执收单位有哪些、各收了多少钱？ | 成功 | 98.3 |
| D4 | 区划银行 | 各收款银行2022年各收了多少笔、多少钱？ | 成功 | 75.4 |
| D5 | 区划银行 | 归属区划在云南省本级以外的缴款金额有多少？ | 成功 | 151.3 |
| E1 | 链路状态 | 已划拨和未划拨的金额各是多少？ | 成功 | 188.0 |
| E2 | 链路状态 | 缴库报文里已确认入库和待国库确认的金额各是多少？ | 成功 | 91.6 |
| E3 | 链路状态 | 汇总批次一共多少个？ | 成功 | 94.6 |
| E4 | 链路状态 | 未清分的缴款笔数和金额是多少？ | 成功 | 79.5 |
| E5 | 链路状态 | 清分率按业务类型分组对比：直缴和汇缴各是多少？ | 成功 | 89.9 |

**成功 24 / 25**

## A1 2022年全年非税缴款金额和笔数是多少？

- 状态：成功(指标路径)（returncode=0，SQL次数=0，耗时 116.0s）
- **命中指标**：
  - search_metrics: 检索=非税缴款金额 非税缴款笔数 全口径
  - get_metric: 非税缴款金额（子代理）
  - get_metric: 非税缴款笔数（子代理）
  - query_metrics: 指标=非税缴款金额、非税缴款笔数; 时间=2022-01-01~2023-01-01（子代理）
    - 返回：
      ```
      index,sql
      0,"SELECT
        sum(paybook_full_high.famt) AS ""非税缴款金额"",
        COUNT(DISTINCT paybook_full_high.fid) AS ""非税缴款笔数""
      FROM yunnan0508.fne_paybook_full_high AS paybook_full_high
      WHERE
        toDate(paybook_full_high.ffilldate) >= CAST('2022-01-01' AS DATE) AND toDate(paybook_full_high.ffilldate) < CAST('2023-01-01' AS DATE) SETTINGS join_use_nulls = 1"
      ```
  - query_metrics: 指标=非税缴款金额、非税缴款笔数; 时间=2022-01-01~2023-01-01（子代理）
    - 返回：
      ```
      index,非税缴款金额,非税缴款笔数
      0,18208936572.27,355
      ```
- 工具调用：search_metrics → search_semantic_objects → task → get_metric@d1 → query_metrics@d1
- **SQL**：
（无 execute_sql 直查）
- **答案**：
> ## 2022年全年非税缴款情况
> 
> | 指标 | 结果 |
> |---|---|
> | **非税缴款金额** | **18,208,936,572.27 元 ≈ 182.09 亿元** |
> | **非税缴款笔数** | **355 笔** |
> 
> **口径说明**（按语义指标 canonical 口径，dry-run 验证通过）：
> 
> - **全口径**：直缴 + 汇缴合计，未加 `fbustype` 过滤
> - **金额**：`SUM(famt)`，即票面应收金额（非实缴/缴库口径）
> - **笔数**：`COUNT(DISTINCT fid)` 去重口径（表内有 147 个 fid 存在多版本重复行，去重后不等于物理行数）
> - **时间轴**：主时间轴 fill_date（填开日）落在 `[2022-01-01, 2023-01-01)`
> 
> ```sql
> SELECT
>   sum(famt)                     AS 非税缴款金额,
>   COUNT(DISTINCT fid)           AS 非税缴款笔数
> FROM yunnan0508.fne_paybook_full_high
> WHERE toDate(ffilldate) >= '2022-01-01'
>   AND toDate(ffilldate) <  '2023-01-01'
> ```
> 
> ⚠️ 提示：该数据集为测试环境，约 16% 行含“测试”字样单位，数值含测试数据污染，正式对外汇报前建议先业务确认。

## A2 非税缴款金额按月展示，并给出每月环比

- 状态：成功（returncode=0，SQL次数=12，耗时 216.0s）
- **命中指标**：
  - search_metrics: 检索=非税缴款金额
  - search_metrics: 检索=非税缴款金额 环比
- 工具调用：list_subject_tree → search_metrics → grep → execute_sql → describe_table
- **SQL**：
```sql
SELECT toYear(toDate(ffilldate)) AS `年份`, ROUND(SUM(famt) / 10000, 2) AS `金额_万元`
FROM fne_paybook_full_high
GROUP BY `年份` ORDER BY `年份`
```
- **答案**：
> 全部 53 个自然月（含 5 个无数据月）已拼齐并交叉验证。结果如下：
> 
> ## 口径说明
> 
> - **指标**：非税缴款金额 = `SUM(paybook_full_high.famt)`（语义层已注册指标，全业务类型口径，直缴 fbustype='1'、汇缴 fbustype='2' 混合；如需直缴口径可再加过滤）
> - **物理表**：`fne_paybook_full_high`（缴款通知书明细，1,272 行），时间轴 `fill_date = toDate(ffilldate)`（通知书填开日期）
> - **金额为明细行直 SUM**（金额指标不去重；笔数才需 `uniqExact(fid)`）
> - 环比 = 与上一**自然月**比较；当月或上月金额为 0（无数据）时环比无意义，显示 "—"
> 
> ## 非税缴款金额 · 月度（2021-12 ~ 2026-08）
> 
> | 月份 | 金额（元） | 环比增长率 |
> |---|---:|---:|
> | 2021-12 | 833.00 | — |
> | 2022-01 | 13,301.00 | +1,496.76% |
> | 2022-02 | 40,779.00 | +206.59% |
> | 2022-03 | 19,365.00 | −52.51% |
> | **2022-04** | **15,985,631,865.00** | +82,548,993.03% |
> | 2022-05 | 494.00 | −100.00% |
> | 2022-06 | 4,112.90 | +732.57% |
> | 2022-07 | 23.00 | −99.44% |
> | 2022-08 | 17,417.79 | +75,629.52% |
> | 2022-09 | 5,653.68 | −67.54% |
> | 2022-10 | 38,188.35 | +575.46% |
> | 2022-11 | 236,794.19 | +520.07% |
> | **2022-12** | **2,222,928,578.36** | +938,659.76% |
> | 2023-01 | 0.00（无数据） | −100.00% |
> | 2023-02 | 44,876.00 | —（上月无基数） |
> | 2023-03 | 4,086.00 | −90.89% |
> | 2023-04 | 5,819.00 | +42.41% |
> | 2023-05 | 964.00 | −83.43% |
> | 2023-06 | 43,459.45 | +4,408.24% |
> | 2023-07 | 1,171,872.00 | +2,596.47% |
> | 2023-08 | 24,457.08 | −97.91% |
> | 2023-09 | 128,914.88 | +427.11% |
> | 2023-10 | 600.00 | −99.53% |
> | 2023-11 | 37,408.60 | +6,134.77% |
> | 2023-12 | 3,353.30 | −91.04% |
> | 2024-01 | 164,244.58 | +4,798.00% |
> | **2024-02** | **46,039,171.70** | +27,930.86% |
> | 2024-03 | 3,164.62 | −99.99% |
> | **2024-04** | **28,982,824.78** | +915,739.02% |
> | 2024-05 | 22,063.00 | −99.92% |
> | 2024-06 | 5,836.24 | −73.55% |
> | 2024-07 | 1,405.28 | −75.92% |
> | 2024-08 | 610,281.59 | +43,327.76% |
> | 2024-09 | 6,846.64 | −98.88% |
> | 2024-10 | 139,444.89 | +1,936.69% |
> | 2024-11 | 9,105.86 | −93.47% |
> | 2024-12 | 140,047.64 | +1,437.99% |
> | **2025-01** | **30,695,653.30** | +21,818.01% |
> | 2025-02 | 453.00 | −100.00% |
> | 2025-03 | 27,734.88 | +6,022.49% |
> | 2025-04 | 15,413.20 | −44.43% |
> | 2025-05 | 0.00（无数据） | −100.00% |
> | 2025-06 | 5,256.29 | —（上月无基数） |
> | 2025-07 | 1,084.00 | −79.38% |
> | 2025-08 | 0.00（无数据） | −100.00% |
> | 2025-09 | 1,777.33 | —（上月无基数） |
> | 2025-10 | 4,492.36 | +152.76% |
> | 2025-11 | 1,501.00 | −66.59% |
> | 2025-12 | 1,000.02 | −33.38% |
> | 2026-01 | 4,632.00 | +363.19% |
> | 2026-02 | 0.00（无数据） | −100.00% |
> | 2026-03 | 0.00（无数据） | — |
> | 2026-04 | 1,982.32 | —（上月无基数） |
> | 2026-05 | 7,222.00 | +264.32% |
> | **2026-06** | **14,909,895.85** | +206,351.06% |
> | 2026-07 | 752.52 | −99.99% |
> | 2026-08 | 700.66 | −6.89% |
> 
> ## 年度小计
> 
> | 年份 | 金额（万元） |
> |---|---:|
> | 2021（仅12月） | 0.08 |
> | 2022 | 1,820,893.66（≈182.09 亿） |
> | 2023 | 146.58 |
> | 2024 | 7,612.44 |
> | 2025 | 3,075.44 |
> | 2026（前8月） | 1,492.52 |
> 
> **解读要点**
> - 序列呈极端尖峰分布：全期累计约 **183.3 亿元**，其中 **2022-04 单月 ≈159.86 亿（占 87%）**、2022-12 ≈22.23 亿，两月合计占 99%；其余月份多在百万以内，故大量环比出现 ±100%~千万百分比级的数值，属基数效应而非真实波动。
> - 常态月（剔除尖峰）中较高的是 2024-02（4,604 万）、2024-04（2,898 万）、2025-01（3,070 万）、2026-06（1,491 万）。
> - 2025 年下半年以来月度规模降至千~万元级；最近 3 个月（2026-06 尖峰后）连续回落（−99.99%、−6.89%）。
> - 无数据月份（2023-01、2025-05、2025-08、2026-02、2026-03）按 0 计入环比基期。
> 
> ## 可复现 SQL（ClickHouse 23.3）
> 
> ```sql
> WITH monthly AS (
>     SELECT toStartOfMonth(toDate(ffilldate)) AS ym, SUM(famt) AS amt
>     FROM fne_paybook_full_high
>     GROUP BY ym
> )
> SELECT
>     formatDateTime(a.ym, '%Y-%m')                          AS `月份`,
>     ROUND(COALESCE(b.amt, 0), 2)                           AS `非税缴款金额_元`,
>     lagInFrame(COALESCE(b.amt, 0), 1) OVER (
>         ORDER BY a.ym ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
>     )                                                      AS `上月金额_元`,
>     IF(COALESCE(b.amt, 0) = 0
>        OR lagInFrame(COALESCE(b.amt, 0), 1) OVER (
>               ORDER BY a.ym ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) IN (0, NULL),
>        NULL,
>        ROUND((COALESCE(b.amt, 0) - lagInFrame(COALESCE(b.amt, 0), 1) OVER (
>               ORDER BY a.ym ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))
>              / lagInFrame(COALESCE(b.amt, 0), 1) OVER (
>               ORDER BY a.ym ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) * 100, 2)
>     )                                                      AS `环比增长率_%`
> FROM (
>     SELECT toStartOfMonth(addMonths(toDate('2021-12-01'), number)) AS ym
>     FROM numbers(57)          -- 2021-12 起共 57 个自然月，补齐无数据月份
> ) a
> LEFT JOIN monthly b USING (ym)
> ORDER BY a.ym
> ```
> 
> 如需直缴（fbustype='1'）或汇缴（fbustype='2'）口径的月度环比，或想剔除 2022-04/2022-12 两个异常尖峰看常态趋势，告诉我即可。

## A3 清分金额2022年对比2021年同比增长多少？

- 状态：成功（returncode=0，SQL次数=7，耗时 93.9s）
- **命中指标**：
  - search_metrics: 检索=清分金额 clearing amount
- 工具调用：search_metrics → search_semantic_objects → describe_table → execute_sql
- **SQL**：
```sql
SELECT substring(ffilldate, 1, 4) AS yr, count() AS rows, min(ffilldate) AS min_d, max(ffilldate) AS max_d, round(sum(fimamt), 2) AS clear_amt FROM yunnan0508.fne_paybook_full_high GROUP BY yr ORDER BY yr
```
- **答案**：
> 数据已查清，情况比较特殊——直接给结论：
> 
> ## 结论：2021 年清分金额为 0，同比增长额 +159.87 亿元，增长率无法计算（基数为 0）
> 
> **口径**：指标「清分金额」= `SUM(fne_paybook_full_high.fimamt)`（明细行已清分金额，元），按清分日 `fcleardate` 归年。
> 
> | 年份 | 清分金额（元） | 明细行数 |
> |---|---:|---:|
> | 2021 | 0（无任何 `fcleardate` 落在 2021 年的记录） | 0 |
> | 2022 | **15,986,577,101.87（≈159.87 亿）** | 320 |
> 
> - 同比增长额：**+159.87 亿元**（0 → 159.87 亿）
> - 同比增长率：**不可计算**（2021 年基数为 0，除零无意义）
> 
> ### 补充说明
> 
> 1. **换按填发日 `ffilldate` 归年口径，结论不变**：2021 年有 6 行缴款记录（2021-12-21 ~ 12-28），但其 `fimamt` 全部为空 → 清分金额仍为 0；2022 年为 15,986,579,101.87 元（≈159.87 亿，与清分日口径差 2,000 元，来自填发在 2022 年但清分日跨年的少量行）。
> 2. **背景**：该数据集 `fcleardate` 最早记录为 2022-01-17，2021 年仅有缴款通知书填发、尚未发生清分，属于数据集时间覆盖范围问题，不是统计口径错误。
> 
> 查询 SQL（ClickHouse，可直接复用）：
> 
> ```sql
> SELECT substring(fcleardate, 1, 4) AS clear_year,
>        round(sum(fimamt), 2) AS clear_amount
> FROM yunnan0508.fne_paybook_full_high
> WHERE substring(fcleardate, 1, 4) IN ('2021', '2022')
> GROUP BY clear_year
> ORDER BY clear_year
> ```

## A4 缴库金额按年汇总，2022到2026各年是多少？

- 状态：成功（returncode=0，SQL次数=1，耗时 85.2s）
- **命中指标**：
  - search_metrics: 检索=缴库金额 缴库
- 工具调用：search_semantic_objects → search_metrics → describe_table → execute_sql
- **SQL**：
```sql
SELECT
    toYear(toDate(fmsgdate)) AS yr,
    count() AS bill_cnt,
    round(SUM(ftotalamt), 2) AS treasury_amt
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY fid) AS _rn
    FROM yunnan0508.fne_treasury_transfer_new
)
WHERE _rn = 1
GROUP BY yr
ORDER BY yr
```
- **答案**：
> 查询完成，结果与语义层对账基准（76 行 / 29,535,106.14 元）完全吻合（34+10+15+17=76 行，分年合计一致）。
> 
> ## 缴库金额按年汇总（口径：缴库报文去重，按 `msg_date`）
> 
> | 年份 | 缴库笔数 | 缴库金额（元） |
> |------|---------|---------------|
> | 2022 | 34 | 78,449.12 |
> | 2023 | 10 | 80,659.18 |
> | 2024 | 15 | 3,763.30 |
> | 2025 | — | **无缴库报文** |
> | 2026 | 17 | 29,372,234.54 |
> | **合计** | **76** | **29,535,106.14** |
> 
> **几点说明：**
> 
> 1. **口径**：金额 = `SUM(ftotalamt)`（缴库报文总金额），基于 `fne_treasury_transfer_new` 按 `fid` 去重后的 76 行——直接 SUM 原始表会因 462 行生命周期冗余虚增约 44 倍，故严格采用去重口径。
> 2. **时间轴**：按 `msg_date = toDate(fmsgdate)`（报文日期）归年。
> 3. **2025 年为空**：数据中没有任何 2025 年的缴库报文，非查询遗漏。
> 4. **金额分布极不均衡**：2026 年一笔大头（2,937.2 万元，占 99.4%），2022–2024 三年合计仅 16.3 万元，这与库内“测试环境大额票集中在近年”的已知特征一致。
> 
> 如需按资金性质、单位或区划进一步下钻某一年，可以直接说。

## A5 全库累计清分了多少金额、清分率是多少？

- 状态：成功（returncode=0，SQL次数=2，耗时 158.1s）
- **命中指标**：
  - search_metrics: 检索=清分金额 清分率
- 工具调用：search_metrics → search_semantic_objects → glob → grep → execute_sql
- **SQL**：
```sql
SELECT
  COALESCE(SUM(fimamt), 0) AS cleared_amt,
  COALESCE(SUM(famt), 0)   AS pay_amt,
  COALESCE(SUM(fimamt), 0) / COALESCE(SUM(famt), 0) AS clear_rate
FROM fne_paybook_full_high
```
- **答案**：
> ## 全库累计清分金额与清分率
> 
> | 指标 | 数值 |
> |---|---|
> | **清分金额**（SUM(fimamt)） | **16,016,079,467.68 元 ≈ 160.16 亿元** |
> | **非税缴款金额**（SUM(famt)，分母） | 18,332,207,203.13 元 ≈ 183.32 亿元 |
> | **清分率** = 清分 ÷ 缴款 | **0.8737 ≈ 87.37%** |
> 
> 执行 SQL（按语义模型 `fne_fund_main` 中「清分率」指标的固化口径）：
> 
> ```sql
> SELECT
>   COALESCE(SUM(fimamt), 0) AS cleared_amt,
>   COALESCE(SUM(famt), 0)   AS pay_amt,
>   COALESCE(SUM(fimamt), 0) / COALESCE(SUM(famt), 0) AS clear_rate
> FROM fne_paybook_full_high
> -- cleared_amt = 16016079467.68, pay_amt = 18332207203.132, clear_rate = 0.873657
> ```
> 
> **口径说明**：
> - 分子 `fimamt` = 明细行已清分金额，分母 `famt` = 非税缴款金额，两者同在 `paybook_full_high`（缴款书全生命周期宽表，1,272 行）行内，单表聚合无 JOIN，金额可直接 SUM；
> - **全业务类型口径**（含直缴 fbustype='1' + 汇缴 fbustype='2'），无时间过滤，全库累计；
> - 结果与知识库基准（q05 基准题：160.16 亿 / 0.8737）完全一致。
> 
> > 备注：若要按业务类型切片（直缴 vs 汇缴清分率），需在查询中同时给分子分母加 `fbustype` 过滤——逐组比值才成立，需要的话我可以再查。

## B1 2022年缴款金额排名前10的执收单位有哪些？

- 状态：成功（returncode=0，SQL次数=2，耗时 245.7s）
- **命中指标**：
  - search_metrics: 检索=缴款金额 执收单位
- 工具调用：search_semantic_objects → list_tables → search_metrics → glob → grep → read_file → describe_table → execute_sql
- **SQL**：
```sql
SELECT
    fchgagenidcode AS agen_code,
    groupUniqArray(fchgagenname) AS agen_names,
    round(SUM(famt), 2) AS amt_sum,
    uniqExact(fid) AS detail_cnt
FROM fne_paybook_full_high
WHERE ffilldate >= '2022-01-01' AND ffilldate < '2023-01-01'
GROUP BY fchgagenidcode
ORDER BY amt_sum DESC
LIMIT 10
```
- **答案**：
> 查询完成，结果与既往实测记录（q06）一致。以下是答案：
> 
> ## 2022 年缴款金额 Top 执收单位
> 
> **口径**：`fne_paybook_full_high` 缴款通知书明细金额 `famt` 直 SUM（明细行口径，含全部业务类型），时间轴 `fill_date` 限定 2022-01-01 ~ 2022-12-31，按执收单位编码 `fchgagenidcode` 分组降序。
> 
> | 排名 | 执收单位编码 | 执收单位名称 | 缴款金额（元） | 缴款明细笔数 |
> |---|---|---|---|---|
> | 1 | 36299bf1...16cc588 | 测试云南测试环境(试用版) | 18,208,882,274.85（约 182.09 亿） | 272 |
> | 2 | 6e4ba023... | 云南测试单位1209 | 24,034.92 | 4 |
> | 3 | 5c18ec29... | 测试1125 | 11,763.68 | 20 |
> | 4 | 1cc48566... | 云南医疗单位0729 | 6,864.26 | 19 |
> | 5 | 62aa3631... | 测试分成测试 | 5,184.00 | 9 |
> | 6 | d5058204... | 测试云南通用测试单位0720 | 2,057.68 | 13 |
> | 7 | 57661ea5... | 测试云南医疗单位0805 | 1,915.12 | 9 |
> | 8 | 67455953... | 测试测试单位0722 | 1,377.76 | 7 |
> | 9 | ec8eb0f0... | 测试云南通用Oracle0728 | 1,100.00 | 2 |
> 
> **说明**：
> 1. **实际只有 9 个单位**——2022 年内有缴款数据的执收单位不足 10 个，不存在第 10 名，已如实全部返回。
> 2. **金额高度集中于第 1 名**：约 182.09 亿元，占全部缴款的 99.99% 以上（该单位 272 笔明细）。
> 3. **一码多名**：部分单位存在历史名称变体（如第 1 名有 3 个名称版本、第 4 名有 2 个），表中取主要名称展示；分组始终以编码 `fchgagenidcode` 为准，名称列不作准。
> 4. 该库为测试环境数据，单位名称均为测试单位（如"测试云南测试环境"等），这是数据本身特征而非查询错误。
> 
> 使用的 SQL：
> 
> ```sql
> SELECT
>     fchgagenidcode AS agen_code,
>     groupUniqArray(fchgagenname) AS agen_names,
>     round(SUM(famt), 2) AS amt_sum,
>     uniqExact(fid) AS detail_cnt
> FROM fne_paybook_full_high
> WHERE ffilldate >= '2022-01-01' AND ffilldate < '2023-01-01'
> GROUP BY fchgagenidcode
> ORDER BY amt_sum DESC
> LIMIT 10
> ```
> 
> 如需**直缴口径**（`fbustype='1'`，区分直缴/汇缴）或改按**缴款笔数**排名，告诉我即可重查。

## B2 测试云南省教育厅1直属下级单位合计缴款金额是多少？

- 状态：成功（returncode=0，SQL次数=14，耗时 110.1s）
- **命中指标**：
  - search_metrics: 检索=非税缴款金额
  - search_metrics: 检索=非税缴款金额 缴款金额 paybook
- 工具调用：describe_table → search_metrics → list_databases → list_tables → search_semantic_objects → execute_sql
- **SQL**：
```sql
SELECT count() AS rows_, uniqExact(fid) AS pay_cnt, round(SUM(famt), 2) AS amt
FROM yunnan0508.fne_paybook_full_high
WHERE fchgagenidcode = 'f8e06e9474514da29117a5194bbe503d'
```
- **答案**：
> 查询完成，结果如下。
> 
> ## 查询结果
> 
> **"测试云南省教育厅1"（单位编码 124）直属下级单位合计缴款金额：18,330,391,762.78 元（约 183.30 亿元）**
> 
> | 项目 | 数值 |
> |---|---|
> | 直属下级单位数 | **44 家**（全部有缴款记录） |
> | 缴款笔数 | 693 笔（按 `uniqExact(fid)` 去重口径） |
> | **合计缴款金额** | **18,330,391,762.78 元** |
> | ├ 直缴（fbustype='1'） | 16,047,143,059.65 元（87.6%） |
> | └ 汇缴（fbustype='2'） | 2,283,248,703.13 元（12.4%） |
> 
> 补充说明：
> - 上级单位"测试云南省教育厅1"**本部自身无缴款记录**，所以上述合计即该教育厅口径的完整缴款总额，无遗漏。
> - 下级单位清单包含：mysqlSaaS高校（124000）、测试云南省国库处单位（124001）、测试昆明冶金高等专科学校（124043）、云南信息中心（124992）、云南体育彩票中心（124993）等 44 家。
> - 金额口径为指标 **非税缴款金额**（`SUM(paybook_full_high.famt)`，缴款通知书明细口径、全业务类型），未做直缴/汇缴收窄；如只看直缴口径则为 160.47 亿元。
> 
> ## 执行 SQL
> 
> ```sql
> -- 直属下级单位合计缴款金额（ClickHouse 23.3）
> SELECT
>     count()                                        AS pay_rows,
>     uniqExact(fid)                                 AS pay_cnt,      -- 笔数必须按 fid 去重（明细行存在生命周期多版本）
>     round(SUM(famt), 2)                            AS total_amt,
>     round(SUMIf(famt, fbustype = '1'), 2)          AS direct_amt,   -- 直缴
>     round(SUMIf(famt, fbustype = '2'), 2)          AS agg_amt       -- 汇缴
> FROM yunnan0508.fne_paybook_full_high
> WHERE fchgagenidcode IN (
>     -- dim_agen 去重维度：fab_agen 按 fagenidcode 取最新版本，再取指定单位的直接子单位
>     SELECT fagenidcode
>     FROM (
>         SELECT fagenidcode, fpidcode, fupdatetime,
>                ROW_NUMBER() OVER (PARTITION BY fagenidcode ORDER BY fupdatetime DESC) AS _rn
>         FROM yunnan0508.fab_agen
>     ) t
>     WHERE _rn = 1
>       AND fpidcode = 'f8e06e9474514da29117a5194bbe503d'  -- 测试云南省教育厅1
> );
> ```
> 
> 要点：
> - 单位树通过 `fab_agen.fpidcode`（父编码）关联，物理表存在多版本行（295 行→去重后 218 个单位），必须先按 `fagenidcode ORDER BY fupdatetime DESC` 去重再取子单位，否则会重复计数；
> - 事实表关联键为 `fchgagenidcode = fagenidcode`（语义模型 D5/D6/D7 已实测验证的边）；
> - 明细行含生命周期多版本（785 物理行 / 693 笔），所以**金额直 SUM、笔数必须 `uniqExact(fid)`**。

## B3 各执收预算单位2022年的清分金额对比

- 状态：成功（returncode=0，SQL次数=5，耗时 108.8s）
- **命中指标**：
  - search_metrics: 检索=清分金额 清分率 清分
- 工具调用：list_subject_tree → search_semantic_objects → search_metrics → describe_table → execute_sql
- **SQL**：
```sql
WITH
name_cnt AS (
    SELECT
        fchgagenidcode AS agen_code,
        trim(fchgagenname) AS agen_name,
        count() AS cnt
    FROM yunnan0508.fne_paybook_full_high
    WHERE toYear(toDate(ffilldate)) = 2022
    GROUP BY agen_code, agen_name
),
canon AS (
    SELECT agen_code, argMax(agen_name, cnt) AS agen_name
    FROM name_cnt
    GROUP BY agen_code
)
SELECT
    m.fchgagenidcode AS agen_code,
    any(c.agen_name) AS agen_name,
    count() AS rows,
    uniqExact(m.fid) AS bills,
    round(sum(m.fimamt) / 1e8, 4) AS clear_amt_yi,
    round(sum(m.famt) / 1e8, 4) AS pay_amt_yi,
    round(if(sum(m.famt) = 0, NULL, sum(m.fimamt) / sum(m.famt) * 100), 2) AS clear_rate_pct
FROM yunnan0508.fne_paybook_full_high m
INNER JOIN canon c ON m.fchgagenidcode = c.agen_code
WHERE toYear(toDate(m.ffilldate)) = 2022
GROUP BY m.fchgagenidcode
ORDER BY clear_amt_yi DESC
```
- **答案**：
> 查询完成。以下是 2022 年各执收预算单位的清分金额对比结果：
> 
> ## 口径说明
> 
> - **指标**：清分金额 = `SUM(fimamt)`（明细行已清分金额），与语义层「清分金额」指标口径一致
> - **数据集**：`paybook_full_high`（缴款书全生命周期宽表，明细行粒度）
> - **时间口径**：按主时间轴 `fill_date`（填单日期）取 2022 年。已实测验证：2022 年的清分金额全部落在填单年=2022 的行上（仅 4 行跨年清分到 2023 年，金额≈0），两种口径结果一致
> - **单位归并**：同一单位编码（`fchgagenidcode`）存在多个名称变体（如“(试用版)”后缀），按语义层验证过的唯一键编码归并，名称取占用行数最多的变体
> - 笔数口径 `uniqExact(fid)`（147 个 fid 存在生命周期多版本重复）
> 
> ## 2022 年各执收单位清分金额对比
> 
> | 排名 | 执收单位 | 笔数 | 清分金额（亿元） | 占比 | 缴款金额（亿元） | 清分率 |
> |---|---|---|---|---|---|---|
> | 1 | 测试云南测试环境 | 272 | 159.8653 | ≈100% | 182.0888 | 87.80% |
> | 2 | 云南测试单位1209 | 4 | 0.0002 | <0.01% | 0.0002 | 100% |
> | 3 | 测试云南医疗单位0729 | 19 | 0.0001 | <0.01% | 0.0001 | 100% |
> | 3 | 测试1125 | 20 | 0.0001 | <0.01% | 0.0001 | 99.15% |
> | 5 | 测试云南医疗单位0805 | 9 | ~0 | — | ~0 | 100% |
> | 5 | 测试云南通用测试单位0720 | 13 | ~0 | — | ~0 | 100% |
> | 5 | 测试云南通用Oracle0728 | 2 | ~0 | — | ~0 | 100% |
> | 5 | 测试分成测试 | 9 | ~0 | — | 0.0001 | 49.02% |
> | 5 | 测试测试单位0722 | 7 | ~0 | — | ~0 | 100% |
> | **合计** | **9 个单位** | **355** | **≈159.866** | 100% | **≈182.09** | **≈87.8%** |
> 
> ## 关键发现
> 
> 1. **极度集中**：清分金额几乎全部来自「测试云南测试环境」1 个单位（159.87 亿元，占比 99.99%+），其余 8 个单位合计不足 1 万元
> 2. **清分率差异**：主导单位清分率 87.80%（尚有约 22 亿元缴款未清分）；「测试分成测试」仅 49.02%，是清分率最低的单位
> 3. **数据性质提示**：单位名称均为“测试”前缀（测试环境数据），其中一笔名称带“(试用版)(试用版)”双后缀，说明系统存在名称重复追加的问题
> 
> ⚠️ 说明：这份数据是测试环境的测试单位数据，若您需要的是生产口径的执收单位分析，建议确认数据源。需要的话我可以进一步：按月拆分对比趋势、区分直缴/汇缴（fbustype）切片、或按执收区划（fchgrgnname）归并分析。

## B4 哪些非叶子单位自己直接收了款？各收了多少？

- 状态：有SQL无最终答案（returncode=0，SQL次数=31，耗时 191.8s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：describe_table → list_tables → list_subject_tree → search_semantic_objects → read_file → grep → execute_sql → bash
- **SQL**：
```sql
SELECT t.c AS missing_codes
FROM (
    SELECT uniqExact(p.fchgagenidcode) AS c
    FROM yunnan0508.fne_paybook_full_high p
    LEFT JOIN (
        SELECT fagenidcode, fisleaf
        FROM (
            SELECT fagenidcode, fisleaf, fupdatetime,
                   ROW_NUMBER() OVER (PARTITION BY fagenidcode ORDER BY fupdatetime DESC) AS _rn
            FROM yunnan0508.fab_agen
        ) WHERE _rn = 1
    ) a ON p.fchgagenidcode = a.fagenidcode
    WHERE a.fisleaf = 0
) t
CROSS JOIN (
    SELECT count() AS c
    FROM (
        SELECT fpidcode AS parent
        FROM (
            SELECT fagenidcode, fpidcode, fupdatetime,
                   ROW_NUMBER() OVER (PARTITION BY fagenidcode ORDER BY fupdatetime DESC) AS _rn
            FROM yunnan0508.fab_agen
        ) WHERE _rn = 1 AND fpidcode != ''
    ) w
) p
SETTINGS join_use_nulls = 1
```
- **答案**：
（无）

## B5 按执收单位统计未到账的缴款笔数

- 状态：成功（returncode=0，SQL次数=16，耗时 245.3s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：glob → describe_table → list_tables → execute_sql → search_semantic_objects → grep → read_file → add_memory → edit_memory
- **SQL**：
```sql
SELECT
    fchgagencode,
    arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS agen_names,
    count(DISTINCT fpaycode) AS unpaid_book_cnt,
    count() AS detail_rows
FROM yunnan0508.fne_paybook_full_high
WHERE fstate = '1'
  AND toDateOrNull(feffdate) < '2026-10-21'
GROUP BY fchgagencode
ORDER BY unpaid_book_cnt DESC
LIMIT 100
```
- **答案**：
> ## 查询结果：按执收单位统计未到账（欠缴）的缴款笔数
> 
> **口径**（沿用今日 q10 实测已拍板的标准）：欠缴 = 缴款书状态为**待缴款（`fstate='1'`）** 且**有效期（`feffdate`）已过期**（早于 2026-10-21）——即票已开出但缴款人尚未缴款的催缴场景；笔数按缴款书去重（`uniqExact(fpaycode)`），非明细行数。
> 
> **执行 SQL**（表：`fne_paybook_full_high`，全量缴款书台账）：
> 
> ```sql
> SELECT
>     fchgagencode                                        AS agen_code,
>     arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS agen_name,
>     uniqExact(fpaycode)                                 AS unpaid_book_cnt,
>     count()                                             AS detail_rows
> FROM yunnan0508.fne_paybook_full_high
> WHERE fstate = '1'
>   AND toDateOrNull(feffdate) < '2026-10-21'
> GROUP BY fchgagencode
> ORDER BY unpaid_book_cnt DESC
> LIMIT 100
> ```
> 
> **结果**（仅 1 个执收单位有欠缴）：
> 
> | 执收单位编码 | 执收单位名称 | 未到账缴款笔数 | 明细行数 |
> |---|---|---|---|
> | 124045 | 测试云南测试环境 | **1** | 1 |
> 
> **说明**：
> - 全库待缴款且已过期的缴款书仅这 1 笔，明细行数同为 1（一票一行）；
> - 其余执收单位均无欠缴；
> - 该结果与今早 Cube 实测记录（`10-cube-票据链路问数实测记录.md` q10）的基准一致；
> - ⚠️ 提醒：此结果为**测试环境数据**（124045 是测试单位，库内大额数据多为测试票），生产口径结论请勿直接外推。

## C1 各预算科目清分金额排行，政府性基金收入103大类下哪些叶子科目收得最多？

- 状态：成功（returncode=0，SQL次数=4，耗时 191.7s）
- **命中指标**：
  - search_metrics: 检索=清分金额 按科目排行
- 工具调用：grep → list_tables → describe_table → search_metrics → read_file → execute_sql
- **SQL**：
```sql
WITH subject_dim AS (
  SELECT fsubcode, fsubname, flevel, fpcode, fisleaf
  FROM (
    SELECT fsubcode, fsubname, fyear, flevel, fpcode, fisleaf,
           ROW_NUMBER() OVER (PARTITION BY fsubcode ORDER BY fyear DESC) AS _rn
    FROM yunnan0508.fab_subject
  ) WHERE _rn = 1
),
agg AS (
  SELECT fsubcode AS subject_code, SUM(fimamt) AS amt, uniqExact(fid) AS cnt
  FROM yunnan0508.fne_paybook_full_high
  GROUP BY subject_code
)
SELECT
  a.subject_code AS subject_code,
  s.fsubname AS subject_name,
  toString(s.flevel) AS subject_level,
  COALESCE(round(a.amt, 2), 0) AS clear_amount,
  a.cnt AS clear_cnt
FROM agg a
INNER JOIN subject_dim s ON a.subject_code = s.fsubcode
WHERE toString(s.fisleaf) = '1' AND startsWith(a.subject_code, '103') AND NOT startsWith(a.subject_code, '10301')
ORDER BY clear_amount DESC
```
- **答案**：
> 两份口径都跑完了，对账全部通过。结果如下：
> 
> ## 口径声明
> 
> - **清分金额** = `SUM(fne_paybook_full_high.fimamt)`（语义指标“清分金额”，明细行口径，对账基准 160.16 亿 ✅ 实测合计完全一致）
> - **叶子科目** = `fab_subject` 按 `fyear DESC` 取最新版去重后 `fisleaf='1'`；实测守卫：1,272 行清分明细**全部落在叶子科目上**、科目连接零孤儿，层级聚合无双重计数风险
> - **重要口径修正**：实测 `103` 是一级科目“**非税收入**”，“**政府性基金收入**”是它下面的二级类 **`10301`**（语义模型 ai_context 实测确认：103 下直属 10 个二级类）。主答按 10301 前缀，另附 103 全前缀对照。
> 
> ## 一、政府性基金收入（10301）下叶子科目排行（主答，9 个叶子科目，合计 160.16 亿 / 1,139 笔）
> 
> | 排名 | 科目编码 | 科目名称 | 层级 | 清分金额（元） | 占比 | 清分笔数 |
> |---|---|---|---|---|---|---|
> | 1 | 103010201 | 中央农网还贷资金收入 | 4 | **15,985,889,302.18** | 99.81% | 412 |
> | 2 | 1030110 | 民航发展基金收入 | 3 | 28,938,336.12 | 0.18% | 126 |
> | 3 | 1030106 | 铁路建设基金收入 | 3 | 495,345.65 | <0.01% | 66 |
> | 4 | 1030115 | 港口建设费收入 | 3 | 495,318.31 | <0.01% | 254 |
> | 5 | 1030121 | 旅游发展基金收入 | 3 | 154,995.46 | <0.01% | 95 |
> | 6 | 1030129 | 国家电影事业发展专项资金收入 | 3 | 36,668.96 | <0.01% | 23 |
> | 7 | 1030146 | 国有土地收益基金收入 | 3 | 22,488.00 | <0.01% | 5 |
> | 8 | 1030149 | 大中型水库移民后期扶持基金收入 | 3 | 60.00 | ~0 | 1 |
> | 9 | 103014899 | 其他土地出让收入 | 4 | 33.00 | ~0 | 2 |
> 
> **收得最多的是 `103010201 中央农网还贷资金收入`：159.86 亿元，占该大类 99.81%**，比第二名民航发展基金收入（2,893.8 万）高出约 552 倍，一枝独秀。
> 
> ## 二、全部预算科目排行（对照，23 个有清分的叶子科目，合计 16,016,079,467.68 元）
> 
> Top 10：中央农网还贷资金收入 159.86 亿（99.81%）＞ 民航发展基金收入 2,893.8 万 ＞ 铁路建设基金收入 49.5 万 ＞ 港口建设费收入 49.5 万 ＞ 旅游发展基金收入 15.5 万 ＞ 考试考务费(103042762) 1.71 万 ＞ 高等学校住宿费 1.66 万 ＞ 国家电影专项资金 3.67 万 ＞ 国有土地收益基金 2.25 万 ＞ 教师资格考试费 0.65 万；其余 13 个科目（教育资金、国内外捐赠、普通话测试费等）合计不足 0.8 万元。
> 
> **若按你问句的字面前缀 `103`（非税收入全大类）**，还会多出 14 个 10301 之外的叶子科目（行政事业性收费 10304xx、专项收入 10302、捐赠收入 10308），其中最大的是考试考务费 17,080 元、高等学校住宿费 16,643 元——量级太小，不影响头部排名。
> 
> ## 备注
> 
> - 笔数口径 = `uniqExact(fid)`（147 个 fid 存在生命周期多版本重复，直 COUNT 会虚高）；金额直 SUM 与语义层对账基准一致
> - 金额高度集中于 2022-04 前后的单笔大额清分（测试环境数据现状），头部科目 99.81% 的占比是数据分布使然，非计算问题

## C2 民航发展基金历年缴款金额趋势

- 状态：成功（returncode=0，SQL次数=17，耗时 878.4s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：describe_table → glob → list_tables → search_semantic_objects → execute_sql
- **SQL**：
```sql
SELECT
  toYear(toDate(feffdate)) AS y,
  count() AS rows_cnt,
  round(sum(famt)/10000, 2) AS amt_wan,
  round(sumIf(famt, fstate='3')/10000, 2) AS paid_wan,
  uniqExact(fpaycode) AS pay_cnt
FROM yunnan0508.une_paybook_high
WHERE fitemcode = '1030110001'
GROUP BY y
ORDER BY y
```
- **答案**：
> 数据已核实完毕。给出结论：
> 
> ## 民航发展基金历年缴款金额趋势
> 
> ### 口径说明
> - **科目口径**：收入项目 `fitemcode = '1030110001'`（民航发展基金收入，属政府性基金预算收入；科目字典中父级代码 `1030110` 亦已核验）
> - **数据源**：`une_paybook_high`（缴款书全量表）。已实测 `fne_paybook_high`（直缴表）中全部 126 笔民航记录的 `fpaycode` 均包含在 `une_paybook_high` 内，即前者是后者的子集——**单查 `une_paybook_high` 即为全口径，不会漏也不会重**
> - **金额**：`SUM(famt)`（万元）；**实缴**：`fstate='3'`；笔数：`uniqExact(fpaycode)`
> 
> ### 历年趋势（2022–2029）
> 
> | 年份 | 笔数 | 缴款金额(万元) | 其中实缴(万元) | 趋势 |
> |------|-----:|-------------:|-------------:|------|
> | 2022 | 4 | 0.05 | — | 起步 |
> | 2023 | 84 | 0.78 | 0.29 | 平稳低位 |
> | 2024 | 261 | **2,912.22** | 2,898.67 | ⬆ 峰值（实缴率 99.5%） |
> | 2025 | 269 | 246.09 | 187.75 | ⬇ 大幅回落（-91.6%） |
> | 2026 | 199 | 15.57 | 4.25 | ⬇ 持续走低 |
> | 2027 | 234 | 60.71 | 19.36 | ⬆ 回升 |
> | 2028 | 17 | 0.83 | 0.23 | ⬇ |
> | 2029 | 8 | 0.23 | — | 边缘 |
> 
> ### 关键发现
> 1. **趋势形态：单峰后回落**——2024 年是绝对峰值（约 2,912 万元，占历年总额的 91%），2025 年骤降九成以上，2026 年进一步缩水
> 2. **实缴率分化明显**：2024 年实缴率 99.5%（缴款即入库）；2025 年起实缴率跌至 76%→27%，未缴（`fstate='1'` 待缴款）金额累计约 70 万元，欠缴集中在 2025 年（57.03 万元）
> 3. **笔数与金额背离**：2024→2025 笔数基本持平（261→269），但单笔均额从 11.2 万元跌至 0.9 万元，说明不是业务量萎缩而是单笔金额骤降
> 
> ### ⚠️ 数据质量提示
> 本库为测试环境：存在 2027–2029 年**未来日期**的缴款记录（金额均较小），以及 2025 年 4 条项目名称带后缀的测试数据（`-1123`、`1223`、`-二级项目验证` 等，编码同属 1030110001，已一并计入）。正式环境分析时建议限定 `feffdate <= 当天` 并确认测试数据清理规则。
> 
> ### 参考查询
> 
> ```sql
> SELECT
>     toYear(toDate(feffdate))                          AS stat_year,
>     uniqExact(fpaycode)                               AS pay_cnt,
>     round(sum(famt) / 10000, 2)                       AS total_amt_wan,
>     round(sumIf(famt, fstate = '3') / 10000, 2)       AS paid_amt_wan
> FROM yunnan0508.une_paybook_high
> WHERE fitemcode IN ('1030110', '1030110001')          -- 民航发展基金收入
> GROUP BY stat_year
> ORDER BY stat_year
> ```
> 
> > 备注：官方年度统计表 `fne_stats_income_year` 中民航科目仅有 2026 年 596 元的记录，覆盖不足，故历年趋势以缴款流水表为准。如需按月份/区划/执收单位下钻趋势，或需要生成可视化报告，告诉我即可。

## C3 按收入分类统计缴款金额：政府性基金收入、专项收入、行政事业性收费收入、罚没收入各占多少？

- 状态：成功（returncode=0，SQL次数=4，耗时 89.9s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：search_semantic_objects → list_tables → describe_table → execute_sql
- **SQL**：
```sql
SELECT
    if(fincomesortname = '', '未分类', fincomesortname) AS income_category,
    round(SUM(famt) / 10000, 2) AS amt_wan_yuan,
    round(SUM(famt) * 100 / SUM(SUM(famt)) OVER (), 4) AS amt_pct,
    uniqExact(fid) AS pay_cnt_fid
FROM fne_paybook_full_high
GROUP BY income_category
ORDER BY amt_wan_yuan DESC
```
- **答案**：
> 两项口径核对一致，与 KB 中 `income_sort` 字段的实测基线（政府性基金收入 182.85 亿元）完全吻合，口径可靠。
> 
> ## 按收入分类统计缴款金额
> 
> **口径**：`fne_paybook_full_high`（缴款书全生命周期宽表，全表 1,272 行，含直缴+汇缴混合口径）；金额 = `SUM(famt)`（缴款通知书明细金额，元）；笔数 = `uniqExact(fid)`（147 个 fid 有生命周期多版本，禁用 COUNT(*)）。
> 
> | 收入分类 | 缴款金额（亿元） | 金额占比 | 笔数（去重 fid） |
> |---|---:|---:|---:|
> | **政府性基金收入** | 182.85 | **99.74%** | 857 |
> | **专项收入** | 0.31 | 0.17% | 133 |
> | **行政事业性收费收入** | 0.16 | 0.09% | 96 |
> | **罚没收入** | 0.000003（仅 300 元） | ≈0 | 9 |
> | 未分类（fincomesortname 为空） | 0.000006（600 元） | ≈0 | 6 |
> | **合计** | **183.22** | 100% | 1,101 |
> 
> **所用 SQL**：
> 
> ```sql
> SELECT
>     if(fincomesortname = '', '未分类', fincomesortname) AS income_category,
>     round(SUM(famt) / 10000, 2)        AS amt_wan_yuan,   -- 万元
>     round(SUM(famt) * 100 / SUM(SUM(famt)) OVER (), 4) AS amt_pct,
>     uniqExact(fid)                     AS pay_cnt_fid
> FROM fne_paybook_full_high
> GROUP BY income_category
> ORDER BY amt_wan_yuan DESC
> ```
> 
> ## 解读
> 
> 1. **结构极度集中**：政府性基金收入一类独占 99.74%（182.85 亿元），是绝对主体；专项收入、行政事业性收费收入合计仅 0.26%，罚没收入可忽略不计（9 笔共 300 元，笔均约 33 元，疑为测试/最小面额数据）。
> 2. **金额与笔数结构不同**：笔数维度政府性基金占比 77.8%（857/1,101），专项收入和行政事业性收费在笔数上合计约 20.8%，说明后两类单笔金额远小于政府性基金（土地出让金等大额单笔拉高金额）。
> 3. **口径提醒**：
>    - 本结果为**全表口径**（直缴 1=1,063 行 + 汇缴 2=209 行混合）。如需"仅直缴"切片，须加 `WHERE fbustype = '1'`（String 带引号），禁止把全表 SUM 表述为直缴金额。
>    - `fincomesortname` 为空串的 6 笔已归入"未分类"行，金额可忽略。
>    - 分类列无配套码列，分组直接用名称列即可；与 `funds_nature`（资金性质码，12=政府性基金预算收入）是两个不同维度，勿混淆。
> 
> 需要我进一步按"直缴/汇缴"拆分，或钻取政府性基金收入下的具体项目/科目明细吗？

## C4 按资金性质分组统计缴款金额

- 状态：成功（returncode=0，SQL次数=3，耗时 150.4s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：search_semantic_objects → glob → execute_sql → grep
- **SQL**：
```sql
SELECT
    ffundsnaturecode AS funds_nature_code,
    ffundsnaturename AS funds_nature_name,
    count() AS row_count,
    round(sum(famt), 2) AS pay_amt
FROM yunnan0508.fne_paybook_full_high
GROUP BY ffundsnaturecode, ffundsnaturename
ORDER BY pay_amt DESC
```
- **答案**：
> 查询完成。按资金性质分组的缴款金额如下（表：`fne_paybook_full_high`，金额 = `SUM(famt)` 全口径缴款金额，全表 1,272 行）：
> 
> | 资金性质码 | 资金性质 | 缴款金额（元） | 行数 | 金额占比 |
> |---|---|---:|---:|---:|
> | 12 | 政府性基金预算收入 | 18,316,046,350.64 | 1,083 | ≈99.9% |
> | 2 | 财政专户管理资金 | 14,867,151.04 | 86 | ≈0.08% |
> | 11 | 一般公共预算收入 | 1,293,101.45 | 97 | ≈0.007% |
> | 5 | 其他 | 600.00 | 6 | ≈0.000003% |
> | **合计** | | **18,332,214,203.13** | **1,272** | 100% |
> 
> **口径说明**：
> - 缴款金额按指标标准取 `SUM(famt)`（非税缴款金额，全业务类型口径，未按 fbustype 过滤）；
> - 分组用中文名 `ffundsnaturename` 展示、码列 `ffundsnaturecode` 对应（String 型，100% 非空，无空码脏行）；
> - 结果与语义层实测记录完全一致（12 码 = 1,083 行 / 183.16 亿元），政府性基金预算收入占绝对主导。
> 
> SQL（可直接复用）：
> 
> ```sql
> SELECT
>     ffundsnaturecode AS funds_nature_code,
>     ffundsnaturename AS funds_nature_name,
>     count()           AS row_count,
>     round(sum(famt), 2) AS pay_amt
> FROM yunnan0508.fne_paybook_full_high
> GROUP BY ffundsnaturecode, ffundsnaturename
> ORDER BY pay_amt DESC
> ```
> 
> 如需进一步按 **业务类型（直缴/汇缴）**、**执收单位** 或 **时间** 在资金性质内下钻，告诉我即可。

## C5 缴款金额前5的收费项目，按直缴汇缴拆分展示

- 状态：成功（returncode=0，SQL次数=6，耗时 120.6s）
- **命中指标**：
  - search_metrics: 检索=非税缴款金额 直缴 汇缴 口径定义
- 工具调用：list_subject_tree → search_semantic_objects → describe_table → execute_sql → search_metrics
- **SQL**：
```sql
WITH
top5 AS (
    SELECT fitemidcode
    FROM fne_paybook_full_high
    GROUP BY fitemidcode
    ORDER BY SUM(famt) DESC
    LIMIT 5
),
names AS (
    SELECT
        fitemidcode AS item_id,
        argMax(fitemname, ffilldate) AS item_name,
        groupUniqArray(fitemname) AS all_names
    FROM fne_paybook_full_high
    WHERE fitemidcode IN top5
    GROUP BY item_id
),
bus AS (
    SELECT
        fitemidcode AS item_id,
        fbustype AS bustype,
        SUM(famt) AS amt,
        uniqExact(fid) AS cnt_fid
    FROM fne_paybook_full_high
    WHERE fitemidcode IN top5
    GROUP BY item_id, bustype
)
SELECT
    n.item_id AS item_id,
    n.item_name AS item_name,
    n.all_names AS all_names,
    round(SUM(b.amt), 2) AS amt_total,
    round(sumIf(b.amt, b.bustype = '1'), 2) AS amt_direct,
    round(sumIf(b.amt, b.bustype = '2'), 2) AS amt_agg,
    sumIf(b.cnt_fid, b.bustype = '1') AS cnt_direct,
    sumIf(b.cnt_fid, b.bustype = '2') AS cnt_agg
FROM bus AS b
INNER JOIN names AS n ON b.item_id = n.item_id
GROUP BY n.item_id, n.item_name, n.all_names
ORDER BY amt_total DESC
```
- **答案**：
> 查询完成。TOP5 项目按**项目 ID** 归并，直缴/汇缴切片口径遵循指标 `非税缴款金额` 的定义(`famt` 直 SUM,`fbustype='1'`=直缴、`'2'`=汇缴),笔数按 `uniqExact(fid)` 去重生命周期版本。全表历史口径(未加时间过滤)：
> 
> ## 缴款金额 TOP5 收费项目(直缴/汇缴拆分)
> 
> | 排名 | 收费项目 | 项目ID | 缴款金额合计(元) | 直缴金额(元) | 直缴占比 | 汇缴金额(元) | 汇缴占比 | 直缴笔数 | 汇缴笔数 |
> |---|---|---|---|---:|---:|---:|---:|---:|---:|
> | 1 | 农网还贷资金收入 | 530020000079 | 16,044,829,547.49 | 16,014,461,111.69 | 99.81% | 30,368,435.80 | 0.19% | 272 | 25 |
> | 2 | 国有重点煤炭企业生产用电、核工业铀扩散厂和堆化工厂生产用电农网还贷资金 | 530020000081 | 2,238,164,885.91 | 159,670.01 | 0.01% | 2,238,005,215.90 | 99.99% | 53 | 14 |
> | 3 | 民航发展基金收入 | 530020000503 | 30,850,779.08 | 30,758,057.70 | 99.70% | 92,721.38 | 0.30% | 87 | 39 |
> | 4 | 高等学校住宿费 | 530020000028 | 14,841,170.00 | 19,271.00 | 0.13% | 14,821,899.00 | 99.87% | 35 | 5 |
> | 5 | 公办幼儿园保教费 | 530020000823 | 1,156,320.00 | 0.00(无直缴) | — | 1,156,320.00 | 100% | 0 | 1 |
> 
> ### 口径说明
> 
> - **金额**:`fne_paybook_full_high.famt`(缴款通知书明细金额)直 SUM,按 `fbustype` 切片，直缴+汇缴=合计，已逐项勾稽核对一致。
> - **笔数**:`uniqExact(fid)`,剔除 147 个 fid 生命周期多版本重复的影响。
> - **名称变体**：项目 `530020000079` 实测存在两个名称(旧名“农网还贷资金收入”299 行止于 2024-06-27,“农网还贷资金收入**a**”38 行自 2024-06-27 起)，同属一个项目 ID,已按 ID 归并、展示取最新名称。
> - **数据窗口**：未加时间过滤，覆盖表内全量历史(最早 2021-12-21 起)。
> 
> ### 复核 SQL
> 
> ```sql
> WITH
> top5 AS (
>     SELECT fitemidcode FROM fne_paybook_full_high
>     GROUP BY fitemidcode ORDER BY SUM(famt) DESC LIMIT 5
> ),
> names AS (
>     SELECT fitemidcode AS item_id,
>            argMax(fitemname, ffilldate) AS item_name,
>            groupUniqArray(fitemname) AS all_names
>     FROM fne_paybook_full_high
>     WHERE fitemidcode IN top5
>     GROUP BY item_id
> ),
> bus AS (
>     SELECT fitemidcode AS item_id, fbustype AS bustype,
>            SUM(famt) AS amt, uniqExact(fid) AS cnt_fid
>     FROM fne_paybook_full_high
>     WHERE fitemidcode IN top5
>     GROUP BY item_id, bustype
> )
> SELECT n.item_id, n.item_name, n.all_names,
>        round(SUM(b.amt), 2) AS amt_total,
>        round(sumIf(b.amt, b.bustype = '1'), 2) AS amt_direct,
>        round(sumIf(b.amt, b.bustype = '2'), 2) AS amt_agg,
>        sumIf(b.cnt_fid, b.bustype = '1') AS cnt_direct,
>        sumIf(b.cnt_fid, b.bustype = '2') AS cnt_agg
> FROM bus b INNER JOIN names n ON b.item_id = n.item_id
> GROUP BY n.item_id, n.item_name, n.all_names
> ORDER BY amt_total DESC
> ```
> 
> **观察**：TOP5 内呈现两种典型模式——大额基金类(农网还贷、民航基金)以直缴为主，而行政事业性收费类(住宿费、保教费)及煤炭用电还贷资金几乎全部走汇缴；保教费全量 1 笔汇缴，样本极少。

## D1 按归属区划统计清分金额

- 状态：成功（returncode=0，SQL次数=5，耗时 84.3s）
- **命中指标**：
  - search_metrics: 检索=清分金额
- 工具调用：list_subject_tree → search_metrics → search_semantic_objects → describe_table → execute_sql
- **SQL**：
```sql
SELECT count() AS n, sum(fimamt) AS clear_amt, sum(famt) AS pay_amt FROM yunnan0508.fne_paybook_full_high WHERE frecrgncode = ''
```
- **答案**：
> 已核实完毕。空区划组 544 行的 `fimamt`（已清分金额）全为 NULL，金额按 0 处理即可（该组其实是**已缴款 23.14 亿但尚未清分**的明细，不是脏数据）。
> 
> ## 统计结果：按归属区划的清分金额
> 
> | 归属区划代码 | 区划名称 | 明细行数 | 清分金额（元） |
> |---|---|---:|---:|
> | 530000 | 云南省本级 | 686 | 16,016,072,677.53 |
> | 000000 | 中央 | 31 | 4,516.12 |
> | 530100 | 昆明市本级 | 8 | 1,778.70 |
> | 530102 | 五华区 | 1 | 495.33 |
> | 532929 | 云龙县 | 2 | 0.00 |
> | （空） | 未填归属区划 | 544 | 0.00（fimamt 全 NULL） |
> 
> **合计 1,272 行，清分金额总计 160.16 亿元**，几乎全部集中在云南省本级（530000）。
> 
> ## 可执行 SQL（ClickHouse）
> 
> ```sql
> SELECT
>     if(frecrgncode = '', '(未填)', frecrgncode) AS frecrgncode,
>     any(frecrgnname)                            AS frecrgnname,
>     count()                                     AS rows_cnt,
>     COALESCE(sum(fimamt), 0)                    AS clear_amt   -- 清分金额（元）
> FROM yunnan0508.fne_paybook_full_high
> GROUP BY frecrgncode
> ORDER BY clear_amt DESC;
> ```
> 
> ## 口径说明
> 
> - **清分金额** = `SUM(fne_paybook_full_high.fimamt)`，与语义层指标「清分金额」完全一致（明细行已清分金额，Nullable Decimal(18,6)，NULL 视为 0）。
> - **归属区划** = `frecrgncode / frecrgnname`（资金归属区划，表内已内联名称，无需额外 join 维表）。
> - **全口径**：包含直缴/汇缴所有 `fbustype` 行；如需“直缴清分金额”，按既有硬规则分子分母同加 `fbustype = '1'` 过滤即可。
> - 空区划组是“已缴款未清分”的真实业务状态（缴款金额 23.14 亿），如后续要做**清分率**分析，这组是重点漏斗观察对象。
> 
> 需要我进一步展开（例如按月份趋势 × 区划，或补一列清分率 = fimamt/famt）吗？

## D2 按执收区划名称统计缴款金额

- 状态：成功（returncode=0，SQL次数=2，耗时 88.5s）
- **命中指标**：
  - search_metrics: 检索=非税缴款金额 缴款金额
- 工具调用：list_tables → search_semantic_objects → search_metrics → describe_table → execute_sql
- **SQL**：
```sql
SELECT
    fchgrgnname AS collect_region_name,
    ROUND(SUM(famt), 2) AS pay_amt,
    uniqExact(fid) AS pay_cnt,
    ROUND(SUM(famt) / uniqExact(fid), 2) AS avg_amt
FROM yunnan0508.fne_paybook_full_high
GROUP BY fchgrgnname
ORDER BY pay_amt DESC
```
- **答案**：
> 查询完成。按执收单位所在区划（`fne_paybook_full_high.fchgrgnname`）汇总的缴款情况如下：
> 
> ## 按执收区划统计缴款金额
> 
> | 执收区划名称 | 缴款金额（元） | 缴款笔数（去重 fid） | 笔均金额（元） |
> |---|---:|---:|---:|
> | 云南省本级 | 18,330,965,893.01 | 1,081 | 16,957,415.26 |
> | 云龙县 | 1,156,320.00 | 1 | 1,156,320.00 |
> | 五华区 | 79,406.12 | 6 | 13,234.35 |
> | 昆明市本级 | 5,184.00 | 9 | 576.00 |
> | 官渡区 | 400.00 | 4 | 100.00 |
> | **合计** | **18,332,205,003.13** | **1,101** | — |
> 
> **口径说明**
> 
> - **表**：`fne_paybook_full_high`（缴款书全生命周期宽表，明细行粒度，共 1,272 行）
> - **执收区划**：取内联列 `fchgrgnname`（执收单位所在区划名称），与 `fchgrgncode` 一一对应，语义层明确"分组展示优先用本列"；实测 5 个区划 100% 非空
> - **缴款金额**：`SUM(famt)`，缴款通知书明细金额（元），明细行口径可直 SUM
> - **缴款笔数**：`uniqExact(fid)`，因 147 个 fid 存在生命周期多版本重复，不能用行数直接当笔数
> - 全量口径，未按 `fbustype`（直缴/汇缴）、`fstate` 等条件过滤，也未限定时间范围
> 
> **值得注意**：云南省本级占绝对主导（18,330.97 亿元，笔均约 1,696 万元），其余 4 个区划合计仅约 124 万元，笔均差异极大（官渡区笔均仅 100 元）——若您关注的是州市/区县级的收入分布，可能需要改按**资金归属区划 `frecrgnname`**（州市/区县维度）统计，但该列与执收区划实测有 584 行不一致，跨区归因口径需业务确认。需要我按归属区划再出一版，或按时间/业务类型（直缴、汇缴）切片吗？

## D3 五华区的执收单位有哪些、各收了多少钱？

- 状态：成功（returncode=0，SQL次数=6，耗时 98.3s）
- **命中指标**：
  - search_metrics: 检索=非税缴款金额 实缴金额
- 工具调用：search_semantic_objects → search_metrics → describe_table → list_tables → execute_sql
- **SQL**：
```sql
SELECT
    fchgrgnname AS agen_rgn,
    count() AS row_cnt,
    uniqExact(fid) AS bill_cnt,
    round(sum(famt), 2) AS amt
FROM fne_paybook_full_high
GROUP BY fchgrgnname
ORDER BY amt DESC
```
- **答案**：
> 查询完成。结果如下（口径：`fne_paybook_full_high` 缴款书宽表，按执收单位区划 `fchgrgnname='五华区'` 过滤；金额 = SUM(famt) 缴款明细金额，笔数 = uniqExact(fid) 去重）：
> 
> ## 五华区执收单位及缴款情况
> 
> | 执收单位 | 缴款笔数 | 缴款金额（元） |
> |---|---:|---:|
> | 智能核销五华区测试单位开票点 | 4 | 77,324.80 |
> | 李思维 | 1 | 1,981.32 |
> | 开票点001 | 1 | 100.00 |
> | **合计** | **6** | **79,406.12** |
> 
> ## 说明
> 
> 1. **数据特征**：当前库为测试环境，五华区的执收单位均为测试单位（全表五华区仅 7 行明细 / 6 笔缴款 / 79,406.12 元，对比云南省本级 183.3 亿元），金额量级很小属正常。
> 
> 2. **对照口径**——若按“资金归属五华区”（`frecrgnname='五华区'`）统计，结果明显不同：仅 **李思维 1 笔 / 990.66 元**。原因是执收单位区划与资金归属区划在测试数据中大量不一致（全表 1,272 行中 584 行两者不匹配），例如同一执收单位的不同明细行可归属不同区划。
> 
> 3. 两个口径验证自洽：按执收区划分组的三家单位金额之和 = 79,406.12 元，与全表区划分布中五华区行完全一致。
> 
> **日常回答“某区的执收单位收了多少钱”建议用第一种口径（执收单位区划）**，即“五华区下辖单位征收的款项”；若您关心的是“缴入五华区财政的资金”，则用第二种口径。需要按缴款方式（直缴/汇缴）或缴款项目进一步拆分的话可以继续查。

## D4 各收款银行2022年各收了多少笔、多少钱？

- 状态：成功（returncode=0，SQL次数=2，耗时 75.4s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：describe_table → search_semantic_objects → execute_sql
- **SQL**：
```sql
SELECT
    trim(frecbankname) AS bank_name,
    uniqExact(fid) AS bill_cnt,
    round(sum(famt), 2) AS total_amt
FROM fne_paybook_full_high
WHERE toYear(toDate(ffilldate)) = 2022
GROUP BY bank_name
ORDER BY total_amt DESC
```
- **答案**：
> ## 各收款银行 2022 年收款统计
> 
> 数据源：`fne_paybook_full_high`（缴款书全生命周期宽表），时间轴 `fill_date = toDate(ffilldate)` = 2022 年。
> 
> | 收款银行 | 笔数 | 金额（元） | 金额（亿元） |
> |---|---:|---:|---:|
> | 中国建设银行 | 226 | 18,208,121,939.04 | ≈182.08 |
> | 中国银行 | 107 | 800,419.02 | ≈80.04 万 |
> | 中国邮政储蓄银行 | 7 | 7,778.00 | 0.78 万 |
> | 中国工商银行 | 11 | 5,426.21 | 0.54 万 |
> | 中国农业银行 | 3 | 510.00 | 510 元 |
> | 中国光大银行 | 1 | 500.00 | 500 元 |
> | **合计** | **355** | **18,208,936,572.27** | **≈182.09 亿** |
> 
> **口径说明：**
> - **笔数**用 `uniqExact(fid)`：该表 147 个 fid 存在生命周期多版本重复（1,272 行物理记录），直接 `count()` 会虚增；分组笔数合计 355 笔与 2022 年度总笔数校验一致。
> - **金额**为 `SUM(famt)`（缴款通知书明细金额），全额口径；建行以 226 笔 / 182.08 亿元占绝对主导（≈99.99%），其余银行单笔金额都很小。
> - 银行名称字段 `frecbankname` 实测带尾部空格，已做 `trim()` 归组；2022 年无“人民银行/支付宝/云南省农村信用社联合社”的记录（这三家出现在其他年份）。
> 
> ```sql
> SELECT
>     trim(frecbankname) AS bank_name,
>     uniqExact(fid)             AS bill_cnt,
>     round(sum(famt), 2)        AS total_amt
> FROM fne_paybook_full_high
> WHERE toYear(toDate(ffilldate)) = 2022
> GROUP BY bank_name
> ORDER BY total_amt DESC
> ```

## D5 归属区划在云南省本级以外的缴款金额有多少？

- 状态：成功（returncode=0，SQL次数=3，耗时 151.3s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：describe_table → search_semantic_objects → glob → execute_sql
- **SQL**：
```sql
SELECT
    round(sumIf(famt, frecrgnname = '云南省本级'), 2)                                    AS prov_amt,
    round(sumIf(famt, frecrgnname != '云南省本级'), 2)                                   AS non_prov_amt_incl_blank,
    uniqExactIf(fid, frecrgnname != '云南省本级')                                        AS non_prov_bill_cnt,
    round(sumIf(famt, frecrgnname != '云南省本级' AND frecrgnname != ''), 2)             AS non_prov_amt_named,
    round(sumIf(famt, frecrgnname = ''), 2)                                             AS blank_amt
FROM fne_paybook_full_high
```
- **答案**：
> ## 结论
> 
> 按缴款书宽表 `fne_paybook_full_high` 的**资金归属区划（frecrgnname）**统计，缴款金额（famt，票面应收口径）分布如下：
> 
> | 口径 | 金额（元） | 笔数 |
> |---|---|---|
> | **省本级以外（区划有明确值）** | **1,169,469.34（约 116.9 万）** | 41 笔 |
> | 归属区划为空（未落值） | 2,314,603,154.58（约 23.15 亿） | 544 笔 |
> | 合计（含空串宽口径） | 2,315,772,623.92（约 23.16 亿） | 585 笔 |
> 
> **省本级以外的明细构成**（明确非省本级的 41 笔）：
> 
> | 归属区划 | 代码 | 金额（元） | 笔数 |
> |---|---|---|---|
> | 云龙县 | 532929 | 1,156,320.00 | 1 |
> | 中央 | 000000 | 9,617.68 | 31 |
> | 昆明市本级 | 530100 | 2,541.00 | 8 |
> | 五华区 | 530102 | 990.66 | 1 |
> 
> 对比：云南省本级 = 16,016,434,579.21 元（554 笔），占绝对主体。
> 
> ## 口径说明（需注意）
> 
> 1. **两套答案取决于如何对待空值**：若问的是“区划明确标注为非省本级”的缴款，答案是 **约 116.9 万元**；若把归属区划为空的 544 笔（23.15 亿，占全表 43%）也视为“非省本级”，则合计约 23.16 亿元。空串这批资金归属区划未落值，按建模备注（fchgrgnname 描述），跨区归因口径需业务确认，建议先向业务方核实这批数据的归属。
> 2. 笔数按 `uniqExact(fid)` 去重（fid 存在生命周期多版本重复，非唯一键）；金额为票面应收金额（famt），不等于实缴/清分金额。
> 3. 另外“中央”000000 这 31 笔虽非省本级，但也不属于任何地方区划，是否计入“省本级以外”可按业务需要取舍（剔除后为 116.85 万）。
> 
> ## 查询 SQL
> 
> ```sql
> -- 省本级以外（区划有明确值）
> SELECT
>     round(sum(famt), 2)          AS non_prov_amt,
>     uniqExact(fid)               AS non_prov_bill_cnt
> FROM fne_paybook_full_high
> WHERE frecrgnname != '' AND frecrgnname != '云南省本级';
> ```

## E1 已划拨和未划拨的金额各是多少？

- 状态：成功（returncode=0，SQL次数=12，耗时 188.0s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：search_semantic_objects → bash → execute_sql → describe_table → add_memory → edit_memory
- **SQL**：
```sql
SELECT
  multiIf(istransfer_grp = '1', '已划拨', '未划拨') AS status,
  uniqExact(fcollectid) AS batches,
  round(sum(batch_amt), 2) AS amount
FROM (
  SELECT
    fcollectid,
    max(fistransfer) AS istransfer_grp,
    max(ftransamt) AS batch_amt
  FROM fne_funddivide_transfer
  WHERE fistransfer IN ('0', '1') AND ftransamt IS NOT NULL
  GROUP BY fcollectid
)
GROUP BY istransfer_grp
ORDER BY istransfer_grp
```
- **答案**：
> ## 结论
> 
> **已划拨 21,024.00 元（34 个批次），未划拨 38,142.30 元（87 个批次）**，合计 59,166.30 元。
> 
> | 划拨状态 | 批次数 | 划拨金额（元） |
> |---|---:|---:|
> | 已划拨（fistransfer='1'） | 34 | 21,024.00 |
> | 未划拨（fistransfer='0'） | 87 | 38,142.30 |
> | **合计** | **121** | **59,166.30** |
> 
> ## 口径说明（重要）
> 
> 数据源为 `fne_funddivide_transfer`（清分划拨批次明细，728 行），按语义模型权威口径 `fistransfer='1'`/`!=1'` 收窄。本次实测发现一个金额重复计数陷阱：
> 
> - **批次头行（fid=fcollectid）与明细行都携带整批金额**：直 SUM 会得到 72,507.62 元，虚增约 22%。实测 0 个批次内出现多个不同金额，说明每行都是整批总额的拷贝。
> - 因此金额必须**先按 fcollectid 去重（取 max）再汇总**。
> - 另有 568 行 `fistransfer=''`（尚未进入划拨流程的清分明细，ftransamt 全 NULL，fimamt 约 160.16 亿），不在本口径内。
> 
> ## 验证 SQL
> 
> ```sql
> SELECT
>   multiIf(istransfer_grp = '1', '已划拨', '未划拨') AS status,
>   uniqExact(fcollectid) AS batches,
>   round(sum(batch_amt), 2) AS amount
> FROM (
>   SELECT
>     fcollectid,
>     max(fistransfer) AS istransfer_grp,
>     max(ftransamt)   AS batch_amt
>   FROM fne_funddivide_transfer
>   WHERE fistransfer IN ('0', '1') AND ftransamt IS NOT NULL
>   GROUP BY fcollectid
> )
> GROUP BY istransfer_grp
> ORDER BY istransfer_grp
> ```
> 
> 测试数据金额量级较小（万元级），如需看占比或按执收单位/科目下钻，随时说。

## E2 缴库报文里已确认入库和待国库确认的金额各是多少？

- 状态：成功（returncode=0，SQL次数=2，耗时 91.6s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：list_tables → search_semantic_objects → grep → read_file → execute_sql
- **SQL**：
```sql
SELECT
    fstatus AS jiaoku_status,
    toString(fincomestatus) AS income_status,
    uniqExact(fid) AS fid_cnt,
    round(SUM(ftotalamt), 2) AS total_amt
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY fid) AS _rn
    FROM yunnan0508.fne_treasury_transfer_new
)
WHERE _rn = 1
GROUP BY fstatus, income_status
ORDER BY jiaoku_status, income_status
```
- **答案**：
> 两个口径的金额已算出，且与语义模型的对账基准完全吻合（76 笔合计 29,535,106.14 = 三组之和 ✓）。
> 
> ## 缴库报文状态金额（按 fid 去重口径，物理表 `fne_treasury_transfer_new` 505 行去重后 76 行）
> 
> | 缴库状态 | 入库确认状态 | 笔数（fid） | 金额（元） |
> |---|---|---:|---:|
> | **已缴库 + 已确认入库** | `fstatus='9'` & `fincomestatus='1'` | **23** | **11,064.00** |
> | **已缴库 + 待国库确认** | `fstatus='9'` & `fincomestatus='0'` | **3** | **35,240.09** |
> 
> - **已确认入库：11,064.00 元**（23 笔，23 个缴库批次）
> - **待国库确认：35,240.09 元**（3 笔，3 个缴库批次）
> 
> 几点口径说明：
> 
> 1. **去重必须先于求和**：物理表 505 行含 33 个重复 `fid` 组（多版本重复报文），直接 SUM 会虚增约 44 倍；本次用 `ROW_NUMBER() OVER (PARTITION BY fid)=1` 去重，与建模时的对账指纹一致。
> 2. **状态取值形态**：`fincomestatus` 为 String 型，过滤值必须带引号（'0'/'1'）；`fstatus='9'` 表示已缴库。语义层实测确认 `fincomestatus` 与 `fid` 完全绑定，去重后状态稳定，可安全按 fid 口径过滤。
> 3. **易混淆项**：语义层提到的“415.5 万待确认中间态”是 505 行**未去重**的行数口径；去重后真实的已缴库待确认金额就是上表的 35,240.09 元。
> 4. 其余 50 笔（29,488,802.05 元）为 `fstatus='0'` 的未缴库报文，不属于“已缴库”两种状态，故未计入。
> 
> 本次统计 SQL（去重口径，可复用）：
> 
> ```sql
> SELECT
>     fstatus,
>     toString(fincomestatus) AS income_status,
>     uniqExact(fid) AS fid_cnt,
>     round(SUM(ftotalamt), 2) AS total_amt
> FROM (
>     SELECT *, ROW_NUMBER() OVER (PARTITION BY fid) AS _rn
>     FROM yunnan0508.fne_treasury_transfer_new
> )
> WHERE _rn = 1
> GROUP BY fstatus, income_status;
> ```

## E3 汇总批次一共多少个？

- 状态：成功（returncode=0，SQL次数=4，耗时 94.6s）
- **命中指标**：（未走指标/检索路径）
- 工具调用：list_tables → search_semantic_objects → describe_table → execute_sql
- **SQL**：
```sql
SELECT
  'funddivide_transfer' AS tbl,
  round(sum(fimamt), 2) AS sum_imamt,
  uniqExact(fcollectid) AS batches_all_incl_empty,
  uniqExact(fid) AS uniq_fid
FROM yunnan0508.fne_funddivide_transfer
UNION ALL
SELECT
  'funddivide_new',
  round(sum(fimamt), 2),
  uniqExact(fcollectid),
  uniqExact(fid)
FROM yunnan0508.fne_funddivide_new
```
- **答案**：
> ## 汇总批次数：428 个
> 
> **口径说明**：汇总批次 = 清分汇总批次，批次 ID 为 `fcollectid`（在 `fne_funddivide_transfer` / `fne_funddivide_new`，两表为同一份数据，均 728 行）。按建模时的硬规则，批次数口径 = `uniqExact(fcollectid)`。
> 
> ### 实测结果
> 
> | 口径 | 数量 |
> |---|---|
> | **有效汇总批次（`fcollectid != ''` 去重）** | **428 个** |
> | 其中：有批次头行的批次（`fid = fcollectid`） | 425 个 |
> | 其中：仅有明细行、无头行的批次 | 3 个 |
> | 未汇总入批次的清分明细行（`fcollectid = ''`，共 178 行） | 不计为批次 |
> | 若把空串也算一个“值” | 429（无效口径，不建议） |
> 
> 批次覆盖时间范围：`fcleardate` 2022-01-25 ~ 2026-08-03。
> 
> ### 验证 SQL
> 
> ```sql
> SELECT
>   count()                                        AS total_rows,
>   uniqExactIf(fcollectid, fcollectid != '')      AS batches_nonempty,
>   countIf(fcollectid = '')                       AS rows_empty_key,
>   countIf(fcollectid != '' AND fid = fcollectid) AS header_rows   -- 批次头行数
> FROM yunnan0508.fne_funddivide_transfer;
> ```
> 
> ### 补充（结合此前实测结论）
> 
> - `fcollectid` 因生命周期多版本在表内非唯一（550 行非空键明细对应 428 个批次），所以必须用 `uniqExact` 去重计数，**不能 count(distinct 之外的行数)**。
> - 若你关心的是“已划拨”的批次：按 `ftransamt` 按 `fcollectid` 去重取 max 的口径，**已划拨('1') 34 批次、未划拨('0') 87 批次**（有划拨金额的共 121 批次），其余 307 个批次尚无划拨金额记录。

## E4 未清分的缴款笔数和金额是多少？

- 状态：成功（returncode=0，SQL次数=2，耗时 79.5s）
- **命中指标**：
  - search_metrics: 检索=未清分 缴款笔数 缴款金额 清分金额
  - search_metrics: 检索=非税缴款笔数 非税缴款金额 定义
- 工具调用：search_semantic_objects → list_subject_tree → search_metrics → execute_sql
- **SQL**：
```sql
SELECT
    COUNT(DISTINCT fid) AS cnt_uncleared,
    ROUND(SUM(famt), 2) AS amt_uncleared
FROM yunnan0508.fne_paybook_full_high
WHERE fisclear = '0'
```
- **答案**：
> 查询完成，结果如下：
> 
> ## 未清分的缴款笔数和金额
> 
> | 指标 | 数值 |
> |---|---|
> | **未清分缴款笔数** | **515 笔**（按 `fid` 去重口径） |
> | **未清分缴款金额** | **2,314,588,645.58 元**（约 **23.15 亿元**） |
> 
> **口径说明**（与语义层已固化的定义一致）：
> - **表**：`fne_paybook_full_high`（缴款通知书明细全量表）
> - **未清分过滤**：`fisclear = '0'`（语义字段 `is_cleared`，实测值域仅 0/1 无 NULL，515 行与行数完全吻合，说明每行 fid 唯一）
> - **笔数**：`COUNT(DISTINCT fid)` —— 与"非税缴款笔数"指标同口径
> - **金额**：`SUM(famt)` —— 与"非税缴款金额"指标同口径（缴款通知书明细金额）
> 
> 与已清分（`fisclear='1'`，757 行）对比，未清分约占全部缴款明细的 40.5%，可作为催缴/清分跟进的重点关注对象。

## E5 清分率按业务类型分组对比：直缴和汇缴各是多少？

- 状态：成功（returncode=0，SQL次数=4，耗时 89.9s）
- **命中指标**：
  - search_metrics: 检索=清分率 清分 按业务类型
- 工具调用：search_metrics → search_semantic_objects → execute_sql
- **SQL**：
```sql
SELECT
    count() AS detail_rows,
    uniqExact(fpaycode) AS pay_count,
    round(SUM(famt), 2) AS non_tax_amt,
    round(SUM(fimamt), 2) AS clear_amt,
    round(SUM(fimamt) / SUM(famt) * 100, 2) AS clear_rate_pct
FROM yunnan0508.fne_paybook_full_high
```
- **答案**：
> 查询完成。基于语义模型 `fne_fund_main` 的清分率口径（清分金额 fimamt ÷ 非税缴款金额 famt，同在 `fne_paybook_full_high` 行内，按 fbustype 分组时比值逐组成立）：
> 
> ## 清分率按业务类型对比
> 
> | 业务类型 | 明细行数 | 缴款笔数 | 非税缴款金额（元） | 清分金额（元） | 清分率 |
> |---|---|---|---|---|---|
> | **直缴**（fbustype='1'） | 1,063 | 848 | 160.47 亿 | 160.16 亿 | **99.80%** |
> | **汇缴**（fbustype='2'） | 209 | 120 | 22.85 亿 | 8.02 万 | **≈0.00%**（实际 0.0035%） |
> | 整体（全类型，对照） | 1,272 | 968 | 183.32 亿 | 160.16 亿 | 87.37% |
> 
> **要点：**
> 
> - **直缴基本全额清分**：1,063 行 / 848 笔，清分率 99.80%，未清分缺口仅约 3,141 万元。
> - **汇缴几乎未清分**：120 笔汇缴缴款（22.85 亿元）中仅 80,244.80 元有清分记录，占比约 0.0035%（四舍五入显示为 0.00%）——汇缴资金链基本停留在“待清分”状态。
> - **整体清分率 87.37%** 完全由直缴贡献：直缴占全部缴款金额的 87.5%（160.47/183.32），其近乎全额清分抬高了整体值；若只看汇缴，资金链滞留问题显著。
> - 口径说明：整体行是“含全类型”的比值（分子分母同表全 SUM），与分组行“组内比值”不可直接相加平均。
> 
> 复用 SQL（分组行）：
> 
> ```sql
> SELECT
>     multiIf(fbustype = '1', '直缴', fbustype = '2', '汇缴', concat('其他:', fbustype)) AS bustype_name,
>     count() AS detail_rows,
>     uniqExact(fpaycode) AS pay_count,
>     round(SUM(famt), 2) AS non_tax_amt,
>     round(SUM(fimamt), 2) AS clear_amt,
>     round(SUM(fimamt) / SUM(famt) * 100, 2) AS clear_rate_pct
> FROM yunnan0508.fne_paybook_full_high
> GROUP BY fbustype
> ORDER BY fbustype
> ```
