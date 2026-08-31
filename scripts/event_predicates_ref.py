# -*- coding: utf-8 -*-
"""
event_predicates_ref.py  —  Per-handler [ctx+8] (arg) PREDICATE table (续107).

Companion to `event_handlers_full_ref.py` (which gives id -> handler).
This file answers: *what does each handler actually TEST / DO?*

============================================================================
HOW THE PREDICATES WERE DERIVED
============================================================================
Two mechanical extractors, both driven off the handler list in
`event_handlers_full_ref.py`:

1. `scripts/_evt_index_expr.py` — symbolic index-expression tracker.
   Each 32-bit register is tracked as (coeff*X + const) through
   shl / lea / imul / add / sub / mov.  Whenever a register becomes
   `coeff*X + GLOBAL`, it is reported.  This recovers **which runtime table
   the handler indexes, and with which stride** — the single most informative
   fact about a predicate.
   * Calibration (both known-decoded): 0x4e82c0 -> `5*X + 0x519548`
     (国情表 stride 5) and 0x4e7e10 -> `14*X + 0x5179b8`
     (49国政治/关系表 stride 14). Both recovered correctly.

2. `scripts/_evt_predicates.py` — per-handler dump of
   (a) the ctx base register (reg most often dereferenced at ctx offsets
       0/4/6/8/0xc), (b) the ARG register loaded from [ctx+8],
   (c) every instruction touching ARG, (d) call targets,
   (e) global immediates in 0x4f0000..0x540000, (f) whether [ctx+0xc]
   (flags) is read.  `_evt_dump3.py` gives raw disassembly for spot checks.

KNOWN TABLES (from MEMORY.md), used to interpret the strides:
    0x519548  国情表            stride 5   (49 provinces)
    0x5179b8  49国政治/关系表   stride 14  (49 provinces)
    0x51eb88  城/町表           stride 31  (200 entries)
    0x519868  武将实体表        stride 47  (370 entries)
    0x516a28  S7 运行时表       stride 16  (200)
    0x5176a8  S10 表            stride 4   (30)
    0x51dc60  外交关系矩阵      (triangular 49*48/2)
NEW (found by this pass):
    0x50cfa8  stride 13        (used by 0x4d5a20, ids 15/16/17) — 未名表

============================================================================
KEY STRUCTURAL FINDING (new in 续107)
============================================================================
The handler population is NOT uniform.  Three distinct kinds showed up:

* **gate**    — tiny boolean: self-assert id, test one flag/global, return 0/1.
                (e.g. 0x41adb0, 0x441cf0, 0x44a120, 0x4b3890)
* **builder** — builds an option/menu list into a global array, no FIRE.
                (e.g. 0x450b90 -> 0x513f08, 0x447520, 0x4d5a20)
* **thunk**   — self-asserts the id then TAIL-JUMPS to a function pointer
                passed in as a parameter (`push <param>; ret`).
                `0x461510` (id 2):  `push eax ; push 0xfd1 ; ret`
                after loading eax from [esp+4].  So the vtable slot holds a
                trampoline and the REAL implementation is supplied by the
                caller.  This is why some "handlers" have zero calls/globals —
                they are dispatch glue, not logic.

Also: several handlers dispatch internally on the id via a small jump table
(`jmp dword [ecx*4 + TABLE]`), e.g. 0x4608b7 -> 0x4608e8 and
0x461da0 -> 0x461dd0 (both 4 entries, id 0..3).
"""

