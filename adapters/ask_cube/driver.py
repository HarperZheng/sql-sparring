"""Windows 侧驱动：逐题问 cube、ask 自动拍板、留痕落盘、作答卡组装。

幂等（§三契约）：--only 子集复跑；作答卡覆盖写，原始留痕按时间戳归档不覆盖。
"""

import json
import shutil
import time
from pathlib import Path

from . import client, policy
from .card import build_card

REPO_ROOT = Path(__file__).resolve().parents[2]


def _archive_existing(path: Path):
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archived = path.with_name(f"{path.stem}.{stamp}{path.suffix}")
    shutil.move(str(path), str(archived))
    return archived.name


def run_question(qid: str, question: str, session_prefix: str, runs_dir: Path) -> dict:
    """一题完整作答流：首答 →（ask 时自动拍板追问）→ 编译 SQL 抓取 → 留痕。

    返回 {card, first_type, raw_rel}。失败重试一次（新 sessionId，v0 同款）。
    """
    runs_dir = Path(runs_dir).resolve()  # 相对路径（--questions 传相对值时）无法 relative_to 仓根
    runs_dir.mkdir(parents=True, exist_ok=True)
    raw_path = runs_dir / f"{qid}.raw.json"
    _archive_existing(raw_path)

    t0 = time.time()
    session_id = f"{session_prefix}-{qid}"
    first, followups, err = _ask_with_retry(question, session_id)

    sql, sql_count = "", 0
    if first and first.get("type") == "answer":
        tables = first.get("tables") or []
        sqls, failed_fetch = [], 0
        for i, t in enumerate(tables):
            if not t.get("query"):
                continue
            try:
                sqls.append(f"-- table[{i}] {t.get('title', '')}\n"
                            + client.fetch_compiled_sql(t["query"]))
            except Exception as e:  # 编译 SQL 抓取失败不崩：答案已到手，SQL 留注释占位
                sqls.append(f"-- table[{i}] 编译 SQL 抓取失败: {str(e)[:200]}")
                failed_fetch += 1
        if sqls:
            sql = "\n\n".join(sqls).split("\n\n")[0].split("\n", 1)[-1]  # 首表 SQL（去注释行）
            sql_count = len(sqls) - failed_fetch
        (runs_dir / f"{qid}.sql.txt").write_text("\n\n".join(sqls), encoding="utf-8")

    elapsed = round(time.time() - t0, 1)
    raw = {
        "session_id": session_id,
        "question": question,
        "first": {"elapsed_sec": round(elapsed, 1), "response": first},
        "followups": followups,
        "error_chain": err,
    }
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    first_type = (first or {}).get("type", "error") if first else "error"
    final_resp = first if first_type != "ask" else (followups[-1]["response"] if followups else None)
    card = build_card(
        qid, question, first_type, first or {}, followups, final_resp or {},
        elapsed_s=elapsed, raw_path=str(raw_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        sql=sql, sql_count=sql_count,
    )
    from schemas.validator import validate_card
    validate_card(card, where="（ask_cube 写卡前）")
    return {"card": card, "first_type": first_type, "raw_rel": str(raw_path)}


def _ask_with_retry(question: str, session_id: str, attempts: int = 3, backoff_s: float = 20.0):
    """首答（失败换新 sessionId 重试，指数式观察上游 502）+ ask 态自动拍板追问。

    上游（Claude API 代理）有间歇 502（v0 q13 同款），故比 v0 的单次重试更耐一点。
    """
    first, followups, err = None, [], ""
    for i in range(attempts):
        sid = session_id if i == 0 else f"{session_id}-r{i + 1}"
        try:
            first = client.post_chat(question, sid)
            err = ""
            break
        except Exception as e:
            err = (err + " | " if err else "") + str(e)[:300]
            if i < attempts - 1:
                time.sleep(backoff_s * (i + 1))
    if first is None:
        return None, [], err

    if isinstance(first, dict) and first.get("type") == "ask":
        msg = policy.followup_message(first)
        try:
            fu_resp = client.post_chat(msg, session_id)
            followups.append({"question": msg, "response_type": fu_resp.get("type", "?"),
                              "response": fu_resp})
        except Exception as e:
            followups.append({"question": msg, "response_type": "exception",
                              "response": {"type": "error", "error": str(e)[:300]}})
    return first, followups, err
