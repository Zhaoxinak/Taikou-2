# -*- coding: utf-8 -*-
"""
verify_appear.py —— 「动态元服/登场」静态回读 (只读, 不开游戏)

校验 4 类事实:
  1) TAIK2W95_big.exe 里 4 个补丁站点字节 + 指令边界对齐 (capstone 解码)
  2) 两个 .edata stub (ensure_queue / APPEAR_CNT trampoline) 解码正确
  3) 待登场槽判据: 池内 354..369 静态状态字必须是 0x808F(原生空槽, 由 ensure_queue 每月武装),
     且扩展槽 370..CAP-1 不得残留 0x800B (存档只序列化 0..369, 落进扩展槽的人读档会消失)
  4) BSDATA1/2 登场日程: 每年到期人数、总计与 16 槽队列的关系。
     登场偏移=0 的一批(=引擎读作 1560, 开局即排队)属原剧本数据事实, 只列告示不判红。
还原: BSDATA*.TR2.orig 备份 + 删 build_big.py 的 4i/4c 段重构建。
"""
import struct, sys, os, json
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = r'F:\Games\Taikou 2\Taikou2 Original'
# ★ TKID_EXE 与 build_big/verify_children 同口径: 交付名(m5/试演档)各不同, 不设=发布默认。
EXE = os.path.join(ROOT, os.environ.get('TKID_EXE') or 'TAIK2W95_big.exe')
BASE = 0x400000
# 地址唯一真源 = build_big.py 落的 _big_layout.json (换 CAP 不用改本脚本)
LY = json.load(open(os.path.join(ROOT, '.rev', '_big_layout.json'), encoding='utf-8'))
POOL, STRIDE = LY['pool_va'], LY['stride']
RES_LO, RES_N = LY['reserve_lo'], LY['reserve_n']
N0, NPOOL = LY['n0'], LY['cap']
V = LY['v']
md = Cs(CS_ARCH_X86, CS_MODE_32)
ok = True


def fail(msg):
    global ok
    ok = False
    print('  !! ' + msg)


# 原始数据告示: 与 exe 补丁无关、且按用户口径"原剧本登场相关先别动"的事实, 只列不判红,
# 免得每次都"有异常"把真回归埋掉。
notes = []


def note(msg):
    notes.append(msg)
    print('  ~  ' + msg)


d = open(EXE, 'rb').read()
pe = pefile.PE(data=d)
secs = {s.Name.rstrip(b'\0').decode(): s for s in pe.sections}
t = secs['.text']
tv = BASE + t.VirtualAddress
ed = secs['.edata']


def T(va, n):
    assert va - tv >= 0 and va - tv < t.SizeOfRawData
    return d[t.PointerToRawData + (va - tv): t.PointerToRawData + (va - tv) + n]


def E(va, n):
    return d[ed.PointerToRawData + (va - POOL): ed.PointerToRawData + (va - POOL) + n]


def dis(va, n, where=T):
    return list(md.disasm(where(va, n), va))


print('== 1) 补丁站点 (%s, %d B, CAP=%d)' % (os.path.basename(EXE), len(d), NPOOL))
SITES = [
    ('(a) 冻结倒数位+空槽埋点', 0x4A4D61, 6, 'inc dword ptr [0x%x]' % V['VACANT_CNT'], 6),
    ('(b) 池扫描界 359->%d' % NPOOL, 0x4A4D84, 5, 'cmp di, 0x%x' % NPOOL, 5),
    ('(c) 元服 call 转桩', 0x4A4F40, 5, 'call 0x%x' % V['APPEAR_STUB'], 5),
    ('(d) 月钩 ensure_queue', 0x4A4CC0, 5, 'call 0x%x' % V['EQ_STUB'], 5),
]
for lbl, va, n, want, ilen in SITES:
    ins = dis(va, n)
    got = ' | '.join('%s %s' % (i.mnemonic, i.op_str) for i in ins)
    tag = 'OK ' if len(ins) == 1 and got == want else 'BAD'
    print('  %s %-24s @%06X  %-26s %s' % (tag, lbl, va, got, ins[0].bytes.hex() if ins else '-'))
    if tag == 'BAD':
        fail('%s 站点解码 = %r (期望 %r)' % (lbl, got, want))

