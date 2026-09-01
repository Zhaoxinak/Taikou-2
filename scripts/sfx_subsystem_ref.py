#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sfx_subsystem_ref.py -- 太阁立志传2「音效子系统」全破参考实现 + 自校验（续195）
=====================================================================================
模块定位：此前项目从未系统破解「音效/素材」层。本模块把 **39 个音效 ID→文件名→玩法语义**
以及其派发器 `play_sfx(0x4997c0)` 的**门控条件**全部钉死，并用 Unicorn 端到端仿真验证。

────────────────────────────── 结构 ──────────────────────────────
  SFX 名指针表   @0x50ba40 : const char* SFX_NAMES[39]   (4B×39, 倒序指向名串池 @0x50badc..)
  名串池         @0x50badc : 39 条 "A:XXXX.KOS" 以 NUL 结尾
  播放主入口     0x4997c0 : play_sfx(uint16 id)
  内层查表播放   0x499740 : 真正按 id 取 SFX_NAMES[id] 后调 0x4015f0
  播放底层       0x4015f0 : cdecl 3 参 (name, 0, 0)
  音效子系统对象  0x5256c8 : word[+0] = 运行期已载入音效数（静态全 0，加载后填 39）
  就绪标志       0x50b9b0 : word == 0x10 表示音效子系统就绪
  全局音效开关   0x520604 : byte bit1（test byte[0x520604],2）

────────────────────────── play_sfx 门控链 ───────────────────────────
  0x4997c0  push esi
  0x4997c1  mov  esi,[esp+8]          ; id
  0x4997c5  cmp  si,0x27              ; ★ 硬编码上限 39（与名表 39 项互证）
  0x4997c9  jae  exit                 ; id >= 39 → 不播
  0x4997cb  mov  ecx,0x5256c8
  0x4997d0  call 0x499780             ; 查询/占用通道（thiscall，无栈参）
  0x4997d5  test eax,eax
  0x4997d7  je   +0xc
  0x4997de  call 0x499770             ; 通道忙 → 先停止
  0x4997e3  test byte[0x520604],2     ; ★ 全局音效开关
  0x4997ea  je   exit                 ; 关闭 → 不播
  0x4997ec  push esi
  0x4997ed  mov  ecx,0x5256c8
  0x4997f2  call 0x499740
  0x4997f7  pop  esi; ret

  0x499740  mov eax,[esp+4]           ; id
  0x499744  cmp ax,[ecx]              ; ★ 二次边界：id < word[0x5256c8]（已载入数）
  0x499747  jae  ret
  0x499749  cmp word[0x50b9b0],0x10   ; ★ 就绪标志
  0x499751  jne ret
  0x49975c  mov eax,[eax*4+0x50ba40]  ; ★ SFX_NAMES[id]
  0x499763  push eax; call 0x4015f0; add esp,0xc

⚠️ 调用约定坑（本模块实测）：
  - 0x499780 / 0x499770 是 **thiscall（ecx=this，无栈参，普通 ret）**，emu 桩只 esp+=4。
  - 0x4015f0 是 **cdecl 3 参**（调用方 `add esp,0xc` 平栈），emu 桩只 esp+=4 并读 [esp+4..]。
  - play_sfx 本身 **stdcall ret 4**？否 —— 它是 `ret`（1 栈参由调用方 `add esp,4` 清），
    实测调用点全为 `push <id>; call 0x4997c0; add esp,4` ⇒ cdecl 1 参。