# ---------------------------------------------------------------------------
# DECODED PREDICATES
#   kind   : gate | builder | thunk | condition | effect | dispatcher
#   tables : list of (global, stride) recovered by _evt_index_expr.py
#   gate   : extra flag/global gating condition
# ---------------------------------------------------------------------------
PREDICATES = {
    # ===== reference: already decoded 续81/82 (kept here for calibration) =====
    0x4e82c0: dict(ids=(13, 14), kind='condition', tables=[(0x519548, 5)],
                   gate='[0x516638] & 0x14',
                   semantics='id13: 当前所在国 idx == arg；id14: 当前气候组 == arg'
                             '（读 [arg*5 + 0x519548]）；arg=bp @0x4e82cf，'
                             'cmp bp,dx @0x4e8345 / cmp bp,ax @0x4e8359',
                   conf='high'),
    0x4e7e10: dict(ids=(10,), kind='condition', tables=[(0x5179b8, 14)],
                   gate='[ctx+0xc] & 2 == 0',
                   semantics='事件关联国 idx == arg（读 [arg*14 + 0x5179b8]）；'
                             'arg=bx @0x4e7e61；命中后子求值 0x49f610 + FIRE(1)',
                   conf='high'),
    0x4b4b20: dict(ids=(9,), kind='condition', tables=[],
                   gate=None,
                   semantics='调 0x49f430(arg) 返回值 == 存储值 → 写 [ctx+6]+0/3 → FIRE',
                   conf='high'),
    0x44ca90: dict(ids=(9,), kind='effect', tables=[],
                   gate='[0x52063c]',
                   semantics='显示 msg 0x1224..0x1227（4 段）+ 查全局门控 0x52063c',
                   conf='high'),
    0x4b3ac0: dict(ids=(15,), kind='effect', tables=[],
                   gate=None,
                   semantics='按 byte[obj+0x1b]&7 跳表（0x4b3be8，7 例程）派发；'
                             '尾部 self-assert id=15 + FIRE(1)',
                   conf='high'),
    0x4499f0: dict(ids=(29,), kind='effect', tables=[],
                   gate=None,
                   semantics='自断言 cmp ax,0x1d @0x449a98；调 getCtx@0x449a66 + '
                             'FIRE@0x449a8a；尾部 msg/概率分支（续106 纠正：非 id0/1）',
                   conf='high'),

    # ===== 续107: gate handlers (tiny booleans) =====
    0x41adb0: dict(ids=(13, 14), kind='gate', tables=[],
                   gate='id ∈ {0xffff, 0xd, 0xe}',
                   semantics='准入判定：读 [ctx+0]，若 == 0xffff 或 0xd(13) 或 '
                             '0xe(14) 则返回非零（放行）；否则 xor eax,eax 返回 0',
                   conf='high'),
    0x441cf0: dict(ids=(16,), kind='gate', tables=[],
                   gate='byte[0x517894] & 4 == 0',
                   semantics='id==0x10(16) 且 全局字节 byte[0x517894] 的 bit2 为 0 '
                             '→ 返回 1；否则跳过',
                   conf='high'),
    0x44a120: dict(ids=(8,), kind='gate', tables=[],
                   gate='[ctx+0xc] & 2 == 0',
                   semantics='id==8 且 flags([ctx+0xc]) bit1 为 0 → 返回 1',
                   conf='high'),
    0x4b3890: dict(ids=(15,), kind='gate', tables=[],
                   gate=None,
                   semantics='id==0xf(15) 且 arg == byte[0x520602]（全局字节，'
                             '经 movzx cx,cl 零扩展后与 [ctx+8] 比较）→ 返回 1',
                   conf='high'),

    # ===== 续107: builders / dispatchers =====
    0x450b90: dict(ids=(3,), kind='builder', tables=[],
                   gate=None,
                   semantics='构造选项数组写入全局 0x513f08：word[0x513f08]=0, '
                             'word[0x513f0a]=1；若 id==3 再写 word[0x513f0c]=2, '
                             'word[0x513f10]=3（菜单项 0..3）',
                   conf='high'),
    0x447520: dict(ids=(3,), kind='builder', tables=[],
                   gate='byte[[0x52063c]+8] & 4',
                   semantics='id==3 且 全局对象 [0x52063c] 偏移 +8 的 bit2 置位时，'
                             '在栈上构造选项表（word[esp+ecx*2+0xc]=1/2…）',
                   conf='high'),
    0x4608b7: dict(ids=(3,), kind='dispatcher', tables=[],
                   gate='[ctx+6] == 0',
                   semantics='按 id 跳表派发：jmp dword [ecx*4 + 0x4608e8]（4 项, '
                             'id 0..3）；并判 [ctx+6](result B) == 0',
                   conf='high'),
    0x461da0: dict(ids=(3,), kind='dispatcher', tables=[],
                   gate='arg == 0（且 arg < 2）',
                   semantics='按 id 跳表派发：jmp dword [ecx*4 + 0x461dd0]（4 项）；'
                             '分支 0x461db6 要求 [ctx+8](arg)==0',
                   conf='high'),
    0x461510: dict(ids=(2,), kind='thunk', tables=[],
                   gate=None,
                   semantics='★ TAIL-CALL 跳板：id==2 时取 [esp+4]（调用方传入的函数'
                             '指针）→ push eax; push 0xfd1; ret 尾跳过去。'
                             '本函数只是派发胶水，真正的实现由调用方供给',
                   conf='high'),
    0x4d5a20: dict(ids=(15, 16, 17), kind='builder', tables=[(0x50cfa8, 13)],
                   gate='[ctx+0xc] & 2 == 0；且 全局 byte[0x516638] & 4',
                   semantics='★續108 定名：构造【謁見(觐见)菜单】选项集。索引 '
                             'lea ecx,[ecx + ebp*4 + 0x50cfa8] @0x4d5ac0（ecx=9*ebp '
                             '⇒ 有效 stride 13）取出 6 个菜单项名（闲谈/赠送礼品/'
                             '有关任务建议/大名的方针/武将的传言/离开）。'
                             '依 [esp+0x28] 参数选择选项集：非 0 → {3,4}（大名的方针、'
                             '武将的传言）/ 2 项；0 → {0}（闲谈）/ 1 项。'
                             '再按 id 判 0xffff / 0x11(17) / 0x10(16) / 0xf(15)',
                   conf='high'),

    # ===== 续107: table-indexing conditions (recovered by _evt_index_expr) =====
    0x4c3610: dict(ids=(13, 14), kind='condition', tables=[(0x519548, 5)],
                   gate=None,
                   semantics='国情表（stride 5）：eax = 5*X + 0x519548；'
                             'arg=bx @0x4c362f，cmp cx,bx @0x4c366d / cmp ax,bx @0x4c3678',
                   conf='high'),
    0x41d980: dict(ids=(14,), kind='condition', tables=[(0x519548, 5), (0x519868, 47)],
                   gate='[ctx+0xc] 读取',
                   semantics='国情表 5*X+0x519548（lea @0x41d9ed）+ 武将实体表 '
                             '47*X+0x519868；arg=cx @0x41d9ce',
                   conf='high'),
    0x4d5560: dict(ids=(13, 14), kind='condition', tables=[(0x519868, 47)],
                   gate='[ctx+0xc] 读取',
                   semantics='武将实体表（stride 47）：esi = 47*X + 0x519868',
                   conf='high'),
    0x444220: dict(ids=(15,), kind='condition', tables=[(0x51eb88, 31)],
                   gate=None,
                   semantics='城/町表（stride 31）：esi = 31*X + 0x51eb88；'
                             'arg=ax @0x44423c 后 and eax,0xff（取低字节）；'
                             '并读 [ctx+6]',
                   conf='high'),
    0x45e78c: dict(ids=(9,), kind='condition', tables=[(0x51eb88, 31), (0x5176a8, 4)],
                   gate=None,
                   semantics='城/町表 31*X+0x51eb88 + S10 表 4*X+0x5176a8；'
                             'arg=si @0x45e79c；含 RNG 0x4ebd60 与消息 0x47b900；'
                             'forward 到 0x470260',
                   conf='high'),
    0x470260: dict(ids=(9,), kind='condition', tables=[(0x51eb88, 31), (0x516a28, 16)],
                   gate=None,
                   semantics='城/町表 31*X+0x51eb88 + S7 运行时表 16*X+0x516a28；'
                             'arg=si @0x470337，cmp cx,si @0x470349；调 0x49f430',
                   conf='high'),
    0x4d1080: dict(ids=(6, 7), kind='condition',
                   tables=[(0x51eb88, 31), (0x5179b8, 14)],
                   gate='[ctx+0xc] 读取',
                   semantics='城/町表 31*X+0x51eb88 + 49国政治表 14*X+0x5179b8；'
                             'arg=ax @0x4d10db（and eax,0xff）；id 取 6/7 分支',
                   conf='high'),
    0x4da170: dict(ids=(0, 3), kind='effect', tables=[(0x519868, 47)],
                   gate='word[参数+0x14]（武将实体号）< 0x172(370)',
                   semantics='★ 与 `0x4daf20` **同构**，且给出武将实体表 stride 47 的'
                             '**第三条独立证据（完整乘减序列）**：'
                             '`lea esi,[eax+eax*2]`(×3) → `shl esi,4`(×48) → '
                             '`sub esi,eax`(×47) → `add esi,0x519868` '
                             '⇒ `esi = 0x519868 + 47*实体号`。'
                             '入口读参数 `word[+0x14]` = **武将实体号**，'
                             '`cmp ax,0x172` (370 = 武将实体表条目数) 越界则 esi=0。'
                             '随后 `0x49f6a0` 取对象、`0x49f5e0` 取对象、getCtx，'
                             '`mov ecx,edi; call 0x49c310` 与 `mov ecx,esi; call 0x49c310` '
                             '对两个对象各调一次同方法，再 push 0xc6 推消息。202 insns（入口段已解）',
                   conf='high'),
    0x4daf20: dict(ids=(0, 3), kind='effect', tables=[(0x519868, 47)],
                   gate='word[参数+0x14]（武将实体号）< 0x172(370)',
                   semantics='与 `0x4da170` **同构**（同一 stride-47 乘减序列 `lea/shl/sub/add '
                             '0x519868`，同一 `cmp ax,0x172` 越界检查）。差异在尾部：'
                             '调 `0x47b5f0`、`0x49f370(ctx)`，再 `push 0xd9; push edi; '
                             'call 0x47b900` 推消息（消息号 0xd9 vs 0x4da170 的 0xc6）。'
                             '165 insns（入口段已解）',
                   conf='high'),
    0x4a3df3: dict(ids=(0,), kind='condition', tables=[(0x51eb88, 31)],
                   gate='[ctx+0xc] 读取；遍历目标非空',
                   semantics='★ 遍历候选对象 + **按「剩余量」做概率判定**：'
                             '`mov ebp,0x32; sub ebp,eax` ⇒ **ebp = 50 − x**（剩余天数/次数）；'
                             '取参数 `[esp+0x28]` 作为**指针数组/链表**遍历'
                             '（`edi = *param; esi = *edi`），与 `[esp+0x2c]` 及 ebx 比对定位目标；'
                             '读对象字段 `byte[+0x25]`（存 `[esp+0x10]`/`[esp+0x20]` 作比较基准）'
                             '与 **`byte[+0x29]`**；命中后 `movzx di,byte[esi+0x29]`，'
                             '`push ebp; call 0x4ebd60` 取 **RNG(ebp)**（概率随剩余量变化），'
                             '再 `call 0x4ebcd0(随机数, byte[+0x29])` 判定。'
                             '其余用城/町表 31*X+0x51eb88，多处 `test [ctx+0]`（id==0 零测试 idiom）。'
                             '220 insns（入口+主循环已解，尾部渲染未逐条追踪）',
                   conf='high'),
    0x4accb0: dict(ids=(0, 3), kind='gate', tables=[],
                   gate='byte[0x5179b7] == 0xff',
                   semantics='读全局字节 byte[0x5179b7]（= 49国政治表基址 0x5179b8-1，'
                             '即「base−1 折位」写法）判 == 0xff；另读 byte[0x520603]；'
                             '写 dword[0x525b1c]=0；id 0/3 双断言（test ax,ax / cmp ax,3 '
                             '均跳至 ret，exit-skip 干净）',
                   conf='high'),

    # ===== 续107: partially decoded (calls/globals known, semantics not traced) =====
    0x4c34cf: dict(ids=(13, 14), kind='condition', tables=[],
                   gate='[调用 0x49f5e0 所得对象 +0x2c] & 0x700 == 0x700 时直接放行',
                   semantics='与 0x4e82c0 同构的并行 id13/14 条件：调 0x49f5e0 取对象，'
                             '读其 [+0x2c] 判 0x700 掩码；否则 getCtx 取 id/arg：'
                             'id13 → `arg == di`（di 由 dl 经 shr/add 符号调整而来）'
                             '@0x4c3503；id14 → `arg == byte[ebx+1]` @0x4c3515'
                             '（与 0x4e82c0 的「气候组 = 国情记录 byte[1]」语义一致）',
                   conf='high'),
    0x46e2e0: dict(ids=(9,), kind='effect', tables=[],
                   gate=None,
                   semantics='取全局指针 `dword[0x5224f0]` 后调 '
                             '`0x47ae00([0x5224f0], 0, 9)`（第三参数 9 = 本 handler 的 id）；'
                             '置 `dword[0x520610] = 1`；**清零三个全局** '
                             '`dword[0x520630]` / `dword[0x520634]` / `dword[0x520638]`；'
                             'getCtx 后以 `dword[0x520630]` 为参数调 '
                             '`0x46e520(&out_a, &out_b, value)`（双输出查询）；'
                             'arg=si @0x46e35b 与 cx 比较 @0x46e36d',
                   conf='high'),
    0x4b4d10: dict(ids=(9,), kind='condition', tables=[],
                   gate='id == 9；0x49f430(arg) 返回值 == 存储值',
                   semantics='★ 与已知 id9 condition `0x4b4b20` **同族**。'
                             '入口先算 `clamp(ebp + edx + 5, 1, 7)`（先 shr/add 符号调整，'
                             '再 `cmp 7; jle` 上限截断、`cmp 1; jge` 下限截断）得 1..7 的'
                             '等级值；getCtx 后要求 id==9；调 `0x49f430(arg)` 取返回值，'
                             '与 `[esp+0x2c]` 存储值比较，相等才继续；再读 [ctx+6](result B)',
                   conf='high'),
    0x4a7000: dict(ids=(5, 15), kind='condition', tables=[(0x51eb88, 31)],
                   gate='byte[城表+0x1b] & 0x10 == 0；byte[城表+0x1d] 非 0xff 且 >0 且 ==1',
                   semantics='取 **城/町表 `0x51eb88`**（直接取首条，esi 常量装载）：'
                             '`test byte[esi+0x1b],0x10` 城種标志位必须为 0；'
                             '读 `byte[esi+0x1d]`（该字段恒 0xffff 即「空城」标记）'
                             '要求 != 0xff 且 > 0 且 == 1；再要求 `arg == bl`(初值 0)；'
                             '最后 id ∈ {5, 0xf}。arg=ax @0x4a700d；'
                             '调 0x49aba0/0x49abc0/0x49ac00/0x49ac30/0x4c9d90',
                   conf='high'),
    0x441750: dict(ids=(9,), kind='condition', tables=[],
                   gate='id == 9；RNG(3) == 0（1/3 概率）；arg < 0x31(49)',
                   semantics='getCtx 后把 id/arg 存栈；id!=9 直接跳过；'
                             '`push 3; call 0x4ebd60` 取随机，`test ax,ax` 非 0 即跳过'
                             '（⇒ **1/3 概率**）；再 `cmp bl,0x31; jae` 要求 arg 是合法'
                             '省索引（<49）',
                   conf='high'),
    0x44d950: dict(ids=(3, 15), kind='condition', tables=[],
                   gate='全局 word[0x5205fe] ∉ {2, 3}；且 arg & 0x8000 == 0',
                   semantics='ctx 由参数 [esp+0x10] 传入；arg=di @0x44d958；再 getCtx 取 id；'
                             '读 [ctx+4](result A) 到 bx，要求 <= 9，用其查**转码表 '
                             'byte[0x44da00]** 得 eax，再经**跳表 0x44d9ec** 派发；'
                             '分支中写 **word[0x506c4c] = 0xaa4**（下一条 MSG id）、'
                             '调 0x4441a0，并判 id==3',
                   conf='high'),
    0x41ddd5: dict(ids=(4, 5, 15), kind='condition', tables=[],
                   gate='[ctx+0xc] 读取',
                   semantics='与 0x4c34cf 同构（先 shr/add 做符号调整）：取 [ctx+0] 到 edx '
                             '后按 id 三分支 —— id < 4 → 一路径；4 <= id <= 5 → 二路径；'
                             'id == 0xf(15) → 三路径；全局 0x51987e（武将实体表 '
                             '0x519868+0x16 区）；调 0x49b8a0',
                   conf='high'),
    0x4c9db0: dict(ids=(4, 5, 15), kind='effect', tables=[],
                   gate='全局 word[0x52544c] == 6',
                   semantics='多段消息效果：门控 `word[0x52544c]==6`（某状态/场景编号）；'
                             '调 `0x4edf70(0x526c50)`；随后依次显示 **MSG 0x5ac / 0x5ad / '
                             '0x5ae…**（push 常量 + call 0x47b900），并调 `0x496ba0(6)` '
                             '与 `0x496ba0(0x13)`',
                   conf='high'),
    0x4d34cb: dict(ids=(11,), kind='effect', tables=[],
                   gate='[ctx+0] == 0xb(11)',
                   semantics='★ 事件到期/复位器：读全局日期字节 byte[0x5205f3] 到 si；'
                             '若 si > 8 → 调 0x4a0d50(0x18 - si, 1)；若 si < 8 → 调 '
                             '0x4a0d50(8 - si, 1)（补足到下一个时间节点）；再调 0x4340f0；'
                             '最后**清空整个 ctx**：[ctx+0]=0xffff，[ctx+4]/+6/+8/+0xa/+0xc '
                             '全部写 bx ⇒ **id 11 = 清除/复位事件上下文**',
                   conf='high'),
    0x4a7160: dict(ids=(17,), kind='effect', tables=[],
                   gate='id 既非 0xffff 也非 0x11(17)',
                   semantics='★ 倒计时/延迟触发器：读 [ctx+2]（计数器）→ 若非 0 则 '
                             '`dec` 并写回 [ctx+2]（每 tick 递减）；若减到 0，则依 flags '
                             '判定——bit4(0x10) 置位继续，bit0 为 0 时 `push 1; call 0x49b840` '
                             '真正触发。⇒ **id 17 = 定时/延时事件**，[ctx+2] 是剩余 tick 数',
                   conf='high'),
    0x45cc40: dict(ids=(6, 7), kind='gate', tables=[],
                   gate='id ∈ {6, 7}',
                   semantics='调 0x45a700 后取 [ctx+0] 到 si；id==7 或 id==6 → 放行；'
                             '否则 xor eax,eax 返回 0',
                   conf='high'),
    0x460420: dict(ids=(9,), kind='builder', tables=[],
                   gate='id == 9；全局 word[0x513fcc] 判定',
                   semantics='id!=9 直接退出；依全局 word[0x513fcc] 与调 0x460500 的返回值'
                             '（1/2/3/4 经 dec 链分支）选路；再调 0x460530 取结果 esi；'
                             '末尾**清零选项数组元素** word[0x513fe0 + eax*2] = 0'
                             '（与 0x450b90 的 0x513f08 属同一选项数组族 0x513fxx）',
                   conf='high'),
    0x4b3b58: dict(ids=(15,), kind='effect', tables=[],
                   gate=None,
                   semantics='★ 是 `0x4b3ac0`(id15) 七路跳表 **`0x4b3be8` 的分支体/公共尾**，'
                             '非独立入口。各分支设消息号 bl：`0x2f` / `0x24` / `0x21` / '
                             '`0x53`(esi=6) / `0x2b`(esi=5, call 0x49a9e0) / '
                             '`byte[edx + 0x508ff0]`(查表)；之后统一 `push esi; '
                             'call 0x49aac0`，若 esi==5 再 `call 0x49f9b0`，'
                             '尾部 `cmp word[ctx],0xf; jne exit; call FIRE(1)`',
                   conf='high'),
    0x460660: dict(ids=(15,), kind='effect', tables=[],
                   gate='RNG(2) == 0；且 [ctx+0] != 0xf',
                   semantics='push 2; call 0x4ebd60（RNG，1/2 概率）；若结果非 0 则退出；'
                             'getCtx 后若 id==0xf(15) 也退出；若参数 [esp+4]==0xf 则调 '
                             '0x496ba0([esp+8] + 0x64)',
                   conf='high'),
    0x484f34: dict(ids=(1,), kind='condition', tables=[],
                   gate='存在 i∈{0,1} 使 byte[obj + 0x268 + 48*i] 的 bit0 置位',
                   semantics='★ id 1 的唯一 handler（decrement idiom 检出）。'
                             '函数以 12 个 `nop` 开头（对齐填充）；esi = ecx（入参对象）；'
                             '**遍历 cx = 0..1**（2 次），索引 = `48*cx`'
                             '（`lea eax,[eax+eax*2]; shl eax,4` = ×3×16 = ×48），'
                             '`test byte[eax + esi + 0x268], dl`(dl=1) 测 bit0；'
                             '命中则留在该索引继续，两次都不中则退出。'
                             '⇒ 对象内嵌 **2 个 48 字节子记录**（起始偏移 +0x268），'
                             'id 1 条件是「两者之一 bit0 置位」',
                   conf='high'),
    0x45f020: dict(ids=(0, 2), kind='builder', tables=[],
                   gate=None,
                   semantics='★ 构造**随机化选项菜单**：RNG(5) → `byte[0x513fd0]`；'
                             'RNG(10) → `byte[0x513fc8]`（两个随机参数）；'
                             '初始化 `dword[0x513fe0] = 0x10001`、`word[0x513fe4] = ax`；'
                             '循环 esi = 3..5 调 `0x45e3e0(0, esi)`，结果依次写入 '
                             '`word[0x513fe6 + 2*(esi-3)]`（填充 3 个选项槽）；'
                             '再调 `0x45eb30(0)`。id 2 强断言 + id 0 零测试',
                   conf='high'),
    0x4c2d5b: dict(ids=(0,), kind='condition', tables=[(0x5179b8, 14)],
                   gate='[ctx+0xc] 读取',
                   semantics='★ **指针 → 省索引 反算（除法魔数坐实 stride 14）**：'
                             '`mov eax,0x92492493; sub ecx,0x5179b8; imul ecx; '
                             'add edx,ecx; sar edx,3` —— 这是 MSVC 有符号除以 **14** 的'
                             '经典魔数序列，即 **省 idx = (指针 − 0x5179b8) / 14**，'
                             '独立佐证 49国政治/关系表 stride = 14。'
                             '若指针恰等于表基址（esi==ebp）则取哨兵值 edx = 0x31(49)。'
                             '随后调 `0x49b5a0(ebx, idx)` → `0x49a750(edi, idx)` → '
                             '`0x49a7e0(edi, 7)` → `0x49f5a0(ebx)`，并用 `0x517c70` '
                             'push 0xb 推消息',
                   conf='high'),
    0x488993: dict(ids=(2,), kind='builder', tables=[],
                   gate=None,
                   semantics='★ **UI / 面板构造器**（非数值谓词）。以 **13 个 `nop` 对齐填充**'
                             '开头（与 `0x484f34` 同款，同编译单元）；edi = ecx（this），'
                             '取 `esi = dword[edi + 0x18]` 成员对象后连续调用 UI 构造：'
                             '`0x4b1d40(8, 0x78)`、`0x4b1190(0x10, 0x80, 0x90, 0x58)` 等'
                             '——参数全是**像素坐标**（7/0x68/0xa0/0x78、0x58/0x90/0x80/0x10）。'
                             '引用的全局 `0x5050d0`/`0x509530`/`0x509f90`/`0x509fa3`/'
                             '`0x509fb6`/`0x50a098`/`0x50a09c` 为面板标题/标签字符串资源。'
                             '78 insns（入口段已解，绘制细节未逐条追踪）',
                   conf='high'),
    0x45dc50: dict(ids=(2,), kind='condition', tables=[],
                   gate=None,
                   semantics='调 0x44dc60 取对象 → 读其 word[+3] 并 `shr 7; and 0x1f` '
                             '**抽取 bits 7..11（5 bit，0..31）** 作为判定字段；'
                             '再 getCtx 判 id==2：成立则继续，否则显示 **MSG 0x313**'
                             '（push 0x313 + call 0x47b900）',
                   conf='high'),
    0x4146c0: dict(ids=(13, 14), kind='effect', tables=[],
                   gate='[ctx+0xc] 读取',
                   semantics='★ 全表最大的 handler（239 insns），**id 13/14 的主效果器**。'
                             '入口先把**两个全局指针 `0x502b08` / `0x502b20` 存入栈帧**'
                             '（`mov dword[esp+0x1c],0x502b08` / `mov dword[esp+0x20],0x502b20`）'
                             '作为输出缓冲区/结构；随后连续调 `0x49f830(2)` / `(3)` / `(0)` / `(8)` '
                             '**取四个槽位对象**（与 `0x415b70` 共用 getter `0x49f830`，'
                             '已见编号 {0,2,3,8}）。其余全局 0x5029f8 / 0x517a6e / '
                             '0x5196a8 / 0x5203c0，并含大量 getter 调用。'
                             '（入口段已解，239 insns 主体未逐条追踪）',
                   conf='high'),
    0x415b70: dict(ids=(13, 14), kind='effect', tables=[],
                   gate='[ctx+0xc] 读取',
                   semantics='多段效果执行器：连续调 `0x49f830(2)` / `0x49f830(3)` / '
                             '`0x49f830(0)` 取三个槽位对象（`0x49f830` = **按槽位编号取对象**'
                             '的 getter，已见编号 {0,2,3,8}）；再调 `0x49f5e0` 取对象、'
                             'getCtx 取 ctx、`call 0x419cf0`；随后依次调 '
                             '`0x498f80(0xd)` / `0x4952f0(0xf)` / `0x495d10(0x12)` … '
                             '（参数 13/15/18… 为子动作编号）。全局 `0x5029f8`。'
                             '103 insns（入口段已解）',
                   conf='high'),
    0x4d83e0: dict(ids=(13, 14), kind='gate', tables=[],
                   gate='全局 byte[0x516638] & 4 必须置位',
                   semantics='先写 word[0x506c4c] = 0xffff；若 byte[0x516638]&4 == 0 则退出；'
                             '否则 getCtx 取 id，要求 0xd(13) <= id <= 0xe(14)；'
                             '命中则 push 1; call 0x4dcc80 并返回 1',
                   conf='high'),
}

