# -*- coding: utf-8 -*-
"""
event_cond_ref.py  —  Reference model of the Taikou2 event-CONDITION evaluators.

Reverse-engineered from the unpacked image (scripts/_unpacked_mem.bin):

  EVALUATOR  0x4e82c0  (condition handler for opcodes 13 & 14)
  EVALUATOR  0x4e7e10  (condition handler for opcode 10)

Shared contract (verified by disassembly):
  * ctx is obtained via   call 0x49f6b0            -> edi/esi = event context
  * opcode  lives at [ctx + 0]   (word)
  * arg     lives at [ctx + 8]   (word)            -> compared against a value
  * flags   lives at [ctx + 0xc] (word/byte)       -> extra gate (e.g. bit 2)
  * on match: call sub-eval 0x4e83e0 / 0x49f610, then fire via 0x49b860 (+ GUI)

Dispatch: C++ VTABLE (call [reg], 0-relative). No static/dynamic indexed table
exists (exhaustively ruled out: literal fn-ptr scan, jmp[reg*4+imm] table scan,
call[reg*4+imm] table scan, all negative). Full opcode->handler map therefore
requires a runtime vtable dump (Unicorn). Only opcodes 10/13/14 are decoded here.

This module is a STRUCTURAL reference (the control flow is exact). The
"current province" value normally comes from runtime (0x44e280 on ctx); we
expose it as an injectable input so the branch logic is testable.
"""
# ----- decoded opcodes -----
OP_PROVINCE_PARAM = 10   # 事件关联国 == arg   (0x4e7e10)
OP_PROVINCE_CUR   = 13   # 当前所在国 == arg   (0x4e82c0)
OP_CLIMATE_CUR    = 14   # 当前气候组 == arg   (0x4e82c0)

# climate group -> is "snow country" (per GAME_DATA_SPEC 3.9.7: +1 in {0,2,4})
SNOW_GROUPS = {0, 2, 4}


def eval_4e82c0(opcode, arg, cur_prov_idx, cur_climate_group, flags=0):
    """Models 0x4e82c0 (opcodes 13 / 14).
    Returns True if the condition holds (would fire the event)."""
    if opcode == OP_PROVINCE_CUR:        # 13: 当前所在国 == arg
        return cur_prov_idx == arg
    if opcode == OP_CLIMATE_CUR:         # 14: 当前气候组 == arg
        return cur_climate_group == arg
    return False


def eval_4e7e10(opcode, arg, assoc_prov_idx, flags=0):
    """Models 0x4e7e10 (opcode 10).
    arg compared against the province index derived from the event's
    associated param struct (byte[param+0x24] -> province-politics entry -> index)."""
    if opcode != OP_PROVINCE_PARAM:
        return False
    # 0x4e7e94: test byte ptr [ctx+0xc], 2  -> flag gating
    if flags & 2:
        return False
    return assoc_prov_idx == arg


# ---- self-checks (assert the *decoded branch semantics*, not runtime data) ----
def _self_test():
    assert eval_4e82c0(13, 5, cur_prov_idx=5, cur_climate_group=0) is True
    assert eval_4e82c0(13, 5, cur_prov_idx=6, cur_climate_group=0) is False
    assert eval_4e82c0(14, 2, cur_prov_idx=0, cur_climate_group=2) is True
    assert eval_4e82c0(14, 4, cur_prov_idx=0, cur_climate_group=2) is False
    assert eval_4e82c0(99, 0, 0, 0) is False            # unknown opcode -> no fire
    assert eval_4e7e10(10, 7, assoc_prov_idx=7) is True
    assert eval_4e7e10(10, 7, assoc_prov_idx=3) is False
    assert eval_4e7e10(10, 7, assoc_prov_idx=7, flags=2) is False  # flag bit2 gates
    print("event_cond_ref self-test: ALL PASS")


if __name__ == '__main__':
    _self_test()
