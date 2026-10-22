"""拍板政策：cube ask 态（反问口径）时适配器的自动应答规则。

v0 同款（2026-10-21 首轮实测）：固定取第一个选项；无选项则要求按最常见口径直出。
拍板动作全程记录进作答卡 arbiter 字段——裁决时"自动拍板"与"人拍板"区分对待（§三）。
"""

FOLLOWUP_TEMPLATE = "就按第一个选项的口径来（%s），直接出答案。"
FOLLOWUP_FALLBACK = "按最常见口径直接出答案"


def followup_message(response: dict) -> str:
    """ask 响应 → 追问文案。"""
    options = response.get("options") or []
    pick = options[0] if options else FOLLOWUP_FALLBACK
    return FOLLOWUP_TEMPLATE % pick


def arbiter_record(first_type: str, response: dict, followups: list) -> dict | None:
    """拍板全程记录：first_type/反问原文/选项/每次追问与结果。非 ask 流返回 None。"""
    if first_type != "ask":
        return None
    return {
        "mode": "auto",  # 自动拍板（人拍板为 "human"，v1 人工在环时出现）
        "policy": "option-1",
        "ask_question": response.get("question", ""),
        "options": response.get("options") or [],
        "followups": followups,  # [{question, response_type, elapsed_s}]
    }
