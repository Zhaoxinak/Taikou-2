#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_s7_statemachine_ref.py  --  续192 交付物
=============================================
判定 S7 `+0x08` 状态机（跳表 0x49c1cc / 派发器 0x49c064）是否 S7 专属。
结论：**否** —— 它是 续155 预警的「共享/通用 16B-entry setter·派发库」，与 S7 专属的 `+0x0f` setter 形成鲜明对照。

自检项（全部 PASS 才算闭合）：
  T1  跳表 0x49c1cc 8 项目标 ≥7/8 `read byte[ecx+5]`（即 +0x05 字节）；例外 [4] 操作派发器预载的 `word[+0x08]`(al 已由 `mov ax,[ecx+8]` 载入) => 状态机以 +0x05 为主键
  T2  派发器 0x49c064 E8-call-site == 0 且 raw-literal 引用 == 0（完全孤立 => 共享库，非 S7 专属）
  T3  +0x08 setter 0x49bfba E8-call-site == 0 且 raw-literal == 0（同 T2）
  T4  跳表 0x49c1cc 仅被派发器自身引用（raw-literal==1 @0x49c085，位于 0x49c064 体内）=> 状态机整体孤立

运行：在 F:/Games/Taikou 2/scripts/ 下 `python sndata_s7_statemachine_ref.py`
"""
import struct, sys
BASE=0x400000
BIN="F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
DISP=0x49c064
JTAB=0x49c1cc
SET08=0x49bfba
SET0A=0x49bfca
SET0B=0x49bfda

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

def raw_literals(b,addr):
    lit=struct.pack("<I",addr);res=[];p=0;n=len(b)
    while True:
        i=b.find(lit,p)
        if i<0: break
        res.append(i+BASE); p=i+1
    return res

def disasm_at(b,va,nbytes=24):
    from capstone import Cs,CS_ARCH_X86,CS_MODE_32
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=False
    off=va-BASE
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(b[off:off+nbytes],va)]

def main():
    b=load();fails=[]
    # T1: 跳表 8 项全读 byte[ecx+5]
    jt=[struct.unpack_from("<I",b,(JTAB-BASE)+i*4)[0] for i in range(8)]
    read05=0
    for addr in jt:
        d=disasm_at(b,addr,24)
        txt=" | ".join(f"{m} {o}" for (_,m,o) in d)
        if "ecx + 5" in txt: read05+=1
    ok_t1 = (read05>=7)
    # T2: 派发器孤立
    e8_disp=find_e8_calls(b,DISP); raw_disp=raw_literals(b,DISP)
    raw_disp=[x for x in raw_disp if not (DISP<=x<DISP+0x200)]
    ok_t2 = (len(e8_disp)==0 and len(raw_disp)==0)
    # T3: +0x08 setter 孤立
    e8_s08=find_e8_calls(b,SET08); raw_s08=raw_literals(b,SET08)
    raw_s08=[x for x in raw_s08 if not (SET08<=x<SET08+0x200)]
    ok_t3 = (len(e8_s08)==0 and len(raw_s08)==0)
    # T4: 跳表仅被派发器引用
    raw_jt=raw_literals(b,JTAB)
    raw_jt=[x for x in raw_jt if not (JTAB<=x<JTAB+0x40)]
    ok_t4 = (len(raw_jt)==1 and raw_jt[0]==0x49c085)

    print("="*70)
    print("S7 +0x08 状态机归属判定（续192）")
    print("="*70)
    print(f"\n[跳表 0x{JTAB:x}] 8 项目标全部 read byte[ecx+5]? {read05}/8")
    for i,addr in enumerate(jt):
        d=disasm_at(b,addr,24)
        txt=" | ".join(f"{m} {o}" for (_,m,o) in d)
        print(f"  [{i}] 0x{addr:x}: {txt}")
    print(f"\n[派发器 0x{DISP:x}] E8={len(e8_disp)} raw={len(raw_disp)} -> 孤立={ok_t2}")
    print(f"[+0x08 setter 0x{SET08:x}] E8={len(e8_s08)} raw={len(raw_s08)} -> 孤立={ok_t3}")
    print(f"[跳表 0x{JTAB:x}] raw 引用(非本表内)={len(raw_jt)} {[hex(x) for x in raw_jt]} -> 仅派发器={ok_t4}")

    print("\n"+"-"*70)
    print("自检结果:")
    print(f"  T1 跳表 ≥7/8 读 byte[+0x05]([4]用+0x08):{'PASS' if ok_t1 else 'FAIL'} ({read05}/8)")
    print(f"  T2 派发器 0x49c064 完全孤立(非S7):  {'PASS' if ok_t2 else 'FAIL'}")
    print(f"  T3 +0x08 setter 0x49bfba 完全孤立:  {'PASS' if ok_t3 else 'FAIL'}")
    print(f"  T4 跳表仅被派发器自身引用:         {'PASS' if ok_t4 else 'FAIL'}")
    all_ok = ok_t1 and ok_t2 and ok_t3 and ok_t4
    print("-"*70)
    print("总判定:", "ALL PASS ✅ => +0x08 状态机=共享库，非 S7 专属" if all_ok else "HAS FAIL ❌")
    return 0 if all_ok else 1

if __name__=="__main__":
    sys.exit(main())
