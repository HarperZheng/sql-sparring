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
| F4 | v0 留痕完整可重放：datus `tmp/qa_run/*.jsonl`（25 份原始 payload 流）、qa_results.json；cube 日志与对账文档 | 可直接作适配器固化的验收 fixture |
| F5 | 两个语义层不同构：datus=dosi YAML 资金链（`fne_fund_main.yml`，16 指标/7 数据集）；cube=Cube schema 票据链（`/agent/dictionary` 可枚举） | 双方首轮实测 |

## 一、角色组件化

互搏的角色全部落为本仓内的**独立组件**，各自有明确的输入/输出/运行环境。除出题人是新起 agent 外，其余皆是对既有链路的封装（考纲编译=纯解析脚本+人工课本）。

| 角色 | 组件 | 职责 | 输入 → 输出 | 运行环境 | 模型 |
|---|---|---|---|---|---|
| 考纲（出题依据） | `syllabus/`（`gen_db_profile.py` + `business.md`） | 编制课本：原始库数据画像 + 业务知识 | ClickHouse 原始库 + 业务文档 → `db_profile.json` + `business.md` | Windows Python（纯解析）+ 人工整理 | 无 |
| 出题人 | `examiner/`（SKILL.md + `bin/examine.py`） | **只读考纲**出题（盲考，不读能力卡） | `syllabus/` → `questions.jsonl` | Claude Code headless（Windows） | Claude |
| 答题人·datus | `adapters/ask_datus/` | 逐题驱动 datus 并提取作答卡 | `questions.jsonl` → `answers/datus/qNN.json` + 原始留痕 | Windows + WSL 桥接（wsl_runner 文件交接） | GLM-5.3-Flash（生产现配，不动） |
| 答题人·cube | `adapters/ask_cube/` | 逐题驱动 cube 服务并提取作答卡 | `questions.jsonl` → `answers/cube/qNN.json` + 原始留痕 | HTTP `:4100/chat` | Claude Agent SDK（生产现配，不动） |
| 裁判 | `judge/`（v1 人工在环 → M4 固化服务） | 逐题对出裁决书 + 修正答案 | 双侧作答卡 + 两侧语义层定义切片 → `verdicts/qNN.json` | v1：人 + Claude 辅助；M4：Claude headless | Claude |
| 编排器 | `bin/round.py` | 按一轮 SOP 顺序调用上述组件（M4 起支持 `--retest` 复验模式） | 轮号 → 本轮全部记录 | Windows Python | 无 LLM，纯流程 |

组件化边界的三条纪律：

1. **组件间只通过 §1.7 四层记录交换数据**（留痕 → 提取 → 裁决 → 回归），不共享内存态、不互相 import。
2. **适配器是独立的**：不搬 datus 仓 `tmp/run_qa.py`，按 §2.2 提取规格重写（v0 payload 作验收 fixture，见 §三）。
3. **出题人/裁判与答题人模型不对称**（决策点 Q1，§五）——评测者与被测者不同源，避免相关盲区。
4. **出题人盲考**：能力卡不进出题人输入，出题只依据考纲（决策点 D3b，§五）。

## 二、出题人启动：四件套

出题人是互搏的起点，也是唯一需要**从零新起**的 agent。启动分四步，每步有独立验收，全部通过才出现第一个机器生成的题库。

**出题依据原则（用户拍板）：根据课本出题，而不是根据答题人的能力出题。** 若按能力卡出题，考卷被答题人现状锚死，能力卡没有的永远不问，互搏就永远发现不了"双侧都没建模"的缺口——v0 的 q26-q30 是反证：预期 nomatch 的 3 题实际可答，这些缺口只有脱离能力卡、从业务与原始库出发才问得出来。因此出题人**只读考纲、不读能力卡**（盲考），能力卡生成器降级换岗到裁决/回灌侧（见本节末）。

### Step 0 — 考纲编译器

