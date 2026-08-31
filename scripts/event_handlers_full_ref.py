# -*- coding: utf-8 -*-
"""
event_handlers_full_ref.py  —  Full EVENT-TYPE id -> handler map (续106).

Reverse-engineered from the unpacked image (scripts/_unpacked_mem.bin).

============================================================================
HOW THE MAP WAS DERIVED  (method; reuse this for any re-derivation)
============================================================================
Per 续81/续82 the event system dispatches by an **event-type id** (word) stored
at `[ctx+0]` of a runtime context object returned by `getCtx = 0x49f6b0`
(0x516610). There is NO static dispatch table — 续81 proved this by scanning
the entire binary (code AND data) for any known handler address as a literal:
**0 hits**. The vtable is built at runtime, so the ONLY static signal is the
**self-assertion**: each handler reads `[ctx+0]`, compares it against its own
id, and conditionally skips if it does not match.

Discovery tool: `scripts/_evt_scan_wide.py` (v7 hybrid scan):
  * function starts = call rel32 targets  UNION  post-ret / forward-jmp addresses
    UNION  standard prologues (`55 89 E5` = push ebp; mov ebp, esp).
    The prologue union is essential: it catches vtable-only handlers
    (e.g. 0x4e82c0) that are never `call`-referenced.
  * per function, detect BOTH assertion idioms:
      (A) direct :  cmp word ptr [BASE+0], imm16
      (B) via-load: mov R2, [BASE+0]  ;  ...  cmp R2, imm16
                    mov R2, [BASE+0]  ;  ...  test R2, R2  (=> id == 0)
                    mov R2, [BASE+0]  ;  ...  dec  R2 ; jcond (=> id == 1)
    where imm in [0..0x3f] and a conditional jump follows within a small window.
  * KEEP a candidate ONLY if the function also calls getCtx (0x49f6b0) or
    FIRE (0x49b860) — the 续82 gold standard. This removes zero/null checks
    (`cmp [eax],0`) and generic struct compares that merely coincide with the idiom.
  * EXCLUDE ids 0x31 (49) and 0x3f (63): these are province-count / max-id
    *boundary* checks (e.g. `cmp cl,0x31`), NOT event ids.

Result: 49 distinct handler functions over 18 distinct event ids (this file).

============================================================================
CONFIDENCE (per id-edge)
============================================================================
  strong    : the assertion uses idiom (A) or via-load `cmp R, imm`
              (the canonical self-assertion form).
  medium    : the assertion uses the zero-test (`test R,R` => id 0) or
              decrement (`dec R ; jcond` => id 1) idiom. These are real
              id-branches but are more prone to being *internal guards*
              (a handler for id N that also has an `if id==0` sub-branch)
              rather than a standalone id-0/1 entry point. Treated as
              candidates pending confirmation by vtable inspection.

============================================================================
CONTEXT CONTRACT  (verified 续81+, unchanged)
============================================================================
    [ctx+0]   word  event-type id      (== the asserted id)
    [ctx+4]   word  result A (handler-writable)
    [ctx+6]   word  result B (handler-writable; appliers set 0/1)
    [ctx+8]   word  arg               (compared against a runtime value)
    [ctx+0xc] word  flags             (extra gate, e.g. bit 2 in 0x4e7e10)

============================================================================
IMPORTANT CORRECTION vs 续82  (do NOT trust the old id0/id1 rows)
============================================================================
续82 attributed id 0/1 to handlers `0x4499f0` and `0x490c0`. BOTH were wrong:
  * `0x490c0` is a 5-hex-digit TYPO (below the image base 0x400000); the real
    address `0x490C00` disassembles as data/junk.
  * `0x4499f0` actually self-asserts **id 29** (`cmp ax, 0x1d` at 0x449a98),
    not 0/1. Evidence: it loads `[ctx+0]` at 0x449a6f and compares to 0x1d.
The REAL id-0 handlers are found only via the zero-test idiom and were
invisible to 续82's narrow `cmp [ctx+0], imm` scan. The REAL id-1 handler
(`0x484f34`) is found via the decrement idiom. This map supersedes 续82.

============================================================================
EVENT-TYPE id -> handler-address list  (derived from _evt_scan_wide.py)
============================================================================
A handler may appear under several ids if it self-asserts more than one id
(the dispatch groups related ids onto one function).
"""
# id -> list of handler addresses (each address is a self-asserting handler)
HANDLERS = {
    0:  [0x4a3df3, 0x4c2d5b, 0x45f020, 0x4accb0, 0x4da170, 0x4daf20],
    1:  [0x484f34],
    2:  [0x45f020, 0x45dc50, 0x461510, 0x488993],
    3:  [0x4accb0, 0x4da170, 0x4daf20, 0x447520, 0x450b90, 0x4608b7, 0x461da0, 0x44d950],
    4:  [0x41ddd5, 0x4c9db0],
    5:  [0x41ddd5, 0x4c9db0, 0x4a7000],
    6:  [0x45cc40, 0x4d1080],
    7:  [0x45cc40, 0x4d1080],
    8:  [0x44a120],
    9:  [0x441750, 0x44ca90, 0x45e78c, 0x460420, 0x46e2e0, 0x470260, 0x4b4b20, 0x4b4d10],
    10: [0x4e7e10],
    11: [0x4d34cb],
    13: [0x4146c0, 0x415b70, 0x41adb0, 0x4c34cf, 0x4c3610, 0x4d5560, 0x4d83e0, 0x4e82c0],
    14: [0x4146c0, 0x415b70, 0x41adb0, 0x4c34cf, 0x4c3610, 0x4d5560, 0x4d83e0, 0x4e82c0, 0x41d980],
    15: [0x44d950, 0x41ddd5, 0x4c9db0, 0x4a7000, 0x444220, 0x460660, 0x4b3890, 0x4b3ac0, 0x4b3b58, 0x4d5a20],
    16: [0x4d5a20, 0x441cf0],
    17: [0x4d5a20, 0x4a7160],
    29: [0x4499f0],
}

