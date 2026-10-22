"""出题驱动器（M2 四件套之三）：考纲课本 → 题库 questions.jsonl。

流程：读课本与 SKILL 契约 → 拼 prompt → 按 conf/models.json examiner 节调 LLM
（缺省本机 claude -p，D9）→ 契约校验 + syllabus_ref 悬空检查 + 覆盖矩阵/配比检查
→ 全过落盘；不合法把错误清单连同上次输出打回重出，最多 --max-retries 次。

用法：
  uv run python bin/examine.py --out rounds/round-02/questions.jsonl \
      --count 30 --mix 事实:10,关联:10,辨析:5,边界:5
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schemas.validator import validate_question  # noqa: E402

CONF_PATH = REPO_ROOT / "conf" / "models.json"
SKILL_PATH = REPO_ROOT / "examiner" / "SKILL.md"

B_REF = re.compile(r"\bB\d{2}\b")


def _out(msg: str) -> None:
    print(msg, flush=True)


def load_knowledge_points(syllabus_dir: Path) -> tuple[str, set[str]]:
    """读课本全文，返回（全文, 知识点编号集合）。"""
    business = syllabus_dir / "business.md"
    if not business.is_file():
        sys.exit(f"[examine] 找不到课本: {business}")
    text = business.read_text(encoding="utf-8")
    points = set(B_REF.findall(text))
    if not points:
        sys.exit("[examine] 课本中未发现任何知识点编号（B\\d\\d）")
    return text, points


def parse_mix(mix: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for part in mix.split(","):
        k, _, v = part.partition(":")
        k, v = k.strip(), v.strip()
        if not k or not v.isdigit() or int(v) <= 0:
            sys.exit(f"[examine] --mix 段不合法: {part!r}（应为 题型:数量，如 事实:10）")
        out[k] = int(v)
    return out


def build_prompt(skill: str, business_text: str, *, round_name: str, start_id: str,
                 count: int, mix: dict[str, int],
                 feedback: list[str] | None = None,
                 previous_output: str | None = None) -> str:
    task = [
        "## 本次出题任务",
        f"- 轮号 round: {round_name}",
        f"- 起始 id: {start_id}（之后连续递增）",
        f"- 题目总数: {count}",
        "- 题型配比: " + ", ".join(f"{k}:{v}" for k, v in mix.items()),
        "- 只输出 JSONL 原文（契约第三节）。",
    ]
    parts = [skill,
             "---\n\n# 随附考纲课本全文\n\n" + business_text,
             "---\n\n" + "\n".join(task)]
    if feedback:
        parts.append("---\n\n## 打回（上次输出不合法，按错误清单修正后重新输出完整题库）\n\n"
                     + "\n".join(f"- {line}" for line in feedback))
    if previous_output:
        parts.append("---\n\n## 上次输出原文\n\n" + previous_output)
    return "\n\n".join(parts)


def call_examiner(prompt: str, timeout: int) -> str:
    conf = json.loads(CONF_PATH.read_text(encoding="utf-8"))["examiner"]
    provider = conf.get("provider", "claude-cli")
    if provider != "claude-cli":
        sys.exit(f"[examine] 暂只支持 provider=claude-cli，当前配置 {provider!r}（D9）")
    claude = shutil.which("claude")
    if not claude:
        sys.exit("[examine] 找不到 claude 命令——provider=claude-cli 需本机可用 claude")
    try:
        proc = subprocess.run([claude, "-p"], input=prompt.encode("utf-8"),
                              capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        sys.exit(f"[examine] claude -p 超时（>{timeout}s）")
    if proc.returncode != 0:
        sys.exit("[examine] claude -p 失败（exit=%d）:\n%s"
                 % (proc.returncode, proc.stderr.decode("utf-8", "replace")[:2000]))
    return proc.stdout.decode("utf-8", "replace")


def strip_fences(text: str) -> str:
    """防御性剥掉 ``` 代码块包裹（契约禁止，打回前先容错）。"""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\r?\n", "", t)
        if t.endswith("```"):
            t = t[:-3].rstrip()
    return t


def parse_questions(raw: str) -> tuple[list[dict], list[str]]:
    problems: list[str] = []
    questions: list[dict] = []
    for lineno, line in enumerate(strip_fences(raw).splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"第{lineno}行不是合法 JSON: {e}")
            continue
        problems += [f"第{lineno}行 {p}" for p in validate_question(obj)]
        questions.append(obj)
    return questions, problems


