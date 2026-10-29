"""bin/round.py — 一轮互搏的编排器（M3）：自动跑 SOP ①–⑤，到轮报即停（D6）。

流程（对每轮）：
  ① 出题      题库 rounds/<轮>/questions.jsonl 不存在时调 bin/examine.py；已存在则跳过
  ② 双侧作答  datus/cube 两适配器进程并行（接口、留痕目录互不相干；侧内仍逐题串行；
              已有卡自动跳过，断点续跑；每侧日志 runs/<侧>.runlog.txt）
  ③ 卡校验    两侧作答卡逐份对 Schema（复用 schemas/validator.py）
  ④ 裁决关口  verdicts/<id>.json 缺任一题 → 打印缺单清单并停（退出码 2），等人工裁决
  ⑤ 轮报      全部裁决就绪后渲染 report.md（双侧状态+值行一致率 D14+分歧明细+复验集），
               即到系统段终点（D6：不自动回改；feedback.md 回改单不是本脚本产物——它由回改①创建）

回改五步（round.py 之外：①智能体（人调起）/ ②③⑤人 / ④本脚本）：
  ① 查证起草  人看过轮报分歧明细后调起智能体，codeqa 逐题查真实字段解法（过滤器+指标+维度+时间锚），
              由智能体创建 feedback.md 回改单（文件头契约+主表+回改卡；待查证→草案）
  ② 审定     人逐行审定（草案→已审定）
  ③ 施工     人按回改卡改双侧语义层（cube 拍板口径落词典属施工；→已施工）
  ④ 复验     本脚本 --retest 一条命令自动：清 datus chat memory（全量，不可逆、不做备份，用户拍板
              2026-10-26）→ 自动重启两服务 → 复验集=上轮分歧∩非剔除行、原题原 ID 重跑 → 裁决关口
              → 轮报（挂→回③，口径错→回①）。产物独立落 retest-rounds/round-<上轮>-r<K>，
              不占轮号（2026-10-29 拍板）；最新尝试已出轮报（完结）才开 r+1，未完结目录续用；
              无 --no-wipe——续跑=重跑同一条命令，再次清记忆并复位服务（2026-10-29 拍板取消）
  ⑤ 闭环     人复验通过且确认后置 feedback.md 行状态=闭环（无独立套件文件——
              feedback.md 即闭环账本，用户拍板 2026-10-26）

用法（Windows 侧 uv 环境）：
  uv run python bin/round.py --round round-02                 # 全流程（①–⑤）
  uv run python bin/round.py --round round-02 --only q01 q21  # 小样/子集（不产轮报）
  uv run python bin/round.py --retest round-02                # ④ 复验（M4 实现）：产物自动落
                                                              # retest-rounds/round-02-r<K>，不占轮号
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台缺省 GBK，中文输出转 UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from schemas.validator import check_cards_dir, check_verdicts_dir  # noqa: E402
from schemas.valuecmp import compare_round  # noqa: E402

SIDES = {"datus": "adapters.ask_datus", "cube": "adapters.ask_cube"}
NO_ANSWER_STATUSES = {"nomatch", "failed"}  # 共同缺口判定：两侧均此二态（implementation §四）


def load_questions(qpath: Path) -> dict[str, str]:
    out = {}
    for line in qpath.read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            out[q["id"]] = q["question"]
    return out


def run(cmd: list[str]) -> None:
    print(f"[round] $ {' '.join(str(c) for c in cmd)}", flush=True)
    rc = subprocess.run(cmd, cwd=REPO_ROOT).returncode
    if rc != 0:
        print(f"[round] 子命令失败（退出码 {rc}），终止", file=sys.stderr)
        sys.exit(1)


def step_examine(round_dir: Path, qpath: Path, name: str) -> None:
    if qpath.exists():
        n = len(load_questions(qpath))
        print(f"[①出题] 题库已存在，跳过（{qpath}，{n} 题）")
        return
    print("[①出题] 题库不存在，调 bin/examine.py …")
    run([sys.executable, str(REPO_ROOT / "bin" / "examine.py"),
         "--out", str(qpath), "--round", name])


def _log_tail(path: Path, n: int = 6) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [ln for ln in lines if ln.strip()][-n:]


def step_answer(round_dir: Path, qpath: Path, todo: list[str]) -> None:
    """双侧并行作答：datus/cube 接口互不相干（:8501 / :4100）、留痕目录分离，可安全并行；
    侧内仍逐题串行（题间隔离靠独立会话），并行只发生在侧与侧之间。
    任一侧失败不砍另一侧：两侧都跑完后统一报失败并退出码 1，已产卡保留（断点续跑可补）。"""
    procs: dict[str, tuple[subprocess.Popen, object]] = {}
    for side, module in SIDES.items():
        answers_dir = round_dir / "answers" / side
        missing = [qid for qid in todo if not (answers_dir / f"{qid}.json").exists()]
        if not missing:
            print(f"[②作答] {side}：{len(todo)} 卡齐全，跳过")
            continue
        log_path = round_dir / "runs" / f"{side}.runlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[②作答] {side}：待答 {len(missing)} 题（已有 {len(todo) - len(missing)} 卡）"
              f"→ 并行启动，日志 {log_path.name}")
        cmd = [sys.executable, "-m", module, "run", "--questions", str(qpath),
               "--only", *missing]
        print(f"[round] $ {' '.join(str(c) for c in cmd)}  > {log_path.name}", flush=True)
        log_f = log_path.open("w", encoding="utf-8")
        try:
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # 子进程输出统一 UTF-8，runlog 可读
            procs[side] = (subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=log_f,
                                            stderr=subprocess.STDOUT, env=env), log_f)
        except Exception:
            log_f.close()
            raise
    if not procs:
        return

    # 轮询进度：只数卡、不动进程；有变化才打一行
    last: dict[str, int] = {}
    while any(p.poll() is None for p, _ in procs.values()):
        time.sleep(20)
        counts = {s: len(list((round_dir / "answers" / s).glob("*.json"))) for s in procs}
        if counts != last:
            last = counts
            print("[②作答] 进行中 " + " · ".join(f"{s} {c}/{len(todo)}" for s, c in counts.items()),
                  flush=True)

    failed = []
    for side, (p, log_f) in procs.items():
        rc = p.wait()
        log_f.close()
        print(f"[②作答] {side} 结束：退出码 {rc}（日志尾部：）")
        for ln in _log_tail(round_dir / "runs" / f"{side}.runlog.txt"):
            print(f"    {side}| {ln}")
        if rc != 0:
            failed.append(side)
    if failed:
        print(f"[round] 作答失败侧：{'、'.join(failed)}（另一侧已产卡保留，断点续跑可补），终止",
              file=sys.stderr)
        sys.exit(1)


def check_cards(round_dir: Path, todo: list[str]) -> None:
    bad = False
    for side in SIDES:
        for fname, probs in check_cards_dir(round_dir / "answers" / side):
            print(f"[③校验] {side}/{fname}: {probs}", file=sys.stderr)
            bad = True
    for side in SIDES:
        answers_dir = round_dir / "answers" / side
        lack = [qid for qid in todo if not (answers_dir / f"{qid}.json").exists()]
        if lack:
            print(f"[③校验] {side} 缺卡：{lack}", file=sys.stderr)
            bad = True
    if bad:
        sys.exit(1)
    print(f"[③校验] 两侧 {len(todo)} 卡全过 Schema")


def load_verdicts(round_dir: Path, todo: list[str]) -> dict[str, dict]:
    verdicts_dir = round_dir / "verdicts"
    for fname, probs in check_verdicts_dir(verdicts_dir):
        print(f"[④裁决] {fname}: {probs}", file=sys.stderr)
        if probs:
            print("[④裁决] 裁决书不合 Schema，修正后重跑", file=sys.stderr)
            sys.exit(1)
    missing = [qid for qid in todo if not (verdicts_dir / f"{qid}.json").exists()]
    if missing:
        print(f"[④裁决] 裁决未完成：缺 {len(missing)} 份（{' '.join(missing)}）")
        print("[④裁决] 人工在环：对照 answers/<侧>/<id>.json 双侧卡逐题写 verdicts/<id>.json"
              "（Schema schemas/verdict.schema.json；D12：问题单 verdict_detail 数组记谁补建模/修bug）")
        print("[④裁决] 续跑：补齐裁决书后重跑本命令（复验模式会再次清记忆并复位服务，"
              "产物续用同一未完结目录——2026-10-29 拍板取消 --no-wipe）")
        sys.exit(2)
    extra = [f.stem for f in verdicts_dir.glob("*.json") if f.stem not in todo]
    if extra:
        print(f"[④裁决] 提示：verdicts/ 里存在不属于本轮的 {extra}")
    return {qid: json.loads((verdicts_dir / f"{qid}.json").read_text(encoding="utf-8"))
            for qid in todo}


# ---------- ⑤ 轮报 ----------

def _issues_line(v: dict) -> str:
    parts = [f"{i['side']}·{i['type']}·{i['target']}" for i in v.get("verdict_detail") or []]
    return "；".join(parts) if parts else "—"


def _gap_pair(cards: dict[str, dict]) -> bool:
    st = {s: (cards[s] or {}).get("status") for s in SIDES}
    return all(st[s] in NO_ANSWER_STATUSES for s in SIDES)


def render_report(round_dir: Path, name: str, questions: dict, todo: list[str],
                  verdicts: dict, cards: dict, retest_of: str | None = None) -> str:
    vc = Counter(v["verdict"] for v in verdicts.values())
    total = len(todo)
    gaps = [qid for qid in todo if _gap_pair({s: cards[s].get(qid) for s in SIDES})]
    vcr = compare_round(round_dir)  # 机械层（D14 两级判定）退居诊断参考；明细表列与参考行取此
    mech = Counter(q["verdict"] for q in vcr["questions"].values())
    status_lines = []
    for side in SIDES:
        sc = Counter((cards[side].get(qid) or {}).get("status", "?") for qid in todo)
        status_lines.append(f"| {side} | " + " / ".join(f"{k} {v}" for k, v in sorted(sc.items())) + " |")

    divergent = [qid for qid in todo if verdicts[qid]["verdict"] != "互证通过"]
    if retest_of:  # 复验轮自身仍有分歧：源轮不变（feedback.md 在源轮），继续对源轮复验
        retest_hint = (f"仍挂题回③施工后继续：uv run python bin/round.py --retest {retest_of}，"
                       f"产物 retest-rounds/{retest_of}-r<K+1>")
    else:
        retest_hint = (f"④复验：uv run python bin/round.py --retest {name}，"
                       f"产物自动落 retest-rounds/{name}-r1 起，不占轮号")

    if retest_of:  # 闭环率=复验集互证通过数/复验集总数（implementation §四）
        passed = sum(1 for qid in todo if verdicts[qid]["verdict"] == "互证通过")
        close_cell = f"{passed}/{total} = {passed / total:.0%}（互证通过数/复验集总数）"
    else:
        close_cell = "—（首轮，无上轮分歧题）"

    head = [
        f"# {name} 轮报",
        "",
        f"- 日期：{date.today().isoformat()}　题数：{total}",
    ]
    if retest_of:
        head.append(f"- 复验自：{retest_of}（回改④复验：清记忆+服务复位后，原题原 ID 重跑）")
    head += [
        "- 双侧作答状态：",
        *status_lines,
        "",
        "## 四指标",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| 一致率（裁决：互证通过/题数） | {vc.get('互证通过', 0)}/{total}"
        f" = {vc.get('互证通过', 0) / total:.1%} |",
        f"| 分歧分布（裁决四态） | 互证通过 {vc.get('互证通过', 0)} / 建模差异 {vc.get('建模差异', 0)}"
        f" / 执行事故 {vc.get('执行事故', 0)} / 待人工 {vc.get('待人工', 0)} |",
        f"| 差距数（双侧共同缺口） | {len(gaps)}（{' '.join(gaps) if gaps else '无'}） |",
        f"| 闭环率 | {close_cell} |",
        "",
        "一致率=裁决互证通过数÷题数（2026-10-26 拍板改口径：互证通过即一致，原 D14 机械一致率退居诊断）。"
        "机械层参考——值行两级判定（D14）："
        f"一致 {mech['一致']} / 不一致 {mech['不一致']} / 待复核 {mech['待复核']}；"
        "行级明细与单侧行清单：`python -m schemas.valuecmp --round <轮>`（待复核走别名登记翻案）。",
        "",
        "## 分歧明细",
        "",
        "| id | 问题 | 裁决 | 值行比对 | 问题单 |",
        "|---|---|---|---|---|",
    ]
    lines = head

    def _qtext(qid: str) -> str:
        t = questions[qid]
        return t if len(t) <= 30 else t[:29] + "…"

    def _vcell(qid: str, diag: bool = True) -> str:
        # diag=True：明细口径（分歧明细用，服务回改①查证，不参与判定）；
        # diag=False：题级两级判定结论（互证通过明细用，与 valuecmp CLI 题级结论同源）
        qcmp = vcr["questions"].get(qid)
        if not qcmp:
            return "—"
        if diag:
            return (f"{qcmp['diag_verdict']}（{qcmp['diag_reason']}；"
                    f"附加行 datus {len(qcmp['extra_datus'])}/cube {len(qcmp['extra_cube'])}）")
        return f"{qcmp['verdict']}（{qcmp['reason']}）"

    for qid in divergent:
        v = verdicts[qid]
        lines.append(f"| {qid} | {_qtext(qid)} | {v['verdict']} | {_vcell(qid)} | {_issues_line(v)} |")

    passed_ids = [qid for qid in todo if verdicts[qid]["verdict"] == "互证通过"]
    lines += ["", f"## 互证通过明细（{len(passed_ids)} 题）", ""]
    if passed_ids:
        lines += ["| id | 问题 | 值行两级判定（题级） | 互证要点 |", "|---|---|---|---|"]
        for qid in passed_ids:
            summary = ((verdicts[qid].get("comparison") or {}).get("summary") or "").strip().rstrip("。")
            if len(summary) > 40:
                summary = summary[:39] + "…"
            lines.append(f"| {qid} | {_qtext(qid)} | {_vcell(qid, diag=False)} | {summary} |")
    else:
        lines += ["（无——全部题存在分歧，见分歧明细）"]

    # 复验集 ids 必须是节标题后的首个非空行（parse_report_retest_ids 按此解析），提示语放在 ids 之后
    lines += ["", "## 复验集", "",
              "、".join(divergent) if divergent else "（无——全部互证通过）", "",
              f"（{retest_hint}）", ""]
    out = round_dir / "report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ---------- ④ 复验（--retest，M4） ----------

DATUS_WSL_DIR = "/mnt/d/develop/datus/Datus-agent"
DATUS_CHAT_MEMORY = f"{DATUS_WSL_DIR}/.datus/memory/chat"
CUBE_DIR = REPO_ROOT.parent / "cube"


def wsl_bash(script: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["wsl.exe", "-e", "bash", "-c", script],
                          capture_output=True, text=True, timeout=timeout)


def parse_report_retest_ids(report_path: Path) -> list[str]:
    """读上轮轮报「复验集」节题号（、分隔），保持出现顺序。"""
    text = report_path.read_text(encoding="utf-8")
    m = re.search(r"## 复验集[^\n]*\n\n?([^\n#]+)", text)
    if not m:
        print(f"[④复验] 上轮轮报无复验集节：{report_path}", file=sys.stderr)
        sys.exit(1)
    ids = re.findall(r"q\d+", m.group(1))
    if not ids:
        print("[④复验] 上轮复验集为空（全部互证通过）——无需复验", file=sys.stderr)
        sys.exit(1)
    return ids


def parse_feedback_main_ids(feedback_path: Path) -> set[str]:
    """读回改单主表行 id（剔除题不进主表，主表行即非剔除行）。"""
    ids = set()
    for ln in feedback_path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("| q"):
            cell = ln.split("|")[1].strip()
            if re.fullmatch(r"q\d+", cell):
                ids.add(cell)
    if not ids:
        print(f"[④复验] 回改单主表无行：{feedback_path}", file=sys.stderr)
        sys.exit(1)
    return ids


def step_retest_setup(name: str, prev: str, qpath: Path) -> list[str]:
    """复验集=上轮轮报复验集 ∩ 回改单主表（非剔除行）；原题原 ID 复制进复验轮目录题库（盲考不变）。"""
    prev_dir = REPO_ROOT / "rounds" / prev
    prev_questions = prev_dir / "questions.jsonl"
    for must in (prev_questions, prev_dir / "report.md", prev_dir / "feedback.md"):
        if not must.exists():
            print(f"[④复验] 上轮缺文件：{must}", file=sys.stderr)
            sys.exit(1)
    report_ids = parse_report_retest_ids(prev_dir / "report.md")
    fb_ids = parse_feedback_main_ids(prev_dir / "feedback.md")
    todo = [q for q in report_ids if q in fb_ids]
    dropped = [q for q in report_ids if q not in fb_ids]
    if dropped:
        print(f"[④复验] 轮报复验集被回改单剔除的题（不进复验）：{dropped}")
    if not todo:
        print("[④复验] 复验集与回改单主表交集为空", file=sys.stderr)
        sys.exit(1)
    if qpath.exists():
        print(f"[④复验题库] 已存在，跳过复制（{qpath}，{len(load_questions(qpath))} 题）")
        return todo
    qmap = load_questions(prev_questions)
    lack = [q for q in todo if q not in qmap]
    if lack:
        print(f"[④复验] 上轮题库缺题：{lack}", file=sys.stderr)
        sys.exit(1)
    kept = [ln for ln in prev_questions.read_text(encoding="utf-8").splitlines()
            if ln.strip() and json.loads(ln).get("id") in set(todo)]
    qpath.parent.mkdir(parents=True, exist_ok=True)
    qpath.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"[④复验题库] 原题原 ID 复制 {len(kept)} 题 ← {prev}/questions.jsonl")
    return todo


def _poll_port(port: int, want_open: bool, timeout_s: int) -> bool:
    import socket
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        s = socket.socket()
        s.settimeout(2)
        try:
            s.connect(("localhost", port))
            s.close()
            if want_open:
                return True
        except OSError:
            if not want_open:
                return True
        s.close()
        time.sleep(3)
    return False


def retest_services_reset(round_dir: Path) -> None:
    """④复验服务复位（不可逆步骤单列执行）：
    ① 停 datus → ② 全量清 chat memory（不可逆、不做备份，用户拍板 2026-10-26）
    → ③ WSL 拉起 datus --web → ④ docker compose restart cube → ⑤ preflight 四项过闸。
    动作留痕 rounds/<轮>/runs/retest.log（含删除前文件盘点）。"""
    log_path = round_dir / "runs" / "retest.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def alog(msg: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    alog("== ④复验服务复位开始 ==")
    # ① 停 datus（旧进程持有 chat memory，先停后清）
    alog("① 停 datus --web（WSL pkill）")
    wsl_bash("pkill -f 'datus --web' || true")
    if not _poll_port(8501, want_open=False, timeout_s=30):
        alog("   :8501 仍在 → pkill -9 强杀")
        wsl_bash("pkill -9 -f 'datus --web' || true")
        _poll_port(8501, want_open=False, timeout_s=30)

    # ② 全量清 chat memory（不可逆！前置校验=盘点留痕；回退=无，用户拍板不做备份；
    #    2026-10-29 拍板取消 --no-wipe：复验续跑重跑本命令即再次全量清，无跳过模式）
    inv = wsl_bash(f"ls -la {DATUS_CHAT_MEMORY} 2>/dev/null; "
                   f"echo COUNT=$(ls {DATUS_CHAT_MEMORY} 2>/dev/null | wc -l)")
    alog("② 全量清 datus chat memory（不可逆、无备份）——删除前盘点：")
    for ln in (inv.stdout or "").strip().splitlines():
        alog("   " + ln)
    wsl_bash(f"rm -rf {DATUS_CHAT_MEMORY}/*")
    after = (wsl_bash(f"ls {DATUS_CHAT_MEMORY} 2>/dev/null | wc -l").stdout or "").strip()
    if after != "0":
        print("[④复验] chat memory 清理后未确认为空，终止", file=sys.stderr)
        sys.exit(1)
    alog(f"   清后余 {after} 项（盘点已留痕 retest.log；无备份，不可回退）")

    # ③ WSL 拉起 datus --web（venv 归 WSL 所有，uv 只在 WSL 侧跑）
    alog("③ WSL 拉起 datus --web（datasource yunnan0508）")
    wsl_bash(f"cd {DATUS_WSL_DIR} && nohup uv run datus --web --datasource yunnan0508 "
             f"--permission-mode auto >> {DATUS_WSL_DIR}/.datus/logs/retest-datus.log "
             f"2>&1 < /dev/null &", timeout=30)
    if not _poll_port(8501, want_open=True, timeout_s=240):
        print("[④复验] datus :8501 未就绪，停机", file=sys.stderr)
        sys.exit(1)
    alog("   :8501 就绪")

    # ④ cube 重启（docker compose 强制重载 schema）
    alog("④ docker compose restart cube（强制重载 schema）")
    subprocess.run(["docker", "compose", "restart", "cube"],
                   cwd=str(CUBE_DIR), capture_output=True, text=True, timeout=300)
    if not _poll_port(4000, want_open=True, timeout_s=180):
        print("[④复验] cubejs :4000 未就绪，停机", file=sys.stderr)
        sys.exit(1)
    alog("   :4000 就绪")
    if not _poll_port(4100, want_open=True, timeout_s=30):
        alog("   :4100 agent-svc 缺失 → start.cmd 补启")
        subprocess.Popen(["cmd", "/c", "start", "", r"D:\develop\cube\start.cmd"])
        if not _poll_port(4100, want_open=True, timeout_s=120):
            print("[④复验] agent-svc :4100 未就绪，停机", file=sys.stderr)
            sys.exit(1)
    alog("   :4100 就绪")

    # ⑤ preflight 四项过闸（语义层 YAML 可解析 + 三服务可达 + 词典可枚举）；
    #   cube 重启后 meta 接口热身期可能 500（2026-10-26 round-03 实测），最多重试 3 次
    for attempt in range(1, 4):
        alog(f"⑤ preflight 四项检查过闸（第 {attempt}/3 次）")
        rc = subprocess.run([sys.executable, str(REPO_ROOT / "bin" / "preflight.py")],
                            cwd=REPO_ROOT).returncode
        if rc == 0:
            break
        if attempt < 3:
            alog("   未全过 → 30s 后重试（服务热身等待）")
            time.sleep(30)
    else:
        print("[④复验] preflight 3 次未全过，停机（退出码≠0）", file=sys.stderr)
        sys.exit(1)
    alog("== ④复验服务复位完成 ==")


def main():
    ap = argparse.ArgumentParser(prog="round", description="一轮互搏编排器（SOP ①–⑤，D6 到轮报即停）")
    ap.add_argument("--round", default=None, help="轮号，如 round-02（复验模式不需要，产物自动命名）")
    ap.add_argument("--only", nargs="*", default=None, help="只跑这些 id（小样/子集；不产轮报）")
    ap.add_argument("--retest", default=None,
                    help="（M4）复验上轮：产物自动落 retest-rounds/round-<上轮>-r<K> 不占轮号；"
                         "清记忆+重启两服务+原题重跑到轮报；闭环=人置 feedback.md 行状态")
    args = ap.parse_args()

    if args.retest:
        if not re.match(r"round-\d+$", args.retest):
            ap.error("--retest 形如 round-02")
        if args.round:
            ap.error("--retest 模式产物自动命名（retest-rounds/round-<上轮>-r<K>），不需要 --round")
        # 产物目录自动命名（2026-10-29 拍板）：最新尝试已出轮报（完结）才开下一号 r+1；
        # 未完结目录续用（断点续跑不换目录）。弃用未完结目录=人手动删除，重跑即重开该号
        base = f"round-{int(args.retest.split('-')[1]):02d}"
        retest_root = REPO_ROOT / "retest-rounds"
        k = 1
        while (retest_root / f"{base}-r{k}" / "report.md").exists():
            k += 1
        name = f"{base}-r{k}"
        round_dir = retest_root / name
        qpath = round_dir / "questions.jsonl"
        # 先校验上轮三件套（缺即退出），再落目录——不产残缺空目录
        step_retest_setup(name, args.retest, qpath)
        round_dir.mkdir(parents=True, exist_ok=True)
        retest_services_reset(round_dir)
    else:
        if not args.round:
            ap.error("--round 必填（跑复验用 --retest <上轮>，产物自动命名）")
        if not re.match(r"round-\d+$", args.round):
            ap.error("--round 形如 round-02")
        name = args.round
        round_dir = REPO_ROOT / "rounds" / name
        round_dir.mkdir(parents=True, exist_ok=True)
        qpath = round_dir / "questions.jsonl"
        step_examine(round_dir, qpath, name)
    questions = load_questions(qpath)
    todo = [qid for qid in questions if not args.only or qid in args.only]
    if not todo:
        print("--only 未匹配任何题", file=sys.stderr)
        sys.exit(1)

    step_answer(round_dir, qpath, todo)
    cards = {s: {qid: json.loads((round_dir / "answers" / s / f"{qid}.json").read_text(encoding="utf-8"))
                 for qid in todo if (round_dir / "answers" / s / f"{qid}.json").exists()}
             for s in SIDES}
    check_cards(round_dir, todo)
    verdicts = load_verdicts(round_dir, todo)

    if args.only:
        print(f"[round] 子集模式（{len(todo)} 题）到裁决关口为止，不产轮报")
        return

    report = render_report(round_dir, name, questions, todo, verdicts, cards, retest_of=args.retest)
    print(f"[⑤轮报] {report}")
    print("[round] 系统段终点（D6）：到轮报为止；feedback.md 回改单由回改①创建"
          "（人看过轮报后调起智能体，codeqa 逐题查证）——②审定→③施工→④--retest 复验→"
          "⑤闭环（人置 feedback.md 行状态=闭环，无套件文件）")


if __name__ == "__main__":
    main()
