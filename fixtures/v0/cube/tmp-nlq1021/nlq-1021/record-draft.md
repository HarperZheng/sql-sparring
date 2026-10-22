# fne_fund_main 问数实测记录（agent-svc 全链路 30 问）

> 2026-10-21 实测。链路：`POST :4100/chat {question, sessionId}` → agent-svc（claude Agent SDK，effort low）
> → cube-ask skill 主链四步（就绪→解析→/agent/query→整理三态）→ 原样透传。每问独立 sessionId，无会话记忆污染。
>
> 「生成的 SQL」两层留痕：① **语义层 query JSON**（`tables[].query`，agent 真正生成的东西）
> ② **Cube 编译 SQL**（`/cubejs-api/v1/sql` 对同一 query 编译的 ClickHouse 方言，agent 链路本身不产裸 SQL）。
>
> 原始三态 JSON：`D:/develop/cube/.tmp/nlq-1021/raw|sql/`（.tmp 已 gitignore）；过程日志 `D:/develop/cube/logs/agent-svc-*.log`。
> 基准列摘自 [08-自然语言问数能回答的问题](08-fne_fund_main自然语言问数能回答的问题.md)；「复核」为人工对照结论。

## 结论速览

| # | 问题 | 判定 | 耗时s | 基准 |
|---|---|---|---|---|
| q01 | 2022 年全年非税缴款金额和笔数是多少？ | ask→追问后 answer | 38.0 | 183.32 亿 / 1,101 笔 |
| q02 | 非税缴款金额按月展示，并给出环比 | answer（可答） | 48.4 | — |
| q03 | 清分金额 2022 年对比 2021 年同比增长多少？ | answer（可答） | 43.5 | 同比指标（28 号方案固化族） |
| q04 | 缴库金额按年汇总 2022 到 2026 各年多少？ | answer（可答） | 24.7 | 报文日期轴 |
| q05 | 全库累计清分了多少、清分率是多少？ | ask→追问后 answer | 27.9 | 160.16 亿 / 0.8737 |
| q06 | 2022 年缴款金额排名前 10 的执收单位 | answer（可答） | 25.0 | — |
| q07 | 主管单位测试云南省教育厅1的下级单位合计缴款多少？ | nomatch（答不了） | 52.4 | 教育厅系实测 160.47 亿（parent_agen 树自联结） |
| q08 | 各执收预算单位（主管预算单位）的清分金额对比 | answer（可答） | 29.3 | — |
| q09 | 哪些非叶子单位自己直接收了款？ | nomatch（答不了） | 22.5 | 1 级也有 23 个叶子单位可直接挂缴款 |
| q10 | 按执收单位统计未到账（欠缴）的缴款笔数 | ask→追问后 answer | 23.5 | is_received='0'，F11 催缴场景 |
| q11 | 各预算科目清分金额排行，政府性基金收入（103）大类下哪些叶子科目收得最多？ | answer（可答） | 30.2 | 103 大类叶子科目 |
| q12 | 民航发展基金历年缴款趋势 | answer（可答） | 71.5 | 科目树下钻实测 3,085.08 万 |
| q13 | 按收入分类统计：政府性基金收入、专项收入、行政事业性收费、罚没各占多少？ | error（链路失败） | 70.9 | — |
| q14 | 按资金性质分组：一般公共预算、政府性基金、财政专户管理资金各收多少？ | answer（可答） | 26.9 | — |
| q15 | 缴款金额前 5 的收费项目，按直缴汇缴拆分展示 | answer（可答） | 26.1 | — |
| q16 | 按归属区划统计清分金额 | answer（可答） | 31.5 | 州市/区县内联维度 |
| q17 | 按执收区划名称统计缴款金额 | answer（可答） | 39.0 | fchgrgnname，5 区划全分布 |
| q18 | 五华区的执收单位有哪些、各收了多少钱？ | answer（可答） | 34.4 | — |
| q19 | 各收款银行（代理银行）2022 年各收了多少笔、多少钱？ | answer（可答） | 22.4 | frecbankname，9 家银行 100% 非空 |
| q20 | 归属区划在云南省本级以外的缴款有多少？ | answer（可答） | 31.8 | frecrgnname 含空串与「中央」特殊值 |
| q21 | 已划拨和未划拨的金额各是多少？ | answer（可答） | 47.8 | 已划拨 24,815 / 未划拨 47,692.62 |
| q22 | 缴库报文里已确认入库和待国库确认的金额各多少？ | answer（可答） | 23.0 | (9,1)=24 行 / (9,0) 中间态 415.5 万 |
| q23 | 汇总批次一共多少个？ | ask→追问后 answer | 30.0 | 正确口径 428（expression 含空串假批次缺陷） |
| q24 | 未清分的缴款笔数和金额是多少？ | answer（可答） | 30.8 | is_cleared='0'，515 行 |
| q25 | 清分率按业务类型分组对比：直缴和汇缴各是多少？ | ask→追问后 answer | 37.6 | instructions 已写明逐组成立 |
| q26 | 划拨金额按划入的下级区划和划入单位拆分统计 | answer（可答） | 30.3 | 期望 nomatch：无区划层级 dim、fsharerate 缓建、划入单位族全空 |
| q27 | 财政专户收入和国库收入分别是多少？ | answer（可答） | 21.3 | 期望 nomatch：只能 funds_nature='2' 近似，无命名指标 |
| q28 | 2022 年缴款金额排名前 10 的缴款人 | answer（可答） | 26.2 | 期望 nomatch：缴款人维度未建模 |
| q29 | 汇缴缴款的缴款明细记录有哪些？ | ask→追问后 answer | 21.8 | 期望 nomatch：une_ 汇缴体系明细未建模 |
| q30 | 各笔缴款的到账日期和退付金额是多少？ | nomatch（答不了） | 22.7 | 期望 nomatch：到账日期轴/退付缓建未建模 |

**判定分布**：answer 20 / ask 6（其中追问后出 answer 6）/ nomatch 3 / error 1 / missing 0（共 30）

## 一、总量·趋势·对比

### q01　2022 年全年非税缴款金额和笔数是多少？

- **判定**：ask→追问后 answer（sessionId `nlq1021-q01`，首答 38.0s，预聚合 —）
- **基准**：183.32 亿 / 1,101 笔

**反问**：「非税缴款」在模型 ai_context 和口径词典中均无既定口径，2022 年数据实际分布在两个维度上，口径不同结果差异巨大（18.2 亿 vs 4.6 万元级别），需要您拍板：按哪个维度界定非税？

**选项**：
1. 收入类别（income_sort_name）：政府性基金收入 + 行政事业性收费收入 + 专项收入 三类合计（2022 年该环境无税收类收入，即全部缴款）
2. 资金性质（funds_nature_name）：政府性基金预算收入 + 财政专户管理资金 + 一般公共预算收入 三类合计（即全部缴款）
3. 仅行政事业性收费收入 + 专项收入（狭义非税，剔除政府性基金）
4. 仅政府性基金收入

**追问**（同会话续问，耗时 42.2s）：就按第一个选项的口径来（收入类别（income_sort_name）：政府性基金收入 + 行政事业性收费收入 + 专项收入 三类合计（2022 年该环境无税收类收入，即全部缴款）），直接出答案。

**表1：2022年非税缴款合计（收入类别三类口径，pay_date）**（1 行）

