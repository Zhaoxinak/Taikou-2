# -*- coding: utf-8 -*-
"""
提取 計略（合戦战术）效果子程引用的静态数据表，填充 §3.10.7/§3.10.8 待破 DATA 缺口。

目标表：
  1. 0x5176a8  伏兵 位置修正表      dword[posMod*4], posMod∈{20,21} (<=0x1e)  -> 32 项 int32
  2. 0x503712  伪兵 造兵类型表      word[esi*4]  esi=parity*6+k(k=0..5) -> 16 项 word
  3. 0x503710  DIR8 八方向偏移表    word[esi*4]  -> 8 项 int16（坐标偏移）
  4. 0x5037b0  谣言 4 修改码表      byte[k]  k=0..3 -> 4 字节
  5. 0x503560  修复 消息索引表      word[ecx*2] -> 16 项 word（ecx=byte[0x511e0d]）
"""
import struct, json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()

def at(va):
    return MEM[va - BASE:]

def i32(va, n):
    return list(struct.unpack_from('<%di' % n, MEM, va - BASE))

def u32(va, n):
    return list(struct.unpack_from('<%dI' % n, MEM, va - BASE))

def i16(va, n):
    return list(struct.unpack_from('<%dh' % n, MEM, va - BASE))

def u16(va, n):
    return list(struct.unpack_from('<%dH' % n, MEM, va - BASE))

def bytes_at(va, n):
    return MEM[va - BASE: va - BASE + n]

out = {}

# 1) 伏兵 位置修正表 0x5176a8 : 32 int32
amb = i32(0x5176a8, 32)
out['ambush_posmod_0x5176a8'] = amb
print('=== 伏兵 位置修正表 0x5176a8 (32 x int32, 索引 20/21 实际命中) ===')
for i, v in enumerate(amb):
    if i >= 18 and i <= 24:
        print(f'  [{i:2d}] = {v} (0x{v & 0xffffffff:08x})')

# 2) 伪兵 造兵类型表 0x503712 : 16 word（esi=parity*6+k, parity∈{0,1}, k=0..5 -> 0..11）
feint = u16(0x503712, 16)
out['feint_spawntype_0x503712'] = feint
print('\n=== 伪兵 造兵类型表 0x503712 (16 x word; 实际索引用 0..11) ===')
for i, v in enumerate(feint):
    print(f'  [{i:2d}] = {v} (0x{v:04x})')

# 3) DIR8 八方向偏移表 0x503710 : 8 int32（子程 0x43a420 以 word 读取低16位）
dir8_w = i16(0x503710, 16)   # 8 项，每项 4 字节，读低 16 位 -> 取 0,2,4..14
dir8 = dir8_w[0::2]
out['dir8_0x503710'] = dir8
print('\n=== DIR8 八方向偏移表 0x503710 (8 x int16 偏移) ===')
names8 = ['E','SE','S','SW','W','NW','N','NE']
for i, v in enumerate(dir8):
    print(f'  dir[{i}] {names8[i]:>3} = {v}')

# 4) 谣言 4 修改码表 0x5037b0 : 4 byte（循环 byte[k], k=0..3, 送 0x4a0c60）
rumor = list(bytes_at(0x5037b0, 4))
out['rumor_mods_0x5037b0'] = rumor
print('\n=== 谣言 4 修改码表 0x5037b0 (4 x byte -> 0x4a0c60) ===')
print('  ', [f'0x{b:02x}' for b in rumor])

# 5) 修复 消息索引表 0x503560 : 16 word（ecx = byte[0x511e0d]）
repair = u16(0x503560, 16)
out['repair_msgidx_0x503560'] = repair
print('\n=== 修复 消息索引表 0x503560 (16 x word; ecx=byte[0x511e0d]) ===')
for i, v in enumerate(repair):
    print(f'  [{i:2d}] = {v} (0x{v:04x})')

# 附带：填埋使用的 sprintf 格式串指针（0x50360c/620/630/634/644/5029b8/5035fc）
print('\n=== 填埋 消息模板指针（0x4ec010/0x4ec870 的 fmt 参数）===')
fmts = {
    '0x50360c': 0x50360c, '0x503620': 0x503620, '0x503630': 0x503630,
    '0x503634': 0x503634, '0x503644': 0x503644, '0x5029b8': 0x5029b8,
    '0x5035fc': 0x5035fc,
}
fmt_ptrs = {}
for nm, va in fmts.items():
    p = struct.unpack_from('<I', MEM, va - BASE)[0]
    fmt_ptrs[nm] = p
    # 尝试把指针当 GBK 串读取（直到 0 或 0x24 '$'）
    s = ''
    if BASE <= p < BASE + len(MEM):
        raw = MEM[p - BASE: p - BASE + 64]
        try:
            s = raw.split(b'\x00')[0].decode('gbk', 'replace')
        except Exception:
            s = repr(raw[:16])
    print(f'  {nm} -> ptr 0x{p:08x}  str="{s}"')

out['block_fmt_ptrs'] = fmt_ptrs

with open('scripts/tactic_tables.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('\n[written] scripts/tactic_tables.json')
