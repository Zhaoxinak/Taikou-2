"""audit_callconv.py — 审计所有 MOD 桩的调用约定一致性（只读，不修改任何文件）

★ 为什么要有这个工具
fix2 抓到的真凶是: 日志桩 0x54C988 以 `ret 4` 结尾(stdcall,自己清参数),
但 child_growth_pass 里 3 个调用点在 call 之后又 `add esp,4` ⇒ 每次多弹 4 字节,
ESP 逐次漂移, 最终 ret 弹到 0 ⇒ EIP=0。

这种 bug 只在我们自己注入的桩里才会出现(原版代码不会有), 而且**很可能不止一处**。
本脚本把整个镜像扫一遍, 找出所有「调用 MOD 区内函数」的站点, 判定是否符合约定:

  被调函数结尾   调用点应做       若调用点做了 add esp,N
  -----------   -------------   ------------------------
  ret   (C3)    调用者清: add esp,4*argc   —— 正常
  ret N (C2)    调用者什么都不做            —— ✗ 双清(多弹 N)

判定方法(保守, 只报高置信度):
  1. 线性反汇编被调函数体, 取第一个 ret / ret imm 作为「结尾」
  2. 若结尾是 `ret N` 且调用点紧随 `add esp,N` ⇒ 必然双清, 报错
  3. 若结尾是 `ret` 且调用点紧随 `add esp,N` ⇒ 正常, 记为调用者清栈

用法: python audit_callconv.py [exe路径]
"""
import struct, sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding='utf-8')

DEFAULT = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big_fix2.exe'
IMAGE_BASE = 0x400000
# 我们注入的桩都放在 .edata 段里的这块区域(见 build_big.py 的 MOD 基址)
MOD_LO, MOD_HI = 0x54B600, 0x54E000

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def sec_map(d):
    e = struct.unpack_from('<I', d, 0x3C)[0]
    opt = e + 24
    n, = struct.unpack_from('<H', d, e + 6)
    osz, = struct.unpack_from('<H', d, e + 20)
    so = opt + osz
    secs = []
    for i in range(n):
        o = so + i * 40
        nm = d[o:o + 8].rstrip(b'\0').decode('latin1')
        vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
        secs.append((nm, va, max(vs, rs), ra))
    return secs


