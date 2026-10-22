"""ask_datus CLI 入口。

用法（Windows 侧 uv 环境）：
  uv run python -m adapters.ask_datus replay
      B1 回归门：25 份 v0 payload 离线重放，与 qa_results.json 逐字段比对
  uv run python -m adapters.ask_datus run --questions rounds/m0/questions.jsonl [--only q01 q02] [--timeout 900]
      活跑：逐题经 WSL 桥接调 datus，作答卡落 rounds/<轮>/answers/datus/
"""

import argparse
import json
import sys
from pathlib import Path

from .driver import DEFAULT_TIMEOUT_S, REPO_ROOT, build_and_write_card, run_question


def cmd_replay(args):
    from .replay import run_replay
    report_out = Path(args.report) if args.report else REPO_ROOT / "rounds" / "m0" / "b1_replay_report.json"
    ok = run_replay(report_out)
    sys.exit(0 if ok else 1)


def cmd_run(args):
    questions_file = Path(args.questions)
    questions = [json.loads(l) for l in questions_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    only = set(args.only or [])
    todo = [q for q in questions if not only or q["id"] in only]
    if not todo:
        print("没有匹配的题目", file=sys.stderr)
        sys.exit(1)

    runs_dir = questions_file.parent / "runs" / "datus"
    answers_dir = questions_file.parent / "answers" / "datus"
    for i, q in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {q['id']} {q['question']}", flush=True)
        result = run_question(q["id"], q["question"], runs_dir, timeout_s=args.timeout)
        card_path = build_and_write_card(q["id"], q["question"], result, answers_dir)
        st = result["extracted"]["status"]
        print(f"    -> {st} ({result['meta']['elapsed_s']}s) 卡：{card_path}", flush=True)


def main():
    ap = argparse.ArgumentParser(prog="adapters.ask_datus")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_replay = sub.add_parser("replay", help="B1 回归门：v0 payload 离线重放比对")
    p_replay.add_argument("--report", default=None, help="报告输出路径（缺省 rounds/m0/b1_replay_report.json）")
    p_replay.set_defaults(func=cmd_replay)

    p_run = sub.add_parser("run", help="活跑：逐题驱动 datus 出作答卡")
    p_run.add_argument("--questions", required=True, help="题目 JSONL（{id, question}）")
    p_run.add_argument("--only", nargs="*", default=None, help="只跑这些 id（子集复跑）")
    p_run.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    p_run.set_defaults(func=cmd_run)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
