"""cube 侧作答卡组装（11 字段，与 ask_datus 同构；契约=schemas/answer_card.schema.json）。

答案唯一载体=值行 values（D14）：散文由 adapters/value_extract.py 结构化后传入，
卡上不再落 answer 散文（散文全文在 runs/ 留痕，raw_path 指认）。
status 取**终态**：ask 经自动拍板拿到 answer → status=answer、arbiter 记录拍板全程；
首答即 answer/nomatch → arbiter 为 null。首答三态由留痕与 arbiter.first_type 记载，
裁决时"自动拍板"与"人拍板"区分对待（§三）。
"""

_FINAL_FROM_FIRST = {"answer": "answer", "nomatch": "nomatch"}


def build_card(qid, question, first_type, first_resp, followups, final_resp,
               values, elapsed_s, raw_path, sql, sql_count) -> dict:
    status = _FINAL_FROM_FIRST.get(first_type)
    arbiter = None
    errors = []

    if first_type == "ask":
        end = (final_resp or {}).get("type")
        status = {"answer": "answer", "ask": "ask", "nomatch": "nomatch"}.get(end, "failed")
        arbiter = {
            "mode": "auto",
            "policy": "option-1",
            "first_type": first_type,
            "ask_question": first_resp.get("question", ""),
            "options": first_resp.get("options") or [],
            "followups": followups,
        }
    elif first_type == "error":
        status = "failed"
        errors.append(str(first_resp.get("error", "unknown")))
    elif status is None:
        status = "failed"
        errors.append(f"未知首答类型: {first_type}")

    metrics_hit = []
    for t in (final_resp or {}).get("tables") or []:
        q = t.get("query") or {}
        if q.get("measures") or q.get("dimensions"):
            metrics_hit.append({"measures": q.get("measures") or [],
                                "dimensions": q.get("dimensions") or []})

    return {
        "id": qid,
        "question": question,
        "status": status,
        "metrics_hit": metrics_hit,
        "sql": sql,
        "sql_count": sql_count,
        "values": values if status == "answer" else [],
        "errors": errors,
        "elapsed_s": elapsed_s,
        "arbiter": arbiter,
        "raw_path": raw_path,
    }
