#!/usr/bin/env python3
# 分析物品表三字节 tier/flag/unk 的打包/语义
import json
from collections import Counter, defaultdict
d=json.load(open('item_table.json'))

by_flag=defaultdict(list)
for x in d: by_flag[x['flag']].append(x)

print("=== flag=0 (18条) ===")
for x in by_flag[0]:
    print(f"  {x['idx']:3d} {x['name']:10s} cat={x['cat']:2d} val={x['val']:3d} tier={x['tier']:3d} unk={x['unk']:3d}")
print("=== flag=0xff (1条) ===")
for x in by_flag[255]:
    print(f"  {x['idx']:3d} {x['name']:10s} cat={x['cat']:2d} val={x['val']:3d} tier={x['tier']:3d} unk={x['unk']:3d}")

print("\n=== flag=0x80 (170条) 的 tier/unk 分布 ===")
t128=by_flag[128]
print("tier dist:", sorted(Counter(x['tier'] for x in t128).items())[:30])
print("unk dist:", sorted(Counter(x['unk'] for x in t128).items())[:30])
# tier vs val 相关性
print("\nflag=0x80: 抽样 (idx,name,cat,val,tier,unk)")
for x in t128[:25]:
    print(f"  {x['idx']:3d} {x['name']:10s} cat={x['cat']:2d} val={x['val']:3d} tier={x['tier']:3d} unk={x['unk']:3d}")

# 假设：tier == val ? 或 tier 是 val 的某种函数
print("\n=== 检验 tier 与 val 关系 ===")
eq=sum(1 for x in d if x['tier']==x['val'])
print(f"tier==val: {eq}/189")
# tier 是否是 (val 的高位或 rank)
# 检查 unk 是否按 cat 分组
print("\n=== unk 是否按 cat 聚集 (flag=0x80) ===")
cat_unk=defaultdict(set)
for x in t128: cat_unk[x['cat']].add(x['unk'])
for c in sorted(cat_unk):
    if len(cat_unk[c])<=6:
        print(f"  cat={c:2d}: unk={sorted(cat_unk[c])}")
    else:
        print(f"  cat={c:2d}: {len(cat_unk[c])} distinct unk")
# 检查 (cat,unk) 是否唯一确定 tier
print("\n=== (cat,unk) -> tier 是否唯一 (抽样) ===")
cu=defaultdict(set)
for x in d: cu[(x['cat'],x['unk'])].add(x['tier'])
multi=[k for k,v in cu.items() if len(v)>1]
print(f"(cat,unk) 冲突数: {len(multi)} / {len(cu)}")
# 检查 (cat,val) -> tier 是否唯一
cv=defaultdict(set)
for x in d: cv[(x['cat'],x['val'])].add((x['tier'],x['flag'],x['unk']))
multi2=[k for k,v in cv.items() if len(v)>1]
print(f"(cat,val) 冲突数: {len(multi2)} / {len(cv)}")
# 是否 (cat,val) 唯一确定全部三字节?
cv_all=defaultdict(set)
for x in d: cv_all[(x['cat'],x['val'])].add((x['tier'],x['flag'],x['unk']))
uniq=[k for k,v in cv_all.items() if len(v)==1]
print(f"(cat,val) 唯一确定三字节: {len(uniq)}/{len(cv_all)}")
# 反过来：三字节是否唯一确定 cat? 
tu=defaultdict(set)
for x in d: tu[(x['tier'],x['flag'],x['unk'])].add(x['cat'])
print(f"三字节唯一确定 cat: {sum(1 for v in tu.values() if len(v)==1)}/{len(tu)}")
