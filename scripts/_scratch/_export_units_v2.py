"""修正版导出：section A = 20 属性(行) x 9 类别(列)，访问 buf[attr + class*20] & 0xf。
同时导出 getLo 结果转换 LUT (0x503138 / 0x503140)。"""
import struct, json, os

DATA = 'F:/Games/Taikou2'
EXE  = 'scripts/_unpacked_mem.bin'

hj = open(os.path.join(DATA,'HJMAPDAT.DAT'),'rb').read()
mem = open(EXE,'rb').read()
BASE = 0x400000

# --- 完整 dump 两张 LUT (各 256 字节) ---
def lut_at(addr):
    off = addr - BASE
    return list(mem[off:off+256])

lut_503138 = lut_at(0x503138)   # fn 0x423f90 使用
lut_503140 = lut_at(0x503140)   # fn 0x423fa0 使用

# --- 重导出：每战 9 类别 x 20 属性 ---
rec_size = 1700
n_rec = len(hj)//rec_size
battles = []
for ridx in range(n_rec):
    rec = hj[ridx*rec_size:(ridx+1)*rec_size]
    secA = rec[0:180]   # unit/formation/strategy 参数区
    terrain = rec[180:940]
    deploy  = rec[940:1700]
    # 20 attr (row) x 9 class (col)
    units = []
    for cl in range(9):
        row = []
        for at in range(20):
            idx = at + cl*20
            val = secA[idx] & 0x0f
            row.append(val)
        units.append(row)
    battles.append({
        'id': ridx,
        'units': units,          # units[class][attr] = secA[attr + class*20] & 0xf
    })

out = {
    'source': 'C:HJMAPDAT.DAT  (38 battles x 1700B)',
    'sectionA_layout': '20 attributes (row) x 9 classes (col); access buf[attr + class*20] & 0xf',
    'accessor': 'getLo(0x439050): eax=[esp+8]=class(0..8); ecx=[esp+4]=attr(0..19); return buf[ecx + eax*20] & 0xf',
    'high_nibble': 'always 0 in all 38 battles (getHi 0x4390c0 is dead)',
    'luts': {
        'fn_0x423f90_lut_0x503138': lut_503138,
        'fn_0x423fa0_lut_0x503140': lut_503140,
        'note': 'raw getLo(0..7) -> effective value via al=[eax+0x503138] / [eax+0x503140]'
    },
    'battles': battles,
}
with open('hjmapdat_units.json','w',encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# 打印 LUT 前 20 项（实际使用的索引范围）
print('LUT 0x503138 [0..19]:', lut_503138[:20])
print('LUT 0x503140 [0..19]:', lut_503140[:20])
print('battles:', len(battles), '| battle0 units[class][attr]:')
for cl in range(9):
    print('  class%d:'%cl, battles[0]['units'][cl])
