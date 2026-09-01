# -*- coding: utf-8 -*-
"""
S15 段C —— 门控注入 + 函数边界修正 + 25B 运行时结构摊平（续220 参考实现 / 自测）

背景
----
续217 静态定位了 16 处 runtime-var 的 val 源；续218 证明孤立 emu 取不到可信值；
续219 注入实体上下文后 13/16 站产出具体 (idx,val)，余 3 站「正常返回但未到 set_c」：
    0x409300 / 0x40c4f3 / 0x40a6ec

本文件给出这 3 站的收口，并连带修正一个方法论级错误：

【根因】owner_fn 归属错误 —— 尾跳转相位函数被误并入前一相位
    原 heuristic「最大 call 目标 ≤ va」只收 `E8 call` 目标，漏了 `E9 jmp` 目标。
    本 EXE 的事件 handler 采用「两相惯用法」：
        dispatcher: call <phase1>;  test eax,eax; je skip;  jmp <phase2>
    phase2 只被 `E9 jmp` 到达 ⇒ 不在 call 目标集里 ⇒ 被并进 phase1 的函数体。
    于是 emu 从 phase1 入口起跑，在 phase1 的 ret 处正常返回，永远到不了 phase2 的 set_c。
    判别器 = 「ret + 0x90 填充」边界（注意：单纯的「指令边界对齐」检查抓不出来，
    因为线性反汇编跨过前一个函数后通常会重新同步，25/25 全 True）。

【三站收口】
  1) 0x409300  owner 0x409250（归属本来正确）——真门控 = segC[0] != 0
       语义: segC[0] = sat_sub8(segC[0], 1) = max(segC[0]-1, 0)   ← 倒计时递减
       (sat_sub8 = 0x4ebd10，新原语：if a<=b then 0 else a-b，字节比较)
  2) 0x40c4f3  owner 修正 0x40c350 → 0x40c4d0（bit2 将軍(足利)暗殺 事件 相位2）
       语义: segC[1] = 0x40c520() = 目标城索引（优先城 25，其次城 22，否则 0x40c5d0 兜底）
  3) 0x40a6ec  owner 修正 0x40a4f0 → 0x40a620（墨俣築城 相位2）
       语义: segC[3] = max(byte[0x513540] >> 1, 1)
       (全函数 emu 会撞进资源加载簇 0x4ec8c0 → `call [0x4fb07c]` 桩清栈不符导致跑飞；
        改用「最小自足切片起点」0x40a6c9 —— val 的 def-use 闭包起点，只读全局，确定可达)

【25B 运行时结构 @0x5203c0 全摊平】
    +0x00 (1B)      事件类型/模式码（直写 2 / 0xff）
    +0x01 (1B)      打包位域：低5位 setter 0x49c420 / 高3位 setter 0x49c440
    +0x02..+0x09    事件旗组A 64bit：测 0x49c390 / 置 0x49c460
    +0x0a..+0x11    事件旗组B 64bit：测 0x49c3d0 / 置 0x49c4b0
    +0x12 (1B)      未定名（访问器带内无命中）
    +0x13..+0x18    段C 参数槽 segC[0..5]：读 0x49c410 / 写 0x49c500
    ---------------- 合计 0x19 = 25 B 闭合

依赖：系统 python3.12（capstone + unicorn）。
"""
import sys, os, json, struct

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from emu_harness import Emu                                    # noqa: E402
from unicorn import UC_HOOK_CODE                               # noqa: E402
from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_ECX,  # noqa: E402
                               UC_X86_REG_EDI, UC_X86_REG_ESI,
                               UC_X86_REG_EIP)
from capstone import Cs, CS_ARCH_X86, CS_MODE_32                # noqa: E402
from _disasm_all import disasm_all                              # noqa: E402

