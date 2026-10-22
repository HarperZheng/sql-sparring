"""契约校验（M1 定稿的执行端）：数据逐份对 schemas/*.schema.json 检查。

两个使用点：
- 适配器写卡前内联校验（adapters/*/driver.py）——格式错误在产出时挡住，不流到裁决层；
- bin/validate.py 命令行——对轮目录全量核查（题库/作答卡/裁决书）。
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent


class ContractError(Exception):
    """数据违反契约；message 含字段路径与 jsonschema 说明。"""


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _fmt(errors) -> str:
    return "; ".join(
        f"{'/'.join(map(str, e.absolute_path)) or '<根>'}: {e.message}" for e in errors
    )


def validate_card(card: dict, where: str = "") -> None:
    """作答卡校验，不过抛 ContractError（适配器写卡前调用）。"""
    errors = list(_validator("answer_card").iter_errors(card))
    if errors:
        raise ContractError(f"作答卡不合契约{where}（id={card.get('id')}）: {_fmt(errors)}")


def _check_file(path: Path, schema_name: str) -> list[str]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"不是合法 JSON: {e}"]
    return [f"{'/'.join(map(str, e.absolute_path)) or '<根>'}: {e.message}"
            for e in _validator(schema_name).iter_errors(obj)]


def check_questions_file(path: Path) -> list[str]:
    """题库 JSONL 逐行校验 + id 去重。返回问题清单（空=通过）。"""
    v = _validator("question")
    problems, seen = [], set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"第{lineno}行 不是合法 JSON: {e}")
            continue
        for e in v.iter_errors(obj):
            problems.append(f"第{lineno}行 {'/'.join(map(str, e.absolute_path)) or '<根>'}: {e.message}")
        qid = obj.get("id")
        if qid in seen:
            problems.append(f"第{lineno}行 id 重复: {qid}")
        seen.add(qid)
    return problems


def check_cards_dir(answers_side_dir: Path) -> list[tuple[str, list[str]]]:
    """answers/<side>/*.json 逐份校验。返回 [(文件名, 问题清单)]，目录不存在返回空。"""
    out = []
    if not answers_side_dir.is_dir():
        return out
    for f in sorted(answers_side_dir.glob("*.json")):
        probs = _check_file(f, "answer_card")
        if probs:
            out.append((f.name, probs))
    return out


def check_verdicts_dir(verdicts_dir: Path) -> list[tuple[str, list[str]]]:
    """verdicts/*.json 逐份校验（M3 起才有，不存在则空）。"""
    out = []
    if not verdicts_dir.is_dir():
        return out
    for f in sorted(verdicts_dir.glob("*.json")):
        probs = _check_file(f, "verdict")
        if probs:
            out.append((f.name, probs))
    return out


def check_round(round_dir: Path) -> list[tuple[str, list[str]]]:
    """轮目录全量核查：questions*.jsonl + answers/<side>/ + verdicts/。"""
    findings = []
    for qf in sorted(round_dir.glob("questions*.jsonl")):
        probs = check_questions_file(qf)
        if probs:
            findings.append((qf.name, probs))
    answers = round_dir / "answers"
    if answers.is_dir():
        for side_dir in sorted(p for p in answers.iterdir() if p.is_dir()):
            findings += check_cards_dir(side_dir)
    findings += check_verdicts_dir(round_dir / "verdicts")
    return findings
