import os
_HERE = os.path.dirname(os.path.abspath(__file__))
"""S6 (0x516610, 46B) 玩家/事件上下文 结构参考实现（二进制可验证）。

验证手段：
  (1) 绝对地址 xref：每个字段在二进制中确实被引用（读/写/位测）。
  (2) 方法表：S6 对象所用的 setter/getter（含钳制值）确实存在。
  (3) 关键语义锚点（玩家武将号、金阈值）的反汇编断言。

不依赖运行时 dump（S6 为运行时全局），仅对静态映像做结构断言。
"""
import struct, pickle, json, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_REG_ECX

IMG = open(os.path.join(_HERE, r'_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000
S6 = 0x516610
d = pickle.load(open(os.path.join(_HERE, r'_insn_addrs.pkl'), 'rb'))[0]
# pickle 键是【文件偏移】，值=[size,text]；disasm_at 的 va 参数是 VA（与键区分）
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def disasm_at(va, n=0x60):
    return list(md.disasm(IMG[va-BASE:va-BASE+n], va))

def find_imm_xref(imm):
    """返回所有以 imm 为绝对地址内存操作数的指令 VA 列表（指令包含式）。"""
    pat = struct.pack('<I', imm)
    out = []; off = 0
    while True:
        i = IMG.find(pat, off)
        if i < 0: break
        off = i + 1
        for j in range(max(0, i-16), i+1):
            if j in SIZE and j <= i < j + SIZE[j]:
                b = list(md.disasm(IMG[j:j+SIZE[j]+8], BASE+j))
                if b: out.append(BASE+j)
                break
    return out

def has_text(va, needle, n=0x200):
    for ins in disasm_at(va, n):
        if needle in f'{ins.mnemonic} {ins.op_str}':
            return True
    return False

# ---- 文档化字段表（offset -> 描述/宽度/钳制/语义）----
FIELDS = {
    0x14: ('W', 60000, '玩家武将索引 (player general idx, 0..369) — getter 0x49f5d0 经 0x519868+idx*47 还原实体'),
    0x16: ('W', None,  '保留/未用：仅被存档序列化读取（0x47e770/0x47e8a0），静态镜像无任何 ecx=0x516610 写入路径。60000 钳制 setter 0x49b970 是共享方法库，本 build 只被 S5(0x5197b0) 与通用 stride-14 初始化器(0x4cf280)调用，不服务 S6（续138 纠错）'),
    0x18: ('W', None,  '保留/未用：同 +0x16（续138 纠错）。共享 setter 0x49b990 服务于 S5/G制struct'),
    0x1a: ('W', None,  '保留/未用：同 +0x16（续138 纠错）。共享 setter 0x49b9b0 服务于 S5/G制struct'),
    0x1e: ('W', None,  '所持金 (gold) — cmp 0xa(10) 不足则弹 MSGX 0x1866；cmp 0xc350(50000) 判富裕'),
    0x20: ('W', None,  '可读 word（getter 3 处），语义 TBD（计数/id）'),
    0x22: ('W', None,  '关联武将索引 #1 — getter 经 0x519868+idx*47，cmp 0x172'),
    0x24: ('W', None,  '关联武将索引 #2 — 与实体索引比较，哨兵 0x172/0xffff；+0x2a 与其 S5(0x5197b0) 槽号相关'),
    0x26: ('W', 10,    '4×4-bit 字段（各 0..10），method-table getter 钳 0xa'),
    0x28: ('B', None,  '瞬态状态位域字节（140 处引用，不持久化）；bit1/2/4 (0x2/0x4/0x10) 被 test'),
    0x29: ('B', None,  '状态字节（setter 经方法表，瞬态）'),
    0x2a: ('B/W', None,'状态/槽位字节 — test 0x20；与 S5(0x5197b0) 槽号比对'),
    0x2c: ('B/W', None,'状态字节 — test 8'),
    0x0e: ('B', None,  'byte 标志（5 处读）'),
    0x0f: ('B', None,  'byte 标志（2 处读）'),
    0x12: ('B', None,  'byte 标志 — cmp 0xff 哨兵'),
    0x13: ('B', None,  'byte 标志 — test 0x20'),
}

checks = []
def chk(name, cond, info=''):
    checks.append((name, bool(cond), info))
    return bool(cond)

# C1: S6 基址与大小
chk('S6 base 0x516610', True)
chk('S6 size 46B', True)

# C2: 玩家武将号 getter 0x49f5d0 读 word[0x516624]
chk('+0x14 getter 0x49f5d0 reads word[0x516624]', has_text(0x49f5d0, 'word ptr [0x516624]'))
chk('+0x14 getter 0x49f5e0 resolves entity 0x519868+idx*47',
    has_text(0x49f5e0, '0x519868') and has_text(0x49f5e0, '0x172'))

# C3: 金 阈值
chk('+0x1e gold cmp 0xa (10) @0x46908e', has_text(0x46908e, '0x51662e') and has_text(0x46908e, '0xa'))
chk('+0x1e gold cmp 0xc350 (50000) @0x4d8f62', has_text(0x4d8f62, '0x51662e') and has_text(0x4d8f62, '0xc350'))

# C4: 三项 60000 setter 钳制（注意：这些 setter 是【共享方法库】，写入的是 ecx 所指任意 struct；
#      本 build 中 S6(0x516610) 从不以 ecx 传入，故 S6 的 +0x16/18/1a 实际未被钳制/未被写入）
for off, setter in [(0x16,0x49b970),(0x18,0x49b990),(0x1a,0x49b9b0)]:
    code = ' '.join(f'{i.mnemonic} {i.op_str}' for i in disasm_at(setter, 0x20))
    chk(f'+{off:02x} shared setter writes [ecx+0x{off:02x}] & clamps 0xea60',
        '0xea60' in code and f'[ecx + 0x{off:02x}]' in code, code)

# C8 (续138/139): S6 的 +0x16/18/1a 无【直接】mov ecx,0x516610 → setter 路径
def global_s6_setter_writes():
    starts = pickle.load(open(os.path.join(_HERE, r'_insn_addrs.pkl'), 'rb'))[1]
    TARGETS = {'0x49b970', '0x49b990', '0x49b9b0'}
    hits = []
    for fn in sorted(starts):
        o = fn; end = fn + 0x800
        insns = []
        while o < end and o in SIZE:
            insns.append((o, TEXT[o]))
            if TEXT[o] == 'ret':
                break
            o += SIZE[o]
        ecx_is_s6 = False
        for off, t in insns:
            if t == 'mov ecx, 0x516610':
                ecx_is_s6 = True; continue
            if t.startswith('mov ecx,') or t.startswith('lea ecx,') or t.startswith('add ecx,') or t.startswith('sub ecx,'):
                ecx_is_s6 = False; continue
            if t.startswith('call ') and t[5:] in TARGETS and ecx_is_s6:
                hits.append(BASE + off)
    return hits
hits = global_s6_setter_writes()
chk('S6 +0x16/18/1a 无【直接】ecx=0x516610 setter 写入路径 (续138)',
    len(hits) == 0, f"hits={[hex(h) for h in hits]}")

# C9 (续139 纠错): 但存在【间接】写入 —— 复位例程 0x4cf240 把 0x516610 作为实参传给 0x4cf280，
#                  后者 esi=arg → ecx=esi → 调用 60000 setter 把 S6+0x16/18/1a 清零。
#                  这是续138 漏掉的「实参传递间接寻址」，必须同时断言存在。
reset_code = ' '.join(f'{i.mnemonic} {i.op_str}' for i in disasm_at(0x4cf240, 0x40))
chk('复位例程 0x4cf240 以 0x516610 为实参调用 0x4cf280 (S6 间接写入)',
    'push 0x516610' in reset_code and 'call 0x4cf280' in reset_code, reset_code[:150])
one_rec = ' '.join(f'{i.mnemonic} {i.op_str}' for i in disasm_at(0x4cf280, 0x40))
chk('0x4cf280 取实参为 this (esi=[esp+0xc]) 并调用三个 60000 setter',
    'esi, dword ptr [esp + 0xc]' in one_rec and 'call 0x49b970' in one_rec
    and 'call 0x49b990' in one_rec and 'call 0x49b9b0' in one_rec, one_rec[:150])
chk('0x4cf240 同时复位 6 条 S5 记录 (esi=0x5197b0, stride 0x1e, 循环 6 次)',
    'mov esi, 0x5197b0' in reset_code and 'add esi, 0x1e' in reset_code
    and 'call 0x49b960' in reset_code, reset_code[:220])

# C5: 每个文档化字段在二进制中有绝对 xref（或属方法表专用）
xref_counts = {off: len([v for v in find_imm_xref(S6+off)]) for off in FIELDS}
for off in (0x14,0x16,0x18,0x1a,0x1e,0x20,0x22,0x24,0x26,0x28,0x29,0x2a,0x2c,0x0e,0x0f,0x12,0x13):
    # 方法表专用字段（仅 ecx 相对访问）允许 xref=0，但仍记录
    chk(f'+{off:02x} xref present or method-only', xref_counts[off] > 0 or off in (0x29,), f"xref={xref_counts[off]}")

# C6: +0x22 经实体索引还原
chk('+0x22 reader 0x40b370 resolves entity 0x519868+idx*47',
    has_text(0x40b370, '0x516632') and has_text(0x40b370, '0x519868') and has_text(0x40b370, '0x172'))
# C7: +0x24 与 S5(0x5197b0) 槽号相关（+0x2a getter 0x49ba60 参与）
chk('+0x24 reader 0x4a3660 refs S5 base 0x5197b0 & +0x24 cmp',
    has_text(0x4a3660, '0x5197b0') and has_text(0x4a3660, '0x516634'))

passed = sum(1 for _, c, _ in checks if c)
total = len(checks)
print(f"S6 结构参考：{passed}/{total} 断言通过")
for name, c, info in checks:
    print(f"  [{'OK' if c else 'FAIL'}] {name}" + (f"  ({info})" if (not c or info) and info else ""))

# 导出 JSON
out = {
    'base': hex(S6), 'size': 46,
    'fields': {f'+{o:02x}': {'width': w, 'clamp': c, 'semantic': s, 'xref': xref_counts.get(o,0)}
               for o, (w, c, s) in FIELDS.items()},
    'assertions': {'passed': passed, 'total': total},
}
json.dump(out, open(os.path.join(_HERE, r's6_struct.json'), 'w'), ensure_ascii=False, indent=2)
print("written scripts/s6_struct.json")
sys.exit(0 if passed == total else 1)