| amt | paybook_count |
|---|---|
| 18208936572.27 | 334 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.paybook_count"
  ],
  "dimensions": [],
  "filters": [],
  "timeDimensions": [
    {
      "dimension": "fiscal_collection_view.pay_date",
      "dateRange": [
        "2022-01-01",
        "2022-12-31"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
```

</details>

**歧义拍板**：非税缴款 = income_sort_name 三类（政府性基金收入/行政事业性收费收入/专项收入）合计，2022-10-21 用户拍板

**答案文本**：口径声明：「非税缴款」按您拍板的收入类别（income_sort_name）口径 = 政府性基金收入 + 行政事业性收费收入 + 专项收入 三类合计；2022 年该环境无税收类收入，故等于全部缴款。时间轴为缴款日期 pay_date（2022-01-01 至 2022-12-31）。金额 18,208,936,572.27 元（≈182.09 亿元），缴款书笔数 334 笔（明细行数口径的 count 另计，未随答案列出）。该合计由不带分组维度的全量查询取得（无分母语义，total 置 null），无截断。该拍板已回写口径词典（term=非税缴款）。

**计划**：[["2022年全年非税缴款金额", "fiscal_collection_view.amt", "用户拍板口径：income_sort_name 三类合计，时间轴 pay_date"], ["2022年全年非税缴款笔数（缴款书数）", "fiscal_collection_view.paybook_count", "ai_context：缴款书笔数用 paybook_count，count 是明细行数勿当笔数"]]

> **复核**：基准 183.32 亿/1,101 笔与 Cube 口径不符：Cube 侧 2022 年=182.09 亿/334 缴款书（pay_date 轴），183.32 亿实为**全库**缴款总额（q05/q17 交叉一致）；1,101 笔疑为 Datus 侧 fne_fund_main 明细口径，Cube 侧各口径（缴款书 968、明细 1,272）均未复现。ask 反问合规（income_sort vs funds_nature 分叉），追问选项 1 落地；反问文案中「18.2 亿」与落地 182.09 亿量级不符，系文案瑕疵。

---

### q02　非税缴款金额按月展示，并给出环比

- **判定**：answer（可答）（sessionId `nlq1021-q02`，首答 48.4s，预聚合 命中）
- **基准**：—

**表1：非税缴款金额按月 + 月环比（pay_date 月粒度，全量 57 个月）**（57 行）

| fiscal_collection_view.pay_date.month | fiscal_collection_view.amt | fiscal_collection_view.amt_mom_diff | fiscal_collection_view.amt_mom_rate |
|---|---|---|---|
| 2021-12 | 833 | None | None |
| 2022-01 | 13301 | 12468 | 1496.76 |
| 2022-02 | 40779 | 27478 | 206.59 |
| 2022-03 | 19815 | -20964 | -51.41 |
| 2022-04 | 15985631415 | 15985611600 | 80674295.23 |
| 2022-05 | 494 | -15985630921 | -100 |
| 2022-06 | 4112.9 | 3618.9 | 732.57 |
| 2022-07 | 23 | -4089.9 | -99.44 |
| 2022-08 | 17617.79 | 17594.79 | 76499.09 |
| 2022-09 | 5453.68 | -12164.11 | -69.04 |
| 2022-10 | 38188.35 | 32734.67 | 600.23 |
| 2022-11 | 236799.19 | 198610.84 | 520.08 |
| 2022-12 | 2222928573.36 | 2222691774.17 | 938639.94 |
| 2023-01 | None | None | None |
| 2023-02 | 44876 | None | None |
| 2023-03 | 4086 | -40790 | -90.89 |
| 2023-04 | 5819 | 1733 | 42.41 |
| 2023-05 | 1014 | -4805 | -82.57 |
| 2023-06 | 43409.45 | 42395.45 | 4181.01 |
| 2023-07 | 1171872 | 1128462.55 | 2599.58 |
| 2023-08 | 24457.08 | -1147414.92 | -97.91 |
| 2023-09 | 128914.88 | 104457.8 | 427.11 |
| 2023-10 | 600 | -128314.88 | -99.53 |
| 2023-11 | 37408.6 | 36808.6 | 6134.77 |
| 2023-12 | 3353.3 | -34055.3 | -91.04 |
| 2024-01 | 164244.582 | 160891.282 | 4798 |
| 2024-02 | 46039471.7 | 45875227.118 | 27931.04 |
| 2024-03 | 2864.62 | -46036607.08 | -99.99 |
| 2024-04 | 28982824.78 | 28979960.16 | 1011651.11 |
| 2024-05 | 22063 | -28960761.78 | -99.92 |
| 2024-06 | 5836.24 | -16226.76 | -73.55 |
| 2024-07 | 1405.28 | -4430.96 | -75.92 |
| 2024-08 | 610281.59 | 608876.31 | 43327.76 |
| 2024-09 | 6446.64 | -603834.95 | -98.94 |
| 2024-10 | 141015.21 | 134568.57 | 2087.42 |
| 2024-11 | 7935.54 | -133079.67 | -94.37 |
| 2024-12 | 140047.64 | 132112.1 | 1664.82 |
| 2025-01 | 30695653.3 | 30555605.66 | 21818.01 |
| 2025-02 | 423 | -30695230.3 | -100 |
| 2025-03 | 27734.88 | 27311.88 | 6456.71 |
| 2025-04 | 15413.2 | -12321.68 | -44.43 |
| 2025-05 | None | None | None |
| 2025-06 | 5196.29 | None | None |
| 2025-07 | 1084 | -4112.29 | -79.14 |
| 2025-08 | None | None | None |
| 2025-09 | 1777.33 | None | None |
| 2025-10 | 4582.36 | 2805.03 | 157.82 |
| 2025-11 | 1501 | -3081.36 | -67.24 |
| 2025-12 | 1000.02 | -500.98 | -33.38 |
| 2026-01 | 4632 | 3631.98 | 363.19 |
| 2026-02 | None | None | None |
| 2026-04 | 1982.32 | None | None |
| 2026-05 | 7222 | 5239.68 | 264.32 |
| 2026-06 | 14909895.85 | 14902673.85 | 206351.06 |
| 2026-07 | 752.52 | -14909143.33 | -99.99 |
| 2026-08 | 700.66 | -51.86 | -6.89 |
| 2026-09 | None | None | None |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.amt_mom_diff",
    "fiscal_collection_view.amt_mom_rate"
  ],
  "dimensions": [],
  "timeDimensions": [
    {
      "dimension": "fiscal_collection_view.pay_date",
      "granularity": "month"
    }
  ],
  "order": {
    "fiscal_collection_view.pay_date": "asc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
```

</details>

**歧义拍板**：「非税缴款金额」取 fiscal_collection_view.amt 缴款明细口径、pay_date 月粒度；「环比」按默认月环比（amt_mom 系固化成员）

**答案文本**：口径声明：「非税缴款」按本系统缴款全景口径处理——fiscal_collection_view 即非税收入缴款明细（fne_paybook_full_high），金额取 amt（famt 合计，缴款明细口径），时间轴用 pay_date（缴款日期）月粒度，未设时间范围（全量 2021-12 至 2026-09 共 57 个月，含少量空月）。环比绑定 meta 固化成员 amt_mom_diff / amt_mom_rate（引擎已算，答案层未重复计算）；环比增长率=（本月−上月）÷上月×100，上月为 0 或无数据时为 null（报无法计算，勿按 0），故 2023-02、2025-06、2025-09、2026-04（上月缺失）及 2021-12（首月）环比为 null。近期数据范围：2026-09 缴款金额为空（该月无数据）。口径词典中「非税缴款」无词条，未发现实质口径分叉，如需按资金性质（funds_nature）或 bgt_style 拆分请拍板后可另查。

**计划**：[["非税缴款金额（元，缴款明细口径，按缴款日期 pay_date 月粒度分组）", "fiscal_collection_view.amt", "ai_context：金额明细用 amt；本系统缴款全景即非税收入缴款，无税/非税分叉成员"], ["月环比差值（与上月差，引擎已算）", "fiscal_collection_view.amt_mom_diff", "meta measures 固化成员 amt_mom_diff，粒度必须 month"], ["月环比增长率（%）", "fiscal_collection_view.amt_mom_rate", "meta measures 固化成员 amt_mom_rate，上月为 0/无数据时为 null"]]

> **复核**：✓ 与能力声明一致：固化环比成员（amt_mom_diff/rate）绑定成功，57 个月全分布，上月缺失报 null（合规），预聚合命中。

---

### q03　清分金额 2022 年对比 2021 年同比增长多少？

- **判定**：answer（可答）（sessionId `nlq1021-q03`，首答 43.5s，预聚合 未命中）
- **基准**：同比指标（28 号方案固化族）

**表1：清分金额 2022 年同比（pay_date 年度轴，分入/划拨双口径）**（0 行）

（空集，0 行）

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.im_amt",
    "fiscal_allocation_view.im_amt_yoy_diff",
    "fiscal_allocation_view.im_amt_yoy_rate",
    "fiscal_allocation_view.trans_amt",
    "fiscal_allocation_view.trans_amt_yoy_diff",
    "fiscal_allocation_view.trans_amt_yoy_rate"
  ],
  "timeDimensions": [
    {
      "dimension": "fiscal_allocation_view.pay_date",
      "granularity": "year",
      "dateRange": [
        "2022-01-01",
        "2022-12-31"
      ]
    }
  ],
  "order": {},
  "limit": 10
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
```

</details>

**歧义拍板**："清分金额"未定默认口径：分入金额(im_amt)与划拨金额(trans_amt)双口径并列呈现，未静默选择；空结果按契约直接拍板为该期无数据、同比无法计算，未追加反向探测查询

**答案文本**：口径声明："清分金额"在 fiscal_allocation_view 有两个金额口径——分入金额 im_amt 与划拨金额 trans_amt，词典无该词条、ai_context 未定默认，本次两口径并出（各带引擎已算的同比差值/增长率成员）。数据范围：时间轴 pay_date，2022-01-01～2022-12-31（同比自动平移至 2021 年），按年分组。查询返回 0 行——该时间范围内无清分数据，故两口径的 2022 年同比增长率均无法计算（非 0%）。如需查看其他年份或改用 trans_date/enter_date 轴（注：同环比不支持这两条轴），请明示后另查。

**计划**：[["定位清分主题", "fiscal_allocation_view", "/agent/meta 目录面：清分流向事实（fdt）"], ["绑定同比计算成员（引擎已算）", "fiscal_allocation_view.im_amt_yoy_diff / im_amt_yoy_rate / trans_amt_yoy_diff / trans_amt_yoy_rate", "meta measures 含 _yoy 系，按 2026-10-18 固化族绑定，答案层不重复计算"], ["时间轴用 pay_date 按年分组", "fiscal_allocation_view.pay_date", "ai_context：同环比仅 pay_date 一条轴，平移 1 年"], ["执行查询", "POST /agent/query", "返回 ok:true 但 data 为空（2022 年 pay_date 轴无清分数据）"]]

> **复核**：同比固化成员绑定成功，但 pay_date 轴下清分记录为空→「无法计算」系合规空集拍板。清分事实须换轴才有数（trans/分入侧日期），同环比族按 pay_date 固化——问清分同比需先指定轴，能力**半可用**（成员在、默认轴无数据）。

---

### q04　缴库金额按年汇总 2022 到 2026 各年多少？

- **判定**：answer（可答）（sessionId `nlq1021-q04`，首答 24.7s，预聚合 命中）
- **基准**：报文日期轴

**表1：各年缴库金额（口径：缴库明细 amt，按缴库日期 build_date 年分组，单位元）**（5 行）

| fiscal_treasury_view.build_date.year | fiscal_treasury_view.amt |
|---|---|
| 2022 | 46053.04 |
| 2023 | 34178.26 |
| 2024 | 3463.3 |
| 2025 | 0 |
| 2026 | 29372234.54 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_treasury_view.amt"
  ],
  "dimensions": [],
  "filters": [],
  "timeDimensions": [
    {
      "dimension": "fiscal_treasury_view.build_date",
      "dateRange": [
        "2022-01-01",
        "2026-12-31"
      ],
      "granularity": "year"
    }
  ],
  "order": {
    "fiscal_treasury_view.build_date": "asc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT date_trunc('year', "fiscal_treasury__build_date_month") "fiscal_treasury_view__build_date_year", sum("fiscal_treasury__amt") "fiscal_treasury_view__amt" 
FROM  dev_pre_aggregations.fiscal_treasury_main  AS "fiscal_treasury__main"
WHERE ("fiscal_treasury__build_date_month" >= CAST(? as TIMESTAMP) AND "fiscal_treasury__build_date_month" <= CAST(? as TIMESTAMP))
GROUP BY 1
ORDER BY  1  ASC
LIMIT 1002022-01-01T00:00:00.0002026-12-31T23:59:59.999
```

</details>

**歧义拍板**：未要求入库状态过滤，采用全部缴库明细（不限定已入国库）；若需「已入国库」口径应改用 enter_status='1' 且时间轴 enter_date

**答案文本**：口径声明：缴库金额 = fiscal_treasury_view.amt（缴库明细口径，去重后 sum），时间轴取缴库日期 build_date（建单日），按年分组，范围 2022-01-01 至 2026-12-31。数据范围：查询范围内 2022/2023/2024/2026 有数据；2025 年查询范围内无缴库数据，按 0 报告。各年金额：2022 年 46,053.04 元；2023 年 34,178.26 元；2024 年 3,463.30 元；2025 年 0 元；2026 年 29,372,234.54 元。查询命中预聚合（fiscal_treasury_main），无截断。

**计划**：[["缴库金额按年汇总（2022-2026），时间轴取缴库日期建单日", "fiscal_treasury_view.amt", "ai_context：缴库金额用 amt，趋势按 build_date"], ["按年分组求和", "fiscal_treasury_view.build_date", "时间维度 year 粒度，dateRange 2022-01-01 至 2026-12-31"]]

> **复核**：各年数字与 q22 交叉一致（2022-2024+2026 合计≈29,455,929.14=q22 两态之和）✓。但时间轴用 build_date（建单日）——meta 无「报文日期」成员，文件指定的报文日期轴在 Cube 面不存在，build_date/enter_date/reconcile_date 是仅有的缴库日期族。

---

### q05　全库累计清分了多少、清分率是多少？

- **判定**：ask→追问后 answer（sessionId `nlq1021-q05`，首答 27.9s，预聚合 —）
- **基准**：160.16 亿 / 0.8737

**反问**：“清分了多少”可查：全库累计分入金额 16,016,079,467.68 元、划拨金额 72,507.62 元、共 728 笔（fiscal_allocation_view，无时间过滤，全量）。但“清分率”在 meta 的 ai_context 和口径词典中均无定义，也没有现成的比率型成员，需要您拍板口径后才能计算——不同口径结果差异巨大（如分入金额/划拨金额≈220,000倍 vs 清分笔数/缴款笔数）

**选项**：
1. 分入金额 ÷ 缴款总额（fiscal_collection_view 口径，跨视图）
2. 分入金额 ÷ 划拨金额（同视图两度量相除）
3. 清分笔数 ÷ 缴款笔数
4. 按其他定义，请补充说明

**追问**（同会话续问，耗时 22.6s）：就按第一个选项的口径来（分入金额 ÷ 缴款总额（fiscal_collection_view 口径，跨视图）），直接出答案。

**表1：口径A：全库累计清分 vs 缴款总额（清分率）**（1 行）

| fiscal_allocation_view.im_amt | fiscal_allocation_view.trans_amt | fiscal_allocation_view.count | fiscal_collection_view.amt | 清分率(%) |
|---|---|---|---|---|
| 16016079467.68 | 72507.62 | 728 | 18332207203.13 | 87.37 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.im_amt",
    "fiscal_allocation_view.trans_amt",
    "fiscal_allocation_view.count"
  ],
  "dimensions": [],
  "filters": [],
  "timeDimensions": [],
  "order": {
    "fiscal_allocation_view.im_amt": "desc"
  },
  "limit": 1
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
```

</details>

**歧义拍板**：清分率口径拍板为「分入金额 ÷ 缴款总额（fiscal_collection_view 缴款明细口径 amt）」；分母未用票面金额 total_amt（fan trap 禁 sum）

**答案文本**：口径声明：清分率按您拍板的口径 = 分入金额（fiscal_allocation_view.im_amt）÷ 缴款总额（fiscal_collection_view.amt，缴款明细口径，非票面金额 total_amt——该成员禁 sum）。两视图均全库无时间过滤，各自单行全量聚合（跨视图不可同查，分别查询后答案层相除）。数据范围：全库累计清分（分入）16,016,079,467.68 元、728 笔（另有划拨金额 72,507.62 元）；缴款总额 18,332,207,203.13 元；清分率 = 16,016,079,467.68 ÷ 18,332,207,203.13 ≈ 87.37%。该口径已回写 /agent/dictionary 词典「清分率」词条。

**计划**：[["全库累计清分金额（分入口径，无时间过滤）", "fiscal_allocation_view.im_amt", "用户问「清分了多少」→ 分入金额口径（清分收入）"], ["全库缴款总额（缴款明细口径，无时间过滤）", "fiscal_collection_view.amt", "用户拍板清分率分母 = fiscal_collection_view 口径缴款总额"], ["清分率 = 分入金额 ÷ 缴款总额", "fiscal_allocation_view.im_amt / fiscal_collection_view.amt", "跨视图无固化比率成员，答案层相除；口径已回写词典「清分率」"]]

> **复核**：✓ **与基准完全一致**（160.16 亿 / 0.8737）。ask 反问合规（分入 vs 划拨双口径），拍板分入口径并回写词典；分子分母跨视图分查后答案层相除，占比走答案层符合契约。

---

## 二、单位维度

### q06　2022 年缴款金额排名前 10 的执收单位

- **判定**：answer（可答）（sessionId `nlq1021-q06`，首答 25.0s，预聚合 —）
- **基准**：—

**表1：2022年缴款金额Top执收单位（口径：缴款明细金额 amt，时间轴 pay_date）**（9 行）

| fiscal_collection_view.chg_agency_code | fiscal_collection_view.chg_agency_name | fiscal_collection_view.amt | fiscal_collection_view.paybook_count |
|---|---|---|---|
| 124045 | 001 / 测试云南测试环境 / 测试云南测试环境(试用版) / 测试云南测试环境(试用版)(试用版) | 18208882274.85 | 253 |
| 425002 | 云南测试单位1209 | 24034.92 | 4 |
| 124100 | 测试1125 | 11763.68 | 18 |
| 125019 | 云南医疗单位0729 / 测试云南医疗单位0729 | 6864.26 | 19 |
| 001 | 测试分成测试 | 5184 | 9 |
| 124576 | 测试云南通用测试单位0720 | 2057.68 | 13 |
| 125020 | 测试云南医疗单位0805 | 1915.12 | 9 |
| 124577 | 测试测试单位0722 | 1377.76 | 7 |
| 124579 | 测试云南通用Oracle0728 | 1100 | 2 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.paybook_count"
  ],
  "dimensions": [
    "fiscal_collection_view.chg_agency_code",
    "fiscal_collection_view.chg_agency_name"
  ],
  "filters": [],
  "timeDimensions": [
    {
      "dimension": "fiscal_collection_view.pay_date",
      "dateRange": [
        "2022-01-01",
        "2022-12-31"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 10
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_collection`.`fchgagencode` `fiscal_collection_view__chg_agency_code`, `fiscal_collection`.chg_agency_name_canon `fiscal_collection_view__chg_agency_name`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count` 
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
GROUP BY 1, 2
ORDER BY  3  DESC
LIMIT 102022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z
```

</details>

**歧义拍板**：无歧义：金额取缴款明细口径 amt（非到账金额 entered_amt），时间按缴款日期 pay_date；无同名口径词典约定。

**答案文本**：口径：fiscal_collection_view 缴款明细金额 amt（famt 合计），时间轴 pay_date 限定 2022-01-01~2022-12-31，按执收单位编码 chg_agency_code 分组降序取前10。单位名称列为一码多名字典序拼接，仅跟随展示不作准。查询实际返回 9 个单位（2022 年内有缴款数据的执收单位不足 10 个，不存在第 10 名），未截断。

**计划**：[["按缴款日期限定 2022 年，按执收单位分组求缴款金额并降序取前10", "fiscal_collection_view.amt", "ai_context：金额用 amt（famt 合计），时间过滤用 pay_date；分组必须用 chg_agency_code"]]

> **复核**：2022 年仅 9 个执收单位有缴款，如实报 9 组并说明无第 10 名 ✓；名称列一码多名拼接不作准（已知特征）。

---

### q07　主管单位测试云南省教育厅1的下级单位合计缴款多少？

- **判定**：nomatch（答不了）（sessionId `nlq1021-q07`，首答 52.4s，预聚合 —）
- **基准**：教育厅系实测 160.47 亿（parent_agen 树自联结）

**缺口**：["模型中不存在单位层级关系成员：fiscal_collection_view / fiscal_allocation_view 均无『主管单位→下级单位』父子维度（allocation 的 ai_context 明示『上/下级分入待层级 ETL』，层级关系未建模），无法按主管单位圈定其下级单位集合", "可用的单位维度仅 chg_agency_code（执收单位）、rec_agency_code（收入单位）、acc_agen_code（代理单位）等平级维度，且收入单位只有编码无名称列，无法用『云南省教育厅1』名称直接过滤或判定层级归属", "fiscal_collection 未做未建模盘点（GET /agent/unmodel/fiscal_collection 返回『未盘点』），无法确认层级字段是否存在于源表待补建；补层级 ETL（约轻扩展量）或拍板改用其他圈定口径（如按执收单位名称模糊匹配）后可重查"]

**nomatch 原文**：主管单位云南省教育厅1的下级单位合计缴款多少？

> **复核**：**与文件能力声明直接相悖**：文件称可答（parent_agen 树自联结，实测 160.47 亿），Cube 部署面无任何单位层级成员（单位仅平级编码/名称维度），nomatch 判定合规且缺口精确。能力盘点系 Datus 侧 fne_fund_main.yml 口径，Cube 面需补层级建模或修正清单。

---

### q08　各执收预算单位（主管预算单位）的清分金额对比

- **判定**：answer（可答）（sessionId `nlq1021-q08`，首答 29.3s，预聚合 —）
- **基准**：—

**表1：口径：划出方执收单位 × 清分金额（划拨金额 trans_amt 降序，附分入金额 im_amt 与记录数）**（25 行）

| fiscal_allocation_view.chg_agency_code | fiscal_allocation_view.trans_amt | fiscal_allocation_view.im_amt | fiscal_allocation_view.count |
|---|---|---|---|
| 124045 | 63371 | 15986585353.85 | 291 |
| 001 | 5082 | 2541 | 16 |
| 124994 | 2966 | 28941171.61 | 141 |
| 125026 | 664.62 | 13384.84 | 36 |
| 124992 | 324 | 287174 | 8 |
| 124993 | 100 | 100 | 1 |
| 125020 | None | 1915.12 | 9 |
| 001001 | None | 0 | 2 |
| 124576 | None | 2057.68 | 13 |
| 425104 | None | 1601.32 | 6 |
| 125019 | None | 6864.26 | 19 |
| 124100 | None | 11663.68 | 19 |
| 124002 | None | 4964 | 17 |
| 125032 | None | 5500.66 | 22 |
| 125029 | None | 30 | 2 |
| 425002 | None | 24034.92 | 4 |
| 105015 | None | 0 | 2 |
| 427008 | None | 2158 | 2 |
| 127208 | None | 12448.24 | 22 |
| 124577 | None | 1377.76 | 7 |
| 425103 | None | 165008.58 | 43 |
| 124579 | None | 1100 | 2 |
| 125022 | None | 3803.64 | 20 |
| 998017 | None | 805.28 | 3 |
| 998015 | None | 4409.24 | 21 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.trans_amt",
    "fiscal_allocation_view.im_amt",
    "fiscal_allocation_view.count"
  ],
  "dimensions": [
    "fiscal_allocation_view.chg_agency_code"
  ],
  "order": {
    "fiscal_allocation_view.trans_amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_allocation`.`fchgagencode` `fiscal_allocation_view__chg_agency_code`, sum(`fiscal_allocation`.`ftransamt`) `fiscal_allocation_view__trans_amt`, sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation_view__im_amt`, count(*) `fiscal_allocation_view__count` 
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
GROUP BY 1
ORDER BY  2  DESC
LIMIT 100
```

</details>

**歧义拍板**：「清分金额」未指明口径，按 ai_context 两个既有金额成员并列输出：主口径 trans_amt（划拨金额，排序依据），附 im_amt（分入金额）；「执收预算单位/主管预算单位」映射为划出方单位编码 chg_agency_code，未静默替换为划入方或预算归类（rec_bgt_agen_code）口径。

**答案文本**：口径声明：执收预算单位按清分记录的划出方单位（chg_agency_code）分组——清分是资金从执收单位划出的流向事实，划出方即执收方；清分金额同时给出口径一「划拨金额 trans_amt」（划拨口径，作主排序）与口径二「分入金额 im_amt」（清分收入口径），未做单一拍板，两口径并列对比。数据范围：全量清分事实（fiscal_allocation_view，时间未过滤），共 25 个执收单位、totalRows=25 未截断。划出方单位名称在 fdt 无数据列，仅出编码（ai_context 明示）。划分拨口径看，单位 124045 以 63,371 元居首（其分入口径达约 159.87 亿元），其后为 001（5,082 元）、124994（2,966 元）；其余 19 个单位无划拨金额（trans_amt 为 null，即最近一轮未发生划拨或金额为空），仅存在分入金额记录。

**计划**：[["各执收预算单位的清分金额，按划出方单位编码分组，划拨金额降序对比，同时附分入金额与清分记录数两个口径", "fiscal_allocation_view.chg_agency_code + fiscal_allocation_view.trans_amt/im_amt/count", "fiscal_allocation_view ai_context：划出方看 chg_agency_code；划拨金额用 trans_amt、分入金额用 im_amt；分组必须用 *_code，*_name 仅展示不作准（划出方单位名称无数据列，只出编码）"]]

> **复核**：清分金额双口径并列对比（trans_amt/im_amt）+ 明示「未做单一拍板」——问句本身口径含糊，并列是契约允许处置。25 单位，与 q05/q21 交叉一致。

---

### q09　哪些非叶子单位自己直接收了款？

- **判定**：nomatch（答不了）（sessionId `nlq1021-q09`，首答 22.5s，预聚合 —）
- **基准**：1 级也有 23 个叶子单位可直接挂缴款

**缺口**：["模型无单位层级（上下级/父单位-子单位）维度，无法判定哪些单位是\"非叶子\"——fiscal_collection_view / fiscal_allocation_view 均只有单位编码（chg_agency_code/rec_agency_code），无层级关系成员", "口径词典无\"非叶子单位\"词条，ai_context 也未提供单位树口径", "\"自己直接收了款\"可映射为执收单位维度（chg_agency_code）+ 缴款金额（amt），但缺层级维度时该主语无法限定，fiscal_collection 主题也未做未建模盘点（unmodel 状态=未盘点），无法确认源库是否有单位层级表可补建"]

**nomatch 原文**：哪些非叶子单位自己直接收了款？

> **复核**：同 q07：无单位层级成员即无法定义「非叶子」，nomatch 合规；文件「1 级 23 叶子」声明在 Cube 面不可验证。

---

### q10　按执收单位统计未到账（欠缴）的缴款笔数

- **判定**：ask→追问后 answer（sessionId `nlq1021-q10`，首答 23.5s，预聚合 —）
- **基准**：is_received='0'，F11 催缴场景

**反问**：「未到账（欠缴）」在模型里有两种实质不同的口径，结果差别很大，请拍板：A) 欠缴口径（场景12）：缴款书状态=待缴款(state='1') 且有效期(eff_date)已过期——票还没缴款；B) 未到账口径：已缴款但资金未到账——received_date 为空（资金到账日期缺失）。两种口径都按执收单位编码(chg_agency_code)分组、笔数用 paybook_count（缴款书去重笔数）。

**选项**：
1. A：欠缴=待缴款+有效期已过期（按 eff_date 催缴口径）
2. B：未到账=已缴款但资金到账日期(received_date)为空
3. 两种口径各出一张表对比

**追问**（同会话续问，耗时 23.8s）：就按第一个选项的口径来（A：欠缴=待缴款+有效期已过期（按 eff_date 催缴口径）），直接出答案。

**表1：欠缴笔数（待缴款+有效期已过期）× 执收单位**（1 行）

| fiscal_collection_view.chg_agency_code | fiscal_collection_view.chg_agency_name | fiscal_collection_view.paybook_count | fiscal_collection_view.count |
|---|---|---|---|
| 124045 | 001 / 测试云南测试环境 / 测试云南测试环境(试用版) / 测试云南测试环境(试用版)(试用版) | 1 | 1 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.paybook_count",
    "fiscal_collection_view.count"
  ],
  "dimensions": [
    "fiscal_collection_view.chg_agency_code",
    "fiscal_collection_view.chg_agency_name"
  ],
  "filters": [
    {
      "member": "fiscal_collection_view.state",
      "operator": "equals",
      "values": [
        "1"
      ]
    },
    {
      "member": "fiscal_collection_view.eff_date",
      "operator": "beforeDate",
      "values": [
        "2026-10-21"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.paybook_count": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_collection`.`fchgagencode` `fiscal_collection_view__chg_agency_code`, `fiscal_collection`.chg_agency_name_canon `fiscal_collection_view__chg_agency_name`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count`, count(*) `fiscal_collection_view__count` 
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
WHERE (`fiscal_collection`.`fstate` = ?) AND (toDateOrNull(`fiscal_collection`.`feffdate`) < parseDateTimeBestEffort(?))
GROUP BY 1, 2
ORDER BY  3  DESC
LIMIT 10012026-10-21T00:00:00.000Z
```

</details>

**歧义拍板**：「未到账（欠缴）」按用户拍板取欠缴口径：state='1' 待缴款 + eff_date 已过期；笔数用 paybook_count（缴款书去重，非明细行数）

**答案文本**：口径：欠缴=缴款书状态为待缴款(state='1')且有效期(eff_date)已过期（早于 2026-10-21），即场景12催缴口径（用户拍板，未到账口径=received_date 为空未采用，已回写词典）。数据范围：全量缴款书数据，无时间范围限定。结果：欠缴缴款书共 1 笔，集中于执收单位 124045（缴款明细行数同为 1，即一票一行）；其余执收单位无欠缴。

**计划**：[["欠缴口径=缴款书状态待缴款(state='1')且有效期(eff_date)早于今天(2026-10-21)，按执收单位分组，笔数用缴款书去重笔数", "fiscal_collection_view.paybook_count", "ai_context 场景12 欠缴判定 + 用户 2026-10-21 拍板（欠缴催缴口径）"], ["分组用执收单位编码，名称列仅跟随展示", "fiscal_collection_view.chg_agency_code", "ai_context：分组必须用 *_code，*_name 一码多名仅展示"]]

> **复核**：文件建议 is_received='0'——Cube 面无 is_received 成员（成员面仅 state/eff_date），agent 反问后采用 state='1'+有效期过期的催缴口径（1 笔）并回写词典。口径偏离文件建议但属 Cube 面唯一可用口径。

---

## 三、科目·项目·收入分类·资金性质

### q11　各预算科目清分金额排行，政府性基金收入（103）大类下哪些叶子科目收得最多？

- **判定**：answer（可答）（sessionId `nlq1021-q11`，首答 30.2s，预聚合 —）
- **基准**：103 大类叶子科目

**表1：政府性基金收入（103）叶子科目清分金额排行（分入金额 im_amt，全量 20 科目）**（20 行）

| fiscal_allocation_view.rec_sub_code | fiscal_allocation_view.rec_sub_name | fiscal_allocation_view.im_amt | fiscal_allocation_view.count |
|---|---|---|---|
| 103010201 | 中央农网还贷资金收入 / 中央农网还贷资金收入25 / 普通话水平测试费 | 15985889302.18 | 275 |
| 1030110 | 民航发展基金收入 | 28938336.12 | 60 |
| 1030106 | 铁路建设基金收入 | 495345.65 | 44 |
| 1030115 | 港口建设费收入 | 495318.31 | 176 |
| 1030121 | 旅游发展基金收入 | 154995.46 | 49 |
| 1030129 | 国家电影事业发展专项资金收入 | 36668.96 | 16 |
| 1030146 | 国有土地收益基金收入 | 22488 | 4 |
| 103042762 | 考试考务费 | 17080 | 19 |
| 103042758 | 高等学校住宿费 | 16643 | 33 |
| 103042706 | 教师资格考试费 | 6531 | 3 |
| 103042755 | 中等职业学校学费 | 4513 | 11 |
| 103040702 | 考试考务费 | 680 | 14 |
| 103045754 | 教材费 | 580 | 9 |
| 103042707 | 普通话水平测试费 | 433 | 2 |
| 1030219 | 教育资金收入 | 260 | 7 |
| 1030801 | 国外捐赠收入 | 100 | 1 |
| 1030802 | 国内捐赠收入 | 100 | 1 |
| 1030149 | 大中型水库移民后期扶持基金收入 | 60 | 1 |
| 103014899 | 其他土地出让收入 | 33 | 1 |
| 103042751 | 预防接种劳务费 | 0 | 2 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.im_amt",
    "fiscal_allocation_view.count"
  ],
  "dimensions": [
    "fiscal_allocation_view.rec_sub_code",
    "fiscal_allocation_view.rec_sub_name"
  ],
  "filters": [
    {
      "member": "fiscal_allocation_view.rec_sub_code",
      "operator": "startsWith",
      "values": [
        "103"
      ]
    }
  ],
  "order": {
    "fiscal_allocation_view.im_amt": "desc"
  },
  "limit": 500
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_allocation`.`frecsubcode` `fiscal_allocation_view__rec_sub_code`, `fiscal_allocation`.rec_sub_name_canon `fiscal_allocation_view__rec_sub_name`, sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation_view__im_amt`, count(*) `fiscal_allocation_view__count` 
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
WHERE ((`fiscal_allocation`.`frecsubcode` ILIKE ?|| '%'))
GROUP BY 1, 2
ORDER BY  3  DESC
LIMIT 500103
```

</details>

**歧义拍板**："清分金额"按 ai_context 唯一口径取分入金额 im_amt（清分收入口径），未用划拨金额 trans_amt；"叶子科目"按返回数据集内编码无下级前缀判定（模型未提供层级维度）；时间范围未指定，取全期。

**答案文本**：口径：清分金额取 fiscal_allocation_view 分入金额 im_amt（ai_context 定义为清分收入口径），按预算科目 rec_sub_code 分组，用 startsWith '103' 限定政府性基金收入大类；时间不限（全期）。科目收得最多的是 103010201（清分金额 15,985,889,302.18 元，275 笔，占大类 99.81%），其后为 1030110 民航发展基金收入（28,938,336.12 元）、1030106 铁路建设基金收入（495,345.65 元）、1030115 港口建设费收入（495,318.31 元）。数据集内 20 个科目编码两两无前缀包含关系，均视为叶子科目，结果无截断（共 20 组）；rec_sub_name 为别名拼接仅展示（103010201 存在一码多名），以编码为准。

**计划**：[["清分金额口径取分入金额 im_amt（ai_context：清分收入口径），按预算科目 rec_sub_code 分组", "fiscal_allocation_view.im_amt / fiscal_allocation_view.rec_sub_code", "/agent/meta/fiscal_allocation_view ai_context"], ["限定政府性基金收入大类：科目编码前缀 103（startsWith 过滤）", "fiscal_allocation_view.rec_sub_code startsWith 103", "预算科目编码层级前缀"], ["叶子科目判定：返回 20 个编码两两无前缀包含关系，均为叶子，无截断（20<500）", "返回数据集内判定", "totalRows=20, truncated=false"]]

> **复核**：✓ 103010201 占大类 99.81%，与「一码两名」已知特征一致；startsWith 前缀过滤合规（filter 三元组，无 SQL 片段）。

---

### q12　民航发展基金历年缴款趋势

- **判定**：answer（可答）（sessionId `nlq1021-q12`，首答 71.5s，预聚合 未命中）
- **基准**：科目树下钻实测 3,085.08 万

**表1：民航发展基金收入（项目 1030110001）历年缴款趋势（按缴款日期 pay_date 年度，金额=amt）**（5 行）

| fiscal_collection_view.pay_date.year | fiscal_collection_view.amt | fiscal_collection_view.paybook_count |
|---|---|---|
| 2022-01-01T00:00:00.000 | 27879.00 | 3 |
| 2023-01-01T00:00:00.000 | 1403.30 | 7 |
| 2024-01-01T00:00:00.000 | 28962042.04 | 68 |
| 2025-01-01T00:00:00.000 | 1837652.80 | 37 |
| 2026-01-01T00:00:00.000 | 21801.94 | 11 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.paybook_count"
  ],
  "dimensions": [],
  "timeDimensions": [
    {
      "dimension": "fiscal_collection_view.pay_date",
      "granularity": "year"
    }
  ],
  "filters": [
    {
      "member": "fiscal_collection_view.item_code",
      "operator": "equals",
      "values": [
        "1030110001"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.pay_date": "asc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT toDateTime64(toStartOfYear(toTimeZone(toDateTime64(toDateOrNull(`fiscal_collection`.`fdate`), 0), 'UTC'), 'UTC'), 0, 'UTC') `fiscal_collection_view__pay_date_year`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count` 
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
WHERE (`fiscal_collection`.`fitemcode` = ?)
GROUP BY 1
ORDER BY  1  ASC
LIMIT 1001030110001
```

</details>

**歧义拍板**：民航发展基金→项目编码 1030110001（民航发展基金收入），item_name contains 民航 全量探测唯一命中，非歧义；「缴款」取缴款金额 amt 口径（非到账 entered_amt/缴库口径）

**答案文本**：口径声明：主题 fiscal_collection_view（缴款全景，缴款书×项目行明细粒度）；「民航发展基金」按项目编码 item_code=1030110001（民航发展基金收入）过滤，该项目在缴款数据中唯一命中；金额=amt（缴款明细口径），笔数=paybook_count（缴款书去重笔数），时间轴=pay_date（缴款日期）按年分组，未限定年份范围（数据自然覆盖 2022–2026，2026 仅为年内已发生部分）。趋势：2022–2023 金额极小（2.8万/0.14万），2024 年跃升至 2896.20 万元（68 笔）为峰值，2025 年回落至 183.77 万元，2026 年至今 2.18 万元。说明：meta 透出的同比成员（amt_yoy_diff/amt_yoy_rate）在本过滤+年度分组下返回空集，故同比列未纳入，未在答案层代算。无截断，共 5 个年度组。

**计划**：[["识别项目", "fiscal_collection_view.item_code", "目录面定位 fiscal_collection_view；item_name contains 民航 探测命中唯一项 1030110001 民航发展基金收入"], ["按年聚合缴款金额与笔数", "fiscal_collection_view.amt", "ai_context：金额用 amt，缴款书笔数用 paybook_count，时间过滤用 pay_date"], ["按缴款日期年度分组", "fiscal_collection_view.pay_date", "趋势轴用 timeDimensions granularity=year，未限定年份范围"]]

> **复核**：✓ 历年合计 3,085.09 万 ≈ 基准 3,085.08 万（分项口径一致）。同比列在 item 过滤+年分组下空集→未纳入且未代算（28 号方案机判合规）。71.5s 全场最长（树下钻试探成本）。

---

### q13　按收入分类统计：政府性基金收入、专项收入、行政事业性收费、罚没各占多少？

- **判定**：error（链路失败）（sessionId `nlq1021-q13-r2`，首答 70.9s，预聚合 —）
- **基准**：—

**error**：{"type": "error", "error": "HTTP Error 502: Bad Gateway"}

> **复核**：**链路缺陷非数据问题**：引擎 success（12 turns），最终 JSON 畸形（assumption 键值混入 plan 数组内）致服务端解析 502，重试同型失败。完整答案已从日志恢复（附录 A）：政府性基金 99.7437%/专项 0.1688%/行政事业性收费 0.0874%/罚没 306 元，分母 183.32 亿与 q05 交叉一致。输出形态兜底（FIRST_INSTRUCTION 第 4 条）未挡住嵌套错位，需加固。

---

### q14　按资金性质分组：一般公共预算、政府性基金、财政专户管理资金各收多少？

- **判定**：answer（可答）（sessionId `nlq1021-q14`，首答 26.9s，预聚合 未命中）
- **基准**：—

**表1：收入侧资金性质×缴款金额（全量，无时间过滤）**（5 行）

| fiscal_collection_view.rec_funds_nature_code | fiscal_collection_view.rec_funds_nature_name | fiscal_collection_view.amt | fiscal_collection_view.count |
|---|---|---|---|
| 12 | 政府性基金预算收入 | 16016379742.39 | 589 |
|  | （未标注资金性质） | 2314603154.582 | 544 |
| 11 | 一般公共预算收入 | 1184377.16 | 63 |
| 2 | 财政专户管理资金 | 39329 | 70 |
| 5 | 其他 | 600 | 6 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.count"
  ],
  "dimensions": [
    "fiscal_collection_view.rec_funds_nature_code",
    "fiscal_collection_view.rec_funds_nature_name"
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
```

