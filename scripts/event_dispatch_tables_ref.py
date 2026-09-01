#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事件派发：转码表/跳表对 + `+0x268` 子记录数组 —— 结构参考 + 自测。

Static only (capstone disasm + byte reads of _unpacked_mem.bin). No emulation.

This closes MEMORY 仍待破 ④ 的三项（第四项「事件 id2 尾跳目标」仍须 emu）。

===============================================================================
1) 待破④ 之「`0x44da00` 转码表 / `0x44d9ec` 跳表」 —— 全部静态破出
===============================================================================
派发器 `0x44d950`（ids 3/15 的 per-tick 状态机）：
    mov  di, word[ctx+8]            ; flags
    call 0x49f6b0                   ; getCtx
    mov  cx, word[0x5205fe]         ; 全局模式
    mov  bp, word[eax]              ; bp = 事件 id
    movzx bx, byte[ctx+4]           ; bx = 状态 state (0..9)
    cmp  cx,2 ; je EXIT
    cmp  cx,3 ; je EXIT             ; 全局 0x5205fe==2/3 → 直接退出
    test edi,0x8000 ; jne EXIT      ; ctx+8 bit15 已处理 → 退出
    cmp  ecx,9 ; ja EXIT            ; state>9 → 退出（越界保护）
    mov  al, byte[ecx + 0x44da00]   ; ★ 转码表（10B，下标 0..9）
    jmp  dword[eax*4 + 0x44d9ec]    ; ★ 跳表（5 项）
  …… 5 个分支体 ……
    0x44d9a0: mov word[0x506c4c], 0xaa4 ; jmp TAIL   （state 9 → 置下一条 MSG）
    0x44d9ab: push esi; call 0x4441a0   ; jmp TAIL   （state 7 处理）
    0x44d9b3: cmp bp,3  ; jne +6
               push esi; call 0x44da10  ; jmp TAIL   （id3 → 0x44da10）
               cmp bp,0xf; jne TAIL
               push esi; call 0x44da90  ; jmp TAIL   （id15 → 0x44da90）
    TAIL 0x44d9d0: cmp bx,9 ; je EXIT
               or edi,0x8000 ; push edi ; call 0x49bfc0   ; ctx+8 |= 0x8000（本 tick 已处理）

★ 跳表 0x44d9ec（5 项，正好占 0x44d9ec..0x44da00 = 20B）
    [0] 0x44d9b3   [1] 0x44d9b3   [2] 0x44d9ab   [3] 0x44d9a0   [4] 0x44d9e4(=EXIT)
★ 转码表 0x44da00（10B） = [0,4,1,4,4,4,4,2,4,3]
    （表长 10 被其后 6 个 nop 填充到下一函数 0x44da10 证实）

⇒ state → 分支：
    state 0 → 0x44d9b3（按 id 分派：id3→0x44da10 / id15→0x44da90）
    state 1 → EXIT（空转）
    state 2 → 0x44d9b3（同上）
    state 3,4,5,6 → EXIT（空转）
    state 7 → 0x44d9ab（call 0x4441a0）
    state 8 → EXIT（空转）
    state 9 → 0x44d9a0（置 word[0x506c4c]=0xaa4，终态不再推进）
  有效状态 = {0,2,7,9}；空转状态 = {1,3,4,5,6,8}

三个分支处理体都是「显示消息」（共享 helper `0x44df20` 取值，终以 `0x47b900` show_MSG）：
  * `0x44da10`(id3)   : MSG = 0x11b9 + (state!=0) → **0x11b9 / 0x11ba**；
                        值 = 0x44df20(ctx, byte[ctx+0xb]*10)（*10 为物品表 stride ⇒
                        byte[ctx+0xb] 是物品槽号）；byte[ctx+0xb]==0 时直接返回（不发消息）。
                        发言者 = 0x49f610() 非空用它，否则回退 0x49f5e0()。
  * `0x44da90`(id15)  : 0x49f610() 非空 → MSG **0xde6**（发言者=B）；否则 → MSG **0xde5**（发言者=A=0x49f5e0()）。
  * `0x4441a0`(state7): 若 word[ctx+8]&2 → MSG **0x1659**（B 非空，发言者=B）/ **0x1658**（B 空，发言者=A）；
                        否则 → MSG **0x57c**。

