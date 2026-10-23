"""Windows 侧驱动：逐题 POST datus chat API（:8501），回收 payload 并组装作答卡。

链路（v1，2026-10-23 起）：client.post_chat_stream（SSE）→ payload 行落盘 →
extractor 提取 → 11 字段作答卡落盘。datus 常驻服务内 agent 配置/语义模型
只在服务启动时装一次（每轮一次初始化，不再每题冷启）；每题新 session_id
保证题间零污染（D7）。
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


def _archive_existing(path: Path) -> str | None:
    """留痕不覆盖：已有文件挪为 <stem>.<时间戳><后缀>，返回归档名。"""
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archived = path.with_name(f"{path.stem}.{stamp}{path.suffix}")
    shutil.move(str(path), str(archived))
    return archived.name


def _ask(question: str, session_id: str, timeout_s: float,
         wall_clock_s: float) -> tuple[list[str], dict, str, str]:
    """首答（网络类失败换新 sessionId 重试，指数式退避；与 cube _ask_with_retry 同款）。

    返回 (payload 行, summary, 实际用的 session_id, 错误链)。
    client.ChatTimeout（读超时/墙钟到点）不在此重试——重试=再等一个整预算，向上抛。
    """
    err = ""
    for i in range(RETRY_ATTEMPTS):
        sid = session_id if i == 0 else f"{session_id}-r{i + 1}"
        try:
            lines, summary = client.post_chat_stream(question, sid, timeout_s=timeout_s,
                                                     wall_clock_s=wall_clock_s)
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
    """跑一题，返回 {card, extracted, meta}。落盘：payload/meta 在 runs_dir。"""
    runs_dir = Path(runs_dir).resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = runs_dir / f"{qid}.payload.jsonl"
    meta_f = runs_dir / f"{qid}.meta.json"
    archived = _archive_existing(payload)

    t0 = time.time()
    timed_out = False
    try:
        lines, summary, session_id, err = _ask(question, f"{session_prefix}-{qid}",
                                               timeout_s, wall_clock_s)
    except client.ChatTimeout as e:
        lines, summary = e.partial, {"timed_out": True}
        session_id, err, timed_out = f"{session_prefix}-{qid}", str(e)[:300], True
        timeout_s = e.timeout_s  # 状态文案记实际触发的上限（墙钟 180s 而非读超时 900s）
    elapsed = round(time.time() - t0, 1)

    payload.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    from . import extractor
    extracted = extractor.extract(lines, timed_out=timed_out, timeout_s=timeout_s)
    if not lines and not timed_out:
        # 重试全挂、零 payload：错误链写进提取结果（卡 status=error，D10 一等留痕）
        extracted["status"] = "报错: chat API 连续失败 | " + err
        extracted["errors"] = [err] if err else []

    meta = {"channel": "chat-api", "session_id": session_id, "timed_out": timed_out,
            "elapsed_s": elapsed, "duration_s": summary.get("duration_s"),
            "requests": summary.get("requests"), "total_tokens": summary.get("total_tokens"),
            "error": err or None}
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "extracted": extracted,
        "meta": meta,
        "archived": {"payload": archived},
        "payload_rel": str(payload.relative_to(REPO_ROOT)).replace("\\", "/"),
    }


def build_and_write_card(qid: str, question: str, result: dict, answers_dir: Path) -> Path:
    """提取结果 → 作答卡（契约校验，不过不落盘）→ 落盘（覆盖写）。返回卡片路径。"""
    from .card import build_card
    from schemas.validator import validate_card
    card = build_card(
        qid, question, result["extracted"],
        elapsed_s=result["meta"]["elapsed_s"],
        raw_path=result["payload_rel"],
    )
    validate_card(card, where="（ask_datus 写卡前）")
    answers_dir.mkdir(parents=True, exist_ok=True)
    out = answers_dir / f"{qid}.json"
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
