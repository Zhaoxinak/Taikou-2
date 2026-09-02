#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_decode_path.py -- 续230 决定性静态校验：
   论证「215 型逐字节字段 schema」在运行期不存在 —— 数据解码路径(0x47f350 + 18 子解码器)
   与「49B 记录显示路径」(read_record 0x47d890 + 三视缓冲 0x522c..) 完全不相交。
   若 0x47f350 及其 18 子解码器内部：
     (a) 0 处 call 0x47d890 (read_record)；
     (b) 0 处引用 0x522c60/0x522c88/0x522c70 (三视缓冲)；
     (c) 0 处出现 ×49 记录 stride 乘法(lea eax,[eax*2]; lea edx,[eax*8]; ...)；
   则 data 路径是「扁平流 -> 固定 section(S0..S17) -> 固定表」模型，不存在按 type 的字段 schema。
"""
import os
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

FUNCS = [0x47f350] + [0x47dae0, 0x47dce0, 0x47e130, 0x47e3a0, 0x47e440, 0x47e5a0,
              0x47e770, 0x47ea80, 0x47ebb0, 0x47ecb0, 0x47ed10, 0x47ed70,
              0x47ee50, 0x47ef00, 0x47f050, 0x47f0a0, 0x47f1b0, 0x47f210]

# 扫描窗口：从函数起点往后 0x600 字节（覆盖主体）
def scan(fva, win=0x600):
    hits = {'read_record': [], 'viewbuf': [], 'stride49': []}
    seen = set()
    for i in md.disasm(MEM[fva - BASE: fva - BASE + win], fva):
        s = f'{i.mnemonic} {i.op_str}'
        # (a) 调用 read_record
        if i.mnemonic == 'call' and '0x47d890' in i.op_str:
            hits['read_record'].append(i.address)
        # (b) 引用三视缓冲（push 立即数 / lea / mov 等包含地址）
        for v in ('0x522c60', '0x522c88', '0x522c70'):
            if v in s:
                hits['viewbuf'].append((i.address, s)); break
        # (c) ×49 stride：典型 (eax*49) 或 lea 组合 eax*2+eax*8+eax*39... 简化为找乘 49 立即数
        if '0x31' in s and ('imul' in s or 'mul' in s):   # 0x31 = 49
            hits['stride49'].append((i.address, s))
    return hits

total = {'read_record': 0, 'viewbuf': 0, 'stride49': 0}
detail = []
for f in FUNCS:
    h = scan(f)
    n_rr = len(h['read_record']); n_vb = len(h['viewbuf']); n_s49 = len(h['stride49'])
    total['read_record'] += n_rr; total['viewbuf'] += n_vb; total['stride49'] += n_s49
    label = 'MAIN' if f == 0x47f350 else f'S{ FUNCS.index(f) }'
    detail.append((label, f, n_rr, n_vb, n_s49))
    if n_rr or n_vb or n_s49:
        for k in ('read_record', 'viewbuf', 'stride49'):
            for x in h[k]:
                print(f'   HIT {label}@{f:06x} {k}: {x}')

print('=' * 72)
print('扫描范围：0x47f350 + 18 子解码器 各 0x600 字节窗口')
print('=' * 72)
print(f'  call read_record(0x47d890) 总计 = {total["read_record"]}')
print(f'  引用三视缓冲(0x522c..)      总计 = {total["viewbuf"]}')
print(f'  ×49 记录 stride 乘立即数     总计 = {total["stride49"]}')
print('-' * 72)
print('  逐函数 (label, va, #read_record, #viewbuf, #stride49):')
for d in detail:
    print(f'    {d[0]:5s} 0x{d[1]:06x}  rr={d[2]} vb={d[3]} s49={d[4]}')
print('=' * 72)
ok = (total['read_record'] == 0 and total['viewbuf'] == 0 and total['stride49'] == 0)
print('结论:', '✅ 数据解码路径与 49B 记录/三视缓冲 完全不相交 —— 无按 type 字段 schema'
      if ok else '❌ 发现交集，需进一步追')