课本 = 两份原料：

**原料一：数据画像 `syllabus/db_profile.json`**（`gen_db_profile.py` 纯解析）——直连 ClickHouse（information_schema + 只读聚合，不经 dosi 引擎，无 Code 115 问题），对非税相关表生成：

| 画像内容 | 本项目已知锚点（全部来自原始库，无一来自能力卡） |
|---|---|
| 表/列/类型/COMMENT 注释 | fne_fund_main 全字段注释 |
| 行数与时间跨度 | 缴款表 53 个月；min/max 日期 |
| 月度/年度行数与金额分布 | 2025-08 两轴均无清分数据；2022-04 单笔 159.86 亿占全量 99.8% |
| 关键维度 distinct 值与分布 | funddivide（直缴/汇缴）、fstate 取值集合 |
| 空值率与空键承载金额 | fcollectid 空键 178/728 行承载 fimamt 99.82% |
| 金额极值/重复键画像 | 划拨批次头行+明细行重复携带整批金额 |

画像本身即孕育边界题与陷阱题——右列每一条都是 v0 实测踩出来的题眼。

**原料二：业务课本 `syllabus/business.md`**（人工整理，一次性 + 递增），从 datus 仓 non_tax 既有业务文档提炼，章节：

1. **业务链路**：缴款→清分→划拨→缴库各环节的业务含义与先后关系
2. **业务术语表**：直缴/汇缴、划拨、清分、欠缴、缴库确认……的业务定义（不是字段定义）
3. **层级结构**：单位树（执收单位→下级）、区划、科目大类→叶子
4. **已知业务事实与基准数**：P0/P1 对数结论中的业务事实（清分率≈0.87、各环节金额量级）
5. **已裁定口径**（递增）：每轮裁决产生的拍板口径**回写进课本**——教材随互搏生长，是比 accepted_answers 更根本的沉淀

**剥题纪律**：课本只含业务知识与事实，**不得含 07/09 号清单的原题文本**，否则出题人抄题；整理时把"题目+答案"剥掉、只留"知识"。

### Step 1 — 出题人 SKILL.md（契约）

出题人 agent 的系统契约，核心条款：

- **输入**：只给考纲（db_profile + business.md）。不给能力卡（盲考，出题人不知道答题人是谁、有什么能力——双侧天然对称）；不给历史题库原文（防照抄 v0 题）。
- **输出**：`questions.jsonl`，每行一题，字段必须含 `syllabus_ref`（回指考纲知识点编号）。
- **四类题型**（按课本知识点性质）：**事实**（单点指标/维度）、**关联**（跨表/跨环节，如链路状态、单位树下钻）、**辨析**（固有口径歧义，如不加直缴汇缴限定的"缴款金额"；歧义出处须能在课本找到）、**边界**（空值/极端分布/无数据期，如 2025-08 无清分数据、划拨重复计数）。
- **不标预期**：题库不含 `expect`——"谁该会"由实答揭示，nomatch 本身即登记；预期断言是自我实现的，考不出真东西。
- **质量门槛**：`syllabus_ref` 引用悬空即打回；出题后做**覆盖矩阵**（考纲知识点 × 题目），漏覆盖的知识点打回补题。
- 输出不合法（schema 校验失败 / 引用悬空 / 覆盖漏项）→ 自动打回重出，最多 N 次。

### Step 2 — `bin/examine.py`（CLI 封装）

出题人是 headless 调用的（无交互），封装为命令行：

```
uv run python bin/examine.py --syllabus syllabus/ --out rounds/round-02/questions.jsonl --count 30 --mix 事实:10,关联:10,辨析:5,边界:5
```

内部：读考纲 → 拼 prompt → `claude -p`（headless）→ JSONL 逐行校验（`schemas/question.schema.json` + syllabus_ref 悬空检查）→ 覆盖矩阵检查 → 落盘。校验失败自动重试。

