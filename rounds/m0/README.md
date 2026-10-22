# rounds/m0 — M0 验证记录

非正式轮（round-02 起才是正式轮）。本目录存 M0 答题链路打通的全部证据。

| 文件/目录 | 内容 |
|---|---|
| `b1_replay_report.json` | B1 回归门：v0 25 份 payload 离线重放，与 qa_results.json 逐字段比对 |
| `a3_replay_report.json` | A3：v0 30 题活重放，首答三态比对 v0 status.json |
| `questions-datus.jsonl` / `questions-cube.jsonl` | A1/A2 新题（**人工出题**，M0 连通验证用，非考纲产物；考纲 M2 才有） |
| `runs/datus/` | datus 活跑留痕：question.txt / payload.jsonl / stderr.txt / meta.json |
| `runs/cube/` | cube 活跑留痕：raw.json（首答+追问）/ sql.txt |
| `answers/datus/` `answers/cube/` | 11 字段最小作答卡 |

A3 判定纪律（v0 语义层已被自身回写改动，静止前提不成立）：

- 硬锚点：q07/q09/q30 必须仍 nomatch（能力边界未动）
- FAIL 条件：锚点失效，或退化对（answer→nomatch / answer→ask）
- ask→answer 翻转 = 词典回写演化（v0 拍板已落活词典），逐题标注，不算失败
- q13 v0 为瞬时 502，翻转为 answer 属预期
