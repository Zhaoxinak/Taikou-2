#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事件 id2/id3 handler `0x461510` + 行商（馬 / 洋枪）購買サブシステム —— 结构参考 + 自测。

Static only (capstone disasm + byte reads of _unpacked_mem.bin). No emulation.

Closes MEMORY 仍待破 ④ 的最后一项「事件 id2 尾跳目标 `0x461510` 的供给者」。
续129 的教训再次应验：**先静态把整条链反汇编出来，不要急着下「须 emu」结论** ——
本项原判「须 Unicorn」，实际纯静态 100% 闭合，且顺带纠偏一处**误反汇编**。

===============================================================================
0) 🔴 纠偏：`0x461510` 根本不是「thunk」
===============================================================================
§3.7.16 原记「★ thunk … `0x461510`(id 2)：`push eax; push 0xfd1; ret` → 跳往 `[esp+4]`」
是**误反汇编**（从错误偏移起解，把 `call 0x460bf0` 的机器码 e8 尾部当成了 ret）。
真实函数体（入口 0x461510，前接 7 个 nop 对齐填充 0x461509..0x46150f）：

    0x461510: call 0x49f6b0             ; getCtx → eax = ctx (0x516610)
    0x461515: mov  ax, word[eax]        ; ctx[+0] = 事件 id
    0x461518: cmp  ax, 2 ; jne 0x46153e
      ── id 2（買馬）──
    0x46151e: mov  eax, dword[esp+4]    ; ★ 参数 = 数量 n（out 值）
    0x461522: push eax                  ; cdecl：后压者为第 1 参
    0x461523: push 0xfd1                ; ⇒ 0x460bf0(msgid=0xfd1, n)
    0x461528: call 0x460bf0             ;   居中对话框「购买%u匹马。」
    0x46152d: mov  ecx, dword[0x52063c]
    0x461533: add  esp, 8
    0x461536: push 0xfd9                ; 「好吧，我会把马匹安全送到您的城中…」
    0x46153b: push ecx
    0x46153c: jmp  0x461561             ; → 共同尾（0x47b900）
      ── id 3（買洋枪）──
    0x46153e: cmp  ax, 3 ; jne 0x461569  ; id 非 2/3 ⇒ 只走共同尾
    0x461544: mov  edx, dword[esp+4]
    0x461548: push edx ; push 0xfdd ; call 0x460bf0   ; 「得到了洋枪%u支。」
    0x461553: mov  eax, dword[0x52063c]
    0x46155b: push 0xfe4                ; 「那么再见了，武士大人。祝您武运昌隆。」
    0x461560: push eax
      ── 共同尾 ──
    0x461561: call 0x47b900 ; add esp, 8             ; show_MSG(対象, msgid)
    0x461569: call 0x4af1c0                          ; 商人退场/刷新
    0x46156e: push 0xfbe ; call 0x49f5e0 ; push eax
    0x461579: call 0x47b900 ; add esp, 8             ; 玩家：「┅┅跑得真快…消失了┅┅。」
    0x461581: ret

⇒ **不存在「调用方供给的函数指针」**，`dword[esp+4]` 是一个 **u16/32 数量值**。

===============================================================================
1) 供给者链（原「仍待破 ④」的答案）
===============================================================================
    0x461410  馬屋主流程 ─┬─ byte[[0x52063c]+7] >= 2 → 0x461590(&out)  常連
                         └─                     < 2 → 0x461710(&out)  新規
    0x4619ec  洋枪主流程 ─┬─ byte[[0x52063c]+7] >= 2 → 0x461a30(&out)  常連
                         └─                     < 2 → 0x461b00(&out)  新規
    （两个主流程同构；`[0x52063c]` = 当前対象，其 `+7` = 行商来访次数 0..3）
    if (eax != 0) { 0x461510(out); 0x461490(); }

    out 值最终来自数值输入窗口：
      0x461590/0x461710/0x461a30/0x461b00
        → 0x461660(price, max/10, 0, use_helper)
            → 0x45cdf0(ctx[+4], max/10, price)
                → 0x47bd10(0x513ea8, 10, cap, 0, -1)   ← 数值输入窗口，返回数量
                                                          （取消 = 0x7fffffff）

