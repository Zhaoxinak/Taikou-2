# -*- coding: utf-8 -*-
"""
diplomacy_ref.py  —  Reference model of the Taikou2 COUNCIL / WORK-ASSIGNMENT
system, including the DIPLOMACY subsystem (高压外交 / 友好外交).

Reverse-engineered 2026-08-29 (续89) from the unpacked image
(scripts/_unpacked_mem.bin, flat map, off = va - 0x400000).

This CLOSES the largest previously-uncracked gameplay module: diplomacy was
never evidenced at the handler level before. The breakthrough came from
finding the two dispatch tables that WERE statically present (previous notes
wrongly assumed everything was runtime-filled C++ voodoo).

--------------------------------------------------------------------------
1. MAIN COUNCIL MENU (大名/家臣会议) — 4 items
--------------------------------------------------------------------------
  name table  : 0x50c7a0, stride 16 B (NOT 14 — corrects 续84)
  builder     : 0x4c1780  (fills [esp+4..+0x10] with the 4 name VAs, shows menu)
  entry filler: 0x4c16a0  (assigns sub-handles 0..3 into 0x525e50)
  dispatch    : 0x4c15ff reads 0x525e50[sel] then
                jmp dword ptr [eax*4 + 0x4c1668]     <-- static jump table

  [0] 听取意见 -> 0x4c1613 -> call 0x4c1830
  [1] 分派工作 -> 0x4c161a -> call 0x4c1ef0     <-- work assignment (contains diplomacy)
  [2] 出兵     -> 0x4c1621 -> call 0x4c2590
  [3] 结束会议 -> 0x4c1628 -> mov esi,1 (exit)

--------------------------------------------------------------------------
2. WORK TYPES (分派工作) — 16 items   <-- DIPLOMACY LIVES HERE
--------------------------------------------------------------------------
  name table  : 0x50c7e0, stride 16 B
  name lookup : 0x4c2190(code) -> picks name VA at [esp + code*4] (16 VAs on stack)
  select menu : 0x4c2000  -> returns selected index
  code table  : 0x525e30  (word[idx] = work-type code 0..15)
  executor    : 0x4c2240  -> 3-item menu 任命 / 其他武将 / 取消
                            (0x50c8e0 / 0x50c8f0 / 0x50c900, stride 16)
  dispatch    : 0x4c55b0  movsx eax,[esp+4]; jmp dword ptr [eax*4 + 0x50c950]
  param table : 0x50c990, 3 B per work type (semantics TBD)

--------------------------------------------------------------------------
3. DIPLOMACY FLOW (高压外交 / 友好外交)
--------------------------------------------------------------------------
  0x4c41e0 高压外交  /  0x4c4320 友好外交   (near-identical siblings)

  1) 0x49f5e0()            -> player object (edi)
  2) call 0x4c4270         -> choose TARGET PROVINCE
        iterates 0x5179b8 (province politics table, stride 14) over 49 entries
        (mov [esp+0x10], 0x31 = 49 ; cmp word[esi+4], 0x172 = lord id < 370)
  3) call 0x4c4300         -> choose MESSENGER (武将); 0xffff = cancel
  4) general entity        : 0x519868 + general_id * 47   (stride 47, 370 entries)
        computed as  lea ecx,[eax+eax*2]; shl ecx,4; sub ecx,eax; add ecx,0x519868
  5) show MSGX 0x875       -> "appoint X as messenger"
  6) store messenger       : dword[0x525ea4] = esi

  NOTE: the two handlers only SET UP the mission; the actual relationship
  change when the messenger reaches the target still needs to be traced
  (see still_unknown below).

--------------------------------------------------------------------------
4. WORK-TYPE EXECUTION / ASSIGN DISPATCH  (本会话扩展; ⚠️ 已被 续95 对齐)
--------------------------------------------------------------------------
  ⚠️ 续95 纠正：0x4c56a0 区实为【工作指令下发】(与 0x4c5699 同簇)而非使者归还
  结算；真正的使者归还结算(读 general +0x16/+0x17/+0x18 并应用效果)在
  0x4b9250 -> 0x4b981c(详见 续95/96 + diplomacy2_ref.py, 183/183 PASS)。
  本节保留的是「玩家侧即时执行 / 指派派发」分支，与 0x4b9250 递延结算互补，非冲突。
  原错误标注 SETTLEMENT 已作废，勿据本节定位结算主函数。

  After a work order is queued (or executed immediately on the player side),
  the entry is:

    0x4c56a0   work-execution / assign dispatch entry
        reads MESSENGER_SLOT (0x525ea4)  -> envoy general-entity pointer
              (0x519868 + id*47 ; [ptr+4] = province idx, cmp ax,0x172)
        reads 0x525ea0                   -> TARGET city/castle entry
              (0x51eb88 + idx*31 ; idx = (ptr-0x51eb88)/31 via magic 0x84210843)
        iterates the work order list with stride 0x12
        builds a RESULT RECORD:  [esi+4] = result type, [esi+6] = value
        shows the result message via 0x47b900 (MSGX ids 0x89e..0x8a7)
        dispatch:  cmp edx,0xf ; ja end ;  jmp dword ptr [edx*4 + 0x4c5b70]

    0x4c5b70   16-entry jump table  -> per-work-type settlement handler
        (the SECOND dispatch layer; 0x50c950 was the ASSIGN layer)

  Settlement handlers (result-type recorded):
    [0] 高压外交 -> 0x4c57cc  (type 0xa)   [1] 友好外交 -> 0x4c57ed (type 9)
    [2] 谋略     -> 0x4c5813  (type 0xd)   [3] 卖出军粮 -> 0x4c5871
    [4] 购入军粮 -> 0x4c58ab  [5] 购入军马 -> 0x4c58db  [6] 购入洋枪 -> 0x4c58fe
    [7] 开垦农田 -> 0x4c5929  [8] 训练     -> 0x4c5954  [9] 修复     -> 0x4c59d2
   [10] 筑城     -> 0x4c59fd  [11] 朝廷工作 -> 0x4c5a49  [12] 收集情报 -> 0x4c5a62
   [13] 移动居城 -> 0x4c5ad4 (nop)         [14] 武者修行 -> 0x4c5a80  [15] 茶会 -> 0x4c5ab0

  0x4c5d00   "pick best target general for 谋略"  (called from 0x4c5813)
        walks a linked list ([esi+4]=next), minimizes
            f = 0xc8 - 2*byte[entity+0xd] + byte[entity+0x29]
        returns the selected general's index (0x519868 base, stride 47)

--------------------------------------------------------------------------
5. RELATION-LEVEL NAME TABLE  0x5080cc  (续90 correction)
--------------------------------------------------------------------------
  NOT a numeric relation matrix. It is the 八级国关系 LEVEL-NAME string
  pool, reached indirectly (0 literal xrefs to the VA found):
    axis A (友好度 8 levels): 盟友 亲密 良好 普通 敌视 险恶 绝交 交战
    axis B (主从度 8 levels): 同盟 从属 支配 最坏 较坏 普通 良好 最好
  => the live relation value is a 0..7 index into this table. The byte that
     holds it is still unwritten via simple [base+0xb..0xd] offsets in the
     functions scanned (see still_unknown).
"""

