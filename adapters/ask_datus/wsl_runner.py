"""WSL 内执行器：跑一题 `datus -p`，payload 流原样落盘。

运行环境：WSL（Ubuntu-26.04），datus 仓自带的 .venv/bin/python 执行，纯标准库。
由 Windows 侧经 `wsl.exe -d Ubuntu-26.04 --` 调起；**题目内容经文件交接，不过命令行**
（免 Windows→WSL 的引号转写坑）。stdout 逐行输出 MessagePayload JSON，直接以字节
写入留痕文件——不解码、不改写，超时被杀时已写入部分天然保留。

用法（Windows 侧拼好 /mnt/ 路径后调用）：
  .venv/bin/python wsl_runner.py \
      --question-file /mnt/d/.../qNN.question.txt \
      --out-payload  /mnt/d/.../qNN.payload.jsonl \
      --out-stderr   /mnt/d/.../qNN.stderr.txt \
      --out-meta     /mnt/d/.../qNN.meta.json \
      [--datus-root /mnt/d/develop/datus/Datus-agent] [--timeout 900]
"""

import argparse
import json
import subprocess
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question-file", required=True)
    ap.add_argument("--out-payload", required=True)
    ap.add_argument("--out-stderr", required=True)
    ap.add_argument("--out-meta", required=True)
    ap.add_argument("--datus-root", default="/mnt/d/develop/datus/Datus-agent")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    question = Path(args.question_file).read_text(encoding="utf-8").strip()
    datus_bin = str(Path(args.datus_root) / ".venv/bin/datus")

    t0 = time.time()
    timed_out = False
    with open(args.out_payload, "wb") as fo, open(args.out_stderr, "wb") as fe:
        # print 模式每次调用即独立新会话（题间零污染）；conf/agent.yml 与
        # .datus/config.yml 锚定 CWD，必须在 datus 仓根目录运行
        proc = subprocess.Popen(
            [datus_bin, "-p", question],
            cwd=args.datus_root,
            stdout=fo,
            stderr=fe,
        )
        try:
            proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            timed_out = True

    meta = {
        "returncode": proc.returncode,
        "timed_out": timed_out,
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.out_meta).write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print("TIMEOUT" if timed_out else "OK")


if __name__ == "__main__":
    main()