### Step 3 — fixture 测试

- 校验器先对 **v0 的 25 题**（转成 questions.jsonl 格式）跑通——格式回归的锚点。
- `db_profile.json` 人工抽查：行数/时间跨度/空键承载对上 P0/P1 结论。
- `business.md` 剥题检查：全文不含 07/09 号清单原题文本。
- 再跑一次真实出题，人工抽检 5 题：syllabus_ref 是否真实、辨析题歧义是否在课本有出处、边界题是否有数据画像依据。

四件套齐 → round-02 题库诞生，互搏起点闭环。

### 能力卡生成器：不删，降级换岗

原 Step 0 的 `capability/gen_datus.py` / `gen_cube.py`（能力卡仍以各自语义模型为源——datus 解析 `fne_fund_main.yml` + **YAML=引擎=KB 三方一致断言**；cube 走 dictionary/members）从出题人输入中移除，产出 `capability/{datus,cube}.json` 挪到裁决与回灌侧，三用：

1. **裁判的语义层切片**：裁决时给裁判看两侧指标/member 定义原文（§四）。
2. **差距分析**：`考纲知识点 × 两侧能力卡` 覆盖差 → **双侧共同建模缺口单**——考纲里有、两侧能力卡都没有的知识点，是互搏最高价值产出（v0 的 q26-q28 即此类），制度化进轮报指标"双侧共同缺口数"。
3. **答题前健康检查**：三方一致断言保留为每轮开跑前的答题人语义层状态门，挂了先修再考。

**每轮作答前刷新**，保证能力卡反映语义层当前状态。附带收益：出题人盲了之后，考纲成为双方共同"教学大纲"，将来第三、第四个答题智能体加入，同一张卷子直接复考。

## 三、答题人适配器固化

### 统一 ask 契约（两侧一致）

- **输入**：`rounds/<轮>/questions.jsonl`（题库外置，适配器零题库）。
- **输出**：`answers/<side>/qNN.json`（统一作答卡）+ `runs/<side>/qNN.raw.*`（原始留痕：datus=payload 流，cube=/chat 响应+日志摘录）。
- **幂等**：`--only qNN` 子集复跑；作答卡覆盖写，原始留痕按时间戳归档不覆盖。
- **作答卡字段**（`schemas/answer_card.schema.json`）：`id / question / status(answer|ask|nomatch|failed) / 口径卡（裁判归一化的口径陈述，v1 可空）/ metrics_hit（工具级命中指标，机器提取）/ sql / answer / elapsed_s / raw_path / arbiter（ask 自动拍板记录）`。

### ask_datus 要点

- **WSL 桥接（文件交接，防 v0 的命令行引号坑）**：Windows 侧 adapter 经 `wsl.exe -d Ubuntu-26.04` 调用仓内 `adapters/ask_datus/wsl_runner.py`（用 datus 现成 `.venv/bin/python` 执行，纯标准库）——runner 在 WSL 内逐题 subprocess 跑 `.venv/bin/datus -p`，原始 payload 流原样落盘 `/mnt/d`（题目内容从不过命令行，免 `MSYS_NO_PATHCONV` 引号转写）；提取与作答卡写盘回到 Windows 侧做。LLM 走既有 portproxy relay。
- 提取规格 = 设计文档 §2.2 表格（SQL←execute_sql toolParams；命中指标←query_metrics/search_metrics/get_metric；答案←depth-0 markdown；真实错误←FuncToolResult `error` 字段，**正文 "Code NNN" 是 KB 文本，勿扫全文**）。
- 已知坑内置：深度>0 子代理的调用也要收（v0 教训）；超时题保留部分输出。
- **验收标准**：对 v0 的 25 份 `tmp/qa_run/*.jsonl` 重放提取器，结果与 `tmp/qa_results.json` 逐字段一致 → 提取器才算固化。

### ask_cube 要点

