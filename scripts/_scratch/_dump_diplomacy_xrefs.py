from capstone import *
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
MEM = open('scripts/_unpacked_mem.bin','rb').read()

xrefs = [0x507f5f, 0x509c7e, 0x509f48, 0x509f58, 0x50c7e0, 0x50ce45]

for va in xrefs:
    off = va - 0x400000
    end = min(off + 0x100, len(MEM))
    code = MEM[off:end]
    print('=== xref', hex(va), '===')
    for ins in md.disasm(code, va):
        s = '{:08x}  {:8s} {}'.format(ins.address, ins.mnemonic, ins.op_str)
        if '49f6b0' in ins.op_str:
            s += '  ; << getCtx'
        if '49b860' in ins.op_str:
            s += '  ; << FIRE'
        if '47b900' in ins.op_str:
            s += '  ; << msgDispatch'
        print(s)
    print()
