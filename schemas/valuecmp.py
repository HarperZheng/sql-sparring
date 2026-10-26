"""值行一致率引擎（D14 两级判定，2026-10-26 拍板）：从双侧作答卡的 values 算一致率。

定位：纯函数 + 只读，不改任何数据。题级判定每题三步（详见 docs/implementation.md §四）：
① 数列快筛：每侧取全部值行数字——金额换算成元（万元/亿元）、剔导出量（引擎侧
   再剔一次，如「期内缴款合计」）、null 不进列——排序、不去重；两列数不等即判
   「不一致」（终审，不再看名字）；双侧都无数列也判「不一致」（都未答出）。
② 键比对：只对过①的题定案，剔导出量行后按（指标，维度）同名行逐行比数值
   （行级三态 同/异/缺）：全部行同名同值 → 「一致」；同名行值异/缺数 → 「不一致」；
   单侧 null 行（对侧无同名行）= 缺行 → 「不一致」。
③ 待复核：键名对不上（数列相等但名字对不齐——错位嫌疑或异名同义）→ 标「待复核」，
   AI 提议别名→人审定→登记表→重算翻案；审定为错位则改判不一致。

依据：键比对一致 ⟹ 数列必然相等，逆否即数列不等 ⟹ 不一致恒真——①判不一致零误判；
数列相等的题不允许跳过②直接判一致（堵住成员贴反被数列规则误判一致的盲区）。

一致率 = ②判「一致」的题数 ÷ 轮题库题数（剔除题已物理删除）；待复核不计分子，
翻案后重算计入。

展示与判定分层：join_rows / 轮报分歧明细「值行比对」列走**明细口径**（不剔导出量行、
共有键计数：值同/值异/不一致 + 单侧行清单），只供回改①查证「哪个指标/维度/筛选错」，
不参与题级判定；题级结论只认两级判定。

归一：键名先文本归一（NFKC + 去首尾空白 + 小写），再查登记表别名
（conf/metrics.json 的 key_aliases：alias→canonical，单层映射不递归）；
登记表缺文件/空表 = 只做文本归一。未登记行（metric 以 `未登记:` 开头）照常
参与比对与数列（它们是真实答案），单列清单作语义层缺口信号。

CLI（轮报渲染外的独立复盘入口）：
  uv run python -m schemas.valuecmp --round rounds/round-02
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

# 金额量纲换算到元；其余单位（笔/张/个/天/%）为计数/时长/百分比量纲，原样不换算
_UNIT_SCALE = {"元": 1.0, "万元": 1e4, "亿元": 1e8}
# 导出量标记（判定口径剔除，子串命中即剔，如「期内缴款合计」）
_EXPORT_MARKS = ("合计", "占比", "排名", "环比", "同比", "均值", "平均")
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "conf" / "metrics.json"

_STAGE_NAME = {"①": "①数列快筛", "②": "②键比对", "③": "③待复核"}


def _scale(unit: str) -> float:
    return _UNIT_SCALE.get(unit, 1.0)


def _is_amount(unit: str) -> bool:
    return unit in _UNIT_SCALE


def _is_export(metric: str) -> bool:
    return any(m in metric for m in _EXPORT_MARKS)


def load_registry() -> dict:
    """读指标登记表（conf/metrics.json）；缺文件/坏表按空表处理（只做文本归一）。"""
    try:
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"metrics": [], "key_aliases": []}
    if not isinstance(reg, dict):
        return {"metrics": [], "key_aliases": []}
    reg.setdefault("metrics", [])
    reg.setdefault("key_aliases", [])
    return reg


def _norm_text(s) -> str:
    return unicodedata.normalize("NFKC", str(s)).strip().lower()


def alias_map(registry: dict) -> dict[str, str]:
    """key_aliases 条目（alias/canonical）→ {归一化别名: 归一化正名}。"""
    out = {}
    for e in registry.get("key_aliases") or []:
        a, c = e.get("alias"), e.get("canonical")
        if a and c:
            out[_norm_text(a)] = _norm_text(c)
    return out


def _row_key(row: dict, aliases: dict[str, str]) -> tuple:
    """join 键 = (归一化 metric, 排序后的归一化 dims 项)。"""
    metric = aliases.get(_norm_text(row.get("metric") or ""),
                         _norm_text(row.get("metric") or ""))
    dims = tuple(sorted(
        (aliases.get(_norm_text(k), _norm_text(k)),
         aliases.get(_norm_text(v), _norm_text(v)))
        for k, v in (row.get("dims") or {}).items()))
    return (metric, dims)


def _seq_value(row: dict) -> float | None:
    """值行 → 进①数列的数字；导出量/null 返回 None（不进列）。"""
    if _is_export(str(row.get("metric") or "")):
        return None
    v = row.get("value")
    if v is None:
        return None
    return round(float(v) * _scale(str(row.get("unit") or "元")), 2)


def sequence(rows: list[dict]) -> list[float]:
    """①数列快筛的单侧数列：金额换算到元、剔导出量、null 不进列，排序、不去重。"""
    return sorted(x for x in (_seq_value(r) for r in rows or []) if x is not None)


def _row_state(ra: dict, rb: dict) -> str:
    """一对同名值行的行级三态：同（金额换算到元后 2 位小数相等，null=null 亦同）/
    异/缺（单侧称无数）。量纲不同（金额 vs 计数等）按 异。"""
    va, vb = ra.get("value"), rb.get("value")
    ua = str(ra.get("unit") or "元")
    ub = str(rb.get("unit") or "元")
    if _is_amount(ua) != _is_amount(ub):
        return "异"
    if va is None and vb is None:
        return "同"  # null=null 算同名同值
    if va is None or vb is None:
        return "缺"
    return "同" if round(float(va) * _scale(ua), 2) == round(float(vb) * _scale(ub), 2) else "异"


def join_rows(rows_a: list[dict], rows_b: list[dict],
              aliases: dict[str, str]) -> dict:
    """键比对明细（**明细口径**，每题都算，供分歧明细展示）：不剔导出量行（展示要全貌）。

    返回 {same, diff, missing, rows, extra_a, extra_b, unregistered}；
    rows 为逐键明细 [{key, dims, unit, a, b, state}]（state∈同/异/缺），
    extra_* 为单侧行清单 ["metric {dims}"]。
    """
    ka = {_row_key(r, aliases): r for r in rows_a or []}
    kb = {_row_key(r, aliases): r for r in rows_b or []}

    same = diff = missing = 0
    detail = []
    for key in sorted(set(ka) & set(kb), key=str):
        ra, rb = ka[key], kb[key]
        state = _row_state(ra, rb)
        same += state == "同"
        diff += state == "异"
        missing += state == "缺"
        detail.append({"key": key[0], "dims": dict(key[1]),
                       "unit": str(rb.get("unit") or "元"),
                       "a": ra.get("value"), "b": rb.get("value"), "state": state})

    extra_a = sorted(set(ka) - set(kb), key=str)
    extra_b = sorted(set(kb) - set(ka), key=str)
    unreg = [f"{side}:{r.get('metric')}"
             for side, lst in (("datus", rows_a or []), ("cube", rows_b or []))
             for r in lst if str(r.get("metric") or "").startswith("未登记:")]
    return {
        "same": same, "diff": diff, "missing": missing, "rows": detail,
        "extra_a": [f"{m} {dict(d)}" for m, d in extra_a],
        "extra_b": [f"{m} {dict(d)}" for m, d in extra_b],
        "unregistered": unreg,
    }


def _diag_verdict(cmp: dict, n_rows_a: int, n_rows_b: int) -> tuple[str, str]:
    """明细口径题级判据（轮报分歧明细「值行比对」列展示用，不参与题级两级判定）。"""
    if cmp["diff"]:
        return "值异", f"共有键异 {cmp['diff']} 行"
    if cmp["missing"]:
        return "不一致", f"共有键缺 {cmp['missing']} 行（单侧无数）"
    if cmp["same"]:
        return "值同", f"共有键全同 {cmp['same']} 行"
    if n_rows_a and n_rows_b:
        return "不一致", "两侧各有产出但无共同可比键（口径未对齐）"
    return "不一致", "单侧无值行（一侧未接住，计不一致不豁免）"


def compare_question(rows_a: list[dict], rows_b: list[dict],
                     aliases: dict[str, str]) -> dict:
    """一道题的两级判定 → {verdict, stage, reason, diag_verdict, diag_reason, cmp}。

    verdict ∈ 一致/不一致/待复核（题级，两级判定）；diag_* 为明细口径判据（仅展示）；
    stage 记题级定案步（①数列快筛/②键比对/③待复核）。
    """
    cmp = join_rows(rows_a, rows_b, aliases)  # 明细口径视图（含导出量行），供展示
    dverdict, dreason = _diag_verdict(cmp, len(rows_a or []), len(rows_b or []))
    base = {"cmp": cmp, "diag_verdict": dverdict, "diag_reason": dreason}
    seq_a, seq_b = sequence(rows_a), sequence(rows_b)

    # ① 数列快筛（终审，不看名字）
    if seq_a != seq_b:
        return {**base, "verdict": "不一致", "stage": "①", "reason":
                f"①数列不等：datus {len(seq_a)} 个数 vs cube {len(seq_b)} 个数"}
    if not seq_a:
        return {**base, "verdict": "不一致", "stage": "①", "reason":
                "①双侧无数列（都未答出数，计不一致）"}

    # ② 键比对（判定口径：剔导出量行后同名行逐行比）
    ka = {_row_key(r, aliases): r for r in rows_a or []
          if not _is_export(str(r.get("metric") or ""))}
    kb = {_row_key(r, aliases): r for r in rows_b or []
          if not _is_export(str(r.get("metric") or ""))}
    shared = set(ka) & set(kb)
    diff = sum(1 for k in shared if _row_state(ka[k], kb[k]) == "异")
    missing = sum(1 for k in shared if _row_state(ka[k], kb[k]) == "缺")
    extras = [ka[k] for k in set(ka) - set(kb)] + [kb[k] for k in set(kb) - set(ka)]
    n_null = sum(1 for r in extras if r.get("value") is None)

    if diff:
        return {**base, "verdict": "不一致", "stage": "②", "reason":
                f"②同名行值异 {diff} 行"}
    if missing:
        return {**base, "verdict": "不一致", "stage": "②", "reason":
                f"②同名行缺数 {missing} 行（单侧称无）"}
    if n_null:
        return {**base, "verdict": "不一致", "stage": "②", "reason":
                f"②单侧 null 行 {n_null} 条，对侧无同名行（缺行）"}
    if len(extras) - n_null:
        return {**base, "verdict": "待复核", "stage": "③", "reason":
                f"③键名对不上 {len(extras) - n_null} 行（数列相等——错位嫌疑或异名同义；"
                "AI提议别名→人审定→登记表→重算）"}
    return {**base, "verdict": "一致", "stage": "②", "reason":
            f"②数列相等且 {cmp['same']} 行同名同值"}


def load_round(round_dir: Path) -> dict:
    """读轮目录 → {qid: {datus: [值行], cube: [值行]}}；缺卡按空值行处理。"""
    qids = []
    qf = round_dir / "questions.jsonl"
    for line in qf.read_text(encoding="utf-8").splitlines():
        if line.strip():
            qids.append(json.loads(line)["id"])
    out = {}
    for qid in qids:
        sides = {}
        for side in ("datus", "cube"):
            p = round_dir / "answers" / side / f"{qid}.json"
            if p.exists():
                sides[side] = json.loads(p.read_text(encoding="utf-8")).get("values") or []
            else:
                sides[side] = []
        out[qid] = sides
    return out


def compare_round(round_dir: Path) -> dict:
    """轮级一致率：②判一致的题数 / 题库题数；附待复核清单与逐题明细（含明细口径判据）。"""
    aliases = alias_map(load_registry())
    data = load_round(round_dir)
    n = len(data)
    questions = {}
    unreg_all: list[str] = []
    n_ok = 0
    for qid, sides in data.items():
        q = compare_question(sides["datus"], sides["cube"], aliases)
        if q["verdict"] == "一致":
            n_ok += 1
        unreg_all += q["cmp"]["unregistered"]
        questions[qid] = {
            "verdict": q["verdict"], "stage": q["stage"], "reason": q["reason"],
            "diag_verdict": q["diag_verdict"], "diag_reason": q["diag_reason"],
            "cmp": q["cmp"],
            "extra_datus": q["cmp"]["extra_a"], "extra_cube": q["cmp"]["extra_b"],
        }
    review = [qid for qid, q in questions.items() if q["verdict"] == "待复核"]
    return {
        "n_questions": n,
        "一致率": {"一致": n_ok, "分母": n, "ratio": (n_ok / n) if n else 0.0},
        "待复核": {"题数": len(review), "题": review},
        "未登记": unreg_all,
        "questions": questions,
    }


def _fmt_ratio(x: float) -> str:
    return f"{x * 100:.1f}%"


def render(result: dict) -> str:
    """比对结果 → 人读文本（轮报可直接引用）。"""
    lines = []
    r = result
    vc = Counter(q["verdict"] for q in r["questions"].values())
    lines.append(f"题库题数（分母，剔除题已删除）：{r['n_questions']}")
    lines.append(f"值行一致率（两级判定 D14，一致/分母）：{r['一致率']['一致']}/{r['一致率']['分母']}"
                 f" = {_fmt_ratio(r['一致率']['ratio'])}"
                 f"（一致 {vc.get('一致', 0)} / 不一致 {vc.get('不一致', 0)}"
                 f" / 待复核 {vc.get('待复核', 0)}）")
    if r["待复核"]["题数"]:
        lines.append(f"待复核题：{' '.join(r['待复核']['题'])}"
                     "（AI提议别名→人审定→登记表→重算翻案）")
    if r["未登记"]:
        lines.append(f"未登记行 {len(r['未登记'])} 条：{r['未登记']}")
    else:
        lines.append("未登记行：0")
    lines.append("")
    lines.append("| 题 | 题级结论 | 定案步 | 判据 | 明细口径 |")
    lines.append("|---|---|---|---|---|")
    for qid, q in r["questions"].items():
        lines.append(f"| {qid} | {q['verdict']} | {_STAGE_NAME[q['stage']]} | {q['reason']}"
                     f" | {q['diag_verdict']}（{q['diag_reason']}） |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(prog="valuecmp", description="值行一致率引擎（D14 两级判定）")
    ap.add_argument("--round", required=True, help="轮目录，如 rounds/round-02")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(render(compare_round(Path(args.round))))


if __name__ == "__main__":
    main()