# Handlers with no predicate decoded yet (no [ctx+8] read surfaced and no
# distinguishing call/global): 0x45dc50 is listed above; these remain open.
STILL_PENDING = [
    0x45dc50,   # only msg 0x47b900 + 0x44dc60 traced; arg use not confirmed
]

# Tables discovered in THIS pass that are not yet in MEMORY.md
NEW_TABLES = {
    0x50cfa8: dict(stride=13, used_by=[0x4d5a20], entries=6,
                   kind='GBK 菜单字符串表（12 字节正文 + 1 字节 NUL）',
                   note='续107 发现、续108 定名：謁見(觐见)菜单 6 个选项名，'
                        '空格 0x20 居中填充。索引式 lea ecx,[ecx + ebp*4 + 0x50cfa8] '
                        '（ecx = 9*ebp ⇒ 有效 stride 13）@0x4d5ac0；'
                        '全镜像（base±4）唯一消费者 = 0x4d5a20'),
}

# 0x50cfa8 — 謁見菜单选项名表（续108 定名）
# 6 条 × 13B，正文 12B GBK + 1B NUL(0x00)，两侧以 0x20 空格居中填充。
AUDIENCE_MENU_STRINGS = {
    0: (0x50cfa8, '闲谈'),
    1: (0x50cfb5, '赠送礼品'),
    2: (0x50cfc2, '有关任务建议'),
    3: (0x50cfcf, '大名的方针'),
    4: (0x50cfdc, '武将的传言'),
    5: (0x50cfe9, '离开'),
}