BASE       = 0x400000
BUF        = 0x5203c0          # S15 段C 运行时结构基址
SEGC       = BUF + 0x13        # 6 个参数槽起点
SET_C      = 0x49c500
GET_C      = 0x49c410
G_513540   = 0x513540          # 0x40a6ec 的 val 源全局
IMG        = open(os.path.join(ROOT, "_unpacked_mem.bin"), "rb").read()

checks = []
def ck(name, cond, extra=""):
    checks.append((name, bool(cond), extra))
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}" + (f"   {extra}" if extra else ""))


# ───────────────────────── 函数边界修正器 ─────────────────────────
def fn_start(va, limit=0x1000):
    """真实函数起点 = 向后最近的「>=2 连续 0x90 填充」之后的首个非 nop 字节。"""
    off = va - BASE
    i = off
    while i > off - limit and i >= 2:
        if IMG[i - 1] == 0x90 and IMG[i - 2] == 0x90 and IMG[i] != 0x90:
            return BASE + i
        i -= 1
    return None


def xrefs(target):
    """返回 (E8 call 站点, E9 jmp 站点)。"""
    c, j = [], []
    for i in range(len(IMG) - 5):
        b = IMG[i]
        if b == 0xe8 or b == 0xe9:
            rel = struct.unpack_from("<i", IMG, i + 1)[0]
            if BASE + i + 5 + rel == target:
                (c if b == 0xe8 else j).append(BASE + i)
    return c, j


def insn_aligned(start, call_va):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    n = call_va - start + 8
    for ins in disasm_all(md, IMG[start - BASE:start - BASE + n], start):
        if ins.address == call_va:
            return True
        if ins.address > call_va:
            return False
    return False


# ───────────────────────── emu 取样 ─────────────────────────
ENT_BASE, ENT_STRIDE = 0x519868, 0x47B


def _emu(entity_idx=0, gates=None):
    e = Emu()
    # 未解析 Win32 导入的 ret 兜底页
    try:
        e.mu.mem_map(0x3000, 0x1000); e.mu.mem_write(0x3000, b"\xc3" * 0x1000)
    except Exception:
        pass
    # page0 = 真实实体副本（续219：空指针解引用 entity+0x25 不再崩）
    ent = ENT_BASE + entity_idx * ENT_STRIDE
    try:
        e.mu.mem_map(0, 0x1000)
        e.mu.mem_write(0, bytes(e.mu.mem_read(ent, ENT_STRIDE)) + b"\x00" * (0x1000 - ENT_STRIDE))
    except Exception:
        pass
    for a, v in (gates or {}).items():
        e.mu.mem_write(a, bytes([v & 0xff]))
    return e, ent


def capture(entry, target_call, entity_idx=0, gates=None, steps=0x200000,
            elide=None, force=None):
    """从 entry 起跑，钩 set_c；用栈上返回地址-5 反推 call 站点，命中 target 即停。
    elide={pc: dst} 调用跳过（净栈 0 且不动目标寄存器的无关 call 段直接跨过）。
    force={pc: (reg, val)} 在指定 PC 强置寄存器。
    返回 (全部命中列表[(call_va,idx,val)], 是否命中 target, 异常串, 最后 PC)。"""
    e, ent = _emu(entity_idx, gates)
    caps, last, hit = [], [0], [False]
    elide = elide or {}
    force = force or {}

    def hk(mu, ad, size, ud):
        last[0] = ad
        if ad in force:
            r, v = force[ad]; mu.reg_write(r, v)
        if ad in elide:
            mu.reg_write(UC_X86_REG_EIP, elide[ad]); return
        if ad == 0x4110e3:   mu.reg_write(UC_X86_REG_EDI, ent)
        elif ad == 0x4110e8: mu.reg_write(UC_X86_REG_ESI, ent)
        elif ad == 0x413db7: mu.reg_write(UC_X86_REG_ESI, ent)
        elif ad == SET_C:
            esp = mu.reg_read(UC_X86_REG_ESP)
            cs  = int.from_bytes(mu.mem_read(esp, 4), "little") - 5
            idx = int.from_bytes(mu.mem_read(esp + 4, 4), "little") & 0xff
            val = int.from_bytes(mu.mem_read(esp + 8, 1), "little")
            caps.append((cs, idx, val))
            if cs == target_call:
                hit[0] = True; mu.emu_stop()

    h = e.mu.hook_add(UC_HOOK_CODE, hk)
    err = None
    try:
        e.call(entry, [0, 0, 0, 0], regs={UC_X86_REG_ECX: BUF}, max_steps=steps)
    except Exception as ex:
        err = str(ex)[:60]
    e.mu.hook_del(h)
    return caps, hit[0], err, last[0]


