# -*- coding: utf-8 -*-
# diplomacy3_ref.py — 太阁立志传2 外交系统 续95 补充参考实现
# 主题: 关系变好写入点 + 外交成败确定性判定 (纠偏「随机失败分支」)
#
# 已破译事实 (capstone 反汇编 + 全映像 e8 扫描, 2026-08-29):
#   * 关系矩阵 REL_MATRIX = 0x51dc60, 49*48/2 = 1176 字节, 上三角, 每国对1字节
#     位域: bit0-2 = 外交関係 8 级 (0..7), bit3-4 = 主从関係 4 级 (0..3, 2/3 镜像)
#   * set_diplo 0x49fe40(a,b,new): 只改 bit0-2
#   * set_lord 0x49ff10(a,b,new): 只改 bit3-4, 存储时 2<->3 镜像 (i>j 反转)
#   * 友好外交成功 0x4b5bcb:
#        lv = (type<2)? diff(1,type) : (type==2 ? 0 : 2)      # diff(a,b)=(a>b)?a-b:0 @0x4ebcd0
#        set_diplo(target, me, lv); set_lord(target, me, 1)    # 1 = 同盟
#        成败: call 0x47bed0 -> 0x47be00 确定性跳表 (无 RNG), 返回非0 = 失败
#        消息 0xb01 / 0xb02
#   * 高压外交成功/屈服 0x4b6095:
#        lv = (type<3)? diff(1,type) : 2
#        set_diplo(target, me, lv); set_lord(target, me, 3)    # 3 = 支配/屈服
#        成败: call 0x47b5f0 恒返回 1 (无随机失败)
#        消息 0xaeb / 0xb08
#   * 崛起/同盟事件 0x416a60: set_diplo(目标,源, lv 或 7-lv)  (lv=维持, 7-lv=反转)
#   * 通用数学: 0x4ebcd0 = diff(a,b)=(a>b)?a-b:0 ; 0x4ebcf0=min(a+b,c) ; 0x4ebd10=字节差
#   * RNG = 0x4ebd30 (LCG: eax=[0x50de48]; imul 0x41c64e6d; add 0x3039) — 不在外交成败路径
#
# 纠偏 (vs 续92/续95 误读):
#   - 续95 的 "高压外交失败分支随机数比较点" 不存在: 高压外交恒成功, 友好外交成败为
#     确定性跳表 (0x47be00), 均不经 RNG。续95 把 0x4b956e (收集情报工作 lv 判定, 给功勋)
#     误当成外交成败判定。
#   - 关系变好的写入点不是 "get+dec 1级", 而是固定 set 到友好/同盟/支配等级。

import struct, sys, os

MEM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_unpacked_mem.bin")
BASE = 0x400000
REL_MATRIX = 0x51dc60
CLAN_TABLE = 0x5179b8
STRIDE = 14
N_CLAN = 49
N_LEVEL = 8          # 外交関係 8 级
N_LORD = 4           # 主从関係 4 级

mem = bytearray(open(MEM_PATH, "rb").read())

# ---- 国指针 / 索引 ----
def clan_ptr(i):
    return CLAN_TABLE + i * STRIDE

def clan_index(ptr):
    if ptr is None:
        return N_CLAN          # 哨兵: 用于 lookup 越界判定
    return (ptr - CLAN_TABLE) // STRIDE

# ---- 上三角关系矩阵寻址 (0x49fd80) ----
def rel_lookup(a, b):
    i = clan_index(a)
    j = clan_index(b)
    if i >= N_CLAN or j >= N_CLAN or i == j:
        return None
    if i > j:
        i, j = j, i
    # 三角累加: 48*i - i*(i-1)/2 + j - i
    ecx = 48 * i - i * (i - 1) // 2
    off = ecx + (j - i)
    return REL_MATRIX + off

def get_diplo(a, b):
    rec = rel_lookup(a, b)
    if rec is None:
        return 0
    return mem[rec - BASE] & 7

def get_lord_raw(a, b):
    rec = rel_lookup(a, b)
    if rec is None:
        return 0
    return (mem[rec - BASE] >> 3) & 3

def get_lord(a, b):
    """带 2<->3 镜像 (0x49fe70)."""
    v = get_lord_raw(a, b)
    i, j = clan_index(a), clan_index(b)
    if i > j:
        v = 5 - v if v in (2, 3) else v
    return v

# ---- setter (位域) ----
def set_diplo(a, b, new):
    rec = rel_lookup(a, b)
    if rec is None:
        return
    cur = mem[rec - BASE]
    new &= 7
    patched = (cur ^ ((cur ^ new) & 7)) & 0xff
    mem[rec - BASE] = patched

def set_lord(a, b, new):
    rec = rel_lookup(a, b)
    if rec is None:
        return
    i, j = clan_index(a), clan_index(b)
    v = new & 3
    if i > j and v in (2, 3):          # 存储镜像
        v = 5 - v
    cur = mem[rec - BASE]
    patched = (cur & 0xe7) | ((v & 3) << 3)
    mem[rec - BASE] = patched

# ---- 通用数学 ----
def diff(a, b):
    """0x4ebcd0: (a>b)? a-b : 0"""
    a &= 0xffff; b &= 0xffff
    return (a - b) if a > b else 0

def min_trunc(a, b, c):
    """0x4ebcf0: min(a+b, c)"""
    s = (a & 0xff) + (b & 0xff)
    return s if s < c else c