def domain_checks(questions: list[dict], *, points: set[str], start_id: str,
                  count: int, mix: dict[str, int], round_name: str) -> list[str]:
    problems: list[str] = []
    if len(questions) != count:
        problems.append(f"题目数 {len(questions)} != 要求 {count}")
    start_n = int(start_id[1:])
    for i, qid in enumerate(q.get("id") for q in questions):
        expect = f"{start_id[0]}{start_n + i:02d}"
        if qid != expect:
            problems.append(f"第{i + 1}题 id={qid!r}，自 {start_id} 起应连续为 {expect}")
            break
    ids = [q.get("id") for q in questions]
    if len(set(ids)) != len(ids):
        problems.append("id 有重复")
    seen_points: set[str] = set()
    seen_types: dict[str, int] = {}
    for i, q in enumerate(questions, 1):
        for r in q.get("syllabus_ref") or []:
            if r not in points:
                problems.append(f"第{i}题 syllabus_ref 悬空: {r}（课本无此编号）")
            seen_points.add(r)
        t = q.get("type")
        seen_types[t] = seen_types.get(t, 0) + 1
        if q.get("round") != round_name:
            problems.append(f"第{i}题 round={q.get('round')!r} != {round_name!r}")
    for t, n in mix.items():
        if seen_types.get(t, 0) != n:
            problems.append(f"题型 {t} 数量 {seen_types.get(t, 0)} != 配比 {n}")
    extra = sorted(set(seen_types) - set(mix))
    if extra:
        problems.append(f"出现配比之外的题型: {extra}")
    uncovered = sorted(points - seen_points)
    if uncovered:
        problems.append("覆盖矩阵漏项（以下知识点零覆盖）: " + ", ".join(uncovered))
    return problems


def print_matrix(questions: list[dict], points: set[str], mix: dict[str, int]) -> None:
    types = list(mix)
    ref_by: dict[str, set[str]] = {}
    for q in questions:
        for r in q.get("syllabus_ref") or []:
            ref_by.setdefault(r, set()).add(q.get("type"))
    _out("\n覆盖矩阵（知识点 × 题型，●=有题）")
    _out("知识点   " + "  ".join(types))
    for p in sorted(points):
        row = "  ".join("●" if t in ref_by.get(p, set()) else "·" for t in types)
        _out(f"{p}    {row}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="M2 出题驱动器：考纲 → 题库（契约校验+悬空+覆盖矩阵）")
    ap.add_argument("--syllabus", default="syllabus", help="考纲目录（含 business.md）")
    ap.add_argument("--out", required=True, help="题库输出路径，如 rounds/round-02/questions.jsonl")
    ap.add_argument("--count", type=int, required=True, help="题目总数")
    ap.add_argument("--mix", default="事实:10,关联:10,辨析:5,边界:5", help="题型配比，如 事实:10,关联:10,辨析:5,边界:5")
    ap.add_argument("--start-id", default="q01", help="起始题号")
    ap.add_argument("--round", default=None, help="轮号（缺省从 --out 路径解析 round-NN）")
    ap.add_argument("--max-retries", type=int, default=3, help="打回重出上限")
    ap.add_argument("--timeout", type=int, default=900, help="单次 claude -p 超时秒数")
    args = ap.parse_args()

    syllabus_dir = Path(args.syllabus)
    if not syllabus_dir.is_absolute():
        syllabus_dir = REPO_ROOT / syllabus_dir
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    m = re.search(r"round-\d+", str(out_path))
    round_name = args.round or (m.group(0) if m else None)
    if not round_name:
        sys.exit("[examine] 无法从 --out 路径解析轮号，请用 --round 指定（如 round-02）")

    mix = parse_mix(args.mix)
    if sum(mix.values()) != args.count:
        sys.exit(f"[examine] --mix 合计 {sum(mix.values())} != --count {args.count}")

    skill = SKILL_PATH.read_text(encoding="utf-8")
    business_text, points = load_knowledge_points(syllabus_dir)
    if args.count < len(points):
        sys.exit(f"[examine] 题目数 {args.count} < 知识点数 {len(points)}，覆盖矩阵不可能无漏项，先调大 --count")

    feedback: list[str] | None = None
    previous: str | None = None
    for attempt in range(1, args.max_retries + 1):
        _out(f"[examine] 第 {attempt}/{args.max_retries} 次出题（count={args.count}，round={round_name}）…")
        prompt = build_prompt(skill, business_text, round_name=round_name,
                              start_id=args.start_id, count=args.count, mix=mix,
                              feedback=feedback, previous_output=previous)
        raw = call_examiner(prompt, args.timeout)
        questions, problems = parse_questions(raw)
        problems += domain_checks(questions, points=points, start_id=args.start_id,
                                  count=args.count, mix=mix, round_name=round_name)
        if not problems:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                "\n".join(json.dumps(q, ensure_ascii=False) for q in questions) + "\n",
                encoding="utf-8")
            _out(f"[examine] 题库落盘: {out_path}（{len(questions)} 题）")
            print_matrix(questions, points, mix)
            return
        _out(f"[examine] 不合法 {len(problems)} 处，打回重出：")
        for p in problems:
            _out(f"  - {p}")
        feedback, previous = problems, raw
    _out("[examine] 打回次数用尽仍不合法——退出码 1")
    sys.exit(1)


if __name__ == "__main__":
    main()
