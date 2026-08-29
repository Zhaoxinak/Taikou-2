# -*- coding: utf-8 -*-
"""
event_id_dispatch_ref.py  —  Reference model of the Taikou2 EVENT DISPATCH.

Reverse-engineered from the unpacked image (scripts/_unpacked_mem.bin).

KEY FINDINGS (2026-08-29, 续82 + 续83)
=======================================
1. The event system dispatches by an **event-type id** stored at `[ctx+0]`
   (word) inside the context object returned by `0x49f6b0` (= 0x516610, a
   runtime-managed object). Each handler method self-asserts its own id
   somewhere in the function body (not only at function entry).

2. There are (at least) TWO dispatch tables indexed by the same id space
   (0..0x3f): a **CONDITION** table (method reads [ctx+8]=arg, tests a
   runtime predicate, then `call 0x49b860` to fire) and an **EFFECT** table
   (method executes the event's scripted consequences: messages, state
   changes, possibly calling FIRE itself).

3. EXACT event-type id set (verified by hand-disassembly of every
   handler enumerated by `_evt_enum3.py` AND the liveness-corrected
   `_evt_enum_full.py`):  {0, 1, 9, 10, 13, 14, 15}.
   - id 0  has THREE effects: 0x4499f0, 0x490c0, 0x4d0ca0 (applier-style).
     id 1  has TWO effects: 0x4499f0, 0x490c0 (the third sibling rejects id=1).
   - id 9  has BOTH a condition (0x4b4b20) and an effect (0x44ca90).
   - id 13/14 share ONE condition (0x4e82c0).
   - id 15 has an effect (0x4b3ac0) that ALSO dispatches on byte[obj+0x1b]&7
     (a per-object-type jump table at 0x4b3be8, 7 cases).

4. The "id ∈ {0,2,3}" assertion in `0x4d0ca0` (a non-vtable function called
   by `0x4d08fe`) is a FALSE POSITIVE for event dispatch — `0x4d0ca0` is a
   monthly scheduler / applier that calls `getCtx`/`FIRE` opportunistically
   but is NOT in the event handler vtable.

5. The remaining 17 candidate functions that v3 reported as "call getCtx +
   call FIRE" but do NOT assert any opcode are appliers / dialog handlers /
   UI actions — they read/write [ctx+6] (a result slot) but never test
   [ctx+0]. They are NOT event handlers.

ctx contract (verified 续81+续83, unchanged):
    [ctx+0]   word  event-type id      (== opcode in condition methods)
    [ctx+4]   word  result A (handler-writable)
    [ctx+6]   word  result B (handler-writable; appliers commonly set 0/1)
    [ctx+8]   word  arg               (compared against a runtime value)
    [ctx+0xc] word  flags             (extra gate, e.g. bit 2 in 0x4e7e10)
"""

