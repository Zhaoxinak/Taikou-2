# 0x172(370) 使用点全量清点与语义分类
# 目的: 判定"扩容"需要 patch 的点集与不能动的点集(哨兵/mov 循环常数)
# 分类: BOUND(cmp/jae 越界界) | SENT(cmp je/jne==0x172 哨兵) | LOOP(mov/cmp jb 循环) | OTHER
import struct, pefile, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_REG, X86_OP_MEM

EXE = r"F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe"
pe = pefile.PE(EXE)
BASE = pe.OPTIONAL_HEADER.ImageBase
sec = [s for s in pe.sections if s.Name.rstrip(b"\0") == b".text"][0]
code = sec.get_data()
t_va = BASE + sec.VirtualAddress
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# 先建立"合法指令链"集合: 线性扫描+失步重同步, 记录每条指令
insns = {}   # addr -> (bytes, mnem, ops_text, op0kind, op0val)
pos, end = 0, len(code)
while pos < end:
    progressed = False
    for ins in md.disasm(code[pos:end], t_va + pos):
        progressed = True
        pos = ins.address - t_va + len(ins.bytes)
        insns[ins.address] = ins
    if not progressed:
        pos += 1

JCC = {  # x86 jcc opcode low nibble / mnemonic
}
results = []
for addr, ins in sorted(insns.items()):
    hit = None
    for op in ins.operands:
        if op.type == X86_OP_IMM and (op.imm & 0xFFFFFFFF) == 0x172:
            hit = op
            break
        if op.type == X86_OP_MEM and (op.mem.disp & 0xFFFFFFFF) == 0x172:
            hit = op
            break
    if hit is None:
        continue
    m = ins.mnemonic
    # 找后续分支(若是 cmp): 取下一条指令
    nxt = None
    if m == "cmp":
        npos = addr + len(ins.bytes)
        nxt = insns.get(npos)
    kind = "?"
    cond = ""
    if m == "cmp":
        if nxt and nxt.mnemonic.startswith("j"):
            cond = nxt.mnemonic
            if cond in ("jae", "ja", "jb", "jbe", "jl", "jge"):
                kind = "BOUND"
            elif cond in ("je", "jne"):
                kind = "SENT"
            elif cond in ("jmp",):
                kind = "CMP+jmp"
            else:
                kind = "CMP+" + cond
        else:
            kind = "CMP(no-jcc)"
    elif m in ("mov", "lea", "xor", "or", "and", "sub", "add", "imul", "push", "cmpxchg"):
        kind = "SET/" + m if m in ("mov", "push") else "ALU/" + m
    elif m == "j":
        kind = "Jcc"
    else:
        kind = "OTHER/" + m
    results.append({
        "addr": addr, "off": addr - t_va, "bytes": ins.bytes.hex(),
        "text": "%s %s" % (m, ins.op_str),
        "kind": kind, "cond": cond,
        "next": ("%s %s" % (nxt.mnemonic, nxt.op_str)) if nxt else "",
    })

results.sort(key=lambda r: r["off"])
from collections import Counter
c = Counter(r["kind"] for r in results)
print("== 0x172 使用点 %d 处 ==" % len(results))
for k, v in c.most_common():
    print("  %-12s x%d" % (k, v))
json.dump(results, open("_sites_172.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("明细 -> _sites_172.json")