# 指令边界: 冻结站点 6B 之后必须正好接回原链 mov ax,[esi+0x2c] -> ... -> cmp di,0x200
seq = dis(0x4A4D61, 0x30)
addrs = [i.address for i in seq]
if not (len(seq) >= 4 and 0x4A4D67 in addrs and 0x4A4D84 in addrs
        and all(seq[i].address + len(seq[i].bytes) == seq[i + 1].address for i in range(len(seq) - 1))):
    fail('0x4A4D61..0x4A4D84 指令链不连续: ' + ' | '.join('%s %s' % (i.mnemonic, i.op_str) for i in seq))
else:
    print('  OK  0x4A4D61..0x4A4D84 指令链连续 (%d 条, 含 0x4A4D67/0x4A4D84 边界)' % len(seq))

print('== 2) .edata stub')
EQ, TR = V['EQ_STUB'], V['APPEAR_STUB']
eq = dis(EQ, 47, E)
print('  ensure_queue (%d B):' % sum(len(i.bytes) for i in eq))
for i in eq:
    print('    +%02d  %-28s %s %s' % (i.address - EQ, i.bytes.hex(), i.mnemonic, i.op_str))
if not (len(eq) == 11 and eq[-1].mnemonic == 'jmp' and eq[-1].op_str == '0x4a4d10'):
    fail('ensure_queue 应为 11 条且尾 jmp 0x4a4d10')
if not (eq[4].op_str == '0x%x' % (EQ + 34) and eq[9].op_str == '0x%x' % (EQ + 16)):
    fail('ensure_queue 分支/回跳目标异常')
tr = dis(TR, 11, E)
print('  APPEAR_CNT trampoline: ' + ' | '.join('%s %s' % (i.mnemonic, i.op_str) for i in tr))
if not (len(tr) == 2 and tr[1].op_str == '0x4a4fc0'):
    fail('trampoline 尾 jmp 应为 0x4a4fc0')

print('== 3) 待登场槽判据')
# 注意: exe 静态图里池 0..369 是 0 (池由剧本/存档载入流程填充), 武装判据必须对着"载入后的真值"核。
# 参照物 = .rev/ents_dump.json (运行期抓取的原生池), 其中 354..369 恰为 0x808F 无名空槽。
live = json.load(open(os.path.join(ROOT, '.rev', 'ents_dump.json'), encoding='utf-8'))
byslot = {e['slot']: e for e in live}
wrong = [k for k in range(RES_LO, RES_LO + RES_N)
         if not (k in byslot and (byslot[k]['status'] if isinstance(byslot[k]['status'], int)
                                 else int(str(byslot[k]['status']), 0)) == 0x808F
                and not (byslot[k].get('surname') or byslot[k].get('given')))]
print('  运行池槽 %d..%d = 0x808F 无名空槽: %s' % (
    RES_LO, RES_LO + RES_N - 1, 'OK (ensure_queue 判据成立)' if not wrong else 'BAD ' + str(wrong)))
if wrong:
    fail('这些槽在运行池里不是 0x808F 空槽, ensure_queue 判据会漏武装: %s' % wrong)
mv = [i for i in eq if i.mnemonic == 'mov' and i.op_str.startswith('eax, 0x')][0]
want_base = POOL + RES_LO * STRIDE + 0x2c
print('  武装基址: stub mov eax, %s (期望 0x%x = 池+354*47+0x2c) %s' % (
    mv.op_str.split(', ')[1], want_base,
    'OK' if int(mv.op_str.split(', ')[1], 16) == want_base else 'BAD'))
if int(mv.op_str.split(', ')[1], 16) != want_base:
    fail('ensure_queue 武装基址算错')
