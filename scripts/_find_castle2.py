
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
import os
ROOT=_ROOT
def decode(fn):
    data=open(os.path.join(ROOT,fn),'rb').read()
    key=data[0x12]^data[0x13]
    s=bytearray(data[0x598:])
    for i in range(len(s)): s[i]^=key
    return key, bytes(s)
def u16(b,i): return b[i]|(b[i+1]<<8)
for sc,fn in (("sc1",_ROOT + '/Taikou2 Original/SNDATA1.TR2'),("sc2",_ROOT + '/Taikou2 Original/SNDATA2.TR2')):
    key,s=decode(fn)
    print(f"\n=== {sc}: key=0x{key:02x} ===")
    cands=[]
    for base in range(21820,21870):
        sj=[s[base+26*i+2] for i in range(200)]
        ent=[u16(s,base+26*i) for i in range(200)]
        if set(sj)==set(range(200)) and all((e<=370 or e==0x172) for e in ent):
            cands.append(base)
    print("permutation-of-0..199 bases:", cands)
    # also: best base by how many self-idx are unique & in 0..199 and entity valid
    best=[]
    for base in range(21790,21890):
        sj=[s[base+26*i+2] for i in range(200)]
        ent=[u16(s,base+26*i) for i in range(200)]
        ok=sum(1 for e in ent if e<=370 or e==0x172)
        uniq=len(set(sj))
        inrange=sum(1 for x in sj if x<200)
        best.append((uniq,inrange,ok,base))
    best.sort(reverse=True)
    print("top by (unique_self, inrange_self, valid_ent):", best[:8])
    if cands:
        b=cands[0]
        print(f"\n-> base {b}: self-idx is exact permutation 0..199")
        sj=[s[b+26*i+2] for i in range(200)]
        # show mapping record_i -> self_idx (should be non-trivial)
        print("  rec0..9 self_idx:", sj[:10])
