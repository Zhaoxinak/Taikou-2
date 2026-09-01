
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

# 按 cat 分类看 val
from collections import defaultdict
by_cat = defaultdict(list)
for it in items:
    by_cat[it['cat']].append(it)

# cat 0..26 (续73)
for cat_id in sorted(by_cat.keys()):
    cat_items = by_cat[cat_id]
    sample = cat_items[:3]
    vals = [it['val'] for it in cat_items]
    avg = sum(vals)/len(vals) if vals else 0
    print('cat={:2d} count={:3d} avg_val={:.1f} sample: {}'.format(
        cat_id, len(cat_items), avg,
        [(it['name'], it['val']) for it in sample]))
