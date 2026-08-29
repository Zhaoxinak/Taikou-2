#!/usr/bin/env python3
# 检验：byte17(现"unk") 是否=组/系列id(相关物品共享)；byte15(现"tier") 是否=rank(与val相关)
import json
from collections import defaultdict
d=json.load(open('item_table.json'))

# 用当前字段名: tier=byte15, flag=byte16, unk=byte17
groups=defaultdict(list)
for x in d: groups[x['unk']].append(x)  # 按当前 unk(=byte17) 分组

print("=== 按 byte17(现unk) 分组，看是否相关物品同组 ===")
for g,items in sorted(groups.items()):
    if len(items)>=2:
        names=", ".join(f"{i['name']}(v{i['val']},t{i['tier']})" for i in items)
        print(f"  unk={g:3d} ({len(items)}): {names}")

# rank(byte15) 与 val 关系：flag=0x80 中
print("\n=== byte15(现tier) vs val（flag=0x80 抽样，看 rank 是否∝val）===")
for x in d:
    if x['flag']==0x80 and x['cat'] in (3,):  # 茶道具类
        print(f"  {x['name']:8s} val={x['val']:3d} byte15(tier)={x['tier']:2d} byte17(unk)={x['unk']:3d}")

# 假设 byte15 = floor(val/k) 之类；检查 byte15 与 val 的相关系数(简单)
import statistics
pairs=[(x['val'],x['tier']) for x in d if x['flag']==0x80]
if len(pairs)>2:
    vs=[p[0] for p in pairs]; ts=[p[1] for p in pairs]
    mv=statistics.mean(vs); mt=statistics.mean(ts)
    cov=sum((v-mv)*(t-mt) for v,t in pairs)/len(pairs)
    sv=statistics.pstdev(vs); st=statistics.pstdev(ts)
    corr=cov/(sv*st) if sv*st else 0
    print(f"\nflag=0x80: corr(val, byte15)={corr:.3f}")

# 反过来假设 byte17 = rank：corr(val, byte17)
pairs2=[(x['val'],x['unk']) for x in d if x['flag']==0x80]
if len(pairs2)>2:
    vs=[p[0] for p in pairs2]; ts=[p[1] for p in pairs2]
    mv=statistics.mean(vs); mt=statistics.mean(ts)
    cov=sum((v-mv)*(t-mt) for v,t in pairs2)/len(pairs2)
    sv=statistics.pstdev(vs); st=statistics.pstdev(ts)
    corr=cov/(sv*st) if sv*st else 0
    print(f"flag=0x80: corr(val, byte17)={corr:.3f}")

# 检查 byte17 是否按 cat 聚集（若是group id，同cat同group）
print("\n=== byte17(现unk) 是否按 cat 聚集 (flag=0x80) ===")
cat_grp=defaultdict(set)
for x in d:
    if x['flag']==0x80: cat_grp[x['cat']].add(x['unk'])
for c in sorted(cat_grp):
    s=cat_grp[c]
    print(f"  cat={c:2d}: {len(s)} distinct byte17 = {sorted(s) if len(s)<=8 else str(len(s))+' vals'}")