# ---------------------------------------------------------------- tables ----
MAIN_MENU = {           # 0x50c7a0, stride 16
    0: ('听取意见', 0x50c7a0, 0x4c1830),
    1: ('分派工作', 0x50c7b0, 0x4c1ef0),
    2: ('出兵',     0x50c7c0, 0x4c2590),
    3: ('结束会议', 0x50c7d0, None),      # 0x4c1628 -> exit
}

# 16 work types: name, name VA, execution handler (from jump table 0x50c950),
# and the 3-byte param record (from 0x50c990).
WORK_TYPES = [
    ('高压外交', 0x50c7e0, 0x4c41e0, (0, 2, 255)),
    ('友好外交', 0x50c7f0, 0x4c4320, (0, 2, 255)),
    ('谋略',     0x50c800, 0x4c4400, (2, 255, 255)),
    ('卖出军粮', 0x50c810, 0x4c4520, (1, 3, 4)),
    ('购入军粮', 0x50c820, 0x4c45c0, (1, 3, 4)),
    ('购入军马', 0x50c830, 0x4c4640, (1, 5, 6)),
    ('购入洋枪', 0x50c840, 0x4c46c0, (1, 8, 7)),
    ('开垦农田', 0x50c850, 0x4c4740, (6, 255, 255)),
    ('训练',     0x50c860, 0x4c4b20, (255, 255, 255)),
    ('修复',     0x50c870, 0x4c4c00, (9, 6, 255)),
    ('筑城',     0x50c880, 0x4c4dd0, (9, 0, 6)),
    ('朝廷工作', 0x50c890, 0x4c5000, (0, 10, 11)),
    ('收集情报', 0x50c8a0, 0x4c5100, (1, 12, 7)),
    ('移动居城', 0x50c8b0, 0x4c5190, (255, 255, 255)),
    ('武者修行', 0x50c8c0, 0x4c5360, (255, 255, 255)),
    ('茶会',     0x50c8d0, 0x4c5430, (15, 0, 11)),
]

