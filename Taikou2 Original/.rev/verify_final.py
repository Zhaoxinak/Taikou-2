# -*- coding: utf8 -*-
"""verify_final.py —— 校验「干净重建」的 big.exe 是否把 fix1/fix2/fix3 全部吸收且不再有覆盖冲突。

四条硬检查:
  A) 5 个诊断 trampoline 站点必须回到原生字节(不再 jmp/call 到 MOD 区)
  B) 两处栈局部数组 memset 长度必须是 370 (不是 CAP=1024)
  C) debug_log 桩(ret 4)的 4 个调用点, 之后一个 add esp,4 都不能有
  D) 培养面板 kd_* 五段必须完整(尾部保有 kd_itoa 的 ret), 且 kd_row 区内
     不得出现任何 0x54B6xx 写标记字节(那是被 trampoline 本体踩过的痕迹)
"""
import struct, sys, capstone

EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'
IB = 0x400000
OK, BAD = [], []


def say(ok, msg):
    (OK if ok else BAD).append(msg)
    print(('  [OK]   ' if ok else '  [FAIL] ') + msg)


d = open(EXE, 'rb').read()
e = struct.unpack_from('<I', d, 0x3C)[0]
n = struct.unpack_from('<H', d, e + 6)[0]
opt = e + 24
sz = struct.unpack_from('<H', d, e + 20)[0]
secs = []
for i in range(n):
    o = opt + sz + i * 40
    nm = d[o:o + 8].rstrip(b'\0').decode('latin1')
    vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
    secs.append((nm, va, max(vs, rs), ra))


def r2o(rva):
    for nm, va, vs, ra in secs:
        if va <= rva < va + vs:
            return ra + (rva - va)
    raise KeyError(hex(rva))


def off(va):
    return r2o(va - IB)


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True


def dis(va, ln):
    o = off(va)
    return list(md.disasm(d[o:o + ln], va))


print('目标: %s (%d B)' % (EXE, len(d)))

# ---- A) 5 个诊断 trampoline 站点 ----
print('\n[A] 诊断 trampoline 站点 (必须回到原生):')
A = [
    (0x4A0D50, b'\x83\xEC\x08\x53\x55', 'ENTRY(E) sub esp,8/push ebx/push ebp'),
    (0x4F44B0, b'\x55\x8B\xEC\x6A\xFF', 'BOOT(F) push ebp/mov ebp,esp/push -1'),
]
for va, want, desc in A:
    got = d[off(va):off(va) + 5]
    say(got == want, '0x%06X %s  %s' % (va, desc, got.hex(' ')))
for va, want, desc in [(0x4A0E47, 0x4A0B00, 'DAILY(D) call 0x4A0B00'),
                       (0x4A0E41, 0x49A1A0, 'EARLY(G) call 0x49A1A0'),
                       (0x4A0DED, 0x4A4C60, 'MONTH(H) call 0x4A4C60')]:
    ins = dis(va, 5)[0]
    calc = ins.operands[0].imm if ins.mnemonic == 'call' else -1
    say(ins.mnemonic == 'call' and (calc & 0xFFFFFFFF) == want,
        '0x%06X %s  实得 %s %s' % (va, desc, ins.mnemonic, ins.op_str))

# ---- B) 两处栈 memset 长度 ----
print('\n[B] 栈局部数组 memset 长度 (必须 370):')
for va in (0x49C5E5, 0x49CD3D):
    got = d[off(va):off(va) + 5]
    say(got == b'\x68\x72\x01\x00\x00',
        '0x%06X push 0x%X  (%s)' % (va, struct.unpack_from('<I', got, 1)[0], got.hex(' ')))

# ---- C) debug_log 调用约定 ----
print('\n[C] debug_log(ret 4) 调用点之后的清栈:')
LOGGER = 0x54C988
_nsaw = 0
_bad = 0
for nm, va, vs, ra in secs:
    base = IB + va
    blob = bytes(d[ra:ra + vs])
    for k in range(len(blob) - 5):
        if blob[k] != 0xE8:
            continue
        rel, = struct.unpack_from('<i', blob, k + 1)
        if base + k + 5 + rel != LOGGER:
            continue
        _nsaw += 1
        nxt = blob[k + 5:k + 8]
        if nxt == b'\x83\xC4\x04':
            _bad += 1
            print('       !! %s@0x%08X 后面还有 add esp,4' % (nm, base + k))
        else:
            print('       %s@0x%08X  后接 %s' % (nm, base + k, nxt.hex(' ')))
say(_nsaw >= 4 and _bad == 0,
    'debug_log 调用点 %d 个 (>=4), 多余 add esp,4 %d 处 (期望 0)' % (_nsaw, _bad))

# ---- D) 培养面板完整性 ----
print('\n[D] 培养面板 kd_* + 反馈小框 (0x552100 起):')
KD = 0x552100
KD_SZ = 0xC00   # M5: 七段 (kd_show/frame/bars/row/itoa/msg/msg_frame), 配额 0xC00
o = off(KD)
blob = d[o:o + KD_SZ]
ins = list(md.disasm(blob, KD))
end = ins[-1].address + len(ins[-1].bytes) if ins else KD
print('       线性反汇编 %d 条, 覆盖 0x%06X..0x%06X' % (len(ins), KD, end))
pts = {}
for i in ins:
    if i.mnemonic == 'ret':
        pts.setdefault('ret', []).append(i.address)
say(len(pts.get('ret', [])) == 7, '七段各一个 ret (实得 %d)' % len(pts.get('ret', [])))
# kd_row 区不得被写标记字节污染
MODB = 0x54B600
hits = []
for i in ins:
    if i.mnemonic == 'mov' and i.op_str.startswith('byte ptr [0x54'):
        a = int(i.op_str.split('[')[1].split(']')[0], 16)
        if MODB <= a < MODB + 0x100:
            hits.append(i.address)
say(not hits, 'kd_* 内没有被 trampoline 的 `mov byte ptr [0x54B6xx],0xFF` 混入 (%d 处)' % len(hits))
# kd_row 关键序列: SetTextColor(0x536034) 必须在 TextOut(0x536040) 之前成对出现
tc = [i.address for i in ins if i.mnemonic == 'call' and '0x536034' in i.op_str]
to = [i.address for i in ins if i.mnemonic == 'call' and '0x536040' in i.op_str]
# 源码形态: kd_frame 2 次(标题/提示) + kd_row 2 次(标签/数值) —— 与 kid_panel.selfcheck 的
# "TextOut == 4" 同源; 控件一旦变少就说明 kd_row 尾部又被截了。
say(len(tc) == 7 and len(to) == 7,
    'SetTextColor %d 次 / TextOut %d 次 (期望 7 / 7: 详情 4 + 小框 3)' % (len(tc), len(to)))
# M5: 反馈小框入口 = 第 5 个 pushad; 它必须在面板配额内且后面还有代码
_pa = [i.address for i in ins if i.mnemonic == 'pushal']
say(len(_pa) == 6 and KD < _pa[4] < KD + KD_SZ, '六段 pushad, 反馈小框入口 = 0x%06X' % (_pa[4] if len(_pa) > 4 else 0))

print('\n===== 汇总: OK %d / FAIL %d =====' % (len(OK), len(BAD)))
for m in BAD:
    print('  FAIL:', m)
sys.exit(1 if BAD else 0)