# Shared runtime helpers identified while decoding (续110)
HELPERS = {
    0x49f830: dict(name='按槽位编号取对象', sig='obj* f(int slot)',
                   note='被 0x415b70(0/2/3) 与 0x4146c60(0/2/3/8) 调用；已见编号 {0,2,3,8}'),
    0x49b840: dict(name='事件触发', sig='void f(int)', note='0x4a7160 在倒计时归零时 push 1 调用'),
    0x496ba0: dict(name='子动作执行', sig='void f(int)',
                   note='0x4c9db0 调 (6)/(0x13)；0x460660 调 (param+0x64)'),
    0x47b900: dict(name='显示 MSG', sig='void f(ctx, msg_id)',
                   note='消息显示主入口；0x45dc50 用 0x313、0x4c9db0 用 0x5ac/0x5ad/0x5ae、'
                        '0x4daf20 用 0xd9、0x4da170 用 0xc6'),
    0x4ebd60: dict(name='RNG(n)', sig='int f(int n)',
                   note='取 [0,n) 随机数；多处用于概率判定'),
    0x4ebcd0: dict(name='概率判定', sig='int f(int value, int rnd)',
                   note='0x4a3df3 用 RNG(ebp) 结果与 byte[+0x29] 判定'),
    0x49f430: dict(name='arg 查询', sig='int f(int arg)',
                   note='id9 条件族（0x4b4b20 / 0x4b4d10 / 0x46e2e0 / 0x470260）共用'),
    0x49c310: dict(name='对象方法（同方法双调用）', sig='int f(obj*)',
                   note='0x4da170 对两个对象各调一次'),
}