</details>

**歧义拍板**：未指定时间范围，按全量数据统计；资金性质取收入归属口径（rec_funds_nature）而非缴款票面口径（funds_nature），如需票面口径可另查

**答案文本**：口径：按收入侧资金性质（rec_funds_nature_code，收入归属口径）分组，金额为缴款金额 amt（缴款明细口径），未加时间过滤，覆盖缴款全景事实全量数据。三项分别：政府性基金预算收入 16,016,379,742.39 元（589 行）、一般公共预算收入 1,184,377.16 元（63 行）、财政专户管理资金 39,329 元（70 行）。另有资金性质未标注（空编码）2,314,603,154.58 元（544 行）与其他 600 元（6 行），一并列出供参考。无截断，共 5 组。

**计划**：[["按收入侧资金性质分组统计缴款金额与明细行数", "fiscal_collection_view.rec_funds_nature_code", "ai_context：rec_* 前缀为收入侧口径，分组必须用 *_code 成员"], ["金额取缴款金额 amt（明细口径）", "fiscal_collection_view.amt", "ai_context：明细金额用 amt"]]

> **复核**：✓ 三类齐全 + 空编码 23.15 亿单列（与 q20 空区划组一致）。

---

### q15　缴款金额前 5 的收费项目，按直缴汇缴拆分展示