def func_epilogue(d, secs, va, maxlen=0x400):
    """从 va 起线性反汇编, 返回第一个 ret/ret imm 的信息。"""
    # 找到 va 所在段的文件偏移
    off = None
    for nm, sva, vs, ra in secs:
        if sva <= va - IMAGE_BASE < sva + vs:
            off = ra + (va - IMAGE_BASE - sva)
            break
    if off is None:
        return None
    for ins in md.disasm(bytes(d[off:off + maxlen]), va):
        if ins.mnemonic == 'ret':
            imm = None
            try:
                if ins.operands:
                    imm = ins.operands[0].imm
            except Exception:
                imm = None
            if not imm:
                return ('ret', 0, ins.address)
            return ('retn', imm, ins.address)
    return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    d = bytearray(open(path, 'rb').read())
    secs = sec_map(d)
    print('审计目标: %s' % path)
    print('MOD 桩区: 0x%06X .. 0x%06X' % (MOD_LO, MOD_HI))
    print()

    sites = []          # (site_va, target_va, 后3字节)
    for nm, sva, vs, ra in secs:
        if nm not in ('.text', '.data', '.edata', '.fdata', '.rsrc'):
            continue
        base = IMAGE_BASE + sva
        blob = d[ra:ra + vs]
        for k in range(len(blob) - 8):
            if blob[k] != 0xE8:
                continue
            rel, = struct.unpack_from('<i', blob, k + 1)
            site = base + k
            tgt = site + 5 + rel
            if MOD_LO <= tgt < MOD_HI:
                sites.append((site, tgt, bytes(blob[k + 5:k + 8])))

    # 去重
    seen = set()
    uniq = []
    for s in sites:
        if s[0] in seen:
            continue
        seen.add(s[0])
        uniq.append(s)

    print('共 %d 个「调用 MOD 桩」的站点, 逐个判定:' % len(uniq))
    print()
    bad, ok, unknown = [], [], []
    for site, tgt, nxt in sorted(uniq):
        ep = func_epilogue(d, secs, tgt)
        if ep is None:
            unknown.append((site, tgt, nxt))
            continue
        kind, imm, epva = ep
        # add esp, N 的机器码: 83 C4 xx (N<128)
        addn = None
        if nxt[0] == 0x83 and nxt[1] == 0xC4:
            addn = nxt[2]
        if kind == 'retn' and imm and addn == imm:
            bad.append((site, tgt, imm, nxt))
            print('  ✗ 双清  0x%06X -> 0x%06X  桩 ret %d, 调用点又 add esp,%d  [%s]'
                  % (site, tgt, imm, addn, nxt.hex(' ')))
        elif kind == 'retn' and imm:
            ok.append((site, tgt, 'retn', imm))
            print('  ✓       0x%06X -> 0x%06X  桩 ret %d, 调用点未重复清' % (site, tgt, imm))
        else:
            ok.append((site, tgt, 'ret', addn))
            print('  ✓       0x%06X -> 0x%06X  桩 ret(cdecl), 调用点 add esp,%s'
                  % (site, tgt, addn if addn is not None else '-'))

    print()
    print('=' * 70)
    print('结论: 双清(多弹栈) %d 处 / 正常 %d 处 / 无法判定 %d 处'
          % (len(bad), len(ok), len(unknown)))
    if bad:
        print()
        print('!!! 需要修的站点 (把调用点后 3 字节 add esp,N 换成 nop):')
        for site, tgt, imm, nxt in bad:
            print('    0x%06X  %s -> 90 90 90' % (site, nxt.hex(' ')))
    if unknown:
        print()
        print('无法判定结尾的桩(手工确认):')
        for site, tgt, nxt in unknown:
            print('    0x%06X -> 0x%06X' % (site, tgt))
    # 两阶段的结论合并返回: 第一类多清栈 + 第二类漏清栈, 任一有异常都算不过
    return (1 if bad else 0) + phase2(d, secs)


# ============================================================================
# Phase 2 (2026-10-07 加): 我们自己调「原生引擎函数」的调用约定。
#
# ★ 为什么要第二阶段: fix2 那次是在.桩内多清栈, 今天是**少清栈** ——
#   0x4A0D50(推天数)是 cdecl, 调用方必须 add esp,8;  cm_foster 里漏了这条,
#   于是 `pop ecx` 每轮都捡回残留实参 0x18, 循环永不结束 => 游戏里日期一路狂奔停不下来。
#   第一阶段只查"调进 MOD 桩"的站点, 查不到这一类 (这是我们调别人, 不是别人调我们)。
#
# 做法: 手工表(见 docs/PLAN_CHILD_RAISING.md §6.15 与 child_growth.py 顶部注释)
# 扫 MOD 区内所有 call,<原语>, 逐个核"调用点有没有按约定清"。
# ============================================================================
# (va, argc, 是否调用者清栈, 说明)
ENGINE_PRIMS = [
    (0x47BED0, 5, True,  '选项对话框 (count, 串指针数组, flag, 0, 0)'),
    (0x44E350, 1, True,  '支付amt -> sat_sub(word[0x51662E], amt), 不查余额'),
    (0x4B5620, 2, True,  '资格判定 qualify(learner, teacher)'),
    (0x4A5100, 2, True,  '挂载到家臣链表 (本人, 主人)'),
    (0x4A5290, 1, True,  '挂本国国主 (本人) / 查不到则浪人化'),
    (0x4EBD60, 1, True,  'rand(n)'),
    (0x4A0D50, 2, True,  '★推天数 (hours, 1) —— 漏 clean 的那次的当事人'),
    (0x49A6B0, 1, False, 'stdcall ret 4: nibble 写手 word[+0x2c] 低 4 位'),
    (0x49A6D0, 1, False, 'stdcall ret 4: 排除位 bit4'),
    (0x49A800, 1, False, 'stdcall ret 4: 大名一族 bit11'),
]
# 纯 ecx 传参 (无栈实参) 的访问器: 不该看见任何 add esp 紧随其后
ECX_ONLY = {0x49A5C0: '年龄 getter', 0x49F5E0: '取实体'}


