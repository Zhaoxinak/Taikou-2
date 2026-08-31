# -*- coding: utf-8 -*-
"""sndata_entity_decoder_ref.py — 续194 破解 P0：SNDATA 49B payload 的「实体初始化解码器」(0x47f7b0)

承接续189「type=0x01 = 43 独立布尔开关，须命名」+ 续193「emu 骨架落地」。
本续在**静态解码 + emu 验证**两层把「43 字节 payload → 游戏字段」的黑箱彻底坐死：

🔑 核心结论（续194）：
  所谓「43 独立布尔开关」是**统计指纹误导**——真相是**一条顺序流解码器** `0x47f7b0`：
    ① 设流游标 `0x522c98 = 0x4eb5c0(arg1*59)`（每条记录的 ~59B 工作缓冲）；
    ② 经 `read_byte(0x47fa40)` / `read_word(0x47fa60)`（游标全局 0x522c98 顺序推进）
       把流字节依次写入**固定游戏表**：
         - 前 7 字节 → 表 0x521aa8[0..6]
         - 次 7 字节 → 表 0x520660[0..6]
         - 余下字节 → **实体池 0x519868 + edi×0x2f(47B)** 的具体字段偏移
           （+2/+8/+a 三 word；+b..+18 十四 byte；+1a/+1d/+26/+2a/+2c 各 word；
            +1b/+1f/+20..+25/+28/+29/+2e 各 byte）。
    ③ 写目标与已知实体字段**精确吻合**：+0x24=国索引 / +0x25=在城索引 /
        +0x26=功勲(word,cap60000) / +0x2a=主君索引(word,0xffff=浪人) /
        +0xf..+0x11=技能三字节 / +0xa..+0xe 覆盖五维区——即 SNDATA 记录是
        **武将初期数据**，43 字节 payload 是其紧凑初始化字段流。
  ⇒ P0「49B 字段命名」从黑箱推进到「流偏移→实体偏移 的精确映射表」，字段语义由
    实体偏移（已有 MEMORY/SNDATA_SPEC）赋予，不再依赖运行期 dump 或猜。

仍未知（续194 下一步）：① 此解码器对应哪类 record type（须对照 833 条记录按 type 归类其
  流布局，确认是否覆盖 type=0x01 等）；② 表 0x521aa8/0x520660 的 7 字节语义（疑似名/缩略/
  头像索引或剧本专用表）；③ 其它分发簇是否有各自的解码器（续160 的 cluster1/else 簇）。

用法：python sndata_entity_decoder_ref.py   （脚本目录 scripts/ 下运行）
"""
import os, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ESP

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

ENTITY_BASE = 0x519868
ENTITY_STRIDE = 0x2f          # 47 字节（"47B" = 十进制47 = 0x2f）
DEC = 0x47f7b0                # 解码器入口
READ_BYTE = 0x47fa40
READ_WORD = 0x47fa60
ALLOC_STUB = 0x4eb5c0         # 流缓冲分配器（emu 中 stub）
ALLOC_RET  = 0x4eb5e0         # 其 ret 4 地址（stub 跳此返回）

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def parse_decoder():
    """从反汇编提取读取序列（call-site 级），并标注两个 7 次循环（tblA/tblB）。
    返回：list of dict {rtype, kind, off, is_loop, loop_base}
      kind: 'entity'/'tblA'/'tblB'/'local'；off: 相对偏移；
      is_loop: 该读取处于 dec/jne 循环中（展开为 7 次）；loop_base: 循环基址(不含E)。
    """
    ins = dis(DEC, 0x2c0)
    sites = []
    pending = None
    for i in ins:
        s = i.mnemonic + " " + i.op_str
        if i.mnemonic == "lea" and i.op_str.startswith("e") and "[" in i.op_str:
            try:
                disp = int(i.op_str.split("0x")[-1].rstrip("]"), 16)
            except ValueError:
                pending = None
                continue
            if 0x519860 <= disp <= 0x5199ff:
                pending = ("entity", disp - ENTITY_BASE)
            elif 0x521000 <= disp <= 0x521bff:
                pending = ("tblA", disp - 0x521aa8)
            elif 0x520600 <= disp <= 0x5207ff:
                pending = ("tblB", disp - 0x520660)
            else:
                pending = None
            continue
        if i.mnemonic == "call" and (f"0x{READ_BYTE:06x}" in s or f"0x{READ_WORD:06x}" in s):
            rtype = "byte" if f"0x{READ_BYTE:06x}" in s else "word"
            kind, off = pending if pending else ("local", None)
            sites.append(dict(rtype=rtype, kind=kind, off=off, is_loop=False, loop_base=None))
            pending = None
        if i.mnemonic in ("ret", "retn"):
            break
    # 标注循环：读取调用后紧跟 inc; dec <reg>; jne(回跳) 者是 7 次循环体
    for idx, st in enumerate(sites):
        nxt = ins  # 需要从原始 ins 找下一指令；改为基于地址查找
    # 简化：前两条（tblA/tblB）即从反汇编确认的 ebp=7/ebx=7 循环
    # 用更稳健的方式：检测 call 之后 3 条内有无 dec ebp/ebx + jne
    addr2idx = {}
    for ii, i in enumerate(ins):
        addr2idx[i.address] = ii
    for idx, st in enumerate(sites):
        # 找到该 call 在 ins 中的指令
        call_addr = None
        for ii, i in enumerate(ins):
            if i.mnemonic == "call" and (f"0x{READ_BYTE:06x}" in (i.mnemonic+" "+i.op_str)
                                         or f"0x{READ_WORD:06x}" in (i.mnemonic+" "+i.op_str)):
                pass
        break
    # 直接按已知：sites[0]=tblA 循环(0x47f7f9,ebp=7)，sites[1]=tblB 循环(0x47f811,ebx=7)
    if sites and sites[0]["kind"] == "tblA":
        sites[0]["is_loop"] = True; sites[0]["loop_base"] = 0x521aa8
    if len(sites) > 1 and sites[1]["kind"] == "tblB":
        sites[1]["is_loop"] = True; sites[1]["loop_base"] = 0x520660
    return sites