===============================================================================
2) 四档行商参数表（价格/上限由 MSGX 台词逐条实锤）
===============================================================================
| 商品 | 档位 | 例程   | 开场 MSG        | 门槛(貫) | 価格(貫/10個) | 上限(個) | 詐欺事件   |
|------|------|--------|-----------------|----------|---------------|----------|------------|
| 馬   | 常連 | 0x461590 | 0xfcd+0xfce   | >= 2     | 2             | 100      | —          |
| 馬   | 新規 | 0x461710 | 0xfd2         | >= 1     | 1             | 500      | 0x461900 指鹿为马 |
| 洋枪 | 常連 | 0x461a30 | 0xfdb+0xfdc   | >= 15    | 15            | 300      | —          |
| 洋枪 | 新規 | 0x461b00 | 0xfde         | >= 10    | 10            | 1000     | 0x461cf0 黑竹竿   |
| 馬   | 詐欺後 | 0x4618bd | 0xfd6→0xfd7 | >= 50    | 50            | 50       | —          |
| 洋枪 | 詐欺後 | 0x461cb0 | 0xfe2→0xfe3 | >= 50    | 50            | 50       | —          |

`0x461660(a0=価格, a1=上限/10, a2=0, a3=是否经 helper 记账)`：
  - a3 == 1（常連/詐欺後）→ 在 0x461660 内部调 `0x4616d0(num*price/10, num)` 记账；
  - a3 == 0（新規）→ 例程内联做同一件事（0x4617c3 / 0x461bb3）。
  ⇒ 两条路完全等价，只是编译器内联与否的差别。

`0x4616d0(cost, num)`：
    ctx[+6] += num / 10            ; 累積購入（10 個単位）
    0x44e5f0(cost)                 ; 扣款：ctx[+4] = 0x4ebcd0(ctx[+4], cost)，再 0x493e50(0x524d50) 刷新金额显示

`0x45cdf0(a=ctx[+4], b=上限/10, c=価格)` 求「钱够买多少」的上限：
    money01 = 10*ctx[+4] + word[0x51662e]        ; 所持金，0.1 貫（100 文）単位
    cap     = 10 * ( ( (money01 / c) / 10 ) )    ; 先除价、再去个位、再 ×10
    最终上限 = min(10*b, cap)                    ; 16-bit 比较 `cmp bx,di`
  ⚠️ `word[0x51662e]` 与 `ctx[+4]` 的货币单位由「门槛式 `word[0x51662e]/10 + ctx[+4] >= price`」
     与「上限式」反推一致（ctx[+4] = 貫、0x51662e = 0.1 貫の位 0..9），属 MEDIUM 置信，
     待运行时实测一枚即可钉死（不影响结构）。

`0x47bd10(0x513ea8, 10, cap, 0, -1)` = 数值输入窗口配置器：
    [0x524188] = 0x513ea8      ; 绑定变量
    [0x524182] = 10            ; 步长（一次 10 匹 / 10 支）
    [0x52417e] = cap           ; 上限
    [0x52417a] = (a4 == -1 ? a1 : a4) = 10   ; 下限
    flags 按 cap 的位数置位（<100000→0x20 / <10000→0x10 / <1000→8 / <100→4 / <10→2）
    → 0x488f60(ecx=0x523d68, flags)    ; 开窗口

===============================================================================
3) 詐欺事件（只有「新規」档位会踩）
===============================================================================
`0x461900`（馬・指鹿为马）/ `0x461cf0`（洋枪・黑竹竿）同构：
    ebp = 0x49f5e0()                ; 玩家 A
    edi = score(A)                  ; 0x461980（馬）/ 0x461d70（洋枪）
    ebx = 0x49f610()                ; 随从 B（可为空）
    esi = score(B) if B else 0
    if (0x4ebe40(max(edi, esi)))    ; ★ 概率门 = (rand()%100) < p
        if (edi >= esi) → MSG 0xfd4 / 0xfe0（玩家自己发现）   return 1
        else            → MSG 0xfd5 / 0xfe1（随从提醒）       return 1
    return 0                        ; 未发现 → 正常成交

    能力评分（★ 技能名表 `0x507b58` 逐字节实锤，见自测）：
      0x461980(p): (byte[p+0xc] / 3) * (((byte[p+0x0f] >> 2) & 3) + 1)
                   └ 内政 /3       └ 技能 #1 = **马术**
      0x461d70(p): (byte[p+0xc] / 3) * (((byte[p+0x10] >> 4) & 3) + 1)
                   └ 内政 /3       └ 技能 #7 位域 → 技能索引 6 = **洋枪**
    ⇒ 「识破假马」看马术、「识破假枪」看洋枪，语义自洽，反过来坐实了
      实体 `+0x0f`~`+0x11` 的 10 技能 2-bit 位序（skill#1 @ +0x0f bits2-3、
      skill#6 @ +0x10 bits4-5）。

