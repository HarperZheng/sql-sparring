"""ask_cube CLI 入口。

用法（Windows 侧 uv 环境）：
  uv run python -m adapters.ask_cube run --questions <题库.jsonl> [--only id ...] [--prefix 会话前缀]
      活跑任意题库（JSONL：{id, question}）；ask 态按拍板政策自动追问并留痕 arbiter。
  uv run python -m adapters.ask_cube reextract --questions <题库.jsonl> [--only id ...]
      raw 留痕重产值行（不重答）：散文＋表格行新提取输入，旧卡归档后覆盖写。
"""

import argparse
import json
from pathlib import Path

from .driver import reextract_question, run_question


def _write_card(answers_dir: Path, card: dict) -> Path:
    answers_dir.mkdir(parents=True, exist_ok=True)
    out = answers_dir / f"{card['id']}.json"
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def cmd_run(args):
    questions_file = Path(args.questions)
    questions = [json.loads(l) for l in questions_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    only = set(args.only or [])
    todo = [q for q in questions if not only or q["id"] in only]
    runs_dir = questions_file.resolve().parent / "runs" / "cube"
    answers_dir = questions_file.resolve().parent / "answers" / "cube"
    for i, q in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {q['id']} {q['question']}", flush=True)
        r = run_question(q["id"], q["question"], args.prefix, runs_dir)
        _write_card(answers_dir, r["card"])
        print(f"    -> {r['first_type']} -> {r['card']['status']} ({r['card']['elapsed_s']}s)", flush=True)


def cmd_reextract(args):
    questions_file = Path(args.questions)
    round_dir = questions_file.resolve().parent
    runs_dir = round_dir / "runs" / "cube"
    answers_dir = round_dir / "answers" / "cube"
    qids = args.only or [p.stem for p in sorted(answers_dir.glob("q*.json"))]
    for qid in qids:
        r = reextract_question(qid, runs_dir, answers_dir)
        print(json.dumps(r, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser(prog="adapters.ask_cube")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="活跑任意题库")
    p.add_argument("--questions", required=True)
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--prefix", default="m0q")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("reextract", help="raw 留痕重产值行（不重答；散文＋表格行新提取输入）")
    p.add_argument("--questions", required=True)
    p.add_argument("--only", nargs="*", default=None)
    p.set_defaults(func=cmd_reextract)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