# Confidence per (id, handler). 'strong' = cmp-imm idiom; 'medium' = zero-test /
# decrement idiom (id 0/1 only).
CONFIDENCE = {
    # id 0 — all medium (zero-test idiom; some are internal guards inside id-2/3 handlers)
    0: {0x4a3df3:'medium', 0x4c2d5b:'medium', 0x45f020:'medium',
        0x4accb0:'medium', 0x4da170:'medium', 0x4daf20:'medium'},
    # id 1 — medium (decrement idiom)
    1: {0x484f34:'medium'},
    # id 2 — strong (via-load cmp 2)
    2: {0x45f020:'strong', 0x45dc50:'strong', 0x461510:'strong', 0x488993:'strong'},
    # id 3 — strong (via-load cmp 3)
    3: {0x4accb0:'strong', 0x4da170:'strong', 0x4daf20:'strong', 0x447520:'strong',
        0x450b90:'strong', 0x4608b7:'strong', 0x461da0:'strong', 0x44d950:'strong'},
    # id 4/5 — strong
    4: {0x41ddd5:'strong', 0x4c9db0:'strong'},
    5: {0x41ddd5:'strong', 0x4c9db0:'strong', 0x4a7000:'strong'},
    # id 6/7 — strong
    6: {0x45cc40:'strong', 0x4d1080:'strong'},
    7: {0x45cc40:'strong', 0x4d1080:'strong'},
    # id 8 — strong
    8: {0x44a120:'strong'},
    # id 9 — strong (0x4b4b20/0x44ca90 verified 续82)
    9: {0x441750:'strong', 0x44ca90:'strong', 0x45e78c:'strong', 0x460420:'strong',
        0x46e2e0:'strong', 0x470260:'strong', 0x4b4b20:'strong', 0x4b4d10:'strong'},
    # id 10 — strong
    10: {0x4e7e10:'strong'},
    # id 11 — strong
    11: {0x4d34cb:'strong'},
    # id 13/14 — strong (via-load cmp 13/14); 0x4e82c0 dual-asserts both
    13: {0x4146c0:'strong', 0x415b70:'strong', 0x41adb0:'strong', 0x4c34cf:'strong',
         0x4c3610:'strong', 0x4d5560:'strong', 0x4d83e0:'strong', 0x4e82c0:'strong'},
    14: {0x4146c0:'strong', 0x415b70:'strong', 0x41adb0:'strong', 0x4c34cf:'strong',
         0x4c3610:'strong', 0x4d5560:'strong', 0x4d83e0:'strong', 0x4e82c0:'strong',
         0x41d980:'strong'},
    # id 15 — strong
    15: {0x44d950:'strong', 0x41ddd5:'strong', 0x4c9db0:'strong', 0x4a7000:'strong',
         0x444220:'strong', 0x460660:'strong', 0x4b3890:'strong', 0x4b3ac0:'strong',
         0x4b3b58:'strong', 0x4d5a20:'strong'},
    # id 16/17 — strong
    16: {0x4d5a20:'strong', 0x441cf0:'strong'},
    17: {0x4d5a20:'strong', 0x4a7160:'strong'},
    # id 29 — strong (via-load cmp 0x1d)
    29: {0x4499f0:'strong'},
}

