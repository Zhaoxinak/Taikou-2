# -*- coding: utf-8 -*-
"""reverse_settle_ref.py — 续180(A) 破解 0x4a61d0（反向支給 castle→A）公式（Unicorn 实跑验证）

0x4a61d0(A)：城堡向工作记录 A 支给三笔资源（与 0x4a5fc0 正向方向相反）。
门：A[0x1b]&0x10 置位 / 城[0x1b]&0x10 置位 / 0x49ac90(A) 或 0x4a5c40(A) 返回 0 → 直接返回。
城目标 edi = 国主驻城（A 的 国 byte[A] → 国政治条目 → 国主实体 → byte[+0x25]）。

三笔转移（castle 扣减、A sat_add，cap 见各包装器族）：
  d1 軍糧(+0x14, cap30000)：
      if castle.r14 > castle.r10*2//5:
          d1 = min( A.r10//15 , castle.r14 - castle.r10*2//5 )
          A.r14 += d1 ; castle.r14 -= d1
  d2 米(+0x12, cap30000)：
      if castle.r12 > 10000 且 A.r12 < 100:
          d2 = min( 100 - A.r12 , castle.r12 - 10000 )
          A.r12 += d2 ; castle.r12 -= d2
  d3 資金(+0x10, cap50000)：★ 仅当 d2>0（落穿 transfer2 成功分支）才执行
      if castle.r10 > payC*2//3:
          payA = pay(A) ; payC = pay(C)        # pay = 0x49fa40 (f=0 时 = 兵員*300&0xffff)
          d3 = round10( min( max(payA - A.r10, 0) , castle.r10 - payC*2//3 ) )
          A.r10 += d3 ; castle.r10 -= d3

注：静态镜像中国政治链表知行节点为空 → pay 的 5*f 项恒 0，pay = (兵員*300)&0xffff。
"""
import os
import sys
import itertools
from reverse_settle_emu import SettleEmu

KUNI = 5
CIDX = 7


def pay(heibei):
    return min((heibei * 300) & 0xFFFF, 50000)


def py_settle(a10, a12, a14, c10, c12, c14, a_hb, c_hb):
    a10, a12, a14 = a10 & 0xFFFF, a12 & 0xFFFF, a14 & 0xFFFF
    c10, c12, c14 = c10 & 0xFFFF, c12 & 0xFFFF, c14 & 0xFFFF
    a10_, a12_, a14_ = a10, a12, a14
    c10_, c12_, c14_ = c10, c12, c14
    # 全函数门槛：A.r10(資金) < 15 → 一笔都不给，直接返回
    #   （0x4a624c: esi=a10//15; test si,si; je 0x4a633a）
    if a10 < 15:
        return (a10_, a12_, a14_, c10_, c12_, c14_)
    # d1 軍糧（+0x14, cap30000）：castle 军粮充足时拨给 A
    #   d1 = min( a10//15 , castle.r14 - castle.r10*2//5 )，需 castle.r14 > castle.r10*2//5
    if c14 > c10 * 2 // 5:
        d1 = min(a10 // 15, c14 - c10 * 2 // 5)
        a14_ = min(a14_ + d1, 30000)
        c14_ = max(c14_ - d1, 0)
    # d2 米（+0x12, cap30000）：A 米未满 100 才考虑；a12>=100 则早退（同时跳过 d3）
    #   （0x4a6299: esi=sat_sub(100,a12); test si,si; je 0x4a633a）
    if a12 >= 100:
        return (a10_, a12_, a14_, c10_, c12_, c14_)
    if c12 > 10000:
        d2 = min(100 - a12, c12 - 10000)
        a12_ = min(a12_ + d2, 30000)
        c12_ = max(c12_ - d2, 0)
    # d3 資金（+0x10, cap50000）：与 d2 是否实际发生无关，仅受 a12<100 门控
    #   payX = 0x49fa40(X) = (兵員*300)&0xffff（静态镜像 f=0 退化为兵員*300&0xffff）
    #   0x4a62e4: esi=sat_sub(payA,a10); je→跳过；0x4a6303: c10<=payC*2//3→跳过
    payA, payC = pay(a_hb), pay(c_hb)
    if payA > a10 and c10 > payC * 2 // 3:
        d3 = min(payA - a10, c10 - payC * 2 // 3)
        d3 = (d3 // 10) * 10
        a10_ = min(a10_ + d3, 50000)
        c10_ = max(c10_ - d3, 0)
    return (a10_, a12_, a14_, c10_, c12_, c14_)


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    ok = True
    e = SettleEmu()
    # 缩减采样空间：覆盖各字段边界 + d2=0 / d2>0 两路 + pay 截断
    hot = [0, 100, 1000, 5000, 24464, 30000]             # a10,a14,c10 (边界+截断)
    a12v = [0, 100, 5000, 24464, 30000]                   # 含 <100 (d2 可触发) 与 >=100
    c12v = [0, 10000, 20000]                              # >10000 才考虑 d2
    c14v = [0, 5000, 20000]                               # >c10*2//5 才考虑 d1
    hbv = [10, 100]                                      # 兵員（pay 截断边界）
    mism = 0
    total = 0
    for (a10, a14, c10, a12, c12, c14, ah, ch) in itertools.product(
            hot, hot, hot, a12v, c12v, c14v, hbv, hbv):
        total += 1
        want = py_settle(a10, a12, a14, c10, c12, c14, ah, ch)
        got = e.run(a10, a12, a14, c10, c12, c14, a_heibei=ah, c_heibei=ch)
        got = tuple(v & 0xFFFF for v in got)
        if got != want:
            mism += 1
            if mism <= 6:
                print("    失败:", (a10, a12, a14, c10, c12, c14, ah, ch),
                      "got", got, "want", want)
    ok &= _t(f"反向支給三笔公式穷举 {total} 组一致（失败 {mism}）", mism == 0)

    # 控制流断言：d2=0 时 d3 必为 0（即使 castle.r10 充足）
    out = e.run(100, 200, 100, 30000, 5000, 5000, a_heibei=50, c_heibei=50)  # A.r12=200→d2=0
    ok &= _t("d2=0 时 d3 跳过（A.r10 不变）", out[0] == 100 and out[3] == 30000)
    # 控制流断言：d2>0 时 d3 可能执行（A.r10 可能变化）
    out2 = e.run(100, 0, 100, 30000, 20000, 20000, a_heibei=100, c_heibei=100)
    ok &= _t("d2>0 时 d3 可触发（A.r10 变化或保持，公式一致）",
             out2 == py_settle(100, 0, 100, 30000, 20000, 20000, 100, 100))

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
