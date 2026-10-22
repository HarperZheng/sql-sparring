# M0 收尾报告（2026-10-22）

## 结论

M0 验收（对接活体验证）全过，**对接成功已证明**：datus 与 cube 两条答题链路端到端可用（真打服务 → 出数值答案 → 留痕 → 提取成卡）。过程中一个关键插曲：链路曾误报大面积 502，根因是脚本 bug（Windows 系统代理劫持 localhost 请求），修复（`trust_env=False`）后全部正常——服务本身始终健康（用户实测判断"服务是通的"是破案关键）。

## 证据

| 验收项 | 做法 | 结果 | 证据位置 |
|---|---|---|---|
| datus 新题活跑 | dn1–dn3 真打 `datus -p`（WSL 桥，GLM-5.3-Flash） | 3/3 status=answer，数值答案（dn1：2024 上半年缴款 75,217,304.92 元 / 102 笔） | `answers/datus/` + `runs/datus/` |
| cube 新题活跑 | cn1–cn3 真打 `:4100/chat` | 3/3 answer，各 1 条编译 SQL（cn1：2023 全年缴款 146.58 万元） | `answers/cube/cn*.json` + `runs/cube/` |

## 过程事故（已修复）

1. **系统代理劫持**：httpx 在 Windows 会读注册表系统代理，11:28 后发往 `localhost:4100` 的请求全被代理返回空 502（浏览器/curl 不读注册表代理故正常）。修复：`trust_env=False`（`adapters/ask_cube/client.py`）。
2. **相对路径组卡崩溃**：runs_dir 传相对路径时 `relative_to` 抛异常（ask_datus/ask_cube 同款）。修复：`resolve()`。

## 遗留与未决

1. 模型不对称已拍板（D9，2026-10-22）：答题人生产现配不动，出题人/裁判的模型、接口、key 走 `conf/models.json`（M1 落骨架）。
2. Git CRLF 提示为行尾换算警告，不影响内容。
3. datus/tmp 与 cube/.tmp 已于 2026-10-22 经用户确认删除（删除前逐文件 SHA256 复验）。
