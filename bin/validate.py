"""契约校验命令行（M1）：对轮目录全量核查契约。

用法（Windows 侧 uv 环境）：
  uv run python bin/validate.py --round rounds/m0
退出码：0=全部通过；1=有问题（逐条打印文件+字段定位）。
"""

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台缺省 GBK，中文输出转 UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.validator import check_round  # noqa: E402


def main():
    ap = argparse.ArgumentParser(prog="validate", description="契约校验（schemas/*.schema.json）")
    ap.add_argument("--round", required=True, help="轮目录，如 rounds/m0")
    args = ap.parse_args()

    findings = check_round(Path(args.round))
    if not findings:
        print("契约校验通过：题库/作答卡/裁决书（存在者）全部合规")
        return
    total = 0
    for where, probs in findings:
        for p in probs:
            print(f"[不合格] {where} {p}")
        total += len(probs)
    print(f"共 {total} 处不合契约")
    sys.exit(1)


if __name__ == "__main__":
    main()
