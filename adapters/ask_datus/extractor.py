"""payload 提取器：MessagePayload JSONL 流 → 结构化作答要素。

提取规格 = docs/问数双智能体互搏设计.md §2.2：

| 要提取     | 来源                                                                 |
|------------|----------------------------------------------------------------------|
| SQL        | call-tool 中 toolName=execute_sql 的 toolParams.sql；另有 code(codeType=sql) 块 |
| 命中指标   | query_metrics / search_metrics / get_metric 的参数与返回（search_semantic_objects 只记 tools_called） |
| 执行结果   | call-tool-result 的 result.result.data.compressed_data（CSV 预览 8 行） |
| 最终答案   | depth-0 的 assistant markdown 内容（取最后一条）                       |
| 真实错误   | call-tool-result 的 error 字段（正文 "Code NNN" 是 KB 文本，勿扫全文）  |

字段口径经 M0 活跑实测校准（rounds/m0/runs/datus/）。
"""

import json
import re

CSV_PREVIEW_LINES = 8

# 进 pending 等结果回配的工具（search_semantic_objects 亦入 pending，但其结果不进 metric_calls）
_PENDING_TOOLS = ("query_metrics", "search_metrics", "get_metric", "search_semantic_objects")
_CODE_ERR_RE = re.compile(r'Code \d+[^"]{0,120}')


def _csv_preview(data):
    """查询结果 data 字典 → CSV 预览（压缩结果只给行数摘要）。"""
    if not isinstance(data, dict):
        return ""
    csv = str(data.get("compressed_data") or "")
    if data.get("is_compressed"):
        rows = data.get("original_rows")
        return f"({rows} rows, compressed)" if rows else "(compressed)"
    lines = [ln for ln in csv.splitlines() if ln.strip()]
    if not lines:
        return ""
    if len(lines) > CSV_PREVIEW_LINES:
        lines = lines[:CSV_PREVIEW_LINES] + [f"... 共 {data.get('original_rows')} 行"]
    return "\n".join(lines)


def _result_rows(pl):
    """call-tool-result payload → 结果数据预览。"""
    result = pl.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return ""
    if isinstance(result, dict):
        inner = result.get("result")
        if isinstance(inner, dict):
            return _csv_preview(inner.get("data") or {})
    return ""


def _names_of(params):
    """query_metrics 形参里的指标名列表。"""
    names = params.get("metrics") or []
    return [str(n) for n in names if n]


def _qm_extras(params):
    """query_metrics 调用实参里的维度与时间范围（条件添加：无则不带键）。"""
    extras = {}
    if params.get("dimensions"):
        extras["dimensions"] = [str(x) for x in params["dimensions"] if x]
    if params.get("time_start") or params.get("time_end"):
        extras["time_start"] = params.get("time_start")
        extras["time_end"] = params.get("time_end")
    return extras


def _describe_call(tool, params):
    """指标类工具调用的一行描述（仅 B1 兼容与人工阅读用，作答卡不带）。"""
    bits = []
    if params.get("metrics"):
        bits.append("指标=" + "、".join(_names_of(params)))
    if params.get("dimensions"):
        bits.append("维度=" + "、".join(str(d) for d in params["dimensions"] if d))
    if params.get("time_start") or params.get("time_end"):
        bits.append(f"时间={params.get('time_start') or '…'}~{params.get('time_end') or '…'}")
    if params.get("time_granularity"):
        bits.append(f"粒度={params['time_granularity']}")
    if params.get("query_text"):
        bits.append(f"检索={params['query_text']}")
    if not bits:
        blob = json.dumps(params, ensure_ascii=False)
        bits.append(blob[:160])
    return f"{tool}: " + "; ".join(bits)


