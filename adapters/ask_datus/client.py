""":8501 chat API 客户端（SSE 流）→ MessagePayload 行序列（与 ask_cube/client.py 同构）。

链路（2026-10-23 活体实测）：POST http://localhost:8501/api/v1/chat/stream
{message, session_id, max_turns} → SSE（event: session|message|usage|end|error）。
message 事件 data = {"type":"createMessage","payload":{MessagePayload}}，内层
payload 与 datus -p 落盘格式同构——extractor 不改，只解 SSE 壳。
每问新 session_id（题间零污染，与 cube 同款）；agent 配置/语义模型只在常驻
服务启动时装一次（UI 回答快的根源，也是本通道替换 WSL 桥的动机）。
"""

import json
import time

import httpx

CHAT_URL = "http://localhost:8501/api/v1/chat/stream"

# 墙钟上限：读超时（httpx read timeout）只拦"流静默"，拦不住"流一直有字节但活儿
# 干不完"——2026-10-23 实测 q16 空转 33 分钟（:8501 连接活跃、无 ClickHouse 查询）。
# 墙钟只看单题总耗时，到点即断（用户拍板 3 分钟），驱动层记超时卡后换下一题。
WALL_CLOCK_S = 180.0

# trust_env=False：httpx 默认经 urllib 读 Windows 注册表系统代理，localhost
# 请求被代理劫持返回空 502（M0 实测 2026-10-22，同 ask_cube/client.py 注记）。
_CLIENT_KW = {"trust_env": False}


class ChatTimeout(Exception):
    """单题超时（读超时或墙钟到点，D10 一等留痕）。partial=已收到的 payload 行（截断留证）。"""

    def __init__(self, partial: list[str], timeout_s: float):
        super().__init__(f"chat API 单题超时（>{timeout_s}s，已收 {len(partial)} 段 payload）")
        self.partial = partial
        self.timeout_s = timeout_s


def post_chat_stream(question: str, session_id: str, timeout_s: float = 900.0,
                     max_turns: int = 30, wall_clock_s: float = WALL_CLOCK_S,
                     subagent_id: str | None = None) -> tuple[list[str], dict]:
    """一问 → (payload 行列表, 汇总 dict)。HTTP/网络类异常向上抛（驱动层重试）。

    payload 行即 extractor.extract() 的输入，与 datus -p 的 payload 文件同格式；
    汇总 dict 记 end/usage 事件的 duration/requests/tokens（驱动层落 meta 留痕）。
    两道闸：读超时=流静默 timeout_s 秒；墙钟=单题总耗时超 wall_clock_s 秒（每行检查）。
    触发任一即抛 ChatTimeout，携带已收到的部分 payload。
    subagent_id：路由字段（StreamChatInput，"builtin name or DB SubAgent id"）——
    传内置名 "ask_metrics" 经 node_factory 落到 AskMetricsAgenticNode（唯一
    query_metrics 挂载点）；缺省 None=默认 chat 节点（自由 SQL 通道）。
    """
    payloads: list[str] = []
    summary: dict = {"duration_s": None, "requests": None, "total_tokens": None}
    body = {"message": question, "session_id": session_id, "max_turns": max_turns}
    if subagent_id:
        body["subagent_id"] = subagent_id
    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout_s, connect=10.0), **_CLIENT_KW) as client:
            with client.stream("POST", CHAT_URL, json=body) as resp:
                resp.raise_for_status()
                event, data = "", ""
                for line in resp.iter_lines():
                    if time.monotonic() - t0 > wall_clock_s:  # 墙钟：总耗时到点即断
                        raise ChatTimeout(payloads, wall_clock_s)
                    if line.startswith(":"):  # SSE 注释（keep-alive）
                        continue
                    if line.startswith("event: "):
                        event = line[len("event: "):].strip()
                    elif line.startswith("data: "):
                        data += line[len("data: "):].strip()
                    elif line == "" and event:
                        _consume(event, data, payloads, summary)
                        event, data = "", ""
                if event:  # 流尾缺空行分隔的最后一块
                    _consume(event, data, payloads, summary)
    except httpx.TimeoutException:
        raise ChatTimeout(payloads, timeout_s) from None
    return payloads, summary


def _consume(event: str, data: str, payloads: list[str], summary: dict):
    """一个完整 SSE 块：message→收 payload 行；end/usage→记汇总；error→抛（可重试）。"""
    if not data:
        return
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        return
    if event == "message":
        if isinstance(obj, dict) and isinstance(obj.get("payload"), dict):
            payloads.append(json.dumps(obj["payload"], ensure_ascii=False))
    elif event == "end":
        summary.update({"duration_s": obj.get("duration"), "requests": obj.get("requests"),
                        "total_tokens": obj.get("tokens")})
    elif event == "usage":
        summary["usage"] = obj
    elif event == "error":
        raise RuntimeError(f"chat API error 事件: {data[:300]}")
