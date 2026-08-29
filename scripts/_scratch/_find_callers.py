from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
TARGETS={0x441580,0x4414d0,0x4411b0}
hits={t:[] for t in TARGETS}
for ins in md.disasm(mem, 0x400000):
    if ins.mnemonic=='call' and ins.op_str.startswith('0x'):
        t=int(ins.op_str,16)
        if t in TARGETS:
            hits[t].append(ins.address)
for t in TARGETS:
    print(f"callers of {t:#x}: {[hex(x) for x in hits[t][:10]]}")
