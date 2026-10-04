# -*- coding: utf-8 -*-
"""probe_oidaudit.py — M1: oid 身份层全量静态清点 (只读 zoom.exe, 不改)

编号体系(本次修正):
  [ent+0]=slot(池/名表索引,0..369) ; [ent+2]=oid/bushou_id(0..699, 稀疏)
按 oid 索引的结构: BSDATA(0x524a20, stride59), 登场标志(0x519288, 700B), 第二状态表(0x2bc 长)

清点目标:
  A. 引用 BSDATA 基址 0x524a20 的指令 + 附近 *59 (imul/lea) 索引模式
  B. 引用登场标志基址 0x519288 的指令 (imm32/push/disp)
  C. 全 .text/.data 里 imm 0x2bc(700) / 0x2bb(699) 出现处
  D. imm 0x3b(59) 与 imul *,59 = oid*59 BSDATA 索引
  E. 调查卡主体全局 0x520630 的读写(判它存 slot 还是 oid)
"""
import pefile, struct, json
from collections import Counter, defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

EXE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.__data__
secs = [(s.Name.rstrip(b'\0').decode(), base + s.VirtualAddress,
         s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]

BSDATA = 0x524a20
APPEAR = 0x519288
CARD   = 0x520630

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def sweep(buf, va):
    i, n = 0, len(buf)
    while i < n:
        adv = False
        for size in range(1, 16):
            if i + size > n: break
            for ins in md.disasm(buf[i:i+size], va+i):
                if len(ins.bytes) == size:
                    yield ins; i += size; adv = True; break
            if adv: break
        if not adv: i += 1

report = defaultdict(list)
imm_counters = Counter()

for nm, sv, ss, pr, sr in secs:
    if nm == '.rsrc': continue
    buf = data[pr:pr+sr]
    for ins in sweep(buf, sv):
        txt = '%s %s' % (ins.mnemonic, ins.op_str)
        for o in ins.operands:
            # A/E/B: 绝对地址 imm 或 disp
            if o.type == X86_OP_IMM:
                v = o.imm & 0xFFFFFFFF
                if v == BSDATA: report['A_BSDATA_ref'].append((nm, '0x%X'%ins.address, txt))
                elif v == APPEAR: report['B_APPEAR_ref'].append((nm, '0x%X'%ins.address, txt))
                elif v == CARD: report['E_CARD_ref'].append((nm, '0x%X'%ins.address, txt))
                elif v in (0x2bc, 0x2bb): report['C_700_imm'].append((nm, '0x%X'%ins.address, txt))
                elif v == 0xa154: report['C_41300_imm'].append((nm, '0x%X'%ins.address, txt))  # BSDATA size push
            if o.type == X86_OP_MEM:
                d = o.mem.disp & 0xFFFFFFFF
                if d == BSDATA: report['A_BSDATA_ref'].append((nm, '0x%X'%ins.address, txt))
                elif d == APPEAR: report['B_APPEAR_ref'].append((nm, '0x%X'%ins.address, txt))
                elif d == CARD: report['E_CARD_ref'].append((nm, '0x%X'%ins.address, txt))
            # D: imul *,59
        if ins.mnemonic == 'imul':
            for o in ins.operands:
                if o.type == X86_OP_IMM and o.imm == 59:
                    report['D_imul59'].append((nm, '0x%X'%ins.address, txt))
                if o.type == X86_OP_IMM and o.imm == 47:
                    report['D_imul47'].append((nm, '0x%X'%ins.address, txt))

print('==== M1 oid 层清点 ====')
order = ['A_BSDATA_ref','D_imul59','B_APPEAR_ref','C_700_imm','C_41300_imm','E_CARD_ref','D_imul47']
for k in order:
    v = report[k]
    print('\n[%s] 命中 %d' % (k, len(v)))
    secn = Counter(x[0] for x in v)
    print('   按节:', dict(secn))
    for row in v[:30]:
        print('   ', row)

# BSDATA 引用点上下文(看是否 *59 索引) + CARD 读写方向
def context(va_hex, want_sec, span=24):
    for nm, sv, ss, pr, sr in secs:
        if nm != want_sec: continue
        off = pr + (va_hex - sv)
        for ins in sweep(data[off-span:off+span], va_hex-span):
            yield ins

print('\n==== CARD 0x520630 读写方向 (判 slot/oid) ====')
for nm, vs, txt in report['E_CARD_ref']:
    va = int(vs, 16)
    print('\n%s %s @ %s' % (nm, vs, txt))
    for ins in context(va, nm, 20):
        print('    0x%X %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))

json.dump({k: v for k, v in report.items()},
          open('_m1_oid_audit.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n-> _m1_oid_audit.json')