def val_at(entry, target_call, gates=None, elide=None, force=None):
    caps, hit, err, _ = capture(entry, target_call, gates=gates, steps=0x40000,
                                elide=elide, force=force)
    for cs, idx, val in caps:
        if cs == target_call:
            return idx, val
    return None, None


def find(pat, lo, span=0x60):
    return IMG.find(pat, lo - BASE, lo - BASE + span) >= 0


# ═════════════════════════ T1 边界修正：25 站点重算 ═════════════════════════
print("\n[T1] 函数边界重算（nop 填充判别器） vs fullmap owner_fn")
fm = json.load(open(os.path.join(ROOT, "s15_segc_fullmap.json"), encoding="utf-8"))
EXPECT_FIX = {
    "0x40c4f3": ("0x40c350", 0x40c4d0),
    "0x40a6ec": ("0x40a4f0", 0x40a620),
    "0x40ad81": ("0x40ad10", 0x40ad60),
    "0x40a62b": ("0x40a4f0", 0x40a620),
    "0x40a79e": ("0x40a4f0", 0x40a620),
}
mism, aligned_all = {}, True
for e in fm["mapping"]:
    cv, ow = int(e["set_c_call"], 16), int(e["owner_fn"], 16)
    ns = fn_start(cv)
    if not insn_aligned(ow, cv):
        aligned_all = False
    if ns != ow:
        mism[e["set_c_call"]] = (e["owner_fn"], ns)
ck("25 站点中恰 5 处 owner 归属需修正", len(mism) == 5, f"实测 {len(mism)}")
for cv, (old, new) in EXPECT_FIX.items():
    got = mism.get(cv)
    ck(f"{cv}: owner {old} → {hex(new)}", got is not None and got[1] == new,
       f"实测 {got}")
ck("『指令边界对齐』检查对 25/25 全 True（证明它抓不出误判）", aligned_all)

# ═════════════════════════ T2 根因：尾跳转相位函数 ═════════════════════════
print("\n[T2] 根因验证：修正后的 owner 只被 E9 jmp 到达（相位2 尾调用）")
for new, old in ((0x40c4d0, 0x40c350), (0x40a620, 0x40a4f0), (0x40ad60, 0x40ad10)):
    c_new, j_new = xrefs(new)
    c_old, _     = xrefs(old)
    ck(f"0x{new:x} 无 E8 call / 有 E9 jmp；而 0x{old:x} 有 E8 call",
       len(c_new) == 0 and len(j_new) >= 1 and len(c_old) >= 1,
       f"new call={[hex(x) for x in c_new]} jmp={[hex(x) for x in j_new]} old call={[hex(x) for x in c_old]}")

print("\n[T2b] 两相 handler 惯用法：dispatcher = call phase1 → jmp phase2")
for disp_call, ph1, disp_jmp, ph2 in ((0x41a48e, 0x40c350, 0x41a497, 0x40c4d0),
                                      (0x40a2e0, 0x40a4f0, 0x40a2ea, 0x40a620)):
    ok_c = IMG[disp_call - BASE] == 0xe8 and \
        BASE + disp_call - BASE + 5 + struct.unpack_from("<i", IMG, disp_call - BASE + 1)[0] == ph1
    ok_j = IMG[disp_jmp - BASE] == 0xe9 and \
        BASE + disp_jmp - BASE + 5 + struct.unpack_from("<i", IMG, disp_jmp - BASE + 1)[0] == ph2
    ck(f"0x{disp_call:x} call 0x{ph1:x} + 0x{disp_jmp:x} jmp 0x{ph2:x}", ok_c and ok_j)
