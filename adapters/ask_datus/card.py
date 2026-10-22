"""作答卡（11 字段，契约=schemas/answer_card.schema.json）：id / question / status /
metrics_hit / sql / sql_count / answer / errors / elapsed_s / arbiter / raw_path。

本文件只做"提取结果 → 卡"的组装；写卡前由 schemas.validator.validate_card 过契约。
status 六值枚举（M1 拍板 D10）：answer|ask|nomatch|timeout|error|failed——
datus -p 无 ask 追问流（arbiter 恒为 null），本侧现产 answer / failed；
ask/nomatch 是 cube 三态概念，六值为两侧共用的超集。
"""

# v0 状态 → 作答卡 status 枚举
_SUCCESS_STATUSES = ("成功", "成功(指标路径)")


def v0_status_to_card_status(status: str) -> str:
    return "answer" if status in _SUCCESS_STATUSES else "failed"


def build_card(qid: str, question: str, extracted: dict, elapsed_s, raw_path: str) -> dict:
    """提取结果 + 运行元数据 → 11 字段作答卡。

    metrics_hit：工具级命中指标（过程证据）——tool/depth/names 三元组，
    rows/desc 等展示性内容留在原始留痕（raw_path 可回查）。
    """
    return {
        "id": qid,
        "question": question,
        "status": v0_status_to_card_status(extracted["status"]),
        "metrics_hit": [
            {"tool": m["tool"], "depth": m["depth"], "names": m["names"]}
            for m in extracted["metric_calls"]
        ],
        "sql": extracted["sql"],
        "sql_count": extracted["sql_count"],
        "answer": extracted["answer"],
        "errors": extracted["errors"],
        "elapsed_s": elapsed_s,
        "arbiter": None,  # datus -p 无 ask 流，M0 恒空
        "raw_path": raw_path,
    }

