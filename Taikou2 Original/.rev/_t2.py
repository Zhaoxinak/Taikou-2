# -*- coding: utf-8 -*-
"""临时: 打印 cm_foster 里与「费用行指针数组」相关的几条指令的实际 capstone 写法。

做法: 复用 build_big 已经写好的地址表 (_big_layout.json 是旧窗 Whites), 只把手算出的
新区地址塞进去, 单独装配一次, 不做整包构建。
"""
import json, sys, capstone
sys.path.insert(0, '.')
import child_menu as CM

LY = json.load(open('_big_layout.json', encoding='utf-8'))
V = LY['v']

MS_COST0 = CM.MS_COST0
MSG_STR.endswith
