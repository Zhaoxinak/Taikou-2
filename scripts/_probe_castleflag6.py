from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
def off_of(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

addr = 0x516638
a = addr.to_bytes(4, "little")   # correct LE = 38 66 51 00
assert a == bytes([0x38,0x66,0x51,0x00]), a.hex()

def find_pat(pat):
    out=[]; s=0
    while True:
        i = MEM.find(pat, s)
        if i<0: break
        out.append(BASE+i); s=i+1
    return out

# absolute store forms
abs_w = {
 "or byte,4": b'\x80\x0d'+a+b'\x04',
 "and byte,fb": b'\x80\x25'+a+b'\xfb',
 "mov byte,imm": b'\xc6\x05'+a,
 "mov [addr],al (a2)": b'\xa2'+a,
 "mov [addr],eax(a3)": b'\xa3'+a,
 "or  byte SIB,4": b'\x80\x0c\x25'+a+b'\x04',
 "and byte SIB,fb": b'\x80\x24\x25'+a+b'\xfb',
}
# register-indirect writers: load 0x516638 into reg, then or/and byte[reg]
regload = {}
for reg in range(8):
    regload[reg] = bytes([0xb8+reg]) + a   # mov eX, 0x516638

writers = []
notes = []
for name, pat in abs_w.items():
    h = find_pat(pat)
    if h:
        writers.extend(h); notes.append(f"{name}: {[f'{x:08x}' for x in h]}")
for reg in range(8):
    rl = regload[reg]
    s=0
    while True:
        i = MEM.find(rl, s)
        if i<0: break
        va = BASE+i
        code = MEM[off_of(va):off_of(va)+0x30]
        fwd = list(md.disasm(code, va))
        for ins in fwd[:10]:
            # look for or/and byte [eReg], imm  (80 /1 or /4 with modrm [eReg])
            # or byte[eax],4 -> 80 08 04 ; and byte[eax],fb -> 80 20 fb
            if ins.mnemonic in ("or","and") and "byte ptr" in ins.op_str:
                # check it references the loaded reg
                regname = ['eax','ecx','edx','ebx','esp','ebp','esi','edi'][reg]
                if regname in ins.op_str:
                    writers.append(va); notes.append(f"reg-indirect {regname} @ {va:08x}: {ins.mnemonic} {ins.op_str}")
                    break
        s = i+1

with open(r"F:/Games/Taikou 2/scripts/_castleflag_fixed.txt", "w", encoding="utf-8") as f:
    f.write(f"=== 0x516638 城主flag 写入者（修正LE） ===\n")
    f.write("\n".join(notes) if notes else "(none found)")
    f.write(f"\n\ntotal writer refs: {len(writers)}\n")

print(f"[OK ] writers={len(writers)}")
for n in notes:
    print("  ", n)
