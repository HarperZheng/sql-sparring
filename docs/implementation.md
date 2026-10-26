# sql-sparring 实施设计

> 主体设计见 [问数双智能体互搏设计.md](问数双智能体互搏设计.md)（总体架构、双方调用方式、SOP、记录层 §1.7）。本文档回答"怎么落地"：角色组件化、出题人如何启动、答题人驱动如何独立固化、记忆隔离、里程碑与决策点。
>
> 状态：**设计定稿，未写代码**。动手顺序从 M0 开始（§6）。

## 〇、前置事实（已验证，实施的地基）

| # | 事实 | 验证出处 |
|---|---|---|
| F1 | 双方查询**同一个 ClickHouse** `172.18.166.126:8123/yunnan0508`——数值互证的前提成立 | cube `.env`（CUBEJS_DB_TYPE=clickhouse）与 datus `.datus/config.yml` 对照 |
| F2 | datus 无头链路已通：`datus -p` 25 题 24 成功、0 真实错误，MessagePayload 提取规则经实战校准 | datus 仓 09-datus-票据链路问数实测记录 |
| F3 | cube 无头链路已通：`POST :4100/chat` 30 题三态（answer/ask/nomatch）齐全，sessionId 续会话可拍板 | datus 仓 09-cube-票据链路问数实测记录 |
| F4 | v0 曾全量留痕：25 题 payload 流与逐题提取结果、cube 30 题三态记录（叙事与判定见 datus 仓 09 号文档） | 适配器提取规格 §2.2 的每条规则有实测出处 |
| F5 | 两个语义层不同构：datus=dosi YAML 资金链（`fne_fund_main.yml`，16 指标/7 数据集）；cube=Cube schema 票据链（`/agent/dictionary` 可枚举） | 双方首轮实测 |

## 一、角色组件化

互搏的角色全部落为本仓内的**独立组件**，各自有明确的输入/输出/运行环境。除出题人是新起 agent 外，其余皆是对既有链路的封装（考纲=人工收编的课本+原始资料存档）。

| 角色 | 组件 | 职责 | 输入 → 输出 | 运行环境 | 模型 |
|---|---|---|---|---|---|
| 考纲（出题依据） | `syllabus/`（`bussiness/` 原始资料 + `business.md` 课本） | 编制课本：收编业务知识（剥离数据落地内容）+ 知识点编号 | 业务原始资料 → `business.md` | 人工整理 | 无 |
| 出题人 | `examiner/`（SKILL.md + `bin/examine.py`） | **只读考纲**出题（盲考，不读答题人侧任何产出） | `syllabus/` → `questions.jsonl` | Claude Code headless（Windows） | 可配置（`conf/models.json` examiner 节；缺省本机 claude 现配） |
| 答题人·datus | `adapters/ask_datus/` | 逐题驱动 datus 并提取作答卡 | `questions.jsonl` → `answers/datus/qNN.json` + 原始留痕 | HTTP chat API（POST :8501/api/v1/chat/stream，datus --web 常驻服务）；全题指标优先 D13（每题先走 ask_metrics 节点，无最终答案降级默认节点） | GLM-5.3-Flash（生产现配，不动） |
| 答题人·cube | `adapters/ask_cube/` | 逐题驱动 cube 服务并提取作答卡 | `questions.jsonl` → `answers/cube/qNN.json` + 原始留痕 | HTTP `:4100/chat` | Claude Agent SDK（生产现配，不动） |
| 裁判 | `judge/`（v1 人工在环 → M4 固化服务） | 逐题对出裁决书 + 修正答案 | 双侧作答卡 + 两侧语义层定义切片 → `verdicts/qNN.json` | v1：人 + DeepSeek 辅助；M4：judge 服务（另一接口 DeepSeek） | 可配置（`conf/models.json` judge 节） |
| 编排器 | `bin/round.py` | 按一轮 SOP 顺序调用上述组件；`--retest` 复验模式：清记忆+自动重启两服务+重跑上轮分歧题到轮报 | 轮号 → 本轮全部记录 | Windows Python | 无 LLM，纯流程 |

组件化边界的三条纪律：

1. **组件间只通过 §1.7 四层记录交换数据**（留痕 → 提取 → 裁决 → 回归），不共享内存态、不互相 import。
2. **适配器是独立的**：提取逻辑按 §2.2 提取规格在本仓重写，不依赖 datus/cube 仓的既有脚本。
3. **出题人/裁判与答题人模型不对称**（决策 D9，§五）——评测者与被测者不同源，避免相关盲区。
4. **出题人盲考**：答题人侧产出（作答卡/留痕）不进出题人输入，出题只依据考纲（决策点 D3，§五）。

## 二、出题人启动：四件套

出题人是互搏的起点，也是唯一需要**从零新起**的 agent。启动分四步，每步有独立验收，全部通过才出现第一个机器生成的题库。

