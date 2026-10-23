"""datus chat API 客户端——本适配器对 datus 的全部调用就是这一个 HTTP 接口
（与 ask_cube/client.py 同构：只解 SSE 壳，业务痕迹交 extractor.py 解析）。

接口  POST http://localhost:8501/api/v1/chat/stream（datus --web 常驻服务）
输入  body = {"message":     题目原文（自然语言）,
              "session_id":  "sparring-q01-m"，每问新开（题间零污染）,
              "max_turns":   30（工具轮上限）,
              "subagent_id": "ask_metrics"}    # 路由字段：指标问答节点
                                               # （query_metrics 唯一挂载点）；
                                               # 缺省=默认 chat 节点
返回  SSE 流（event: session|message|usage|end|error），逐块解析：
      message 块 → data["payload"] 是一条 MessagePayload，剥壳后逐行 append 进
                   返回值 payloads（与 datus -p 落盘同格式）；
      end 块    → duration/requests/tokens 记入 summary；
      error 块  → 抛 RuntimeError（网络类，驱动层重试）。

匹配指标 / 获得 SQL / 执行 SQL 三步都在 datus 服务内部完成，本文件只经 :8501、
零数据库依赖；每步的痕迹落在返回的 MessagePayload 行里（content[].type 分
call-tool / call-tool-result，extractor.py 按此提取）：

  匹配指标  call-tool：toolName=search_metrics（输入 toolParams={"query_text":
            "缴库"}，在语义层找有哪些指标）或 get_metric（输入 toolParams=
            {"name":"缴库金额"}，取该指标定义）；配对 call-tool-result 的
            result.result = 命中的指标清单 / 指标定义。
  获得 SQL  call-tool：toolName=query_metrics，输入 toolParams={"metrics":
            ["缴库金额"], "dimensions":[...], "time_start", "time_end",
            "time_granularity"}——datus 侧 LLM 只出参数不写 SQL，SQL 由 dosi
            引擎按语义模型 yml（datus 仓 subject/semantic_models/yunnan0508/
            fne_fund_main.yml）编译；SQL 全文不经 LLM、也不出现在返回体
            （工具层故意剥离，datus 仓 semantic_tools.py:1412——防 LLM 上下文
            膨胀）；实际执行原文由 datus 侧日志旁路留痕（dosi/runtime.py 的
            dosi_sql_executed 行，2026-10-23 v4 加），evidence.py 按题时间窗
            提取进作答卡。datus 另有 dry_run=true 只编译不执行的用法，
            本适配器不走。
  执行 SQL  同一 query_metrics 调用内：dosi 引擎在 datus 服务内对
            ClickHouse 执行（连接/账号配在 datus 仓 conf/agent.yml
            datasources.yunnan0508）；配对 call-tool-result 的
            result.result.data.compressed_data = CSV 数据行，回给 LLM 作答。

agent 配置/语义模型只在常驻服务启动时装一次（UI 回答快的根源，也是本通道
替换 WSL 桥的动机）。
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
