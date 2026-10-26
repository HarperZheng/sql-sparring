# round-02 回改单

- 日期：2026-10-26　主表 15 行（剔除 15 题已删除出轮）：已审定 11 / 草案 4

## 文件头（回改契约）

**回改五步**：①查证起草（智能体：读轮报分歧明细，codeqa 逐题查真实字段解法——过滤器+指标+维度+时间锚，写入本单，待查证→草案）→ ②审定（人：逐行审定，草案→已审定）→ ③施工（人：按回改卡改双侧语义层+清记忆，→已施工）→ ④复验（`bin/round.py --retest` 一条命令自动：清 datus chat memory[全量，不可逆无备份]→重启两服务→原题重跑到轮报；挂→回③，口径错→回①）→ ⑤闭环（人：复验通过且确认后把本单对应行状态改"闭环"；无独立套件文件，本单即闭环账本）。

**状态机**：待查证→草案→已审定→已施工→闭环；终态另有剔除（本轮不做的题，不进五步与闭环统计）。

**冲突规则**：本单与裁决书冲突以本单为准（本单产生于 codeqa 查证之后）；本单与课本「已裁定口径」冲突以课本为准；全局拍板写在本文件头，逐行拍板不得与之相悖。

**全局拍板（2026-10-26，适用全轮逐行）**：

1. **缴款时间统一用 FDATE**（缴款日期，字段 `fdate`），精度只到日期（toDate），不带时、分、秒。涉"缴款日期"锚点的题一并按此执行。
2. **「已缴入国库」判定统一 fenterstatus='1'**（资金实际入库态），时间锚统一 **fenterdate**（入库日期，toDate）。涉"缴入国库"判定或缴库环节时间锚的题（q05、q21、q27、q28、q29、q30）一并执行；q27 的"尚未缴入国库"取其否定（fenterstatus≠'1'）。
3. **字段取数以 codeqa 查证的云南生产源代码为准**（feedback 单所记字段即 codeqa 结论，不再逐处标注存疑）；Oracle 应用库结论落到 ClickHouse 落地表前须先做列名映射验证（属施工核对动作，不改变本单字段结论）。
4. **档位阈值统一以 10 倍为区间**（2026-10-26）：每档上界=下界×10，首尾开区间兜底；金额类起点 1 千元（<1千/1千–1万/1万–10万/10万–100万/≥100万），时长类起点 1 天（<1天/1–10天/10–100天/≥100天）。涉分档题（q19/q21/q22/q23/q24）一律按此，不再逐题定档。
5. **笔数键统一 fpaycode**（2026-10-26）：缴款类笔数指标（缴款/完成/未缴/分档/耗时配对）统一 `COUNT(DISTINCT fpaycode)` 去重计数；q18 改法行"fid 1:1 可保留"随之作废——落地库实测 1,281 行 fid distinct 1,110 / fpaycode distinct 975，92 个 fpaycode 拆多明细行，1:1 不成立。涉 q18/q19/q21/q22；q24/q27 的 ftransno 属划拨/缴库单据号口径，不在本拍板内。datus 侧已回③返工（2026-10-26）：非税缴款笔数=975、完成缴款笔数=直缴 570/汇缴 68 合计 638（原 fid 口径 629/99/728）。

## 主表

