# sql-sparring — 问数双智能体互搏

两个 NL 问数智能体（datus、cube）就同一批自然语言问题独立作答、互检、由裁判定谳；分歧经**回改五步**（查证起草→审定→施工→复验→闭环）落到两侧语义层；互搏的副产品是一套不断生长的问数回归套件。

- **datus 侧**：dosi 引擎语义层（`fne_fund_main.yml`，资金链，16 指标/7 数据集），无头驱动 chat API（`POST :8501/api/v1/chat/stream`，`datus --web` 常驻服务），全题先走 `ask_metrics` 节点（query_metrics 通道，D13），模型 GLM-5.3-Flash。
- **cube 侧**：Cube schema 语义层（票据链），无头驱动 `POST :4100/chat`（agent-svc，三态 answer/ask/nomatch）。
- **同库互证的前提已验证**：双方查询同一 ClickHouse `172.18.166.126:8123/yunnan0508`。
- 核心机制：**先比口径、后比数值**——口径不同=建模差异（回改补建模），口径同值同=互证通过，口径同值异=执行事故（回改修 bug）。
- **出题以考纲为源（课本），不以答题人能力为源**：考纲=业务原始资料+业务课本（`syllabus/` 目录自包含），不读数据项与数据源；出题人盲考，不读答题人侧任何产出；分歧经裁决与回改单由人审定、施工落语义层。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/问数双智能体互搏设计.md](docs/问数双智能体互搏设计.md) | **总体设计**：架构、两个智能体的无头调用方式、一轮 SOP、记录层四层格式（§1.7） |
| [docs/implementation.md](docs/implementation.md) | **实施设计**：角色组件化、考纲目录与出题人四件套（盲考）、答题人适配器固化与验收、裁判与记忆隔离、决策点台账、里程碑 M0–M4 |

## 运行入口

| 层 | 文件 | 环节 | 职责 |
|---|---|---|---|
| 主入口 | `bin/round.py` | ①–⑤ 串联 | 一轮全流程：①出题→②双侧作答→③提取→④裁决关口→⑤轮报，到轮报即停；`suite-add` 子命令做回改⑤闭环入库；人日常只碰这一个 |
| 组件入口 | `bin/examine.py` | ① 出题 | 只出题（读考纲→出题→schema/覆盖矩阵校验→落盘题库）；round.py 内部也调它 |
| 组件入口 | `adapters/ask_datus` | ②③ datus 侧 | 逐题驱动 datus（:8501 chat API，全题指标优先 D13）+ 提取出作答卡 + SQL 执行记录取证；可单跑 `--only qNN` |
| 组件入口 | `adapters/ask_cube` | ②③ cube 侧 | 逐题驱动 cube（:4100/chat，三态分流 + ask 自动拍板）+ 提取出作答卡；可单跑 `--only qNN` |
| 组件入口 | `judge/` | ④ 裁决 | 逐题出裁决书；v1=人工在环（目录 M4 才建），M4 固化为 headless 服务 |
| 辅助工具 | `bin/preflight.py` | 环节外·开跑前 | 健康检查：双侧服务可达、语义层文件可解析；单次执行，不进轮循环、不留档 |
| 辅助工具 | `bin/validate.py` | 环节外·质检 | 全量契约校验：题库/作答卡/裁决书逐份对 schema，不过即逐条报错退出 |

### 产出物对照

