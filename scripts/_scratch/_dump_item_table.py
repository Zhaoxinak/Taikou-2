import json
with open('scripts/item_table.json','rb') as f:
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