- `POST http://localhost:4100/chat {question, sessionId}`，三态分流：`answer`（提取 query JSON/编译 SQL/数值）/ `ask`（缺口径）/ `nomatch`（能力外）。
- **sessionId 策略**：每题新会话（题间零污染）；`ask` 态自动拍板——适配器按预设口径政策（缺省口径取自考纲"已裁定口径"节或人工预拍）构造追问再 POST 同 sessionId，拍板动作记入作答卡 `arbiter` 字段（裁决时"自动拍板"与"人拍板"区分对待）。
- **验收标准**：重放 v0 的 30 题，三态分布与首轮实测一致（q07/q09/q30 nomatch、q25/q29 ask）。

### 代码归属：永久在本仓（决策点 D8，用户拍板）

两适配器**永久固化在本仓 `adapters/`，不回迁** datus/cube 仓库——统一契约始终只有一份实现、一个事实源，杜绝双仓同步与漂移；互搏是适配器的唯一用户，产品仓库保留各自现有工具（datus 仓 tmp/run_qa.py 作历史参考）。v0 fixture 重放仍是适配器自身的回归门：每次改动提取规格后重放，与 `qa_results.json` 逐字段一致才放行。

## 四、裁判与记忆隔离

### 裁判实施：先人工在环，后固化

- **v1（round-02）人工在环**：把 v0 的 10 号对账文档逐题结构化为 `verdicts/*.json` 作为**校准集**——裁决书格式、口径卡写法、"只陈述客观差异不预判对错"的文风，先在人手里定型。
- 裁决四态：`互证通过`（口径同+值同）/ `建模差异`（口径不同→差距单）/ `执行事故`（口径同+值不同→bug 单）/ `待人工`。
- 裁判输入切片：两侧语义层**定义原文**（datus=YAML 指标定义节选；cube=member 定义节选），只给相关切片，不给全量。
- **M4 固化**为 judge 服务（Claude headless），以 round-02/03 的人工裁决为回归基准。
- **差距分析（材料包）**：`考纲知识点 × 两侧能力卡` 覆盖差 → **双侧共同建模缺口**（考纲覆盖而两侧能力卡皆无的知识点），按本侧视角写入两侧 issues 文件 §③；轮报指标增至五个：一致率 / 分歧分布 / 差距数 / 闭环率 / **双侧共同缺口数**。

### 回灌材料包：轮的终点，不自动回灌

**系统边界止于材料（决策点 D6，用户拍板）**：互搏产出回灌材料包后本轮结束；语义层修改、口径拍板、复验发起、回归入库全部是系统外的人工动作。每个语义层 diff 都有人背书——语义层是生产资产（改动牵动 P0/P1 基准与已发布查询），agent 自动改等于绕过工程评审；口径取舍是业务决策，系统只能并列双方证据，不能代拍。

材料包三件（`rounds/<轮>/feedback/`）：

| 文件 | 内容 |
|---|---|
| `issues-datus.md` | datus 侧全部要动手的，四节：① 建模差异（现象→双方口径对照→修法，每条附**记忆清理条目**）② 执行事故（现象→口径相同证据→疑似根因）③ 双侧共同缺口（**本侧视角**：datus 需建模什么）④ 待拍板口径（双方证据并列，拍板结果人工回填；附建议落课本的"已裁定口径"文案草案） |
| `issues-cube.md` | cube 侧同构四节（③ 写 cube 需建模什么；① 记忆清理栏写"无持久会话记忆，拍板口径落词典"） |
| `suite-candidates.jsonl` | 回归候选（T3 修正答案），人工删掉不认可的行 → `bin/round.py suite-add` 入库 |

