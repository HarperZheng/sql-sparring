"""Windows 侧驱动：逐题调度 WSL 内 datus，回收留痕并组装作答卡。

链路：题目写文件 → wsl.exe 调 wsl_runner.py（文件交接）→ payload 落盘 →
extractor 提取 → 11 字段作答卡落盘。
幂等（§三契约）：--only 子集复跑；作答卡覆盖写，原始留痕按时间戳归档不覆盖。
"""

import json
import shutil
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_SCRIPT = Path(__file__).with_name("wsl_runner.py")

# 生产现配（不动，Q1）：datus 在 WSL，GLM-5.3-Flash 经既有 portproxy relay
WSL_DISTRO = "Ubuntu-26.04"
WSL_PYTHON = "/mnt/d/develop/datus/Datus-agent/.venv/bin/python"
DATUS_ROOT = "/mnt/d/develop/datus/Datus-agent"
DEFAULT_TIMEOUT_S = 900
WINDOWS_SLACK_S = 60  # Windows 侧兜底超时 = WSL 超时 + 余量，防 wsl.exe 挂死


def to_wsl_path(win_path: Path) -> str:
    """D:\\a\\b → /mnt/d/a/b（仅本仓约定的盘符映射）。"""
    p = win_path.resolve()
    return f"/mnt/{p.drive[0].lower()}{p.as_posix()[2:]}"


def _archive_existing(path: Path) -> str | None:
    """留痕不覆盖：已有文件挪为 <stem>.<时间戳><后缀>，返回归档名。"""
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archived = path.with_name(f"{path.stem}.{stamp}{path.suffix}")
    shutil.move(str(path), str(archived))
    return archived.name


def run_question(qid: str, question: str, runs_dir: Path, timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    """跑一题，返回 {card, extracted, meta}。落盘：题目/留痕/meta 在 runs_dir。"""
    runs_dir.mkdir(parents=True, exist_ok=True)
    q_file = runs_dir / f"{qid}.question.txt"
    q_file.write_text(question, encoding="utf-8")
    payload = runs_dir / f"{qid}.payload.jsonl"
    stderr_f = runs_dir / f"{qid}.stderr.txt"
    meta_f = runs_dir / f"{qid}.meta.json"

    archived = _archive_existing(payload)
    archived_err = _archive_existing(stderr_f)

    cmd = [
        "wsl.exe", "-d", WSL_DISTRO, "--", WSL_PYTHON, to_wsl_path(RUNNER_SCRIPT),
        "--question-file", to_wsl_path(q_file),
        "--out-payload", to_wsl_path(payload),
        "--out-stderr", to_wsl_path(stderr_f),
        "--out-meta", to_wsl_path(meta_f),
        "--datus-root", DATUS_ROOT,
        "--timeout", str(timeout_s),
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout_s + WINDOWS_SLACK_S)
    if proc.returncode != 0:
        raise RuntimeError(
            f"wsl_runner 失败 rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[-500:]}")

    meta = json.loads(meta_f.read_text(encoding="utf-8"))
    lines = payload.read_text(encoding="utf-8").splitlines()
    from . import extractor
    extracted = extractor.extract(
        lines, timed_out=meta["timed_out"], timeout_s=timeout_s)
    return {
        "extracted": extracted,
        "meta": meta,
        "archived": {"payload": archived, "stderr": archived_err},
        "payload_rel": str(payload.relative_to(REPO_ROOT)).replace("\\", "/"),
    }


def build_and_write_card(qid: str, question: str, result: dict, answers_dir: Path) -> Path:
    """提取结果 → 作答卡 → 落盘（覆盖写）。返回卡片路径。"""
    from .card import build_card
    card = build_card(
        qid, question, result["extracted"],
        elapsed_s=result["meta"]["elapsed_s"],
        raw_path=result["payload_rel"],
    )
    answers_dir.mkdir(parents=True, exist_ok=True)
    out = answers_dir / f"{qid}.json"
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
