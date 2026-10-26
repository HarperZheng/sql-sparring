"""值行提取步（D14，2026-10-26 拍板）：作答散文 → 值行数组，适配器直接产值行卡。

两侧适配器（ask_datus / ask_cube）共用：答案正文（散文，全文在 runs/ 留痕）交 LLM
结构化为值行，只抄数不推算；卡上不再落 answer 字段。提取失败降级为 values=[]
+ 卡 errors 记原因，不影响作答与状态（散文永远可回查 raw_path）。

模型配置：conf/models.json `extractor` 节（换模型换接口只改配置）——
  provider: claude-cli（缺省，本机 `claude -p`）| deepseek（OpenAI 兼容 /chat/completions）
  base_url_env / key_env / model / timeout_s 按需填。

值行契约（schemas/answer_card.schema.json）：metric 非空、unit ∈ 枚举、dims ≤2、
value 为数字或 null；合计/占比/排名等导出量不落行（清洗时剔除）；题目未问的
附加指标行不落行（2026-10-26 拍板：只改提取提示词，比对层不动，round-03 q11/q20 实测驱动）。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONF_PATH = REPO_ROOT / "conf" / "models.json"

UNIT_ENUM = ("元", "万元", "亿元", "笔", "张", "个", "天", "%")
EXPORT_PREFIXES = ("合计", "占比", "排名", "环比", "同比", "均值", "平均")
MAX_ROWS = 200
DEFAULT_TIMEOUT_S = 300

_PROMPT = """你是问数答案的结构化提取器。把下面的「答案正文」转成值行数组（JSON），只抄数不推算。

值行格式：{{"metric": "指标名", "unit": "单位", "dims": {{"维度名": "成员名"}}, "value": 数字或null}}
规则：
1. 只抄正文明确写出的数，不推算、不求和、不补行；正文没有数字就输出 []。
2. 只提取问题所问的原始计量行：旁注、解释性文字、题外数字、顺带提到的其他口径一律不要；合计/占比/排名/环比/同比/均值等可由其他行导出的量不要；题目未问的附加指标行（如只问金额时行里顺带给出的笔数、张数列）即使出现在「查询返回的结构化行」里也不要。
3. metric 优先从「命中指标」里取原词；都不贴切时用 未登记:<简短名>。
4. dims ≤2 对，维度名与成员名用正文原词；无维度分解写 {{}}。
5. unit 只能取：元/万元/亿元/笔/张/个/天/%。
6. value 是 JSON 数字或 null（正文明确说该行无数时用 null）；禁止字符串数字；百分数去掉 % 号且 unit="%"; 千分位逗号去掉。
7. 只输出 JSON 数组原文，不要解释、不要代码块围栏。

命中指标：{names}
问题：{question}

答案正文：
{answer}"""


def _load_conf() -> dict:
    conf = json.loads(CONF_PATH.read_text(encoding="utf-8"))
    return conf.get("extractor") or {}


def _call_llm(prompt: str, conf: dict, timeout_s: int) -> str:
    provider = conf.get("provider", "claude-cli")
    if provider == "claude-cli":
        import shutil
        claude = shutil.which("claude")
        if not claude:
            raise RuntimeError("找不到 claude 命令（provider=claude-cli）")
        proc = subprocess.run([claude, "-p"], input=prompt.encode("utf-8"),
                              capture_output=True, timeout=timeout_s)
        if proc.returncode != 0:
            raise RuntimeError(f"claude -p 退出码 {proc.returncode}: "
                               + proc.stderr.decode("utf-8", "replace")[:300])
        return proc.stdout.decode("utf-8", "replace")
    if provider == "deepseek":
        import urllib.request
        base = os.environ[conf["base_url_env"]].rstrip("/")
        body = json.dumps({
            "model": conf.get("model", "deepseek-chat"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode("utf-8")
        req = urllib.request.Request(
            base + "/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + os.environ[conf["key_env"]]})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    raise RuntimeError(f"未知 extractor provider: {provider!r}")


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\r?\n", "", t)
        if t.endswith("```"):
            t = t[:-3].rstrip()
    return t


def _parse_array(raw: str) -> list:
    """LLM 输出 → JSON 数组；容忍围栏与前后杂讯（取首个 [ 到末个 ]）。"""
    t = _strip_fences(raw)
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, list) else []
    except json.JSONDecodeError:
        i, j = t.find("["), t.rfind("]")
        if 0 <= i < j:
            obj = json.loads(t[i:j + 1])
            return obj if isinstance(obj, list) else []
        raise


def _to_number(v):
    """宽容收数：JSON 数字直过；"1,234.5"/"1,234.5%" 等字符串数字剥逗号与 % 转数字；
    其余（真文字串）返回 None 表示无数。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        s = v.strip().replace(",", "").rstrip("%").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def sanitize(raw_rows: list) -> tuple[list[dict], list[str]]:
    """LLM 原始输出 → 契约合法值行；逐条清洗，问题行剔除并记原因。"""
    rows, problems = [], []
    seen: set[tuple] = set()
    for i, item in enumerate(raw_rows):
        if len(rows) >= MAX_ROWS:
            problems.append(f"值行超上限 {MAX_ROWS}，其余丢弃")
            break
        if not isinstance(item, dict):
            problems.append(f"[{i}] 非对象，丢弃")
            continue
        metric = str(item.get("metric", "")).strip()
        if not metric:
            problems.append(f"[{i}] metric 为空，丢弃")
            continue
        if metric.split(":")[-1].startswith(EXPORT_PREFIXES):
            problems.append(f"[{i}] {metric!r} 是导出量，剔除")
            continue
        unit = str(item.get("unit", "")).strip()
        if unit not in UNIT_ENUM:
            problems.append(f"[{i}] {metric!r} unit={unit!r} 不在枚举，丢弃")
            continue
        dims = item.get("dims") or {}
        if not isinstance(dims, dict) or len(dims) > 2 \
                or not all(isinstance(k, str) and k and isinstance(v, str) and v
                           for k, v in dims.items()):
            problems.append(f"[{i}] {metric!r} dims 不合法（须 ≤2 对非空字符串），丢弃")
            continue
        value = _to_number(item.get("value"))
        if item.get("value") is not None and value is None:
            problems.append(f"[{i}] {metric!r} value 非数字，丢弃")  # null 语义=正文明确说无数，不得混用
            continue
        key = (metric, tuple(sorted(dims.items())))
        if key in seen:
            problems.append(f"[{i}] {metric!r} 重复键，丢弃")
            continue
        seen.add(key)
        rows.append({"metric": metric, "unit": unit, "dims": dims, "value": value})
    return rows, problems


def extract_values(question: str, answer_markdown: str,
                   metric_names: list[str] | None = None,
                   timeout_s: int | None = None) -> tuple[list[dict], list[str]]:
    """散文 → (值行, 问题清单)。正文为空或无数字 → ([], [])；LLM/解析失败 → ([], [原因])。"""
    if not (answer_markdown or "").strip():
        return [], []
    conf = _load_conf()
    timeout = timeout_s or int(conf.get("timeout_s", DEFAULT_TIMEOUT_S))
    names = "、".join(dict.fromkeys(metric_names or [])) or "（无）"
    prompt = _PROMPT.format(names=names, question=question, answer=answer_markdown)
    try:
        raw = _call_llm(prompt, conf, timeout)
        rows, problems = sanitize(_parse_array(raw))
    except Exception as e:  # 网络/超时/解析全降级：卡上 values=[] + errors 记原因
        return [], [f"值行提取失败: {str(e)[:300]}"]
    return rows, problems
