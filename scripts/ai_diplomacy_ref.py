# -*- coding: utf-8 -*-
"""
ai_diplomacy_ref.py -- Reference model of the Taikou2 AI ACTIVE DIPLOMACY
DECISION subsystem. This was the LAST unbroken item of the diplomacy module
(续89 / 续96 下一步①). Reverse-engineered 2026-08-29 (续104) from the
unpacked image (scripts/_unpacked_mem.bin, flat map, off = va - 0x400000).

This CLOSES the diplomacy module end-to-end:
  - storage matrix + setters            (续95)
  - envoy-return settlement + success/fail determinism (续96)
  - AI initiative (this file, 续104)

--------------------------------------------------------------------------
CALL CHAIN -- the AI initiates diplomacy every AI daimyo's turn
--------------------------------------------------------------------------
  0x4a0d50  TOP-LEVEL AI TURN DRIVER        (per daimyo / per turn)
     -> 0x4a6ba0  AI "think" entry
          (mode arg 1/6/11/21...; runs a FIXED sequence of AI subsystems;
           SKIPPED entirely if dword[0x52060c] != 0)
        -> 0x4a70b0  PER-PROVINCE AI DISPATCH
             (loops 49 provinces @0x5179b8 stride14; for each with valid
              lord (word[+4] < 0x172 = 370) and matching status byte
              (byte[0x519640+i] == global flag 0x5205f2, or == 0x1f when
              flag==1), calls the specialized sub-deciders)
           -> 0x4a84e0  *** AI DIPLOMACY DECISION ***   (focus of this file)
           -> 0x4a8250 / 0x4a8870 / 0x4a8e80 / 0x4a97d0 / 0x4a92c0 / 0x4a94e0
                            (the OTHER AI decisions: attack / develop /
                             recruit / etc. -- NOT diplomacy, still to label)
  Gated by 0x4a0d10 (is-AI-active guard: returns nonzero => skip the block)
  and skip-flag dword[0x52060c].

--------------------------------------------------------------------------
0x4a84e0  AI DIPLOMACY DECISION (for province `self`)
--------------------------------------------------------------------------
  * builds the 国力 (national power) table 0x5259e8 via 0x4a8840, which calls
    0x49faf0 once per province.
        国力(prov) = sum over province's castle linked-list of
                     byte[castle+0xf] * byte[castle+0xc]   (castle military)
                     scaled,  +  province byte[0xc] & 0xf  weighted,
                     CAP 0xea60 (60000).
  * LOOP 1: among provinces esi where  lord<370  AND
            get_master_vassal(esi, self) == 2   (主从関係 == 2)
            pick the one with MAX  word[providx*2 + 0x5259e8]  (国力).
            -> set_master_vassal(self, esi, 0)              ; clear the tie
            -> set_diplomacy(self, esi, min(rel+2, 7))      ; improve +2, cap 7
            -> announce MSGX 0xd1f
  * LOOP 2: build a neighbor-province list via castle adjacency
            (castles with lord<200, get_master_vassal(prov, self) == 1),
            for each such province esi:
            -> set_master_vassal(self, esi, 0)
            -> set_diplomacy(self, esi, min(rel+2, 7))
            -> announce MSGX 0xd1e
  NET EFFECT: each turn the AI normalizes its hierarchical ties -- it releases
  overlord/subordinate bonds and converts them into plain friendly diplomatic
  relations, improving +2/turn toward the cap 7, and prioritizes the strongest
  powers (by 国力). Deterministic (no RNG), consistent with 续96.

--------------------------------------------------------------------------
CORRECTION to 续96's "AI 何时调 0x4b5bcb / 0x4b6095"
--------------------------------------------------------------------------
  friendly_success 0x4b5bcb  and  pressure_submit 0x4b6095  have ZERO direct
  (E8 rel32) callers. They are reached ONLY via the indirect envoy-return
  settlement dispatch  0x4b9250 -> 0x4b981c  (续95/96). The AI does NOT call
  them; it drives  set_diplomacy(0x49fe40) / set_master_vassal(0x49ff10)
  DIRECTLY inside 0x4a84e0. So there is no separate "AI triggers 0x4b5bcb"
  path -- the AI's active diplomacy IS the direct setter pass above.

--------------------------------------------------------------------------
HELPER FUNCTIONS
--------------------------------------------------------------------------
  0x49faf0  prov_power(prov)      -> word  (国力, cap 60000)   [49 callers]
  0x4a8840  build_power_tbl()     -> fills 0x5259e8[49]
  0x4ebca0  min(a + b, c)
  0x4a0d10  ai_active_guard()     -> nonzero == skip
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

import os

IMG = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000

# reference constants
TOP_AI_DRIVER   = 0x4a0d50
AI_THINK_ENTRY  = 0x4a6ba0
AI_PERPROV_DISP = 0x4a70b0
AI_DIPLO_DEC    = 0x4a84e0
SET_DIPLO       = 0x49fe40
SET_MASTER_VASS = 0x49ff10
GET_MASTER_VASS = 0x49fe70
GET_DIPLO       = 0x49fd60
FRIENDLY_SUCC   = 0x4b5bcb
PRESSURE_SUBMIT = 0x4b6095
PROV_POWER_FN   = 0x49faf0
BUILD_PW_TBL    = 0x4a8840
MIN_AB_C        = 0x4ebca0
POWER_TBL       = 0x5259e8
SKIP_FLAG       = 0x52060c
AI_ACTIVE_GUARD = 0x4a0d10

# other AI sub-deciders dispatched by 0x4a70b0 (NOT diplomacy -- still to label)
AI_OTHER_DEC = {
    0x4a8250: "attack/develop/recruit? (A)",
    0x4a8870: "attack/develop/recruit? (B)",
    0x4a8e80: "attack/develop/recruit? (C)",
    0x4a97d0: "attack/develop/recruit? (D)",
    0x4a92c0: "attack/develop/recruit? (E, gate for F)",
    0x4a94e0: "attack/develop/recruit? (F)",
}


def count_direct_callers(target, data):
    """Count direct `call rel32` (E8) callers of `target` via pure byte scan."""
    n = 0
    i = 0
    N = len(data)
    while i < N - 5:
        if data[i] == 0xE8:
            imm = int.from_bytes(data[i + 1:i + 5], 'little', signed=True)
            tgt = (BASE + i + 5 + imm) & 0xffffffff
            if tgt == target:
                n += 1
        i += 1
    return n


def self_test():
    with open(IMG, 'rb') as f:
        data = f.read()
    checks = []
    # (1) AI success handlers are indirect-only (envoy-return settlement)
    c_fs = count_direct_callers(FRIENDLY_SUCC, data)
    c_ps = count_direct_callers(PRESSURE_SUBMIT, data)
    checks.append(("friendly_success 0x4b5bcb has 0 direct E8 callers", c_fs == 0, c_fs))
    checks.append(("pressure_submit 0x4b6095 has 0 direct E8 callers", c_ps == 0, c_ps))
    # (2) AI diplomacy decision reachable from the top driver
    c84 = count_direct_callers(AI_DIPLO_DEC, data)
    c70 = count_direct_callers(AI_PERPROV_DISP, data)
    c6b = count_direct_callers(AI_THINK_ENTRY, data)
    checks.append(("0x4a84e0 (AI diplo dec) >=1 caller", c84 >= 1, c84))
    checks.append(("0x4a70b0 (per-prov dispatch) >=1 caller", c70 >= 1, c70))
    checks.append(("0x4a6ba0 (AI think entry) >=1 caller", c6b >= 1, c6b))
    # (3) prov_power called ~49 times (one per province) -- sanity anchor
    c_pw = count_direct_callers(PROV_POWER_FN, data)
    checks.append(("0x49faf0 (prov_power) called ~49x", 40 <= c_pw <= 60, c_pw))
    ok = True
    for name, cond, val in checks:
        print("  [%-4s] %s  (got %d)" % ("PASS" if cond else "FAIL", name, val))
        ok = ok and cond
    # informational only:
    c0d = count_direct_callers(TOP_AI_DRIVER, data)
    print("  [info ] 0x4a0d50 (top AI driver) direct callers = %d" % c0d)
    print("SELF_TEST:", "ALL PASS" if ok else "FAILURES PRESENT")
    return ok


if __name__ == "__main__":
    self_test()