- 共同缺口两侧各写各的行动项（自包含，不互相引用）；待拍板口径两份都放全量（拍板一次、两侧各自动手）；课本增补草案折在 §④，拍板后人工粘贴进 `syllabus/business.md`。
- 轮报五指标只在 report.md，材料包头部一行链接过去，不重复维护。
- **复验轮**（人工发起）：`bin/round.py --retest <上轮>`，上轮分歧题原题进下轮题库复验集重跑，通过且人工确认才写入 accepted_answers.json。闭环率是**跨轮指标**（上轮分歧题在本轮复验集的通过率）——它测的是"人拿着材料修完语义层后问题是否真消失"，中间隔着完整的工程过程，比系统自改自测可信。

### 记忆隔离（变量控制）

依据 v0 实测的**记忆粘性**（agent 援引"沿用 q10 拍板口径"，旧口径会跨会话复现）：

- 每轮开跑前快照 `.datus/memory/chat/`；同一侧轮内复跑前**恢复快照**——保证测的是语义层当前状态，不是上一轮的聊天记忆（决策点 D7）。
- 回灌后**定向清**（不是恢复旧快照——语义层已改，快照里的旧口径记忆与新时代不匹配）：材料包 `issues-datus.md` §① 每条建模差异附**记忆清理条目**（受影响 chat memory 的定位），清理由人工执行；不清则旧口径复活（v0 已验证的坑）。
- **闭环验收判据**：清记忆 → 复验重跑 → 仍通过，才算口径真修进了语义层；清后重跑挂 = 口径还赖在记忆里，回灌未完成。
- **教训升格**：chat memory 里反复出现的有益教训（如"该库需子查询绕过 Code 115"）应升格进语义层 ai_context / KB 文档后从记忆清除——知识落在能被测试的层里。
- cube 侧对应纪律：无持久会话记忆，sessionId 不跨轮复用；拍板口径落词典（词典即其"语义层记忆"）。

## 五、决策点台账

### 已议定（D1–D8）

| # | 决策 | 内容 | 落点 |
|---|---|---|---|
| D1 | 记录四层分离 | 原始留痕/机器提取/裁决/回归基准各层单一用途，禁止混写 | 设计文档 §1.7 |
| D2 | 命中指标两级记录 | 工具级 `metrics_hit`（过程证据，机器提取）+ 口径级 `cards`（裁决证据，裁判归一化） | 作答卡 schema |
| D3a | 能力卡以语义模型为源 | datus 解析 YAML+三方断言；cube 走 dictionary/members；用途=裁判切片/差距分析/答题前健康检查，**不进出题人** | §二 末 |
| D3b | 出题以考纲为源（用户拍板） | 课本=原始库数据画像+业务知识；**根据课本出题，而非根据答题人能力出题**；能力卡不进出题人输入（盲考） | §二 Step 0 |
| D4 | 对账先口径后数值 | 口径不同=建模差异；口径同值同=互证；口径同值异=执行事故 | 裁决四态 |
| D5 | 回归基准三层 | T1 文档基准（07 号）→ T2 双侧互证 → T3 修正答案+人工确认；沉淀进 `suite/accepted_answers.json` | §六 M4 |
| D6 | 不自动回灌（用户拍板） | 互搏止于**回灌材料包**（两侧 issues + 回归候选）；语义层修改/口径拍板/复验发起/套件入库均为人工动作 | §四 |
| D7 | 记忆隔离与清理细化 | 只快照/恢复 `.datus/memory/chat/`；回灌**定向清**（清理条目由材料包提供）；**清后重跑仍通过=闭环验收**；有益教训升格进语义层 | §四 |
| D8 | 适配器永久留本仓（用户拍板） | `ask_datus`/`ask_cube` 固化在 sql-sparring `adapters/`，**不回迁**各自仓库；统一契约单一事实源 | §三 |

### 待确认（Q1，附建议）

| # | 议题 | 建议 | 理由 |
|---|---|---|---|
| Q1 | 模型不对称 | 出题人/裁判用 Claude；答题人保持生产现配（datus=GLM-5.3-Flash、cube=Claude Agent SDK） | 评测者与被测者不同源，避免相关盲区；答题人反映真实生产状态 |

