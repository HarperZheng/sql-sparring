"""Windows 侧驱动：逐题 POST datus chat API（:8501），回收 payload 并组装作答卡。

链路（2026-10-23 起）：client.post_chat_stream（SSE）→ payload 行落盘 →
extractor 提取 → 11 字段作答卡落盘。datus 常驻服务内 agent 配置/语义模型
只在服务启动时装一次（每轮一次初始化，不再每题冷启）；每题新 session_id
保证题间零污染（D7）。
路由（D13 全题指标优先）：每题先走 ask_metrics 节点（query_metrics 通道），无最终
答案降级默认 chat 节点再答，meta.routes 全留痕；路由不读题型（盲考纪律）。
幂等（§三契约）：--only 子集复跑；作答卡覆盖写，原始留痕按时间戳归档不覆盖。
（v0 的 WSL 桥接 wsl_runner.py 已退役，文件保留作回退参考。）
"""

import json
import shutil
import time
from pathlib import Path

from . import client

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIMEOUT_S = 900
WALL_CLOCK_S = 180    # 单题墙钟 3 分钟（2026-10-23 用户拍板）：到点记超时卡换下一题。
                      # 已知代价：实测成功题最长 200.6s（q12），此类题会被截为超时卡。
RETRY_ATTEMPTS = 3    # 与 ask_cube 同款：网络类失败换新 session 重试
RETRY_BACKOFF_S = 20.0

# 路由（D13 全题指标优先，2026-10-23 拍板）：每题先走 ask_metrics 节点（唯一
# query_metrics 挂载点，node_factory 硬编码映射），无最终答案降级默认 chat 节点再答。
# 路由不读题型——题型是出题人侧考纲信息，答题人不读题型字段（盲考纪律）。
METRICS_SUBAGENT = "ask_metrics"


def _archive_existing(path: Path) -> str | None:
    """留痕不覆盖：已有文件挪为 <stem>.<时间戳><后缀>，返回归档名。"""
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archived = path.with_name(f"{path.stem}.{stamp}{path.suffix}")
    shutil.move(str(path), str(archived))
    return archived.name


def _ask(question: str, session_id: str, timeout_s: float,
         wall_clock_s: float, subagent_id: str | None = None) -> tuple[list[str], dict, str, str]:
    """首答（网络类失败换新 sessionId 重试，指数式退避；与 cube _ask_with_retry 同款）。

    返回 (payload 行, summary, 实际用的 session_id, 错误链)。
    client.ChatTimeout（读超时/墙钟到点）不在此重试——重试=再等一个整预算，向上抛。
    """
    err = ""
    for i in range(RETRY_ATTEMPTS):
        sid = session_id if i == 0 else f"{session_id}-r{i + 1}"
        try:
            lines, summary = client.post_chat_stream(question, sid, timeout_s=timeout_s,
                                                     wall_clock_s=wall_clock_s,
                                                     subagent_id=subagent_id)
            return lines, summary, sid, ""
        except client.ChatTimeout:
            raise
        except Exception as e:
            err = (err + " | " if err else "") + str(e)[:300]
            if i < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_BACKOFF_S * (i + 1))
    return [], {}, session_id, err


