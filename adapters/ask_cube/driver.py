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

_ROW_CAP = 50  # 单表喂提取的行数上限（超出截断并注明；全量行永远在 raw 留痕可回查）


def _archive_existing(path: Path):
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archived = path.with_name(f"{path.stem}.{stamp}{path.suffix}")
    shutil.move(str(path), str(archived))
    return archived.name


def _tables_rows_text(tables: list) -> str:
    """tables[*].rows → 提取器可抄的结构化文本段（value=null 原样保留）。

    round-03 q16 实测：cube 答案散文只写口径与结论、数据行仅存 tables.rows，
    只喂散文提取会丢行（5 行丢 4）——故表格行随散文一并进提取输入，仍只抄数不推算。
    """
    parts = []
    for i, t in enumerate(tables or []):
        rows = t.get("rows") or []
        if not rows:
            continue
        note = f"（超{_ROW_CAP}行截断，仅前{_ROW_CAP}行）" if len(rows) > _ROW_CAP else ""
        title = t.get("title") or f"table[{i}]"
        parts.append(f"[查询返回表格·{title}·共{len(rows)}行{note}]\n"
                     + json.dumps(rows[:_ROW_CAP], ensure_ascii=False))
    if not parts:
        return ""
    return ("\n\n以下为查询实际返回的结构化行（与散文冲突时以行数据为准；只抄数不推算，"
            "value=null 表示该行无数）：\n" + "\n".join(parts))


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

    # 值行提取步（D14）：终答散文＋查询返回表格行（全文已留 raw.json）交 LLM 结构化为值行
    # （adapters/value_extract.py，模型走 conf/models.json extractor 节）；提取问题
    # 清单追加进卡 errors；失败降级 values=[]，不影响作答状态。
    values, vprobs = [], []
    if (final_resp or {}).get("type") == "answer":
        names = [m for t in final_resp.get("tables") or []
                 for m in ((t.get("query") or {}).get("measures") or [])]
        prose = (final_resp.get("answer") or "") + _tables_rows_text(final_resp.get("tables"))
        if prose.strip():
            from ..value_extract import extract_values
            values, vprobs = extract_values(question, prose, names)

    card = build_card(
        qid, question, first_type, first or {}, followups, final_resp or {},
        values, elapsed_s=elapsed, raw_path=str(raw_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        sql=sql, sql_count=sql_count,
    )
    if vprobs:
        card["errors"] = list(card.get("errors") or []) + vprobs
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


def reextract_question(qid: str, runs_dir: Path, answers_dir: Path) -> dict:
    """raw 留痕重产值行（不重答、不重问智能体）：散文＋表格行新提取输入，覆盖写卡。

    幂等与回退：旧卡先按时间戳归档再覆盖（回退=取归档文件）；status≠answer 跳过。
    """
    runs_dir, answers_dir = Path(runs_dir), Path(answers_dir)
    raw_path = runs_dir / f"{qid}.raw.json"
    card_path = answers_dir / f"{qid}.json"
    if not raw_path.exists() or not card_path.exists():
        return {"id": qid, "skipped": "缺 raw 或卡"}
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card.get("status") != "answer":
        return {"id": qid, "skipped": f"status={card.get('status')}"}
    first = raw.get("first") or {}
    first_resp = first.get("response") or {}
    followups = raw.get("followups") or []
    final_resp = first_resp if first_resp.get("type") != "ask" \
        else (followups[-1].get("response") if followups else None)
    if not final_resp or final_resp.get("type") != "answer":
        return {"id": qid, "skipped": "raw 无 answer 终答"}
    names = [m for t in final_resp.get("tables") or []
             for m in ((t.get("query") or {}).get("measures") or [])]
    prose = (final_resp.get("answer") or "") + _tables_rows_text(final_resp.get("tables"))
    if not prose.strip():
        return {"id": qid, "skipped": "散文与表格行皆空"}
    from ..value_extract import extract_values
    values, vprobs = extract_values(card["question"], prose, names)
    archived = _archive_existing(card_path)
    card["values"] = values
    if vprobs:
        card["errors"] = list(card.get("errors") or []) + vprobs
    from schemas.validator import validate_card
    validate_card(card, where="（ask_cube 重提取写卡前）")
    card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"id": qid, "values": len(values), "archived": archived, "problems": vprobs}
