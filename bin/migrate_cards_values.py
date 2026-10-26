"""round-02 作答卡一次性迁移：answer 散文 → values 值行（D14，2026-10-26 用户拍板）。

数字来源：rounds/round-02/verdicts/qNN.json 的 cards.<side>.values（裁判已从散文提取、
经人工拍板确认的数，与轮报一致率口径同源），本脚本只做确定性键转换，不重新抄数。

转换纪律：
- 只搬纯数字/null 键；字符串复合值（如 "139 笔 / 159.86 亿元"）不进值行，散文留 runs/；
- 合计/占比键=导出量，不落行（可由原始行算出，比对时由代码导出）；
- 指标名同一题两侧必须一致（join 键），dim 成员名保留裁决书原文（别名归一属登记表，后续沉淀）。

用法（覆盖写卡，回退=git restore rounds/round-02/answers）：
  uv run python bin/migrate_cards_values.py --round rounds/round-02
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.validator import validate_card  # noqa: E402

# ---- 每题转换规则表 ----
# dim 模式：固定 metric/unit，键→dims 成员；drop=不落行的键；aux=非维度键的显式映射。
# map 模式：每键显式 (metric, unit, dims[, note])；shared=两侧共用，datus/cube=单侧追加。
RULES = {
    "q10": {"type": "dim", "metric": "非税缴款金额", "unit": "元", "dim": "月份", "drop": set()},
    "q11": {
        "type": "map",
        "shared": {"合计": ("已缴入国库金额", "元", {})},
        "datus": {
            "国库已确认": ("已缴入国库金额", "元", {"缴库状态": "国库已确认"}),
            "已缴库待确认": ("已缴入国库金额", "元", {"缴库状态": "已缴库待确认"}),
        },
        "cube": {"缴库明细": ("缴库明细数", "个", {}), "缴库单": ("缴库单数", "张", {})},
    },
    "q12": {"type": "dim", "metric": "直缴缴款总额", "unit": "元", "dim": "年份", "drop": set()},
    "q14": {
        "type": "map",
        "shared": {},
        "datus": {
            "榜首(测试云南测试环境)": ("榜首缴款金额", "元", {}, "测试云南测试环境"),
            "有缴款单位数": ("有缴款单位数", "个", {}),
        },
        "cube": {
            "缴款人名单": ("缴款人名单", "个", {}),
            "期内缴款合计": ("期内缴款合计", "元", {}),
            "缴款书": ("缴款书数", "张", {}),
        },
    },
    "q15": {
        "type": "dim", "metric": "代理银行代收金额", "unit": "元", "dim": "代理银行",
        "drop": {"合计"},
        "aux": {"缴款书": ("缴款书数", "张", {})},
    },
    "q16": {"type": "dim", "metric": "待划拨金额", "unit": "元", "dim": "收入项目", "drop": set()},
    "q17": {
        "type": "map",
        "shared": {"有缴款单位数": ("有缴款单位数", "个", {})},
        "datus": {
            "榜首(测试云南测试环境)": ("榜首缴款金额", "元", {}, "测试云南测试环境"),
            "未匹配行金额": ("未匹配行金额", "元", {}),
        },
        "cube": {"榜首(编码124045)": ("榜首缴款金额", "元", {}, "编码124045")},
    },
    "q18": {
        "type": "dim", "metric": "缴款笔数", "unit": "笔", "dim": "缴款方式",
        "drop": {"合计", "直缴占比", "汇缴占比"},
    },
    "q19": {"type": "dim", "metric": "未缴款单位数", "unit": "个", "dim": "金额档", "drop": {"合计"}},
    "q20": {
        "type": "dim", "metric": "未缴款金额", "unit": "元", "dim": "归属级次",
        "drop": {"合计", "省占比", "县占比"}, "member_strip_paren": True,
    },
    "q21": {"type": "dim", "metric": "缴款批次笔数", "unit": "笔", "dim": "耗时档", "drop": set()},
    "q22": {"type": "dim", "metric": "未缴款笔数", "unit": "笔", "dim": "未缴时长档", "drop": {"合计"}},
    "q23": {"type": "dim", "metric": "滞留在途金额", "unit": "元", "dim": "滞留时长档", "drop": {"合计"}},
    "q24": {"type": "dim", "metric": "滞留在途金额", "unit": "元", "dim": "滞留时长档", "drop": {"合计"}},
    "q27": {
        "type": "map",
        "shared": {},
        "datus": {
            "已清分且资金未到账_笔数": ("已清分且资金未到账笔数", "笔", {}),
            "已清分且资金未到账_金额(亿元)": ("已清分且资金未到账金额", "亿元", {}),
            "已到账已清分未划拨_笔数": ("已到账已清分未划拨笔数", "笔", {}),
            "已到账已清分未划拨_金额(万元)": ("已到账已清分未划拨金额", "万元", {}),
            "缴库侧反向异常_笔数": ("缴库侧反向异常笔数", "笔", {}),
        },
        "cube": {"对账成功且未缴入国库_笔数": ("对账成功且未缴入国库笔数", "笔", {})},
    },
}


def _row(metric: str, unit: str, dims: dict, value, note: str | None = None) -> dict:
    row = {"metric": metric, "unit": unit, "dims": dims, "value": value}
    if note:
        row["note"] = note
    return row


def convert(qid: str, side: str, raw: dict | None) -> list[dict]:
    """裁决书 values 字典 → 值行数组；raw 为空返回 []。"""
    if not raw:
        return []
    rule = RULES[qid]
    rows: list[dict] = []
    if rule["type"] == "dim":
        strip = rule.get("member_strip_paren", False)
        for key, val in raw.items():
            if key in rule["drop"]:
                continue
            if key in rule.get("aux", {}):
                metric, unit, dims = rule["aux"][key]
                rows.append(_row(metric, unit, dims, val))
                continue
            member = key
            note = None
            if strip and "(" in key:
                member, _, tail = key.partition("(")
                member = member.strip()
                note = tail.rstrip(")")
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                if val is not None:
                    continue  # 字符串复合值不进值行
            rows.append(_row(rule["metric"], rule["unit"], {rule["dim"]: member}, val, note))
    else:  # map
        table = dict(rule.get("shared", {}))
        table.update(rule.get(side, {}))
        for key, val in raw.items():
            if key not in table:
                continue  # 规则表未登记的键不落行（含字符串复合值）
            metric, unit, dims, *rest = table[key]
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                if val is not None:
                    continue
            rows.append(_row(metric, unit, dims, val, rest[0] if rest else None))
    return rows


def main():
    ap = argparse.ArgumentParser(description="round-02 作答卡 answer→values 一次性迁移（D14）")
    ap.add_argument("--round", required=True, help="轮目录，如 rounds/round-02")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    round_dir = Path(args.round)
    n_side_rows = {}
    for side in ("datus", "cube"):
        for card_path in sorted((round_dir / "answers" / side).glob("q*.json")):
            card = json.loads(card_path.read_text(encoding="utf-8"))
            verdict_path = round_dir / "verdicts" / f"{card['id']}.json"
            raw = None
            if verdict_path.exists():
                verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
                raw = verdict.get("cards", {}).get(side, {}).get("values")
            rows = convert(card["id"], side, raw)
            card.pop("answer", None)  # 散文不落卡，全文在 runs/（raw_path 指认）
            card["values"] = rows
            validate_card(card, where=f"（{card_path.name} 迁移后）")
            card_path.write_text(
                json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            n_side_rows[f"{side}/{card['id']}"] = len(rows)

    total_files = len(n_side_rows)
    non_empty = sum(1 for v in n_side_rows.values() if v)
    print(f"迁移完成：{total_files} 张卡（answer 已移除，values 落卡，全部过契约校验）")
    print(f"非空值行卡 {non_empty} 张，总行数 {sum(n_side_rows.values())}")
    for k, v in n_side_rows.items():
        if v:
            print(f"  {k}: {v} 行")


if __name__ == "__main__":
    main()