| id | 问题 | 修改对象 | 过滤器 | 指标 | 维度 | 时间锚 | 状态 |
|---|---|---|---|---|---|---|---|
| q10 | 今年各月的缴款金额走势怎么样？ | 双侧 | 今年缴款（fdate 落 2026） | 缴款金额（双侧现行，不变） | 月份 | FDATE(toDate)（全局拍板1） | 已审定 |
| q11 | 今年已经缴入国库的非税资金一共有多少？ | 双侧 | fenterstatus='1'（fincomestatus 不参与） | 缴库金额 SUM(ftotalamt) | —（无维度分解） | fenterdate(toDate)（全局拍板2） | 已审定 |
| q12 | 今年通过直缴方式缴款的资金总额是多少？ | 双侧 | 直缴 fbustype='1' + 今年缴款（fdate 落 2026） | 缴款金额（不变） | —（总量） | FDATE(toDate)（全局拍板1） | 已审定 |
| q14 | 今年缴款金额排名前十的缴款人有哪些？ | 双侧 | 今年缴款（fdate 落 2026） | 缴款金额 | 缴款人（付款方）Top10（账号字段不建维度） | FDATE(toDate)（全局拍板1） | 已审定 |
| q15 | 今年各代理银行代收的非税收入金额排名情况怎么样？ | 双侧 | 今年（fdate 落 2026） | 代收非税收入金额（不变） | 代理银行（排名） | FDATE(toDate)（全局拍板1） | 已审定 |
| q16 | 今年按收入项目汇总的待划拨金额，排名前五的收入项目是哪些？ | cube（datus 零修改） | 未划拨 fistransfer!='1'（trans_stats 整列未同步，不作过滤依据）+今年 | 待划拨金额 pending_trans_amt=SUM(ftransamt)（ftransamt=CH 落地列名，源侧应用库=FAMT，两层不冲突，datus yml:1639） | 收入项目（Top5） | clear_date 清分日期（双侧时间轴对齐） | 已审定 |
| q17 | 今年各家执收单位经手的收入金额排下来，前十名是哪些单位？ | 双侧 | 今年（fdate 落 2026） | 执收单位经手收入金额（不变） | 执收单位（Top10） | FDATE(toDate)（全局拍板1） | 已审定 |
| q18 | 今年完成的缴款里，直缴和汇缴两种方式各有多少笔？占比是多少？ | 双侧 | 完成缴款 fisreceived='1' | 完成笔数 COUNT(DISTINCT fpaycode)（fid 1:1 不成立，随全局拍板5；占比=各方式笔数÷完成总笔数，分母不带维度单独全量查） | fbustype（'1'直缴/'2'汇缴，datus 补枚举标签） | fdate(toDate)（"完成的缴款"不另立 freceiveddate 到账锚） | 已审定 |
| q19 | 今年单笔缴款按金额大小分档后，各档的缴款笔数分布是怎样的？ | 双侧 | 今年缴款（fdate 落 2026）+排除作废 fstate!='2' | 笔数 COUNT(DISTINCT fpaycode) | 金额档位（单笔金额=缴款书总额 ftotalamt，非明细行 famt；代码无现成档位标准，按全局拍板4 10 倍区间：<1千/1千–1万/1万–10万/10万–100万/≥100万） | fdate(toDate)（全局拍板1） | 草案 |
| q20 | 今年完成清分的资金，按中央、省、市、县四级归属的金额占比是怎样的？ | cube | 完成清分 fispayenter='Y'（fpayenterdate 非空兜底）+今年 fdate 落 2026 | SUM(fne_funddivide.fimamt 分入金额)（占比=各级金额/总额） | 归属级次 frechgncode（收入区划）→afa_auth_region.fbgtlevel→字典110（1中央/2省/3市/4县/5乡/0共享） | fdate/fyear(toDate)（fcleardate 是清分操作时间，非业务锚） | 草案 |
| q21 | 今年从缴款到资金缴入国库，各笔缴款的全程耗时按时间区间分档后，各档的笔数分布如何？ | 双侧 | —（拍板未涉额外过滤） | 耗时天数=fenterdate−fdate + 笔数 COUNT(DISTINCT fpaycode) | 耗时区间分档（代码无现成耗时/分档逻辑，按全局拍板4 时长序列：<1天/1–10天/10–100天/≥100天）；跨链逐笔配对 une_paybook.fpaycode=fne_treasury_transfer.fpaycode（TreasuryDao 子查询证实） | 起点 fdate(toDate)（全局拍板1；codeqa 备查 fconfirmdate=缴款确认日，复验偏差回①）→终点 fenterdate(toDate)（全局拍板2） | 草案 |
| q22 | 今年已开具但缴款人一直未缴款的缴款通知书，按未缴时长分档统计，各档有多少笔？ | 双侧 | 已开具且未缴款 fstate='1'（fstate!='2' 保有效）+fne_paybook 按 fpaycode 左连无记录兜底 | 未缴笔数 COUNT(DISTINCT fpaycode) | 未缴时长分档（全局拍板4 时长序列：<1天/1–10天/10–100天/≥100天） | ffillDate(toDate)（未缴时长=开具日至今，无缴款日期可减） | 已审定 |
| q23 | 执收单位已经收上来但还没有汇缴上缴的资金，按滞留时长分档，各档金额是多少？ | cube | 已收 fisreceived='1'（同 q18 完成口径）+未汇缴（fisgenerec=0 未生成缴库记录；单位端 fbatchno IS NULL；fbustype 是直缴/汇缴业务类型勿用作汇缴状态） | 滞留金额 SUM(fnr_unpaid.famt)（累计未汇缴，报表列 JZQJAMT 直接取） | 滞留时长分档（代码无现成分档逻辑，按全局拍板4 时长序列：<1天/1–10天/10–100天/≥100天） | freceiveddate 到账日（起算锚；存量池，题面无"今年"限定） | 草案 |
| q24 | 今年已下达划拨指令但资金尚未划转到账的部分，按滞留时长分档，各档金额有多大？ | 双侧 | 在途滞留池：fistransfer='1'（配 fstats∈{1,9}）+fiseenter='0'（兜底 fenterdate IS NULL）+今年下达 FTRANSDATE 落 2026 | 主=在途滞留金额 SUM(FAMT)，辅=在途笔数 COUNT(DISTINCT FTRANSNO)，派生=滞留天数（当前日−FTRANSDATE）；字段纠偏：应用库源侧无 trans_stats/ftransamt，实为 FSTATS/FAMT；落地列名=ftransamt/trans_stats/fisenter（源侧 FAMT/FSTATS/fiseenter 的 CH 映射，datus yml:1639/933 已按映射施工） | 滞留时长分档（全局拍板4 时长序列） | FTRANSDATE(toDate)（下达日） | 已审定 |
| q27 | 有没有资金尚未缴入国库、就已经完成对账或财政记账的记录？ | 双侧 | 两层：①对账层 freconcilestatus='1'（0未对账/1成功/2失败）且 fenterstatus≠'1'；②记账层 fincomestatus='1' 且 fenterstatus≠'1'（合全局拍板2） | ftransno 去重笔数+单号明细 | 异常类型（对账/记账） | —（异常存在性校验，无时间锚） | 已审定 |
## 回改卡（已审定 11 + 草案 4）