ck("0x40ad10 体内 0x40ad48 尾跳 0x40ad60",
   IMG[0x40ad48 - BASE] == 0xe9 and
   0x40ad48 + 5 + struct.unpack_from("<i", IMG, 0x40ad48 - BASE + 1)[0] == 0x40ad60)

# ═════════════════════════ T3 三站门控捕获 ═════════════════════════
print("\n[T3] 三站 (idx,val) 捕获")
caps, hit, err, _ = capture(0x409250, 0x409300, gates={SEGC + 0: 30})
ck("0x409300 全函数 + 门控 segC[0]=30 → (0,29)",
   hit and caps and caps[-1][1] == 0 and caps[-1][2] == 29, f"caps={[(hex(a),b,c) for a,b,c in caps]}")

caps0, hit0, _, _ = capture(0x409250, 0x409300, gates=None)
ck("0x409300 零态（segC[0]=0）不可达 —— 门控确为 segC[0]!=0", (not hit0) and len(caps0) == 0)

caps, hit, err, _ = capture(0x40c4d0, 0x40c4f3)
ck("0x40c4f3 修正 owner 0x40c4d0 → (1,0)",
   hit and caps and caps[-1][1] == 1 and caps[-1][2] == 0, f"caps={[(hex(a),b,c) for a,b,c in caps]}")

caps, hit, err, _ = capture(0x40a620, 0x40a6ec)
got62b = [t for t in caps if t[0] == 0x40a62b]
ck("0x40a620 起跑先命中 0x40a62b=(5,1)（与 fullmap immediate 条目一致 ⇒ 反证 owner 修正）",
   len(got62b) == 1 and got62b[0][1] == 5 and got62b[0][2] == 1, f"caps={[(hex(a),b,c) for a,b,c in caps]}")

idx, val = val_at(0x40a6c9, 0x40a6ec)
ck("0x40a6ec 切片入口 0x40a6c9 → (3,1)（零态 byte[0x513540]=0）", idx == 3 and val == 1,
   f"got=({idx},{val})")

# ═════════════════════════ T4 值公式参数扫描 ═════════════════════════
print("\n[T4] 值公式参数扫描")
ok = tot = 0
for v in (0, 1, 2, 5, 29, 30, 31, 100, 255):
    i2, v2 = val_at(0x4092e1, 0x409300, gates={SEGC + 0: v})
    tot += 1; ok += (i2 == 0 and v2 == (0 if v <= 1 else v - 1))
ck(f"0x409300: segC[0]=sat_sub8(segC[0],1)=max(v-1,0) 扫描 {ok}/{tot}", ok == tot)

ok = tot = 0
for v in (0, 1, 2, 3, 4, 7, 8, 15, 16, 50, 99, 200, 255):
    i2, v2 = val_at(0x40a6c9, 0x40a6ec, gates={G_513540: v})
    tot += 1; ok += (i2 == 3 and v2 == max(v >> 1, 1))
ck(f"0x40a6ec: segC[3]=max(byte[0x513540]>>1,1) 扫描 {ok}/{tot}", ok == tot)

# ═════════════════════════ T5 门控原语语义 ═════════════════════════
print("\n[T5] 门控/值源原语")
e, _ = _emu()
ok = tot = 0
for a, b in ((0, 0), (0, 1), (1, 1), (2, 1), (30, 1), (255, 1), (5, 9), (200, 100)):
    r = e.call(0x4ebd10, [a, b])["eax"] & 0xff
    tot += 1; ok += (r == (0 if a <= b else a - b))
