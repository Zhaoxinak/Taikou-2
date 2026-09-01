
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
for sc, fn in (("sc1",_ROOT + '/Taikou2 Original/SNDATA1.TR2'),("sc2",_ROOT + '/Taikou2 Original/SNDATA2.TR2')):
    data=open(os.path.join(ROOT,fn),'rb').read()
    print(f"=== {sc} len={len(data)} ===")
    print("magic:", data[:16])
    print("hdr[0x10:0x20]:", list(data[0x10:0x20]))
    print("data[0x12]^data[0x13] = 0x%02x" % (data[0x12]^data[0x13]))
    # try several (base, key) combos and check province@27052 vs [5,0,64,28,0]
    for base in (1420, 1432, 9612, 0):
        for ko in ("xor12_13",):
            key = data[0x12]^data[0x13]
            s=bytearray(data[base:])
            for i in range(len(s)): s[i]^=key
            pv=list(s[27052:27057])
            print(f"  base={base} key=0x{key:02x} province@27052={pv}")