命中诈欺后：显示 0xfd6/0xfe2（商人辩解）→ 重开数值窗口，价格抬到 **50 貫/10 個、上限 50**。

===============================================================================
4) 成交后 `0x461490`（两个主流程共用）
===============================================================================
    0x49bfe0(対象, 0xff)                             ; 收尾消息
    byte[対象 + 7] = min(byte[対象 + 7] + 1, 3)      ; 来访次数 +1，上限 3
    if (word[ctx + 6] >= 0x1e)  FIRE(1)              ; 累積購入(10 個単位) >= 30 触发事件
    if (byte[0x523a14] & 2) 0x4eeda0(0x526c58, 0x5239f0), 0x4869b0(0x5239f0)
    0x4a0d50(1, 1)

⇒ 行商的价格档随来访次数升高（0..1 次＝新規・便宜但有诈欺；2..3 次＝常連・贵但无诈欺）。

===============================================================================
5) 魔数除数（全部数值实测，不靠眼估）
===============================================================================
    0x66666667 + sar 2  = ÷10     （0..20000 全等，0 mismatch）
    0x55555556 (high+sign) = ÷3   （0..20000 全等）
    0x10624dd3 + sar 7  = ÷2000   （0..6210 全等；0x493500 的 file = id/2000）
  与续96 的警告同源：`0x66666667` + `sar 3` 才是 ÷20，位移量决定除数。
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


import io
import json
import os
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, 'rb').read()
BASE = 0x400000


def off(va):
    return va - BASE


def u32(va):
    return struct.unpack('<I', data[off(va):off(va) + 4])[0]


_md = Cs(CS_ARCH_X86, CS_MODE_32)
_md.detail = False


def dis(va0, va1):
    """线性反汇编 [va0, va1)，返回 [(mnemonic, op_str), ...]"""
    out = []
    for ins in _md.disasm(data[off(va0):off(va1)], va0):
        out.append((ins.mnemonic, ins.op_str))
    return out


def has(seq, mnem, *subs):
    for m, o in seq:
        if m != mnem:
            continue
        if all(s in o for s in subs):
            return True
    return False


CHECKS = PASS = 0


def chk(name, cond):
    global CHECKS, PASS
    CHECKS += 1
    if cond:
        PASS += 1
        print('  [OK] %s' % name)
    else:
        print('  [NG] %s' % name)
    return bool(cond)


# --------------------------------------------------------------------------
# 结构化事实（复刻用）
# --------------------------------------------------------------------------

HANDLER_461510 = {
    'entry': 0x461510,
    'kind': 'effect',          # 不是 thunk：无尾跳、无调用方供给的函数指针
    'ids': (2, 3),
    'arg': '数量 n（匹 / 支），来自数值输入窗口 0x47bd10',
    'arg_type': 'u32（& 0xffff 使用）',
    'branches': {
        2: {'box_msgid': 0xfd1, 'then_msgid': 0xfd9},
        3: {'box_msgid': 0xfdd, 'then_msgid': 0xfe4},
    },
    'common_tail': {'helper': 0x4af1c0, 'final_msgid': 0xfbe, 'speaker': 0x49f5e0},
}

# 六个数值窗口调用点：例程 → (a0=価格, a1=上限/10, a2, a3)
SPINNER_CALLS = {
    0x461619: dict(goods='馬', tier='常連', price=2, max10=10, use_helper=1),
    0x46178a: dict(goods='馬', tier='新規', price=1, max10=50, use_helper=0),
    0x4618c5: dict(goods='馬', tier='詐欺後', price=50, max10=5, use_helper=1),
    0x461ab9: dict(goods='洋枪', tier='常連', price=15, max10=30, use_helper=1),
    0x461b7a: dict(goods='洋枪', tier='新規', price=10, max10=100, use_helper=0),
    0x461cb8: dict(goods='洋枪', tier='詐欺後', price=50, max10=5, use_helper=1),
}

