#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0 收口（续174）：SNDATA 49B 记录「处理架构」最终判定。

承接续159-166 与本次攻坚。把 P0 从「~164 种类型 payload 字段 schema」收敛为
「粗粒度 category→resource-set 系统 + 记录为二进制场景/资产数据（非文本/非逐字段描述符）」。
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def has(va, needle, n=0x400):
    return any(needle in f'{i.mnemonic} {i.op_str}' for i in dis(va, n))

ok = True
def chk(name, cond, extra=''):
    global ok
    print(('  [PASS] ' if cond else '  [FAIL] ') + name + ((' — ' + extra) if extra else ''))
    ok = ok and cond

print('=== A. 主循环 0x4e8604 处理管线（续160 坐实）===')
chk('迭代记录索引 call 0x480240', has(0x4e8604, 'call 0x480240', 0x30))
chk('结束哨兵 cmp si,-1', has(0x4e8604, 'cmp si, -1', 0x30))
chk('扇出 call 0x47fc60', has(0x4e8604, 'call 0x47fc60', 0x30))
chk('匹配器 call 0x47b390 (模板 0x50d834)', has(0x4e8604, 'call 0x47b390', 0x100) and has(0x4e8604, 'push 0x50d834', 0x100))
chk('谓词 call 0x47fb80', has(0x4e8604, 'call 0x47fb80', 0x100))
chk('全局选择器 0x5205fe 三路值开关', has(0x4e8604, 'mov ax, word ptr [0x5205fe]', 0x140))
chk('簇0(==0): 0x492e20/0x493140/0x48cc20', has(0x4e8604, 'call 0x492e20', 0x140))
chk('簇1(==1): 0x492ed0/0x4931f0', has(0x4e8604, 'call 0x492ed0', 0x140))

print('=== B. 主循环 = 单管线 + 全局模式，非 per-type 分派 ===')
# 三路开关后簇0/簇1/else 是顺序调用（无 cmp <type>; je 各自分支）
code = dis(0x4e8604, 0x300)
has_typecmp = any(i.mnemonic=='cmp' and 'word ptr [esp + 0xc]' in i.op_str and '0x' in i.op_str
                  and i.address > 0x4e86a9 and i.address < 0x4e86c5 for i in code)
chk('簇0/簇1 由 0x5205fe 全局值开关选择（非 per-record type 比较）', not has_typecmp,
    '0x5205fe 是全局模式选择器')
# else 簇始终执行（簇0/簇1 后 fall-through 到 0x4e870f）
chk('else 簇(0x491e70/0x4873b0) 两模式均执行', has(0x4e8604, 'call 0x491e70', 0x300))

print('=== C. payload 非文本（本次实证）===')
recs1 = []
d = open(os.path.join(ROOT, _ROOT + '/Taikou2 Original/SNDATA1.TR2'), 'rb').read()
body = d[16:]
recs1 = [body[i*49:(i+1)*49] for i in range(len(body)//49)]
chk('记录数 == 833', len(recs1) == 833, f'{len(recs1)}')
# 0x0c/0xf3 填充类型占比
filler = sum(1 for r in recs1 if (r[0]&0xff) in (0x0c, 0xf3))
chk('0x0c/0xf3 填充类型占比 < 60%', filler/len(recs1) < 0.60, f'{filler}/{len(recs1)}={filler/len(recs1):.0%}')
# payload 无真实文本：干净日文文本视图数 == 0（2499 视图全为二进制）
def is_clean_cjk(seg):
    if b'\x0c' in seg or b'\xf3' in seg: return False
    z = seg.find(b'\x00'); s = seg if z < 0 else seg[:z]
    if len(s) < 3: return False
    try: t = s.decode('gbk')
    except: return False
    cjk = sum(1 for c in t if 0x4e00 <= ord(c) <= 0x9fff or 0x3040 <= ord(c) <= 0x30ff)
    return cjk/len(t) > 0.6
clean_cnt = sum(1 for r in recs1 for o in (6,19,32) if is_clean_cjk(r[o:49]))
chk('干净日文文本视图数 == 0（payload 全为二进制，非文本）', clean_cnt == 0,
    f'{clean_cnt}/{len(recs1)*3} 视图')

print('=== D. 3 视图消费者 = 0x480000 显示格式化器（续165）===')
chk('0x480000 读 0x522c88/0x522c60/0x522c70', has(0x480000,'0x522c88') and has(0x480000,'0x522c70'))
chk('0x480000 空格对齐补 14/18/18', has(0x480000,'0xe') and has(0x480000,'0x12'))
# 0x47d860 是文件 seek（idx*40960），非 payload 字段解析
code2 = dis(0x47d860, 0x40)
chk('0x47d860 是文件 seek(idx*5<<13=idx*40960)', any('shl eax, 0xd' in f'{i.mnemonic} {i.op_str}' for i in code2),
    '记录索引用于 seek，非 payload 字段解析')

print('\nRESULT:', 'ALL PASS' if ok else 'FAIL')
import sys; sys.exit(0 if ok else 1)
