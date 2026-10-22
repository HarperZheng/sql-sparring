"""Batch NL-QA runner: drives `datus -p` over the 25 questions from doc 08
(08-fne_fund_main自然语言问数能回答的问题.md), recording question / matched metrics /
generated SQL / answer / error codes per question.

Extraction sources (MessagePayload JSON lines on stdout):
    execute_sql call-tool        -> generated SQL (toolParams.sql)
    execute_sql call-tool-result -> result rows preview (CSV)
    query_metrics call-tool      -> metric names + dimensions + time range (命中指标)
    query_metrics result         -> metric execution rows preview (CSV)
    search_metrics / get_metric  -> retrieval query + matched metric names
    depth-0 assistant markdown   -> final user-facing answer
    any call-tool-result blob    -> ClickHouse "Code NNN" error fragments

Usage (WSL, from the Datus-agent repo root):
    .venv/bin/python /mnt/d/develop/datus/tmp/run_qa.py                # all 25 questions
    .venv/bin/python /mnt/d/develop/datus/tmp/run_qa.py A1 A5 E1       # subset by id
    TIMEOUT_S=600 .venv/bin/python /mnt/d/develop/datus/tmp/run_qa.py  # override timeout

Outputs:
    /mnt/d/develop/datus/tmp/qa_run/<ID>.jsonl   raw MessagePayload stream (audit trail)
    /mnt/d/develop/datus/tmp/qa_summary.md       human-readable record (question/metrics/SQL/answer)
    /mnt/d/develop/datus/tmp/qa_results.json     machine-readable results
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/mnt/d/develop/datus/Datus-agent")
OUT_DIR = Path("/mnt/d/develop/datus/tmp/qa_run")
TIMEOUT_S = int(os.environ.get("TIMEOUT_S", "900"))
CSV_PREVIEW_LINES = 8

# (id, category, question) — from 08-fne_fund_main自然语言问数能回答的问题.md
QUESTIONS = [
    ("A1", "总量趋势", "2022年全年非税缴款金额和笔数是多少？"),
    ("A2", "总量趋势", "非税缴款金额按月展示，并给出每月环比"),
    ("A3", "总量趋势", "清分金额2022年对比2021年同比增长多少？"),
    ("A4", "总量趋势", "缴库金额按年汇总，2022到2026各年是多少？"),
    ("A5", "总量趋势", "全库累计清分了多少金额、清分率是多少？"),
    ("B1", "单位维度", "2022年缴款金额排名前10的执收单位有哪些？"),
    ("B2", "单位维度", "测试云南省教育厅1直属下级单位合计缴款金额是多少？"),
    ("B3", "单位维度", "各执收预算单位2022年的清分金额对比"),
    ("B4", "单位维度", "哪些非叶子单位自己直接收了款？各收了多少？"),
    ("B5", "单位维度", "按执收单位统计未到账的缴款笔数"),
    ("C1", "科目项目", "各预算科目清分金额排行，政府性基金收入103大类下哪些叶子科目收得最多？"),
    ("C2", "科目项目", "民航发展基金历年缴款金额趋势"),
    ("C3", "科目项目", "按收入分类统计缴款金额：政府性基金收入、专项收入、行政事业性收费收入、罚没收入各占多少？"),
    ("C4", "科目项目", "按资金性质分组统计缴款金额"),
    ("C5", "科目项目", "缴款金额前5的收费项目，按直缴汇缴拆分展示"),
    ("D1", "区划银行", "按归属区划统计清分金额"),
    ("D2", "区划银行", "按执收区划名称统计缴款金额"),
    ("D3", "区划银行", "五华区的执收单位有哪些、各收了多少钱？"),
    ("D4", "区划银行", "各收款银行2022年各收了多少笔、多少钱？"),
    ("D5", "区划银行", "归属区划在云南省本级以外的缴款金额有多少？"),
    ("E1", "链路状态", "已划拨和未划拨的金额各是多少？"),
    ("E2", "链路状态", "缴库报文里已确认入库和待国库确认的金额各是多少？"),
    ("E3", "链路状态", "汇总批次一共多少个？"),
    ("E4", "链路状态", "未清分的缴款笔数和金额是多少？"),
    ("E5", "链路状态", "清分率按业务类型分组对比：直缴和汇缴各是多少？"),
]


def _csv_preview(data):
    """Preview rows from a query result `data` dict (original_rows + CSV payload)."""
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
    """Pull the result-data preview out of a call-tool-result payload."""
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
    """Metric/dimension names out of query_metrics-style params."""
    names = params.get("metrics") or []
    return [str(n) for n in names if n]


def _describe_call(tool, params):
    """Human-readable one-liner of a metric-related tool call."""
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
    if not bits:  # unknown shape — dump compact params
        blob = json.dumps(params, ensure_ascii=False)
        bits.append(blob[:160])
    return f"{tool}: " + "; ".join(bits)


def extract(lines):
    """Pull answers, metric calls, SQL + results, tool calls, and CH error codes."""
    sqls, sql_results, answers, errors = [], [], [], []
    metric_calls, tools_called = [], []
    pending = {}  # callToolId -> (tool, params)
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
                elif tool in ("query_metrics", "search_metrics", "get_metric", "search_semantic_objects"):
                    pending[pl.get("callToolId", "")] = (tool, params, depth)
            elif ctype == "call-tool-result":
                err = pl.get("error")
                if err:
                    errors.extend(m.strip() for m in re.findall(r"Code \d+[^\"]{0,120}", str(err)))
                info = pending.pop(pl.get("callToolId", ""), None)
                rows = _result_rows(pl)
                if info:
                    tool, params, d = info
                    if tool == "query_metrics":
                        metric_calls.append({
                            "tool": tool,
                            "depth": d,
                            "desc": _describe_call(tool, params),
                            "names": _names_of(params),
                            "rows": rows,
                        })
                    elif tool == "search_metrics":
                        names = []
                        result = pl.get("result")
                        if isinstance(result, dict):
                            items = result.get("result") or []
                            if isinstance(items, list):
                                names = [str(m.get("name")) for m in items if isinstance(m, dict) and m.get("name")]
                        metric_calls.append({
                            "tool": tool,
                            "depth": d,
                            "desc": _describe_call(tool, params),
                            "names": names,
                            "rows": "",
                        })
                    elif tool == "get_metric":
                        name = params.get("name") or params.get("metric_name") or ""
                        metric_calls.append({
                            "tool": tool,
                            "depth": d,
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
    # unmatched pending calls (tool raised before result) still count as metric usage
    for tool, params, d in pending.values():
        metric_calls.append({"tool": tool, "depth": d, "desc": _describe_call(tool, params),
                             "names": _names_of(params), "rows": "(无返回)"})
    return sqls, sql_results, answers, errors, metric_calls, tools_called


def run_one(qid, question):
    t0 = time.time()
    rc, lines, stderr_tail = None, [], ""
    try:
        proc = subprocess.run(
            [str(ROOT / ".venv/bin/datus"), "-p", question],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            encoding="utf-8",
            errors="replace",
        )
        rc = proc.returncode
        lines = proc.stdout.splitlines()
        stderr_tail = proc.stderr[-1500:]
    except subprocess.TimeoutExpired as exc:
        rc = "TIMEOUT"
        stdout = exc.stdout
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        lines = (stdout or "").splitlines()
    elapsed = round(time.time() - t0, 1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{qid}.jsonl").write_text("\n".join(lines), encoding="utf-8")

    sqls, sql_results, answers, errors, metric_calls, tools_called = extract(lines)
    if rc == "TIMEOUT":
        status = f"超时({TIMEOUT_S}s，部分输出)"
    elif errors:
        status = "报错: " + " | ".join(dict.fromkeys(errors[-3:]))
    elif sqls and answers:
        status = "成功"
    elif sqls:
        status = "有SQL无最终答案"
    elif answers and metric_calls:
        status = "成功(指标路径)"
    elif answers:
        status = "有答案无SQL"
    else:
        status = "无输出"

    return {
        "id": qid,
        "question": question,
        "status": status,
        "returncode": str(rc),
        "elapsed_s": elapsed,
        "metric_calls": metric_calls,
        "tools_called": list(dict.fromkeys(tools_called)),
        "sql": sqls[-1] if sqls else "",
        "sql_count": len(sqls),
        "sql_results": sql_results,
        "answer": answers[-1] if answers else "",
        "errors": list(dict.fromkeys(errors))[-5:],
        "stderr_tail": stderr_tail,
    }


def write_summary(results):
    cats = {q[0]: q[1] for q in QUESTIONS}
    md = ["# fne_fund_main 问数执行记录（自动生成）", "",
          f"- 执行时间：{time.strftime('%Y-%m-%d %H:%M:%S')} | 超时 {TIMEOUT_S}s/题 | 引擎：datus -p（GLM-5.3-Flash 经 relay，数据源 yunnan0508/CH23.3）",
          "- 原始 payload 留档：tmp/qa_run/<ID>.jsonl", "",
          "## 总览", "",
          "| ID | 分类 | 问题 | 状态 | 耗时s |", "|---|---|---|---|---:|"]
    for r in results:
        md.append(f"| {r['id']} | {cats[r['id']]} | {r['question']} | {r['status']} | {r['elapsed_s']} |")
    md.append("")
    ok = sum(1 for r in results if r["status"].startswith("成功"))
    md.append(f"**成功 {ok} / {len(results)}**")
    md.append("")
    for r in results:
        md.append(f"## {r['id']} {r['question']}")
        md.append("")
        md.append(f"- 状态：{r['status']}（returncode={r['returncode']}，SQL次数={r['sql_count']}，耗时 {r['elapsed_s']}s）")
        if r.get("metric_calls"):
            md.append("- **命中指标**：")
            for m in r["metric_calls"]:
                depth = f"（子代理）" if m.get("depth") else ""
                md.append(f"  - {m['desc']}{depth}")
                if m.get("rows"):
                    md.append(f"    - 返回：`{m['rows'].splitlines()[0]}`" if "\n" not in m["rows"]
                              else "    - 返回：\n      ```\n      " + "\n      ".join(m["rows"].splitlines()) + "\n      ```")
        else:
            md.append("- **命中指标**：（未走指标/检索路径）")
        if r.get("tools_called"):
            md.append(f"- 工具调用：{' → '.join(r['tools_called'])}")
        md.append("- **SQL**：")
        if r["sql"]:
            md.append("```sql")
            md.append(r["sql"])
            md.append("```")
        else:
            md.append("（无 execute_sql 直查）")
        for rows in (r.get("sql_results") or [])[:1]:
            md.append("- SQL 返回：")
            md.append("```")
            md.append(rows)
            md.append("```")
        md.append("- **答案**：")
        if r["answer"]:
            md.append("> " + r["answer"].replace("\n", "\n> "))
        else:
            md.append("（无）")
        if r["errors"]:
            md.append("- **错误**：" + "；".join(r["errors"]))
        md.append("")
    Path("/mnt/d/develop/datus/tmp/qa_summary.md").write_text("\n".join(md), encoding="utf-8")
    Path("/mnt/d/develop/datus/tmp/qa_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    subset = set(sys.argv[1:])
    todo = [q for q in QUESTIONS if not subset or q[0] in subset]
    results = []
    for i, (qid, cat, question) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {qid} {question}", flush=True)
        r = run_one(qid, question)
        print(f"    -> {r['status']} ({r['elapsed_s']}s)", flush=True)
        results.append(r)
        write_summary(results)  # incremental: safe to Ctrl-C midway
    print(f"\nDone: {sum(1 for r in results if r['status'].startswith('成功'))}/{len(results)} 成功")


if __name__ == "__main__":
    main()
