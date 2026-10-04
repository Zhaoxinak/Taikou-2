import struct
d = open('clean_dump.bin','rb').read()
BASE = 0x400000
LO, HI = 0x1000, 0x133000

def all_refs(tgt):
    pat = struct.pack('<I', tgt); out = []; i = d.find(pat)
    while i >= 0:
        out.append(BASE + i); i = d.find(pat, i + 1)
    return out

def back_targets(va):
    """返回所有目标 <= va 的回边目标(由 va 之前的指令发出)"""
    res = set()
    o = va - BASE
    for i in range(0x1000, o):
        b0 = d[i]; tgt = None
        if 0x70 <= b0 <= 0x7F:
            tgt = BASE + i + 2 + struct.unpack('<b', d[i+1:i+2])[0]
        elif b0 == 0xE9:
            tgt = BASE + i + 5 + struct.unpack_from('<i', d, i+1)[0]
        elif b0 == 0xEB:
            tgt = BASE + i + 2 + struct.unpack('<b', d[i+1:i+2])[0]
        elif b0 == 0x0F and 0x80 <= d[i+1] <= 0x8F:
            tgt = BASE + i + 6 + struct.unpack_from('<i', d, i+2)[0]
        if tgt is not None and 0x1000 < tgt <= va:
            res.add(tgt)
    return res

for tgt,name in ((0x514e0c,'卡片标志'),(0x514ee8,'CARD_CUR')):
    print('=== %s 0x%06X 引用点 ===' % (name, tgt))
    for va in all_refs(tgt):
        # 只关心代码段内的引用
        if va >= 0x519000:   # 数据区
            print('  0x%06X (数据区/表)' % va); continue
        back = sorted(back_targets(va))
        # 只保留 window 内(<=0x800 字节)的回边
        near = [b for b in back if va - b <= 0x900]
        print('  0x%06X  起始回边候选: %s' % (va, ' '.join('0x%06X' % b for b in near[-4:]) or '-'))