**出题依据原则（用户拍板）：根据课本出题，而不是根据答题人的能力出题。** 若按答题人现有能力出题，考卷被答题人现状锚死，不会的永远不问，互搏就永远发现不了"双侧都没建模"的缺口——v0 的 q26-q30 是反证：预期 nomatch 的 3 题实际可答，这些缺口只有从业务出发才问得出来；问到库中无数据的内容撞出 nomatch，正是"双侧共同缺口"的发现方式。因此出题人**只读考纲**（盲考），答题人侧任何产出不进其输入。附带收益：考纲成为双方共同"教学大纲"，将来第三、第四个答题智能体加入，同一张卷子直接复考。

### Step 0 — 业务课本（人工整理，一次性 + 递增）

考纲 = `syllabus/` 目录，自包含两件：**原始资料** `syllabus/bussiness/`（业务方文档原件，原样存档，是出处）与**业务课本** `syllabus/business.md`（出题人唯一读物）。课本从原始资料**收编业务知识**（业务链路 / 名词解释 / 资金主链 / 票据流 / 业务口径提示），做四件事：

1. **剥离数据落地内容**：表定义、字段名、业务概念↔表名对照、数据可得性（空缺）**一概不收编**——库表结构知识由答题人的语义层自行承载，出题人不该知道（决策 D11）；
2. **加知识点编号**（B01…）：题库 `syllabus_ref` 回指于此，可追溯每题考的什么；
3. **补"已裁定口径"空章节**（递增）：每轮裁决产生的拍板口径**回写进课本**——教材随互搏生长，拍板口径的根本沉淀（闭环行只落在 feedback.md，无独立套件文件）；
4. **剥题检查**：课本只含业务知识与事实，**不得含历史题库的原题文本与答案式数值**，否则出题人抄题；数值锚点不进课本。

出题人不读 `bussiness/` 原料目录——原料是出处存档，不是出题输入（决策 D11：出题只依据业务，不依据数据项与数据源）。

### Step 1 — 出题人 SKILL.md（契约）

出题人 agent 的系统契约，核心条款：

- **输入**：只给考纲（= `business.md` 课本，不读 `bussiness/` 原料）。不给答题人侧任何产出（盲考，出题人不知道答题人是谁、有什么能力——双侧天然对称）；不给历史题库原文（防照抄 v0 题）。
- **输出**：`questions.jsonl`，每行一题，字段必须含 `syllabus_ref`（回指考纲知识点编号）。
- **题型问数族五型**（定义见 `examiner/SKILL.md`）：总量趋势、排名对比、分布结构、超期账龄、异常校验（考数据查询，答案形态必须是数值/排名/清单/分布）。配比缺省五型各 6（共 30 题）。概念族 4 型（事实/关联/辨析/边界）与环节归因本期撤销，后续考虑加入（见设计文档 §五）。
- **不标预期**：题库不含 `expect`——"谁该会"由实答揭示，nomatch 本身即登记；预期断言是自我实现的，考不出真东西。
- **质量门槛**：`syllabus_ref` 引用悬空即打回；出题后做**覆盖矩阵**（考纲知识点 × 题目），漏覆盖的知识点打回补题。
- 输出不合法（schema 校验失败 / 引用悬空 / 覆盖漏项）→ 自动打回重出，最多 N 次。

### Step 2 — `bin/examine.py`（CLI 封装）

出题人是 headless 调用的（无交互），封装为命令行：

```
uv run python bin/examine.py --syllabus syllabus/ --out rounds/round-02/questions.jsonl --count 30
```

内部：读考纲 → 拼 prompt → 按 `conf/models.json` 的 examiner 节调 LLM（缺省本机 `claude -p` headless）→ JSONL 逐行校验（`schemas/question.schema.json` + syllabus_ref 悬空检查）→ 覆盖矩阵检查 → 落盘。校验失败自动重试。

### Step 3 — 校验与抽查

- 校验器先对既有题库（rounds/m0/questions-*.jsonl 及其作答卡）跑通——格式回归的锚点。
- `business.md` 剥题检查：全文不含历史题库原题文本与答案式数值。
- 再跑一次真实出题，人工抽检 5 题：syllabus_ref 是否真实、辨析题歧义是否在课本有出处、边界题是否出自课本业务事实。

四件套齐 → round-02 题库诞生，互搏起点闭环。

## 三、答题人适配器固化

### 统一 ask 契约（两侧一致）

