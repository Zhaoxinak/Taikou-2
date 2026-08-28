# -*- coding: utf-8 -*-
"""
event_id_dispatch_ref.py  —  Reference model of the Taikou2 EVENT DISPATCH.

Reverse-engineered from the unpacked image (scripts/_unpacked_mem.bin) and
confirmed by disassembly of every candidate handler enumerated by
_evt_enum3.py (liveness-correct opcode scanner).

KEY FINDING (2026-08-29, 续82)
-------------------------------
The event system dispatches by an **event-type id** stored at `[ctx+0]`
(word) inside the context object returned by `0x49f6b0` (= 0x516610, a
runtime-managed object). Each handler method self-asserts its own id:

    mov  reg, [ctx]        ; opcode / event-type id (word)
    cmp  reg, <id>         ; assert this handler owns <id>

There are (at least) TWO dispatch tables indexed by the same id space
(0..~60): a **CONDITION** table (method reads [ctx+8]=arg, tests a runtime
predicate, then `call 0x49b860` to fire) and an **EFFECT** table (method
executes the event's scripted consequences: messages, state changes).

This supersedes the 续81 view that every method is purely a "condition
evaluator". Some low ids are conditions, some are effects, some have BOTH a
condition and an effect handler (e.g. id 9). The dispatch itself is still a
C++ vtable (call [reg], 0-relative) — the static image contains only the
methods, not the vtable; full id->handler mapping therefore requires a
runtime vtable dump (Unicorn). NOTE: this is NOT blocked — the original game
files exist at <project>/Taikou2 Original/ (111 files, verified); the old
"scenario data is empty" claim was a path mistake. What IS statically
reliable here is the per-method id assertion + the condition/effect
classification below.

ctx contract (verified 续81, unchanged):
    [ctx+0]  word  event-type id      (== opcode in condition methods)
    [ctx+8]  word  arg               (compared against a runtime value)
    [ctx+0xc] word flags             (extra gate, e.g. bit 2 in 0x4e7e10)

Handlers decoded so far (handler -> id(s), kind):
    CONDITION:
      0x4e82c0  id 13 (current province == arg), id 14 (climate group == arg)
      0x4e7e10  id 10 (associated province == arg; flags&2 gates)
      0x4b4b20  id 9  (calls 0x49f430(arg); compares result to stored val)
    EFFECT:
      0x44ca90  id 9  (renders msg 0x1224..0x1227; checks global 0x52063c)
      0x4b3ac0  id 15 (renders messages; checks global 0x52063c)
      0x4499f0  id 0/1 (near-identical effector sibling)
      0x490c0   id 0/1 (near-identical effector sibling)
"""

# handler -> set of event-type ids it asserts, and its kind
HANDLERS = {
    # condition methods (read [ctx+8] arg, test predicate, fire)
    0x4e82c0:  {'ids': (13, 14), 'kind': 'condition',
                'desc': 'id13: current province idx == arg; '
                        'id14: current climate-group == arg'},
    0x4e7e10:  {'ids': (10,),    'kind': 'condition',
                'desc': 'id10: associated-province idx == arg (flags&2 gates)'},
    0x4b4b20:  {'ids': (9,),     'kind': 'condition',
                'desc': 'id9: 0x49f430(arg) result == stored value'},
    # effect methods (execute event consequences)
    0x44ca90:  {'ids': (9,),     'kind': 'effect',
                'desc': 'id9: renders messages 0x1224..0x1227; checks global 0x52063c'},
    0x4b3ac0:  {'ids': (15,),    'kind': 'effect',
                'desc': 'id15: renders messages; checks global 0x52063c'},
    0x4499f0:  {'ids': (0, 1),   'kind': 'effect',
                'desc': 'id0/1: effector (near-identical sibling of 0x490c0)'},
    0x490c0:   {'ids': (0, 1),   'kind': 'effect',
                'desc': 'id0/1: effector (near-identical sibling of 0x4499f0)'},
}

# reverse: id -> handlers
def handlers_for(event_id):
    return [h for h, info in HANDLERS.items() if event_id in info['ids']]

def kind_of(handler):
    return HANDLERS.get(handler, {}).get('kind')

# ---- self-tests: assert the *structural* facts (no runtime data needed) ----
def _self_test():
    # id 13/14 share one condition method
    assert handlers_for(13) == [0x4e82c0]
    assert handlers_for(14) == [0x4e82c0]
    # id 10 is a single condition method
    assert handlers_for(10) == [0x4e7e10]
    # id 9 has BOTH a condition (0x4b4b20) and an effect (0x44ca90)
    h9 = handlers_for(9)
    assert 0x4b4b20 in h9 and 0x44ca90 in h9
    assert kind_of(0x4b4b20) == 'condition'
    assert kind_of(0x44ca90) == 'effect'
    # id 0/1 have two effect siblings
    assert set(handlers_for(0)) == {0x4499f0, 0x490c0}
    assert set(handlers_for(1)) == {0x4499f0, 0x490c0}
    # id 15 is an effect
    assert handlers_for(15) == [0x4b3ac0]
    print("event_id_dispatch_ref self-test: ALL PASS")

if __name__ == '__main__':
    _self_test()
