#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_record_layout_ref.py -- 续208：SNDATA 49B 记录布局彻底定型（3 word + 3 字符串）
================================================================================
突破来源（纯静态，三处代码互证）：

【证据 1】记录读取器 0x47d890 = read_record(idx, &buf)  [thiscall, ecx=fileobj]
    eax = idx & 0xffff
    ecx = (eax + eax*2) << 4          ; = 48*idx
    edx = ecx + eax + 0x10            ; = 49*idx + 16   ← stride=49, 文件头=16
    lseek([esi], edx, 0)              ; call dword ptr [0x4fb0a8]
    0x4411b0(ecx=fileobj, buf, 0x31)  ; read 0x31 = 49 字节
  ⇒ 记录 stride = 49B，文件头 = 0x10 B。offset(idx) = 49*idx + 16。

【证据 2】扇出 0x47fc60（把记录拆成 3 word + 3 串）
    sub esp,0xd4 ; buf = [esp]
    0x47d720(...)                     ; 开文件
    0x47d890(idx=[esp+0xd8], &buf)    ; 读 49B 到 buf
    *[esp+0xdc] = word[buf+0x00]      ; word A
    *[esp+0xe0] = word[buf+0x02]      ; word B
    *[esp+0xe4] = word[buf+0x04]      ; word C
    strcpy(0x522c88, buf+0x06)        ; 串 1
    strcpy(0x522c60, buf+0x13)        ; 串 2
    strcpy(0x522c70, buf+0x20)        ; 串 3
  ⇒ 6 + 13 + 13 + 17 = 49，完美平铺，无剩余字节。

【证据 3】0x4ebfe0 = strcpy（非 IAT，直接 call）
    mov edx,[esp+4] ; esi=[esp+0xc] ; eax=edx
    while (cl = *esi) { *edx++ = cl; cl = esi[1]; esi++ }
    *edx = 0 ; ret            ← cdecl，调用方 add esp,8

⚠️ 纠正续189：「43B payload = 171 型指纹 / type=0x01 = 43 个独立布尔」是把
   字符串字节当成位域读的产物。真实 payload = 三个 NUL 结尾定长串字段。

本脚本用 SNDATA1.TR2 / SNDATA2.TR2 静态验证该布局并导出全量记录。
"""
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))

import os, struct, json
from collections import Counter

HDR    = 0x10   # 证据 1
STRIDE = 49     # 证据 1
# 证据 2：字段切片
F_WORDS = [(0x00, 'wordA'), (0x02, 'wordB'), (0x04, 'wordC')]
F_STRS  = [(0x06, 0x13, 'str1'), (0x13, 0x20, 'str2'), (0x20, 0x31, 'str3')]


def dec(b):
    """定长串槽 → (可见文本, 是否合法 NUL 结尾串, NUL 后残留字节)"""
    n = b.find(b'\x00')
    if n < 0:
        return bytes(b).decode('latin-1', 'replace'), False, b''
    body, tail = b[:n], b[n + 1:]
    try:
        s = body.decode('gbk')
    except Exception:
        s = body.decode('latin-1', 'replace')
    return s, True, bytes(tail)


def parse(path):
    raw = open(path, 'rb').read()
    body = len(raw) - HDR
    n = body // STRIDE
    recs = []
    for i in range(n):
        o = HDR + i * STRIDE
        r = raw[o:o + STRIDE]
        d = {'idx': i}
        for off, name in F_WORDS:
            d[name] = struct.unpack_from('<H', r, off)[0]
        for a, b_, name in F_STRS:
            s, ok, tail = dec(r[a:b_])
            d[name] = s
            d[name + '_ok'] = ok
            d[name + '_tail'] = tail.hex()
        recs.append(d)
    return raw, n, body % STRIDE, recs


def main():
    orig = os.path.join(_ROOT, 'Taikou2 Original')
    report = {}
    for fn in ('SNDATA1.TR2', 'SNDATA2.TR2'):
        p = os.path.join(orig, fn)
        if not os.path.isfile(p):
            print('MISS', p)
            continue
        raw, n, rem, recs = parse(p)
        print('=' * 78)
        print('%s  size=%d  头=%d  stride=%d  → %d 条 (余 %d B)' % (fn, len(raw), HDR, STRIDE, n, rem))

        # --- 布局自检 1：三串槽是否都以 NUL 收尾 ---
        ok1 = sum(1 for r in recs if r['str1_ok'])
        ok2 = sum(1 for r in recs if r['str2_ok'])
        ok3 = sum(1 for r in recs if r['str3_ok'])
        print('  NUL 结尾合法率: str1 %d/%d  str2 %d/%d  str3 %d/%d' % (ok1, n, ok2, n, ok3, n))

        # --- 布局自检 2：可打印性（非空串里 ASCII/GBK 可打印占比）---
        def printable(s):
            return s != '' and all((32 <= ord(c) < 127) or ord(c) > 0x2000 for c in s)
        for key in ('str1', 'str2', 'str3'):
            vals = [r[key] for r in recs]
            ne = [v for v in vals if v != '']
            pr = [v for v in ne if printable(v)]
            print('  %s: 非空 %d/%d，其中可打印 %d (%.1f%%)' %
                  (key, len(ne), n, len(pr), 100.0 * len(pr) / max(1, len(ne))))
            print('      样例: %s' % (sorted(set(ne))[:6],))

        # --- 布局自检 3：NUL 后残留是否为 0（定长槽应清零）---
        for key in ('str1', 'str2', 'str3'):
            dirty = [r['idx'] for r in recs if r[key + '_tail'].strip('0') != '']
            print('  %s NUL 后有非零残留的记录数: %d %s' % (key, len(dirty), dirty[:8]))

        # --- word 分布 ---
        for name in ('wordA', 'wordB', 'wordC'):
            c = Counter(r[name] for r in recs)
            print('  %s: 唯一值 %d, top5 %s, max=%d' %
                  (name, len(c), c.most_common(5), max(r[name] for r in recs)))

        report[fn] = {
            'size': len(raw), 'header': HDR, 'stride': STRIDE, 'count': n, 'remainder': rem,
            'records': recs,
        }

    out = os.path.join(_ROOT, 'scripts', 'sndata_record_layout.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('\nJSON ->', out)

    # ---- 自测 ----
    assert report, '未读到任何 SNDATA'
    for fn, d in report.items():
        recs = d['records']
        assert d['remainder'] == 0, '%s: 49B stride 未整除，布局假设失败 (余 %d)' % (fn, d['remainder'])
        for key in ('str1', 'str2', 'str3'):
            r = sum(1 for x in recs if x[key + '_ok']) / float(len(recs))
            assert r > 0.98, '%s.%s NUL 合法率仅 %.3f' % (fn, key, r)
    print('RESULT: PASS ✅ 49B = word×3 + 定长串×3(13/13/17)，两文件全量校验通过')


if __name__ == '__main__':
    main()