res_ext = [k for k in range(N0, NPOOL)
           if struct.unpack_from('<H', E(POOL + k * STRIDE + 0x2c, 2))[0] == 0x800B]
print('  扩展槽 %d..%d 带 0x800B 者: %d %s' % (N0, NPOOL - 1, len(res_ext),
                                              'OK (存档外槽不参与登场)' if not res_ext else 'BAD'))
if res_ext:
    fail('扩展槽被武装, 读档会丢人: %s' % res_ext[:8])

print('== 4) BSDATA 登场日程')
R = 59


def s7(r, off):
    return r[off:off + 7].split(b'\x00')[0].decode('gbk', 'replace')


# MOD 预载批次已认领的 oid: 这些人我们开局就按儿童态放进池里并置 登场标志=1,
# 原生登场队列会自动跳过(标志!=0), 不会二次实例化。
MINE = {str(e['oid']) for e in json.load(
    open(os.path.join(ROOT, '.rev', '_child_expect.json'), encoding='utf-8')).values()}

for tag in ('BSDATA1', 'BSDATA2'):
    p = os.path.join(ROOT, tag + '.TR2')
    bs = open(p, 'rb').read()
    snd = open(os.path.join(ROOT, tag.replace('BSDATA', 'SNDATA') + '.TR2'), 'rb').read()
    yearly, susp, asap = {}, 0, []
    for oid in range(700):
        rec = bs[oid * R:oid * R + R]
        w = struct.unpack_from('<H', rec, 0x27)[0]
        birth, app = 1490 + (w & 0x7f), 1560 + ((w >> 7) & 0x3f)
        if snd[0x14 + oid]:                      # 已在剧本中 -> 引擎不会重复登场
            continue
        if app >= 1623:
            susp += 1
        else:
            yearly.setdefault(app, []).append((oid, birth, (s7(rec, 0) + s7(rec, 7)).strip()))
            if app <= 1560:
                asap.append((oid, birth, (s7(rec, 0) + s7(rec, 7)).strip()))
    print('  %s: 动态登场 %d 人 / 挂起(1623) %d 人' % (tag, sum(len(v) for v in yearly.values()), susp))
    if asap:
        # 登场年偏移 bits7..12 = 0 的语义(别再读成"未设定"): 引擎例程 0x4A4D10 的比较是
        #   mov dx,(word[rec+0x27]>>7)&0x3f ; cmp dx, word[年-1560] ; ja skip
        # 即「登场偏移 <= 当前年偏移」⇒ 0 就是 1560 = 开局第一个月就有资格登场。
        # 这是原剧本数据事实(且用户口径"原剧本登场相关先别动"), 故只告示不判红。
        note('%s: 登场偏移=0(=按 1560 开局即排队) %d 人 —— 生年<=1560(开局成年) %d 人 / '
             '生年>1560(开局登场尚未出生者, 原始数据瑕疵) %d 人: %s'
             % (tag, len(asap), sum(1 for a in asap if a[1] <= 1560),
                sum(1 for a in asap if a[1] > 1560),
                ' '.join('%s(oid%d,%d生%s)' % (n, o, b, ' MOD已认领' if str(o) in MINE else '')
                         for o, b, n in sorted(asap, key=lambda x: x[1]) if b > 1560)))
    for y in sorted(yearly):
        if y == 1560:
            continue          # 已由上面的告示整批列出, 不再占一行
        print('    %d: %s' % (y, '、'.join('%s(oid%d,%d生)' % (n, o, b)
                                           for o, b, n in sorted(yearly[y], key=lambda x: x[1]))))
    mx = max((len(v) for v in yearly.values()), default=0)
    print('    单年最多 %d 人 (队列 = 池尾 16 空槽 + 游戏内身故腾槽; 超额者自动排队, 有空位即登场)' % mx)

print('\n结果: %s%s' % ('全部通过' if ok else '有异常, 见上',
                       '  (原始数据告示 %d 条, 见 ~ 行)' % len(notes) if ok and notes else ''))