# dispatch tables / globals
JT_MAIN       = 0x4c1668   # 4 entries  -> 0x4c1613/1a/21/28
JT_WORK       = 0x50c950   # 16 entries -> execution handlers
PARAM_WORK    = 0x50c990   # 16 x 3 B
CODE_TABLE    = 0x525e30   # word[] work-type code per menu slot
SUBHANDLE_TBL = 0x525e50   # word[] sub-handle per main-menu slot
MESSENGER_SLOT = 0x525ea4  # dword, stores the chosen messenger object
PROVINCE_TBL  = 0x5179b8   # province politics, stride 14, 49 entries
GENERAL_ENT   = 0x519868   # general entity table, stride 47, 370 entries
GENERAL_PTR   = 0x517848   # dword -> general pointer array
MSGX_APPOINT  = 0x875      # "appoint X as messenger"

DIPLOMACY = {
    '高压外交': 0x4c41e0,
    '友好外交': 0x4c4320,
}

# ---------------------------------------------------------------------------
# 4. SETTLEMENT / EXECUTION LAYER  (续90, 2026-08-30)
# ---------------------------------------------------------------------------
SETTLE_FN     = 0x4c56a0   # work-order settlement entry
SETTLE_JT     = 0x4c5b70   # 16-entry jump table -> per-work-type settlement handler
TARGET_SLOT   = 0x525ea0   # dword, target city/castle entry (0x51eb88 + idx*31)
STRAT_SELECT  = 0x4c5d00   # 谋略: pick best target general (linked-list minimizer)
MSGX_RESULT   = 0x47b900   # result-message display (ids 0x89e .. 0x8a7)

# result-type byte written into the result record [esi+4] for each work type
SETTLE_HANDLERS = [
    (0,  '高压外交', 0x4c57cc, 0x0a),
    (1,  '友好外交', 0x4c57ed, 0x09),
    (2,  '谋略',     0x4c5813, 0x0d),
    (3,  '卖出军粮', 0x4c5871, None),
    (4,  '购入军粮', 0x4c58ab, None),
    (5,  '购入军马', 0x4c58db, None),
    (6,  '购入洋枪', 0x4c58fe, None),
    (7,  '开垦农田', 0x4c5929, None),
    (8,  '训练',     0x4c5954, None),
    (9,  '修复',     0x4c59d2, None),
    (10, '筑城',     0x4c59fd, None),
    (11, '朝廷工作', 0x4c5a49, None),
    (12, '收集情报', 0x4c5a62, None),
    (13, '移动居城', 0x4c5ad4, None),
    (14, '武者修行', 0x4c5a80, None),
    (15, '茶会',     0x4c5ab0, None),
]