| 层 | 文件 | 产出物 | 产出物说明 |
|---|---|---|---|
| 主入口 | `bin/round.py` | `rounds/<轮>/report.md` | 轮报：双侧状态、四指标、分歧明细、下轮复验集，一页看懂本轮 |
| 回改①（人调起智能体） | | `rounds/<轮>/feedback.md` | 回改单：文件头（契约+状态机+冲突规则+全局拍板）+主表（id/问题/修改对象/codeqa拍板结论/状态）+回改卡（证据/双侧改法/前置验证/记忆清理/验收）；人看过轮报后由智能体创建，非 round.py 产物 |
| 组件入口 | `bin/examine.py` | `rounds/<轮>/questions.jsonl` | 题库，每行一题：`id`/`question`/`syllabus_ref`（回指课本知识点），不含预期答案字段（盲考） |
| 组件入口 | `adapters/ask_datus` | `rounds/<轮>/answers/datus/qNN.json`（×30） | datus 作答卡：status/metrics_hit/sql/sql_count/answer/errors/elapsed_s/arbiter/raw_path 等机器提取字段 |
| | | `rounds/<轮>/runs/datus/qNN.payload.jsonl` | 该题 datus agent 循环的原始报文流，一字不改存档，一级证据 |
| | | `rounds/<轮>/runs/datus/qNN.meta.json` | 该题运行元数据：会话 id、耗时、token、路由记录（meta.routes 两级尝试） |
| 组件入口 | `adapters/ask_cube` | `rounds/<轮>/answers/cube/qNN.json`（×30） | cube 作答卡，与 datus 侧同构 11 字段 |
| | | `rounds/<轮>/runs/cube/qNN.raw.json` | 该题 `:4100/chat` 原始响应留痕（含日志摘录） |
| 组件入口 | `judge/`（v1=人工在环） | `rounds/<轮>/verdicts/qNN.json`（×30） | 裁决书：四态结论 + `cards` 双侧口径卡对照 + `verdict_detail` 问题单（side/type/target/suggest） |
| 辅助工具 | `bin/preflight.py` | 无 | 只在终端打印健康检查结论，明确不留档 |
| 辅助工具 | `bin/validate.py` | 无 | 终端逐条报错 + 退出码，不留档 |

说明：×30 = 每题一份（q01…q30）；产出路径均在 `rounds/<轮>/` 下，四层对应 runs（留痕）→ answers（提取）→ verdicts（裁决）→ feedback.md（回改单）。

## v0 证据（首轮人工实测，位于 datus 仓库 `Datus-agent/development_process_record/non_tax/`）

- 07-fne_fund_main自然语言问数能回答的问题（人工盘点与 T1 基准）
- 09-datus-票据链路问数实测记录（25 题 24 成功）
- 09-cube-票据链路问数实测记录（30 题三态齐全）
- 10-票据链路问数对账（datus-vs-cube）（逐题对账，互搏机制的原型输出）

## 状态

**M0 已完成（2026-10-22）**：双适配器落地（`adapters/ask_datus` WSL 桥 + `adapters/ask_cube` :4100 三态）；对接活体验证通过——datus 3 题、cube 3 题新题真打均出数值答案；证据见 `rounds/m0/`。
**M1 已完成（2026-10-22）**：契约定稿——三份 JSON Schema（题库/作答卡/裁决书）+ 校验器 `bin/validate.py` + `conf/models.json` 模型配置骨架（D9/D10）；M0 全量证据过校验，适配器写卡前内联校验。
**M2 已完成（2026-10-22）**：考纲自包含（`syllabus/bussiness/` 原始资料 + `business.md` 课本 B01–B21，只含业务知识——表定义/字段名/数据可得性已剥离，D11）+ 出题人契约 `examiner/SKILL.md`（题型问数族 5 型；概念族与环节归因已撤销，见设计文档 §五）+ 出题驱动 `bin/examine.py` + 健康检查 `bin/preflight.py`（单次执行）。机器题库：round-02 共 30 题过契约校验（21 知识点全覆盖、零表名泄漏）。
**M3 进行中（2026-10-23）**：轮驱动器 `bin/round.py`（出题→双侧作答→卡校验→裁决关口→轮报，D6 到轮报即停）+ datus 适配器 chat API 化（与 cube 同构）+ round-02 全量双侧作答。

实施路线 M0（答题链路打通）→ M1（契约定稿）→ M2（出题人四件套）→ M3（首个自动轮+人工裁决）→ M4（复验闭环+回归套件+裁判固化），见实施设计 §六。

已议定决策 D1–D12（含不自动回改、记忆隔离细化、适配器永久留本仓、模型不对称与可换配置——出题人/裁判的模型、接口、key 走 `conf/models.json`、出题依据=纯业务、裁判只判一致与归因）；待确认清零，见实施设计 §五。