- **输入**：`rounds/<轮>/questions.jsonl`（题库外置，适配器零题库）。
- **输出**：`answers/<side>/qNN.json`（统一作答卡）+ `runs/<side>/`（原始留痕：datus=`qNN.payload.jsonl` payload 流 + `qNN.meta.json` 会话/耗时/token；cube=`qNN.raw.json` /chat 响应+日志摘录）。
- **幂等**：`--only qNN` 子集复跑；作答卡覆盖写，原始留痕按时间戳归档不覆盖。
- **开跑前健康检查**：datus 三方一致断言（语义层 YAML=引擎=KB 互相印证）与 cube 词典可达，挂了先修再考。
- **作答卡字段**（`schemas/answer_card.schema.json`，以 rounds/m0 六张实卡为底定稿，M1 拍板 D10 不改写不迁移）：`id / question / status（六值 answer|ask|nomatch|timeout|error|failed）/ metrics_hit（命中指标，机器提取；datus={tool,depth,names}、cube={measures,dimensions} 两形态）/ sql（双侧同放 SQL 文本，cube 为编译后）/ sql_count / values（值行数组，答案唯一载体，D14）/ errors / elapsed_s / arbiter（ask 自动拍板记录）/ raw_path`。**口径卡只在裁决书，作答卡不设**（D10）。**值行增量（D14）**：round-02 起生效（2026-10-26 拍板）——适配器提取步（`adapters/value_extract.py`，模型走 `conf/models.json` extractor 节）直接产值行卡，`answer` 字段自契约删除（散文全文在 runs/ 留痕）；round-02 卡已由 `bin/migrate_cards_values.py` 迁移为 `values`（数字源=裁决书口径卡，确定性键转换）；m0 存档卡文件里的 answer 原样保留（D10 不改写不迁移），校验豁免其缺 values、schema 不再描述该字段——写卡前适配器内联过契约校验，全量核查用 `bin/validate.py`。

### ask_datus 要点

- **chat API 通道（与 ask_cube 同构）**：adapter 直接 `POST http://localhost:8501/api/v1/chat/stream`（datus --web 常驻服务，SSE 流）——agent 配置/语义模型只在服务启动时装一次，每题新 `session_id` 保证题间零污染；message 事件内层 payload 即 MessagePayload，提取器（extractor.py）按 §2.2 规格解析。单题读超时（默认 900s）按超时截断落卡、保留部分输出；网络类失败换新 session 重试（3 次，与 cube 同款）。前置：`datus --web` 在跑（preflight 第 2 项查）。
- 提取规格 = 设计文档 §2.2 表格（SQL←execute_sql toolParams；命中指标←query_metrics/search_metrics/get_metric；**值行←提取步 LLM 结构化 depth-0 散文**（`adapters/value_extract.py`，模型走 `conf/models.json` extractor 节）——散文仅 runs 留痕，只抄数不推算，题目未问的附加指标行不抄（即使出现在查询返回的表格行里；2026-10-26 拍板，round-03 q11/q20 附加行实测驱动），指标名优先取命中指标原词、不贴切标 `未登记:<名>`，D14；真实错误←FuncToolResult `error` 字段，**正文 "Code NNN" 是 KB 文本，勿扫全文**）。
- 已知坑内置：深度>0 子代理的调用也要收（v0 教训）；超时题保留部分输出。
- **验收标准**：提取规格 §2.2 逐条在活跑留痕上有实测例证（rounds/m0/runs/datus/）；作答卡字段与 §三 ask 契约一致；值行验收=round-02 实测（2026-10-26）：30 卡迁移值行、提取步活跑 q15 散文→5 行逐行吻合；q15 工行分项两侧差 17.63 记入明细供回改①（成员名两侧表述不同，别名归一随指标登记表沉淀）；引擎判定按 D14 两级判定改写后复跑为准（推演：一致=q12，1/15，待复核 0——未验证）。

### ask_cube 要点

- `POST http://localhost:4100/chat {question, sessionId}`，三态分流：`answer`（提取 query JSON/编译 SQL/数值）/ `ask`（缺口径）/ `nomatch`（能力外）。
- **sessionId 策略**：每题新会话（题间零污染）；`ask` 态自动拍板——适配器按预设口径政策（缺省口径取自考纲"已裁定口径"节或人工预拍）构造追问再 POST 同 sessionId，拍板动作记入作答卡 `arbiter` 字段（裁决时"自动拍板"与"人拍板"区分对待）。
- **验收标准**：新题活跑可调用、能答数（≥2 题，至少 1 题数值答案）。

### 代码归属：永久在本仓（决策点 D8，用户拍板）

两适配器**永久固化在本仓 `adapters/`，不回迁** datus/cube 仓库——统一契约始终只有一份实现、一个事实源，杜绝双仓同步与漂移；互搏是适配器的唯一用户。

## 四、裁判与记忆隔离

### 裁判实施：先人工在环，后固化

