
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
import re, struct
b=open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read(); BASE=0x400000
def va2off(v): return v-BASE
def find_imm32(v):
    pat=struct.pack("<I", v); return [BASE+m.start() for m in re.finditer(re.escape(pat), b)]
print("== 裸名串搜索 ==")
for s in (b"PRESS.GRP", b"END.GRP", b"SMODE.GRP", b"EXTFACE.PK8", b"GRPDATA", b".GRP", b".PK8"):
    hits=[BASE+m.start() for m in re.finditer(re.escape(s), b)]
    print(s, [hex(h) for h in hits][:10], "n=",len(hits))
print()
print("== 名串地址的 imm32 引用 ==")
for name,va in (("A:ACERTWP.GRP",0x50a178),("A:KOEILOGO.GRP",0x50a2b0),("A:SMODE.GRP",0x50da30),("A:EXTFACE.PK8",0x506bf0),("C:NPKDATA.IDX",0x506b80)):
    print(name, hex(va), "->", [hex(x) for x in find_imm32(va)])