自校验：见文件末尾 main()（静态结构断言 + Unicorn 端到端 39/39 + 门控负例）。
输出：scripts/sfx_subsystem.json
"""
import os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "scripts/_unpacked_mem.bin")
BASE = 0x400000

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(BIN, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

# ---------------- 常量 ----------------
SFX_TBL = 0x50ba40          # const char* SFX_NAMES[39]
SFX_POOL = 0x50badc         # 名串池起点
SFX_N = 39                  # 0x27
PLAY_MAIN = 0x4997c0        # play_sfx(id)
PLAY_INNER = 0x499740       # 查表播放
PLAY_BOTTOM = 0x4015f0      # 底层播放(cdecl 3 参)
SFX_OBJ = 0x5256c8          # 音效子系统对象；word[+0]=已载入数
SFX_READY = 0x50b9b0        # word == 0x10 就绪
SFX_ENABLE = 0x520604       # byte bit1 全局开关

# 39 个音效 ID → (文件名, 中文语义, 类别)。中文语义由「文件名罗马字 + 调用点玩法上下文」双语坐实。
SFX_SEMANTICS = {
    0:  ("A:CLICK.KOS",    "UI 点击/确定",      "UI"),
    1:  ("A:CANCEL.KOS",   "UI 取消",           "UI"),
    2:  ("A:KOUGEKI1.KOS", "攻击(通常)1",       "战斗"),
    3:  ("A:KOUGEKI2.KOS", "攻击(通常)2",       "战斗"),
    4:  ("A:OPENGATE.KOS", "开城门",            "攻城战"),
    5:  ("A:TOTUGEKI.KOS", "突击",              "战斗"),
    6:  ("A:TEPPOU.KOS",   "铁炮射击",          "战斗"),
    7:  ("A:IDOU.KOS",     "部队移动",          "战斗"),
    8:  ("A:SEIKOU.KOS",   "行动成功",          "内政/通用"),
    9:  ("A:SHIPPAI.KOS",  "行动失败",          "内政/通用"),
    10: ("A:GIHEI.KOS",    "伪兵(疑兵)计略",    "计略"),
    11: ("A:KAKEI.KOS",    "火计(火攻)",        "计略"),
    12: ("A:RAKUSEKI.KOS", "落石(攻城防御)",    "攻城战"),
    13: ("A:SYUUZEN.KOS",  "修缮(修复)",        "攻城战/内政"),
    14: ("A:UMETATE.KOS",  "埋立(填埋/普请)",   "攻城战/内政"),
    15: ("A:ZANSYU.KOS",   "残守/残兵(待考)",   "战斗"),
    16: ("A:SHIKI.KOS",    "士气(动摇/鼓舞)",   "战斗"),
    17: ("A:KOATARI.KOS",  "小命中(轻伤)",      "单挑/战斗"),
    18: ("A:OOATARI.KOS",  "大命中(重创)",      "单挑/战斗"),
    19: ("A:UKETA.KOS",    "受击(挨打)",        "单挑/战斗"),
    20: ("A:YOKETA.KOS",   "闪避(躲开)",        "单挑/战斗"),
    21: ("A:METUBUSI.KOS", "目溃(致盲)",        "忍术/计略"),
    22: ("A:IATSU.KOS",    "威压",              "计略"),
    23: ("A:KEMURI.KOS",   "烟(烟幕)",          "计略"),
    24: ("A:NIGERU.KOS",   "败走/逃跑",         "战斗"),
    25: ("A:IKARI.KOS",    "愤怒",              "战斗"),
    26: ("A:KAISHIN.KOS",  "会心一击",          "单挑/战斗"),
    27: ("A:TGENSYOU.KOS", "敌现象/敌现身",     "战斗"),
    28: ("A:IGENSYOU.KOS", "异现象(异变)",      "战斗/事件"),
    29: ("A:INOTIGOI.KOS", "命乞(求饶)",        "单挑/战斗"),
    30: ("A:IZOUKA.KOS",   "威吓/伊杂贺(待考)", "计略"),
    31: ("A:GINOUUP.KOS",  "技能提升",          "养成"),
    32: ("A:MACHIMES.KOS", "町消息(町内广播)",  "内政"),
    33: ("A:NINJA.KOS",    "忍者",              "忍术/计略"),
    34: ("A:MI_HARE.KOS",  "天候·晴",           "天候"),
    35: ("A:MI_AME.KOS",   "天候·雨",           "天候"),
    36: ("A:MATISIRO.KOS", "待机/町城(待考)",   "内政"),
    37: ("A:SIKAKU.KOS",   "死角(背袭)",        "战斗"),
    38: ("A:KAMINARI.KOS", "雷",                "天候/计略"),
}


def rd(va, n):
    return MEM[va - BASE: va - BASE + n]


def cstr(va, maxlen=24):
    b = rd(va, maxlen)
    z = b.find(0)
    return b[:z if z >= 0 else maxlen].decode("ascii", "replace")


def disasm(va, size):
    return list(md.disasm(rd(va, size), va))


def ops_at(va, size):
    """返回该地址起 size 字节内的指令文本（已物化 list，避免 capstone 嵌套）。"""
    return list(md.disasm(rd(va, size), va))


def imm_of(op_str):
    vals = []
    for tok in op_str.split(","):
        tok = tok.strip()
        if re.fullmatch(r"(0x[0-9a-f]+|[0-9]+)", tok):
            vals.append(int(tok, 16) if tok.startswith("0x") else int(tok))
    return vals


# =====================================================================
# 1. 静态：名表提取
# =====================================================================
def sfx_names():
    out = []
    for i in range(SFX_N):
        p = struct.unpack("<I", rd(SFX_TBL + 4 * i, 4))[0]
        out.append((i, p, cstr(p)))
    return out


# =====================================================================
# 2. 静态：play_sfx 调用点 ID 提取（窗口自校准，抗 capstone 错位）
# =====================================================================
def find_call_sites(target):
    sites = []
    for off in range(len(MEM) - 5):
        if MEM[off] != 0xE8:
            continue
        rel = struct.unpack_from("<i", MEM, off + 1)[0]
        if ((BASE + off + 5 + rel) & 0xFFFFFFFF) != target:
            continue
        sites.append(BASE + off)
    return sites


def arg_at(call_va, span=0x40):
    """回溯 call_va 前最近的 `push <imm>` 实参。

    ⚠️ 工具坑（本模块实测）：从单一固定起点反汇编极易错位（x86 变长指令），
    一旦错位就完全抽不到 push。正确做法 = **枚举回溯长度** back=1..span，
    只接受「指令流中恰好存在一条 address==call_va 的指令」的起点（即指令边界对齐），
    在这些候选里取 **back 最大**（上下文最全）的那一个。
    """
    cands = []
    for back in range(1, span):
        start = call_va - back
        try:
            ins = list(md.disasm(rd(start, back + 16), start))
        except Exception:
            continue
        idx = None
        for k, i in enumerate(ins):
            if i.address == call_va:
                idx = k
                break
        if idx is None:
            continue          # 起点错位（无指令边界落在 call_va）→ 丢弃
        pushes = []
        for i in ins[:idx]:
            if i.mnemonic == "push":
                v = imm_of(i.op_str)
                if v:
                    pushes.append((i.address, v[0]))
        if pushes:
            cands.append((back, pushes[-1]))
    if not cands:
        return None
    cands.sort()
    return cands[-1][1]       # 取窗口最大的那个（上下文最全、最可信）


def call_site_ids(target=PLAY_MAIN):
    """返回 [(call_va, id or None)]"""
    out = []
    for va in find_call_sites(target):
        p = arg_at(va)
        out.append((va, p[1] if p else None, p[0] if p else None))
    return out


# =====================================================================
# 3. emu：Unicorn 端到端验证
# =====================================================================
def emu_play(id_, loaded=SFX_N, ready=0x10, enable=2, stub_query=True):
    """仿真 play_sfx(id_)，返回底层播放函数 0x4015f0 收到的实参 (name_ptr, a2, a3)；
    未触发播放则返回 None。"""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP

    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, len(MEM))
    mu.mem_write(BASE, MEM)
    STACK_TOP = 0x600000
    mu.mem_map(STACK_TOP, 0x40000)
    STOP = 0x700000
    mu.mem_map(STOP, 0x1000)
    mu.mem_write(STOP, b"\x90\x90\x90\x90")
    # 桩页（供 0x499780/0x499770/0x4015f0 跳入）
    STUB = 0x900000
    mu.mem_map(STUB, 0x1000)
    mu.mem_write(STUB, b"\xc3" * 0x1000)

    # ---- 预置运行期全局（静态全 0，必须手动灌）----
    mu.mem_write(SFX_OBJ, struct.pack("<H", loaded) + b"\x00" * 30)
    mu.mem_write(SFX_READY, struct.pack("<H", ready))
    mu.mem_write(SFX_ENABLE, bytes([enable]))

    captured = []

    def on_code(mu2, address, size, ud):
        sp = mu2.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack("<I", mu2.mem_read(sp, 4))[0]
        if address == STUB:                       # 通道查询 0x499780 -> eax=0（闲）
            mu2.reg_write(UC_X86_REG_EAX, 0)
            mu2.reg_write(UC_X86_REG_ESP, sp + 4)
            mu2.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB + 0x10:              # 0x499770 停止（本测试不会走到）
            mu2.reg_write(UC_X86_REG_EAX, 0)
            mu2.reg_write(UC_X86_REG_ESP, sp + 4)
            mu2.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB + 0x20:              # 0x4015f0 cdecl 3 参
            a1 = struct.unpack("<I", mu2.mem_read(sp + 4, 4))[0]
            a2 = struct.unpack("<I", mu2.mem_read(sp + 8, 4))[0]
            a3 = struct.unpack("<I", mu2.mem_read(sp + 0xc, 4))[0]
            captured.append((a1, a2, a3))
            mu2.reg_write(UC_X86_REG_EAX, 0)
            mu2.reg_write(UC_X86_REG_ESP, sp + 4)
            mu2.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB + 0x30:              # 0x4f1ef8（若被调用）-> 返回 0
            mu2.reg_write(UC_X86_REG_EAX, 0)
            mu2.reg_write(UC_X86_REG_ESP, sp + 4)
            mu2.reg_write(UC_X86_REG_EIP, ret)
        elif address == STOP:
            mu2.emu_stop()

    # 重定向三个被调用者到桩
    mu.mem_write(0x499780, b"\xe9" + struct.pack("<i", STUB - (0x499780 + 5)) + b"\x90" * 8)
    mu.mem_write(0x499770, b"\xe9" + struct.pack("<i", (STUB + 0x10) - (0x499770 + 5)) + b"\x90" * 8)
    mu.mem_write(0x4015f0, b"\xe9" + struct.pack("<i", (STUB + 0x20) - (0x4015f0 + 5)) + b"\x90" * 8)
    mu.mem_write(0x4f1ef8, b"\xe9" + struct.pack("<i", (STUB + 0x30) - (0x4f1ef8 + 5)) + b"\x90" * 8)
    mu.hook_add(UC_HOOK_CODE, on_code)

    esp = STACK_TOP + 0x40000 - 0x2000
    mu.mem_write(esp, struct.pack("<I", STOP))
    mu.mem_write(esp + 4, struct.pack("<I", id_ & 0xFFFF))
    mu.reg_write(UC_X86_REG_ESP, esp)
    mu.reg_write(UC_X86_REG_EIP, PLAY_MAIN)
    mu.emu_start(PLAY_MAIN, STOP + 1, count=0x200000)
    return captured[0] if captured else None


# =====================================================================
# 4. 自校验
# =====================================================================
FAIL = []


def check(name, cond, extra=""):
    tag = "OK  " if cond else "FAIL"
    if not cond:
        FAIL.append(name)
    print("  [%s] %s%s" % (tag, name, ("  -- " + extra) if extra and not cond else ""))


def main():
    print("=" * 78)
    print("太阁立志传2 · 音效子系统 参考实现自校验（续195）")
    print("=" * 78)

    # ---------- A. 名表结构 ----------
    print("\n[A] SFX 名指针表 @0x%06x (4B×%d)" % (SFX_TBL, SFX_N))
    names = sfx_names()
    check("A1 表长 39，指针全部落在名串池 0x%06x..0x%06x" % (SFX_POOL, SFX_POOL + 0x250),
          len(names) == SFX_N and all(SFX_POOL <= p < SFX_POOL + 0x300 for _, p, _ in names),
          str([(i, hex(p), s) for i, p, s in names if not (SFX_POOL <= p < SFX_POOL + 0x300)][:3]))
    check("A2 39 条名串全为 A:*.KOS 且以 NUL 结尾",
          all(re.fullmatch(r"A:[A-Z0-9_]+\.KOS", s) for _, _, s in names),
          str([(i, s) for i, _, s in names if not re.fullmatch(r"A:[A-Z0-9_]+\.KOS", s)]))
    check("A3 名串与 SFX_SEMANTICS 中文语义表逐项一致",
          all(names[i][2] == SFX_SEMANTICS[i][0] for i in range(SFX_N)),
          str([(i, names[i][2], SFX_SEMANTICS[i][0]) for i in range(SFX_N)
               if names[i][2] != SFX_SEMANTICS[i][0]]))
    for i, p, s in names[:4] + names[-2:]:
        print("        [%2d] 0x%06x -> 0x%06x  %-16s %s" % (i, SFX_TBL + 4 * i, p, s, SFX_SEMANTICS[i][1]))

    # ---------- B. play_sfx 门控静态断言 ----------
    print("\n[B] play_sfx 门控链静态断言")
    o = " ; ".join("%s %s" % (i.mnemonic, i.op_str) for i in ops_at(PLAY_MAIN, 0x40))
    check("B1 play_sfx 硬编码上限 `cmp si,0x27`（39）", "cmp" in o and "0x27" in o, o[:120])
    check("B2 全局开关 `test byte[0x520604],2`", "0x520604" in o and ", 2" in o, o[:160])
    check("B3 音效子系统对象 0x5256c8（thiscall ecx）", "0x5256c8" in o, o[:160])
    check("B4 调内层查表 0x499740", "0x499740" in o, o[:160])

    oi = " ; ".join("%s %s" % (i.mnemonic, i.op_str) for i in ops_at(PLAY_INNER, 0x40))
    check("B5 内层二次边界 `cmp ax,[ecx]`（ecx=0x5256c8 已载入数）", "cmp" in oi and "[ecx]" in oi, oi[:120])
    check("B6 内层就绪标志 `cmp word[0x50b9b0],0x10`", "0x50b9b0" in oi and "0x10" in oi, oi[:160])
    check("B7 内层查表 `mov eax,[eax*4+0x50ba40]`", "0x50ba40" in oi and "eax*4" in oi, oi[:160])
    check("B8 内层调底层播放 0x4015f0", "0x4015f0" in oi, oi[:160])

    # ---------- C. 调用点 ID 分布 ----------
    print("\n[C] play_sfx 调用点 ID 提取")
    sites = call_site_ids(PLAY_MAIN)
    resolved = [(va, i) for va, i, _ in sites if i is not None and i < SFX_N]
    check("C1 play_sfx 调用点 >= 70 处", len(sites) >= 70, "got %d" % len(sites))
    check("C2 可静态定 ID 的调用点 >= 66 处", len(resolved) >= 66, "got %d" % len(resolved))
    from collections import Counter
    c = Counter(i for _, i in resolved)
    covered = sorted(set(i for _, i in resolved))
    check("C3 39 个音效中 >= 20 个有静态调用点", len(covered) >= 20, "got %d" % len(covered))
    check("C4 关键 ID 命中已知调用点（0=点击/1=取消/11=火计/31=技能提升/33=忍者）",
          all(k in c for k in (0, 1, 11, 31, 33)), str({k: c.get(k) for k in (0, 1, 11, 31, 33)}))
    print("        已覆盖 ID (%d/39): %s" % (len(covered), covered))
    print("        TOP 调用: %s" % ", ".join("id%d=%s×%d" % (i, SFX_SEMANTICS[i][0][2:-4], n)
                                             for i, n in c.most_common(8)))

    # ---------- D. emu 端到端 ----------
    print("\n[D] Unicorn 端到端：play_sfx(id) -> 0x4015f0(name, 0, 0)")
    ok = 0
    bad = []
    for i in range(SFX_N):
        got = emu_play(i)
        exp_ptr = struct.unpack("<I", rd(SFX_TBL + 4 * i, 4))[0]
        if got and got[0] == exp_ptr and got[1] == 0 and got[2] == 0:
            ok += 1
        else:
            bad.append((i, got, exp_ptr))
    check("D1 全 39 个 ID 端到端：0x4015f0 收到 (SFX_NAMES[id], 0, 0)", ok == SFX_N,
          "%d/%d ; bad=%s" % (ok, SFX_N, bad[:3]))
    if ok == SFX_N:
        print("        ✅ 39/39 —— ID→文件名映射由运行时坐实（非静态猜测）")

    # ---------- E. emu 门控负例 ----------
    print("\n[E] Unicorn 门控负例（不播放的四种情形）")
    check("E1 id=39（越界，cmp si,0x27 拦下）不播放", emu_play(39) is None)
    check("E2 全局开关关闭（byte[0x520604]=0）不播放", emu_play(5, enable=0) is None)
    check("E3 就绪标志未置（word[0x50b9b0]!=0x10）不播放", emu_play(5, ready=0) is None)
    check("E4 已载入数不足（word[0x5256c8]=5, id=10）不播放", emu_play(10, loaded=5) is None)
    check("E5 已载入数足够（word[0x5256c8]=11, id=10）正常播放",
          (emu_play(10, loaded=11) or (None,))[0] ==
          struct.unpack("<I", rd(SFX_TBL + 40, 4))[0])

    # ---------- F. 落盘 ----------
    out = {
        "meta": {
            "title": "太阁立志传2 音效子系统（续195）",
            "sfx_table_va": hex(SFX_TBL), "sfx_count": SFX_N,
            "sfx_name_pool_va": hex(SFX_POOL),
            "play_sfx": hex(PLAY_MAIN), "play_inner": hex(PLAY_INNER),
            "play_bottom_cdecl3": hex(PLAY_BOTTOM),
            "sfx_object": hex(SFX_OBJ), "ready_flag": hex(SFX_READY),
            "enable_flag": hex(SFX_ENABLE),
            "note": "word[0x5256c8]=运行期已载入数; word[0x50b9b0]==0x10=就绪; byte[0x520604] bit1=全局音效开关",
        },
        "sfx": [
            {"id": i, "file": names[i][2], "ptr": hex(names[i][1]),
             "zh": SFX_SEMANTICS[i][1], "cat": SFX_SEMANTICS[i][2],
             "static_calls": c.get(i, 0),
             "call_sites": ["0x%x" % va for va, j in resolved if j == i]}
            for i in range(SFX_N)
        ],
        "call_sites_total": len(sites),
        "call_sites_id_resolved": len(resolved),
    }
    p = os.path.join(ROOT, "scripts", "sfx_subsystem.json")
    import json
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n[输出] %s" % p)

    print("\n" + "=" * 78)
    if FAIL:
        print("RESULT: %d FAIL ❌  -> %s" % (len(FAIL), FAIL))
        return 1
    print("RESULT: ALL PASS ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