ck(f"0x4ebd10 = sat_sub8(a,b) = (a<=b ? 0 : a-b) 扫描 {ok}/{tot}", ok == tot)

e, _ = _emu()
p = e.alloc(0x80)
ok = tot = 0
for f12, f13, f25, want in ((0xff, 7, 7, 1), (0xff, 7, 8, 0), (0x00, 7, 7, 0), (0xff, 0, 0, 1)):
    e.write(p + 0x12, bytes([f12])); e.write(p + 0x13, bytes([f13])); e.write(p + 0x25, bytes([f25]))
    r = e.call(0x4bb4e0, [p])["eax"]
    tot += 1; ok += (r == want)
ck(f"0x4bb4e0(entity) = (byte[+0x12]==0xff && byte[+0x13]==byte[+0x25]) 扫描 {ok}/{tot}", ok == tot)

ok = tot = 0
for v in (0, 1, 77, 255):
    e2, _ = _emu(gates={G_513540: v})
    tot += 1; ok += ((e2.call(0x43ca60, [])["eax"] & 0xff) == v)
ck(f"0x43ca60() = byte[0x513540] 取值器 扫描 {ok}/{tot}", ok == tot)

# ═════════════════════════ T6 25B 运行时结构摊平 ═════════════════════════
print("\n[T6] 25B 结构 @0x5203c0 —— 9 个访问器偏移契约（静态字节）")
ck("0x49c410 get_c(idx): al=byte[ecx+idx+0x13], ret 4",
   find(b"\x8a\x44\x01\x13", 0x49c410, 0x20) and find(b"\xc2\x04\x00", 0x49c410, 0x20))
ck("0x49c500 set_c(idx,val): byte[eax+ecx+0x13]=dl, ret 8",
   find(b"\x88\x54\x08\x13", 0x49c500, 0x20) and find(b"\xc2\x08\x00", 0x49c500, 0x20))
ck("0x49c420 +0x01 低5位域 setter: byte[ecx+1]=(byte[ecx+1]&0xe0)|v",
   find(b"\x8a\x41\x01", 0x49c420, 0x20) and find(b"\x24\xe0", 0x49c420, 0x20)
   and find(b"\x88\x41\x01", 0x49c420, 0x20))
ck("0x49c440 +0x01 高3位域 setter: byte[ecx+1]=(v<<5)|(byte[ecx+1]&0x1f)",
   find(b"\xc0\xe0\x05", 0x49c440, 0x20) and find(b"\x80\xe2\x1f", 0x49c440, 0x20)
   and find(b"\x88\x41\x01", 0x49c440, 0x20))
ck("0x49c390 旗组A 测位: byte[esi+edi+2] & (1<<bit%8), ret 4",
   find(b"\x8a\x4c\x3e\x02", 0x49c390, 0x40) and find(b"\xc2\x04\x00", 0x49c390, 0x40))
ck("0x49c3d0 旗组B 测位: byte[esi+edi+0xa] & (1<<bit%8), ret 4",
   find(b"\x8a\x4c\x3e\x0a", 0x49c3d0, 0x40) and find(b"\xc2\x04\x00", 0x49c3d0, 0x40))
ck("0x49c460 旗组A 置位: 读改写 byte[esi+edi+2], ret 8",
   find(b"\x8a\x5c\x3e\x02", 0x49c460, 0x50) and find(b"\xc2\x08\x00", 0x49c460, 0x50))
ck("0x49c4b0 旗组B 置位: 读改写 byte[esi+edi+0xa], ret 8",
   find(b"\x8a\x5c\x3e\x0a", 0x49c4b0, 0x50) and find(b"\xc2\x08\x00", 0x49c4b0, 0x50))
ck("0x49c2b0 word getter: ax=word[ecx]", find(b"\x66\x8b\x01", 0x49c2b0, 0x10))

