import pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE = 0x400000
d, starts = pickle.load(open('scripts/_insn_addrs.pkl', 'rb'))
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}
def fn_of(off):
    best=None
    for st in sorted(starts):
        if st<=off: best=st
        else: break
    return best if best is not None else off
print('=== callers of 0x4cf280 ===')
for off,s in SIZE.items():
    if TEXT[off]=='call 0x4cf280':
        print(f'  0x{BASE+off:06x} (fn 0x{BASE+fn_of(off):06x})')
print('=== callers of 0x4cf280 passing 0x516610? scan args ===')
# 找 push 0x516610 后紧跟 call 0x4cf280（同函数）
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
for off,s in SIZE.items():
    if TEXT[off]=='call 0x4cf280':
        # 向前看 0x20 内是否有 push 0x516610
        o=off
        found=False
        while o>off-0x30 and o in SIZE:
            o-=SIZE[o]
            if TEXT[o]=='push 0x516610':
                found=True; break
        if found:
            print(f'  >>> 0x{BASE+off:06x} 之前 push 0x516610 (S6 传入!)')