### q10 今年各月的缴款金额走势怎么样？

- 裁决：建模差异（缴款金额时间锚双轨：datus 主时间轴 fill_date；cube pay_date）
- 证据：人工拍板（全局拍板1；q10/q12/q15/q17 四题同根因合并拍板）
- 拍板结论：时间锚 FDATE(toDate)，维度按月，指标缴款金额不变
- datus 改法：主时间轴由开票日 `fill_date=toDate(ffilldate)` 切换为 `FDATE=toDate(fdate)`
- cube 改法：维持 `pay_date=toDateOrNull(fdate)`（本就是 FDATE），确认输出仅到日期、不带时分秒
- 前置验证：两侧改后各跑 q10，月度金额序列应一致
- 记忆清理：datus 清"缴款走势按开票日"相关 chat memory；cube 口径落词典
- 验收：④复验 q10 双侧互证通过

### q11 今年已经缴入国库的非税资金一共有多少？

- 裁决：建模差异（"已缴入国库"的状态判定与时间锚）
- codeqa 证据：2026-10-26 图谱问答（财政票据V3-云南，图谱 ready）——fstatus（缴库指令执行结果，回执驱动 2→33→9/39）与 fenterstatus（资金实际入库，入库流水驱动）不等价：EVL 回单路径 fenterstatus='1' 对应 fstatus='39'；人工缴库两步写存在 fstatus='9' 而 fenterstatus≠'1' 中间态；直缴表 fne_agen_treasury 无 fenterstatus 字段；fmsgdate 经实测在云南库代码零命中（字段不存在）。国库接收判据 `TreasuryAccept.xml:55-59`：(fstatus='39' or '9') and FINCOMESTATUS='0' and fenterdate is not null——入账认定含 fenterdate 非空，佐证入库态以 fenterstatus/fenterdate 为准
- 拍板结论：过滤器 fenterstatus='1'（fincomestatus 属"已写国库收入"第三层，不参与本口径）；指标 缴库金额 SUM(ftotalamt)；维度 无；时间锚 fenterdate(toDate)
- datus 改法：判定条件 fstatus='9'+income_status 分层 → fenterstatus='1'；时间锚 fmsgdate → fenterdate
- cube 改法：维持 fenterstatus='1'+fenterdate，随拍板确认（零修改）
- 前置验证：ClickHouse 落地库 fenterstatus/fenterdate 列存在性与 '1' 行数量级
- 记忆清理：datus 清"已缴库=fstatus 9/income_status 分层"相关 chat memory（q11 及沿用它的 q21/q27-q30 探索记忆）；cube 口径落词典
- 验收：④复验 q11 双侧同口径同值。注：本轮双卡金额恰好同为 33,306.09 元属当前数据巧合，不作等价依据

### q12 今年通过直缴方式缴款的资金总额是多少？

- 裁决：建模差异（缴款类"今年"时间锚点，同 q10 根因）
- 证据：人工拍板（全局拍板1）
- datus 改法：年度窗口锚点改用 FDATE(toDate)
- cube 改法：已锚 pay_date=FDATE，随总拍板确认精度到日期（零修改）
- 前置验证：同 q10
- 记忆清理：datus 清"直缴年度窗口按开票日"类记忆
- 验收：④复验 q12 双侧互证通过

### q14 今年缴款金额排名前十的缴款人有哪些？

- 裁决：待人工→已审定（缴款人维度缺失 + payer_name 全列脱敏）
- 证据：人工拍板（cube 卡内自述 payer_name 全列脱敏为空，access_policy 侧；datus 缴款人维度未建）
- datus 改法：语义层补"缴款人（付款方）"维度
- cube 改法：解除 `payer_name`（物理 `fpayername`）的 access_policy 脱敏——当前全列脱敏为空致排名不可答
- 前置验证：解除脱敏后抽查 fpayername 非空率与样例值
- 记忆清理：datus 清"缴款人不可查"类记忆；cube 口径落词典
- 验收：④复验 q14 双侧 Top10 名单可比。注：缴款人账号类字段（`fpayerno`/`fpayerid`）维持不建维度，不在本拍板范围

### q15 今年各代理银行代收的非税收入金额排名情况怎么样？

- 裁决：建模差异（"今年"时间锚点，同 q10 根因）
- 证据：人工拍板（全局拍板1）
- datus 改法："今年"窗口锚点改用 FDATE(toDate)
- cube 改法：已锚 FDATE，随总拍板确认精度到日期（零修改）
- 前置验证：同 q10
- 记忆清理：datus 清"代理银行排名按开票日"类记忆
- 验收：④复验 q15 双侧互证通过

### q16 今年按收入项目汇总的待划拨金额，排名前五的收入项目是哪些？

