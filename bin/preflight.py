"""开跑前健康检查（M2 四件套之四）：双侧服务可达 + 语义层可解析。

**单次执行**：顺序跑完四项检查、打印结论、以退出码结束（0=全过，1=有挂）。
无循环、无排程、不留档、不落作答卡、不消耗答题人 LLM 调用（不发探题）。
用法：开跑前人手动跑一次；M3 起轮驱动器（bin/round.py）开轮时调用一次。

  uv run python bin/preflight.py

检查项（防的都是 M0 实测过的真实事故）：
  1. datus 语义层 YAML 可解析——裁决回灌人工改坏 YAML，下轮开跑才发现；
  2. datus chat API :8501 可达——常驻服务（datus --web）没起/挂了；
  3. cube agent-svc :4100 可达且词典可枚举——常驻服务没起/挂了；
  4. cubejs :4000 可达（编译 SQL 抓取依赖）——同上。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import httpx  # noqa: E402
import yaml  # noqa: E402

# trust_env=False：绕过 Windows 注册表系统代理劫持 localhost 请求的坑
# （M0 实测 2026-10-22，见 adapters/ask_cube/client.py 注记）。
_HTTP_KW = {"trust_env": False, "timeout": 30.0}


def check_datus_yaml(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, f"文件不存在: {path}"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"YAML 解析失败: {str(e)[:200]}"
    if not isinstance(data, dict) or not data:
        return False, "YAML 顶层不是非空映射"
    top = ", ".join(list(data.keys())[:6])
    return True, f"可解析，顶层键: {top}"


def check_datus_api() -> tuple[bool, str]:
    """:8501 chat API 存活探针（GET /openapi.json；不发探题、不耗 LLM 调用）。"""
    return _probe("http://localhost:8501/openapi.json")


def _probe(url: str, headers: dict | None = None) -> tuple[bool, str]:
    try:
        with httpx.Client(**_HTTP_KW) as c:
            r = c.get(url, headers=headers or {})
    except Exception as e:
        return False, f"不可达: {str(e)[:200]}"
    if r.is_success:
        return True, f"HTTP {r.status_code}"
    return False, f"HTTP {r.status_code}（服务在但接口异常）"


def check_cube_agent_svc() -> tuple[bool, str]:
    """:4100 agent-svc 存活探针（GET /health；不发探题、不耗 LLM 调用）。"""
    return _probe("http://localhost:4100/health")


def check_cube_gateway() -> tuple[bool, str]:
    """:4000 网关双查：cubejs meta + /agent/dictionary（词典枚举，挂 :4000 agent-api）。"""
    from adapters.ask_cube import client

    try:
        secret = client._cubejs_secret()
    except Exception as e:
        return False, f"取 CUBEJS_API_SECRET 失败: {str(e)[:200]}"
    auth = {"Authorization": "Bearer " + secret}
    meta_url = client.SQL_URL.rsplit("/", 1)[0] + "/meta"
    ok_meta, d_meta = _probe(meta_url, headers=auth)
    ok_dict, d_dict = _probe("http://localhost:4000/agent/dictionary", headers=auth)
    ok = ok_meta and ok_dict
    return ok, f"meta: {d_meta}; 词典: {d_dict}"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="开跑前健康检查（单次执行，退出码 0/1）")
    ap.add_argument("--datus-yaml",
                    default=r"D:\develop\datus\Datus-agent\subject\semantic_models\yunnan0508\fne_fund_main.yml")
    args = ap.parse_args()

    checks = [
        ("datus 语义层 YAML 可解析", lambda: check_datus_yaml(Path(args.datus_yaml))),
        ("datus chat API :8501 存活", check_datus_api),
        ("cube agent-svc :4100 存活", check_cube_agent_svc),
        ("cube :4000 网关（meta+词典）", check_cube_gateway),
    ]
    all_ok = True
    for name, fn in checks:
        ok, detail = fn()
        all_ok &= ok
        print(f"{'✓' if ok else '✗'} {name} — {detail}", flush=True)
    print("\n结论: " + ("全部通过，可开跑" if all_ok else "有检查项未过——先修再考（单次执行结束）"))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
