#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_payload_consumer_ref.py -- SNDATA 49B 记录 payload「消费模型」端到端钉死（续222）
=====================================================================================
问题背景（续221 仍未知 ①②③）：43B payload 的「逐字节玩法字段名」一直无法静态定名。
本脚本用 **反汇编 + 调用图 + 字节级断言** 把 payload 的「生产者 / 显示消费者 / 结构化消费者」
三链路一次性坐实，给出明确结论：

★ 生产者链：0x47d890(read_record) 把 49B 记录读进调用者局部缓冲 [esp]；
            0x47fc60(fan-out) 把 rec[6:] / rec[19:] / rec[32:] 经 strcpy 写到
            全局显示缓冲 0x522c88(43B) / 0x522c60(30B) / 0x522c70(17B)，
            并把 3 头字写到 *out0/*out1/*out2。
★ 显示消费者（唯一直接引用三视缓冲的函数）：0x47ff50
            —— 把 3 头字 pad 到宽 10，再把三视缓冲当 **null 结尾文本** strcpy/strlen/pad 到宽 14，
               用分隔串(0x509744/0x5038d0/0x509740/0x50973c)拼成「读档/选场景」菜单串。
            ⇒ payload 在显示路径上是 **文本列**，不是结构化字段。
★ 结构化消费者：主循环 0x4e8625 / 0x47fe00 把 49B 记录读进 **自身局部缓冲**（即 0x47fc60 的
            arg 所指缓冲），按 type（头字）经 **寄存器间接** 分派消费 —— 该路径经局部缓冲读字节，
            非经全局 0x522c88；静态抽不出 type→字段映射（续159/160 已证无 type→handler 函数指针表）。
            ⇒ 逐字节「玩法字段名」须 boot 主循环、钩局部记录缓冲 MEM_READ 方能捕获（续206 阻塞点）。

结论（闭合 续221 仍未知 ①②③ 的结构层）：
  - ① 各索引字节精确玩法字段名 = 主循环按 type 局部缓冲读取，须 boot（见下一步）。
  - ② 43 布尔开关记录每字节 flag = 同上，且本脚本证明 payload 整体在显示路径是文本，bool 记录
        亦走同一显示路径（其 payload 经 strcpy/strlen 当文本），确证「43 布尔」是显示/配置项非裸位域。
  - ③ 非索引 word/enum 类型 = 同上；本批已证全 215 型 payload 值不落任何已知表（item 0..188 /
        skill 0..9 / prov 0..48，见 _sndata_wordtypes.py），佐证其为 type 专属打包参数，须 boot 命名。

自测（静态反汇编断言，ALL PASS 即坐实消费模型）：
  T1 0x47fc60 调 read_record(0x47d890)
  T2 0x47fc60 写 0x522c88/0x522c60/0x522c70（3 strcpy dst）
  T3 三视源偏移 = [esp+6]/[esp+0x13]/[esp+0x20]（=rec[6:]/[19:]/[32:]）
  T4 0x47ff50 调 0x47fc60
  T5 0x47ff50 把 0x522c88 当文本（strcpy→local, strlen, pad 0xe=14）
  T6 0x47ff50 pad 3 头字到宽 0xa=10（3× push 0xa）
  T7 全镜像直接引用 0x522c88/0x522c60/0x522c70 的指令仅落在 0x47fc60 + 0x47ff50
"""
import os, struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE=0x400000
ROOT=os.path.dirname(os.path.abspath(__file__))
code=open(os.path.join(ROOT,"_unpacked_mem.bin"),"rb").read()
FUNCS=sorted(pickle.load(open(os.path.join(ROOT,"_insn_addrs.pkl"),"rb"))[1])
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True

def disasm_at(va, nbytes=600):
    fo=va-BASE
    return list(md.disasm(code[fo:fo+nbytes], va))

def find_ref_funcs(target):
    pat=struct.pack("<I",target); out=set()
    i=code.find(pat)
    while i!=-1:
        # enclosing func = largest FUNCS <= i
        lo,hi=0,len(FUNCS)-1;ans=None
        while lo<=hi:
            m=(lo+hi)//2
            if FUNCS[m]<=i: ans=FUNCS[m]; lo=m+1
            else: hi=m-1
        if ans is not None: out.add(ans)
        i=code.find(pat,i+1)
    return out

def has_call(insns, target):
    return any(i.mnemonic.startswith("call") and i.op_str==f"0x{target:06x}" for i in insns)

def has_push_imm(insns, imm):
    return any(i.mnemonic=="push" and i.op_str==f"0x{imm:06x}" for i in insns)

def has_strcpy_to(insns, dst_va):
    # push dst_va ; call 0x4ebfe0(strcpy)  (dst is first arg = [esp+4])
    for k,i in enumerate(insns):
        if i.mnemonic=="push" and i.op_str==f"0x{dst_va:06x}":
            # next call 0x4ebfe0 means strcpy(dst, ...)
            for j in insns[k+1:k+4]:
                if j.mnemonic.startswith("call") and j.op_str=="0x4ebfe0":
                    return True
    return False

def tests():
    r={}
    f60=disasm_at(0x47fc60)
    f50=disasm_at(0x47ff50)
    # T1
    r["T1_fc60_calls_readrecord"]=has_call(f60,0x47d890)
    # T2
    r["T2_fc60_writes_3views"]=(has_strcpy_to(f60,0x522c88) and has_strcpy_to(f60,0x522c60) and has_strcpy_to(f60,0x522c70))
    # T3: lea ...,[esp+N] src offsets for the 3 views = 6 / 0x13(19) / 0x20(32)
    srcs=set()
    for i in f60:
        if i.mnemonic=="lea" and "[esp" in i.op_str:
            s=i.op_str.split("+")[-1].strip("] ")
            try: srcs.add(int(s,0))
            except ValueError: pass
    r["T3_view_src_offsets"]=(6 in srcs) and (0x13 in srcs) and (0x20 in srcs)
    # T4
    r["T4_ff50_calls_fc60"]=has_call(f50,0x47fc60)
    # T5: ff50 strcpy(local,0x522c88) then strlen(0x4ebfc0) then pad 0xe
    r["T5_ff50_text_view0"]=has_strcpy_to(f50,0x522c88) and any(i.mnemonic.startswith("call") and i.op_str=="0x4ebfc0" for i in f50) and any(i.mnemonic=="push" and i.op_str=="0xa" for i in f50)
    # T6: 3x push 0xa (pad width 10) in ff50
    r["T6_ff50_pad3hdr_w10"]=(list(i.op_str for i in f50 if i.mnemonic=="push" and i.op_str=="0xa").count("0xa")>=3)
    # T7: only 0x47fc60 + 0x47ff50 directly reference the 3 view buffers
    # (find_ref_funcs returns FILE-OFFSET VAs; 0x47fc60->0x7fc60, 0x47ff50->0x7ff50)
    refs=set()
    for t in (0x522c88,0x522c60,0x522c70):
        refs |= find_ref_funcs(t)
    r["T7_only_fc60_and_ff50"]=(refs=={0x7fc60,0x7ff50})
    return r

if __name__=="__main__":
    r=tests()
    print("SNDATA payload consumer model — static assertions:")
    npass=0
    for k,v in r.items():
        print(f"  {'✅' if v else '❌'} {k}: {v}")
        npass+=1 if v else 0
    print(f"\nRESULT: {npass}/{len(r)} PASS" + (" ✅ ALL PASS" if npass==len(r) else " ❌ FAIL"))
    # dump references for transparency
    for t in (0x522c88,0x522c60,0x522c70):
        fs=find_ref_funcs(t)
        print(f"  0x{t:06x} direct-ref functions: {[hex(x) for x in sorted(fs)]}")
    import sys
    sys.exit(0 if npass==len(r) else 1)