- 裁决：建模差异（cube 缺"待划拨金额"度量；trans_stats 2026 年全空）
- 证据：人工拍板 + q16 卡实测（trans_stats 整列未同步）
- datus 改法：零修改——语义层已有"未划拨金额"指标，按原问答对（勾稽 424=324+100）
- cube 改法：① 度量 `pending_trans_amt`=sum(ftransamt) WHERE fistransfer!='1'（与 datus 同口径；trans_stats 整列未同步，不作过滤依据）；② `fiscal_allocation_view.yml` includes 白名单加入该度量；③ 词典/ai_context 词条"待划拨金额"（synonyms=未划拨金额，时间轴=清分日期 clear_date 与 datus 对齐；复验按原问作答，不得自动改答已划拨）
- 前置验证：动手前先跑 fistransfer 分布（预期 '1'→324、其余→100）
- 记忆清理：cube 口径落词典
- 验收：④复验 q16 双侧前五收入项目与金额一致

### q17 今年各家执收单位经手的收入金额排下来，前十名是哪些单位？

- 裁决：建模差异（"今年"时间锚点，同 q10 根因）
- 证据：人工拍板（全局拍板1）
- datus 改法："今年"窗口锚点改用 FDATE(toDate)
- cube 改法：已锚 FDATE，随总拍板确认精度到日期（零修改）
- 前置验证：同 q10
- 记忆清理：datus 清"执收单位排名按开票日"类记忆
- 验收：④复验 q17 双侧互证通过

### q18 今年完成的缴款里，直缴和汇缴两种方式各有多少笔？占比是多少？

- 裁决：建模差异（"完成的缴款"界定与笔数粒度）
- codeqa 证据：2026-10-26 图谱问答——完成=`fne_paybook.fisreceived='1'`（`PayBookServiceImpl.java:750-765` 写入、`UPayBook.xml:46-50` 报表判据）；fid 与 fpaycode 1:1（`PayBookServiceImpl.java:722-729` 唯一性校验）；fbustype '1'直缴/'2'汇缴（`PayBook.java:69`，cube 词典映射获证实）；cube state='3' 与代码字典冲突（`BillStateConsts.java:3-14`：3=已缴款未到账、4=已到账；cube 视图 state 物理映射不在本仓未核）
- 拍板结论：过滤器 fisreceived='1'；指标 完成笔数 COUNT(DISTINCT fpaycode)；维度 fbustype（'1'直缴/'2'汇缴，datus 补枚举标签）；时间锚 fdate（"完成的缴款"不另立 freceiveddate 到账锚）
- datus 改法：时间锚 ffilldate→fdate + 补完成态过滤；笔数键 fid（原判 1:1 可保留）→ COUNT(DISTINCT fpaycode)（2026-10-26 全局拍板5：1:1 前提经落地实测不成立——92 个 fpaycode 拆多明细行，两笔数指标已回③返工为 fpaycode，实测直缴 570/汇缴 68 合计 638）
- cube 改法：完成态 state='3'→fisreceived='1'；时间锚 pay_date=fdate 已符。占比=各方式完成笔数÷完成总笔数，分母用不带维度的单独全量查询
- 前置验证：ClickHouse 落地表 fisreceived 列映射验证（Oracle 应用库结论，未验证）
- 记忆清理：datus 清"完成缴款=全部缴款/按开票日"类记忆；cube 词典改"完成"词条
- 验收：④复验 q18 双侧直缴/汇缴笔数与占比一致。注：q22/q26（票据类剔除集）的"缴款（未）完成"判定留待后续随本口径对齐

### q19 今年单笔缴款按金额大小分档后，各档的缴款笔数分布是怎样的？

- 裁决：待人工→草案（档位标准双侧不一 + cube 复验链路 502）
- 现状：datus 自定档位 <1万/1–10万/10–50万/50–100万/≥100万；cube ask 选项 100元以下/100–1万/1–10万/10–100万/100万以上。cube 侧另有复验链路问题：自动拍板后的追加重放遇 502 Bad Gateway（修bug）
- codeqa 证据：2026-10-26 图谱问答（云南源代码）——单笔缴款金额=缴款书总额 `UNE_PAYBOOK.FTOTALAMT`（与明细行 famt 不同层，按笔分档须取总额）；作废态=`fstate='2'`（q22 同源）；全库搜"分档/档位"零命中——代码无现成档位标准，属业务自定口径；财政端缴款日期 `FNE_PAYBOOK.FPAYDATE` 为 VARCHAR(yyyyMMdd) 格式
- 拍板结论：过滤器 今年缴款（fdate 落 2026，全局拍板1）+排除作废 fstate!='2'；指标 笔数 COUNT(DISTINCT fpaycode)；维度 金额档位（按 ftotalamt 切桶，全局拍板4 10 倍区间：<1千/1千–1万/1万–10万/10万–100万/≥100万）；时间锚 fdate(toDate)
- datus 改法：核对现行金额取数层（明细 famt vs 缴款书总额 ftotalamt），统一按 ftotalamt；档位改全局拍板4 10 倍区间（弃自定 <1万/1–10万/10–50万/50–100万/≥100万 五档）；年度窗口锚 fdate
- cube 改法：ask 选项归一为拍板4 10 倍区间序列；另修复验链路 502 Bad Gateway（执行事故，独立于口径修）
- 前置验证：CH 落地表 fdate/ftotalamt/fstate 列名映射验证（全局拍板3，未验证）
- 查证实证（2026-10-26 直查落地库）：前置验证① 完成——fdate/ftotalamt/fstate 落地即此名，无需映射；笔数键落地实测 1,281 行 fid distinct 1,110 / fpaycode distinct 975（92 个 fpaycode 拆多明细行），拍板字面 fpaycode 可执行（键冲突已由全局拍板5 统一解决）；2026 池（pay_date 落 2026 + fstate≠'2'）按 fpaycode 分档预览：<1千 44 / 1千–1万 8 / 1万–10万 3 / ≥100万 1（按 fid 口径则 45/13/3/1）；ftotalamt 书级 0 冲突（同 fpaycode 多行总额一致）。施工遗留：档位边界归属（恰 1 千元落 <1千 还是 1千–1万）拍板4 未写明，暂按左闭右开 [下界, 上界) 施工
- 记忆清理：datus 清"按明细金额分档"类记忆；cube 词典落"单笔缴款金额"词条
- 验收：④复验 q19 双侧同档位笔数分布一致

