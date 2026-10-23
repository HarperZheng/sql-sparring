"""ask_datus：逐题驱动 datus（POST :8501 chat API，常驻服务）并提取作答卡。

组件边界（D8）：本包为独立重写实现，不 import datus 仓任何代码；
提取语义以设计文档 §2.2 为规格，字段口径经 M0 活跑实测校准（rounds/m0）。
（v0–v1 走 WSL 桥接调 datus -p，wsl_runner.py 保留作回退参考。）
"""