# 行商分档例程
MERCHANT_ROUTINES = {
    0x461590: dict(goods='馬', tier='常連', min_kan=2, msgs=(0xfcd, 0xfce),
                   poor=(0xfcf, 0xfd0), scam=None),
    0x461710: dict(goods='馬', tier='新規', min_kan=1, msgs=(0xfd2,),
                   poor=(0xfcf, 0xfd3), scam=0x461900),
    0x461a30: dict(goods='洋枪', tier='常連', min_kan=15, msgs=(0xfdb, 0xfdc),
                   poor=(0xfcf, 0xfd0), scam=None),
    0x461b00: dict(goods='洋枪', tier='新規', min_kan=10, msgs=(0xfde,),
                   poor=(0xfcf, 0xfdf), scam=0x461cf0),
}

MSG_TEXTS = {
    0xfcc: '┅┅武士大人，武士大人。您是在找马匹吗？',
    0xfcd: '对前来惠顾的武士大人，我们负责售后运输…',
    0xfce: '10匹马2贯钱。最多可以购买100匹。',
    0xfcf: '糟糕，钱不够了┅┅。',
    0xfd0: '只有这么点钱，武士大人真是辛苦啊。',
    0xfd1: '购买%u匹马。',
    0xfd2: '10匹马1贯钱。最多可以购买500匹。',
    0xfd3: '什么，像您这么一贫如洗的武士大人…',
    0xfd4: '噢，这么多马┅┅嗯？这是什么？其中竟混杂着鹿！',
    0xfd5: '大人，这┅┅居然指鹿为马…',
    0xfd6: '马是四条腿，鹿也是四条腿…这次就分开交易。',
    0xfd7: '那么10匹马50贯钱，最多可以购买50匹。',
    0xfd9: '好吧，我会把马匹安全送到您的城中。',
    0xfda: '┅┅我手中有上等洋枪…',
    0xfdb: '这都是我精挑细选的洋枪，性能有保证！',
    0xfdc: '10支洋枪15贯钱，最多可以卖到300支。',
    0xfdd: '得到了洋枪%u支。',
    0xfde: '10支洋枪10贯钱，可以卖到1000枝。',
    0xfdf: '在现在这个时代，身上带不到10贯钱…',
    0xfe0: '这个枪身怎么有节呢┅┅这不是普通的黑竹竿吗！',
    0xfe1: '大人！不要受骗！这只是普通的黑竹竿！',
    0xfe2: '下雨时也可以使用…这次我就只出售真正的枪支吧。',
    0xfe3: '那么10支洋枪50贯钱，最多可以买50支。',
    0xfe4: '那么再见了，武士大人。祝您武运昌隆。',
    0xfb0: '如果您改变主意的话，请再来找我。',
    0xfbe: '┅┅跑得真快，像一阵风似的消失了┅┅。',
}


# --------------------------------------------------------------------------
# 魔数除数（实测）
# --------------------------------------------------------------------------

def _h32(a, b):
    return (a * b) >> 32


def _s32(v):
    v &= 0xffffffff
    return v - (1 << 32) if v >> 31 else v


def d10(x):
    """0x66666667 + sar 2"""
    h = _s32(_h32(0x66666667, x & 0xffffffff))
    return (h >> 2) if h >= 0 else -((-h + 3) >> 2)


def d3(x):
    """0x55555556: eax=edx ; shr edx,31 ; add eax,edx"""
    h = _s32(_h32(0x55555556, x & 0xffffffff))
    return h + (1 if h < 0 else 0)


def d2000(x):
    """0x10624dd3 + sar 7"""
    h = _s32(_h32(0x10624dd3, x & 0xffffffff))
    return (h >> 7) if h >= 0 else -((-h + 127) >> 7)


def _tdiv(a, b):
    return abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)


# --------------------------------------------------------------------------
# 自测
# --------------------------------------------------------------------------

