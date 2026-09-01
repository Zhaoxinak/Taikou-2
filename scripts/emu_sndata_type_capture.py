#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
emu_sndata_type_capture.py  v3 (续195 延伸)
=====================================================================================
用 Unicorn 真实跑主循环 0x4e8604，捕获 SNDATA 记录的「type→簇 handler→资源表」路由与
消费者落点。修正 续194 末发现的 STUB_READ2 参数错位（见下），从而完整主循环可跑通——
原以为的「堆分配器深坑」实为栈缓冲 + 参数槽写反造成的假象。

回调 ABI（来自 _lindis / 本脚本 disasm 校验）：
  [0x4fb0a8] lseek(handle,off,whence)  3-arg stdcall ret 12  → esp+=16
  [0x4fb0a0] read(handle,dst,cnt)      3-arg stdcall ret 12  → esp+=16
  [0x4fb09c] flush/close(handle)       1-arg stdcall ret 4   → esp+=8
  [0x4fb080] stream_fill(buf, cnt=0x100) 2-arg stdcall ret 8 → 入口 [esp+4]=cnt, [esp+8]=buf, esp+=12
              （0x4ef690: push buf; push 0x100; call [0x4fb080]，返回后读 buf[0] 做字符变换）
  0x47d720 文件init  2-arg stdcall ret 8  → esp+=12，返回 eax=1
  0x47fe00 游标迭代  (0, [0x509684])→idx，调用方 add esp,8 → 桩 esp+=4，返回的 idx 进 eax

主循环 0x4e8604 结构（disasm 印证）：
  call 0x480240(→0x47fe00 取 idx；esi=idx；si==-1 退出)
  call 0x47fc60(idx,&w1,&w2,&w3) 扇出；w1/w2/w3 全 0 → 调 0x47b160 跳下一轮
  call 0x47b390(0x50d834) 匹配器 gate1 (test eax @0x4e8661, je 0x4e8604)
  call 0x47fb80(idx)     谓词 gate2 (test eax @0x4e866e, je 0x4e8604)
  mov ax,[0x5205fe] 三路 switch：
     mode==0 → 簇0 (0x492e20,0x493140,0x48cc20,0x48d350,0x48e690,0x4a0b20)
     mode==1 → 簇1 (0x492ed0,0x4931f0,0x4ac9c0,0x4ae380,0x4a0b70)
     else    → 直落 else 簇 (0x491e70,0x4873b0,0x491f90,0x492050,0x499050)
     else 簇在全部 mode 均执行（mode0/1 先跑各自簇再 fall-through；mode≥2 直落）
  派发纯由 mode 决定（与 type 无关）；type 特异性由「簇内 handler 内部按 id/sub/type 分支」决定
  ⇒ 找「type→资源表」须真跑各 handler 体，抓其 MEM_READ 落点。

本脚本两阶段：
  阶段1 (--stage 1)：簇 handler + 前置 setup + 0x47b160 全部短路（仅记录被调用地址与 ecx），
      确认完整主循环可端到端跑通（推翻「堆深坑」），产出 sndata_type_to_cluster.json
      （每 type → 每 mode → 被调用的 handler 有序列表）。
  阶段2 (--stage 2)：前置 setup 真跑，簇 handler 真跑并用 MEM_READ 钩子记录落在已知
      数据表（实体/城/国/国情/名称/S7/S15/扇出全局）的读数，计算 benum 索引区间，
      产出 sndata_handler_footprints.json（每 type×handler → 触及表与索引区间）。