def run_question(qid: str, question: str, runs_dir: Path,
                 timeout_s: int = DEFAULT_TIMEOUT_S, session_prefix: str = "sparring",
                 wall_clock_s: float = WALL_CLOCK_S) -> dict:
    """跑一题，返回 {card, extracted, meta}。落盘：payload/meta 在 runs_dir。

    路由（D13 全题指标优先）：一律先走 ask_metrics，该尝试无最终答案（未建模/
    报错/超时）时降级默认 chat 再答一次。每次尝试的 payload 先归档再覆盖写
    （留痕不覆盖），meta.routes 记尝试全貌，平铺字段=最终采纳尝试。
    """
    runs_dir = Path(runs_dir).resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = runs_dir / f"{qid}.payload.jsonl"
    meta_f = runs_dir / f"{qid}.meta.json"

    plan = ["metrics", "chat"]  # D13：全题指标优先，不读题型
    routes: list[dict] = []
    final: dict | None = None
    total_elapsed = 0.0
    for route in plan:
        subagent = METRICS_SUBAGENT if route == "metrics" else None
        sid = f"{session_prefix}-{qid}" + ("-m" if route == "metrics" else "")
        archived = _archive_existing(payload)
        t0 = time.time()
        started_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0))
        timed_out = False
        try:
            lines, summary, session_id, err = _ask(question, sid, timeout_s,
                                                   wall_clock_s, subagent)
        except client.ChatTimeout as e:
            lines, summary = e.partial, {"timed_out": True}
            session_id, err, timed_out = sid, str(e)[:300], True
            limit_s = e.timeout_s  # 状态文案记实际触发的上限（墙钟 180s 而非读超时 900s）
        else:
            limit_s = timeout_s
        t1 = time.time()
        elapsed = round(t1 - t0, 1)
        ended_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t1))
        total_elapsed = round(total_elapsed + elapsed, 1)

        payload.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

        from . import extractor
        extracted = extractor.extract(lines, timed_out=timed_out, timeout_s=limit_s)
        if not lines and not timed_out:
            # 重试全挂、零 payload：错误链写进提取结果（卡 status=error，D10 一等留痕）
            extracted["status"] = "报错: chat API 连续失败 | " + err
            extracted["errors"] = [err] if err else []
        final = {"route": route, "extracted": extracted, "session_id": session_id,
                 "timed_out": timed_out, "elapsed_s": elapsed, "summary": summary,
                 "error": err, "archived": archived,
                 "started_at": started_at, "ended_at": ended_at,
                 "started_epoch": t0, "ended_epoch": t1}
        routes.append({
            "route": route, "subagent_id": subagent, "session_id": session_id,
            "started_at": started_at, "ended_at": ended_at,
            "timed_out": timed_out, "elapsed_s": elapsed,
            "duration_s": summary.get("duration_s"), "requests": summary.get("requests"),
            "total_tokens": summary.get("total_tokens"), "status": extracted["status"],
            "answered": bool(extracted["answer"]), "error": err or None,
            "archived_payload": archived,
        })
        if extracted["answer"]:
            break  # 该通道出了最终答案，不再降级

    assert final is not None  # plan 非空，循环至少执行一次

    # v4 SQL 旁路取证（2026-10-23）：指标路径出答案但卡无 SQL（query_metrics
    # 返回体不含 SQL 原文，datus 工具层故意剥离）时，从 datus 日志按本题
    # 时间窗提取实际执行原文。取证在墙钟外；任何失败降级为不填充（sql 保持
    # ""），不影响作答与状态；chat 路由的 SQL 本就在 payload，不走此路。
    sql_source = ""
    if final["extracted"]["sql_count"] == 0 and final["extracted"]["metric_calls"]:
        from . import evidence
        window_sqls = evidence.harvest(final["started_epoch"], final["ended_epoch"])
        if window_sqls:
            final["extracted"]["sql"] = window_sqls[-1]
            final["extracted"]["sql_count"] = len(window_sqls)
            sql_source = "datus-log"

    meta = {"channel": "chat-api", "route_used": final["route"], "routes": routes,
            # 以下平铺字段=最终采纳尝试（兼容旧读者）；elapsed_s=全 attempts 总耗时
            "session_id": final["session_id"], "timed_out": final["timed_out"],
            "elapsed_s": total_elapsed,
            "duration_s": final["summary"].get("duration_s"),
            "requests": final["summary"].get("requests"),
            "total_tokens": final["summary"].get("total_tokens"),
            "error": final["error"] or None, "sql_source": sql_source}
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "extracted": final["extracted"],
        "meta": meta,
        "archived": {"payload": final["archived"]},
        "payload_rel": str(payload.relative_to(REPO_ROOT)).replace("\\", "/"),
    }


def build_and_write_card(qid: str, question: str, result: dict, answers_dir: Path) -> Path:
    """提取结果 → 值行提取步 → 作答卡（契约校验，不过不落盘）→ 落盘（覆盖写）。返回卡片路径。

    值行提取步（D14）：答案散文（extracted["answer"]，全文已留 runs/）交 LLM 结构化为
    值行（adapters/value_extract.py，模型走 conf/models.json extractor 节）；提取问题清单
    追加进卡 errors。失败降级 values=[]，不影响作答状态。
    """
    from .card import build_card
    from schemas.validator import validate_card
    from ..value_extract import extract_values
    extracted = result["extracted"]
    values, vprobs = [], []
    if (extracted.get("answer") or "").strip():
        names = [n for m in extracted.get("metric_calls") or [] for n in m.get("names") or []]
        values, vprobs = extract_values(question, extracted["answer"], names)
    card = build_card(
        qid, question, extracted, values,
        elapsed_s=result["meta"]["elapsed_s"],
        raw_path=result["payload_rel"],
    )
    if vprobs:
        card["errors"] = list(card.get("errors") or []) + vprobs
    validate_card(card, where="（ask_datus 写卡前）")
    answers_dir.mkdir(parents=True, exist_ok=True)
    out = answers_dir / f"{qid}.json"
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
