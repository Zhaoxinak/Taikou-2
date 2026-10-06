# -*- coding: utf-8 -*-
"""
probe_child.py —— M1「儿童态配方」静态探针 (只读, 不开游戏)

要钉死的五件事 (PLAN_CHILD_PRELOAD.md §4 的 K1..K5):
  K1 引擎有没有原生「年龄」消费点: 实体+0x1b(生年偏移) 的读点 / 常数 1490 / 年字 [0x5205f0]
  K2 排除位全量读写点: +0x2c bit4(0x10)/bit7(0x80)、+0x2d bit7、+0x2e bit0..3
       -> 谁置位、谁清位、谁读它做判定 (决定儿童用哪一位"在场但不参与")
  K3 名单/调查卡依赖: 关键例程(访问器/实例化/元服/谓词/名单构造)的调用者清单
  K4 有没有代码往池区/表区写绝对地址 (扩展槽 370+ 会不会被 native 代码踩掉)
  K5 登场标志表 [0x519288+oid] 的读写点 —— 预载器置 1 后谁可能清回 0

两种独立方法互证, 且**必须报覆盖率**:
  A) 失步重同步线性反汇编扫代码段 0x401000..0x4C4000
  B) ModRM 字节型扫描扫整镜像 0x401000..0x533000
     —— 保护壳自驱代码(0x52D100 段)在代码段之外, 只用 A 会漏。
产物: .rev/_child_probe.json + 终端摘要
"""
import struct, json, sys, os, re
import capstone
from capstone.x86 import X86_OP_REG, X86_OP_IMM, X86_OP_MEM

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = r'F:\Games\Taikou 2\Taikou2 Original'
REV = os.path.join(ROOT, '.rev')
D = open(os.path.join(REV, 'clean_dump.bin'), 'rb').read()
BASE = 0x400000
CODE = (0x401000, 0x4FA000)          # 编译代码段 (0x4FA000 后是 IAT/静态数据; 熵实测)
IMG = (0x401000, 0x533000)           # 整个映射镜像(含静态表 + 保护壳自驱代码)

POOL, STRIDE, N0 = 0x519868, 47, 370
POOL_HI = POOL + STRIDE * N0
KEYABS = {POOL: '实体池基', 0x521AA8: '姓表', 0x520660: '名表', 0x524A20: 'BSDATA镜像',
          0x519288: '登场标志表', 0x5205F0: '当前年', 0x5205F1: '当前月',
          0x508D98: '城属性表', 0x5179BC: '49国表', 0x51E9C0: '候选数组',
          0x522C98: 'BSDATA读游标', 0x51EB88: '城/势力记录表', 0x519868: '实体池基'}
for k in range(0, STRIDE * N0, 4):    # 池内任意 4 字节对齐落点
    KEYABS.setdefault(POOL + k, None)

FIELDS = {0x02: 'bushou_id', 0x12: '城属性0', 0x13: '城副本', 0x14: '城属性1', 0x15: '城属性2',
          0x16: '存活标记', 0x18: '城word', 0x1b: '生年偏移', 0x1d: '父id',
          0x20: '体力上限', 0x21: '体力现役', 0x22: '体力消耗', 0x24: '国',
          0x25: '城/基础值', 0x28: '俸禄', 0x29: '忠诚', 0x2a: '主君',
          0x2c: '状态字A', 0x2d: '状态字B', 0x2e: '位标志组'}
WREGS = {'eax', 'ecx', 'edx', 'ebx', 'esi', 'edi'}
WRITEMN = {'mov', 'or', 'and', 'xor', 'add', 'sub', 'inc', 'dec', 'movzx', 'movbe', 'xchg', 'shl', 'shr', 'set'}
OPC1 = {0x80, 0x81, 0x82, 0x83, 0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x8D, 0x8F,
        0xF6, 0xF7, 0xFE, 0xFF, 0xC6, 0xC7, 0x38, 0x39, 0x3A, 0x3B,
        0x00, 0x01, 0x08, 0x09, 0x10, 0x11, 0x18, 0x19, 0x20, 0x21,
        0x28, 0x29, 0x30, 0x31, 0x84, 0x85, 0xD0, 0xD1, 0xD2, 0xD3, 0x8F}

