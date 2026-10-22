"""最小作答卡（M0 底坯，11 字段）：id / question / status / metrics_hit / sql /
sql_count / answer / errors / elapsed_s / arbiter / raw_path。

M1 将升格为 schemas/answer_card.schema.json；本文件只做"提取结果 → 卡"的组装。
status 枚举（answer|ask|nomatch|failed）——datus 侧 M0 只会出现 answer / failed：
datus -p 无 ask 追问流（arbiter 恒为 null），nomatch 是 cube 三态概念。
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