- **v1（round-02）人工在环**：把 v0 的 10 号对账文档逐题结构化为 `verdicts/*.json` 作为**校准集**——裁决书格式、口径卡写法、"只陈述客观差异不预判对错"的文风，先在人手里定型。
- 裁决四态：`互证通过`（口径同+值同）/ `建模差异`（口径不同→差距单）/ `执行事故`（口径同+值不同→bug 单）/ `待人工`。
- **裁判输入=两侧作答卡**：四态判定只靠两卡（sql 文本 + metrics_hit + 值行已足够，SQL 里去重键/时间轴一眼可见；散文不落卡，D14）；仅 nomatch 归因时现查语义层相关条目（datus=YAML、cube=词典）。
- **M4 固化**为 judge 服务（另一接口 DeepSeek，接口与 key 走 `conf/models.json` judge 节），以 round-02/03 的人工裁决为回归基准。
- **共同缺口（进回改单主表）**：同一题两侧均 nomatch/failed → 判双侧共同缺口，修改对象记双侧，进回改单主表（被动统计，只覆盖被问到的题）；轮报四指标：一致率（裁决口径：互证通过数 ÷ 题数，2026-10-26 拍板改版）/ 分歧分布 / 差距数 / 闭环率。

### 值行一致率引擎：两级判定（D14，2026-10-26 拍板）

轮报一致率由 `schemas/valuecmp.py` 纯代码计算，每题三步：

| 步 | 做什么 | 出口 |
|---|---|---|
| ① 数列快筛 | 每侧取全部值行数字：金额换算成元（万元/亿元）、剔导出量（引擎侧再剔一次，如 q14「期内缴款合计」）、null 不进列 → 排序、**不去重** | 两列数不等 → 判「不一致」，终审，不再看名字 |
| ② 键比对 | 只对过了①的题：按（指标，维度）同名行逐行比数值 | 全部行同名同值 → 判「一致」；同名行缺行/值异 → 判「不一致」 |
| ③ 待复核 | ②中键名对不上（数列相等但名字对不齐——错位嫌疑或异名同义） | 标「待复核」：AI 提议别名→人审定→指标登记表→重算翻案；审定为错位则改判不一致 |

- **机械一致率 = ②判「一致」的题数 ÷ 轮题库题数**（剔除题已物理删除）；待复核不计分子，翻案后重算计入。轮报四指标之一致率自 2026-10-26 二次拍板起改用**裁决口径：互证通过数 ÷ 题数**（互证通过即一致），机械一致率退居轮报诊断参考行与 valuecmp CLI——两层并存：判定看裁决，机械层供查证。
- 依据：键比对一致 ⟹ 数列必然相等，逆否即数列不等 ⟹ 不一致恒真——①判「不一致」零误判；数列相等的题不允许跳过②直接判一致（堵住成员贴反被数列规则误判一致的盲区）。
- 细则：null=null 算同名同值；一侧有 null 行另一侧没有 → 缺行判不一致；双侧都无数列 → 判不一致；换算只对金额，笔/张/% 等原样比。
- **展示与判定分层**：轮报分歧明细「值行比对」列与引擎 `join_rows` 走**明细口径**（共有键计数：值同/值异/不一致 + 单侧行清单，含导出量行），只供回改①查证哪个指标/维度/筛选错，不参与题级判定；题级结论只认两级判定。别名登记表 `conf/metrics.json` 只服务③的翻案重算（AI 提议工具随 M4 裁判固化落地，此前待复核由人审登记）。
- round-02 推演（2026-10-26，按现卡推演，引擎改写后复跑验证）：①出局 14 题、两关全过 1 题（q12 → 一致，1/15=6.7%）、待复核 0。

### 回改五步：轮报即系统段终点，不自动回改

**系统边界止于轮报（决策点 D6，用户拍板）**：round.py 出轮报后本轮系统段结束；回改单不是系统产物——回改①由人看过轮报分歧明细后调起智能体，codeqa 逐题查证后由智能体创建 feedback.md；审定、施工、复验、闭环按回改五步走（不叫回灌）。每个语义层 diff 都有人背书——语义层是生产资产（改动牵动 P0/P1 基准与已发布查询），agent 自动改等于绕过工程评审；口径取舍是业务决策，系统只能并列双方证据，不能代拍。

回改单 = `rounds/<轮>/feedback.md` 单文件，三部分：文件头（回改契约：五步+状态机+冲突规则+全局拍板）+ 主表（每行 id/问题/修改对象/codeqa拍板结论/状态）+ 回改卡（每题一节：证据/双侧改法/前置验证/记忆清理/验收）。由回改①的智能体创建（未查完的行登记状态=待查证；执行契约=`feedback/SKILL.md`），内容按回改五步推进：