## 六、里程碑（M0–M4，答题链路先行）

| 里程碑 | 内容 | 验收 | 产出 |
|---|---|---|---|
| **M0 答题链路打通** | Windows 侧 uv 环境初始化（pyproject.toml + uv.lock 入 git，依赖仅 httpx/jsonschema/pydantic）+ `ask_datus`（wsl_runner 桥接 + §2.2 提取器）+ `ask_cube`（:4100 三态 + 拍板政策）+ **最小作答卡结构**（id / question / status / metrics_hit / sql / sql_count / answer / errors / elapsed_s / arbiter / raw_path——M1 升格为正式 schema 的底坯） | ① **对接活体验证（主目标）**：datus ≥2 道新题活跑（`datus -p`）status=answer 且带数值；cube ≥2 道新题活跑（`:4100/chat`）至少 1 题数值答案；② A3：v0 cube 30 题活重放三态比对——锚点保持（q07/q09 nomatch 不变、q30 退付未建模边界不消失）、无退化对，词典回写演化/口径反问拍板闭环逐题标注；③ B1：v0 datus 25 份 payload 离线重放，提取与 `qa_results.json` 逐字段一致（豁免 elapsed_s/returncode/stderr_tail/question） | `adapters/` 双适配器 + `rounds/m0/` 证据 + `pyproject.toml` |
| **M1 契约定稿** | 四个 JSON Schema（question / answer_card / verdict / capability）+ v0 作答卡样例 fixtures + questions.jsonl 格式定稿；answer_card 以 M0 最小结构为底补全（口径卡 / arbiter 全字段），适配器输出切换到 schema 校验 | schemas 通过 v0 数据回填校验；适配器全量输出过校验 | `schemas/` + `fixtures/` |
| **M2 出题人启动** | 考纲编译器（db_profile 纯解析 + business.md 剥题整理）+ SKILL.md + `bin/examine.py` + fixture 测试；能力卡生成器换岗至裁决/回灌侧 | db_profile 抽查对上 P0/P1 结论；business.md 剥题检查通过；题库覆盖矩阵无漏项；首个机器题库诞生 | `syllabus/` + `examiner/` + `capability/` + round-02 题库 |
| **M3 首个自动轮** | `bin/round.py` 跑 round-02 全流程（出题→双侧作答→提取）；裁决人工在环 | 一轮完整记录落盘 + 轮报五指标（一致率/分歧分布/差距数/闭环率/双侧共同缺口数） | `rounds/round-02/` + report |
| **M4 复验轮与固化** | 复验轮机制跑通：人工按材料包修双侧语义层并清记忆 → 发起复验（`--retest <上轮>`，复验集=上轮分歧题）→ 通过题人工确认入库；材料包格式定稿；裁判固化 judge 服务 | 复验轮至少跑通一次且闭环率>0；judge 以人工裁决为回归基准 | 回归套件 + 材料包模板 |

顺序依赖：M0（链路可行性）→ M1（契约定稿）→ M2 → M3 → M4。**M0 先行的理由**：两条答题链路是全系统最大的外部依赖风险（WSL 桥、:4100 活服务、提取规格），先证明"可调用、能答数"，再冻结契约——契约没有跳过，只是延后到有真实输出为底时才定稿。M0 只依赖 §2.2 提取规格与最小作答卡结构，不依赖完整 schema；datus 侧与 cube 侧可并行，datus 侧提取器可对 v0 留痕离线开发调试。

## 七、运行入口与目录树（M4 完成态）

### 运行入口

主入口 + 三个组件入口，人只碰 `bin/round.py`：