"""
import os, struct, json, argparse
from collections import defaultdict
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN  = os.path.join(ROOT, "scripts/_unpacked_mem.bin")
SND_PATH = os.path.join(ROOT, "Taikou2 Original/SNDATA1.TR2")
BASE = 0x400000

# ---- 已知数据表范围（VA）----
TABLES = [
    ("entity",   0x519868, 0x519868 + 47*370),     # 实体 47×370
    ("castle",   0x51eb88, 0x51eb88 + 31*200),     # 城 31×200
    ("country",  0x519548, 0x519548 + 5*49),       # 国 5×49
    ("copol",    0x5179b8, 0x5179b8 + 14*49),      # 国政治 14×49
    ("name",     0x506ca8, 0x506ca8 + 0x4000),     # 名称总表（保守上界）
    ("s7",       0x516a28, 0x516a28 + 16*200),     # S7 每城 16×200
    ("s15",      0x5203c0, 0x5203c0 + 0x40),       # S15 事件旗
    ("fanout",   0x522c60, 0x522c88 + 43),         # 扇出三全局
    ("matcher",  0x5250d4, 0x5250e8 + 0x10),       # 匹配器全局
    ("thisobj",  0x523748, 0x526c50 + 0x10),       # this 对象区
]
STRIDE = {"entity":47, "castle":31, "country":5, "copol":14, "s7":16}

# ---- 簇 handler 集合（addr, ecx, nargs 中由调用方 push 的常量 arg0；None=无）----
PRE = [(0x4edfa0,0x526c50,None),(0x47adc0,0x526c50,None),(0x4ee340,0x5239f0,None),
       (0x4ee340,0x523ae0,None),(0x4ee340,0x523748,None),(0x4b0ad0,0x523748,None)]
CLUSTER0 = [(0x492e20,0x523748,None),(0x493140,0x523748,None),(0x48cc20,0x523748,0),
            (0x48d350,0x523748,None),(0x48e690,0x523748,None),(0x4a0b20,0x523748,0)]
CLUSTER1 = [(0x492ed0,0x523748,None),(0x4931f0,0x523748,None),(0x4ac9c0,0x523748,None),
            (0x4ae380,0x523748,1),(0x4a0b70,0x523748,0)]
ELSE = [(0x491e70,0x524740,None),(0x4873b0,0x524740,None),(0x491f90,0x524740,None),
        (0x492050,0x524740,None),(0x499050,0x524740,None)]
CLUSTER_ADDRS = {a for a,_,_ in CLUSTER0+CLUSTER1+ELSE}
PRE_ADDRS = {a for a,_,_ in PRE}
# 每条记录处理末尾的清理调用（0x47ad60/0x4edf70）：在未初始化状态下会无限循环/卡死，
# 且不是「按 type 定位资源表」的消费者，两个阶段都短路。
SHORT_ADDRS = PRE_ADDRS | {0x47ad60, 0x4edf70}
ALL_HOOK_ADDRS = CLUSTER_ADDRS | PRE_ADDRS | {0x47b160} | SHORT_ADDRS

def r32(mu, a): return struct.unpack_from("<I", mu.mem_read(a,4),0)[0]
def w32(mu, a, v): mu.mem_write(a, struct.pack("<I", v & 0xffffffff))

class Emu:
    def __init__(self):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        with open(BIN,"rb") as f: self.code = f.read()
        assert len(self.code) >= 0x200000
        self.mu.mem_map(BASE, len(self.code))
        self.mu.mem_write(BASE, self.code)
        self.STACK_TOP = 0x600000
        self.mu.mem_map(self.STACK_TOP, 0x40000)
        self.STOP = 0x700000
        self.mu.mem_map(self.STOP, 0x1000)
        self.mu.mem_write(self.STOP, b"\x90\x90\x90\x90")
        # 额外 scratch（吸收堆式读写 / 未映射小对象）
        self.mu.mem_map(0x800000, 0x200000)        # 0x800000..0xA00000
        self.mu.mem_map(0xC00000, 0x1000)          # 桩页 0xC00000..0xC01000
        self.mu.mem_write(0xC00000, b"\xc3"*0x1000)
        self.last=[0]
        self.mu.hook_add(UC_HOOK_CODE, lambda mu,a,s,u: self.last.__setitem__(0,a))

def type_of(idx, SND):
    rec = SND[16+idx*49: 16+idx*49+2]
    return struct.unpack_from("<H", rec, 0)[0] & 0xff

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=0, help="1=路由 2=资源 0=两者")
    args = ap.parse_args()
    SND = open(SND_PATH,"rb").read()
    assert len(SND) >= 16+833*49, f"SNDATA 长度异常 {len(SND)}"
    N = 833
    e = Emu()
    # 把 SND 文件内容放到一个映射区，供 read/lseek 桩喂
    FILE_BASE = 0xA00000
    e.mu.mem_map(FILE_BASE, 0x10000)
    e.mu.mem_write(FILE_BASE, SND)
    STUB_LSEEK, STUB_READ, STUB_FLUSH = 0xC00000,0xC00010,0xC00020
    # 通用回调桩：仅 ret（按 cdecl 约定，调用方自行清栈），用于喂未初始化的 0x4fb000 回调表槽位，
    # 避免「call [未初始化槽]」→ 跳飞到数据区。仅 lseek/read/flush 用真实喂数据桩。
    STUB_CB_GENERIC = 0xC00030
    e.mu.mem_write(STUB_CB_GENERIC, b"\xc3")   # ret
    # 先把整个 0x4fb000..0x4fb200 回调表填成通用 ret，再覆盖真实喂数据桩
    for off in range(0x4fb000, 0x4fb200, 4):
        e.mu.mem_write(off, struct.pack("<I", STUB_CB_GENERIC))
    e.mu.mem_write(0x4fb0a8, struct.pack("<I",STUB_LSEEK))
    e.mu.mem_write(0x4fb0a0, struct.pack("<I",STUB_READ))
    e.mu.mem_write(0x4fb09c, struct.pack("<I",STUB_FLUSH))

    # 所有需要读寄存器的「手交地址」集中在此，避免在每条指令上调用 mu.reg_read（性能杀手）。
    STUB_ADDRS = {STUB_LSEEK, STUB_READ, STUB_FLUSH, 0x47d720, 0x47fe00,
                  0x47b160, 0x47b390, 0x47fb80, 0x47fc60}

    pos=[0]; strpos=[0]
    q=[0]; qidx=[0]
    cur_idx=[0]
    # 状态（按阶段切换）
    stage=[1]
    invoked=[]                      # 路由：本次循环被调用的 (idx, mode, addr, ecx)
    current_handler=[None]         # 资源：当前正在跑的 handler
    fp=defaultdict(lambda: defaultdict(lambda: defaultdict(set)))  # fp[type][handler_name][table]=set(addrs)
    cur_type=[0]
    last_target=[0]
    cursor_done=[False]

    def on_code(mu, address, size, ud):
        last_target[0]=address
        # 常见路径（绝大部分指令）不做任何 reg_read，仅做两次集合判定后返回，保证原生速度。
        if address in STUB_ADDRS:
            sp = mu.reg_read(UC_X86_REG_ESP)
            if address == STUB_LSEEK:
                off = r32(mu, sp+8); pos[0]=off
                ret = r32(mu, sp)
                mu.reg_write(UC_X86_REG_EAX, off & 0xffffffff)
                mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == STUB_READ:
                dst = r32(mu, sp+8); cnt = r32(mu, sp+0xc)
                n = min(cnt, len(SND)-pos[0])
                if n<0: n=0
                mu.mem_write(dst, SND[pos[0]:pos[0]+n]); pos[0]+=n
                ret = r32(mu, sp)
                mu.reg_write(UC_X86_REG_EAX, n & 0xffffffff)
                mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == STUB_FLUSH:
                ret = r32(mu, sp)
                mu.reg_write(UC_X86_REG_EAX, 0)
                mu.reg_write(UC_X86_REG_ESP, sp+8); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x47d720:
                ret = r32(mu, sp)
                mu.reg_write(UC_X86_REG_EAX, 1)
                mu.reg_write(UC_X86_REG_ESP, sp+12); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x47fe00:   # 游标迭代：返回队列下一 idx，空则 -1
                ret = r32(mu, sp)
                v = q[qidx[0]] if qidx[0] < len(q) else -1
                qidx[0]+=1
                if v < 0: cursor_done[0]=True
                cur_idx[0] = v if v>=0 else cur_idx[0]
                mu.reg_write(UC_X86_REG_EAX, v & 0xffffffff)
                mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x47b160:   # 全零记录跳过的 debug log
                ret = r32(mu, sp)
                mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x47b390:   # 匹配器：强制开门（返回 1），跳过其内部查询逻辑
                ret = r32(mu, sp)
                mu.reg_write(UC_X86_REG_EAX, 1)
                mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x47fb80:   # 谓词：强制开门（返回 1）
                ret = r32(mu, sp)
                mu.reg_write(UC_X86_REG_EAX, 1)
                mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x47fc60:   # 扇出：仅阶段1短路（写非零 w1/w2/w3 使跳过检查通过）
                if stage[0] == 1:
                    ret = r32(mu, sp)
                    p1, p2, p3 = r32(mu, sp+8), r32(mu, sp+12), r32(mu, sp+16)
                    w32(mu, p1, 1); w32(mu, p2, 1); w32(mu, p3, 1)
                    mu.reg_write(UC_X86_REG_EAX, 1)
                    mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
                # 阶段2 不拦截，真跑
        elif address in ALL_HOOK_ADDRS:
            sp = mu.reg_read(UC_X86_REG_ESP)
            ecx = mu.reg_read(UC_X86_REG_ECX)
            if address in SHORT_ADDRS:
                # 前置 setup / 末尾清理：不是数据消费者，两个阶段都短路返回
                ret = r32(mu, sp)
                mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address in CLUSTER_ADDRS:
                if stage[0] == 1:
                    # 路由：记录并短路返回
                    invoked.append((cur_idx[0], mode_cur[0], address, ecx))
                    ret = r32(mu, sp)
                    mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
                else:
                    # 资源：标记 current_handler，真跑（不短路）
                    current_handler[0] = address
        # 其他指令正常执行

    def on_mem_read(mu, access, address, size, value, ud):
        if stage[0] != 2: return
        ch = current_handler[0]
        if ch is None: return
        key = ch if isinstance(ch, tuple) else ch
        # 仅记录已知表范围，去重
        for name,b0,b1 in TABLES:
            if b0 <= address < b1:
                fp[cur_type[0]][key][name].add(address)
                return
        # 其他读数忽略（控制体积）

    # 代码钩子挂全局（仅目标地址有逻辑，其余快速 fall-through）；MEM_READ 钩子只挂在
    # 已知数据表区间内（避免每次内存读都进 Python，且天然过滤无关访问）。
    e.mu.hook_add(UC_HOOK_CODE, on_code)
    for _name,_b0,_b1 in TABLES:
        e.mu.hook_add(UC_HOOK_MEM_READ, on_mem_read, begin=_b0, end=_b1)

    # patch 两处 gate je 为 nop（强制处理每条记录；匹配器/谓词仍真跑以设上下文）
    for je_addr in (0x4e8663, 0x4e8670):
        b0 = e.mu.mem_read(je_addr,1)[0]
        nop_len = 6 if b0==0x0f else 2
        e.mu.mem_write(je_addr, b"\x90"*nop_len)
    # 0x47b160 也在 ALL_HOOK 里短路；确保 0x4e8654 的 push 0x50d834;call 0x47b390 正常（匹配器真跑）

    mode_cur=[0]

    # 以 prologue 入口 0x4e8600 驱动单条记录：栈顶放 STOP 返回地址，函数末尾 ret 到 STOP 即停止。
    def run_one():
        e.mu.reg_write(UC_X86_REG_ESP, 0x638000)
        e.mu.mem_write(0x638000, struct.pack("<I", e.STOP))
        e.mu.reg_write(UC_X86_REG_EIP, 0x4e8600)
        e.mu.emu_start(0x4e8600, e.STOP+1, count=0x400000)

    # ---------- 阶段1：路由 ----------
    if args.stage in (0,1):
        stage[0]=1
        print("=== 阶段1：路由捕获（逐条驱动 0x4e8600，簇 handler 短路）===")
        routing = {}   # type -> mode -> [handlers in order]
        for mode in (0,1,2):
            mode_cur[0]=mode
            q=list(range(N)); qidx[0]=0; cursor_done[0]=False
            e.mu.mem_write(0x5205fe, struct.pack("<H", mode))
            e.mu.mem_write(0x522c60, b"\x00"*0x60); e.mu.mem_write(0x522c88, b"\x00"*0x40)
            while not cursor_done[0] and qidx[0] <= N:
                try:
                    run_one()
                except Exception as ex:
                    print(f"  ** 模式 {mode} 记录#{qidx[0]} 崩溃 last_target=0x{last_target[0]:06x}: {ex}")
                    break
                if cursor_done[0]: break
            # 聚合
            seen=defaultdict(list)
            for (idxv,m,addr,ecx) in invoked:
                if m!=mode: continue
                seen[type_of(idxv,SND)].append("0x%06x"%addr)
            invoked.clear()
            for t,addrs in seen.items():
                routing.setdefault(t, {})[str(mode)] = list(dict.fromkeys(addrs))
            print(f"  模式 {mode}: 覆盖 type 数={len(seen)}, 处理记录={qidx[0]}")
        out1 = {"routing": {f"0x{t:02x}": routing[t] for t in sorted(routing)}}
        with open(os.path.join(ROOT,"scripts/sndata_type_to_cluster.json"),"w",encoding="utf-8") as f:
            json.dump(out1, f, ensure_ascii=False, indent=1)
        print(f"落盘 scripts/sndata_type_to_cluster.json (types={len(routing)})")

    # ---------- 阶段2：资源 ----------
    if args.stage in (0,2):
        stage[0]=2
        print("\n=== 阶段2：资源捕获（簇 handler 真跑 + MEM_READ 钩子）===")
        # 每个 distinct type 取首个 idx 作为代表
        rep={}
        for idx in range(N):
            t=type_of(idx,SND)
            if t not in rep: rep[t]=idx
        print(f"  distinct types={len(rep)}，逐 type 跑 mode0/1 ...")
        processed=0; crashed=[]
        for t, idx in sorted(rep.items()):
            cur_type[0]=t
            for mode in (0,1):
                mode_cur[0]=mode
                q=[idx]; qidx[0]=0; cursor_done[0]=False
                current_handler[0]=None
                e.mu.mem_write(0x5205fe, struct.pack("<H", mode))
                e.mu.mem_write(0x522c60, b"\x00"*0x60); e.mu.mem_write(0x522c88, b"\x00"*0x40)
                try:
                    run_one()
                except Exception as ex:
                    crashed.append((t,mode,hex(e.last[0]),str(ex)[:60]))
                # 该 type 的足迹已写入 fp[t]
            processed+=1
            if processed % 20 == 0:
                print(f"  ... 已处理 {processed}/{len(rep)} types")
        # 汇总足迹
        summary={}
        for t in sorted(fp):
            summary[f"0x{t:02x}"]={}
            for key in fp[t]:
                kname = key if isinstance(key,int) else f"pre@{key[1]:06x}"
                tblinfo={}
                for name,addrs in fp[t][key].items():
                    al=sorted(addrs)
                    info={"count":len(al),"min":al[0],"max":al[-1]}
                    if name in STRIDE:
                        idxs=[(a-TABLES[[x[0] for x in TABLES].index(name)][1])//STRIDE[name] for a in al if (a-TABLES[[x[0] for x in TABLES].index(name)][1])%STRIDE[name]==0]
                        if idxs: info["idx_min"]=min(idxs); info["idx_max"]=max(idxs); info["idx_samples"]=sorted(set(idxs))[:12]
                    tblinfo[name]=info
                summary[f"0x{t:02x}"][kname]=tblinfo
        with open(os.path.join(ROOT,"scripts/sndata_handler_footprints.json"),"w",encoding="utf-8") as f:
            json.dump({"footprints":summary, "crashed":crashed}, f, ensure_ascii=False, indent=1)
        print(f"落盘 scripts/sndata_handler_footprints.json (types={len(summary)}, crashed={len(crashed)})")
        if crashed[:10]:
            print("  部分崩溃样本:", crashed[:10])

if __name__=="__main__":
    main()