# Handlers whose id-assertion + [ctx+8] predicate were ALREADY decoded 续81/续82
# (read [ctx+8]=arg, compare to a runtime value, then FIRE or execute effect).
DECODED_CONDITIONS = {
    0x4e82c0: "id13: 玩家当前所在国 idx == arg (读 [arg-prov*5+0x519548]); "
              "id14: 当前气候组 == arg (读 [arg-prov*5+0x519548].byte[1]); "
              "门控 [0x516638]&0x14; calls getCtx+FIRE",
    0x4e7e10: "id10: 事件关联国 idx == arg (读 [arg-prov*14+0x5179b8]); "
              "门控 [ctx+0xc]&2==0; 成功→子求值 0x49f610 + FIRE(1)",
    0x4b4b20: "id9: 调 0x49f430(arg) 返回值 == 存储值 → FIRE (续82)",
    0x44ca90: "id9 EFFECT: 显示 msg 0x1224..0x1227 + 查 [0x52063c] 全局门控 (续82)",
    0x4b3ac0: "id15 EFFECT: 按 byte[obj+0x1b]&7 跳表派发 7 子例程 (续82)",
    0x4499f0: "id29: 读 [ctx+0] 自断言 == 0x1d(29); 调 getCtx(0x449a66)+FIRE(0x449a8a); "
              "尾部 msg/概率分支 (续106 新定位; 原 续82 误记为 id0/1)",
}

# Handlers whose id is known (strong/medium) but whose [ctx+8] predicate is
# NOT yet decoded. Follow-up: per-handler reverse of the arg<->runtime compare.
CONDITIONS_PENDING = [
    0x45dc50, 0x461510, 0x488993, 0x447520, 0x450b90, 0x4608b7, 0x461da0, 0x44d950,
    0x41ddd5, 0x4c9db0, 0x4a7000, 0x45cc40, 0x4d1080, 0x44a120,
    0x441750, 0x45e78c, 0x460420, 0x46e2e0, 0x470260, 0x4b4d10,
    0x4e7e10, 0x4d34cb,
    0x4146c0, 0x415b70, 0x41adb0, 0x4c34cf, 0x4c3610, 0x4d5560, 0x4d83e0, 0x41d980,
    0x444220, 0x460660, 0x4b3890, 0x4b3b58, 0x4d5a20, 0x441cf0, 0x4a7160,
    0x4a3df3, 0x4c2d5b, 0x45f020, 0x4accb0, 0x4da170, 0x4daf20,  # id-0 candidates (medium)
    0x484f34,  # id-1 candidate (medium)
]

# Lower-confidence / ambiguous — listed for completeness, NOT asserted by self-test.
# 0x45f020/0x4accb0/0x4da170/0x4daf20 assert BOTH a strong id (2 or 3) AND id 0;
# the id-0 branch is likely an internal guard inside an id-2/3 handler.
LOW_CONF = {
    4:  [0x428990, 0x429380, 0x43c130],
    28: [0x531278],
}

def handlers_for(event_id):
    return HANDLERS.get(event_id, [])

def all_ids():
    return sorted(HANDLERS)

def confidence_of(event_id, handler):
    return CONFIDENCE.get(event_id, {}).get(handler)

# ---- self-tests: structural facts only (no runtime data needed) ----
def _self_test():
    all_h = sorted({h for v in HANDLERS.values() for h in v})
    # 49 distinct handler functions
    assert len(all_h) == 49, f"expected 49 distinct handlers, got {len(all_h)}"
    # 18 distinct event ids
    assert len(HANDLERS) == 18, f"expected 18 ids, got {len(HANDLERS)}"
    assert all_ids() == [0,1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,29]

    # every address is a plausible code address
    for h in all_h:
        assert 0x400000 <= h < 0x600000, f"bad handler addr {h:#x}"

    # boundary ids must NOT appear
    assert 0x31 not in HANDLERS, "0x31 is a province boundary, not an event id"
    assert 0x3f not in HANDLERS, "0x3f is the max-id boundary, not an event id"
    # the 续82 typo address must NOT be present
    assert 0x490c0 not in all_h, "0x490c0 is a typo'd bad address; must not appear"

    # key verified handlers present
    for hid in (0x4e82c0, 0x4e7e10, 0x4b4b20, 0x44ca90, 0x4b3ac0, 0x4499f0,
                0x4a3df3, 0x484f34, 0x4d5a20):
        assert hid in all_h, f"missing known handler {hid:#x}"

    # structural relationships
    assert 0x4e82c0 in handlers_for(13) and 0x4e82c0 in handlers_for(14)
    assert 0x4e7e10 in handlers_for(10)
    assert 0x4b3ac0 in handlers_for(15)
    assert 0x4b4b20 in handlers_for(9) and 0x44ca90 in handlers_for(9)
    assert 0x4499f0 in handlers_for(29)          # corrected: id 29, NOT 0/1
    assert 0x484f34 in handlers_for(1)           # real id-1 handler
    assert 0x4a3df3 in handlers_for(0)           # id-0 via zero-test idiom

    # every decoded-condition handler is in the map
    for h in DECODED_CONDITIONS:
        assert h in all_h, f"decoded handler {h:#x} not in map"

    print("event_handlers_full_ref self-test: ALL PASS  "
          f"({len(all_h)} distinct handlers, {len(HANDLERS)} ids, "
          "0x31/0x3f boundaries excluded, 0x490c0 typo excluded)")

if __name__ == '__main__':
    _self_test()