# handler -> set of event-type ids it asserts, and its kind + semantics
HANDLERS = {
    # ===== CONDITION methods (read [ctx+8] arg, test predicate, fire) =====
    0x4e82c0: {'ids': (13, 14), 'kind': 'condition',
               'desc': 'id13: 玩家当前所在国 idx == arg  '
                       '(读 [arg-prov_idx*5 + 0x519548] == [ctx+8]); '
                       'id14: 当前气候组 == arg '
                       '(读 [arg-prov_idx*5 + 0x519548].byte[1] == [ctx+8]); '
                       '门控 [0x516638] & 0x14 (bit2 & bit4) 必须置位'},
    0x4e7e10: {'ids': (10,),    'kind': 'condition',
               'desc': 'id10: 事件关联国 idx == arg '
                       '(读 [arg-prov*14 + 0x5179b8] == [ctx+8]); '
                       '门控 [ctx+0xc] & 2 必须=0; '
                       '成功后调 sub-eval 0x49f610 显示 0x845/0x846 + FIRE(1) + 写 [ctx+6]'},
    0x4b4b20: {'ids': (9,),     'kind': 'condition',
               'desc': 'id9: 调 0x49f430(arg) 返回值 == 某存储值; '
                       '成功后写 [ctx+6]+0/3 (依 flag 决定) + FIRE'},

    # ===== EFFECT methods (execute event consequences) =====
    0x44ca90: {'ids': (9,),     'kind': 'effect',
               'desc': 'id9: 显示消息 0x1224..0x1227 (4 段); 检查 [0x52063c] 全局门控'},
    0x4b3ac0: {'ids': (15,),    'kind': 'effect',
               'desc': 'id15: 多目标效果 — 按 byte[obj+0x1b] & 7 跳表派发 7 子例程 '
                       '(0x4b3b11/1a/69/69/84/84/72); 含 msg 0x44/0x53/0x2b/0x21/0x24/0x2f '
                       '+ 查 0x508ff0 + 调 0x49a9e0/0x49aac0; 尾部 self-assert id=15 + FIRE(1)'},
    0x4499f0: {'ids': (0, 1),   'kind': 'effect',
               'desc': 'id0/1: 显示 msg 0x7d + 查 [esp+0x28](>0x5dc?) + '
                       'rand%3 == 0 概率分支 → 显示 msg 0x8f + 调 0x49b2b0(push 2); '
                       '调 0x49f6b0 拿 ctx → 写 [ctx+4]=si, [ctx+6]=0 → FIRE(0|1); '
                       '按 [edi+3] bit5..bit1 调 0x49b280(arg); 显示 msg 0x7f + 调 0x4a0d50(2,1)'},
    0x490c0:  {'ids': (0, 1),   'kind': 'effect',
               'desc': 'id0/1: 与 0x4499f0 近同构兄弟; 差异仅在尾部 getter '
                       '0x4a0d50 vs 0x49b2b0, push 参数 1 vs 0'},
    0x4d0ca0: {'ids': (0, 2, 3), 'kind': 'effect-applier',
               'desc': 'FALSE POSITIVE for vtable dispatch — id 接受集合 = {0,2,3} '
                       '但本函数不是虚表派发,而是 0x4d08fe 月处理函数内的子调用; '
                       '语义为赐物/扣俸: 依 6 类对象类型分支(查 0x5197b0) + '
                       '随机概率 + msg 0x46/0x103/0x104 + 调 0x4d05e0/0x495920/0x4d0e80/0x4d0f20/0x4d0fa0'},
}

# True event handler vtable entries (id -> list of handler addresses)
# NOTE: 0x4d0ca0 is excluded here — it is an applier, not a vtable entry.
VTABLE_HANDLERS = {
    0:  [0x4499f0, 0x490c0],
    1:  [0x4499f0, 0x490c0],
    9:  [0x4b4b20, 0x44ca90],   # condition + effect (same id)
    10: [0x4e7e10],
    13: [0x4e82c0],
    14: [0x4e82c0],
    15: [0x4b3ac0],
}

def handlers_for(event_id):
    return VTABLE_HANDLERS.get(event_id, [])

def kind_of(handler):
    return HANDLERS.get(handler, {}).get('kind')

def ids_of(handler):
    return HANDLERS.get(handler, {}).get('ids', ())

# ---- self-tests: assert the *structural* facts (no runtime data needed) ----
def _self_test():
    # Every id in the vtable maps to at least one handler
    for eid in VTABLE_HANDLERS:
        assert VTABLE_HANDLERS[eid], f"empty handler list for id {eid}"

    # id 0/1 share the same two effect handlers (0x4499f0 + 0x490c0)
    assert set(handlers_for(0)) == {0x4499f0, 0x490c0}
    assert set(handlers_for(1)) == {0x4499f0, 0x490c0}

    # id 9 has BOTH a condition (0x4b4b20) and an effect (0x44ca90)
    h9 = handlers_for(9)
    assert 0x4b4b20 in h9 and 0x44ca90 in h9
    assert kind_of(0x4b4b20) == 'condition'
    assert kind_of(0x44ca90) == 'effect'

    # id 13/14 share one condition method
    assert handlers_for(13) == [0x4e82c0]
    assert handlers_for(14) == [0x4e82c0]

    # id 10 is a single condition method
    assert handlers_for(10) == [0x4e7e10]

    # id 15 is a single effect with internal jump-table dispatch
    assert handlers_for(15) == [0x4b3ac0]
    assert kind_of(0x4b3ac0) == 'effect'

    # 0x4d0ca0 is flagged as applier, not vtable handler
    assert kind_of(0x4d0ca0) == 'effect-applier'
    assert 0x4d0ca0 not in sum(VTABLE_HANDLERS.values(), [])

    # Total event-type ids: 7
    assert len(VTABLE_HANDLERS) == 7
    assert sorted(VTABLE_HANDLERS) == [0, 1, 9, 10, 13, 14, 15]

    # All ids fall in [0..0x3f]
    for eid in VTABLE_HANDLERS:
        assert 0 <= eid <= 0x3f

    print("event_id_dispatch_ref self-test: ALL PASS  (7 ids, 7 handlers, "
          "1 false-positive applier flagged)")

if __name__ == '__main__':
    _self_test()
