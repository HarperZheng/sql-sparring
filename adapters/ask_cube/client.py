""":4100/chat 客户端与编译 SQL 抓取。

链路（v0 实测，09-cube 记录）：POST :4100/chat {question, sessionId} → agent-svc
→ cube-ask skill → /agent/query。每问新 sessionId（题间零污染）；
失败重试一次（换新 sessionId，避免 resume 到坏上下文，v0 同款）。
"""

import httpx

CHAT_URL = "http://localhost:4100/chat"
SQL_URL = "http://localhost:4000/cubejs-api/v1/sql"
CHAT_TIMEOUT_S = 660.0   # v0 实测同款：单问上限 11 分钟
SQL_TIMEOUT_S = 60.0
CUBE_ROOT = r"D:\develop\cube"  # 读 .env 取 CUBEJS_API_SECRET（生产现配，不动）


def _cubejs_secret() -> str:
    path = None
    from pathlib import Path
    path = Path(CUBE_ROOT) / ".env"
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("CUBEJS_API_SECRET="):
            return line.split("=", 1)[1].strip().strip('"').strip("\r")
    raise RuntimeError(f"{path} 中未找到 CUBEJS_API_SECRET")


def post_chat(question: str, session_id: str) -> dict:
    """一问 → 响应 dict（含 type: answer|ask|nomatch|error）。网络异常向上抛。"""
    with httpx.Client(timeout=httpx.Timeout(CHAT_TIMEOUT_S)) as client:
        r = client.post(CHAT_URL, json={"question": question, "sessionId": session_id})
        r.raise_for_status()
        return r.json()


def fetch_compiled_sql(query: dict) -> str:
    """语义层 query JSON → Cube 编译的 ClickHouse SQL（失败返回注释说明，不抛）。"""
    try:
        with httpx.Client(timeout=httpx.Timeout(SQL_TIMEOUT_S)) as client:
            r = client.post(
                SQL_URL, json={"query": query},
                headers={"Authorization": "Bearer " + _cubejs_secret()})
            r.raise_for_status()
            sql = r.json().get("sql", {}).get("sql")
            if sql:
                return _flatten(sql)
            return "-- /v1/sql 无 sql 字段"
    except Exception as e:  # 留痕尽力而为，不阻断作答
        return f"-- /v1/sql 失败: {e}"


def _flatten(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return "".join(_flatten(i) for i in x)
    return str(x)
