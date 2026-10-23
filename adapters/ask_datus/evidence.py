"""datus 日志旁路取证（v4，2026-10-23）：按题时间窗提取实际执行的 dosi SQL。

为什么走日志：query_metrics 正常调用的返回体不含 SQL（工具层故意剥离，
datus 仓 datus/tools/func_tool/semantic_tools.py:1412——防 LLM 上下文膨胀；
q10/q11 payload 实证 metadata 无 sql），实际执行原文只落在 datus 自己的
日志里（datus/tools/semantic_tools/dosi/runtime.py 的 dosi_sql_executed
INFO 行，v4 加——记于 engine.execute 成功后，零行为改动，LLM 无感知）。

定位规则：日志文件名按服务启动日命名、跨天不换名（如 agent.2026-10-22.log
在 10-23 仍在追加），所以按"mtime 最新的 agent.*.log"找当前文件（与 datus
自身 _get_current_log_file 同规则）。目录候选：env DATUS_LOG_DIR > datus
工作区 .datus/logs（实测主位置）> ~/.datus/logs（datus 代码默认值）。
轮转旧文件名带 .log.<日期> 后缀，glob("agent.*.log") 不会误命中。

解析规则：structlog 日志行首带时间戳（YYYY-MM-DD HH:MM:SS）；标记行的
sql= 参数放在末位，其后全部文本（含跨物理行的续行，直到下一条带时间戳的
日志行为止）即 SQL 原文。

时钟源（2026-10-23 实测）：datus 跑在 WSL，日志时间戳走 UTC，比 Windows
本地（driver 记录的 started/ended）慢 8 小时（日志末行 07:24:15 vs
Windows 15:26 同一停机时刻）。harvest 用"日志文件 mtime = 末条时间戳的
写入时刻"自校准固定偏移，不写死时区；校准失败（无时间戳行）按偏移 0，
最坏降级为取证为空。

失败兜底：日志文件缺失/无标记行/窗口无命中一律返回空列表，不抛——
取证是加分项，绝不影响作答与卡状态（卡 sql="" 降级）。
"""

import os
import re
import time
from pathlib import Path

# 日志行首时间戳（structlog TimeStamper，本地时间），如 2026-10-23 14:30:01
_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\b")
_MARKER = "dosi_sql_executed"

# datus 工作区日志目录（实测主位置；env DATUS_LOG_DIR 可覆盖）
_DATUS_WS_LOGS = Path(r"D:\develop\datus\Datus-agent\.datus\logs")


def _candidate_dirs() -> list[Path]:
    """日志目录候选，按优先级：env 覆盖 > datus 工作区 > 用户主目录。"""
    dirs = []
    env = os.environ.get("DATUS_LOG_DIR")
    if env:
        dirs.append(Path(env))
    dirs.append(_DATUS_WS_LOGS)
    dirs.append(Path.home() / ".datus" / "logs")
    return dirs


def _current_log_file() -> Path | None:
    """mtime 最新的 agent.*.log；全找不到返回 None。"""
    best = None
    for d in _candidate_dirs():
        if not d.is_dir():
            continue
        for f in d.glob("agent.*.log"):
            try:
                if best is None or f.stat().st_mtime > best.stat().st_mtime:
                    best = f
            except OSError:
                continue
    return best


def _sql_text(marker_line: str) -> str:
    """标记行中 sql= 之后的文本（structlog 若带引号包裹则容错剥除并还原转义）。

    structlog 渲染会把值包进引号并把内部引号转义为 \\'（烟测实测：
    sql='SELECT dateTrunc(\\'MONTH\\', ...)）。剥外层引号后还需把 \\' 还原为
    ' 才是执行原文。CH 财务 SQL 不含字面反斜杠，单条 replace 足够。
    """
    idx = marker_line.find("sql=")
    if idx < 0:
        return ""
    text = marker_line[idx + len("sql="):].strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1]
    return text.replace("\\'", "'")


def harvest(started_epoch: float, ended_epoch: float) -> list[str]:
    """时间窗 [started_epoch, ended_epoch]（Windows epoch 秒）内的 SQL 原文列表。

    日志时间戳时钟与 Windows 本地可能存在固定偏移（实测 WSL 走 UTC），
    用"日志文件 mtime = 末条时间戳的写入时刻"自校准：line_epoch =
    mktime(时间戳按本地解释) + 偏移。返回按日志出现顺序排列。
    """
    log_file = _current_log_file()
    if log_file is None:
        return []
    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    offset = 0.0  # 偏移自校准：文件 mtime（末条真实写入时刻）− 末条时间戳按本地解释
    try:
        mtime = log_file.stat().st_mtime
        for line in reversed(lines):
            m = _TS_RE.match(line)
            if m:
                offset = mtime - time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
                break
    except (OSError, ValueError):
        offset = 0.0

    sqls: list[str] = []
    capturing = False
    for line in lines:
        if not _TS_RE.match(line):  # 无时间戳 = 上一条的续行（多行 SQL）
            if capturing and sqls:
                sqls[-1] += "\n" + line
            continue
        capturing = False
        if _MARKER not in line:
            continue
        try:
            m = _TS_RE.match(line)
            line_epoch = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")) + offset
        except ValueError:
            continue
        if started_epoch <= line_epoch <= ended_epoch:
            capturing = True
            sqls.append(_sql_text(line))
    return [s for s in sqls if s]