# 结构 25B = 1+1+8+8+1+6 闭合
LAYOUT = [("事件类型/模式码", 0x00, 1), ("打包位域(低5/高3)", 0x01, 1),
          ("事件旗组A 64bit", 0x02, 8), ("事件旗组B 64bit", 0x0a, 8),
          ("未定名", 0x12, 1), ("段C 参数槽 segC[0..5]", 0x13, 6)]
tot = sum(n for _, _, n in LAYOUT)
ck(f"结构字段 1+1+8+8+1+6 = {tot} = 25B 无缝闭合", tot == 25 and
   all(LAYOUT[i][1] + LAYOUT[i][2] == LAYOUT[i + 1][1] for i in range(len(LAYOUT) - 1)))

# ═════════════════════════ T7 16 站逐站点归属重采 ═════════════════════════
print("\n[T7] 16 处 runtime-var 逐站点归属重采（修正 续219『首个 set_c 即停』的串味）")
runtime_sites = [e["set_c_call"] for e in fm["mapping"] if e["val_kind"] == "runtime-var"]
ck("fullmap runtime-var 站点数 = 16", len(runtime_sites) == 16, f"实测 {len(runtime_sites)}")

# 站点专属配方：门控 / 最小自足切片起点 / 调用跳过
G_MODE = 0x520605                       # word[0x520604] 的高字节；bits4-5 = (word>>12)&3
SPEC = {
    "0x409300": dict(entry=0x409250, gates={SEGC + 0: 30}),          # 门控 segC[0]!=0
    "0x413d4f": dict(entry=0x413d10, gates={G_MODE: 0x30}),          # 模式 si==3
    "0x413d65": dict(entry=0x413d10, gates={G_MODE: 0x30}),          # 模式 si==3
    "0x413d80": dict(entry=0x413d10, gates=None),                    # 模式 si==0（零态）
    "0x413d9c": dict(entry=0x413d10, gates={G_MODE: 0x20}),          # 模式 si==2
    "0x409814": dict(entry=0x4097bc, elide={0x4097f2: 0x40980c}),    # 调用跳过
    "0x40a6ec": dict(entry=0x40a6c9),                                # 最小自足切片
}
merged = {}
for cv in runtime_sites:
    sp = SPEC.get(cv) or dict(entry=fn_start(int(cv, 16)))
    caps, _, _, _ = capture(sp["entry"], int(cv, 16), gates=sp.get("gates"),
                            elide=sp.get("elide"))
    for cs, idx, val in caps:
        key = hex(cs)
        if key == cv:
            merged[cv] = (idx, val)

missing = [c for c in runtime_sites if c not in merged]
ck("16/16 站点均有按站点归属的具体 (idx,val)", len(missing) == 0,
   f"实测 {len(merged)}/16 缺 {missing}")
ck("全部 idx ∈ [0,5]（segC 合法槽位）", all(0 <= v[0] <= 5 for v in merged.values()))

# owner 0x413d10 下 4 站点必须彼此可区分归属（续219 曾把它们记成同一值）
d10 = [c for c in runtime_sites if fn_start(int(c, 16)) == 0x413d10]
ck(f"owner 0x413d10 下 {len(d10)} 站点各自独立归属", len(d10) == 4 and all(c in merged for c in d10),
   f"{ {c: merged.get(c) for c in d10} }")

# ═════════════════════ T8 0x413d10 = 2-bit 模式选择器 ═════════════════════
print("\n[T8] 0x413d10：si=(word[0x520604]>>12)&3 四分支穷举")
MODE_EXPECT = {0x00: [(0x413d80, 0, 20)],
               0x10: [],
               0x20: [(0x413d9c, 0, 20)],
               0x30: [(0x413d4f, 0, 20), (0x413d65, 1, 20)]}
