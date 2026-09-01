
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
import json
with open(_ROOT + '/scripts/item_table.json','rb') as f:
    data = f.read().decode('utf-8', errors='replace')
items = json.loads(data)
print('total items:', len(items))
sorted_items = sorted(items, key=lambda x: -x.get('val', 0))
for it in sorted_items[:15]:
    print('idx={:3d} val={:6d} cat={} tier={:3d} flag={:3d} name={}'.format(
        it['idx'], it['val'], it['cat'], it['tier'], it['flag'], it['name']))
print()
import statistics
vals = [it['val'] for it in items]
print('val: min={} max={} mean={:.1f} median={}'.format(
    min(vals), max(vals), statistics.mean(vals), statistics.median(vals)))
print('val==0:', sum(1 for v in vals if v == 0))