### q20 今年完成清分的资金，按中央、省、市、县四级归属的金额占比是怎样的？

- 裁决：待人工→草案（cube 缺清分归属级次维度）
- 现状：cube 缺中央/省/市/县四级映射维度；datus 卡有 frecrgncode 映射自述（000000=中央、530000=省、非 000000 且后两位 00=市、非 00 结尾=县，见留档提交 8b65831 的候选行存档，未经验证）
- codeqa 证据：2026-10-26 图谱问答——"完成清分"=是否到账对账 `FISPAYENTER='Y'`（`FundDivide.xml:80-82`；或 `FPAYENTERDATE` 非空兜底，`DayEndPayInfoCapitalReceiveReconcileServiceImpl.java:86-89`）；级次权威映射=收入区划 `FRECRGNCODE` → 区划表 `AFA_AUTH_REGION.FBGTLEVEL` → 字典110（1中央/2省/3市/4县/5乡/0共享，`BgtLevelConsts.java:10-35`）；代码按级次分列 F_IMAMT_ZY/SHENJI/SHIJI/XIANJI/XIANGJI+单位提留（FCALCSOURCE='3'）；FCLEARDATE 是清分操作时间非业务锚
- 拍板结论：过滤器 完成清分 fispayenter='Y' + 今年 fdate 落 2026；指标 SUM(fimamt 分入金额)；维度 归属级次（frechgncode→fbgtlevel→字典110），占比=各级金额/总额；时间锚 fdate/fyear(toDate)
- datus 改法：现行自创映射（000000=中央、后两位推导）与字典110 有分歧点（字典 0=共享/1=中央），退役改走权威字典110；000000 实际归属以前置验证实测为准
- cube 改法：fiscal_allocation 补级次维度（区划→级次映射），占比=各级金额/总额
- 前置验证（2026-10-26 实测）：① frechgncode/区划 fbgtlevel 列名映射——通过（afa_auth_region.fcode 唯一 191/191，fdt 728 行区划码全命中 5 码；fbgtlevel 存 UUID=afa_res_dictitem.id 非字典码）；② 000000 归属——字典110 判中央级，datus 自创口径一致，分歧未触发；③ **施工新发现——过滤字段 fispayenter/fpayenterdate CK 全库未落地**（system.columns 全业务库 *payenter* 0 列，fne_funddivide_transfer/fne_funddivide_new 均无该列；最近候选 fisenter ''690/'0'37/'1'1、freconcilestatus ''690/'0'33/'1'5 均近全空不可替代）——"完成清分"过滤断供，待 ETL 补列
- 施工记录（cube 侧，2026-10-26）：真 join 拍板已落地——fiscal_allocation 主 SQL 4 层→6 层（frecrgncode→afa_auth_region.fcode→fbgtlevel(UUID)→afa_res_dictitem 字典110 取 fname，零静态映射，CK 23.3 每层单 join 合规），新维度 bgt_level（归属级次）进 cube+view+词典「归属级次」词条；回归全绿（count=728、im_amt=16,016,079,467.68 与改前分毫不差，区划分组 686/31/8/2/1 不增行）；全量级次分布 省 686 行 160.16 亿/中央 31 行 4,516.12/市 8 行 1,778.70/县 3 行 495.33；**完成清分过滤未施工**（前置验证③字段断供）——补列前 cube 侧该口径只能出全量，复验比对需注明差异根因
- 查证实证（2026-10-26 直查落地库）：① 前置验证① 完成——落地列名是 `frecrgncode`（主表行 frechgncode 系笔误，codeqa 证据行 FRECRGNCODE 即正确名）；`fbgtlevel` 实为 UUID 外键，须再经 `afa_res_dictitem`（fdictcode='110'）解码出 fcode，比单子所写多一跳；② 前置验证② 完成——000000 区划行 fname='中央'，其级次 UUID 经字典110 解码=fcode'1' 中央级（530000/53→'2'省级、210a…→'3'市级、8da5…→'4'县级，区划表无'0'共享行），datus 自创口径与字典110 对 000000 的归属一致，分歧点解除；③ 前置验证未挂的意外——`fispayenter`/`fpayenterdate` 在落地三表（funddivide_transfer/funddivide_new/paybook_full_high）均不存在，"完成清分"过滤器的落地替代需补拍板（候选：funddivide 有清分记录即视为已清分，或 paybook.is_cleared='1'）；funddivide 侧 frecrgncode 728 行全非空（paybook 宽表侧 553 行空串），级次维度应锚清分侧
- 记忆清理：datus 清"后两位推导级次"类记忆；cube 词典落"归属级次"词条
- 验收：④复验 q20 双侧四级金额占比一致——ETL 补 fispayenter/fpayenterdate 后过滤对齐复验；补列前仅可全量口径比对（cube 侧 bgt_level 维度已就绪）