def mod_range():
    """MOD 区起止: 以 _big_layout.json 为准, 没有退回写死的常量"""
    try:
        import json, os
        LY = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         '_big_layout.json'), encoding='utf-8'))
        return LY['mod_base'], LY['mod_base'] + LY['mod_sz']
    except Exception:
        return MOD_LO, MOD_HI


def phase2(d, secs):
    lo, hi = mod_range()
    print()
    print('=' * 70)
    print('第二阶段: MOD 代码调用原生引擎函数的清栈核对 (区间 0x%06X..0x%06X)' % (lo, hi))
    print('  phase1 查"别人调我们", 这一阶段查"我们调别人" -- 漏清栈的症状通常是')
    print('  栈漂移/循环变量被吞/日期狂奔, 不会立刻崩, 所以必须静态钉死。')
    print()
    want = {va: (argc, clean) for va, argc, clean, _doc in ENGINE_PRIMS}
    hits = []
    # MOD 区在哪一段
    for nm, sva, vs, ra in secs:
        if nm != '.edata':
            continue
        base = IMAGE_BASE + sva
        blob = d[ra:ra + vs]
        off = None
        for k in range(len(blob) - 8):
            site = base + k
            if not (lo <= site < hi):
                continue
            if blob[k] != 0xE8:
                continue
            rel, = struct.unpack_from('<i', blob, k + 1)
            tgt = site + 5 + rel
            if tgt in want or tgt in ECX_ONLY:
                off = ra + k
                hits.append((site, tgt, off))
    bad2, ok2 = [], []
    for site, tgt, off in sorted(hits):
        # 取调用点后两条指令
        nxt = []
        for ins in md.disasm(bytes(d[off + 5:off + 5 + 12]), site + 5):
            nxt.append((ins.mnemonic, ins.op_str))
            if len(nxt) >= 2:
                break
        addn = None
        for mn, op in nxt[:2]:
            if mn == 'add' and op.startswith('esp, '):
                addn = int(op.split(', ')[1], 16) if op.split(', ')[1].startswith('0x') \
                    else int(op.split(', ')[1])
                break
        if tgt in ECX_ONLY:
            if addn is None:
                ok2.append(site)
                print('  ✓       0x%06X -> 0x%06X  %s (纯 ecx, 无栈实参)' % (site, tgt, ECX_ONLY[tgt]))
            else:
                bad2.append(site)
                print('  ✗       0x%06X -> 0x%06X  %s 不该清栈, 却 add esp,%d'
                      % (site, tgt, ECX_ONLY[tgt], addn))
            continue
        argc, clean = want[tgt]
        doc = [x[3] for x in ENGINE_PRIMS if x[0] == tgt][0]
        need = argc * 4 if clean else None
        if clean:
            if addn == need:
                ok2.append(site)
                print('  ✓       0x%06X -> 0x%06X  cdecl %d 实参, add esp,%d  (%s)'
                      % (site, tgt, argc, need, doc))
            else:
                bad2.append(site)
                print('  ✗ 漏/错清 0x%06X -> 0x%06X  cdecl %d 实参需 add esp,%d, 实得 %s  (%s)'
                      % (site, tgt, argc, need, addn if addn is not None else '无', doc))
        else:
            if addn is None:
                ok2.append(site)
                print('  ✓       0x%06X -> 0x%06X  stdcall %d 实参自清, 调用点未重复清  (%s)'
                      % (site, tgt, argc, doc))
            else:
                bad2.append(site)
                print('  ✗ 双清   0x%06X -> 0x%06X  桩自己 ret 4 却调用点又 add esp,%d  (%s)'
                      % (site, tgt, addn, doc))
    print()
    print('第二阶段结论: 符合 %d 处 / 异常 %d 处' % (len(ok2), len(bad2)))
    return 1 if bad2 else 0


if __name__ == '__main__':
    sys.exit(main())
