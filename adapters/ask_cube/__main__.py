"""ask_cube CLI 入口。

用法（Windows 侧 uv 环境）：
  uv run python -m adapters.ask_cube replay-v0 [--only q01 q07]
      A3：v0 30 题活重放（打 :4100 活服务），首答三态比对 fixtures/v0/cube/tmp-nlq1021/status.json
  uv run python -m adapters.ask_cube run --questions rounds/m0/questions-cube.jsonl [--only cn1]
      活跑任意题库（JSONL：{id, question}）
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

from .driver import REPO_ROOT, run_question

FIXTURE_DIR = REPO_ROOT / "fixtures" / "v0" / "cube" / "tmp-nlq1021" / "nlq-1021"
FIXTURE_STATUS = FIXTURE_DIR / "status.json"
FIXTURE_QUESTIONS = FIXTURE_DIR / "questions.json"

# v0 q13 是瞬时 502（链路故障非数据问题，09-cube 记录已恢复完整答案），允许翻转为 answer
EXPECTED_TRANSIENT = {"q13": "v0 为瞬时 502 链路故障，answer 为合理复原"}

# 硬锚点：字面三态必须保持（nomatch 不得消失）
HARD_ANCHORS = {"q07", "q09"}
# 边界锚点 q30（2026-10-22 实测修订）：「退付金额」未建模这一事实不得消失。
# 字面 nomatch 锚点过严——实测首答变 ask 且明示退付未建模、经拍板按到账口径出
# 明细，是边界表达精细化而非能力突破；直接 answer（无拍板硬算退付）才是锚点失效。
BOUNDARY_ANCHOR_Q30 = "退付"

# (v0类型, 本次类型) → 判定。词典回写演化=预期内（v0 拍板已落活词典，服务不再反问）；
# 退化对=FAIL（能力倒退）；其余差异单列待查。
# ("answer","ask") 不在此表：首答变反问要看拍板追问是否成功（查 raw 留痕），
# 追问出答案=口径反问闭环（行为漂移非退化），追问失败才是退化。
_FLIP_VERDICTS = {
    ("ask", "answer"): "词典回写演化（v0 拍板已落词典，无需再反问）",
    ("nomatch", "answer"): "语义层增强（原能力外变可答）——单列待查",
    ("nomatch", "ask"): "语义层增强（可反问拍板）——单列待查",
    ("answer", "nomatch"): "退化：answer 变 nomatch",
}


def _followup_ok(qid: str) -> bool:
    """qid 首答变反问后，自动拍板追问是否成功出答案（证据=raw 留痕 followups）。"""
    raw = REPO_ROOT / "rounds" / "m0" / "runs" / "cube" / f"{qid}.raw.json"
    try:
        data = json.loads(raw.read_text(encoding="utf-8"))
        fus = data.get("followups") or []
        return bool(fus) and fus[0].get("response_type") == "answer"
    except (OSError, json.JSONDecodeError):
        return False


def _q30_boundary_ok() -> bool:
    """q30 边界锚点：首答 ask 是否明示退付未建模（无对应成员/无词条/未建模）。"""
    raw = REPO_ROOT / "rounds" / "m0" / "runs" / "cube" / "q30.raw.json"
    try:
        data = json.loads(raw.read_text(encoding="utf-8"))
        text = json.dumps((data.get("first") or {}).get("response") or {}, ensure_ascii=False)
        return BOUNDARY_ANCHOR_Q30 in text and any(
            w in text for w in ("未建模", "无对应成员", "无该词条"))
    except (OSError, json.JSONDecodeError):
        return False


def _write_card(answers_dir: Path, card: dict) -> Path:
    answers_dir.mkdir(parents=True, exist_ok=True)
    out = answers_dir / f"{card['id']}.json"
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _run_set(questions: list, runs_dir: Path, answers_dir: Path, session_prefix: str, only: set):
    todo = [q for q in questions if not only or q["id"] in only]
    results = []
    for i, q in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {q['id']} {q['question']}", flush=True)
        r = run_question(q["id"], q["question"], session_prefix, runs_dir)
        _write_card(answers_dir, r["card"])
        print(f"    -> {r['first_type']} -> {r['card']['status']} ({r['card']['elapsed_s']}s)", flush=True)
        results.append(r)
    return results


def cmd_replay_v0(args):
    """A3：30 题活重放 + 首答三态比对。sessionId 前缀带日期戳，不复用 v0 会话。

    --only 子集重跑时与既有报告合并（新结果覆盖旧值，未重跑题沿用上次结果）。
    --report-only 不打服务，仅按既有报告 + raw 留痕重算判定（锚点/拍板证据在 raw）。
    """
    questions = [{"id": x["id"], "question": x["q"]}
                 for x in json.loads(FIXTURE_QUESTIONS.read_text(encoding="utf-8"))]
    v0 = {e["id"]: e.get("type") for e in json.loads(FIXTURE_STATUS.read_text(encoding="utf-8"))}
    only = set() if args.report_only else set(args.only or [])
    stamp = time.strftime("%m%d")
    m0_dir = REPO_ROOT / "rounds" / "m0"
    results = [] if args.report_only else _run_set(
        questions, m0_dir / "runs" / "cube", m0_dir / "answers" / "cube",
        session_prefix=f"a3{stamp}", only=only)

    got = {r["card"]["id"]: r["first_type"] for r in results}
    report_out = m0_dir / "a3_replay_report.json"
    prev = {}
    if report_out.exists():
        try:
            prev = json.loads(report_out.read_text(encoding="utf-8")).get("per_question", {})
        except json.JSONDecodeError:
            prev = {}
    for qid, entry in prev.items():
        if qid not in got and qid not in only:
            got[qid] = entry.get("got", "(未跑)")

    rows, hard_diff, evolved, pending = [], [], [], []
    for qid, v0_type in v0.items():
        g = got.get(qid, "(未跑)")
        if g == v0_type:
            verdict = "一致"
        elif qid in EXPECTED_TRANSIENT and g != "error":
            verdict = f"预期内翻转（{EXPECTED_TRANSIENT[qid]}）"
        elif qid in HARD_ANCHORS and g != "nomatch":
            verdict = f"锚点失效：{qid} 必须 nomatch"
            hard_diff.append(qid)
        elif qid == "q30" and v0_type == "nomatch" and g != "nomatch":
            if g == "ask" and _q30_boundary_ok():
                verdict = "边界锚点保持（退付未建模已明示，拍板后按到账口径出明细）"
                evolved.append(qid)
            else:
                verdict = "锚点失效：退付未建模边界消失（直接 answer 或未明示）"
                hard_diff.append(qid)
        elif v0_type == "answer" and g == "ask":
            if _followup_ok(qid):
                verdict = "口径反问→自动拍板闭环（追问已出答案，行为漂移非退化）"
                evolved.append(qid)
            else:
                verdict = "退化：变反问且拍板未成功"
                hard_diff.append(qid)
        elif (v0_type, g) in _FLIP_VERDICTS:
            verdict = _FLIP_VERDICTS[(v0_type, g)]
            if verdict.startswith("退化"):
                hard_diff.append(qid)
            else:
                evolved.append(qid)
        else:
            verdict = "未归类差异——单列待查"
            pending.append(qid)
        rows.append((qid, v0_type, g, verdict))

    print("\n=== A3 三态比对（首答）===")
    print(f"{'id':<5}{'v0':<10}{'本次':<10}判定")
    for qid, v0t, g, verdict in rows:
        print(f"{qid:<5}{v0t:<10}{g:<10}{verdict}")
    dist = Counter(g for _, _, g, _ in rows)
    v0_dist = Counter(v0t for _, v0t, _, _ in rows)
    print(f"\n分布：v0={dict(v0_dist)} 本次={dict(dist)}")
    if evolved:
        print(f"拍板/演化类翻转 {len(evolved)} 题：{', '.join(evolved)}（逐题判定见上表）")
    if pending:
        print(f"未归类差异 {len(pending)} 题：{', '.join(pending)}")
    ok = not hard_diff
    print(f"结果：{'PASS' if ok else 'FAIL — 锚点失效/能力退化: ' + ', '.join(hard_diff)}")

    report = {"per_question": {q: {"v0": v, "got": g, "verdict": c} for q, v, g, c in rows},
              "v0_dist": dict(v0_dist), "got_dist": dict(dist),
              "expected_transient": EXPECTED_TRANSIENT, "pass": ok}
    out = report_out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告：{out}")
    sys.exit(0 if ok else 1)


def cmd_run(args):
    questions = [json.loads(l) for l in Path(args.questions).read_text(encoding="utf-8").splitlines() if l.strip()]
    m0_dir = Path(args.questions).parent
    _run_set(questions, m0_dir / "runs" / "cube", m0_dir / "answers" / "cube",
             session_prefix=args.prefix, only=set(args.only or []))


def main():
    ap = argparse.ArgumentParser(prog="adapters.ask_cube")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("replay-v0", help="A3：v0 30 题活重放三态比对")
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--report-only", action="store_true",
                   help="不跑题，仅按既有报告+raw 留痕重算判定")
    p.set_defaults(func=cmd_replay_v0)

    p = sub.add_parser("run", help="活跑任意题库")
    p.add_argument("--questions", required=True)
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--prefix", default="m0q")
    p.set_defaults(func=cmd_run)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