### q21 今年从缴款到资金缴入国库，各笔缴款的全程耗时按时间区间分档后，各档的笔数分布如何？

- 裁决：待人工→草案（环节耗时/日期差类指标缺失 + 跨链配对维度缺）
- 现状：cube 缺环节耗时/日期差类指标（全程闭环耗时分档）；datus 缺缴库↔缴款跨链逐笔配对维度（被语义模型拒绝）。全程终点"缴入国库"受全局拍板2（fenterstatus='1'+fenterdate）约束
- codeqa 证据：2026-10-26 图谱问答——跨链逐笔配对可行：`une_paybook.FPAYCODE = FNE_TREASURY_TRANSFER.FPAYCODE`（`TreasuryDao.xml` 子查询证实）；起点候选 `FCONFIRMDATE` 缴款确认日（`RptAgenPayment.xml`"缴款起始日期"；FDATE 为缴款书日期、FPAYDATE 属对账单表勿混）；终点 `FENTERDATE` 入库日（`ttm.fenterdate as fintredate`；fbuilddate=报文建立、ftransdate=报文发送勿混）；代码无现成耗时计算与分档逻辑
- 拍板结论：起点=**fdate**（全局拍板1"缴款时间统一 FDATE"覆盖耗时起点，不另立 fconfirmdate；codeqa 备查：fconfirmdate 为缴款确认日，复验若发现耗时被"开票→缴款"拖延段污染，回①重查）；终点=fenterdate 入库日（全局拍板2）；指标 耗时天数=fenterdate−fdate + 笔数 COUNT(DISTINCT fpaycode)；维度 耗时区间分档（代码无现成标准，按全局拍板4 时长序列：<1天/1–10天/10–100天/≥100天）
- datus 改法：补缴库↔缴款跨链配对（fpaycode 关联，此前被语义模型拒绝——dosi 建关联或新增数据集）；补耗时计算+分档维度
- cube 改法：补日期差类指标（fenterdate−fdate）+分档维度；两链跨 cube 关联落法随施工定
- 前置验证：① CH 落地表两链 fpaycode 关联命中率与 fenterdate 列映射（全局拍板3，未验证）；② fdate≤fenterdate 抽查（异常负耗时行数）
- 记忆清理：datus 清"跨链配对不可行"类记忆；cube 词典落"全程耗时"词条
- 验收：④复验 q21 双侧同档位笔数一致

### q22 今年已开具但缴款人一直未缴款的缴款通知书，按未缴时长分档统计，各档有多少笔？

- 裁决：待人工→已审定（"未缴款/欠缴"的判定字段）
- codeqa 证据：2026-10-26 图谱问答（云南源代码 `UPayBook.xml:1428-1431`）；`fisreceived` 是缴款表"到账"标志（`UPayBook.xml:1333`），比未缴款靠后一环
- 拍板结论：过滤器 已开具且未缴款 = 缴款书状态 `fstate='1'`（1未缴款/2作废/3已缴款/4已到账，`fstate!='2'` 保有效）+ 兜底 fne_paybook 按 fpaycode 左连无记录（`fp.fid is null`，防状态未回写脏数据）；指标 未缴笔数 COUNT(DISTINCT fpaycode)（通知书可能因明细拆多行）；维度 未缴时长分档（全局拍板4 时长序列：<1天/1–10天/10–100天/≥100天）；时间锚 ffillDate（未缴时长=开具日期至当前日期天数，缴款记录不存在无缴款日期可减）
- datus 改法：原口径 `is_received='0'` 作废——会把"已缴款未到账"误算进欠缴；按拍板重建口径
- cube 改法：state='1' 方向一致，补 fne_paybook 无记录兜底
- 前置验证：codeqa 结论出自 Oracle 应用库，ClickHouse 落地需列名映射验证后再动手（未验证，依据=codeqa 引用行号）
- 记忆清理：datus 清 is_received='0'=欠缴 记忆；cube 词典落"未缴款"词条
- 验收：④复验 q22 双侧分档笔数一致

### q23 执收单位已经收上来但还没有汇缴上缴的资金，按滞留时长分档，各档金额是多少？

