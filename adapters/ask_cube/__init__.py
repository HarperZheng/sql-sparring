"""ask_cube：逐题驱动 cube 服务（POST :4100/chat）并提取作答卡。

组件边界（D8）：独立重写实现，不 import cube 仓代码；
v0 实测（fixtures/v0/cube/tmp-nlq1021/，30 题三态）为其回归参照（A3）。
三态：answer（有答案）/ ask（反问口径）/ nomatch（能力外）；另有 error（链路失败）。
"""