| 步 | 谁 | 做什么 | 状态流转 | 产出物 |
|---|---|---|---|---|
| ① 查证起草 | 智能体（人调起） | 读轮报分歧明细，用 codeqa 逐题查真实字段解法（过滤器+指标+维度+时间锚，统一以 CK 宽表字段落单），并向 codeqa ETL 抽取代码仓（「财政V3抽取-全国通用版」）逐字段核宽表存在性（三态记前置验证），创建回改单 feedback.md | 待查证→草案 | 回改单（新建）：各行拍板结论+回改卡 |
| ② 审定 | 人 | 逐行审定拍板结论与双侧改法 | 草案→已审定 | — |
| ③ 施工 | 人 | 按回改卡改双侧语义层（datus dosi YAML / cube schema+词典；cube 侧"记忆清理"=拍板口径落词典，属施工） | 已审定→已施工 | 语义层 diff |
| ④ 复验 | 系统 | `uv run python bin/round.py --round <新轮> --retest <上轮>` 一条命令自动：**清 datus chat memory（全量清空，不可逆、不做备份，用户拍板 2026-10-26）** → **datus KB 重投影**（命令与根因见下方注记；③手工改 YAML 后 KB 索引静默过期，不重投影则复验作答仍拿旧元数据）→ **自动重启两服务**（datus：WSL 停旧进程拉起 `datus --web`，轮询 :8501 就绪；cube：`docker compose restart cube` 强制重载 schema + agent-svc 探 :4100、缺则 `D:\develop\cube\start.cmd` 补启；任一未就绪停机退出码≠0）→ 复验集=上轮 report 复验集 ∩ feedback 非剔除行，**原题原 ID 复制**进新轮（不重新出题，盲考不变）→ 双侧作答+提取作答卡 → 裁决关口（AI 初步裁决+人确认，缺单停机）→ 轮报（闭环率=复验集互证通过数/复验集总数） | 已施工→（挂：回③；口径错：回①） | 新轮完整记录（questions/answers/verdicts/report） |
| ⑤ 闭环 | 人 | 复验通过且人工确认后，feedback.md 行状态改"闭环"（**无独立套件文件——feedback.md 即闭环账本**） | 已施工→闭环 | feedback.md 状态列 |

- 状态机：待查证→草案→已审定→已施工→闭环；终态另有剔除（本轮不做的题——如题型撤销类，不进五步与闭环统计）。
- 冲突规则：回改单与裁决书冲突以回改单为准（回改单产生于 codeqa 查证之后）；与课本「已裁定口径」冲突以课本为准（课本是下一轮出题依据）；全局拍板写在文件头，逐行拍板不得与之相悖。
- 记忆清理：回改卡每条建模差异附**记忆清理条目**（受影响 chat memory 的定位，cube 侧=拍板口径落词典属③施工）；datus 侧清理由④复验开跑**代码自动执行**——全量清空 chat memory，**不可逆、不做备份**（用户拍板 2026-10-26；datus 实例为互搏专用，全量清最彻底）；不清则旧口径复活（v0 已验证的坑）。
- **KB 重投影（datus 侧，③→④ 之间，④开跑自动执行）**：datus 语义 KB（`.datus/data/{project}/datus_db/` 的 LanceDB：metrics.lance/semantic_dataset.lance 等）是 `subject/semantic_models/{datasource}/*.yml` 的投影，但**查询路径不校验过期**——dosi 引擎（get_metric/query_metrics）直读 YAML 永远新鲜，agent 聊天选指标/维度走 KB 向量检索，内容=上次显式同步时刻；③手工/IDE 改 YAML 后 KB 静默过期，agent 拿旧指标元数据作答（2026-10-26 实证：2026-10-20 的旧索引让 round-02 施工后的查询继续以 fill_date 为时间轴、绕过语义路径直写 SQL）。重投影命令（无 LLM、不联网、幂等，embedding 走本地 fastembed）：
  `wsl -e bash -ic "conda activate datus && cd /mnt/d/develop/datus/Datus-agent && uv run datus bootstrap-kb --datasource yunnan0508 --components semantic_model --kb_update_strategy sync-yaml"`
  编入 --retest 时置于清记忆之后、拉起 datus 服务之前；web UI 内保存 YAML 会自动同步（保存路径内置 sync_osi_to_db），不经过 UI 的施工必须显式重投影。
- 闭环率是**跨轮指标**（上轮分歧题在本轮复验集的通过率）——它测的是"人拿着回改单修完语义层后问题是否真消失"，中间隔着完整的工程过程，比系统自改自测可信。

### 记忆隔离（变量控制）

依据 v0 实测的**记忆粘性**（agent 援引"沿用 q10 拍板口径"，旧口径会跨会话复现）：

- 每轮开跑前快照 `.datus/memory/chat/`；同一侧轮内复跑前**恢复快照**——保证测的是语义层当前状态，不是上一轮的聊天记忆（决策点 D7）。
- 回改复验（回改④）开跑时**全量清**（不是恢复旧快照——语义层已改，快照里的旧口径记忆与新时代不匹配；也不按回改卡定向清——散文条目机器不可执行，datus 实例为互搏专用故全量清空）：清理由 `--retest` **代码自动执行**，不可逆、不做备份（用户拍板 2026-10-26）；不清则旧口径复活（v0 已验证的坑）。
- **闭环验收判据**：清记忆 → 复验重跑 → 仍通过，才算口径真修进了语义层；清后重跑挂 = 口径还赖在记忆里，回改未完成。
- **教训升格**：chat memory 里反复出现的有益教训（如"该库需子查询绕过 Code 115"）应升格进语义层 ai_context / KB 文档后从记忆清除——知识落在能被测试的层里。
- cube 侧对应纪律：无持久会话记忆，sessionId 不跨轮复用；拍板口径落词典（词典即其"语义层记忆"）。