| 层 | 入口 | 职责 |
|---|---|---|
| 主入口 | `bin/round.py` | 一轮全流程（自动执行 SOP 第 1–6 步，到产出材料包为止） |
| 组件入口 | `bin/examine.py` | 只出题（SOP 第 1 步），round.py 内部也调它 |
| 组件入口 | `adapters/`（两个） | 答题驱动器，round.py 逐侧调用；可单跑（子集复跑/fixture 回归门） |
| 组件入口 | `judge/` | 裁决：v1 人工在环（人读作答卡写 verdicts），M4 固化为 headless 服务 |
| 被封装 | `claude -p` | examiner/judge 的 LLM 调用由上述 Python 入口内部发起，人不直接调 |

典型命令（M2/M3 落地后；**Windows 侧 uv 环境执行**，ask_datus 内部经 wsl_runner 桥接 WSL）：

```bash
# 跑一整轮：出题→双侧作答→提取→裁决在环→材料包+轮报（SOP 1–6 自动，7–8 留给人）
uv run python bin/round.py --round round-02

# 复验轮（人工发起，M4）：上轮分歧题原题进复验集
uv run python bin/round.py --round round-03 --retest round-02

# 只出题（考纲编译好之后）
uv run python bin/examine.py --syllabus syllabus/ --out rounds/round-02/questions.jsonl --count 30 --mix 事实:10,关联:10,辨析:5,边界:5

# 单侧子集复跑（回归失败题时）
uv run python -m adapters.ask_datus --round round-02 --only q09

# 回归候选入库（人工在 suite-candidates.jsonl 删掉不认可的行之后）
uv run python bin/round.py suite-add --round round-02
```

与 SOP 的对应：round.py 自动跑 ①出题→②双侧作答→③提取→④裁决（人工在环确认）→⑤轮报→⑥材料包渲染，**到材料包即停**（D6）；第 ⑦ 步（修语义层/拍板/清记忆）与第 ⑧ 步（复验发起/确认入库）是人工动作——复验的"发起"就是带 `--retest` 再跑一次 round.py，"确认入库"就是删行后 `suite-add`。

### 目录树（M4 完成态）

```
D:\develop\sql-sparring\
  README.md  docs\                     索引 + 总体设计 + 本实施设计
  schemas\  fixtures\                  M1：四类 JSON Schema + v0 回填样例（契约定稿，answer_card 以 M0 最小结构为底）
  adapters\{ask_datus, ask_cube}\      M0：双答题驱动器（永久在本仓，D8）
  syllabus\                            M2：考纲=课本（db_profile 数据画像 + business.md 业务课本，出题唯一依据）
  examiner\                            M2：出题人（SKILL.md + bin/examine.py，只读考纲盲考）
  capability\                          M2：能力卡生成器与产出（裁决/差距分析侧，不进出题人）
  judge\  bin\round.py                 M3/M4：裁判（人工在环→固化服务）+ 一轮编排器（--retest 复验）
  rounds\round-NN\                     每轮记录（§1.7 四层：runs 留痕→answers 提取→verdicts 裁决→feedback 材料包）
    feedback\                          轮终点（D6 不自动回灌）：issues-{datus,cube}.md + suite-candidates.jsonl
  suite\accepted_answers.json          跨轮回归基准（人工确认后入库）
```

## 八、v0 数据迁移

- datus 侧：`tmp/qa_run/*.jsonl` + `tmp/qa_results.json` → M0 的重放验收基准与 M1 的 fixtures；10 号对账总表 → M3 裁决校准集。
- cube 侧：09-cube 文档 + `logs/agent-svc-*.log` → ask_cube 验收参照。
- 业务课本：07/09/10 号及 03/P0/P1 业务文档**剥题提炼**（只留业务知识与事实，不留原题文本）→ `syllabus/business.md`；P0/P1 实测事实（空键承载、极值分布、无数据期）→ `db_profile.json` 的抽查锚点。
- 首轮叙事文档（07/09/09/10）留在 datus 仓 `development_process_record/non_tax/` 作历史记录，机器层自 round-02 起全部落本仓。