# ---- 外交成功关系变更 (续95 写入点) ----
def friendly_success(work_type, target, me):
    """0x4b5bcb 友好外交成功: set_lord=1(同盟), set_diplo=lv."""
    if work_type < 2:
        lv = diff(1, work_type)
    elif work_type == 2:
        lv = 0
    else:
        lv = 2
    set_diplo(target, me, lv)
    set_lord(target, me, 1)         # 1 = 同盟
    return lv

def pressure_success(work_type, target, me):
    """0x4b6095 高压外交/屈服成功: set_lord=3(支配), set_diplo=lv."""
    lv = diff(1, work_type) if work_type < 3 else 2
    set_diplo(target, me, lv)
    set_lord(target, me, 3)         # 3 = 支配/屈服
    return lv

# ---- 成败判定 (确定性, 无 RNG) ----
def pressure_succeeds():
    """0x47b5f0: 恒返回 1 (无随机失败)."""
    return True

def friendly_decision(work_type):
    """0x47be00 确定性跳表: 工作类型有效(0<type<=0xc)且非越界则成败由条件定.
    简化模型: type 在 [1,0xc] 内即进入判定 (返回非0 = 失败标记含义见注);
    这里只建模 '工作类型窗口' 校验, 不臆测跳表内部逐档语义."""
    return 0 < work_type <= 0xc

# ================= 自校验 =================
def _run_tests():
    ok = tot = 0
    def chk(name, cond):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
        else:
            print(f"  [NG] {name}")

    # diff
    chk("diff(5,2)=3", diff(5, 2) == 3)
    chk("diff(1,2)=0", diff(1, 2) == 0)
    chk("diff(0xffff,0)=0xffff", diff(0xffff, 0) == 0xffff)
    chk("diff(3,3)=0", diff(3, 3) == 0)
    # min_trunc
    chk("min_trunc(10,5,20)=15", min_trunc(10, 5, 20) == 15)
    chk("min_trunc(10,20,25)=25", min_trunc(10, 20, 25) == 25)

    # 三角寻址 (穷举小规模断言)
    for a in range(N_CLAN):
        for b in range(a + 1, N_CLAN):
            i, j = a, b
            ecx = 48 * i - i * (i - 1) // 2
            off = ecx + (j - i)
            chk(f"idx a={a},b={b}", rel_lookup(clan_ptr(a), clan_ptr(b)) == REL_MATRIX + off)
            # 交换对称
            chk(f"sym a={a},b={b}",
                rel_lookup(clan_ptr(a), clan_ptr(b)) == rel_lookup(clan_ptr(b), clan_ptr(a)))

    # set/get round-trip + 位域不干扰
    a, b = clan_ptr(2), clan_ptr(7)
    for d in range(8):
        set_diplo(a, b, d)
        chk(f"diplo rt d={d}", get_diplo(a, b) == d)
    for l in range(4):
        set_lord(a, b, l)
        chk(f"lord rt l={l}", get_lord(a, b) == l)
        chk(f"diplo保留 d=7 after lord l={l}", get_diplo(a, b) == 7)
    set_diplo(a, b, 0)
    chk("diplo保留 after reset", get_diplo(a, b) == 0)
    chk("lord保留 after diplo reset", get_lord(a, b) == 3)

    # 镜像: set_lord(支配=3) 在 i>j 时存储为 2, get 还原 3
    a2, b2 = clan_ptr(9), clan_ptr(3)   # i>j
    set_lord(a2, b2, 3)
    chk("lord mirror store", get_lord_raw(a2, b2) == 2)
    chk("lord mirror get", get_lord(a2, b2) == 3)
    set_lord(a2, b2, 2)                 # 存储 3 (被支配)
    chk("lord mirror2 store", get_lord_raw(a2, b2) == 3)
    chk("lord mirror2 get", get_lord(a2, b2) == 2)

    # 友好外交成功: set_lord=1 (同盟)
    t, m = clan_ptr(5), clan_ptr(1)
    lv = friendly_success(0, t, m)
    chk("friendly lv(type0)", lv == diff(1, 0))
    chk("friendly lord=1", get_lord(t, m) == 1)
    lv2 = friendly_success(5, t, m)
    chk("friendly lv(type5)=2", lv2 == 2)
    chk("friendly lord stays 1", get_lord(t, m) == 1)
    # 高位主从不影响外交位
    chk("friendly diplo lv preserved", get_diplo(t, m) == 2)

    # 高压外交成功: set_lord=3 (支配)
    t3, m3 = clan_ptr(8), clan_ptr(2)
    lv3 = pressure_success(0, t3, m3)
    chk("pressure lv(type0)", lv3 == diff(1, 0))
    chk("pressure lord=3", get_lord(t3, m3) == 3)
    lv4 = pressure_success(4, t3, m3)
    chk("pressure lv(type4)=2", lv4 == 2)
    chk("pressure lord stays 3", get_lord(t3, m3) == 3)

    # 成败判定模型
    chk("pressure always succeeds", pressure_succeeds() is True)
    chk("friendly window 1 ok", friendly_decision(1) is True)
    chk("friendly window 0xc ok", friendly_decision(0xc) is True)
    chk("friendly window 0 fail", friendly_decision(0) is False)
    chk("friendly window >0xc fail", friendly_decision(0xd) is False)

    print(f"\nRESULT: {ok}/{tot} checks passed")
    return ok == tot

if __name__ == "__main__":
    sys.exit(0 if _run_tests() else 1)
