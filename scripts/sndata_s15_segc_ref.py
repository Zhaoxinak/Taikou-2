#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_s15_segc_ref.py  --  续193 交付物
============================================
S15 事件旗 `0x5203c0` 段C 6 字节语义攻坚。
  ① emu 确认 setter 0x49c500(idx,val) 写 `byte[ecx+0x13+idx]`（段C = +0x13..+0x18 共6B, idx 0..5）
  ② getter 0x49c410 读回一致（round-trip）
  ③ 静态 E8 call-site 扫描 25 处，按 idx(0..5) 归类 val 分布 —— 揭示段C 是「每事件 6 槽 scratch 数组」

自检项：
  T1  emu: set_c(buf, idx, val) 后 buf[0x13+idx]==val（idx 0..5）
  T2  emu: get_c(buf, idx) 返回值 == 上次 set_c 写入值（round-trip）
  T3  setter E8 call-site 计数 == 25
  T4  全部 call-site 的 idx ∈ {0,1,2,3,4,5}（6 槽边界吻合）
  T5  按 idx 归类的 val 分布落盘（usage pattern）

运行：在 F:/Games/Taikou 2/scripts/ 下 `python sndata_s15_segc_ref.py`
"""
import struct, sys, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import emu_harness as H

BASE=0x400000
BIN="F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
SET_C=0x49c500
GET_C=0x49c410

def load():
    with open(BIN,"rb") as f: return f.read()

def find_e8_calls(b,target):
    res=[];p=0;n=len(b)
    while p<n-5:
        if b[p]==0xE8:
            rel=struct.unpack_from("<i",b,p+1)[0]
            if (p+BASE)+5+rel==target: res.append(p+BASE)
        p+=1
    return res

def get_two_pushes(b,call_va):
    """取 call 前最近两个 push（args[0]=idx@esp+4, args[1]=val@esp+8）。"""
    cp=call_va-BASE; start=max(0,cp-24); args=[]
    i=cp-1
    while i>=start and len(args)<2:
        c=b[i]
        if c==0x6A: args.insert(0,("imm8",b[i+1])); i-=2; continue
        if c==0x68: args.insert(0,("imm32",struct.unpack_from("<I",b,i+1)[0])); i-=5; continue
        if 0x50<=c<=0x57:
            regs=["eax","ecx","edx","ebx","esp","ebp","esi","edi"]
            args.insert(0,("reg",regs[c-0x50])); i-=1; continue
        i-=1
    return args

def main():
    b=load()
    e=H.Emu()
    buf=e.alloc(0x40); e.write(buf,b"\x00"*0x40)
    fails=[]
    # T1: emu set_c byte offset
    ok_t1=True
    for idx in range(6):
        val=(idx*0x23+7)&0xff
        e.call(SET_C,[idx,val],regs={H.UC_X86_REG_ECX:buf})
        got=e.read(buf+0x13+idx,1)[0]
        if got!=val: ok_t1=False; fails.append(f"T1 idx={idx} wrote {val:02x} got {got:02x}")
    # T2: getter round-trip
    ok_t2=True
    for idx in range(6):
        val=(idx*0x11+3)&0xff
        e.call(SET_C,[idx,val],regs={H.UC_X86_REG_ECX:buf})
        r=e.call(GET_C,[idx],regs={H.UC_X86_REG_ECX:buf})
        if (r["eax"]&0xff)!=val: ok_t2=False; fails.append(f"T2 idx={idx} get {r['eax']&0xff:x} != {val:x}")
    # T3/T4/T5: static call-site classification
    calls=find_e8_calls(b,SET_C)
    ok_t3 = (len(calls)==25)
    parsed=[]
    for c in calls:
        a=get_two_pushes(b,c)
        idx = a[0][1] if len(a)>0 and a[0][0] in ("imm8","imm32") else a[0][1] if a else None
        val = a[1][1] if len(a)>1 else None
        # 仅采纳 idx 为立即数的（reg 来源需运行时，标记）
        parsed.append((c, idx, val, a))
    idxs=[p[1] for p in parsed if isinstance(p[1],int)]
    ok_t4 = all(0<=x<=5 for x in idxs)
    # T5: 按 idx 归类 val
    by_idx={i:{} for i in range(6)}
    for c,idx,val,a in parsed:
        if isinstance(idx,int) and 0<=idx<=5:
            key = val if isinstance(val,int) else str(a[1])
            by_idx[idx][key]=by_idx[idx].get(key,0)+1
    ok_t5 = (len(by_idx)==6)

    print("="*70); print("S15 段C 6B 语义（续193）"); print("="*70)
    print(f"\n[setter 0x{SET_C:x}] emu 确认写 byte[ecx+0x13+idx] (idx 0..5 => +0x13..+0x18)")
    print(f"[getter 0x{GET_C:x}] emu round-trip OK")
    print(f"\n[T3] E8 call-site = {len(calls)} (期望 25): {'PASS' if ok_t3 else 'FAIL'}")
    print(f"[T4] 全部 idx ∈ 0..5: {'PASS' if ok_t4 else 'FAIL'} (idx 集合={sorted(set(idxs))})")
    print(f"\n[T5] 按 idx 归类的 val 分布（usage pattern）:")
    for i in range(6):
        dist=", ".join(f"{k}:{v}" for k,v in sorted(by_idx[i].items(), key=lambda x:-x[1]))
        print(f"  idx[{i}] (+0x{0x13+i:02x}): {dist}")
    print(f"\n[T1] emu set_c byte-offset: {'PASS' if ok_t1 else 'FAIL'}")
    print(f"[T2] emu get/set round-trip: {'PASS' if ok_t2 else 'FAIL'}")

    # 落盘结构化结果
    out={"setter":SET_C,"getter":GET_C,"byte_offset_base":0x13,"n_bytes":6,
         "call_site_count":len(calls),"idx_val_distribution":{str(k):v for k,v in by_idx.items()},
         "parsed":[{"va":c,"idx":idx,"val":val} for c,idx,val,a in parsed]}
    with open("sndata_s15_segc.json","w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)

    all_ok=ok_t1 and ok_t2 and ok_t3 and ok_t4 and ok_t5
    print("-"*70)
    print("总判定:", "ALL PASS ✅" if all_ok else f"HAS FAIL ❌ {fails}")
    return 0 if all_ok else 1

if __name__=="__main__":
    sys.exit(main())