===============================================================================
2) 待破④ 之「`+0x268` 处 2×48B 子记录」 —— 纠偏：不是独立表
===============================================================================
`0x484f34`(id1) 反汇编：
    esi = this ; edi = 0 ; cx = 0 ; dl = 1
  LOOP: eax = cx ; eax = eax*3 ; eax <<= 4        ; eax = cx*48
        test byte[eax + esi + 0x268], dl          ; 测 byte[this+0x268 + cx*48] bit0
        jne FOUND
        inc cx ; cmp cx,2 ; jl LOOP               ; 仅 2 个槽 (cx=0,1)
  FOUND: edi = this + 0x244 + cx*48               ; 选中子记录基址
        dword[edi+0x24] &= ~1                     ; 清 bit0（已处理）
        0x4edfa0(0x526c50) … call dword[edx+0x14] … 0x4edf70(0x526c50)
                                                  ; edx = dword[edi] = vptr ⇒ 虚调用 vtable[5](0)
🔑 **几何实证**：子记录数组基 = `this + 0x244`，stride = **48**，2 条；
   记录内 flags dword 在 **+0x24** ⇒
     rec[0] flag @ this+0x244+0x24 = **this+0x268**
     rec[1] flag @ this+0x274+0x24 = **this+0x298** = 0x268 + 1*48  ✔
   ⇒ 旧注「`+0x268` 处 2×48B 子记录」是**误读**：0x268 并非表基址，而是
     **子记录 0 内部的 flags dword（+0x24）**；stride 48 来自外层数组（基 0x244）。
   每条子记录是 C++ 对象（+0 = vptr），flags bit0 = 待处理，处理 = 调 vtable[5](0)，
   并置于 `0x526c50` 的临界区（0x4edfa0/0x4edf70）内。⇒ 这是一个 **2 槽待处理任务队列**。

===============================================================================
3) 同一函数内还发现第二组「转码表 + 跳表」（同一编译器惯用法）
===============================================================================
`0x484f34` 尾部二级派发（先要求 dword[ctx+0]==1）：
    eax = dword[ctx+4] ; eax += 0xfffff81f        ; ⇒ eax = dword[ctx+4] − 2017
    cmp eax,0xd ; ja 其他                          ; 仅 0..13 有效 ⇒ 原值 2017..2030
    dl = byte[eax + 0x4850a8]                      ; ★ 转码表（14B）
    jmp dword[edx*4 + 0x485098]                    ; ★ 跳表（4 项）
★ 跳表 0x485098 = [0x48505d, 0x484fcc, 0x485016, 0x485090]
★ 转码表 0x4850a8 = [0,0,0,0,0, 3,3,3,3,3,3,3, 1, 2]
    （表长 14 被其后 10 个 nop 证实）
⇒ 2017..2021 → 0x48505d ；2022..2028 → 0x485090 ；2029 → 0x484fcc ；2030 → 0x485016

🔑 **通用惯用法（可复用）**：本 binary 的 switch 常被 MSVC 编译成
   「范围检查 → byte 转码表 → dword 跳表」两级；转码表长度 = 上界+1，
   其后紧跟 nop 对齐填充，跳表紧邻转码表之前。见 MEMORY.md 方法论。
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, 'rb').read()
BASE = 0x400000
def off(va): return va - BASE
def u32(va): return struct.unpack('<I', data[off(va):off(va)+4])[0]

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def dis(va0, va1):
    out = []
    for ins in md.disasm(data[off(va0):off(va1)], va0):
        if ins.address >= va1:
            break
        out.append((ins.address, ins.mnemonic, ins.op_str))
    return out

def has(s, mnem, *subs):
    return any(m == mnem and all(x in op for x in subs) for (_, m, op) in s)

CHECKS = PASS = 0
def chk(name, cond):
    global CHECKS, PASS
    CHECKS += 1
    if cond:
        PASS += 1
        print('  [PASS] %s' % name)
    else:
        print('  [FAIL] %s' % name)

# ---------------------------------------------------------------- expected data
JT_44D9EC = [0x44d9b3, 0x44d9b3, 0x44d9ab, 0x44d9a0, 0x44d9e4]
TC_44DA00 = [0, 4, 1, 4, 4, 4, 4, 2, 4, 3]
EXIT_VA   = 0x44d9e4
JT_485098 = [0x48505d, 0x484fcc, 0x485016, 0x485090]
TC_4850A8 = [0,0,0,0,0, 3,3,3,3,3,3,3, 1, 2]