for hi, want in sorted(MODE_EXPECT.items()):
    caps, _, _, _ = capture(0x413d10, None, gates={G_MODE: hi} if hi else None)
    ck(f"si={(hi >> 4) & 3} → {[hex(w[0]) for w in want] or '无写入'}",
       caps == want, f"实测 {[(hex(a), b, c) for a, b, c in caps]}")

# ═════════════════════ T9 0x409814 = 0x518588 表记录索引 ═════════════════════
print("\n[T9] 0x409814：segC[1] = (ptr-0x518588)/139（÷139 魔数 0x75ded953 + sar 6）")
ok = tot = 0
for k in (0, 1, 2, 3, 5, 10, 19, 20, 42, 99, 150, 199):
    i2, v2 = val_at(0x4097bc, 0x409814, elide={0x4097f2: 0x40980c},
                    force={0x4097c3: (UC_X86_REG_ESI, 0x518588 + 139 * k)})
    tot += 1; ok += (i2 == 1 and v2 == (k & 0xff))
ck(f"esi=0x518588+139*k → segC[1]=k 扫描 {ok}/{tot}", ok == tot)
ck("÷139 魔数 0x75ded953 位于 0x4097d9（stride 139 第二证据）",
   struct.unpack_from("<I", IMG, 0x4097d9 + 1 - BASE)[0] == 0x75ded953)
ck("0x409282 lea 系数链 base+v+138v = base+139v（stride 139 第一证据）",
   find(b"\x8d\x8c\x41\x88\x85\x51\x00", 0x409282, 0x10))
i2, v2 = val_at(0x4097bc, 0x409814, elide={0x4097f2: 0x40980c},
                force={0x4097c3: (UC_X86_REG_ESI, 0)})
ck("0x4097d0 `mov edi,0x14` 为不可达死代码（esi 被常量 0x518588 覆盖后 jne 恒成立）",
   i2 == 1 and v2 == 0, f"强置 esi=0 仍走除法路径 → ({i2},{v2})，非 20")

