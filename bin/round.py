"""bin/round.py — 一轮互搏的编排器（M3）：自动跑 SOP ①–⑥，到材料包即停（D6）。

流程（对每轮）：
  ① 出题      题库 rounds/<轮>/questions.jsonl 不存在时调 bin/examine.py；已存在则跳过
  ② 双侧作答  datus/cube 两适配器进程并行（接口、留痕目录互不相干；侧内仍逐题串行；
              已有卡自动跳过，断点续跑；每侧日志 runs/<侧>.runlog.txt）
  ③ 卡校验    两侧作答卡逐份对 Schema（复用 schemas/validator.py）
  ④ 裁决关口  verdicts/<id>.json 缺任一题 → 打印缺单清单并停（退出码 2），等人工裁决
  ⑤⑥ 轮报+材料包  全部裁决就绪后渲染 report.md + feedback/issues-{datus,cube}.md
               + suite-candidates.jsonl，即到轮终点（D6：不自动回灌）

用法（Windows 侧 uv 环境）：
  uv run python bin/round.py --round round-02                 # 全流程（①–⑥）
  uv run python bin/round.py --round round-02 --only q01 q21  # 小样/子集（不产轮报）
  uv run python bin/round.py --round round-03 --retest round-02   # M4：复验轮
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台缺省 GBK，中文输出转 UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from schemas.validator import check_cards_dir, check_verdicts_dir  # noqa: E402

SIDES = {"datus": "adapters.ask_datus", "cube": "adapters.ask_cube"}
NO_ANSWER_STATUSES = {"nomatch", "failed"}  # 共同缺口判定：两侧均此二态（implementation §四）


def load_questions(qpath: Path) -> dict[str, str]:
    out = {}
    for line in qpath.read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            out[q["id"]] = q["question"]
    return out


def run(cmd: list[str]) -> None:
    print(f"[round] $ {' '.join(str(c) for c in cmd)}", flush=True)
    rc = subprocess.run(cmd, cwd=REPO_ROOT).returncode
    if rc != 0:
        print(f"[round] 子命令失败（退出码 {rc}），终止", file=sys.stderr)
        sys.exit(1)


def step_examine(round_dir: Path, qpath: Path, name: str) -> None:
    if qpath.exists():
        n = len(load_questions(qpath))
        print(f"[①出题] 题库已存在，跳过（{qpath}，{n} 题）")
        return
    print("[①出题] 题库不存在，调 bin/examine.py …")
    run([sys.executable, str(REPO_ROOT / "bin" / "examine.py"),
         "--out", str(qpath), "--round", name])


def _log_tail(path: Path, n: int = 6) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [ln for ln in lines if ln.strip()][-n:]


def step_answer(round_dir: Path, qpath: Path, todo: list[str]) -> None:
    """双侧并行作答：datus/cube 接口互不相干（:8501 / :4100）、留痕目录分离，可安全并行；
    侧内仍逐题串行（题间隔离靠独立会话），并行只发生在侧与侧之间。
    任一侧失败不砍另一侧：两侧都跑完后统一报失败并退出码 1，已产卡保留（断点续跑可补）。"""
    procs: dict[str, tuple[subprocess.Popen, object]] = {}
    for side, module in SIDES.items():
        answers_dir = round_dir / "answers" / side
        missing = [qid for qid in todo if not (answers_dir / f"{qid}.json").exists()]
        if not missing:
            print(f"[②作答] {side}：{len(todo)} 卡齐全，跳过")
            continue
        log_path = round_dir / "runs" / f"{side}.runlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[②作答] {side}：待答 {len(missing)} 题（已有 {len(todo) - len(missing)} 卡）"
              f"→ 并行启动，日志 {log_path.name}")
        cmd = [sys.executable, "-m", module, "run", "--questions", str(qpath),
               "--only", *missing]
        print(f"[round] $ {' '.join(str(c) for c in cmd)}  > {log_path.name}", flush=True)
        log_f = log_path.open("w", encoding="utf-8")
        try:
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # 子进程输出统一 UTF-8，runlog 可读
            procs[side] = (subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=log_f,
                                            stderr=subprocess.STDOUT, env=env), log_f)
        except Exception:
            log_f.close()
            raise
    if not procs:
        return

    # 轮询进度：只数卡、不动进程；有变化才打一行
    last: dict[str, int] = {}
    while any(p.poll() is None for p, _ in procs.values()):
        time.sleep(20)
        counts = {s: len(list((round_dir / "answers" / s).glob("*.json"))) for s in procs}
        if counts != last:
            last = counts
            print("[②作答] 进行中 " + " · ".join(f"{s} {c}/{len(todo)}" for s, c in counts.items()),
                  flush=True)

    failed = []
    for side, (p, log_f) in procs.items():
        rc = p.wait()
        log_f.close()
        print(f"[②作答] {side} 结束：退出码 {rc}（日志尾部：）")
        for ln in _log_tail(round_dir / "runs" / f"{side}.runlog.txt"):
            print(f"    {side}| {ln}")
        if rc != 0:
            failed.append(side)
    if failed:
        print(f"[round] 作答失败侧：{'、'.join(failed)}（另一侧已产卡保留，断点续跑可补），终止",
              file=sys.stderr)
        sys.exit(1)


def check_cards(round_dir: Path, todo: list[str]) -> None:
    bad = False
    for side in SIDES:
        for fname, probs in check_cards_dir(round_dir / "answers" / side):
            print(f"[③校验] {side}/{fname}: {probs}", file=sys.stderr)
            bad = True
    for side in SIDES:
        answers_dir = round_dir / "answers" / side
        lack = [qid for qid in todo if not (answers_dir / f"{qid}.json").exists()]
        if lack:
            print(f"[③校验] {side} 缺卡：{lack}", file=sys.stderr)
            bad = True
    if bad:
        sys.exit(1)
    print(f"[③校验] 两侧 {len(todo)} 卡全过 Schema")


def load_verdicts(round_dir: Path, todo: list[str]) -> dict[str, dict]:
    verdicts_dir = round_dir / "verdicts"
    for fname, probs in check_verdicts_dir(verdicts_dir):
        print(f"[④裁决] {fname}: {probs}", file=sys.stderr)
        if probs:
            print("[④裁决] 裁决书不合 Schema，修正后重跑", file=sys.stderr)
            sys.exit(1)
    missing = [qid for qid in todo if not (verdicts_dir / f"{qid}.json").exists()]
    if missing:
        print(f"[④裁决] 裁决未完成：缺 {len(missing)} 份（{' '.join(missing)}）")
        print("[④裁决] 人工在环：对照 answers/<侧>/<id>.json 双侧卡逐题写 verdicts/<id>.json"
              "（Schema schemas/verdict.schema.json；D12：issues[] 记谁补建模/修bug）")
        sys.exit(2)
    extra = [f.stem for f in verdicts_dir.glob("*.json") if f.stem not in todo]
    if extra:
        print(f"[④裁决] 提示：verdicts/ 里存在不属于本轮的 {extra}")
    return {qid: json.loads((verdicts_dir / f"{qid}.json").read_text(encoding="utf-8"))
            for qid in todo}


# ---------- ⑤⑥ 轮报 + 材料包 ----------

def _issues_line(v: dict) -> str:
    parts = [f"{i['side']}·{i['type']}·{i['target']}" for i in v.get("issues") or []]
    return "；".join(parts) if parts else "—"


def _gap_pair(cards: dict[str, dict]) -> bool:
    st = {s: (cards[s] or {}).get("status") for s in SIDES}
    return all(st[s] in NO_ANSWER_STATUSES for s in SIDES)


def render_report(round_dir: Path, name: str, questions: dict, todo: list[str],
                  verdicts: dict, cards: dict) -> str:
    vc = Counter(v["verdict"] for v in verdicts.values())
    total = len(todo)
    passed = vc.get("互证通过", 0)
    gaps = [qid for qid in todo if _gap_pair({s: cards[s].get(qid) for s in SIDES})]
    status_lines = []
    for side in SIDES:
        sc = Counter((cards[side].get(qid) or {}).get("status", "?") for qid in todo)
        status_lines.append(f"| {side} | " + " / ".join(f"{k} {v}" for k, v in sorted(sc.items())) + " |")

    divergent = [qid for qid in todo if verdicts[qid]["verdict"] != "互证通过"]
    retest_round = f"round-{int(name.split('-')[1]) + 1:02d}"

    lines = [
        f"# {name} 轮报",
        "",
        f"- 日期：{date.today().isoformat()}　题数：{total}",
        "- 双侧作答状态：",
        *status_lines,
        "",
        "## 四指标",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| 一致率（互证通过/总题） | {passed}/{total} = {passed / total:.1%} |",
        f"| 分歧分布 | 建模差异 {vc.get('建模差异', 0)} / 执行事故 {vc.get('执行事故', 0)} / 待人工 {vc.get('待人工', 0)} |",
        f"| 差距数（双侧共同缺口） | {len(gaps)}（{' '.join(gaps) if gaps else '无'}） |",
        "| 闭环率 | —（首轮，无上轮分歧题） |",
        "",
        "## 分歧明细",
        "",
        "| id | 问题 | 裁决 | 问题单 |",
        "|---|---|---|---|",
    ]
    for qid in divergent:
        v = verdicts[qid]
        qtext = questions[qid] if len(questions[qid]) <= 30 else questions[qid][:29] + "…"
        lines.append(f"| {qid} | {qtext} | {v['verdict']} | {_issues_line(v)} |")
    lines += ["", f"## 复验集（默认进 {retest_round}）", "",
              "、".join(divergent) if divergent else "（无——全部互证通过）", ""]
    out = round_dir / "report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def render_feedback(round_dir: Path, name: str, questions: dict, todo: list[str],
                    verdicts: dict, cards: dict) -> list[Path]:
    fb_dir = round_dir / "feedback"
    fb_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    for side in SIDES:
        other = "cube" if side == "datus" else "datus"
        sec1, sec2, sec3, sec4 = [], [], [], []
        for qid in todo:
            v = verdicts[qid]
            mine = [i for i in (v.get("issues") or []) if i["side"] in (side, "both")]
            if _gap_pair({s: cards[s].get(qid) for s in SIDES}) and v["verdict"] != "互证通过":
                sec3 += [f"### {qid} {questions[qid]}", f"- {v['verdict_detail']}", ""]
            elif v["verdict"] == "建模差异":
                cd, cc = v["cards"]["datus"], v["cards"]["cube"]
                body = [f"### {qid} {questions[qid]}",
                        f"- 现象：{v['verdict_detail']}",
                        f"- {side} 口径：{cd.get('caliber', '—')}｜时间轴：{cd.get('time_axis', '—')}",
                        f"- {other} 口径：{cc.get('caliber', '—')}｜时间轴：{cc.get('time_axis', '—')}"]
                body += [f"- 修法：{i['type']} {i['target']} —— {i['suggest']}" for i in mine]
                mc = v.get("memory_cleanup")
                if mc and side == "datus":
                    body.append(f"- 记忆清理（人工执行，D7）：{mc.get('target')} — {mc.get('note')}")
                sec1 += body + [""]
            elif v["verdict"] == "执行事故" and mine:
                sec2 += [f"### {qid} {questions[qid]}",
                         f"- 现象：{v['verdict_detail']}",
                         f"- 口径相同证据：{v.get('comparison', {}).get('summary', '见 comparison.metrics')}",
                         *[f"- 排错：{i['target']} —— {i['suggest']}" for i in mine], ""]
            elif v["verdict"] == "待人工":
                cd, cc = v["cards"]["datus"], v["cards"]["cube"]
                sec4 += [f"### {qid} {questions[qid]}",
                         f"- {side}：{cd.get('caliber', '—')}（值：{cd.get('values')}）",
                         f"- {other}：{cc.get('caliber', '—')}（值：{cc.get('values')}）",
                         "- 拍板后：结论回写课本「已裁定口径」，两侧照改", ""]
        text = "\n".join([
            f"# {name} 回灌材料包 · {side} 侧（D6：人工处置，系统到此为止）", "",
            "## ① 建模差异（谁补建模：side/type 见每条）", *(sec1 or ["（无）", ""]),
            "## ② 执行事故（口径同值异，修 bug 不动建模）", *(sec2 or ["（无）", ""]),
            "## ③ 双侧共同缺口（两侧均答不出；被动统计，只覆盖被问到的题）", *(sec3 or ["（无）", ""]),
            "## ④ 待拍板口径（双方证据并列，拍板结果人工回填 + 课本增补草案）", *(sec4 or ["（无）", ""]),
        ])
        p = fb_dir / f"issues-{side}.md"
        p.write_text(text, encoding="utf-8")
        outs.append(p)

    suite = []
    for qid in todo:
        v = verdicts[qid]
        if v.get("corrected"):
            suite.append(json.dumps({
                "id": qid, "question": questions[qid],
                "answer": v["corrected"].get("answer"),
                "basis": v["corrected"].get("basis"), "since_round": name,
            }, ensure_ascii=False))
    p = fb_dir / "suite-candidates.jsonl"
    p.write_text("\n".join(suite) + ("\n" if suite else ""), encoding="utf-8")
    outs.append(p)
    return outs


def main():
    ap = argparse.ArgumentParser(prog="round", description="一轮互搏编排器（SOP ①–⑥，D6 到材料包即停）")
    ap.add_argument("--round", required=True, help="轮号，如 round-02")
    ap.add_argument("--only", nargs="*", default=None, help="只跑这些 id（小样/子集；不产轮报）")
    ap.add_argument("--retest", default=None, help="（M4）复验上轮，复验集=上轮分歧题")
    args = ap.parse_args()
    if not re.match(r"round-\d+$", args.round):
        ap.error("--round 形如 round-02")
    if args.retest:
        print("[round] --retest 复验模式属 M4，本版未实现", file=sys.stderr)
        sys.exit(1)

    name = args.round
    round_dir = REPO_ROOT / "rounds" / name
    round_dir.mkdir(parents=True, exist_ok=True)
    qpath = round_dir / "questions.jsonl"

    step_examine(round_dir, qpath, name)
    questions = load_questions(qpath)
    todo = [qid for qid in questions if not args.only or qid in args.only]
    if not todo:
        print("--only 未匹配任何题", file=sys.stderr)
        sys.exit(1)

    step_answer(round_dir, qpath, todo)
    cards = {s: {qid: json.loads((round_dir / "answers" / s / f"{qid}.json").read_text(encoding="utf-8"))
                 for qid in todo if (round_dir / "answers" / s / f"{qid}.json").exists()}
             for s in SIDES}
    check_cards(round_dir, todo)
    verdicts = load_verdicts(round_dir, todo)

    if args.only:
        print(f"[round] 子集模式（{len(todo)} 题）到裁决关口为止，不产轮报")
        return

    report = render_report(round_dir, name, questions, todo, verdicts, cards)
    feedbacks = render_feedback(round_dir, name, questions, todo, verdicts, cards)
    print(f"[⑤⑥轮报] {report}")
    for p in feedbacks:
        print(f"[⑤⑥材料包] {p}")
    print("[round] 轮终点（D6）：修语义层/拍板口径/清记忆均为人工动作；复验=M4 --retest")


if __name__ == "__main__":
    main()