- **判定**：answer（可答）（sessionId `nlq1021-q15`，首答 26.1s，预聚合 未命中）
- **基准**：—

**表1：口径A：前5收费项目按业务类型（直缴/汇缴）拆分**（10 行）

| fiscal_collection_view.item_code | fiscal_collection_view.item_name | fiscal_collection_view.bus_type | fiscal_collection_view.amt |
|---|---|---|---|
| 103010201001 | 农网还贷资金收入 | 1 | 15985880682.69 |
| 103010201002 | 国有重点煤炭企业生产用电、核工业铀扩散厂和堆化工厂生产用电农网还贷资金 | 2 | 2238005215.90 |
| 1030110001 | 民航发展基金收入 | 1 | 30758057.70 |
| 103010201001 | 农网还贷资金收入 | 2 | 30297369.11 |
| 1030102010011 | 农网还贷资金收入a | 1 | 28580429.00 |
| 103042758 | 高等学校住宿费 | 2 | 14821899.00 |
| 103010201002 | 国有重点煤炭企业生产用电、核工业铀扩散厂和堆化工厂生产用电农网还贷资金 | 1 | 159670.01 |
| 1030110001 | 民航发展基金收入 | 2 | 92721.38 |
| 1030102010011 | 农网还贷资金收入a | 2 | 71066.69 |
| 103042758 | 高等学校住宿费 | 1 | 19271.00 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt"
  ],
  "dimensions": [
    "fiscal_collection_view.item_code",
    "fiscal_collection_view.item_name",
    "fiscal_collection_view.bus_type"
  ],
  "filters": [
    {
      "member": "fiscal_collection_view.item_code",
      "operator": "equals",
      "values": [
        "103010201001",
        "103010201002",
        "1030110001",
        "1030102010011",
        "103042758"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_collection`.`fitemcode` `fiscal_collection_view__item_code`, `fiscal_collection`.item_name_canon `fiscal_collection_view__item_name`, `fiscal_collection`.`fbustype` `fiscal_collection_view__bus_type`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt` 
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
WHERE (`fiscal_collection`.`fitemcode` IN (?, ?, ?, ?, ?))
GROUP BY 1, 2, 3
ORDER BY  4  DESC
LIMIT 10010301020100110301020100210301100011030102010011103042758
```

</details>

**歧义拍板**：时间范围未指明→取全量；直缴/汇缴按 bus_type 编码 1/2 拆分，编码映射未在 meta 透出，原样展示

**答案文本**：口径：fiscal_collection_view，缴款金额=amt（缴款明细口径），全量历史数据（未加时间过滤）。前5项目按 amt 降序：农网还贷资金收入(103010201001)、国有重点煤炭企业生产用电…农网还贷资金(103010201002)、民航发展基金收入(1030110001)、农网还贷资金收入a(1030102010011)、高等学校住宿费(103042758)。拆分维度 bus_type（fbustype：直缴/汇缴），返回值为编码 1/2，meta 未透出 1/2 与直缴/汇缴的映射字典，编码原样展示——如需确定哪个是直缴请拍板。另注意 103010201001 与 1030102010011 疑似同项目不同编码（'农网还贷资金收入'/'农网还贷资金收入a'），ai_context 载明一码多名/脏数据仅跟随展示不作准，故按编码分列。

**计划**：[["缴款金额前5的收费项目", "fiscal_collection_view.item_code", "ai_context：明细金额用 amt，分组用 item_code"], ["按业务类型（直缴/汇缴）拆分", "fiscal_collection_view.bus_type", "bus_type=fbustype（直缴/汇缴）"]]

> **复核**：bus_type 编码 1/2 的直缴/汇缴映射 meta 未透出，agent 拒绝臆测、编码原样展示——**合规**；但 q25/q29 会话内自行给出映射（说明映射散落未固化），建议写进 ai_context 或词典。

---

## 四、区划与银行

### q16　按归属区划统计清分金额

- **判定**：answer（可答）（sessionId `nlq1021-q16`，首答 31.5s，预聚合 —）
- **基准**：州市/区县内联维度

**表1：清分金额（分入金额 im_amt）×收入归属区划**（5 行）

| fiscal_allocation_view.rec_rgn_code | fiscal_allocation_view.im_amt | fiscal_allocation_view.count |
|---|---|---|
| 530000 | 16016072677.53 | 686 |
| 000000 | 4516.12 | 31 |
| 530100 | 1778.7 | 8 |
| 530102 | 495.33 | 1 |
| 532929 | 0 | 2 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.im_amt",
    "fiscal_allocation_view.count"
  ],
  "dimensions": [
    "fiscal_allocation_view.rec_rgn_code"
  ],
  "order": {
    "fiscal_allocation_view.im_amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_allocation`.`frecrgncode` `fiscal_allocation_view__rec_rgn_code`, sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation_view__im_amt`, count(*) `fiscal_allocation_view__count` 
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
GROUP BY 1
ORDER BY  2  DESC
LIMIT 100
```

</details>

**歧义拍板**：「清分金额」拍板为分入金额 im_amt（清分收入口径，词典无词条、ai_context 唯一指向）；「归属区划」拍板为划入方收入归属区划 rec_rgn_code（ai_context：收入归属区划，分组必须用 *_code）。未做时间范围过滤，按全量统计。

**答案文本**：口径声明：清分金额取 fiscal_allocation_view.im_amt（分入金额，ai_context 指明的清分收入口径；非划拨金额 trans_amt）；归属区划取 rec_rgn_code（划入方/收入归属区划，仅编码，名称列不作准）。无时间过滤，覆盖全量 728 笔清分记录；各组合计 16,016,079,467.68 元，与不带分组的全量合计查询一致。5 个区划组，未截断。划出方区划、清分金额其他口径如需可另行指定。

**计划**：[["按收入归属区划分组统计清分金额", "fiscal_allocation_view.im_amt / fiscal_allocation_view.rec_rgn_code", "ai_context：金额清分收入口径用 im_amt；归属区划用 rec_rgn_code（划入方）"], ["全量合计校验", "fiscal_allocation_view.im_amt", "不带 dimensions 的独立全量查询"]]

> **复核**：✓ 16,016,079,467.68 与 q05 分入合计完全一致。

---

### q17　按执收区划名称统计缴款金额

- **判定**：answer（可答）（sessionId `nlq1021-q17`，首答 39.0s，预聚合 未命中）
- **基准**：fchgrgnname，5 区划全分布

**表1：缴款金额按执收区划（rec_rgn_code+名称展示，全期）**（6 行）

| fiscal_collection_view.rec_rgn_code | fiscal_collection_view.rec_rgn_name | fiscal_collection_view.amt | fiscal_collection_view.count |
|---|---|---|---|
| 530000 | 云南省本级 | 16016434579.21 | 686 |
|  | None | 2314603154.58 | 544 |
| 532929 | 云龙县 | 1156320 | 2 |
| 000000 | 中央 | 9617.68 | 31 |
| 530100 | 昆明市本级 | 2541 | 8 |
| 530102 | 五华区 | 990.66 | 1 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.count"
  ],
  "dimensions": [
    "fiscal_collection_view.rec_rgn_code",
    "fiscal_collection_view.rec_rgn_name"
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_collection`.`frecrgncode` `fiscal_collection_view__rec_rgn_code`, `fiscal_collection`.rec_rgn_name_canon `fiscal_collection_view__rec_rgn_name`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt`, count(*) `fiscal_collection_view__count` 
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
```

</details>

**歧义拍板**：问句"按执收区划名称"与 ai_context 单一口径（编码分组、名称仅展示）一致，直接采用 rec_rgn_code 分组并附 rec_rgn_name 列，未另开口径分支。

**答案文本**：口径声明：缴款金额取 fiscal_collection_view 明细金额 amt；分组按 ai_context 规定使用收入归属区划编码 rec_rgn_code（区划名称 rec_rgn_name 为该编码别名拼接、不作准，仅跟随展示）。数据范围：未加时间过滤，覆盖视图全量缴款数据，共 6 组、未截断。数据说明：有 544 条明细（约 23.15 亿）区划编码为空、名称为 null，作为单独一组列示；合计 183.3 亿，云南省本级占 160.16 亿为最大区划。

**计划**：[["缴款金额按收入归属区划分组，金额用明细金额 amt，附带明细行数 count", "fiscal_collection_view.amt", "ai_context：明细金额用 amt；分组用 *_code 成员，*_name 仅跟随展示"], ["按收入归属区划编码 rec_rgn_code 分组、区划名称 rec_rgn_name 展示", "fiscal_collection_view.rec_rgn_code", "ai_context：分组必须用 *_code，*_name 是别名拼接不作准，不用于分组"]]

> **复核**：**选错维度（全场最重）**：问「执收区划」，分组用了 rec_rgn_code（收入区划；ai_context 明确 rec_* 前缀=收入侧），而 meta 明确存在 chg_rgn_code（执收区划编码）。agent 引用 ai_context 辩称「规定使用 rec_rgn_code」——ai_context 只列举分组用 code 的例子，无执收区划→rec_rgn 映射，属错误辩护。数字内部自洽但维度错误，正确口径应按 chg_rgn_code 重查。

---

### q18　五华区的执收单位有哪些、各收了多少钱？

- **判定**：answer（可答）（sessionId `nlq1021-q18`，首答 34.4s，预聚合 未命中）
- **基准**：—

**表1：五华区（530102）执收单位×缴款金额（缴款侧 amt）**（3 行）

| fiscal_collection_view.chg_agency_code | fiscal_collection_view.chg_agency_name | fiscal_collection_view.amt | fiscal_collection_view.paybook_count |
|---|---|---|---|
| 777001 | 智能核销五华区测试单位开票点 | 77324.80 | 2 |
| 125026 | 云南医保测试单位改名 / 开票点一 / 李思维 | 1981.32 | 1 |
| 124994 | 云南发展改革委员会 / 开票点001 / 开票点002 | 100.00 | 1 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.paybook_count"
  ],
  "dimensions": [
    "fiscal_collection_view.chg_agency_code",
    "fiscal_collection_view.chg_agency_name"
  ],
  "filters": [
    {
      "member": "fiscal_collection_view.chg_rgn_code",
      "operator": "equals",
      "values": [
        "530102"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_collection`.`fchgagencode` `fiscal_collection_view__chg_agency_code`, `fiscal_collection`.chg_agency_name_canon `fiscal_collection_view__chg_agency_name`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count` 
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
WHERE (`fiscal_collection`.`fchgrgncode` = ?)
GROUP BY 1, 2
ORDER BY  3  DESC
LIMIT 100530102
```

</details>

**歧义拍板**：「执收单位」= 缴款书执收方 chg_agency（非收入侧 rec_agency，其无名称列）；「收了多少钱」= 缴款金额 amt 合计；时间范围不限

**答案文本**：口径声明：主题 fiscal_collection_view（缴款全景）；「执收单位」按缴款书执收方 chg_agency_code 分组（词典无词条，按 ai_context 默认口径），五华区经区划分组实测对应编码 530102；金额为缴款金额 amt（缴款明细口径），全部时间范围未加限定。数据范围：五华区共 3 个执收单位、4 笔缴款书，合计 79406.12 元，最大为「智能核销五华区测试单位开票点」77324.80 元（占比 97.3%，按返回行计算）。未截断（totalRows=3）。附带说明：未指明时未改用到账金额 entered_amt，如需到账/入库口径可另查。

**计划**：[["执收单位按缴款书执收方（chg_agency）分组", "fiscal_collection_view.chg_agency_code", "ai_context：分组必须用 *_code 成员"], ["五华区定位为区划编码 530102", "fiscal_collection_view.chg_rgn_code", "实测 chg_rgn_code 分组结果中 chg_rgn_name='五华区' ↔ 530102"], ["金额用缴款金额 amt", "fiscal_collection_view.amt", "ai_context：明细金额用 amt；金额未指明到账/入库，取缴款侧 amt，附缴款书笔数 paybook_count"], ["词典无「执收单位」「五华区」词条，按 ai_context 默认口径执行", "fiscal_collection_view.amt", "GET /agent/dictionary 两词均无 entries；执收单位取缴款书执收方 chg_agency，未取收入侧 rec_agency（无名称列）"]]

> **复核**：3 单位 4 笔 79,406.12 元；五华区=530102 系 agent 区划分组实测对应（无名称→编码字典），合理。注意其区划过滤维度未明示（chg_rgn/rec_rgn 之辨同 q17）。

---

### q19　各收款银行（代理银行）2022 年各收了多少笔、多少钱？

- **判定**：answer（可答）（sessionId `nlq1021-q19`，首答 22.4s，预聚合 未命中）
- **基准**：frecbankname，9 家银行 100% 非空

**表1：2022 年各收款银行：缴款笔数与金额（缴款日期口径）**（6 行）

| fiscal_collection_view.rec_bank_code | fiscal_collection_view.rec_bank_name | fiscal_collection_view.paybook_count | fiscal_collection_view.amt |
|---|---|---|---|
| 0105 | 中国建设银行 | 211 | 18208121939.04 |
| 0104 | 中国银行 | 103 | 800419.02 |
| 0100 | 中国邮政储蓄银行 | 7 | 7778 |
| 0102 | 中国工商银行 | 9 | 5426.21 |
| 0103 | 中国农业银行 | 3 | 510 |
| 0303 | 中国光大银行 | 1 | 500 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.paybook_count",
    "fiscal_collection_view.amt"
  ],
  "dimensions": [
    "fiscal_collection_view.rec_bank_code",
    "fiscal_collection_view.rec_bank_name"
  ],
  "timeDimensions": [
    {
      "dimension": "fiscal_collection_view.pay_date",
      "dateRange": [
        "2022-01-01",
        "2022-12-31"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_collection`.`frecbankcode` `fiscal_collection_view__rec_bank_code`, `fiscal_collection`.`frecbankname` `fiscal_collection_view__rec_bank_name`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt` 
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
GROUP BY 1, 2
ORDER BY  4  DESC
LIMIT 1002022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z
```

</details>

**歧义拍板**：笔数取缴款书票数口径（paybook_count）而非明细行数 count；金额取缴款金额（amt）而非到账金额（entered_amt）

**答案文本**：口径：按收款银行（rec_bank_code/rec_bank_name）分组，笔数=缴款书笔数 paybook_count（票数口径，非明细行数），金额=缴款金额 amt，时间轴=缴款日期 pay_date，范围 2022-01-01 至 2022-12-31。共 6 家银行、334 笔；建行 211 笔 182.08 亿元占绝对主体。无歧义分叉，未截断（totalRows=6）。

**计划**：[["按收款银行分组，统计 2022 年缴款书笔数与缴款金额", "fiscal_collection_view.rec_bank_code / fiscal_collection_view.rec_bank_name", "view 维度成员，收款银行编码/名称"], ["笔数用缴款书笔数（票数口径，非明细行数）", "fiscal_collection_view.paybook_count", "ai_context：一票多项目行，count 是行数勿当笔数"], ["金额用缴款金额", "fiscal_collection_view.amt", "ai_context：明细金额用 amt"], ["时间范围 2022-01-01 至 2022-12-31", "fiscal_collection_view.pay_date", "ai_context：时间过滤用 pay_date（缴款日期）"]]

> **复核**：✓ 334 笔与 q01 缴款书笔数一致；2022 年 6 家银行（基准「9 家」为全量口径差异）；银行口径用 rec_bank_code（另有 rec_acct_bank 开户行名）合理。

---

### q20　归属区划在云南省本级以外的缴款有多少？

- **判定**：answer（可答）（sessionId `nlq1021-q20`，首答 31.8s，预聚合 —）
- **基准**：frecrgnname 含空串与「中央」特殊值

**表1：云南省本级以外缴款合计（rec_rgn_code≠530000）**（1 行）

| fiscal_collection_view.amt | fiscal_collection_view.paybook_count |
|---|---|
| 2315772623.922 | 504 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.paybook_count"
  ],
  "dimensions": [],
  "filters": [
    {
      "member": "fiscal_collection_view.rec_rgn_code",
      "operator": "notEquals",
      "values": [
        "530000"
      ]
    }
  ],
  "order": {},
  "limit": 10
}
```

**表2：口径参照：按收入归属区划分组（全部）**（6 行）

| fiscal_collection_view.rec_rgn_code | fiscal_collection_view.rec_rgn_name | fiscal_collection_view.amt | fiscal_collection_view.paybook_count |
|---|---|---|---|
| 530000 | 云南省本级 | 16016434579.21 | 507 |
|  | None | 2314603154.582 | 465 |
| 532929 | 云龙县 | 1156320 | 1 |
| 000000 | 中央 | 9617.68 | 29 |
| 530100 | 昆明市本级 | 2541 | 8 |
| 530102 | 五华区 | 990.66 | 1 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.paybook_count"
  ],
  "dimensions": [
    "fiscal_collection_view.rec_rgn_code",
    "fiscal_collection_view.rec_rgn_name"
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 200
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
WHERE (`fiscal_collection`.`frecrgncode` <> ? OR `fiscal_collection`.`frecrgncode` IS NULL)
LIMIT 10530000
```

</details>

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表2</summary>

```sql
SELECT `fiscal_collection`.`frecrgncode` `fiscal_collection_view__rec_rgn_code`, `fiscal_collection`.rec_rgn_name_canon `fiscal_collection_view__rec_rgn_name`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count` 
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
LIMIT 200
```

</details>

**歧义拍板**：'云南省本级'识别为 rec_rgn_code='530000'；'以外'含区划编码为空的记录（notEquals 语义），如需剔除空区划请另行拍板

**答案文本**：口径：归属区划按收入侧 rec_rgn_code（清分后收入归属区划）；缴款金额=amt，笔数=缴款书笔数 paybook_count（非明细行数）。'云南省本级'=编码530000（按全量分组实测唯一对应）。'以外'按 rec_rgn_code≠530000 计：金额 2,315,772,623.922 元、504 笔缴款书。拍板说明：区划编码为空的缴款（23.15亿元/465笔，占'以外'的 99.9%）按 notEquals 语义计入'以外'——若需剔除区划为空仅看明确市县级，'以外'金额仅 1,169,469.34 元、39 笔，可再确认口径。全部口径合计 18,332,207,203.132 元/968 笔。数据范围：缴款全景视图全量（未加时间过滤）。

**计划**：[["归属区划取收入区划编码(rec_rgn_code)，金额用缴款金额 amt，笔数用缴款书笔数 paybook_count", "fiscal_collection_view.rec_rgn_code", "ai_context：rec_* 为收入归属侧口径；金额=amt，缴款书笔数=paybook_count"], ["省级本级=编码530000(云南省本级)，以外=rec_rgn_code notEquals 530000", "fiscal_collection_view.rec_rgn_code", "按 rec_rgn_code 全量分组实测，530000 名称即'云南省本级'"], ["以外合计 2,315,772,623.922 元、504 笔", "fiscal_collection_view.amt", "notEquals 530000 不带维度全量查询返回；含区划为空的 2,314,603,154.582 元(465笔)及云龙县/中央/昆明市本级/五华区小额"]]

> **复核**：✓ 文件警示的空串/特殊值全部命中并合规处置：空编码 23.15 亿计入「以外」（占 99.9%），拍板透明且给出剔除后数字（116.95 万/39 笔）。

---

## 五、链路进度与状态

### q21　已划拨和未划拨的金额各是多少？

- **判定**：answer（可答）（sessionId `nlq1021-q21`，首答 47.8s，预聚合 未命中）
- **基准**：已划拨 24,815 / 未划拨 47,692.62

**表1：划拨口径：已划拨 vs 未划拨（清分收入总额拆分）**（1 行）

| fiscal_allocation_view.trans_amt | fiscal_allocation_view.im_amt | fiscal_allocation_view.im_amt_not_transferred | fiscal_allocation_view.trans_amt_rate |
|---|---|---|---|
| 72507.62 | 16016079467.68 | 16016006960.06 | 0.0005 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.trans_amt",
    "fiscal_allocation_view.im_amt"
  ],
  "dimensions": [],
  "filters": [],
  "timeDimensions": [],
  "order": {},
  "limit": 10
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT sum(`fiscal_allocation`.`ftransamt`) `fiscal_allocation_view__trans_amt`, sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation_view__im_amt` 
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
LIMIT 10
```

</details>

**歧义拍板**：『已划拨』取 trans_amt 合计口径；『未划拨』= im_amt 总额 − trans_amt 总额（is_transfer 标志全空不可用，改走金额差值；如需按划转状态明细口径请提供 ftransstats 期望分组）

**答案文本**：口径：基于清分流向视图 fiscal_allocation_view 全量数据（未按时间过滤）。已划拨金额 = 划拨金额 trans_amt 合计 72,507.62 元（trans_amt 仅在存在划拨记录的明细行非空，sum 自动忽略 null）；未划拨金额 = 清分分入金额 im_amt 合计 16,016,079,467.68 元减已划拨部分，得 16,016,006,960.06 元，未划拨占比约 99.95%。歧义拍板：『是否划转』标志 is_transfer 在数据中实测全为空（按 '1'/'0' 过滤均返回 0 行），无法按状态标志直接分组，故改用金额字段差值口径拆分，此拍板未经词典确认（词典无『划拨』词条）。数据范围：测试环境数据，trans_amt 仅少量明细有值，已划拨金额极小属数据现状非计算错误。

**计划**：[["已划拨金额=划拨金额合计(trans_amt，仅有划拨记录的行非空)", "fiscal_allocation_view.trans_amt", "ai_context：划拨金额用 trans_amt"], ["未划拨金额=清分总金额(im_amt)−已划拨金额，答案层差值(无固化成员)", "fiscal_allocation_view.im_amt", "ai_context：分入金额用 im_amt；差值恒走答案层"], ["是否划转标志(is_transfer)实测全为空，equals '0'/'1' 均返回0行，故按金额字段拆分而非按标志分组", "fiscal_allocation_view.is_transfer", "成员面 description：fistransfer 0否1是；查询实测空值"], ["划拨/入库到账日期用 enter_date，本答案未按时间过滤，范围为全部数据", "fiscal_allocation_view.pay_date", "ai_context：时间过滤用 pay_date，未指定期限则不限时"]]

> **复核**：与基准数字主语不同：文件基准 24,815/47,692.62（合计恰为 72,507.62）是**划拨子集内部**的状态拆分；agent 以全量清分为主语（160.16 亿 vs 7.25 万）。is_transfer 实测全空（新数据发现），金额差值口径合规。需对齐「已划拨/未划拨」的口径定义后重测。

---

### q22　缴库报文里已确认入库和待国库确认的金额各多少？

- **判定**：answer（可答）（sessionId `nlq1021-q22`，首答 23.0s，预聚合 未命中）
- **基准**：(9,1)=24 行 / (9,0) 中间态 415.5 万

**表1：缴库报文：已确认入库 vs 待国库确认（enter_status 分组，全量）**（2 行）

| enter_status | amt | count | bill_count |
|---|---|---|---|
| 0（待国库确认/未入库） | 29409625.05 | 50 | 44 |
| 1（已确认入库/已入国库） | 46304.09 | 26 | 26 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_treasury_view.amt",
    "fiscal_treasury_view.count",
    "fiscal_treasury_view.bill_count"
  ],
  "dimensions": [
    "fiscal_treasury_view.enter_status"
  ],
  "filters": [],
  "timeDimensions": [],
  "order": {
    "fiscal_treasury_view.amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
```

</details>

**歧义拍板**："已确认入库"映射 enter_status='1'（已入国库）；"待国库确认"映射 enter_status='0'（模型口径原文为"未入库"），未指定时间范围故查全量

**答案文本**：口径声明：缴库入库视图（fiscal_treasury_view，缴库单×科目去重明细），入库状态用 enter_status——'1'已入国库（已确认入库）、'0'未入库（对应问句中的"待国库确认"，模型内该状态原文为"未入库"，如有出入请指正）；金额用 amt（明细口径，去重后 sum 正确），未限定时间范围，为全量数据。结果：待国库确认 29,409,625.05 元（50 行明细/44 张缴库单），已确认入库 46,304.09 元（26 行明细/26 张缴库单）。合计由本结果两行直接可加（2 组全量、无截断）。

**计划**：[["按入库状态分组汇总缴库金额与笔数", "fiscal_treasury_view.amt", "ai_context：入库状态 enter_status='1'已入国库 / '0'未入库，明细金额用 amt"]]

> **复核**：income_status 成员在 Cube 面不存在（meta 实证，仅 status/enter_status/reconcile_status），enter_status 是唯一入库状态成员——agent 选择正确。基准 (9,1)=24 行/415.5 万与 agent 26 行/2,940.96 万不可直接比（不同字段+不同表范围）。

---

### q23　汇总批次一共多少个？

- **判定**：ask→追问后 answer（sessionId `nlq1021-q23`，首答 30.0s，预聚合 —）
- **基准**：正确口径 428（expression 含空串假批次缺陷）

**反问**：「汇总批次一共多少个」有两种口径分叉，实质改变结果，需要拍板：A. 划转视图 fiscal_allocation_view 里「是否汇总 collect_flag=是」的清分记录数（模型直接支持，一条 count 即可）；B. 去重的汇总单据批次数（按 fcollectid 去重计数）——成员面没有 fcollectid 维度，也没有对应去重计数度量，该口径当前查不了（只能转建模补成员）。选 A 还是 B？

**选项**：
1. A：查 collect_flag=是 的汇总清分记录数（立即可查）
2. B：按汇总单据 fcollectid 去重的批次数（需建模补成员后才能查）

**追问**（同会话续问，耗时 21.5s）：就按第一个选项的口径来（A：查 collect_flag=是 的汇总清分记录数（立即可查）），直接出答案。

**表1：口径A：汇总批次（collect_flag=1）清分记录数**（1 行）

| fiscal_allocation_view.count |
|---|
| 550 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.count"
  ],
  "filters": [
    {
      "member": "fiscal_allocation_view.collect_flag",
      "operator": "equals",
      "values": [
        "1"
      ]
    }
  ],
  "order": {
    "fiscal_allocation_view.count": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT count(*) `fiscal_allocation_view__count` 
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
WHERE (if(empty(`fiscal_allocation`.`fcollectid`), '0', '1') = ?)
ORDER BY  1  DESC
LIMIT 1001
```

</details>

**歧义拍板**：用户拍板口径A：汇总清分记录数（collect_flag=1），非 fcollectid 去重批次数

**答案文本**：口径声明：按用户拍板的口径A，「汇总批次」= 划转视图（fiscal_allocation_view）中是否汇总 collect_flag=1 的清分记录数，全时间范围、无其他过滤。歧义拍板：collect_flag 实际取值为 1/0（字面「是」无命中），已按 1 过滤；「按 fcollectid 去重的批次数」口径模型无成员、当前查不了（已写入口径词典备查）。数据范围：550 条，非截断（totalRows=1，单行聚合）。

**计划**：[["口径A：按 collect_flag=1（是否汇总）过滤的清分记录数", "fiscal_allocation_view.count", "成员面 ai_context：collect_flag 由 fcollectid 非空衍生，取值 1/0；用户拍板口径A"], ["全表清分记录（参考分母，非本次口径）", "fiscal_allocation_view.count", "主度量附列，用于数据范围核对"]]

> **复核**：**已知缺陷复现**：fcollectid 去重口径模型无成员；agent 反问后按 collect_flag=1 得 550 条记录，文件基准 428 为 fcollectid 去重真实批次数（expression 含空串假批次缺陷仍在）。550≠428 系记录数 vs 去重口径+假批次。词典已回写。

---

### q24　未清分的缴款笔数和金额是多少？

- **判定**：answer（可答）（sessionId `nlq1021-q24`，首答 30.8s，预聚合 未命中）
- **基准**：is_cleared='0'，515 行

**表1：未清分缴款（clear_date 为空）笔数与金额**（1 行）

| paybook_count | amt |
|---|---|
| 439 | 2314587534.582 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.paybook_count",
    "fiscal_collection_view.amt"
  ],
  "filters": [
    {
      "member": "fiscal_collection_view.clear_date",
      "operator": "notSet",
      "values": []
    }
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt` 
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
WHERE (toDateOrNull(`fiscal_collection`.`fcleardate`) IS NULL)
ORDER BY  2  DESC
LIMIT 100
```

</details>

**歧义拍板**：「未清分」拍板为 clear_date 为空（notSet）；词典无该词约定，如需改为按缴款书状态等其他口径请告知后回写词典

**答案文本**：口径：未清分按「清分日期 clear_date（fcleardate）为空」过滤（词典无「未清分」词条，此为模型内唯一清分标记，直接采用并声明）。笔数用缴款书笔数 paybook_count（去重票数，非明细行数），金额用缴款金额 amt 合计。数据范围：缴款全景事实 fne_paybook_full_high 全期，不限时间。结果：未清分缴款书 439 笔，金额合计 2,314,587,534.58 元。

**计划**：[["未清分（清分日期为空）的缴款书笔数", "fiscal_collection_view.paybook_count", "meta ai_context：缴款书笔数用 paybook_count，count 是明细行数勿当笔数"], ["未清分（清分日期为空）的缴款金额合计", "fiscal_collection_view.amt", "meta ai_context：明细金额用 amt"], ["未清分过滤条件", "fiscal_collection_view.clear_date", "清分日期 fcleardate 为 notSet = 未清分"]]

> **复核**：is_cleared 成员在 Cube 面不存在（meta 实证，仅 clear_date），「clear_date 为空」是唯一可用口径——439 缴款书/23.15 亿。与基准 515 行（is_cleared='0'）不可直接比（成员缺失+缴款书 vs 行数口径）。

---

### q25　清分率按业务类型分组对比：直缴和汇缴各是多少？

- **判定**：ask→追问后 answer（sessionId `nlq1021-q25`，首答 37.6s，预聚合 —）
- **基准**：instructions 已写明逐组成立

**反问**：「清分率」在模型 meta（fiscal_collection_view / fiscal_allocation_view 的 ai_context 与成员面）中没有任何定义，口径词典也无该词条；而「直缴/汇缴」分组维度已确认存在（fiscal_collection_view.bus_type，fbustype：直缴/汇缴）。清分率的分子/分母不明确，不同取法结果实质不同，需拍板后再查。

**选项**：
1. 划转成功笔数 ÷ 清分记录数（fiscal_allocation_view：trans_stats=9 的 count ÷ 总 count，按划出/划入区划关联 bus_type 需联查）
2. 划拨金额 ÷ 分入金额（fiscal_allocation_view.trans_amt ÷ im_amt）
3. 已划转到账金额 ÷ 缴款金额（跨 fiscal_treasury_view/fiscal_collection_view，需联查，跨视图不可同查只能分别取数后答案层相除）
4. 其他（请说明分子/分母口径）

**追问**（同会话续问，耗时 33.6s）：就按第一个选项的口径来（划转成功笔数 ÷ 清分记录数（fiscal_allocation_view：trans_stats=9 的 count ÷ 总 count，按划出/划入区划关联 bus_type 需联查）），直接出答案。

**表1：清分率（口径：划转成功笔数÷清分记录数，fiscal_allocation_view）**（2 行）

| fiscal_allocation_view.count | fiscal_allocation_view.trans_stats | fiscal_allocation_view.clear_rate_num | fiscal_allocation_view.clear_rate_pct |
|---|---|---|---|
| 728 | 全部 | 0 | 0.00 |
| 0 | 9 | 0 | 0.00 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.count"
  ],
  "dimensions": [],
  "filters": [],
  "timeDimensions": [],
  "order": {
    "fiscal_allocation_view.count": "desc"
  },
  "limit": 100
}
```

**表2：业务类型分布（缴款全景，bus_type：1=直缴 2=汇缴，参考背景）**（2 行）

| fiscal_collection_view.bus_type | fiscal_collection_view.paybook_count | fiscal_collection_view.count |
|---|---|---|
| 1 | 848 | 1063 |
| 2 | 120 | 209 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.paybook_count",
    "fiscal_collection_view.count"
  ],
  "dimensions": [
    "fiscal_collection_view.bus_type"
  ],
  "filters": [],
  "timeDimensions": [],
  "order": {
    "fiscal_collection_view.paybook_count": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT count(*) `fiscal_allocation_view__count` 
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
LIMIT 100
```

</details>

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表2</summary>

```sql
SELECT `fiscal_collection`.`fbustype` `fiscal_collection_view__bus_type`, COUNT(DISTINCT `fiscal_collection`.`fpaycode`) `fiscal_collection_view__paybook_count`, count(*) `fiscal_collection_view__count` 
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
GROUP BY 1
ORDER BY  2  DESC
LIMIT 100
```

</details>

**歧义拍板**：清分率口径由用户拍板：划转成功笔数（trans_stats=9）÷ 清分记录数；分子分母同取 fiscal_allocation_view 全量（无时间范围限制）

**答案文本**：口径声明：清分率按拍板口径＝划转成功笔数÷清分记录数（fiscal_allocation_view.count filter trans_stats=9 ÷ count），已回写口径词典。查询结果：清分记录数共 728 条，其中划转状态=9（成功）0 条，清分率＝0÷728＝0.00%（数据范围：fiscal_allocation_view 全量，未加时间过滤）。直缴/汇缴分组说明：bus_type（1=直缴，2=汇缴）位于 fiscal_collection_view，与 fiscal_allocation_view 之间引擎无 join path、也无联查 view，实测报错 "Can't find join path to join 'fiscal_collection', 'fiscal_allocation'"，故按业务类型拆分的清分率当前查不了；作为参考给出缴款侧业务类型分布（直缴 848 票/1063 行，汇缴 120 票/209 行）。若需按直缴/汇缴拆分清分率，需补建跨视图联查（轻扩展，拍板后另办）。

**计划**：[["清分记录数（分母，全量）", "fiscal_allocation_view.count", "meta 成员面 measures"], ["划转成功记录数（分子，trans_stats=9）", "fiscal_allocation_view.count + filter trans_stats=9", "成员 description：9成功"], ["业务类型分组（直缴/汇缴）", "fiscal_collection_view.bus_type", "成员 description：fbustype（直缴/汇缴）"]]

> **复核**：**真实建模缺口**：跨 view 无 join path 实证报错（"Can't find join path to join 'fiscal_collection', 'fiscal_allocation'"）——文件「逐组成立」的直缴/汇缴清分率拆分在 Cube 面查不了，需联查 view。主口径划转成功 0/728=0.00%（trans_stats=9 全库 0 条，与 q21 is_transfer 全空互证：划拨环节基本未发生）。参考表给出缴款侧直缴/汇缴分布（120 票/209 行与 q29 一致）。

---

## 六、还答不了的（nomatch 验证）

### q26　划拨金额按划入的下级区划和划入单位拆分统计

- **判定**：answer（可答）（sessionId `nlq1021-q26`，首答 30.3s，预聚合 —）
- **基准**：期望 nomatch：无区划层级 dim、fsharerate 缓建、划入单位族全空

**表1：划拨金额：划入区划×划入单位（清分流向）**（9 行）

| fiscal_allocation_view.rec_rgn_code | fiscal_allocation_view.rec_rgn_name | fiscal_allocation_view.rec_agency_code | fiscal_allocation_view.trans_amt | fiscal_allocation_view.count |
|---|---|---|---|---|
| 530000 | 云南省本级 | 36299bf16778469f9c5eafdbf16cc588 | 63371 | 291 |
| 530000 | 云南省本级 | db33a748c53e4f70b8c71569127f71df | 2936 | 129 |
| 530000 | 云南省本级 |  | 2541 | 9 |
| 530100 | 昆明市本级 | 62aa363159804af19811045eeef897f0 | 2541 | 8 |
| 530000 | 云南省本级 | 808548570b444a3ca6d9c1b4ed5428b7 | 664.62 | 33 |
| 530000 | 云南省本级 | dd9c08b7a7b948f795ec3f26f05ccdd9 | 324 | 8 |
| 530000 | 云南省本级 | 5c3391a145e546c9b5f61a512b590516 | 100 | 1 |
| 000000 | 中央 | df155e380d804b90be68033d4333a80b | 30 | 2 |
| 530102 | 五华区 | 808548570b444a3ca6d9c1b4ed5428b7 | None | 1 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.trans_amt",
    "fiscal_allocation_view.count"
  ],
  "dimensions": [
    "fiscal_allocation_view.rec_rgn_code",
    "fiscal_allocation_view.rec_rgn_name",
    "fiscal_allocation_view.rec_agency_code"
  ],
  "order": {
    "fiscal_allocation_view.trans_amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
```

</details>

**歧义拍板**："下级区划"取划入方区划 rec_rgn_code（层级 ETL 未补全，未做上下级过滤）；划拨金额取 trans_amt 口径

**答案文本**：口径：划拨金额=fiscal_allocation_view.trans_amt（划拨口径，非分入金额 im_amt），按划入方区划（rec_rgn_code）×划入方单位（rec_agency_code）分组。拍板说明："下级区划"按划入方区划 rec_rgn_code 解释——ai_context 注明上/下级层级 ETL 未补全，无独立"下级区划"成员，结果含中央/省本级/市/区县全部划入区划；如需仅限某一级下级区划请给区划编码过滤。划入方单位暂无名称列（待 ETL），仅出编码。数据范围：全时段清分记录，共 728 笔、划拨金额合计 72507.62 元，分组共 29 组（表中仅列有金额的前 9 组，其余 20 组金额为 null/未划拨），无截断。

**计划**：[["按划入方区划+划入方单位分组，统计划拨金额及笔数", "fiscal_allocation_view.trans_amt", "ai_context：划拨金额用 trans_amt；划入方看 rec_rgn_code/rec_agency_code，方向不混用"], ["划入区划名称仅展示辅助", "fiscal_allocation_view.rec_rgn_name", "ai_context：*_name 为别名拼接展示、不作准，分组用 *_code"]]

> **复核**：未如文件预期 nomatch：以划入方平级维度（rec_rgn_code×rec_agency_code）近似并明示层级缺失，口径透明。严格按契约「完全没覆盖→nomatch」应反问，agent 选择了透明近似作答（边界行为）。划入单位族「实测全空」的文件声明与 Cube 面不符（rec_agency_code 有值，29 组）。划拨合计 72,507.62 与 q05/q21 一致 ✓。

---

### q27　财政专户收入和国库收入分别是多少？

- **判定**：answer（可答）（sessionId `nlq1021-q27`，首答 21.3s，预聚合 —）
- **基准**：期望 nomatch：只能 funds_nature='2' 近似，无命名指标

**表1：清分收入按资金归口（bgt_style，全时段）**（3 行）

| fiscal_allocation_view.bgt_style | fiscal_allocation_view.im_amt | fiscal_allocation_view.count |
|---|---|---|
| 1 | 16016039490.68 | 644 |
| 2 | 39377 | 78 |
| 4 | 600 | 6 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_allocation_view.im_amt",
    "fiscal_allocation_view.count"
  ],
  "dimensions": [
    "fiscal_allocation_view.bgt_style"
  ],
  "order": {
    "fiscal_allocation_view.im_amt": "desc"
  },
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT `fiscal_allocation`.`fbgtstyle` `fiscal_allocation_view__bgt_style`, sum(`fiscal_allocation`.`fimamt`) `fiscal_allocation_view__im_amt`, count(*) `fiscal_allocation_view__count` 
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
GROUP BY 1
ORDER BY  2  DESC
LIMIT 100
```

</details>

**歧义拍板**："收入"绑定 im_amt（清分收入口径）而非划拨金额 trans_amt；未限定时间范围，按全时段汇总

**答案文本**：口径声明：以清分流向视图 fiscal_allocation_view 的分入金额 im_amt（清分收入口径）为准，按资金管理方式 bgt_style 区分归口（1=国库，2=财政专户，4=其他；3=代收无数据）。问句未限定时间范围，为全时段汇总。结果：国库收入 16,016,039,490.68 元（644 笔）；财政专户收入 39,377.00 元（78 笔）；另有归口为"其他"的 600.00 元（6 笔），非国库/专户口径未计入二者。数据为返回行原值，无截断。

**计划**：[["按资金管理方式 bgt_style 分组，取分入金额合计（清分收入口径）", "fiscal_allocation_view.im_amt", "ai_context：金额用 im_amt；bgt_style 1国库 2专户 3代收 4其他"], ["按 bgt_style 分组以区分国库/专户", "fiscal_allocation_view.bgt_style", "ai_context：资金归口用 bgt_style（1国库 2专户）+ rec_acct_type 互校"]]

> **复核**：**优于预期**：bgt_style（资金管理方式 1=国库/2=专户/4=其他）正是国库/专户区分成员，08 文件漏盘此口径。国库 160.16 亿与清分分入合计一致 ✓。

---

### q28　2022 年缴款金额排名前 10 的缴款人

- **判定**：answer（可答）（sessionId `nlq1021-q28-r2`，首答 26.2s，预聚合 未命中）
- **基准**：期望 nomatch：缴款人维度未建模

**表1：2022年缴款金额排名前10的缴款人（按 pay_date，金额=amt）**（1 行）

| fiscal_collection_view.payer_name | fiscal_collection_view.amt | fiscal_collection_view.count |
|---|---|---|
| None | 18208936572.27 | 385 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.amt",
    "fiscal_collection_view.count"
  ],
  "dimensions": [
    "fiscal_collection_view.payer_name"
  ],
  "timeDimensions": [
    {
      "dimension": "fiscal_collection_view.pay_date",
      "dateRange": [
        "2022-01-01",
        "2022-12-31"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.amt": "desc"
  },
  "limit": 10
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
SELECT (NULL) `fiscal_collection_view__payer_name`, sum(`fiscal_collection`.`famt`) `fiscal_collection_view__amt`, count(*) `fiscal_collection_view__count` 
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
GROUP BY 1
ORDER BY  2  DESC
LIMIT 102022-01-01T00:00:00.000Z2022-12-31T23:59:59.999Z
```

</details>

**歧义拍板**：缴款人取 payer_name 维度；脱敏导致其全为 null，属数据事实而非查询失败，未做反向探测。

**答案文本**：口径声明：缴款金额=fiscal_collection_view.amt（缴款明细口径），时间=pay_date 落在 2022-01-01~2022-12-31，缴款人维度=payer_name（meta 注明该列已脱敏）。数据范围：2022 全年共 385 行明细、合计缴款金额 18,208,936,572.27 元，但 payer_name 维度全部为空——分组仅返回 1 个 null 组，没有任何有名称的缴款人，因此无法给出有意义的 Top 10 名单。按空结果拍板：2022 年缴款人名称无有效数据（全库脱敏后为空）。

**计划**：[["按缴款人汇总2022年缴款金额取前10", "fiscal_collection_view.payer_name / fiscal_collection_view.amt", "ai_context：金额用 amt（缴款明细口径），时间过滤用 pay_date；缴款人名称 payer_name 已脱敏（access_policy）"]]

> **复核**：payer_name 已建模（meta 实证）但全空脱敏 → agent 按空结果拍板「无有效名单」，实质结论与文件 nomatch 预期一致（缴款人不可用）。18,208,936,572.27 与 q01 一致 ✓。「未建模」表述应修正为「已建模但数据脱敏为空」。

---

### q29　汇缴缴款的缴款明细记录有哪些？

- **判定**：ask→追问后 answer（sessionId `nlq1021-q29`，首答 21.8s，预聚合 —）
- **基准**：期望 nomatch：une_ 汇缴体系明细未建模

**反问**：「汇缴缴款」对应缴款书业务类型 bus_type（fbustype：直缴/汇缴），库中实际取值为 '1'（1063 行）和 '2'（209 行）两种，但模型 meta 与口径词典均未写明哪个编码是汇缴。请确认「汇缴」对应哪个值？

**选项**：
1. bus_type='2' 是汇缴（1=直缴，惯例映射）
2. bus_type='1' 是汇缴
3. 两个值都算汇缴（不做过滤）

**追问**（同会话续问，耗时 51.4s）：就按第一个选项的口径来（bus_type='2' 是汇缴（1=直缴，惯例映射）），直接出答案。

**表1：汇缴缴款明细（bus_type=2，前 100 行，按缴款日期倒序）**（20 行）

| fiscal_collection_view.pay_code | fiscal_collection_view.pay_date | fiscal_collection_view.chg_agency_code | fiscal_collection_view.chg_agency_name | fiscal_collection_view.sub_code | fiscal_collection_view.sub_name | fiscal_collection_view.count | fiscal_collection_view.amt |
|---|---|---|---|---|---|---|---|
| 53000026000000391098 | 2026-06-15T16:00:00.000 | 124045 | 001 / 测试云南测试环境 / 测试云南测试环境(试用版) / 测试云南测试环境(试用版)(试用版) | 1030110 | 民航发展基金收入 | 1 | 20000 |
| 53000026000000391100 | 2026-06-15T16:00:00.000 | 124045 | 001 / 测试云南测试环境 / 测试云南测试环境(试用版) / 测试云南测试环境(试用版)(试用版) | 103010201 | 中央农网还贷资金收入 / 中央农网还贷资金收入25 | 1 | 65017.59 |
| 53000026000000391080 | 2026-06-15T16:00:00.000 | 124045 | 001 / 测试云南测试环境 / 测试云南测试环境(试用版) / 测试云南测试环境(试用版)(试用版) | 103042758 | 高等学校住宿费 | 1 | 14820171 |
| 53000026904000000036 | 2026-06-05T16:00:00.000 | 998017 | 通用测试单位070301 | 1030110 | 民航发展基金收入 | 1 | 301.98 |
| 53000026904000000010 | 2026-06-05T16:00:00.000 | 998017 | 通用测试单位070301 | 1030110 | 民航发展基金收入 | 1 | 402.64 |
| 53010226821000000227 | 2026-04-02T16:00:00.000 | 125026 | 云南医保测试单位改名 / 开票点一 / 李思维 | 1030115 | 港口建设费收入 | 2 | 1981.32 |
| 53010026000000390247 | 2026-01-12T16:00:00.000 | 124992 | 云南信息技术中心 / 信息技术中心 | 103010201 | 中央农网还贷资金收入 / 中央农网还贷资金收入25 | 1 | 484 |
| 53010026000000390247 | 2026-01-12T16:00:00.000 | 124992 | 云南信息技术中心 / 信息技术中心 | 1030115 | 港口建设费收入 | 2 | 528 |
| 53010026000000390247 | 2026-01-12T16:00:00.000 | 124992 | 云南信息技术中心 / 信息技术中心 | 103042758 | 高等学校住宿费 | 1 | 324 |
| 53010026000000390247 | 2026-01-12T16:00:00.000 | 124992 | 云南信息技术中心 / 信息技术中心 | 1030110 | 民航发展基金收入 | 1 | 396 |
| 53000025907000000033 | 2025-10-14T16:00:00.000 | 998021 | 云南医疗测试单位10131 | 103010201 | 中央农网还贷资金收入 / 中央农网还贷资金收入25 | 1 | 632.36 |
| 53000025907000000033 | 2025-10-14T16:00:00.000 | 998021 | 云南医疗测试单位10131 | 1030121 | 旅游发展基金收入 | 1 | 3120 |
| 53010025000000389434 | 2025-10-14T16:00:00.000 | 124994 | 云南发展改革委员会 / 开票点001 / 开票点002 | 103010201 | 中央农网还贷资金收入 / 中央农网还贷资金收入25 | 1 | 100 |
| 53000025821000000570 | 2025-07-28T16:00:00.000 | 125026 | 云南医保测试单位改名 / 开票点一 / 李思维 | 1030110 | 民航发展基金收入 | 1 | 861 |
| 53000025849000000268 | 2025-06-17T16:00:00.000 | 999012 | 智能核销单位0408 | 1030115 | 港口建设费收入 | 1 | 123 |
| 53000025902000000065 | 2025-06-17T16:00:00.000 | 425107 | 云南测试单位95 | 1030115 | 港口建设费收入 | 1 | 123 |
| 53000025902000000030 | 2025-06-16T16:00:00.000 | 425107 | 云南测试单位95 | 1030121 | 旅游发展基金收入 | 1 | 369 |
| 53000025902000000049 | 2025-06-16T16:00:00.000 | 425107 | 云南测试单位95 | 1030121 | 旅游发展基金收入 | 1 | 123 |
| 53000025902000000057 | 2025-06-16T16:00:00.000 | 425107 | 云南测试单位95 | 1030121 | 旅游发展基金收入 | 1 | 246 |
| 53000025849000000209 | 2025-06-15T16:00:00.000 | 999012 | 智能核销单位0408 | 1030115 | 港口建设费收入 | 1 | 123 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.count",
    "fiscal_collection_view.amt"
  ],
  "dimensions": [
    "fiscal_collection_view.pay_code",
    "fiscal_collection_view.pay_date",
    "fiscal_collection_view.chg_agency_code",
    "fiscal_collection_view.chg_agency_name",
    "fiscal_collection_view.sub_code",
    "fiscal_collection_view.sub_name"
  ],
  "filters": [
    {
      "member": "fiscal_collection_view.bus_type",
      "operator": "equals",
      "values": [
        "2"
      ]
    }
  ],
  "order": {
    "fiscal_collection_view.pay_date": "desc"
  },
  "limit": 100
}
```

**表2：汇缴缴款汇总（bus_type=2，全量单行聚合）**（1 行）

| fiscal_collection_view.count | fiscal_collection_view.paybook_count | fiscal_collection_view.amt |
|---|---|---|
| 209 | 120 | 2284794298.882 |

**生成 query：**
```json
{
  "measures": [
    "fiscal_collection_view.count",
    "fiscal_collection_view.paybook_count",
    "fiscal_collection_view.amt"
  ],
  "dimensions": [],
  "filters": [
    {
      "member": "fiscal_collection_view.bus_type",
      "operator": "equals",
      "values": [
        "2"
      ]
    }
  ],
  "limit": 100
}
```

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表1</summary>

```sql
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
```

</details>

<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表2</summary>

```sql
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
```

</details>

**歧义拍板**：汇缴拍板为 bus_type='2'（1=直缴，惯例映射；meta 与词典原先未写明编码），已固化进口径词典

**答案文本**：口径：汇缴 = fiscal_collection_view.bus_type（fbustype）= '2'（1=直缴），按你拍板的口径执行，并已回写口径词典（term=汇缴，legacy:false）。数据范围：全库汇缴缴款明细共 209 行（缴款书 120 票），缴款金额合计 2,284,794,298.88 元；明细表按缴款日期倒序返回前 100 行（覆盖 2024-10-09 至 2026-06-15），其余 109 组明细可提高 limit 或在构建器中查看全量。

**计划**：[["汇缴 = 缴款书业务类型 bus_type=2（用户拍板，1=直缴），已回写口径词典", "fiscal_collection_view.bus_type", "用户选项一拍板 2026-10-21；词典词条已固化（legacy:false）"], ["明细行数用 count、缴款书笔数用 paybook_count（一票多项目行）、金额用 amt", "fiscal_collection_view.amt", "meta ai_context：明细金额 amt；缴款书笔数 paybook_count"], ["明细按缴款码×缴款日期×执收单位×票面科目展示，取前 100 行按缴款日期倒序", "fiscal_collection_view.pay_code", "meta：分组用 *_code，名称列仅展示"]]

> **复核**：agent 把「汇缴」落到 bus_type='2'（120 票/209 行/22.85 亿）——对问句字面合理并已回写词典；但文件所指缺口是 une_ 汇缴体系明细（未建模），该缺口未显式宣告。属问句歧义（体系明细 vs 业务类型）而非 agent 错误。

---

### q30　各笔缴款的到账日期和退付金额是多少？

- **判定**：nomatch（答不了）（sessionId `nlq1021-q30`，首答 22.7s，预聚合 —）
- **基准**：期望 nomatch：到账日期轴/退付缓建未建模

**缺口**：["「到账日期」可查：fiscal_collection_view.received_date（资金到账日期，freceiveddate）为明细级维度，可逐笔给出", "「退付金额」在当前模型中不存在任何成员：fiscal_collection_view / fiscal_treasury_view 成员面均无退付/退库类度量或维度", "退付口径词典无词条（GET /agent/dictionary?term=退付 为空，无 legacy 可参考）", "fiscal_collection 未建模盘点（conf/unmodel/fiscal_collection.json 不存在，status=未盘点），无法确认源库退付表（UBR_PAYCODE 系，本环境实测 0 行）是否可补建", "需要拍板：①若接受用「到账金额 entered_amt」或「缴款金额 amt」替代退付金额，可立即出「缴款码×到账日期×金额」明细表；②若必须退付金额，需先做未建模盘点/补建后另查"]

**nomatch 原文**：各笔缴款的到账日期和退付金额是多少？

> **复核**：nomatch 合规：退付成员成员面全空+词典无词条；且 agent 明示「到账日期可查」并给替代方案（received_date/entered_amt 实测有数 2022-2026 五个年度组）。**08 文件「到账日期轴数据空缺」缺口声明已过时**。缺口文案引用 UBR_PAYCODE 0 行属记忆召回，轻微越线（无实害）。

---

## 附录 A：q13 恢复的完整答案

> q13 引擎执行成功但输出 JSON 畸形（`"assumption":"..."` 键值对混入 `plan` 数组内部，数组未闭合）
> → 服务端 `JSON.parse` 失败 502。以下为从 agent-svc 日志恢复、仅做形态修复（内容零改动）的完整答案：

```json
{
  "type": "answer",
  "title": "按收入类别看四类收入占比（缴款金额）",
  "plan": [
    [
      "按收入类别分组统计缴款金额占比",
      "fiscal_collection_view.income_sort_name",
      "收入类别名称（income_sort_name）天然包含四类收入，直接分组"
    ],
    [
      "金额用缴款金额 amt",
      "fiscal_collection_view.amt",
      "ai_context：明细金额用 amt"
    ],
    [
      "分母用全量不带分组的合计",
      "fiscal_collection_view.amt",
      "单独查询取全量总数，占比在表内计算"
    ]
  ],
  "assumption": "四类收入词直接映射到 income_sort_name 取值（词典无词条、无口径分叉），按该维度分组；金额用 amt；未加时间过滤",
  "tables": [
    {
      "title": "收入类别×缴款金额及占比（全量）",
      "query": {
        "measures": [
          "fiscal_collection_view.amt"
        ],
        "dimensions": [
          "fiscal_collection_view.income_sort_name"
        ],
        "order": {
          "fiscal_collection_view.amt": "desc"
        },
        "limit": 100
      },
      "rows": [
        {
          "fiscal_collection_view.income_sort_name": "政府性基金收入",
          "fiscal_collection_view.amt": "18285222472.21",
          "share_pct": "99.7437"
        },
        {
          "fiscal_collection_view.income_sort_name": "专项收入",
          "fiscal_collection_view.amt": "30951894.082",
          "share_pct": "0.1688"
        },
        {
          "fiscal_collection_view.income_sort_name": "行政事业性收费收入",
          "fiscal_collection_view.amt": "16031930.84",
          "share_pct": "0.0874"
        },
        {
          "fiscal_collection_view.income_sort_name": "（空）",
          "fiscal_collection_view.amt": "600",
          "share_pct": "0.0000033"
        },
        {
          "fiscal_collection_view.income_sort_name": "罚没收入",
          "fiscal_collection_view.amt": "306",
          "share_pct": "0.0000017"
        }
      ],
      "total": "18332207203.132"
    }
  ],
  "answer": "口径声明：按收入类别（income_sort_name）分组，金额用缴款金额 amt（明细缴款口径），分母为全量合计 18332207203.132 元（单独无分组查询取得），占比=各类金额÷全量合计。结果：政府性基金收入 18,285,222,472.21 元占 99.7437%；专项收入 30,951,894.08 元占 0.1688%；行政事业性收费收入 16,031,930.84 元占 0.0874%；罚没收入 306 元占约 0.0000017%（几乎为零）。另有收入类别为空的 600 元一并计入分母。数据范围：全部缴款数据，未加时间过滤；共 5 组，无截断。",
  "truncated": false,
  "rows": 5,
  "hitPreAgg": true,
  "audited": false
}
```

## 附录 B：执行与复现方式

**单问手测**（中文 body 必须落盘走 `-d @file`，git-bash 内联中文必 GBK 500）：

```bash
printf '{"question":"2022 年全年非税缴款金额和笔数是多少？","sessionId":"nlq-demo-1"}' > /tmp/q.json
curl -s -X POST http://localhost:4100/chat -H "Content-Type: application/json" -d @/tmp/q.json
```

**批量实测**（本记录 30 问的驱动，问数+追问+编译 SQL 一条龙）：

```bash
cd D:/develop/cube/.tmp/nlq-1021
python run.py        # 30 问并发 2 路 → raw/*.json，随后逐 answer 抓 /cubejs-api/v1/sql → sql/*.sql
python followup.py   # ask 态同 sessionId 续问采用第一选项 → raw/*-followup.json + 对应 sql
python gen.py        # 生成本记录（record-draft.md）
```

要点：每问独立 `sessionId`（agent-svc 以 sessionId resume 引擎会话，独立 id = 无记忆污染）；
编译 SQL 用 `POST /cubejs-api/v1/sql`（body 同 `/agent/query` 的 query），token 取 `.env` 的 `CUBEJS_API_SECRET`；
全程逐块日志在 `logs/agent-svc-YYYY-MM-DD.log`（thinking/tool_use/tool_result 全文）。

## 附录 C：关键发现（复核结论）

1. **维度选错 1 例（q17，最重）**：问「执收区划」按 rec_rgn_code（收入区划）分组，meta 明有 chg_rgn_code；agent 还引用 ai_context 做错误辩护。建议：ai_context 或词典显式固化区划族（执收=chg_* / 收入=rec_*）映射。
2. **08 文件能力盘点与 Cube 部署面落差（4 例）**：q07/q09 单位层级（文件称可答、Cube 面无层级成员）；q21 基准口径为划拨子集拆分（且 is_transfer 全空是新发现）；q22 income_status 不存在（仅 enter_status）；q24 is_cleared 不存在（仅 clear_date 空）。
3. **08 文件缺口声明过时（3 例）**：到账日期轴（received_date 有数 2022-2026、entered_amt 同环比族齐全）；国库/专户（bgt_style 可直接答，q27）；缴款人（payer_name 已建模、脱敏全空，q28）。
4. **ask 态 6 问全部合规反问且追问后落地**：非税缴款/清分率/欠缴/汇总批次/直缴汇缴清分率/汇缴明细——每问给出带依据的选项，拍板后均出答案并回写词典，无静默选口径。
5. **已知缺陷复现 2 例 + 新发现 1 例**：q23 空串假批次（550 条≠真批次 428）；q25 跨 view 无 join path（直缴/汇缴清分率查不了，需联查 view）；新发现 is_transfer 全空、trans_stats=9 全库 0 条（划拨环节基本未发生）。
6. **输出形态缺陷 1 例（q13）**：引擎 success 但最终 JSON 畸形（assumption 键值混入 plan 数组）→ 服务端解析 502，重试同型失败；完整答案已从日志恢复（附录 A）。建议加固：服务端轻量 JSON 修复或 SKILL 输出兜底加嵌套示例。
7. **数字交叉验证全部通过**：全库缴款 183.32 亿（q05/q17/q20）、2022 缴款 182.09 亿（q01/q19/q28）、清分分入 160.16 亿（q05/q16/q17/q27）、划拨 72,507.62 元（q05/q21/q26）、民航 3,085.09 万≈基准 3,085.08 万（q11/q12）。
8. **基准数字口径注记**：文件 q01 基准 183.32 亿/1,101 笔实为全库总额（2022 年应为 182.09 亿/334 缴款书）；1,101 笔在 Cube 侧任何口径均未复现（缴款书 968/明细 1,272）——两套模型（Datus fne_fund_main vs Cube fne_paybook_full_high）数字不可直接对表。
9. **未建模清单未盘点**：fiscal_collection/fiscal_allocation 的 unmodel 状态=「未盘点」（q07/q09/q30 三处缺口都指向此）——建议先跑一轮未建模盘点再决定补建优先级。
