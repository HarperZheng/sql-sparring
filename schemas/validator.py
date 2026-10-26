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


def _card_semantic_problems(card: dict, legacy: bool = False) -> list[str]:
    """schema 之外作答卡的语义规则：
    1. values 值行为答案唯一载体（D14，2026-10-26 拍板 answer 自契约删除）；
       m0 存档卡（legacy=True）内保留 answer 散文，豁免缺 values（D10 不改写不迁移）；
    2. 值行 metric 不得是导出量（合计/占比/排名可由原始行算出，落行即重复登记）。"""
    probs = []
    if "values" not in card:
        if legacy and "answer" in card:
            pass  # m0 存档卡：契约已删 answer 字段，存档原样保留，不再要求 values
        else:
            probs.append("缺答案载体 values（D14 唯一载体；散文只在 runs/ 留痕）")
    for i, row in enumerate(card.get("values") or []):
        name = row.get("metric", "")
        if name.split(":")[-1].startswith(("合计", "占比", "排名")):
            probs.append(f"values[{i}] metric={name!r} 是导出量，不落值行（由代码导出比对）")
    return probs


def validate_card(card: dict, where: str = "", legacy: bool = False) -> None:
    """作答卡校验，不过抛 ContractError（适配器写卡前调用）。"""
    errors = list(_validator("answer_card").iter_errors(card))
    errors += _card_semantic_problems(card, legacy)
    if errors:
        raise ContractError(f"作答卡不合契约{where}（id={card.get('id')}）: {_fmt(errors)}")


def _check_file(path: Path, schema_name: str, legacy: bool = False) -> list[str]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"不是合法 JSON: {e}"]
    probs = [f"{'/'.join(map(str, e.absolute_path)) or '<根>'}: {e.message}"
             for e in _validator(schema_name).iter_errors(obj)]
    if schema_name == "answer_card":
        probs += _card_semantic_problems(obj, legacy)
    return probs


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


def validate_question(q: dict) -> list[str]:
    """单题内存校验（bin/examine.py 出题驱动用）。返回问题清单（空=通过）。"""
    return [f"{'/'.join(map(str, e.absolute_path)) or '<根>'}: {e.message}"
            for e in _validator("question").iter_errors(q)]


def check_cards_dir(answers_side_dir: Path) -> list[tuple[str, list[str]]]:
    """answers/<side>/*.json 逐份校验。返回 [(文件名, 问题清单)]，目录不存在返回空。
    m0 为 D14 前存档轮（D10 不改写不迁移）：卡内 answer 散文豁免缺 values。"""
    out = []
    if not answers_side_dir.is_dir():
        return out
    legacy = answers_side_dir.parent.name == "answers" \
        and answers_side_dir.parent.parent.name == "m0"
    for f in sorted(answers_side_dir.glob("*.json")):
        probs = _check_file(f, "answer_card", legacy=legacy)
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