def _derive_status(errors, sqls, answers, metric_calls):
    """状态七分支（与 v0 一致；超时分支由驱动层在传入前处理）。"""
    if errors:
        return "报错: " + " | ".join(dict.fromkeys(errors[-3:]))
    if sqls and answers:
        return "成功"
    if sqls:
        return "有SQL无最终答案"
    if answers and metric_calls:
        return "成功(指标路径)"
    if answers:
        return "有答案无SQL"
    return "无输出"


def extract(lines, timed_out=False, timeout_s=None):
    """payload 行序列 → 提取结果字典。

    lines：stdout 逐行（可为已 splitlines 的列表或文件迭代器）。
    timed_out/timeout_s：仅驱动超时分支使用，常规提取时缺省。
    """
    sqls, sql_results, answers, errors = [], [], [], []
    metric_calls, tools_called = [], []
    pending = {}  # callToolId -> (tool, params, depth)

    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        depth = payload.get("depth", 0)
        role = payload.get("role")
        for c in payload.get("content") or []:
            ctype, pl = c.get("type"), c.get("payload") or {}
            tool = str(pl.get("toolName", ""))
            if ctype == "call-tool":
                params = pl.get("toolParams") or {}
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except json.JSONDecodeError:
                        params = {"raw": params}
                tools_called.append(f"{tool}@d{depth}" if depth else tool)
                if tool == "execute_sql":
                    if params.get("sql"):
                        sqls.append(str(params["sql"]))
                elif tool in _PENDING_TOOLS:
                    pending[pl.get("callToolId", "")] = (tool, params, depth)
            elif ctype == "call-tool-result":
                err = pl.get("error")
                if err:
                    errors.extend(m.strip() for m in _CODE_ERR_RE.findall(str(err)))
                info = pending.pop(pl.get("callToolId", ""), None)
                rows = _result_rows(pl)
                if info:
                    tool, params, d = info
                    if tool == "query_metrics":
                        metric_calls.append({
                            "tool": tool, "depth": d,
                            "desc": _describe_call(tool, params),
                            "names": _names_of(params), "rows": rows,
                            **_qm_extras(params),
                        })
                    elif tool == "search_metrics":
                        names = []
                        result = pl.get("result")
                        if isinstance(result, dict):
                            items = result.get("result") or []
                            if isinstance(items, list):
                                names = [str(m.get("name")) for m in items
                                         if isinstance(m, dict) and m.get("name")]
                        metric_calls.append({
                            "tool": tool, "depth": d,
                            "desc": _describe_call(tool, params),
                            "names": names, "rows": "",
                        })
                    elif tool == "get_metric":
                        name = params.get("name") or params.get("metric_name") or ""
                        metric_calls.append({
                            "tool": tool, "depth": d,
                            "desc": f"get_metric: {name}",
                            "names": [str(name)] if name else [],
                            "rows": rows,
                        })
                elif tool == "execute_sql" and rows:
                    sql_results.append(rows)
            elif ctype == "code" and pl.get("codeType") == "sql" and pl.get("content"):
                sqls.append(str(pl["content"]))
            elif ctype == "markdown" and role == "assistant" and depth == 0 and pl.get("content"):
                answers.append(str(pl["content"]))

    # 有调用无结果（工具抛错早于返回）仍计为指标使用
    for tool, params, d in pending.values():
        entry = {"tool": tool, "depth": d, "desc": _describe_call(tool, params),
                 "names": _names_of(params), "rows": "(无返回)"}
        if tool == "query_metrics":
            entry.update(_qm_extras(params))
        metric_calls.append(entry)

    if timed_out:
        status = f"超时({timeout_s}s，部分输出)"
    else:
        status = _derive_status(errors, sqls, answers, metric_calls)

    return {
        "status": status,
        "metric_calls": metric_calls,
        "tools_called": list(dict.fromkeys(tools_called)),
        "sql": sqls[-1] if sqls else "",
        "sql_count": len(sqls),
        "sql_results": sql_results,
        "answer": answers[-1] if answers else "",
        "errors": list(dict.fromkeys(errors))[-5:],
    }