## 五、决策点台账

### 已议定（D1–D11）

| # | 决策 | 内容 | 落点 |
|---|---|---|---|
| D1 | 记录四层分离 | 原始留痕/机器提取/裁决/回归基准各层单一用途，禁止混写 | 设计文档 §1.7 |
| D2 | 命中指标两级记录 | 工具级 `metrics_hit`（过程证据，机器提取）+ 口径级 `cards`（裁决证据，裁判归一化） | 作答卡 schema |
| D3 | 出题以考纲为源（用户拍板） | **根据课本出题，而非根据答题人能力出题**；答题人侧产出不进出题人输入（盲考） | §二 Step 0 |
| D4 | 对账先口径后数值 | 口径不同=建模差异；口径同值同=互证；口径同值异=执行事故 | 裁决四态 |
| D5 | 回归基准三层 | T1 文档基准（07 号）→ T2 双侧互证 → T3 修正答案+人工确认；闭环沉淀=feedback.md 行状态（无独立套件文件） | §六 M4 |
| D6 | 不自动回改（用户拍板） | round.py 止于**轮报**（report.md）；回改单由回改①的智能体创建（人调起）；审定/施工/复验/闭环按回改五步走 | §四 |
| D7 | 记忆隔离与清理细化 | 轮内只快照/恢复 `.datus/memory/chat/`；回改**全量清**（④复验开跑代码执行，不可逆不做备份）；**清后重跑仍通过=闭环验收**；有益教训升格进语义层 | §四 |
| D8 | 适配器永久留本仓（用户拍板） | `ask_datus`/`ask_cube` 固化在 sql-sparring `adapters/`，**不回迁**各自仓库；统一契约单一事实源 | §三 |
| D9 | 模型不对称与可换配置（用户拍板 2026-10-22） | **答题人**生产现配不动（datus=GLM-5.3-Flash、cube=Claude Agent SDK 现配）；**出题人**经本机 claude 无头调起（现配即 GLM 系；出题受考纲约束，与答题人同源风险低）；**裁判**与出题人/答题人不同接口不同源——用另一接口的 DeepSeek 模型（v1=人 + DeepSeek 辅助，M4 固化）。**裁判与出题人的模型/接口/key 一律走配置文件 `conf/models.json`**：换模型、换接口只改配置不改代码；key 不入库，配置文件只存环境变量名（本仓已公开于 GitHub，真实 key 放本机环境变量） | §一 角色表、§二 Step 2、§四、§七、里程碑 M1/M2/M4 |
| D10 | M1 契约三拍板（用户 2026-10-22） | ① 作答卡 `status` **六值超集**：answer/ask/nomatch/timeout/error/failed（failed=适配器链路失败，error=智能体答错/中断，timeout=超时截断，两侧共用）；② **口径卡只在裁决书** `cards`，作答卡保持纯机器提取零 LLM；③ 作答卡**以 M0 实卡为底定稿**（`sql`/`sql_count` 双侧同放 SQL），不做 queries 改造、不迁移 M0 证据卡 | §三、设计文档 §1.7、schemas/answer_card.schema.json |
| D11 | 出题依据=纯业务（用户 2026-10-22） | 考纲只有业务课本一件，**不读数据项与数据源**（无库表画像、无数据源文档）；库表结构知识由答题人的语义层自行承载；原始资料存档进考纲目录 `syllabus/bussiness/`（出处，非出题输入）；撞库答不出=nomatch 共同缺口，属发现非缺陷。**课本本身同样不含表定义、字段名、数据可得性**（v2 剥离，用户 2026-10-22 当日追加） | §二 Step 0 |
| D12 | 裁判只判一致与归因（用户 2026-10-22） | 裁判**不产数值真伪结论**：同口径同值=互证通过（同库互证即正确性证据）；口径不同=建模差异，谁补建模记入 `issues[]`（side 支持 both；type 四分：补指标/补维度/改口径/修bug）；口径同值异=执行事故，`type: 修bug`，属排错不属建模。非互证通过的题**默认进下轮复验集**，前提=对应侧补完语义层才发起复验（人工时机保证） | 设计 §1.7③；复验规则 §四 |
| D13 | 全题指标优先（用户拍板 2026-10-23） | datus 接题后**一律先走 `ask_metrics` 节点**（请求体 `subagent_id` 路由；query_metrics 交 dosi 引擎按语义模型编译 SQL，**metrics_hit 由此有值**），无最终答案（未建模/报错/超时）降级默认 chat 节点再答（表达力兜底）。**路由不读题型**——题型是出题人侧考纲信息，答题人不读题型字段（盲考纪律）；两级尝试全留痕（meta.routes）。**SQL 证据走执行记录取证（v4）**：datus 侧 `dosi_sql_executed` 日志行 + `adapters/ask_datus/evidence.py` 按题时间窗提取，LLM 无感知 | 设计 §2.1；`adapters/ask_datus/driver.py`；`adapters/ask_datus/evidence.py`（v4 取证） |
| D14 | 答案唯一载体=值行（用户拍板 2026-10-26） | 作答卡去散文：`values` 值行数组为答案唯一载体（指标×维度成员→数+单位；metric 取指标登记表 `conf/metrics.json`，无则标 `未登记:<名>`；合计/占比/排名=导出量不登记、代码导出比对；散文全文留 runs/）。轮报一致率=**两级判定**（`schemas/valuecmp.py`，同日拍板：①数列快筛——金额换算成元、剔导出量、null 不进列，排序不去重，数列不等即判不一致（终审）；②键比对——过①的题按（指标，维度）同名行逐行比，全部同名同值才一致，缺行/值异判不一致；③键名对不上标待复核，AI 提议别名→人审定→登记表→重算翻案。详见 §四「值行一致率引擎」）。已落地：round-02 卡迁移 + 提取步直产 + 轮报接线；引擎两级判定改写与复跑为紧接着的实施项 | 设计 §1.4/§1.7②/§2.2；作答卡 schema；`bin/migrate_cards_values.py`；`schemas/valuecmp.py`、§四 值行一致率引擎 |

