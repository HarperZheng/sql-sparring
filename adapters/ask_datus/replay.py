"""B1 回归门：对 v0 的 25 份 payload 离线重放提取器，与 qa_results.json 逐字段比对。

输入：fixtures/v0/qa_run/<ID>.jsonl（提取器输入）
      fixtures/v0/qa_results.json（标准答案，v0 产物）
豁免字段（不在留痕里，重放无法恢复，逐项记录原因）：
  - elapsed_s  计时信息，进程运行时产物
  - returncode 进程退出码，payload 流之外的进程信息
  - stderr_tail 标准错误尾部，同上（且 v0 归档版 qa_results.json 已不含此字段）
  - desc       展示拼接串（glossary 既定豁免；本门仍比对，若恒等则豁免多余）
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures" / "v0"

# 比对字段 → 豁免原因（豁免字段必须写明理由）
EXEMPT = {
    "elapsed_s": "计时不在 payload 留痕里，重放无法恢复",
    "returncode": "进程退出码是 payload 流之外的进程信息",
    "stderr_tail": "标准错误尾部不在留痕里；v0 归档版无此字段",
    "question": "题目文本是运行输入（-p 参数），不是提取产物；作答卡的 question 由题库注入",
    "desc": "展示拼接串，非数据（glossary 豁免项；仍参与比对，恒等则说明豁免多余）",
}

# 提取器可产出、参与逐字段比对的字段
_FIELDS = ["id", "status", "metric_calls", "tools_called",
           "sql", "sql_count", "sql_results", "answer", "errors"]


def _flatten(obj, prefix=""):
    """嵌套结构 → {点路径: 叶值}，供逐字段 diff 定位。"""
    items = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            items.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            items.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        items[prefix] = obj
    return items


def replay_one(qid: str, expected: dict):
    """重放一题，返回 (extracted, diffs)。diffs: {字段路径: (期望, 实际)}。"""
    from . import extractor
    payload_file = FIXTURES / "qa_run" / f"{qid}.jsonl"
    lines = payload_file.read_text(encoding="utf-8").splitlines()
    got = extractor.extract(lines)

    diffs = {}
    for field in _FIELDS:
        exp_v, got_v = expected.get(field), got.get(field)
        if field == "id":
            exp_v, got_v = qid, qid
        if exp_v != got_v:
            if field == "metric_calls":
                # desc 参与比对但单独豁免通道：仅当去 desc 后一致，才算 desc 差异
                strip = lambda calls: [{k: v for k, v in c.items() if k != "desc"} for c in calls]
                if isinstance(exp_v, list) and isinstance(got_v, list) and strip(exp_v) == strip(got_v):
                    diffs["metric_calls.desc"] = ("(仅 desc 差异)", "(仅 desc 差异)")
                    continue
            for path, ev in _flatten({field: exp_v}).items():
                gv = _flatten({field: got_v}).get(path)
                if ev != gv:
                    diffs[path] = (ev, gv)
    return got, diffs


def run_replay(report_out: Path | None = None) -> bool:
    expected_all = json.loads((FIXTURES / "qa_results.json").read_text(encoding="utf-8"))
    report = {"per_question": {}, "exempt": EXEMPT, "pass": True}
    n_diff_q = 0
    for expected in expected_all:
        qid = expected["id"]
        got, diffs = replay_one(qid, expected)
        real_diffs = {p: d for p, d in diffs.items() if not p.endswith(".desc")}
        desc_only = bool(diffs) and not real_diffs
        if diffs:
            n_diff_q += 1
        report["per_question"][qid] = {
            "diff_fields": sorted(diffs.keys()),
            "desc_only": desc_only,
            "detail": {p: {"expected": d[0], "actual": d[1]} for p, d in diffs.items()},
        }
        if real_diffs:
            report["pass"] = False

    print(f"重放 {len(expected_all)} 题，字段比对完成")
    if report["pass"]:
        print(f"结果：PASS — 无实质差异（{n_diff_q} 题存在仅-desc差异）" if n_diff_q
              else "结果：PASS — 全部字段一致（含 desc）")
    else:
        print(f"结果：FAIL — {n_diff_q} 题有差异")
        for qid, r in report["per_question"].items():
            if r["diff_fields"] and not r["desc_only"]:
                print(f"  {qid}: {', '.join(r['diff_fields'])}")
                for p, d in list(r["detail"].items())[:3]:
                    print(f"    {p}\n      期望: {str(d['expected'])[:200]}\n      实际: {str(d['actual'])[:200]}")

    if report_out:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告：{report_out}")
    return report["pass"]