- 裁决：待人工→草案（cube 缺"已收未汇缴/已收未划拨滞留"口径）
- 现状：datus 现行近似=未划拨金额×is_received='1'（q22 拍板后 fisreceived 语义已纠偏为缴款表到账标志，本口径复用前需重验）；滞留起点 trans_date 未回填的局限已自述
- codeqa 证据：2026-10-26 图谱问答——已收=财政端 `fne_paybook.FISRECEIVED='1'`（`PayBookServiceImpl.java:750-765`，与 q18 完成口径同源）；未汇缴=财政端 `fne_income_daybook.FISGENEREC=0` 未生成缴库记录（`IncomeDayBookServiceImpl.java:256-264`）/单位端 `une_cbill.FBATCHNO IS NULL`（`CollectServiceImpl.java:1207-1214`"非税统一票据(未汇缴)"）；FBUSTYPE（1直缴/2汇缴）是业务类型非汇缴状态勿用；滞留金额=累计未汇缴 `fnr_unpaid.FAMT`（报表列 JZQJAMT 直接取，`UPayBook.xml:357-377`）；滞留起点=`FRECEIVEDDATE` 到账日期（`PayBook.java:96`）；全库"滞留"仅专户清分配置命中，无现成分档逻辑
- 拍板结论：过滤器 已收 fisreceived='1' + 未汇缴（fisgenerec=0 未生成缴库记录；单位端 fbatchno IS NULL）；指标 滞留金额 SUM(fnr_unpaid.famt)；维度 滞留时长分档（按全局拍板4 时长序列：<1天/1–10天/10–100天/≥100天）；起算锚 freceiveddate 到账日期（存量池，题面无"今年"限定）
- datus 改法：现行近似口径与本拍板的差异在"未汇缴"判定（未生成缴库记录 vs 未划拨），修改对象主列 cube，datus 侧复验对齐后定是否随改
- cube 改法：补"已收未汇缴"口径+滞留时长分档维度；滞留起算改 freceiveddate 到账日（现 trans_date 未回填局限退役）
- 前置验证：① CH 落地列名映射（fisreceived/fisgenerec/freceiveddate 及 fnr_unpaid 落地表存在性，全局拍板3，未验证）；② fisgenerec 分布实测
- 查证实证（2026-10-26 直查落地库）：① 前置验证① 完成——`fnr_unpaid` 落地表不存在，拍板指标的直接落点落空；fisreceived/freceiveddate 存在，落地于 `fne_income_daybook`（740 行，freceiveddate 2022–2026 全非空，fimamt 合计 1,472,288.25）；② 前置验证② 完成——income_daybook 的 fisgenerec 全 740 行=0 无区分度，"未汇缴=fisgenerec=0" 过滤在该表上恒真（该表本身即未生成缴库记录的日记账池，与拍板池语义自洽）；③ 新增待拍板：指标落点替代（候选=income_daybook 池直 SUM；其 447 个 fpaycode 与 paybook 已收池 100% 重叠）+ 金额列 fimamt（1,472,288.25）vs fownimamt（1,139,899.98）二选一
- 记忆清理：datus 清"已收未汇缴=未划拨"类记忆；cube 词典落"已收未汇缴"词条
- 验收：④复验 q23 双侧分档金额一致

### q24 今年已下达划拨指令但资金尚未划转到账的部分，按滞留时长分档，各档金额有多大？