def expand_seq(sites, E):
    """展开循环为 7 次，返回与执行顺序一致的 49 项 (rtype, abs_addr)。"""
    out = []
    for st in sites:
        if st["is_loop"]:
            for k in range(7):
                base = st["loop_base"] + E * 7 + k
                out.append((st["rtype"], base))
        else:
            if st["kind"] == "entity":
                out.append((st["rtype"], ENTITY_BASE + E * ENTITY_STRIDE + st["off"]))
            elif st["kind"] == "tblA":
                out.append((st["rtype"], 0x521aa8 + E * 7 + st["off"]))
            elif st["kind"] == "tblB":
                out.append((st["rtype"], 0x520660 + E * 7 + st["off"]))
            else:  # local
                out.append((st["rtype"], None))
    return out


def _selftest():
    sites = parse_decoder()
    ncall = len(sites)
    nbyte = sum(1 for s in sites if s["rtype"] == "byte")
    nword = sum(1 for s in sites if s["rtype"] == "word")
    expanded = expand_seq(sites, 7)
    print(f"[*] 解码器 call-site 数: {ncall} (27 byte + 10 word = 37)；展开循环后执行读取: {len(expanded)}")

    ok = []
    def chk(name, cond, extra=""):
        ok.append(bool(cond))
        print(f"  [{'OK' if cond else 'FAIL'}] {name}{(' — ' + extra) if extra else ''}")

    print("--- T1 解码器 call-site 序列规模正确（37 / 27 byte / 10 word）---")
    chk("call-site 总数 == 37", ncall == 37, f"{ncall}")
    chk("read_byte == 27", nbyte == 27, f"{nbyte}")
    chk("read_word == 10", nword == 10, f"{nword}")
    chk("展开后执行读取 == 49（2 循环×7 + 35）", len(expanded) == 49, f"{len(expanded)}")

    # 解析出的实体偏移集合
    ent_offs = sorted({s["off"] for s in sites if s["kind"] == "entity"})
    print(f"--- T2 实体字段偏移覆盖（{len(ent_offs)} 个）：{ent_offs} ---")
    chk("国索引 +0x24 出现", 0x24 in ent_offs)
    chk("在城索引 +0x25 出现", 0x25 in ent_offs)
    chk("功勲 +0x26 出现", 0x26 in ent_offs)
    chk("主君索引 +0x2a 出现", 0x2a in ent_offs)
    chk("技能区 +0xf 出现", 0xf in ent_offs)
    chk("表A 0x521aa8 写入出现", any(s["kind"] == "tblA" for s in sites))
    chk("表B 0x520660 写入出现", any(s["kind"] == "tblB" for s in sites))

    # ---- EMU 验证 ----
    print("--- T3 emu 解码器 + 字节落点验证（stub 0x4eb5c0，执行序驱动）---")
    sys.path.insert(0, HERE)
    from emu_harness import Emu
    from unicorn.x86_const import UC_X86_REG_ECX
    e = Emu()
    SBUF = e.alloc(0x60)
    stream = bytes((k % 256) for k in range(0x59))
    e.write(SBUF, stream)
    E = 7
    ENT = ENTITY_BASE + E * ENTITY_STRIDE

    reader_log = []
    stub_hits = [0]
    def stub_hook(mu, address, size, ud):
        if address == ALLOC_STUB:
            stub_hits[0] += 1
            mu.reg_write(UC_X86_REG_EAX, SBUF)
            mu.reg_write(UC_X86_REG_EIP, ALLOC_RET)
    def reader_hook(mu, address, size, ud):
        if address in (READ_BYTE, READ_WORD):
            cur = int.from_bytes(mu.mem_read(0x522c98, 4), "little")
            reader_log.append((address, cur))
    h1 = e.mu.hook_add(UC_HOOK_CODE, stub_hook)
    h2 = e.mu.hook_add(UC_HOOK_CODE, reader_hook)
    try:
        e.call(DEC, [E, 0], max_steps=0x200000)
        ran = True
    except Exception as ex:
        ran = False
        print("    emu 异常:", ex)
    e.mu.hook_del(h1); e.mu.hook_del(h2)
    chk("emu 解码器完整跑完（无崩溃）", ran)
    print(f"    [debug] stub 命中 {stub_hits[0]} 次；reader 捕获 {len(reader_log)} 次；首次游标 0x{reader_log[0][1]:06x}")

    # 用执行序（reader_log 游标）逐一验证 expanded 序列的落点
    chk("reader 捕获 == 49（与展开序列一致）", len(reader_log) == 49, f"{len(reader_log)}")
    chk("首次读取游标 == SBUF", reader_log[0][1] == SBUF, f"0x{reader_log[0][1]:06x}")
    # 游标顺序递进（每步 +1 或 +2）
    prog = all((reader_log[i+1][1] - reader_log[i][1]) in (1, 2) for i in range(len(reader_log)-1))
    chk("游标严格顺序递进（+1/+2）", prog)

    mism = []
    for (rtype, abs_addr), (raddr, cur) in zip(expanded, reader_log):
        if abs_addr is None:
            continue
        soff = cur - SBUF
        sz = 2 if rtype == "word" else 1
        exp_v = int.from_bytes(stream[soff: soff + sz], "little")
        got_v = int.from_bytes(e.mu.mem_read(abs_addr, sz), "little")
        if got_v != exp_v:
            mism.append((hex(abs_addr), soff, exp_v, got_v))
    chk("全部 49 次读取落点吻合（无 mismatch）", len(mism) == 0,
        f"{len(mism)} 处不符: {mism[:5]}")
    if mism:
        for m in mism[:8]:
            print("      mismatch %s <- stream[0x%02x] expect=%d got=%d" % m)

    # 表A[0]/表B[0] 抽样
    ta0 = e.mu.mem_read(0x521aa8 + E * 7, 1)[0]
    tb0 = e.mu.mem_read(0x520660 + E * 7, 1)[0]
    chk("表A[E*7+0] == stream[0]", ta0 == stream[0], f"0x{ta0:02x} vs 0x{stream[0]:02x}")
    chk("表B[E*7+0] == stream[7]", tb0 == stream[7], f"0x{tb0:02x} vs 0x{stream[7]:02x}")
    # 实体关键字段抽样（国/城/功勲/主君）
    ent_got = lambda o, s: int.from_bytes(e.mu.mem_read(ENT + o, s), "little")
    # 找 expanded 中 entity+0x24 的 soff：从 reader_log 中对应项
    for (rtype, abs_addr), (raddr, cur) in zip(expanded, reader_log):
        if abs_addr == ENT + 0x24:
            soff24 = cur - SBUF
            chk("实体+0x24(国) == stream[对应]", ent_got(0x24, 1) == stream[soff24],
                f"0x{ent_got(0x24,1):02x} vs stream[0x{soff24:02x}]=0x{stream[soff24]:02x}")
        if abs_addr == ENT + 0x2a:
            soff2a = cur - SBUF
            chk("实体+0x2a(主君) == stream[对应]", ent_got(0x2a, 2) == int.from_bytes(stream[soff2a:soff2a+2], "little"),
                f"0x{ent_got(0x2a,2):04x} vs stream[0x{soff2a:02x}]")

    n = sum(ok)
    print(f"\nRESULT: {n}/{len(ok)} checks passed")
    return n == len(ok)


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
