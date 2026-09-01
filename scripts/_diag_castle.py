
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
import json, struct, os

ROOT = _ROOT
def decode(fn):
    with open(fn,'rb') as f: data=f.read()
    assert data[:16]==b'TAIKOU2_SCENARIO', fn
    key = data[0x12]^data[0x13]
    stream = bytearray(data[0x598:])
    for i in range(len(stream)): stream[i]^=key
    return key, bytes(stream)

def hexdump(b, off, n):
    out=[]
    for i in range(0,n,26):
        chunk=b[off+i:off+i+26]
        h=' '.join(f'{x:02x}' for x in chunk)
        out.append(f"  +{i:3d}  {h}")
    return '\n'.join(out)

for sc, fn in (("sc1",_ROOT + '/Taikou2 Original/SNDATA1.TR2'),):
    key, s = decode(os.path.join(ROOT, fn))
    print(f"=== {sc}: XOR key=0x{key:02x} streamlen={len(s)} ===")
    print(f"province@27052 = {list(s[27052:27057])}  (expect [5,0,64,28,0])")
    # self-idx discriminator: find base/stride/pos giving 0..199 for 200 records
    best=[]
    for S in range(20,40):
        for P in range(0,8):
            for base in range(0, len(s)-S*200):
                cnt=sum(1 for i in range(200) if base+S*i+P < len(s) and s[base+S*i+P]==i)
                if cnt>=190:
                    best.append((cnt,S,P,base))
    best.sort(reverse=True)
    print("top self-idx matches (cnt,S,P,base):")
    for c in best[:12]:
        print("  ",c, f" ends@ {c[3]+c[1]*200}")
    print()
    for base in (21852,21492):
        print(f"--- base {base} (first 3 records, 26B each) ---")
        print(hexdump(s, base, 3*26))
    # entity idx word at base 21852: are values < 0x172 mostly?
    print("\nentity_idx (WORD@0) at 21852/26:")
    eids=[s[21852+26*i]|(s[21852+26*i+1]<<8) for i in range(200)]
    print("  min",min(eids),"max",max(eids),"sentinel0x172",sum(1 for e in eids if e==0x172))
    print("  first 12:", eids[:12])
