# -*- coding: utf-8 -*-
"""probe_listdlg.py — 原生列表对话框的"一屏 12 项"到底是硬门还是分页 (纯静态读 exe)

三条问题:
  Q1 0x47BED0 / 0x47BE00 的控制流: count>12 时显示什么、返回什么
  Q2 全镜像有没有别的调用者能给出 count>12 (若有, 说明 12 不是硬门或它自己分页)
  Q3 这片区域里是否存在第二个"带滚动/翻页"的名单对话框
"""
import struct, sys, capstone

EXE = sys.argv[1] if len(sys.argv) > 1 else '../TAIK2W95_big.exe'
d = open(EXE, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]      # SizeOfOptionalHeader 在 pe+20
SECS = []
for i in range(nsec):
    o = pe + 24 + opt + i * 40
    nm = d[o:o + 8].rstrip(b'\x00').decode('ascii', 'replace')
    vs = struct.unpack_from('<I', d, o + 8)[0]
    va, rs, ra = struct.unpack_from('<III', d, o + 12)
    SECS.append((nm, 0x400000 + va, vs, rs, ra))


def AT(va, k):
    for nm, sva, vs, rs, ra in SECS:
        if sva <= va < sva + max(vs, rs):
            off = ra + (va - sva)
            return d[off:off + k]
    raise KeyError('%08X' % va)


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def dis(va, n=40):
    out = []
    for x in md.disasm(AT(va, n * 12), va):
        out.append('  %08X  %-20s %s %s' % (x.address, x.bytes.hex(), x.mnemonic, x.op_str))
        if len(out) >= n:
            break
    return out


def callers(target):
    """全镜像扫 E8 rel32 调用点 (代码既在 .text 也在 .data ⇒ 逐节扫, 别假设 offset==RVA)"""
    res = []
    for nm, sva, vs, rs, ra in SECS:
        k = min(vs, rs)
        blob = d[ra:ra + k]
        for off in range(0, len(blob) - 5):
            if blob[off] != 0xE8:
                continue
            rel = struct.unpack_from('<i', blob, off + 1)[0]
            if sva + off + 5 + rel == target:
                res.append(sva + off)
    return res


def align_back(va, back=300, want=12):
    """从 va-back 起逐字节找**能正好落在 call 上**的线性反汇编起点, 返回 call 前 want 条"""
    best = None
    for st in range(back):
        a = va - back + st
        try:
            seq = list(md.disasm(AT(a, back * 2), a))
        except Exception:
            continue
        addrs = [x.address for x in seq]
        if va in addrs:
            i = addrs.index(va)
            if best is None or i > best[0]:
                best = (i, seq[:i + 1])
    if best is None:
        return ['      (对不齐, 需人工看)']
    return ['  %08X  %-20s %s %s' % (x.address, x.bytes.hex(), x.mnemonic, x.op_str)
            for x in best[1][-want:]]


if __name__ == '__main__':
    print('== 镜像 %s ==' % EXE)
    print('  ' + '  '.join('%s@%06X(vs=%X)' % (nm, sva, vs) for nm, sva, vs, rs, ra in SECS))

    import collections
    for t in (0x47BED0, 0x47BE00):
        cs = callers(t)
        print('\nQ2  callers(0x%06X) = %d 处' % (t, len(cs)))
        push_imm = collections.Counter()
        for c in cs:
            ls = align_back(c, 300, 14)
            # cdecl 反序入栈 ⇒ **紧挨 call 的那枚 push 才是 arg1 = count**
            ps = [l for l in ls if ' push ' in l]
            cnt = ps[-1].split('push')[1].strip() if ps else '(无)'
            if cnt.startswith('0x'):
                try:
                    push_imm[int(cnt, 16)] += 1
                    continue
                except ValueError:
                    pass
            push_imm[cnt if not cnt.startswith('[') else '内存'] += 1
        print('   紧挨 call 的那枚 push (=arg1 count) 的分布:')
        for k, v in push_imm.most_common(30):
            print('     %s : %d' % (k, v))
        print('   call 前最近一枚 push 立即数的分布 (None=来自寄存器/内存):')
        for k, v in push_imm.most_common(30):
            print('     %s : %d' % (k, v))
        print('   抽样 6 处调用现场:')
        for c in cs[:6]:
            print('  --- call @ %08X' % c)
            for l in align_back(c, 300, 10):
                print(l)