# ---------------------------------------------------------------------------
# 5. RELATION-LEVEL NAME TABLE  0x5080cc  (续90 correction)
# ---------------------------------------------------------------------------
RELNAME_TBL  = 0x5080cc   # 八级国关系 level-name string pool (indirect refs only)
# axis A (友好度 8 levels) then axis B (主从度 8 levels)
RELNAME_AXIS_A = ['盟友', '亲密', '良好', '普通', '敌视', '险恶', '绝交', '交战']
RELNAME_AXIS_B = ['同盟', '从属', '支配', '最坏', '较坏', '普通', '良好', '最好']

def general_entity_va(general_id):
    """0x519868 + id*47 (the EXE computes it as ((id*3)<<4) - id + 0x519868)."""
    if general_id >= 370:      # cmp ax, 0x172 -> jae (null)
        return 0
    return GENERAL_ENT + general_id * 47

def work_handler(work_type):
    """work-type code (0..15) -> execution handler VA"""
    if 0 <= work_type < len(WORK_TYPES):
        return WORK_TYPES[work_type][2]
    return None

def work_name(work_type):
    if 0 <= work_type < len(WORK_TYPES):
        return WORK_TYPES[work_type][0]
    return None

def work_params(work_type):
    if 0 <= work_type < len(WORK_TYPES):
        return WORK_TYPES[work_type][3]
    return None

# ------------------------------------------------------------ self-tests ----
def _self_test():
    # diplomacy handlers landed
    assert DIPLOMACY['高压外交'] == 0x4c41e0
    assert DIPLOMACY['友好外交'] == 0x4c4320
    assert work_handler(0) == 0x4c41e0
    assert work_handler(1) == 0x4c4320
    # 16 work types, names align with the name table VAs (stride 16)
    assert len(WORK_TYPES) == 16
    for i, (name, va, _h, _p) in enumerate(WORK_TYPES):
        assert va == 0x50c7e0 + 16 * i, (i, name, hex(va))
    # known non-diplomacy handlers
    assert work_handler(10) == 0x4c4dd0      # 筑城
    assert work_handler(12) == 0x4c5100      # 收集情报
    assert work_name(15) == '茶会'
    # main menu dispatch
    assert MAIN_MENU[1][0] == '分派工作' and MAIN_MENU[1][2] == 0x4c1ef0
    assert MAIN_MENU[3][2] is None           # 结束会议 -> exit
    # general entity stride 47
    assert general_entity_va(0) == 0x519868
    assert general_entity_va(1) == 0x519868 + 47
    assert general_entity_va(370) == 0       # out of range -> null
    # params
    assert work_params(0) == (0, 2, 255)
    assert work_params(3) == (1, 3, 4)
    # ---- settlement layer (续90) ----
    assert SETTLE_FN == 0x4c56a0
    assert SETTLE_JT == 0x4c5b70
    assert TARGET_SLOT == 0x525ea0
    assert STRAT_SELECT == 0x4c5d00
    assert len(SETTLE_HANDLERS) == 16
    # diplomacy settlement handlers + result-type bytes
    assert SETTLE_HANDLERS[0] == (0, '高压外交', 0x4c57cc, 0x0a)
    assert SETTLE_HANDLERS[1] == (1, '友好外交', 0x4c57ed, 0x09)
    assert SETTLE_HANDLERS[2] == (2, '谋略',     0x4c5813, 0x0d)
    assert SETTLE_HANDLERS[15] == (15, '茶会',   0x4c5ab0, None)
    # relation-name table (correction): two 8-level axes
    assert RELNAME_TBL == 0x5080cc
    assert RELNAME_AXIS_A == ['盟友','亲密','良好','普通','敌视','险恶','绝交','交战']
    assert RELNAME_AXIS_B == ['同盟','从属','支配','最坏','较坏','普通','良好','最好']
    print("diplomacy_ref self-test: ALL PASS")

if __name__ == '__main__':
    _self_test()
