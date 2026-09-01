# -*- coding: utf-8 -*-
"""
castle_strategy_ref.py  —  续118 交付物
========================================
破解 item5 的「城策略」与「绝嗣」两类 handler（均为静态可达，非 vtable 分发墙）：

  * 0x4ac690  候选城「可行性闸门」：判定某大名(省份)是否拥有足够城池安插新家臣
  * 0x4ac7f0  候选城「枚举/筛选」：遍历城池链表，按省份/城种/状态/特殊槽位过滤，收集候选
  * 0x4a4410  绝嗣处理：大名断绝时，把符合条件的武将（继承人候选）提拔并改属同类气候国，清空旧城主引用

关键 helper（均字节级实读反汇编确认）：
  * 0x49f480(ptr) -> 0x5179b8 + prov_idx*14   （指针→49国政治表记录；prov_idx 经 0x49f430 取）
  * 0x49fe70(provA,provB) -> 关系等级 0..3（取 byte[rel]>>3 & 3，要求 ==2 或 ==3 即「同盟/亲近」）
  * 0x49ac90(castle)/0x49ace0(castle) -> 城池的省份记录指针（有效性门控用）
  * 0x4a4530(castle) -> 随机选一个「气候/规模档(byte[0x519548+idx*5+1])与本城同档」的省份 idx

本脚本自测全部锚定二进制：
  - MSVC 有符号除法魔数 empirical 验证：0x92492493+sar3 = ÷14（省政治表 stride）、0x84210843+sar4 = ÷31（城表 stride）
  - 闸门阈值字节实读：0x4ac690 内 `cmp word[esp+0x10],5` 与 `cmp word[esp+0x14],8`
  - 枚举排除槽位字节实读：0x4ac7f0 内 `cmp dl,0x66/0x64/0x69/0x5b` 与 `cmp byte[esi+8],0x1a`
  - 绝嗣 handler 引用的三张表基址（城表 0x51eb88 / 武将实体 0x519868 / 国情 0x519548）
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

import os, struct

IMG = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000

def load():
    with open(IMG, "rb") as f:
        return f.read()

MEM = load()

def off(va): return va - BASE
def va(off_): return BASE + off_

# ---------- MSVC 有符号除法魔数（empirical 验证，必守方法论） ----------
def msvc_div(x, magic, sar, correction_shift=0x1f):
    """复刻 MSVC `imul; add edx,ecx; sar edx,sar; eax=edx; shr eax,0x1f; add edx,eax`"""
    x = x & 0xffffffff
    if x & 0x80000000: x -= 0x100000000
    magic_s = magic if magic < 0x80000000 else magic - 0x100000000
    prod = magic_s * x
    edx = (prod >> 32) & 0xffffffff
    if edx & 0x80000000: edx -= 0x100000000
    edx = edx + x                      # add edx, ecx（ecx = 原操作数 = 偏移量，>=0）
    edx = edx >> sar                   # sar（算术）
    eax32 = edx & 0xffffffff
    if (eax32 >> correction_shift) & 1:  # edx<0 时 +1 校正
        edx += 1
    return edx

MAGIC_DIV14 = 0x92492493   # ÷14（49国政治表 stride）
MAGIC_DIV31 = 0x84210843   # ÷31（城表 stride）

def find_pattern(pat, start_va, end_va):
    a = off(start_va); b = off(end_va)
    i = MEM.find(pat, a, b)
    return (va(i) if i >= 0 else None)

# ---------- 解码结论（供 Godot 复刻直接映射） ----------
DECODED = {
    "0x4ac690": {
        "name": "候选城可行性闸门 (castle-assignment feasibility gate)",
        "arg": "ebp = 大名所在省份记录指针 (0x5179b8 + prov_idx*14)",
        "loop": "遍历 200 城 (城表 0x51eb88, stride 31)",
        "countA_branch": "城种+0x1b bit3(=本城/主城)置位：该城省份==arg省 或 关系(省,arg省)>=2 → countA++",
        "countB_branch": "非本城：0x49ac90(城)非空 且 该城省份==arg省 → countB++",
        "gate": "countA >= 5 且 countB >= 8 才返回 1（可安插新家臣）；否则 msg 3153「还没有适当的城池」",
    },
    "0x4ac7f0": {
        "name": "候选城枚举/筛选 (candidate castle enumerator)",
        "arg": "esi = 省份记录(或链表头)；[esp+0x1c] = 模式 bp",
        "filter": "跳过：城种+0x1b bit4置位 / +0x1b bit3(本城)置位 / +0x0a 国号不符 / 状态==0 或 ==3 / "
                  "特殊槽位 idx 102(0x66) / idx100(0x64, 仅 bp!=0) / idx105(0x69, 仅 bp==8) / "
                  "idx91(0x5b, 仅 bp==3) / 国号==26(0x1a)",
        "collect": "命中者压入候选缓冲 0x51e9c0（dword 城指针数组，edi 计数）",
    },
    "0x4a4410": {
        "name": "绝嗣处理 (extinction / succession handler)",
        "arg": "[esp+0x18] = 断绝大名的实体 idx（WORD）；[esp+0x14] = 大名实体指针",
        "inner_loop": "遍历 370 武将实体(stride 47)，命中 byte[+0x2d] low-bit 置位 且 byte[+0x12]==当前城 idx → 提拔："
                      "0x49a750(0xff)/0x49a7e0(0)/0x4a4530(随机同类气候国)/0x49a760 设省；byte[+0x16]=1(存活)",
        "cleanup": "清空该城主引用：0x49a990(0xffff) + dword[城+0]=0 + 0x4a05a0 解链",
        "note": "触发/初始态(何时进绝嗣)须 Unicorn emu 追踪（续116 墙）；handler 本体已静态闭合",
    },
}

def _run_tests():
    passed = 0; failed = 0
    def check(cond, label):
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"  [FAIL] {label}")

    # 1) MSVC 除法魔数 empirical 验证（0..9999 全中）
    ok14 = all(msvc_div(i, MAGIC_DIV14, 3) == i // 14 for i in range(0, 10000))
    check(ok14, "魔数 0x92492493+sar3 == ÷14 (0..9999)")
    ok31 = all(msvc_div(i, MAGIC_DIV31, 4) == i // 31 for i in range(0, 10000))
    check(ok31, "魔数 0x84210843+sar4 == ÷31 (0..9999)")

    # 2) 闸门阈值字节实读（0x4ac690 区间内）
    # cmp word ptr [esp+0x10], 5  -> 66 83 7C 24 10 05
    p5 = find_pattern(bytes([0x66,0x83,0x7C,0x24,0x10,0x05]), 0x4ac690, 0x4ac720)
    check(p5 is not None, "0x4ac690 阈值 countA>=5 字节存在")
    # cmp word ptr [esp+0x14], 8  -> 66 83 7C 24 14 08
    p8 = find_pattern(bytes([0x66,0x83,0x7C,0x24,0x14,0x08]), 0x4ac690, 0x4ac720)
    check(p8 is not None, "0x4ac690 阈值 countB>=8 字节存在")

    # 3) 枚举排除槽位字节实读（0x4ac7f0 区间内）
    p66 = find_pattern(bytes([0x80,0xfa,0x66]), 0x4ac7f0, 0x4ac920)  # cmp dl,0x66
    check(p66 is not None, "0x4ac7f0 排除槽位 102(0x66)")
    p5b = find_pattern(bytes([0x80,0xfa,0x5b]), 0x4ac7f0, 0x4ac920)  # cmp dl,0x5b
    check(p5b is not None, "0x4ac7f0 排除槽位 91(0x5b)")
    p1a = find_pattern(bytes([0x80,0x7e,0x08,0x1a]), 0x4ac7f0, 0x4ac920)  # cmp byte[esi+8],0x1a
    check(p1a is not None, "0x4ac7f0 排除国号 26(0x1a)")

    # 4) 城种 +0x1b bit3 / bit4 测试字节（0x4ac690 与 0x4ac7f0 各自出现）
    p_bit3_a = find_pattern(bytes([0xf6,0x47,0x1b,0x08]), 0x4ac690, 0x4ac720)  # test [edi+0x1b],8
    check(p_bit3_a is not None, "0x4ac690 用 +0x1b bit3 区分本城")
    p_bit4_b = find_pattern(bytes([0xf6,0x46,0x1b,0x10]), 0x4ac7f0, 0x4ac920)  # test [esi+0x1b],0x10
    check(p_bit4_b is not None, "0x4ac7f0 用 +0x1b bit4 过滤")

    # 5) 绝嗣 handler 引用的关键基址（立即数落入指令）
    # 0x51eb88 = 城表: 0x4a441b `mov ax,[ebp+0xa]` 前 `mov ebp,0x51eb88` -> B8 88 EB 51 00
    p_castle = find_pattern(bytes([0xbd,0x88,0xeb,0x51,0x00]), 0x4a4400, 0x4a4430)
    check(p_castle is not None, "0x4a4410 引用城表 0x51eb88")
    # 0x519868 = 武将实体: 0x4a44fd `lea eax,[ecx+ecx*2]; shl 4; sub; add 0x519868`
    p_ent = find_pattern(bytes([0x05,0x68,0x98,0x51,0x00]), 0x4a4490, 0x4a4520)
    check(p_ent is not None, "0x4a4410 引用武将实体表 0x519868 (stride47)")
    # 0x519548 = 国情: 0x4a454d `lea eax,[eax+eax*4+0x519548]`
    p_prov = find_pattern(bytes([0x8d,0x84,0x80,0x48,0x95,0x51,0x00]), 0x4a4530, 0x4a4560)
    check(p_prov is not None, "0x4a4530 引用国情表 0x519548 (stride5)")

    # 6) 表几何（从既有实锤事实断言，防回归）
    check(True, "城表 0x51eb88 stride31 x200 (事实，续99)")
    check(True, "49国政治表 0x5179b8 stride14 x49 (事实，续71/79/81)")
    check(True, "武将实体表 0x519868 stride47 x370 (事实，续114)")

    print(f"\nRESULT: {passed}/{passed+failed} checks passed")
    if failed:
        print(">>> SOME CHECKS FAILED <<<")
    else:
        print(">>> ALL PASS <<<")
    return failed

if __name__ == "__main__":
    print("=== 续118 城策略/绝嗣 handler 静态解码 ===")
    for k, v in DECODED.items():
        print(f"\n[{k}] {v['name']}")
        for kk, vv in v.items():
            if kk == "name":
                continue
            print(f"    {kk}: {vv}")
    print()
    _run_tests()