- 裁决：待人工→已审定（在途滞留池口径 + 字段纠偏 + datus 窗口漂移 bug）
- codeqa 证据：2026-10-26 图谱问答（财政票据V3-云南，clear-transfer 域）——应用库无 `trans_stats`/`ftransamt`：实为 `FSTATS`（0未发/1已发/7失败/9成功回执/14校验不通过，`MsgStatus.java:12-20`）与 `FAMT`（划拨单 `FNE_CAPITAL_TRANSFER.FAMT`，经 `FTRANSNO` 关联带入）；fstats='9'≠到账——回执只写 fstats+fistransfer，到账由独立动作写 fiseenter='1'+fenterdate（`ConvertUnit.java:426-428` vs `EnterTransfer.xml:108-134`）
- 拍板结论：过滤器 在途滞留池 = 指令已发 `fistransfer='1'`（配 `fstats∈{1,9}`）+ 尚未到账 `fiseenter='0'`（兜底 `fenterdate IS NULL`）+ 今年下达 FTRANSDATE 落 2026；指标 主=在途滞留金额 SUM(FAMT)，辅=在途笔数 COUNT(DISTINCT FTRANSNO)，派生=滞留天数（当前日−FTRANSDATE）；维度 滞留时长分档；时间锚 FTRANSDATE(toDate)
- datus 改法：新增在途口径+分档维度（现"未划拨金额"=fistransfer≠'1' 是 q16 互补池，不得混用；缴款侧 is_received/received_date 探索排除——缴款到账≠划转到账）；修 q24 卡窗口漂移 bug（SQL 年度窗口漂至 2023-11-08~2024-11-02，题问 2026）
- cube 改法：`trans_stats='1'` 过滤改按滞留池三条件（0 结果根因之一为 trans_stats 列未同步，q16 拍板已注明不作过滤依据）；trans_date 按月近似分档退役改真分档
- 前置验证（2026-10-26 实测）：① 落地列名映射——CK 物理列=ftransamt/ftransstats/fisenter（源侧 FAMT/FSTATS/fiseenter；CK 无名为 trans_stats 的列，该名系 datus 字段名）；fisenter 分布 ''690/'0'37/'1'1（fistransfer='1' 的 38 行中 37 行='0'、1 行='1'）；ftransstats 728/728 全空（fstats∈{1,9} 配套条件落地不可执行确认）；② FTRANSDATE 落地分布——ftransdate 仅 2/728 行有值（fistransfer='1' 37 行中仅 1 行），分档缺起点锚维持不建
- 施工记录（cube 侧，2026-10-26）：is_enter 改 fisenter 直挂+fenterdate 非空兜底（sql：if(fisenter='1' OR fenterdate!='','1','0')；原 fenterdate 空兜底口径退役），在途池执行口径与 datus 对齐（metrics.json 登记：fistransfer='1'+fisenter='0'，fstats∈{1,9} 不入过滤）；trans_stats 维度补映射注记（datus 字段名 trans_stats ↔ CK 物理列 ftransstats）；CK 在途池基线实测 37 行/27 张划拨单/24,715 元/2026 下达 0 行（按下达日过滤为空属预期）；trans_bill_count/trans_order_date 成员面不变，metrics.json「在途滞留金额」条目已补 cube 对齐注记。施工坑：cube yml 的 description 内 `{...}` 会被 schema 编译器当模板吞掉、误报 `description=null` 编译错（`fstats∈{1,9}` 即触发），yml 描述一律避免花括号（本卡写作"fstats 1/9"）；REST 冒烟全绿（交叉表 37/1/122/568、池 24,715 元/27 单/37 行、回归 728/160.16 亿不变）
- 施工记录（datus 侧，2026-10-26）：落点=transfer_new 数据集（fne_transfer_new 划拨指令生命周期表，129 行）+指标 在途滞留金额/在途滞留笔数+字段 enter_flag/enter_date/transit_days/transit_duration_bucket；存量在途池口径 fistransfer='1' AND fisenter='0'（不带年度窗口——ftransdate 仅 2/129 非空且均 2024、池内仅 1/33 行，「今年下达落 2026」不可判，题面「今年」按 transdate 过滤会清空在途池属数据现实；ftransstats 全 129/129 空串，待拍板遗留随整列未同步一并搁置）；datus 基线=33 行/20,924 元/27 个 ftransno，分档 未知 26 单 20,894 元+≥100天 1 单 30 元。对表差异（④复验「双侧分档金额一致」前必须解决）：cube 基线 37 行/27 单/24,715 元锚在 fne_funddivide_transfer（清分划拨明细，728 行），datus 锚 fne_transfer_new——27 个 ftransno 完全相同，但 funddivide 表多 4 行生命周期冗余致 4 单金额翻倍（1820→3640/1767→3534/103→206/101→202，虚增 3,791 元），须 cube 改锚 transfer_new 或对 4 冗余行去重；另 transfer_new 池内 2 对同额行（100×2、10×2，fcollectid 不同，双表一致）使 raw SUM 20,924 与 (ftransno,ftransamt) 去重 20,814 差 110 元，属「同单同额多批次 vs 生命周期冗余」判定，待拍板
- 记忆清理：datus 清"未划拨金额=在途滞留"类记忆（两池互补不得混用）；cube 词典落"在途滞留"词条
- 验收：④复验 q24 双侧分档金额一致
- 待拍板遗留：失败(7)/校验不通过(14) 是否入池、bank/tips 两通道是否都入池（滞留档位已按全局拍板4 时长序列落定，2026-10-26）

### q27 有没有资金尚未缴入国库、就已经完成对账或财政记账的记录？

- 裁决：建模差异（"对账"与"财政记账"的业务落点）
- codeqa 证据：2026-10-26 图谱问答（云南源代码 `TreasuryTransferTipsMsg.java:52-62`、`TreasuryTransferMsg.java:562-564`）；代码自身判"已入库"即用 fenterstatus='1'（`TreasuryTransfer.xml:231`）
- 拍板结论：两层口径：①对账层=已完成对账（`freconcilestatus='1'`，0未对账/1成功/2失败，同表 FNE_TREASURY_TRANSFER_MSG）且未入库（`fenterstatus≠'1'`，与全局拍板2一致）；②记账层=已写国库收入（`fincomestatus='1'`，记账回写）且未入库。指标 ftransno 去重笔数+单号明细；维度 异常类型（对账/记账）；时间锚 无（异常存在性校验）
- datus 改法：补 2 个维度 `fenterstatus`/`freconcilestatus`（语义层均未建，CK 表有列；income_status 现成）；原 is_cleared（清分环节）落点作废——源代码对账在缴库报文表，与清分无关
- cube 改法：补 1 个维度 `income_status`（fincomestatus 记账判定，fiscal_treasury 未建）+词典词条"未入库先对账"；度量/过滤现成（bill_count/amt + reconcile_status/enter_status，`fiscal_treasury.yml:242-252,45-55`）
- 前置验证：CH 落地表 freconcilestatus/fincomestatus 列映射（未验证）
- 记忆清理：datus 清 is_cleared=对账 记忆；cube 词典落词条
- 验收：④复验 q27 双侧预期空集一致（三态自洽实测，同批 26 单；答案形态=ftransno 去重笔数+单号明细）