## 六、里程碑（M0–M4，答题链路先行）

| 里程碑 | 内容 | 验收 | 产出 |
|---|---|---|---|
| **M0 答题链路打通** | Windows 侧 uv 环境初始化（pyproject.toml + uv.lock 入 git，依赖仅 httpx/jsonschema/pydantic）+ `ask_datus`（wsl_runner 桥接 + §2.2 提取器）+ `ask_cube`（:4100 三态 + 拍板政策）+ **最小作答卡结构**（id / question / status / metrics_hit / sql / sql_count / answer / errors / elapsed_s / arbiter / raw_path——M1 升格为正式 schema 的底坯） | **对接活体验证**：datus ≥2 道新题活跑（`datus -p`）status=answer 且带数值；cube ≥2 道新题活跑（`:4100/chat`）至少 1 题数值答案 | `adapters/` 双适配器 + `rounds/m0/` 证据 + `pyproject.toml` |
| **M1 契约定稿** | 三个 JSON Schema（question / answer_card / verdict）+ questions.jsonl 格式定稿；answer_card 以 M0 实卡为底定稿（status 六值、arbiter 全字段；口径卡只在裁决书，D10），适配器写卡前内联 schema 校验 + `bin/validate.py` 全量校验器；`conf/models.json` 骨架落盘（examiner/judge 两节，key 只存环境变量名）；M4-值行增量（D14）见决策点台账 | 适配器全量输出过 schema 校验 | `schemas/` + `bin/validate.py` + `conf/models.json` |
| **M2 出题人启动** | 业务课本（`business.md` 收编业务知识+剥离数据落地+知识点编号，D11）+ SKILL.md + `bin/examine.py`（LLM 调用接入 `conf/models.json` examiner 节，缺省本机 claude 现配）+ `bin/preflight.py` 开跑前健康检查（单次执行） | business.md 剥题检查通过；题库覆盖矩阵无漏项；冒烟试答两侧出卡；首个机器题库诞生 | `syllabus/` + `examiner/` + round-02 题库 |
| **M3 首个自动轮** | `bin/round.py` 跑 round-02 全流程（出题→双侧作答→提取）；裁决人工在环 | 一轮完整记录落盘 + 轮报四指标（一致率/分歧分布/差距数/闭环率） | `rounds/round-02/` + report |
| **M4 复验轮与固化** | 回改五步跑通：①智能体起草②人审定③按回改卡修双侧语义层 → ④`--retest` 复验一条命令自动（清记忆[全量不可逆无备份]→datus KB 重投影[见 §四注记]→重启两服务→原题重跑→裁决→轮报，复验集=上轮分歧题∩非剔除行）→ ⑤人工置 feedback.md 行状态=闭环；回改单格式定稿；裁判固化 judge 服务（模型/接口接 `conf/models.json` judge 节） | 回改五步至少跑通一次且闭环率>0；judge 以人工裁决为回归基准 | 复验轮记录 + 回改单模板 |