# Globals identified while decoding the predicates (续108)
NEW_GLOBALS = {
    0x506c4c: dict(name='下一条 MSG id', width='word',
                   note='由 0x44d950 写 0xaa4、由 0x4d83e0 写 0xffff（清空/无消息）；'
                        '推测为「下一条要显示的消息编号」'),
    0x513f08: dict(name='选项数组 #1', width='word[]',
                   note='0x450b90 写入 0/1/(2)/3 —— 菜单选项索引数组'),
    0x513fcc: dict(name='选项计数/模式', width='word',
                   note='0x460420 读取并与 3 比较，决定分支'),
    0x513fc8: dict(name='随机参数 A', width='byte',
                   note='0x45f020 由 RNG(10) 写入（0..9）'),
    0x513fd0: dict(name='随机参数 B', width='byte',
                   note='0x45f020 由 RNG(5) 写入（0..4）'),
    0x513fe0: dict(name='选项数组 #2', width='word[]',
                   note='0x460420 清零 word[0x513fe0 + eax*2]；0x45f020 初始化为 '
                        'dword 0x10001 并在 +0x4 写 ax；与 0x513f08 同族'),
    0x513fe6: dict(name='选项槽（3 连槽）', width='word[3]',
                   note='0x45f020 循环 esi=3..5 调 0x45e3e0(0,esi) 依次写入'),
    0x52544c: dict(name='状态/场景编号', width='word',
                   note='0x4c9db0 判 == 6 才执行多段消息效果'),
    0x520610: dict(name='事件子系统标志', width='dword',
                   note='0x46e2e0 置 1'),
    0x520630: dict(name='查询输入/结果 A', width='dword',
                   note='0x46e2e0 清零后作为 0x46e520 的参数'),
    0x520634: dict(name='查询输出 B', width='dword', note='0x46e2e0 清零'),
    0x520638: dict(name='查询输出 C', width='dword', note='0x46e2e0 清零'),
    0x5224f0: dict(name='子系统对象指针', width='dword',
                   note='0x46e2e0 读取后传给 0x47ae00'),
    0x5205fe: dict(name='日期/时序全局', width='word',
                   note='0x44d950 判 ∉{2,3}；紧邻已知时间全局 0x5205f0..f3'),
    0x5205f3: dict(name='日期字节（时间全局 +3）', width='byte',
                   note='0x4d34cb 读取并与 8 比较；属 0x5205f0..f3 日期计数器族'),
}

