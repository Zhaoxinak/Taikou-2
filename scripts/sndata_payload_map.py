# -*- coding: utf-8 -*-
"""
Static extractor for the SNDATA 49B payload decode (v2: record-pointer aware).

Architecture (reversed this session):
  * 0x47fc60 = record LOADER: copies record[6:49] -> global 0x522c88,
               record[0x13] -> 0x522c60, record[0x20] -> 0x522c70, and the
               header words into globals (0x5205fe etc.).
  * 0x4e8625 = main record LOOP: a content-based switch that calls a SEQUENCE
               of per-type handler functions (direct E8 calls). Each handler
               receives a pointer to the 49B record and reads record bytes via
               [rec_ptr + k] (k in 0..0x30), writing fields to 0x509xxx buffers.

This tool:
  1) enumerates handler functions called inside the 0x4e8625 processing region,
  2) for each handler, tracks the record pointer (a stack-arg-derived register)
     and resolves every strcpy/memcpy SRC that is [rec_ptr + k] to a record
     offset (and hence a payload offset if 6 <= k < 49), pairing it with the
     DST 0x509xxx buffer pushed for that call.

Output: sndata_handler_map.json
"""
import os, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

B1 = 0x522c60                          # record[0x13]
B2 = 0x522c70                          # record[0x20]
STR_COPY = {0x4ebfe0, 0x4ec010}        # strcpy / memcpy-ish helpers
REGS = ['eax', 'ecx', 'edx', 'ebx', 'esi', 'edi', 'ebp', 'esp']

def dis(va, maxb=8000, maxn=1500):
    code = IMG[va-BASE: va-BASE+maxb]
    out = []
    for i in md.disasm(code, va):
        out.append(i)
        if len(out) >= maxn:
            break
    return out

def is_buf(val):
    return 0x509000 <= val < 0x520000

def rec_offset_to_payload(k):
    """record offset k -> human label / payload offset (or None)."""
    if 6 <= k < 49:
        return ("payload+0x%02x" % (k - 6))
    if k == 0x13:
        return "rec[0x13]"
    if k == 0x20:
        return "rec[0x20]"
    return "rec+0x%x" % k

# ---- (1) enumerate handlers called inside the 0x4e8625 processing region ----
LOOP_LO, LOOP_HI = 0x4e8604, 0x4e89ef
handlers = set()
for i in dis(LOOP_LO, maxb=LOOP_HI-LOOP_LO+0x400, maxn=2500):
    if i.address > LOOP_HI:
        break
    if i.mnemonic == 'call' and i.op_str.startswith('0x'):
        tgt = int(i.op_str, 16)
        if BASE <= tgt < BASE + len(IMG):
            handlers.add(tgt)
handlers = sorted(handlers)
print("candidate handlers called from 0x4e8625: %d" % len(handlers))

# ---- (2) per-handler: track record pointer, resolve src/dst ----
def extract(handler):
    res = []
    reg = {}          # reg -> ('rec', off) | ('imm', val) | ('buf', val) | None
    push_win = []     # recent pushes: (kind, value, addr)  kind in rec/imm/buf

    def setreg(r, v):
        reg[r] = v

    for i in dis(handler):
        m, o = i.mnemonic, i.op_str
        # --- data-flow on registers ---
        if m in ('mov', 'lea') and ',' in o:
            dst, src = o.split(',', 1); dst, src = dst.strip(), src.strip()
            if dst in REGS and dst != 'esp':
                if src in reg:
                    setreg(dst, reg[src])
                elif src.startswith('0x'):
                    v = int(src, 16)
                    setreg(dst, ('buf', v) if is_buf(v) else ('imm', v))
                elif src.startswith('[') and src.endswith(']'):
                    inner = src[1:-1].strip()
                    # form: [esp+K]  (call arg = record pointer) or [reg] (alias)
                    if inner in reg:
                        setreg(dst, reg[inner])
                    elif inner.startswith('esp') or inner.startswith('ebp'):
                        # stack slot -> treat as a pointer source (record arg)
                        setreg(dst, ('rec', 0))
                    else:
                        # [reg + off] load -> alias the base reg's tracking
                        base = inner.split('+')[0].split('-')[0].strip()
                        if base in reg:
                            setreg(dst, reg[base])
                        else:
                            reg.pop(dst, None)
                else:
                    reg.pop(dst, None)
        elif m in ('add', 'sub') and ',' in o:
            dst, src = o.split(',', 1); dst, src = dst.strip(), src.strip()
            if dst in reg:
                if src.startswith('0x') and reg[dst] is not None and reg[dst][0] in ('rec', 'imm'):
                    delta = int(src, 16) if m == 'add' else -int(src, 16)
                    reg[dst] = (reg[dst][0], reg[dst][1] + delta)
                elif src in reg and reg[src] is not None:
                    # add reg, reg2 -> offset shift by reg2 if imm
                    if reg[src][0] == 'imm':
                        reg[dst] = (reg[dst][0], reg[dst][1] + (reg[src][1] if m=='add' else -reg[src][1]))
                    else:
                        reg.pop(dst, None)
                else:
                    reg.pop(dst, None)
        elif m == 'push':
            s = o.strip()
            kind, val = None, None
            if s in reg and reg[s] is not None:
                kind, val = reg[s]
            elif s.startswith('0x'):
                v = int(s, 16)
                kind, val = ('buf', v) if is_buf(v) else ('imm', v)
            if kind is not None:
                push_win.append((kind, val, i.address))
            if len(push_win) > 16:
                push_win.pop(0)
        elif m == 'call' and o.startswith('0x'):
            tgt = int(o, 16)
            if tgt in STR_COPY:
                # find a 'rec' src and a 'buf' dst in the push window
                recs = [(v, a) for (k, v, a) in push_win if k == 'rec']
                bufs = [(v, a) for (k, v, a) in push_win if k == 'buf']
                for (rv, ra) in recs:
                    for (bv, ba) in bufs:
                        res.append((hex(i.address), rec_offset_to_payload(rv), hex(bv)))
                # also catch concrete src like 0x522c60/0x522c70 (record bytes)
                for (kv, ka) in [(v, a) for (k, v, a) in push_win if k == 'imm']:
                    if kv in (B1, B2):
                        lbl = "rec[0x13]" if kv == B1 else "rec[0x20]"
                        for (bv, ba) in bufs:
                            res.append((hex(i.address), lbl, hex(bv)))
            push_win = []
        elif m in ('ret',):
            push_win = []
    return res

report = {}
for h in handlers:
    pairs = extract(h)
    if pairs:
        report[hex(h)] = pairs

with open(os.path.join(HERE, "sndata_handler_map.json"), "w") as f:
    json.dump(report, f, indent=1)

print("\nhandlers with payload->buffer mappings: %d" % len(report))
for h, pairs in sorted(report.items()):
    print("\n%s : %d pairs" % (h, len(pairs)))
    seen = set()
    for (cs, off, buf) in pairs:
        key = (off, buf)
        if key in seen:
            continue
        seen.add(key)
        print("    call@%-8s  %-12s -> %s" % (cs, off, buf))