顺序依赖：M0（链路可行性）→ M1（契约定稿）→ M2 → M3 → M4。**M0 先行的理由**：两条答题链路是全系统最大的外部依赖风险（WSL 桥、:4100 活服务、提取规格），先证明"可调用、能答数"，再冻结契约——契约没有跳过，只是延后到有真实输出为底时才定稿。M0 只依赖 §2.2 提取规格与最小作答卡结构，不依赖完整 schema；datus 侧与 cube 侧可并行，datus 侧提取器可对 v0 留痕离线开发调试。

## 七、运行入口与目录树（M4 完成态）

### 运行入口

主入口 + 三个组件入口，人只碰 `bin/round.py`：

| 层 | 入口 | 职责 |
|---|---|---|
| 主入口 | `bin/round.py` | 一轮全流程（自动执行 SOP ①–⑤，到轮报为止）；`--retest` 复验模式：清记忆+自动重启两服务+重跑上轮分歧题到轮报（回改④） |
| 组件入口 | `bin/examine.py` | 只出题（SOP 第 1 步），round.py 内部也调它 |
| 组件入口 | `adapters/`（两个） | 答题驱动器，round.py 逐侧调用；可单跑（`--only` 子集复跑） |
| 组件入口 | `judge/` | 裁决：v1 人工在环（人读作答卡写 verdicts），M4 固化为 headless 服务 |
| 被封装 | examiner/judge 的 LLM 调用 | 由上述 Python 入口内部发起（examiner 缺省本机 `claude -p`，judge 为另一接口 DeepSeek），模型/接口/key 一律读 `conf/models.json`，人不直接调 |

典型命令（M2/M3 落地后；**Windows 侧 uv 环境执行**，ask_datus 打 :8501 常驻服务、ask_cube 打 :4100）：

```bash
# 跑一整轮：出题→双侧作答→提取→裁决在环→轮报（SOP ①–⑤ 自动，回改五步留给人+智能体）
uv run python bin/round.py --round round-02

# 复验轮（回改④，人工发起）：一条命令自动——清记忆（全量，不可逆无备份）
#   +重启两服务+上轮分歧题原题进复验集重跑+裁决+轮报；datus 启动命令首跑前实测校准进代码
uv run python bin/round.py --round round-03 --retest round-02

# 只出题（考纲编译好之后）
uv run python bin/examine.py --syllabus syllabus/ --out rounds/round-02/questions.jsonl --count 30

# 单侧子集复跑（回归失败题时）
uv run python -m adapters.ask_datus --round round-02 --only q09

# 闭环（回改⑤，人工）：复验通过且确认后，把 feedback.md 对应行状态改"闭环"
#   （无独立命令、无套件文件——feedback.md 即闭环账本）
```

与 SOP 的对应：round.py 自动跑 ①出题→②双侧作答→③提取→④裁决（人工在环确认）→⑤轮报，**到轮报即停**（D6）；回改五步从轮报接手——①查证起草（人看过分歧明细后调起智能体，codeqa 逐题，创建 feedback.md）→②审定（人）→③施工（人，改双侧语义层；cube 口径落词典）→④复验（`--retest` 一条命令自动：清 datus chat memory[全量，不可逆无备份]→重启两服务→原题重跑→裁决在环→轮报）→⑤闭环（人工置 feedback.md 行状态=闭环）。

### 目录树（M4 完成态）

```
D:\develop\sql-sparring\
  README.md  docs\                     索引 + 总体设计 + 本实施设计
  schemas\  bin\validate.py            M1：三类 JSON Schema + 全量校验器（契约定稿，answer_card 以 M0 实卡为底；值行增量 D14）
  conf\models.json                     M1：出题人/裁判模型配置骨架（key 只存环境变量名，D9）
  adapters\{ask_datus, ask_cube}\      M0：双答题驱动器（永久在本仓，D8）
  syllabus\{bussiness\,business.md}    M2：考纲=原始资料+业务课本（出题唯一依据，D11）
  examiner\                            M2：出题人（SKILL.md + bin/examine.py，只读考纲盲考）
  judge\  bin\round.py                 M3/M4：裁判（人工在环→固化服务）+ 一轮编排器（--retest 复验）
  rounds\round-NN\                     每轮记录（§1.7 四层：runs 留痕→answers 提取→verdicts 裁决→feedback.md 回改单）
    feedback.md                        回改①产物（人看过轮报后由智能体创建）：主表+回改卡；⑤闭环行=其状态列（无套件文件）
```

## 八、v0 与业务文档的取用

- 裁决校准：10 号对账总表（datus 仓）→ M3 裁决校准集。
- 业务课本：原始资料 `syllabus/bussiness/`（业务方文档）**收编业务知识 + 剥离数据落地内容（表定义/字段名/数据可得性不收编）+ 知识点编号**（剥题纪律照旧：不留原题文本与答案式数值）→ `syllabus/business.md`（决策 D11）。
- 首轮叙事文档（07/09/09/10）留在 datus 仓 `development_process_record/non_tax/` 作历史记录，机器层自 round-02 起全部落本仓。
