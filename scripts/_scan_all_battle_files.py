#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描全部解压后的游戏文件，寻找 stride=0x60(96B) 与 stride=0x14(20B) 的数值表。
   目标：(1) 96B 兵种/阵形/计略 记录；(2) 20B/条 兵种类型属性表(stride 0x14)。
   判定：干净周期(自相关峰值) + 数值在合理区间(1..255，且有一定多样性)。"""
import sys, os, struct
sys.path.insert(0, 'scripts')
from real_assets import ls11_decompress

DATA = 'F:/Games/Taikou2'
STRIDES = [0x14, 0x18, 0x20, 0x30, 0x40, 0x48, 0x50, 0x60, 0x64, 0x70, 0x80, 0x90, 0xC0]

def autocorr_period(blob, max_period=0x200):
    """在候选周期内找自相关最强的 stride（跳过 stride 1）。"""
    n = len(blob)
    best = None
    for p in range(2, min(max_period, n // 4 + 1)):
        # 比较 offset 0..n-2p 与 offset p..n-p，统计相等字节数
        same = 0
        total = n - 2 * p
        if total <= 0: continue
        for i in range(0, total, 7):  # 抽样加速
            if blob[i] == blob[i + p]:
                same += 1
        ratio = same / (total / 7)
        if ratio > 0.85:
            return p, ratio
    return None, 0.0

def stat_quality(blob, stride):
    """抽查若干条记录，看数值是否合理（1..255 为主，含多样性）。"""
    n = len(blob)
    nrec = n // stride
    if nrec < 4: return 0.0, 0
    vals = []
    for r in range(0, min(nrec, 40)):
        base = r * stride
        for b in blob[base:base + stride]:
            vals.append(b)
    if not vals: return 0.0, 0
    inrange = sum(1 for v in vals if 1 <= v <= 255)
    diversity = len(set(vals))
    q = inrange / len(vals) * min(1.0, diversity / 30.0)
    return q, diversity

def scan_blob(name, blob):
    results = []
    for stride in STRIDES:
        if len(blob) < stride * 4: continue
        p, ratio = autocorr_period(blob[: min(len(blob), 0x4000)])
        if p == stride:
            q, div = stat_quality(blob, stride)
            if q > 0.3:
                nrec = len(blob) // stride
                results.append((stride, ratio, q, div, nrec))
    return results

def main():
    files = sorted(os.listdir(DATA))
    for fn in files:
        p = os.path.join(DATA, fn)
        if not os.path.isfile(p): continue
        ext = fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''
        if ext == 'lzw':
            raw = open(p, 'rb').read()
            blob = ls11_decompress(raw)
            if not blob:
                # 试非LS11：可能是明文
                blob = raw
        elif ext in ('tr2', 'dat', 'idx', 'grp', 'pk8', 'kos'):
            blob = open(p, 'rb').read()
        else:
            continue
        if len(blob) < 0x40: continue
        res = scan_blob(fn, blob)
        if res:
            print('### %s  (size=%d)' % (fn, len(blob)))
            for stride, ratio, q, div, nrec in sorted(res, key=lambda x: -x[2]):
                print('   stride=0x%x(%d)  autocorr=%.2f  quality=%.2f  diversity=%d  nrec=%d'
                      % (stride, stride, ratio, q, div, nrec))
                # 打印首两条样本
                base = 0
                print('     rec0:', ' '.join('%02x' % b for b in blob[base:base + stride][:24]))
                if nrec > 1:
                    base = stride
                    print('     rec1:', ' '.join('%02x' % b for b in blob[base:base + stride][:24]))

if __name__ == '__main__':
    main()
