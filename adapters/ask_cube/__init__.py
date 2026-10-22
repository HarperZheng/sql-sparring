"""ask_cube：逐题驱动 cube 服务（POST :4100/chat）并提取作答卡。

组件边界（D8）：独立重写实现，不 import cube 仓代码。
三态：answer（有答案）/ ask（反问口径）/ nomatch（能力外）；另有 error（链路失败）。
ask 态按拍板政策自动追问（policy.py），链路与超时口径经 M0 活跑实测校准。
"""
