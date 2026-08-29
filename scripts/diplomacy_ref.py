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
    print("diplomacy_ref self-test: ALL PASS")

if __name__ == '__main__':
    _self_test()