def verify():
    global CHECKS, PASS
    CHECKS = PASS = 0

    print('--- 1) 跳表 0x44d9ec / 转码表 0x44da00 (派发器 0x44d950, ids 3/15) ---')
    jt = [u32(0x44d9ec + i*4) for i in range(5)]
    chk('跳表 0x44d9ec = 5 项且值正确', jt == JT_44D9EC)
    chk('跳表紧邻转码表之前 (0x44d9ec+20 == 0x44da00)', 0x44d9ec + 5*4 == 0x44da00)
    tc = list(data[off(0x44da00):off(0x44da00)+10])
    chk('转码表 0x44da00 (10B) 值正确', tc == TC_44DA00)
    chk('转码表长 10 由其后 6 个 nop 填充到 0x44da10 证实',
        all(b == 0x90 for b in data[off(0x44da0a):off(0x44da10)]) and
        0x44da00 + 10 == 0x44da0a)

    # state -> branch
    st2br = {s: (jt[tc[s]] if tc[s] < 5 else None) for s in range(10)}
    chk('state 0 -> 0x44d9b3 (按 id 分派)', st2br[0] == 0x44d9b3)
    chk('state 2 -> 0x44d9b3 (按 id 分派)', st2br[2] == 0x44d9b3)
    chk('state 7 -> 0x44d9ab (call 0x4441a0)', st2br[7] == 0x44d9ab)
    chk('state 9 -> 0x44d9a0 (置 0x506c4c=0xaa4)', st2br[9] == 0x44d9a0)
    chk('空转状态 {1,3,4,5,6,8} 全部 -> EXIT 0x44d9e4',
        all(st2br[s] == EXIT_VA for s in (1, 3, 4, 5, 6, 8)))
    chk('有效状态恰为 {0,2,7,9}',
        sorted(s for s in range(10) if st2br[s] != EXIT_VA) == [0, 2, 7, 9])

    d = dis(0x44d950, 0x44d9ea)
    chk('派发器含 state 越界检查 (cmp ecx,9 ; ja)',
        has(d, 'cmp', 'ecx', '9') and has(d, 'ja'))
    chk('派发器读转码表 [ecx+0x44da00]', has(d, 'mov', '0x44da00'))
    chk('派发器经跳表 [eax*4 + 0x44d9ec] 派发',
        has(d, 'jmp', '0x44d9ec') and any('*4' in op for (_, m, op) in d if m == 'jmp'))
    chk('派发器读 state 于 byte[ctx+4]', has(d, 'movzx', 'esi + 4'))
    chk('早退：全局 0x5205fe 比较', has(d, 'mov', '0x5205fe'))
    chk('早退：test edi,0x8000 (ctx+8 bit15 已处理)', has(d, 'test', 'edi', '0x8000'))
    chk('尾部置 ctx+8 |= 0x8000 (call 0x49bfc0)', has(d, 'call', '0x49bfc0'))
    chk('state 9 分支置 word[0x506c4c] = 0xaa4',
        has(d, 'mov', '0x506c4c', '0xaa4'))
    chk('id 分派：cmp bp,3 与 cmp bp,0xf',
        has(d, 'cmp', 'bp', '3') and has(d, 'cmp', 'bp', '0xf'))

    print('--- 2) 三个分支体都是「显示消息」(共享 0x44df20 + 0x47b900) ---')
    h3 = dis(0x44da10, 0x44da87)
    chk('0x44da10(id3): MSG 基 0x11b9', has(h3, 'add', 'ecx', '0x11b9'))
    chk('0x44da10(id3): 值 = 0x44df20(ctx, byte[ctx+0xb]*10)',
        has(h3, 'call', '0x44df20') and has(h3, 'movzx', 'ebx + 0xb'))
    chk('0x44da10(id3): byte[ctx+0xb]==0 时直接返回', has(h3, 'je'))
    chk('0x44da10(id3): 终以 0x47b900 显示', has(h3, 'call', '0x47b900'))
    h15 = dis(0x44da90, 0x44dae2)
    chk('0x44da90(id15): MSG 0xde6 (B 非空) / 0xde5 (B 空)',
        has(h15, 'push', '0xde6') and has(h15, 'push', '0xde5'))
    chk('0x44da90(id15): 终以 0x47b900 显示', has(h15, 'call', '0x47b900'))
    h7 = dis(0x4441a0, 0x4441f6)
    chk('0x4441a0(state7): MSG 0x57c / 0x1658 / 0x1659',
        has(h7, 'mov', 'edi', '0x57c') and has(h7, 'mov', 'edi', '0x1658')
        and has(h7, 'mov', 'edi', '0x1659'))
    chk('0x4441a0(state7): 判 word[ctx+8]&2', has(h7, 'test', 'bl', '2'))
    chk('0x4441a0(state7): 终以 0x47b900 显示', has(h7, 'call', '0x47b900'))
    chk('三分支体共享 helper 0x44df20',
        all(has(x, 'call', '0x44df20') for x in (h3, h15, h7)))

    print('--- 3) `+0x268` 子记录数组 (0x484f34 id1) ---')
    # geometry: array base this+0x244, stride 48, flags dword at +0x24
    geo_ok = all(0x244 + i*48 + 0x24 == 0x268 + i*48 for i in range(2))
    chk('几何：0x244 + i*48 + 0x24 == 0x268 + i*48 (i=0,1)', geo_ok)
    chk('rec[0] @ this+0x244..0x274, flag @ this+0x268', 0x244 + 0x24 == 0x268)
    chk('rec[1] @ this+0x274..0x2a4, flag @ this+0x298', 0x274 + 0x24 == 0x298)
    f1 = dis(0x484f34, 0x484fa3)
    chk('0x484f34 以 12 个 nop 对齐填充开头',
        all(b == 0x90 for b in data[off(0x484f34):off(0x484f40)]))
    chk('循环仅 2 槽 (cmp cx,2)', has(f1, 'cmp', 'cx', '2'))
    chk('stride 48 = (cx*3)<<4 (lea + shl 4)',
        has(f1, 'lea', 'eax + eax*2') and has(f1, 'shl', 'eax', '4'))
    chk('测 byte[esi + 0x268 + cx*48] bit0 (dl=1)',
        has(f1, 'test', 'esi + 0x268', 'dl') and has(f1, 'mov', 'dl', '1'))
    chk('命中后 edi = this + 0x244 + cx*48', has(f1, 'lea', 'edi', 'esi + 0x244'))
    chk('清 flags bit0: dword[edi+0x24] &= ~1', has(f1, 'and', '0xfffffffe'))
    chk('子记录是 C++ 对象：虚调用 [vptr + 0x14] (=vtable[5])',
        has(f1, 'call', 'edx + 0x14'))
    chk('临界区 0x526c50 (0x4edfa0 / 0x4edf70)',
        has(f1, 'call', '0x4edfa0') and has(f1, 'call', '0x4edf70')
        and has(f1, 'mov', 'ecx', '0x526c50'))

    print('--- 4) 第二组转码表/跳表 (0x485098 / 0x4850a8) ---')
    jt2 = [u32(0x485098 + i*4) for i in range(4)]
    chk('跳表 0x485098 = 4 项且值正确', jt2 == JT_485098)
    chk('跳表紧邻转码表之前 (0x485098+16 == 0x4850a8)', 0x485098 + 4*4 == 0x4850a8)
    tc2 = list(data[off(0x4850a8):off(0x4850a8)+14])
    chk('转码表 0x4850a8 (14B) 值正确', tc2 == TC_4850A8)
    chk('转码表长 14 由其后 nop 填充证实',
        all(b == 0x90 for b in data[off(0x4850b6):off(0x4850b6)+10]))
    f2 = dis(0x484f9f, 0x484fd0)
    chk('二级派发：eax = dword[ctx+4] - 2017 (add 0xfffff81f)',
        has(f2, 'add', 'eax', '0xfffff81f') and 0x100000000 - 0xfffff81f == 2017)
    chk('二级派发：范围 0..13 (cmp eax,0xd ; ja)', has(f2, 'cmp', 'eax', '0xd'))
    chk('二级派发：转码 0x4850a8 -> 跳表 0x485098',
        has(f2, 'mov', '0x4850a8') and has(f2, 'jmp', '0x485098'))
    chk('取值映射 2017..2021->0x48505d / 2022..2028->0x485090 / 2029->0x484fcc / 2030->0x485016',
        all(jt2[tc2[v-2017]] == exp
            for v, exp in [(2017, 0x48505d), (2021, 0x48505d),
                           (2022, 0x485090), (2028, 0x485090),
                           (2029, 0x484fcc), (2030, 0x485016)]))

    print('\nRESULT: %d/%d checks passed' % (PASS, CHECKS))
    return PASS == CHECKS

if __name__ == '__main__':
    import sys
    sys.exit(0 if verify() else 1)