# ═════════════════════════ 落盘 ═════════════════════════
out = {
    "_doc": "续220：S15 段C 三站门控收口 + owner 边界修正 + 25B 结构摊平",
    "owner_fix": {k: {"old": v[0], "new": hex(v[1]),
                      "reason": "相位2 仅由 E9 jmp 到达（两相 handler 尾调用）"}
                  for k, v in EXPECT_FIX.items()},
    "three_sites": {
        "0x409300": {"owner": "0x409250", "segC_idx": 0,
                     "gate": "segC[0] != 0",
                     "formula": "segC[0] = sat_sub8(segC[0],1) = max(segC[0]-1,0)",
                     "captured_at_gate30": [0, 29], "sweep": "9/9"},
        "0x40c4f3": {"owner": "0x40c4d0 (修正自 0x40c350)", "segC_idx": 1,
                     "event": "bit2 将軍(足利)暗殺 · 相位2",
                     "formula": "segC[1] = 0x40c520() = 目标城索引(优先25→22→0x40c5d0兜底)",
                     "captured": [1, 0]},
        "0x40a6ec": {"owner": "0x40a620 (修正自 0x40a4f0)", "segC_idx": 3,
                     "event": "墨俣築城 · 相位2",
                     "slice_entry": "0x40a6c9",
                     "formula": "segC[3] = max(byte[0x513540]>>1, 1)",
                     "captured_zero_state": [3, 1], "sweep": "13/13"},
    },
    "primitives": {
        "0x4ebd10": "sat_sub8(a,b) = (a<=b ? 0 : a-b)  ← 新原语",
        "0x4bb4e0": "entity 谓词 = (byte[+0x12]==0xff && byte[+0x13]==byte[+0x25])",
        "0x43ca60": "byte[0x513540] 取值器",
        "0x40c520": "城索引选择器：0x40c550(25)→25 / 0x40c550(22)→22 / else 0x40c5d0",
        "0x4a0ef0": "word[ecx + (a*5+b)*2] —— 5 列 word 矩阵取值器（表 0x518588 +0x00）",
        "0x4a0f10": "word[ecx + (a*5+b)*2 + 0x32] —— 同表第二矩阵（+0x32）",
    },
    "table_0x518588": {
        "stride": 139,
        "evidence": ["0x409282 lea 系数链 base + v + 138v", "0x4097d9 ÷139 魔数 0x75ded953 + sar 6"],
        "matrices": {"+0x00": "5 列 word (0x4a0ef0)", "+0x32": "5 列 word (0x4a0f10)"},
        "note": "0x409814 写 segC[1] = (ptr-0x518588)/139 记录索引；0x40a4f0 用 0x4a0f30 求 5 word 和",
    },
    "mode_selector_0x413d10": {
        "expr": "si = (word[0x520604] >> 12) & 3",
        "si=0": "set_c(0, 0x413db0(slot3))  @0x413d80",
        "si=1": "无写入",
        "si=2": "set_c(0, 0x413db0(slot0))  @0x413d9c",
        "si=3": "set_c(0, 0x413db0(slot0)) @0x413d4f + set_c(1, 0x413db0(slot3)) @0x413d65",
    },
    "dead_code": {"0x4097d0": "mov edi,0x14 不可达：esi 在 test 前被常量 0x518588 覆盖，jne 恒成立"},
    "corrections_to_x219": [
        "续219『首个 set_c 即停』导致同 owner 多站点串味：0x413d10 下 4 站被记成同一 (0,20)，"
        "实际仅 0x413d80 在零态执行，另 3 站需 si=3/si=2；0x409814 的 (0,30) 实为前一站 0x4097b7 的立即值。",
        "本文件改用『栈上返回地址-5 反推 call 站点』做逐站点归属，16/16 全部按站点确证。",
    ],
    "struct_0x5203c0_25B": [
        {"off": "+0x00", "size": 1, "name": "事件类型/模式码", "access": "直写 (mov byte[0x5203c0],imm)"},
        {"off": "+0x01", "size": 1, "name": "打包位域 低5位+高3位", "access": "set 0x49c420 / 0x49c440"},
        {"off": "+0x02", "size": 8, "name": "事件旗组A 64bit", "access": "test 0x49c390 / set 0x49c460"},
        {"off": "+0x0a", "size": 8, "name": "事件旗组B 64bit", "access": "test 0x49c3d0 / set 0x49c4b0"},
        {"off": "+0x12", "size": 1, "name": "未定名", "access": "(访问器带内无命中)"},
        {"off": "+0x13", "size": 6, "name": "段C 参数槽 segC[0..5]", "access": "get 0x49c410 / set 0x49c500"},
    ],
    "runtime_var_merged": {k: (list(v) if v else None) for k, v in merged.items()},
    "methodology": "函数起点集合必须同时收 E8 call 与 E9 jmp 目标；判别器用『ret+0x90 填充』边界，"
                   "『指令边界对齐』检查无鉴别力（25/25 全 True）。"
                   "全函数 emu 被无关 I/O 阻断时，改用『最小自足切片起点』= val 的 def-use 闭包起点。",
}
with open(os.path.join(ROOT, "s15_segc_gated_capture.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

npass = sum(1 for _, c, _ in checks if c)
print(f"\n段C 25B 结构：{' | '.join(f'{d[0]}@{d[1]}' for d in [(x['name'], x['off']) for x in out['struct_0x5203c0_25B']])}")
print(f"三站收口：0x409300=(0,29,门控segC[0]!=0) 0x40c4f3=(1,0,owner→0x40c4d0) 0x40a6ec=(3,1,owner→0x40a620)")
print(f"\nRESULT: {npass}/{len(checks)} " + ("PASS" if npass == len(checks) else "FAIL"))
sys.exit(0 if npass == len(checks) else 1)
