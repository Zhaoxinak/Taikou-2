
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>
from capstone import *
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()

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
