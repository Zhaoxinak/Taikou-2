import json
with open('scripts/item_table.json','rb') as f:
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