md = capstone.Cs(CS_ARCH := capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True


def sweep(buf, va):
    """失步重同步: 一条线性流断在某字节上就 +1 重来, 保证全窗口都被解码过"""
    pos, n, stalls = 0, len(buf), 0
    while pos < n:
        prog = False
        for ins in md.disasm(buf[pos:min(n, pos + 0x10000)], va + pos):
            prog = True
            pos = ins.address - va + len(ins.bytes)
            yield ins
        if not prog:
            stalls += 1
            pos += 1
    sweep.stalls = stalls


def decode_at(va, span=14):
    for ins in md.disasm(D[va - BASE: va - BASE + span], va):
        return ins
    return None


def main():
    cbuf = D[CODE[0] - BASE: CODE[1] - BASE]
    ibuf = D[IMG[0] - BASE: IMG[1] - BASE]
    out = {}

    ins_list = list(sweep(cbuf, CODE[0]))
    dec = sum(len(i.bytes) for i in ins_list)
    print('== A) 代码段 %08X..%08X  反汇编 %d 条 / %d B (窗口 %d B, %.2f%%), 失步重同步 %d 次'
          % (CODE[0], CODE[1], len(ins_list), dec, len(cbuf), 100.0 * dec / len(cbuf), sweep.stalls))

    calls = [struct.unpack_from('<i', i.bytes, 1)[0] + i.address + 5
             for i in ins_list if i.mnemonic in ('call', 'jmp') and len(i.bytes) == 5 and i.bytes[0] in (0xE8, 0xE9)]
    fs = set(calls) | {CODE[0]}
    pos = 0
    while True:
        p = cbuf.find(b'\xC3', pos)
        if p < 0:
            break
        fs.add(CODE[0] + p + 1)
        pos = p + 1
    fn_starts = sorted(fs)

    def fn_of(va):
        lo, hi = 0, len(fn_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if fn_starts[mid] <= va:
                lo = mid
            else:
                hi = mid - 1
        return fn_starts[lo]

    fld = {k: [] for k in FIELDS}
    absrefs = []
    for ins in ins_list:
        for o in ins.operands:
            if o.type == X86_OP_MEM:
                m = o.mem
                if m.disp in FIELDS and m.index == 0 and m.scale in (0, 1) \
                        and ins.reg_name(m.base) in WREGS:
                    fld[m.disp].append((ins.address, ins.mnemonic, ins.op_str,
                                        ins.reg_name(m.base), o.size, fn_of(ins.address)))
                if m.disp in KEYABS or POOL <= m.disp < POOL_HI:
                    absrefs.append((ins.address, ins.mnemonic, ins.op_str, m.disp, o.size))
            elif o.type == X86_OP_IMM:
                v = o.imm & 0xFFFFFFFF
                if v in KEYABS or POOL <= v < POOL_HI:
                    absrefs.append((ins.address, ins.mnemonic, ins.op_str, v, 4))

    print('== 实体字段访问点 (基址寄存器∈{eax..edi}, A 法)')
    for k in sorted(FIELDS):
        hits = sorted(fld[k])
        print('   +%02X %-12s %3d  读%3d 写%3d' % (k, FIELDS[k], len(hits),
                                                  sum(1 for h in hits if h[1] not in WRITEMN),
                                                  sum(1 for h in hits if h[1] in WRITEMN)))
        out['fldA_%02x' % k] = [{'va': '%X' % a, 'fn': '%X' % f, 'txt': '%s %s' % (mn, op), 'reg': rg, 'sz': sz}
                                for a, mn, op, rg, sz, f in hits]

    print('\n== K2) 状态字节: 方向修正后的读写分类 (mem 是首操作数=写)')
    # 实体感知函数集: 函数内出现 池绝对引用 / 步长47 运算 / 调用实体访问器
    ENT_CALLERS = {0x408DC0, 0x470690, 0x47F7B0, 0x4A4FC0, 0x49A610, 0x49A6B0, 0x49A860, 0x4A4D10}
    stride_fns, pool_fns = set(), set()
    for ins in ins_list:
        f = fn_of(ins.address)
        for o in ins.operands:
            if o.type == X86_OP_MEM and (POOL <= o.mem.disp < POOL_HI or o.mem.disp in KEYABS):
                pool_fns.add(f)
            if o.type == X86_OP_IMM and (POOL <= (o.imm & 0xFFFFFFFF) < POOL_HI):
                pool_fns.add(f)
        if ins.mnemonic == 'add' and any(o.type == X86_OP_IMM and o.imm in (STRIDE, STRIDE * 2, 0x2f) for o in ins.operands):
            stride_fns.add(f)
        if ins.mnemonic in ('imul', 'lea') and any(o.type == X86_OP_IMM and o.imm == STRIDE for o in ins.operands):
            stride_fns.add(f)
        if ins.mnemonic == 'call':
            t = struct.unpack_from('<i', ins.bytes, 1)[0] + ins.address + 5 if len(ins.bytes) == 5 else 0
            if t in ENT_CALLERS:
                stride_fns.add(f)
    ent_fns = pool_fns | stride_fns
    print('   实体感知函数: 池引用 %d + 步长/访问器 %d => 并集 %d' % (len(pool_fns), len(stride_fns), len(ent_fns)))
    out['ent_fns'] = ['%X' % f for f in sorted(ent_fns)]

    def direction(ins):
        return 'W' if ins.operands and ins.operands[0].type == X86_OP_MEM else 'R'

    for k in (0x2c, 0x2d, 0x2e):
        rows = []
        for a, mn, op, rg, sz, f in sorted(fld[k]):
            ins = decode_at(a)
            if ins is None:
                continue
            d = direction(ins)
            if mn in ('lea', 'call', 'jmp'):
                continue
            imm = next((o.imm & 0xFFFF for o in ins.operands if o.type == X86_OP_IMM), None)
            rows.append((d, a, f, mn, op, imm, f in ent_fns))
        ws = [r for r in rows if r[0] == 'W']
        rs = [r for r in rows if r[0] == 'R']
        print('   +%02X 总 %d: 写 %d (实体函数内 %d) / 读判 %d (实体函数内 %d)'
              % (k, len(rows), len(ws), sum(1 for r in ws if r[6]), len(rs), sum(1 for r in rs if r[6])))
        for d, a, f, mn, op, imm, ent in rows:
            if not ent:
                continue
            if d == 'W' or imm is not None:
                bits = '' if imm is None else (' bit' + ','.join(str(b) for b in range(16) if (imm >> b) & 1))
                print('     %s %s%08X fn%08X %-6s %-42s imm=%s%s'
                      % (d, 'E' if ent else '.', a, f, mn, op, ('%X' % imm) if imm is not None else '-', bits))
        out['k2_%02x' % k] = [{'d': d, 'va': '%X' % a, 'fn': '%X' % f, 'txt': '%s %s' % (mn, op),
                               'imm': imm, 'ent': ent} for d, a, f, mn, op, imm, ent in rows]

    # ---- B) ModRM 字节型扫描 (全镜像, 与 A 互证) ----
    _cache = {}

    def byte_scan(disp):
        if disp in _cache:
            return _cache[disp]
        res = {}
        for m in re.finditer(re.escape(bytes([disp])), ibuf):
            p = m.start()
            for want in (1, 2):                    # mod=01 disp8 / mod=10 disp32
                start = p - 2
                if start < 1:
                    continue
                b1 = ibuf[start + 1]
                mod, rm = b1 >> 6, b1 & 7
                if rm in (4, 5):
                    continue                       # SIB / [ebp+disp]: 形态另计
                if mod != want:
                    continue
                if want == 2 and ibuf[p:p + 4] != bytes([disp, 0, 0, 0]):
                    continue
                if ibuf[start] not in OPC1:
                    continue
                st = start - 1 if ibuf[start - 1] == 0x66 else start
                ins = decode_at(IMG[0] + st)
                if ins is None:
                    continue
                if any(o.type == X86_OP_MEM and o.mem.disp == disp and o.mem.index == 0
                       for o in ins.operands):
                    res.setdefault(IMG[0] + st, []).append(ins)
        _cache[disp] = res
        return res

    print('\n== B) ModRM 字节型扫描 (全镜像 0x%08X..0x%08X)' % (IMG[0], IMG[1]))
    for k in (0x1b, 0x2c, 0x2d, 0x2e, 0x12, 0x13, 0x25, 0x2a, 0x16):
        res = byte_scan(k)
        a_only = {h[0] for h in fld.get(k, [])}
        b_all = set(res)
        outside = sorted(v for v in b_all if not (CODE[0] <= v < CODE[1]))
        print('   +%02X %-12s B法 %3d 点 | A法 %3d | B-A 独有 %d %s | 代码段外 %d %s'
              % (k, FIELDS[k], len(b_all), len(a_only), len(b_all - a_only),
                 ['%X' % x for x in sorted(b_all - a_only)[:6]], len(outside), ['%X' % x for x in outside[:8]]))
        out['fldB_%02x' % k] = [{'va': '%X' % v, 'txt': '%s %s' % (i.mnemonic, i.op_str),
                                 'imm': [o.imm for o in i.operands if o.type == X86_OP_IMM]}
                                for v, ii in sorted(res.items()) for i in ii]

    # ---- 状态字节 写入点的立即数直方图 (谁置哪几位) ----
    print('\n== K2b) 状态字节 写入点 + 立即数')
    for k in (0x2c, 0x2d, 0x2e):
        hist = {}
        for v, ii in sorted(byte_scan(k).items()):
            for i in ii:
                if i.mnemonic in WRITEMN or i.mnemonic in ('mov', 'or', 'and', 'xor', 'inc', 'dec'):
                    imms = [o.imm & 0xFFFF for o in i.operands if o.type == X86_OP_IMM]
                    if any(o.type == X86_OP_MEM and o.mem.disp == k for o in i.operands):
                        # 目标必须是内存侧(写), 即 mem 是第一个操作数
                        if i.operands and i.operands[0].type == X86_OP_MEM:
                            hist.setdefault((i.mnemonic, tuple(imms)), []).append(v)
        for (mn, imms), vs in sorted(hist.items()):
            print('   +%02X  %-5s %-12s %d 处: %s' % (k, mn, ','.join(hex(x) for x in imms) or '-',
                                                      len(vs), ['%08X' % x for x in vs[:24]]))
        out['wr_%02x' % k] = {('%s/%s' % (mn, ','.join('%x' % x for x in imms))): ['%X' % v for v in vs]
                              for (mn, imms), vs in hist.items()}

    # ---- K1 ----
    print('\n== K1) 年龄来源')
    y = [(i.address, i.mnemonic, i.op_str) for i in ins_list
         for o in i.operands if o.type == X86_OP_IMM and 1480 <= o.imm <= 1600]
    y1490 = [x for x in y if x[2].split()[-1] in ('0x5d2', '1490')]
    print('   imm 恰为 1490 : %d 处 %s' % (len(y1490), ['%08X %s %s' % x for x in y1490[:14]]))
    print('   imm∈[1480,1600] 共 %d 处; 其中 add/cmp 到 1560(0x618) 的: %d'
          % (len(y), sum(1 for x in y if '0x618' in x[2])))
    ent1b = [(a, mn, op, f) for a, mn, op, rg, sz, f in sorted(fld[0x1b]) if f in ent_fns]
    print('   +0x1b 全 %d 处, 其中"实体感知函数"内 %d 处:' % (len(fld[0x1b]), len(ent1b)))
    for a, mn, op, f in ent1b:
        print('     %08X fn%08X %-6s %s' % (a, f, mn, op))

    dy = sorted(set(absrefs and [x for x in absrefs if x[3] in (0x5205F0, 0x5205F1)]))
    print('   年/月字引用 %d 处:' % len(dy))
    for a, mn, op, d, sz in dy:
        print('     %08X (fn %08X) %-6s %-40s ; %s' % (a, fn_of(a), mn, op, KEYABS.get(d, hex(d))))
    out['k1'] = {'imm_year': ['%08X %s %s' % t for t in y], 'f1b': out['fldA_1b'],
                 'date': ['%08X %s %s' % (a, mn, op) for a, mn, op, d, sz in dy]}

    # ---- K3 ----
    TGT = {0x408DC0: '访问器(bit4->NULL)', 0x47F7B0: '实例化(oid,slot)', 0x4A4FC0: '元服初始化',
           0x4A4D10: '登场例程(月)', 0x49A900: '谓词A(大名)', 0x4BB4E0: '谓词B(城归属)',
           0x47DF00: '存档读入器', 0x47DCE0: '存档写出器', 0x49A610: 'nib_get', 0x49A6B0: 'nib_set',
           0x4193B0: '名单构造器', 0x413720: '按国检索', 0x470690: 'is_alive',
           0x49AF00: '城属性0', 0x49AF50: '城属性1', 0x49AFA0: '城属性2',
           0x4A4872: '死亡腾槽0x800B', 0x46A4A0: '49国代表', 0x409340: '实体init', 0x4A3DF3: '概率取+0x25',
           0x49A860: '置bit15', 0x4A4C60: '登场内层', 0x4A0DED: '日期推进内层', 0x4A0D50: '日期推进'}
    xrefs = {}
    off = 0
    while off < len(cbuf) - 5:
        b = cbuf[off]
        if b in (0xE8, 0xE9):
            t = (CODE[0] + off + 5 + struct.unpack_from('<i', cbuf, off + 1)[0]) & 0xFFFFFFFF
            if t in TGT:
                xrefs.setdefault(TGT[t], []).append(('call' if b == 0xE8 else 'jmp', CODE[0] + off))
            off += 5
            continue
        if b == 0x68:
            t = struct.unpack_from('<I', cbuf, off + 1)[0]
            if t in TGT:
                xrefs.setdefault(TGT[t], []).append(('push', CODE[0] + off))
        off += 1
    print('\n== K3) 关键例程 xref')
    for name in sorted(TGT.values()):
        xs = xrefs.get(name, [])
        print('   %-22s %2d: %s' % (name, len(xs), ', '.join('%s@%08X' % x for x in xs[:20])))
    out['k3'] = {k: [[t, '%X' % a] for t, a in v] for k, v in xrefs.items()}

    # ---- K4 / K5 ----
    print('\n== K4) 绝对地址引用分桶')
    bytab = {}
    for a, mn, op, d, sz in absrefs:
        key = KEYABS.get(d) or ('池内+%X' % (d - POOL))
        bytab.setdefault(key, []).append((a, mn, op))
    for k in sorted(bytab, key=lambda x: -len(bytab[x])):
        print('   %-16s %3d 处' % (k, len(bytab[k])))
    out['k4'] = {k: [['%08X' % a, '%s %s' % (mn, op)] for a, mn, op in sorted(v)] for k, v in bytab.items()}
    print('\n== K5) 登场标志表 读写点')
    fl = sorted(bytab.get('登场标志表', []))
    for a, mn, op in fl:
        print('   %08X (fn %08X) %-6s %s' % (a, fn_of(a), mn, op))
    out['k5'] = [['%08X' % a, '%s %s' % (mn, op)] for a, mn, op in fl]
    print('\n== K4b) 实体池基/池内 绝对写点')
    for k, v in sorted(bytab.items()):
        if k == '实体池基' or k.startswith('池内+'):
            for a, mn, op in v:
                if mn in WRITEMN:
                    print('   %s %08X %-6s %s' % (k, a, mn, op))

    # ---- K6) 状态位访问器簇 + 少数可疑写点上下文 ----
    print('\n== K6) 状态位访问器簇 (0x49A6C0..0x49A900 / 0x49BD40..0x49BDD0)')
    acc = {}
    for lo, hi in ((0x49A6B0, 0x49A910), (0x49BD40, 0x49BDE0)):
        for ins in md.disasm(D[lo - BASE: hi - BASE], lo):
            mem = next((o.mem for o in ins.operands if o.type == X86_OP_MEM), None)
            if mem is None or mem.disp not in (0x2c, 0x2d, 0x2e):
                continue
            imm = next((o.imm & 0xFFFF for o in ins.operands if o.type == X86_OP_IMM), None)
            kind = {'or': 'SET', 'and': 'CLR', 'mov': 'WR', 'test': 'TST', 'xor': 'XOR', 'add': 'ADD'}.get(ins.mnemonic, ins.mnemonic)
            bits = '' if imm is None else ','.join(str(b) for b in range(16) if (imm >> b) & 1)
            print('   +%02X %-4s imm=%-6s bit%-8s %08X  %s %s' % (mem.disp, kind, ('%X' % imm) if imm is not None else '-',
                                                                  bits or '-', ins.address, ins.mnemonic, ins.op_str))
            acc.setdefault(mem.disp, []).append((ins.address, kind, imm))
    out['k6'] = {('0x%02x' % k): [['%08X' % a, t, ('%X' % i) if i is not None else None] for a, t, i in v]
                 for k, v in acc.items()}

    print('\n== K6b) +0x2e 的"寄存器位"写点与清零点上下文')
    for va in (0x40BF50, 0x40BF5E, 0x40BF6C, 0x433C50, 0x49A88D, 0x4CFB06, 0x4D53DA, 0x4E27D9):
        print('   --- %08X ---' % va)
        for ins in md.disasm(D[va - BASE: va - BASE + 40], va):
            print('     %08X  %-20s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

    json.dump(out, open(os.path.join(REV, '_child_probe.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n-> _child_probe.json  (%d 键)' % len(out))


if __name__ == '__main__':
    main()
