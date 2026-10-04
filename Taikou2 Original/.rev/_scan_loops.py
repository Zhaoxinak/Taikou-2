import struct
d = open('clean_dump.bin','rb').read()
BASE = 0x400000

def calls_to(tgt):
    out=[]
    for i in range(0x1000, 0x133000-5):
        if d[i] == 0xE8:
            rel = struct.unpack_from('<i', d, i+1)[0]
            if BASE+i+5+rel == tgt: out.append(BASE+i)
    return out

def func_start(va):
    o = va - BASE
    j = o - 1
    # 跳过尾部填充 0xCC/0x90
    while j > 0x1000 and d[j] in (0xCC, 0x90): j -= 1
    # 现在 d[j] 应是某条指令/函数的最后字节; 再往回找上一个函数末尾标记
    k = j
    while k > 0x1000:
        if d[k] in (0xC3, 0xC2, 0xCC):
            # d[k] 是 ret/填充; 从 k+1 起跳过填充即为新函数起点
            m = k + 1
            while m < o and d[m] in (0xCC, 0x90): m += 1
            if m < o: return BASE + m
        k -= 1
    return None

def loop_head(va, fstart):
    o = va - BASE
    best = None
    for i in range(o-1, fstart-BASE, -1):
        b0 = d[i]
        tgt = None
        if 0x70 <= b0 <= 0x7F:
            tgt = BASE + i + 2 + struct.unpack('<b', d[i+1:i+2])[0]
        elif b0 == 0xE9:
            tgt = BASE + i + 5 + struct.unpack_from('<i', d, i+1)[0]
        elif b0 == 0xEB:
            tgt = BASE + i + 2 + struct.unpack('<b', d[i+1:i+2])[0]
        if tgt is not None and fstart < tgt <= va and (best is None or tgt > best):
            best = tgt
    return best

PUMPS = calls_to(0x4eefa0)
print('泵点 %d 个' % len(PUMPS))
seen = {}
for c in PUMPS:
    fs = func_start(c)
    if fs is None:
        print('  0x%06X 函数起点未识别' % c); continue
    lh = loop_head(c, fs)
    if lh is None:
        print('  0x%06X 无回边  函数起 0x%06X' % (c, fs)); continue
    seen.setdefault((fs, lh), []).append(c)
print()
print('=== 候选模态循环 ===')
for (fs, head), sites in sorted(seen.items(), key=lambda kv: kv[0][1]):
    n = min(0x600, 0x133000 - (head-BASE))
    body = d[head-BASE: head-BASE + n]
    rc = struct.pack('<I', 0x514ee8) in body
    rf = struct.pack('<I', 0x514e0c) in body
    print('循环头 0x%06X  函数 0x%06X  泵点x%-2d  循环内CARD_CUR=%s  卡片标志=%s  %s'
          % (head, fs, len(sites), 'Y' if rc else '.', 'Y' if rf else '.',
             ' '.join('0x%06X' % s for s in sites[:5])))
