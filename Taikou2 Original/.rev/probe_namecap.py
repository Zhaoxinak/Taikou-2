# P3 前置静态探测: 姓表 0x520660 / 名表 0x521AA8 (stride 7)
# 目的:
#  1) 判定索引空间 (oid 0..699 还是 slot)
#  2) 找表容量常数 (imul 7 / cmp 0x2BC 等)
#  3) 摸清名表之后到 0x522C88+ 的对象, 写满是否踩界
import pefile, struct, json
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM

EXE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.__data__
secs = []
for s in pe.sections:
    name = s.Name.rstrip(b'\x00').decode()
    secs.append((name, base + s.VirtualAddress, s.Misc_VirtualSize,
                 s.PointerToRawData, s.SizeOfRawData))

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

MEM_MNEMS = {'mov','lea','cmp','push','add','sub','and','or','xor','test','xchg',
             'adc','sbb','movzx','movsx','inc','dec','neg','not','cmpxchg','movbe','xadd','bt'}

def sweep(buf, va):
    """线性反汇编, 停滞则前进 1 字节重同步."""
    i = 0
    n = len(buf)
    while i < n:
        advanced = False
        for size in range(1, 16):
            if i + size > n:
                break
            for ins in md.disasm(buf[i:i+size], va + i):
                if len(ins.bytes) == size:
                    yield ins
                    i += size
                    advanced = True
                    break
            if advanced:
                break
        if not advanced:
            i += 1

LO, HI = base + 0x4000, base + 0x6000  # 覆盖整个 .data 视图: 收集表基址引用
WIN_LO, WIN_HI = 0x520000, 0x524000

sites = []
for name, sv, ss, pr, sr in secs:
    if name not in ('.text', '.data'):
        continue
    buf = data[pr:pr+sr]
    for ins in sweep(buf, sv):
        if ins.mnemonic not in MEM_MNEMS:
            continue
        for o in ins.operands:
            if o.type != X86_OP_MEM:
                continue
            a = o.mem.disp
            if a is None:
                continue
            if WIN_LO <= a < WIN_HI:
                sites.append({
                    'sec': name,
                    'va': '0x%X' % ins.address,
                    'm': ins.mnemonic,
                    't': ins.op_str,
                    'disp_abs': '0x%X' % a,
                    'index': md.reg_name(o.mem.index) if o.mem.index else None,
                    'scale': o.mem.scale,
                    'base_reg': md.reg_name(o.mem.base) if o.mem.base else None,
                })
            break

print('in-window (0x520000..0x524000) mem sites:', len(sites))
g = defaultdict(list)
for s in sites:
    g[s['disp_abs']].append(s)
for k in sorted(g, key=lambda x: int(x, 16)):
    print(k, 'count=', len(g[k]))
    for s in g[k][:16]:
        print('   ', s['sec'], s['va'], s['m'], s['t'],
              'idx=%s scale=%s base=%s' % (s['index'], s['scale'], s['base_reg']))

# ---- imul 7 与容量常数 ----
print('\n=== imul *,7 in .text ===')
hits7 = []
for name, sv, ss, pr, sr in secs:
    if name != '.text':
        continue
    buf = data[pr:pr+sr]
    for ins in sweep(buf, sv):
        if ins.mnemonic == 'imul':
            for o in ins.operands:
                if o.type == X86_OP_IMM and o.imm == 7:
                    hits7.append((ins.address, ins.op_str))
print('count:', len(hits7))
for a, t in hits7[:60]:
    print('  0x%X  imul %s' % (a, t))

# ---- 0x520660 / 0x521AA8 / 0x522C88 作为立即数(dword 窗口)出现处 ----
print('\n=== raw dword windows ===')
targets = {0x520660: 'SURNAME', 0x521AA8: 'GIVEN', 0x522C88: 'UNK_522C88'}
for tv, label in targets.items():
    pk = struct.pack('<I', tv)
    found = []
    for name, sv, ss, pr, sr in secs:
        off = pr
        end = pr + sr
        while True:
            j = data.find(pk, off, end)
            if j < 0:
                break
            va = None
            for name2, sv2, ss2, pr2, sr2 in secs:
                if pr2 <= j < pr2 + sr2 and sv2 <= base + (j - pr2) < sv2 + ss2:
                    va = base + (j - pr2)
                    break
            found.append('%s+0x%X%s' % (name, j - pr, (' VA 0x%X' % va) if va else ''))
            off = j + 1
    print(label, hex(tv), 'len=', len(found))
    for f in found[:24]:
        print('   ', f)

# ---- .data 中 0x520000..0x524000 段的占用画像: 哪些偏移非零, 结构参考 ----
print('\n=== .data occupancy 0x520600..0x523000 (16B rows, compressed) ===')
for name, sv, ss, pr, sr in secs:
    if name != '.data':
        continue
    a0, a1 = 0x520600, 0x523000
    off0, off1 = pr + (a0 - sv), pr + (a1 - sv)
    blob = data[off0:off1]
    # 每 0x40 打一行 hex 摘要太细; 找零运行长度 >= 0x20 的空洞
    run = 0
    runs = []
    for idx in range(len(blob)):
        if blob[idx] == 0:
            run += 1
        else:
            if run >= 0x20:
                runs.append(('0x%X..0x%X' % (a0 + idx - run, a0 + idx - 1), run))
            run = 0
    if run >= 0x20:
        runs.append(('0x%X..end' % (a0 + len(blob) - run), run))
    print('zero-runs >=0x20:')
    for r in runs:
        print('  ', r[0], 'len 0x%X' % r[1])