# Internal per-id jump tables found inside handlers (NOT the top-level vtable)
INTERNAL_JUMP_TABLES = {
    0x4608e8: dict(handler=0x4608b7, entries=4, note='id 0..3 跳表'),
    0x461dd0: dict(handler=0x461da0, entries=4, note='id 0..3 跳表'),
    0x4b3be8: dict(handler=0x4b3ac0, entries=7, note='byte[obj+0x1b]&7 对象类别跳表'),
}

def predicates_for(event_id):
    return {h: p for h, p in PREDICATES.items() if event_id in p['ids']}

def tables_of(handler):
    return PREDICATES.get(handler, {}).get('tables', [])

# ---- self-tests: assert the *structural* facts ----
def _self_test():
    for h, p in PREDICATES.items():
        assert 0x400000 <= h < 0x600000, f"bad handler addr {h:#x}"
        assert p['ids'], f"handler {h:#x} has no ids"
        assert p['conf'] in ('high', 'medium'), f"bad confidence for {h:#x}"

    # calibration: the two already-decoded handlers must resolve to the
    # known tables with the known strides
    assert (0x519548, 5) in tables_of(0x4e82c0), "0x4e82c0 must index 国情表 stride 5"
    assert (0x5179b8, 14) in tables_of(0x4e7e10), "0x4e7e10 must index 49国政治表 stride 14"

    # the 续106 correction must be reflected here too
    assert 29 in PREDICATES[0x4499f0]['ids'], "0x4499f0 is id 29"
    assert 0 not in PREDICATES[0x4499f0]['ids'], "0x4499f0 must NOT claim id 0"
    assert 1 not in PREDICATES[0x4499f0]['ids'], "0x4499f0 must NOT claim id 1"
    assert 0x490c0 not in PREDICATES, "0x490c0 is a typo'd bad address"

    # every discovered table must have a plausible stride
    for h, p in PREDICATES.items():
        for base, stride in p['tables']:
            assert 0x4f0000 <= base < 0x540000, f"bad table base {base:#x} in {h:#x}"
            assert 1 <= stride <= 64, f"implausible stride {stride} in {h:#x}"

    # kinds must be from the allowed vocabulary
    for h, p in PREDICATES.items():
        assert p['kind'] in ('gate', 'builder', 'thunk', 'condition', 'effect',
                             'dispatcher'), f"bad kind for {h:#x}"

    # the thunk finding
    assert PREDICATES[0x461510]['kind'] == 'thunk', "0x461510 must be a tail-call thunk"

    # 续108: the menu-string table 0x50cfa8 must be a 6 x 13B layout
    assert len(AUDIENCE_MENU_STRINGS) == 6, "audience menu must have 6 entries"
    addrs = [a for a, _ in AUDIENCE_MENU_STRINGS.values()]
    assert addrs == sorted(addrs), "menu entries must be ascending"
    for i in range(1, len(addrs)):
        assert addrs[i] - addrs[i-1] == 13, f"menu stride must be 13, got {addrs[i]-addrs[i-1]}"
    assert addrs[0] == 0x50cfa8, "menu table must start at 0x50cfa8"
    # the only consumer is 0x4d5a20
    assert NEW_TABLES[0x50cfa8]['used_by'] == [0x4d5a20]

    # FULL COVERAGE: every handler in the id->handler map must be documented here
    from event_handlers_full_ref import HANDLERS
    all_h = sorted({h for v in HANDLERS.values() for h in v})
    missing = [h for h in all_h if h not in PREDICATES]
    assert not missing, f"handlers missing predicates: {[f'0x{x:x}' for x in missing]}"
    assert len(PREDICATES) == len(all_h) == 49, (
        f"expected 49 documented handlers, got {len(PREDICATES)} (map has {len(all_h)})")

    n_high = sum(1 for p in PREDICATES.values() if p['conf'] == 'high')
    assert n_high == len(PREDICATES), f"{len(PREDICATES)-n_high} handler(s) still medium"
    for g, d in NEW_GLOBALS.items():
        assert 0x4f0000 <= g < 0x540000, f"bad global {g:#x}"
        assert d['name'], f"global {g:#x} unnamed"
    print("event_predicates_ref self-test: ALL PASS  "
          f"({len(PREDICATES)} handlers documented, {n_high} high-confidence, "
          f"{len(NEW_TABLES)} new table, {len(NEW_GLOBALS)} globals, "
          f"{len(INTERNAL_JUMP_TABLES)} internal jump tables)")

if __name__ == '__main__':
    _self_test()
