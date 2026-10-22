# adapters/ — 答题人适配器使用说明

两个驱动器分别驱动 datus 与 cube 两个问数智能体（生产现配，不动）逐题作答，产出统一作答卡与原始留痕。互搏正式轮（round-02 起）由 `bin/round.py` 调用（M3 落地），平时可按本文单独使用。

## 前置条件

| 程序 | 依赖 | 检查方法 |
|---|---|---|
| ask_datus | WSL 发行版 `Ubuntu-26.04`，datus 虚拟环境在 `/mnt/d/develop/datus/Datus-agent/.venv/` | `wsl -l -v` 能看到该发行版 |
| ask_cube | cube 服务 `:4100`（问数）与 `:4000`（编译 SQL）在跑；`D:\develop\cube\.env` 里有 `CUBEJS_API_SECRET` | 浏览器开 `http://localhost:4100/` 返回正常页面 |

两个程序都在本仓根目录用 uv 环境执行（Windows 侧）。

## 怎么用

题库是 JSONL 文件，每行一题：`{"id": "x01", "question": "自然语言问题"}`。

```bash
# datus：逐题经 WSL 桥接调 datus -p
uv run python -m adapters.ask_datus run --questions rounds/m0/questions-datus.jsonl
#     可选 --only dn1 dn2（子集复跑）   --timeout 900（单题上限秒数）

# cube：逐题 POST :4100/chat
uv run python -m adapters.ask_cube run --questions rounds/m0/questions-cube.jsonl
#     可选 --only cn1（子集复跑）   --prefix m0q（会话前缀，每题实际用 <prefix>-<id>）
```

### 两个程序各自的要点

- **ask_datus**：Windows 不直接跑 datus，而是把题目写成文件、经 `wsl.exe -d Ubuntu-26.04` 在 WSL 里用 datus 自带虚拟环境执行（WSL 桥接——题目内容从不过命令行，避免引号转写坑）。单题超时默认 900 秒，超时截断但保留已产出的部分输出。
- **ask_cube**：每题新开会话（sessionId，会话标识，题间零污染）；若首答是反问（三态中的 ask），按拍板政策自动把第一个选项原文回发同一会话再取答案，追问与选项记入作答卡 `arbiter` 字段；答案里的语义层查询会再调 `:4000` 换取编译后的 SQL（失败不阻断作答，留注释说明）。

## 输出在哪

以题库所在目录为根（如 `rounds/m0/`）：

| 位置 | 内容 |
|---|---|
| `runs/<侧>/` | 原始留痕（一级证据，一字不改）。datus：question.txt / payload.jsonl / stderr.txt / meta.json；cube：raw.json（首答+追问）/ sql.txt |
| `answers/<侧>/<id>.json` | 作答卡 11 字段：id / question / status / metrics_hit（命中了哪些语义层指标）/ sql / sql_count / answer / errors / elapsed_s / arbiter（自动拍板记录）/ raw_path |

- status 取值：datus 侧 `answer`（成功）/ `failed`；cube 侧 `answer` / `ask`（首答反问）/ `nomatch`（能力外）/ `failed`。
- 幂等：`--only` 可复跑子集；作答卡覆盖写，原始留痕按时间戳归档不覆盖。

完整实例见 `rounds/m0/`。

## 常见问题

| 现象 | 原因与处理 |
|---|---|
| cube 全部返回 502 且响应体为空 | 十有八九是 Windows 系统代理劫持了 localhost 请求（浏览器/curl 不读该代理，容易误判"服务挂了"）。适配器已内置绕过（`trust_env=False`）；自己写脚本调 `:4100` 时记得同样处理 |
| datus 报 WSL 发行版不存在 | `wsl -l -v` 看实际名字，与 `adapters/ask_datus/driver.py` 的 `WSL_DISTRO` 对齐 |
| cube 连接被拒 | `:4100` 服务没起，先启动 cube 服务再跑 |
| datus 某题很久不出结果 | 单题本就慢（M0 实测 75–155 秒）；超 900 秒按超时截断并保留部分输出，可用 `--timeout` 加大 |

## 术语

（全文定义与 `docs/glossary.md` 一致，此处为速查）

- **作答卡**：每题的机器提取结果（统一 11 字段结构），从原始留痕提取而来。
- **payload（原始报文）**：datus 逐条输出的原始消息流，一字不改存档，是一级证据。
- **三态**：cube 返回的三种类型：answer（有答案）/ ask（反问口径）/ nomatch（能力外）。
- **拍板政策**：对口径反问的标准应答规则——本项目取第一个选项原文回发同一会话。
- **WSL 桥接**：Windows 侧经 `wsl.exe` 调用 WSL 内命令、以文件交接数据的方式。