def verify():
    print('--- 1) 纠偏：0x461510 不是 thunk ---')
    h = dis(0x461510, 0x461582)
    chk('入口 0x461510 即 call getCtx(0x49f6b0)',
        h[0][0] == 'call' and h[0][1] == '0x49f6b0')
    chk('函数起始由前接 nop 填充证实 (0x461509..0x46150f)',
        all(b == 0x90 for b in data[off(0x461509):off(0x461510)]))
    chk('读 ctx[+0] 并自断言 id==2 / id==3',
        has(h, 'cmp', 'ax', '2') and has(h, 'cmp', 'ax', '3'))
    chk('★ 无 ret 型尾跳：0x461510..0x46152c 内不存在 ret',
        not any(m == 'ret' for m, _ in dis(0x461510, 0x46152d)))
    chk('id2：push 0xfd1 → call 0x460bf0（居中对话框）',
        has(h, 'push', '0xfd1') and has(h, 'call', '0x460bf0'))
    chk('id3：push 0xfdd → call 0x460bf0',
        has(h, 'push', '0xfdd'))
    chk('id2 成交语 0xfd9 / id3 成交语 0xfe4',
        has(h, 'push', '0xfd9') and has(h, 'push', '0xfe4'))
    chk('参数取自 dword[esp+4]（cdecl 第 1 参）',
        has(h, 'mov', 'eax', 'esp + 4') and has(h, 'mov', 'edx', 'esp + 4'))
    chk('id2 分支尾跳到共同尾 0x461561',
        has(h, 'jmp', '0x461561'))
    chk('共同尾：0x47b900 → 0x4af1c0 → 0xfbe(0x49f5e0) → 0x47b900 → ret',
        has(h, 'call', '0x4af1c0') and has(h, 'push', '0xfbe')
        and has(h, 'call', '0x49f5e0') and h[-1][0] == 'ret')
    chk('id 非 2/3 直接落到共同尾 0x461569',
        any(m == 'jne' and '0x461569' in o for m, o in h))

    print('--- 2) 供给者：2 个 e8 caller，0 处绝对引用 ---')
    callers = []
    for i in range(len(data) - 5):
        if data[i] == 0xE8:
            rel = struct.unpack('<i', data[i + 1:i + 5])[0]
            if (BASE + i + 5 + rel) & 0xffffffff == 0x461510:
                callers.append(BASE + i)
    chk('e8 caller 恰为 0x46147a / 0x461a1a', sorted(callers) == [0x46147a, 0x461a1a])
    pat = struct.pack('<I', 0x461510)
    chk('全镜像 0 处绝对 dword 引用 ⇒ 无静态派发表', pat not in data)

    ca = dis(0x461440, 0x46148a)
    cb = dis(0x4619ec, 0x461a2a)
    chk('caller A 0x461410：按 byte[[0x52063c]+7] 分档 (>=2 → 0x461590 / <2 → 0x461710)',
        has(ca, 'cmp', 'ecx + 7', '2') and has(ca, 'call', '0x461590')
        and has(ca, 'call', '0x461710'))
    chk('caller B 0x4619ec：同构 (>=2 → 0x461a30 / <2 → 0x461b00)',
        has(cb, 'cmp', 'ecx + 7', '2') and has(cb, 'call', '0x461a30')
        and has(cb, 'call', '0x461b00'))
    chk('out 参数是栈上局部 (lea r,[esp+4])，caller 取出后 push 给 handler',
        has(ca, 'lea', 'esp + 4') and has(cb, 'lea', 'esp + 4'))
    chk('eax != 0 才调 handler，随后 call 0x461490',
        has(ca, 'call', '0x461490') and has(cb, 'call', '0x461490'))

    print('--- 3) 四档行商例程（门槛 / 台词 / 诈欺）---')
    f590 = dis(0x461590, 0x461651)
    f710 = dis(0x461710, 0x461900)
    fa30 = dis(0x461a30, 0x461af1)
    fb00 = dis(0x461b00, 0x461cf0)
    chk('0x461590 馬常連：0xfcd+0xfce，门槛 money01/10 + ctx[+4] >= 2',
        has(f590, 'push', '0xfcd') and has(f590, 'push', '0xfce')
        and has(f590, 'cmp', 'edx', '2'))
    chk('0x461710 馬新規：0xfd2，门槛 >= 1，诈欺判定 0x461900',
        has(f710, 'push', '0xfd2') and has(f710, 'cmp', 'edx', '1')
        and has(f710, 'call', '0x461900'))
    chk('0x461a30 洋枪常連：0xfdb+0xfdc，门槛 >= 0xf(15)',
        has(fa30, 'push', '0xfdb') and has(fa30, 'push', '0xfdc')
        and has(fa30, 'cmp', 'edx', '0xf'))
    chk('0x461b00 洋枪新規：0xfde，门槛 >= 0xa(10)，诈欺判定 0x461cf0',
        has(fb00, 'push', '0xfde') and has(fb00, 'cmp', 'edx', '0xa')
        and has(fb00, 'call', '0x461cf0'))
    chk('四档取 money = word[0x51662e]（0.1 貫位）与 ctx[+4]（貫）',
        all(has(f, 'mov', '0x51662e') for f in (f590, f710, fa30, fb00))
        and all(has(f, 'mov', 'esi + 4') or has(f, 'mov', 'edi + 4')
                for f in (f590, f710, fa30, fb00)))
    chk('四档经 out 指针回写数量 (mov dword ptr [r], eax)',
        has(f590, 'mov', 'dword ptr [ecx]', 'eax')
        and has(f710, 'mov', 'dword ptr [esi]', 'eax')
        and has(fa30, 'mov', 'dword ptr [ecx]', 'eax')
        and has(fb00, 'mov', 'dword ptr [esi]', 'eax'))
    chk('取消（0x7fffffff）→ MSG 0xfb0 且返回 0',
        all(has(f, 'cmp', 'eax', '0x7fffffff') and has(f, 'push', '0xfb0')
            for f in (f590, f710, fa30, fb00)))

    print('--- 4) 六个数值窗口调用点 (0x461660 实参) ---')
    ok = True
    for site, exp in SPINNER_CALLS.items():
        # 从 call 指令往前，收集紧邻的连续 push 序列（cdecl 实参）
        seq = dis(site - 24, site + 5)
        idx = next(i for i, (m, o) in enumerate(seq)
                   if m == 'call' and o == '0x461660')
        argpush = []
        for m, o in reversed(seq[:idx]):
            if m != 'push':
                break
            argpush.append(o.strip())
        vals = []
        for o in argpush:                       # 逆序 = cdecl 参数序
            try:
                vals.append(int(o, 16) if o.lower().startswith('0x') else int(o))
            except ValueError:
                vals.append(None)
        args = [v for v in vals if v is not None][:4]
        want = [exp['price'], exp['max10'], 0, exp['use_helper']]
        good = args == want
        ok &= good
        print('   0x%x %s%-4s → args=%s 期望%s %s'
              % (site, exp['goods'], exp['tier'], args, want, 'OK' if good else 'NG'))
    chk('六处 0x461660(価格, 上限/10, 0, use_helper) 实参全对', ok)
    chk('上限 = 10 × a1 与台词一致 (100/500/50/300/1000/50)',
        [e['max10'] * 10 for e in SPINNER_CALLS.values()] == [100, 500, 50, 300, 1000, 50])

    print('--- 5) 数量选择链 0x461660 → 0x45cdf0 → 0x47bd10 ---')
    f660 = dis(0x461660, 0x4616d0)
    chk('0x461660：把关 0x7fffffff，a2!=0 则 word[a2+6]=0xffff',
        has(f660, 'cmp', 'edi', '0x7fffffff') and has(f660, 'mov', '0xffff'))
    chk('0x461660：cost = (num*price)/10 后交 0x4616d0（魔数 0x66666667 + sar 2）',
        has(f660, 'imul', 'ecx', 'esi') and has(f660, 'mov', 'eax', '0x66666667')
        and has(f660, 'sar', 'edx', '2') and has(f660, 'call', '0x4616d0'))
    f6d0 = dis(0x4616d0, 0x461706)
    chk('0x4616d0(cost, num)：ctx[+6] += num/10',
        has(f6d0, 'add', 'word ptr [esi + 6]', 'dx'))
    chk('0x4616d0：cost 交给扣款函数 0x44e5f0',
        has(f6d0, 'call', '0x44e5f0'))
    fe5 = dis(0x44e5f0, 0x44e620)
    chk('0x44e5f0 扣款：ctx[+4] = 0x4ebcd0(ctx[+4], cost) 且刷新 0x493e50(0x524d50)',
        has(fe5, 'call', '0x4ebcd0') and has(fe5, 'mov', 'word ptr [esi + 4]', 'ax')
        and has(fe5, 'call', '0x493e50'))
    fcdf = dis(0x45cdf0, 0x45ce90)
    chk('0x45cdf0：money01 = 10*ctx[+4] + word[0x51662e]（lea 5*a → lea 2*ecx）',
        has(fcdf, 'lea', 'eax + eax*4') and has(fcdf, 'lea', 'edx + ecx*2')
        and has(fcdf, 'mov', '0x51662e'))
    chk('0x45cdf0：idiv 価格 → /10 → ×10（上限 = 10*sets）',
        has(fcdf, 'idiv', 'ecx') and has(fcdf, 'mov', 'eax', '0x66666667')
        and has(fcdf, 'shl', 'edi', '1'))
    chk('0x45cdf0：最终 min(10*b, cap)（16-bit cmp bx,di）',
        has(fcdf, 'cmp', 'bx', 'di') and has(fcdf, 'lea', 'ebx', 'eax + eax*4'))
    fb = dis(0x47bd10, 0x47bd8b)
    chk('0x47bd10 数值窗口：步长 10 → [0x524182]，上限 → [0x52417e]，下限 → [0x52417a]',
        has(fb, 'mov', '0x524182') and has(fb, 'mov', '0x52417e')
        and has(fb, 'mov', '0x52417a') and has(fb, 'mov', '0x524188'))
    chk('0x47bd10：a4 == -1 时下限取 a1（cmp ecx,-1）', has(fb, 'cmp', 'ecx', '-1'))
    chk('0x47bd10：位数 flags 100000/10000/1000/100/10',
        all(has(fb, 'cmp', 'eax', c) for c in ('0x186a0', '0x2710', '0x3e8', '0x64', '0xa')))
    chk('0x47bd10：开窗口 0x488f60(this=0x523d68, flags)',
        has(fb, 'mov', 'ecx', '0x523d68') and has(fb, 'call', '0x488f60'))

    print('--- 6) 诈欺事件：概率门 + 能力评分（技能位序反证）---')
    f900 = dis(0x461900, 0x461980)
    chk('0x461900：A=0x49f5e0 / B=0x49f610，取 max 后交概率门 0x4ebe40',
        has(f900, 'call', '0x49f5e0') and has(f900, 'call', '0x49f610')
        and has(f900, 'call', '0x4ebe40'))
    chk('0x461900：A 发现→0xfd4，B 提醒→0xfd5',
        has(f900, 'push', '0xfd4') and has(f900, 'push', '0xfd5'))
    fcf0 = dis(0x461cf0, 0x461d70)
    chk('0x461cf0（洋枪）：A 发现→0xfe0，B 提醒→0xfe1',
        has(fcf0, 'push', '0xfe0') and has(fcf0, 'push', '0xfe1'))
    s980 = dis(0x461980, 0x4619a5)
    sd70 = dis(0x461d70, 0x461d95)
    chk('评分公式 = (byte[+0xc]/3) * ((技能档 &3)+1)（魔数 0x55555556）',
        has(s980, 'mov', 'eax', '0x55555556') and has(s980, 'imul', 'eax', 'ecx')
        and has(sd70, 'mov', 'eax', '0x55555556') and has(sd70, 'imul', 'eax', 'ecx'))
    chk('★ 馬用技能位 +0x0f>>2&3，洋枪用 +0x10>>4&3',
        has(s980, 'mov', 'ecx + 0xf') and has(s980, 'shr', 'ecx', '2')
        and has(sd70, 'mov', 'ecx + 0x10') and has(sd70, 'shr', 'ecx', '4'))
    chk('两位域都 and 3 后 +1（and ecx,3 ; inc ecx）',
        has(s980, 'and', 'ecx', '3') and has(s980, 'inc', 'ecx')
        and has(sd70, 'and', 'ecx', '3') and has(sd70, 'inc', 'ecx'))
    skills = []
    for i in range(10):
        b = data[off(0x507b58) + i * 5: off(0x507b58) + i * 5 + 5]
        skills.append(b.decode('gbk').rstrip('\x00'))
    chk('技能名表 0x507b58 (10×5B) 顺序正确',
        skills == ['口才', '马术', '算术', '剑术', '忍术', '兵法', '洋枪', '筑城', '礼法', '茶道'])
    chk('★ 语义自洽：识破假马=马术(idx1)，识破假枪=洋枪(idx6)',
        skills[1] == '马术' and skills[6] == '洋枪')

    print('--- 7) 成交后 0x461490：来访次数与累积 ---')
    f490 = dis(0x461490, 0x461509)
    chk('来访次数 +1 且上限 3（cmp 3; jbe / mov eax,3）',
        has(f490, 'inc', 'eax') and has(f490, 'cmp', 'eax', '3')
        and has(f490, 'mov', 'eax', '3'))
    chk('写入器 0x49bfb0（set byte[対象+7]）', has(f490, 'call', '0x49bfb0'))
    chk('ctx[+6] >= 0x1e(30) → FIRE(1) via 0x49b860',
        has(f490, 'cmp', 'esi + 6', '0x1e') and has(f490, 'call', '0x49b860'))

    print('--- 8) helper 0x460bf0：居中对话框几何 ---')
    fbf0 = dis(0x460bf0, 0x460c3e)
    chk('文本取 0x493500(msgid)（file = id/2000）', has(fbf0, 'call', '0x493500'))
    chk('宽度 = strlen(文本)*8 + 0x28（0x4ebfc0 即 strlen）',
        has(fbf0, 'call', '0x4ebfc0') and has(fbf0, 'lea', 'ecx', 'eax*8 + 0x28'))
    chk('屏幕宽 0x280(640)，居中 x = (640-w)/2',
        has(fbf0, 'mov', 'eax', '0x280') and has(fbf0, 'sar', 'eax', '1'))
    chk('y=0xb8(184)，h=0x20(32)，交给 0x47afd0',
        has(fbf0, 'push', '0xb8') and has(fbf0, 'push', '0x20')
        and has(fbf0, 'call', '0x47afd0'))
    chk('0x493500 跳表 0x4935f4 = 4 项（4 个消息文件）',
        [u32(0x4935f4 + i * 4) for i in range(4)]
        == [0x493532, 0x493539, 0x493546, 0x493553])

    print('--- 9) 魔数除数实测 ---')
    chk('0x66666667 + sar 2 == ÷10 (0..20000 全等)',
        all(d10(x) == _tdiv(x, 10) for x in range(0, 20001)))
    chk('0x55555556 (high+sign) == ÷3 (0..20000 全等)',
        all(d3(x) == _tdiv(x, 3) for x in range(0, 20001)))
    chk('0x10624dd3 + sar 7 == ÷2000 (0..6210 全等)',
        all(d2000(x) == _tdiv(x, 2000) for x in range(0, 6211)))
    chk('反例警戒：sar 3 才是 ÷20（f(20)=1 而非 2）', d10(20) == 2)

    print('--- 10) MSGX 台词与模型一致 ---')
    p = os.path.join('scripts', 'msgx_all_texts.json')
    texts = {}
    if os.path.exists(p):
        texts = json.load(open(p, encoding='utf-8')).get('texts', {})
    if texts:
        chk('id2 对话框 0xfd1 含 %u（购买%u匹马）', '%u' in texts.get(str(0xfd1), ''))
        chk('id3 对话框 0xfdd 含 %u（得到了洋枪%u支）', '%u' in texts.get(str(0xfdd), ''))
        chk('价格/上限台词与表一致：0xfce=2贯100匹 / 0xfd2=1贯500匹',
            '2贯' in texts.get(str(0xfce), '') and '100匹' in texts.get(str(0xfce), '')
            and '1贯' in texts.get(str(0xfd2), '') and '500匹' in texts.get(str(0xfd2), ''))
        chk('洋枪台词：0xfdc=15贯300支 / 0xfde=10贯1000',
            '15贯' in texts.get(str(0xfdc), '') and '300支' in texts.get(str(0xfdc), '')
            and '10贯' in texts.get(str(0xfde), '') and '1000' in texts.get(str(0xfde), ''))
        chk('诈欺后抬价：0xfd7=50贯50匹 / 0xfe3=50贯50支',
            '50贯' in texts.get(str(0xfd7), '') and '50匹' in texts.get(str(0xfd7), '')
            and '50贯' in texts.get(str(0xfe3), '') and '50支' in texts.get(str(0xfe3), ''))
    else:
        print('   (skip: scripts/msgx_all_texts.json 缺失)')

    print('\nRESULT: %d/%d checks passed' % (PASS, CHECKS))
    return PASS == CHECKS


if __name__ == '__main__':
    sys.exit(0 if verify() else 1)
