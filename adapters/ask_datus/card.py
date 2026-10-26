"""作答卡（11 字段，契约=schemas/answer_card.schema.json）：id / question / status /
metrics_hit / sql / sql_count / answer / errors / elapsed_s / arbiter / raw_path。

本文件只做"提取结果 → 卡"的组装；写卡前由 schemas.validator.validate_card 过契约。
status 六值枚举（M1 拍板 D10）：answer|ask|nomatch|timeout|error|failed——
datus（-p 与 chat API 皆然）无 ask 追问流（arbiter 恒为 null），本侧现产 answer / failed；
ask/nomatch 是 cube 三态概念，六值为两侧共用的超集。
"""

# v0 状态 → 作答卡 status 枚举
# "有答案无SQL"（知识库/概念题直答，无 SQL 无指标调用）属正当作答 → answer：
# 2026-10-23 烟测修正（曾误标 failed——M0 全数值题时代未出现该形态）；
# 有无 SQL 由卡上 sql_count 自己说话，裁决可见，不影响 status。
_SUCCESS_STATUSES = ("成功", "成功(指标路径)", "有答案无SQL")


def v0_status_to_card_status(status: str) -> str:
    if status in _SUCCESS_STATUSES:
        return "answer"
    if status.startswith("超时"):  # 驱动超时分支产出"超时(900s，部分输出)"
        return "timeout"
    if status.startswith("报错"):  # 引擎/工具真实报错（error=智能体答错/中断）
        return "error"
    return "failed"


def _hit(m: dict) -> dict:
    """metric_calls 条目 → metrics_hit 条目；query_metrics 附带的维度/时间条件透传。"""
    hit = {"tool": m["tool"], "depth": m["depth"], "names": m["names"]}
    for k in ("dimensions", "time_start", "time_end"):
        if k in m:
            hit[k] = m[k]
    return hit


def build_card(qid: str, question: str, extracted: dict, elapsed_s, raw_path: str) -> dict:
    """提取结果 + 运行元数据 → 11 字段作答卡。

    metrics_hit：工具级命中指标（过程证据）——tool/depth/names，query_metrics
    条目另带 dimensions/time_start/time_end（调用实参，无则不带键）；
    rows/desc 等展示性内容留在原始留痕（raw_path 可回查）。
    """
    return {
        "id": qid,
        "question": question,
        "status": v0_status_to_card_status(extracted["status"]),
        "metrics_hit": [_hit(m) for m in extracted["metric_calls"]],
        "sql": extracted["sql"],
        "sql_count": extracted["sql_count"],
        "answer": extracted["answer"],
        "errors": extracted["errors"],
        "elapsed_s": elapsed_s,
        "arbiter": None,  # datus 无 ask 流，M0 恒空
        "raw_path": raw_path,
    }

