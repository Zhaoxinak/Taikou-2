
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
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
data = MEM[0x50c7c0-0x400000:0x50c7c0-0x400000+240]
print('raw bytes 0x50c7c0..+240:')
for i in range(0, 240, 14):
    chunk = data[i:i+14]
    h = chunk.hex()
    s = chunk.decode('gbk', errors='replace')
    print(f'+{i:#04x}: {h} | {s}')
