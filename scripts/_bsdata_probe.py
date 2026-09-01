# -*- coding: utf-8 -*-
"""_bsdata_probe.py — 续200 探针：BSDATA*.TR2 = 700 武将 × 59B 实体记录？

思路：
 1) 用 sndata_entity_decoder_ref 的 parse_decoder()/expand_seq() 取解码器 0x47f7b0 的
    「执行序读取列表」，配合 emu 游标日志，反算 **流偏移 -> 目标(实体偏移/表A/表B)** 有序映射。
 2) 用该映射解 BSDATA1/2.TR2 的 700 条 59B 记录，交叉验证姓名(GBK)与史实数值。
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")

import sndata_entity_decoder_ref as R
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP
from emu_harness import Emu

E = 7
ENT = R.ENTITY_BASE + E * R.ENTITY_STRIDE
sites = R.parse_decoder()
expanded = R.expand_seq(sites, E)          # [(rtype, abs_addr)] 执行序

# ---- emu 取游标序列，把 expanded 与流偏移对齐 ----
e = Emu()
SBUF = e.alloc(0x80)
e.write(SBUF, bytes((k % 256) for k in range(0x60)))
log = []
def stub(mu, a, s, ud):
    if a == R.ALLOC_STUB:
        mu.reg_write(UC_X86_REG_EAX, SBUF); mu.reg_write(UC_X86_REG_EIP, R.ALLOC_RET)
def rd(mu, a, s, ud):
    if a in (R.READ_BYTE, R.READ_WORD):
        log.append((a, int.from_bytes(mu.mem_read(0x522c98, 4), "little") - SBUF))
h1 = e.mu.hook_add(UC_HOOK_CODE, stub); h2 = e.mu.hook_add(UC_HOOK_CODE, rd)
e.call(R.DEC, [E, 0], max_steps=0x200000)
e.mu.hook_del(h1); e.mu.hook_del(h2)

print("[*] expanded=%d  emu_reads=%d" % (len(expanded), len(log)))
assert len(expanded) == len(log) == 49

MAP = []   # (stream_off, size, kind, off_desc)
for (rtype, addr), (fa, soff) in zip(expanded, log):
    size = 1 if rtype == "byte" else 2
    if addr is None:
        kind, od = "local", None
    elif R.ENTITY_BASE <= addr < R.ENTITY_BASE + 0x2f * 400 and (addr - R.ENTITY_BASE) % 0x2f == (ENT - R.ENTITY_BASE) % 0x2f or (ENT <= addr < ENT + 0x2f):
        kind, od = "entity", addr - ENT
    elif 0x521aa8 <= addr < 0x521aa8 + 0x2000:
        kind, od = "tblA", addr - (0x521aa8 + E * 7)
    elif 0x520660 <= addr < 0x520660 + 0x2000:
        kind, od = "tblB", addr - (0x520660 + E * 7)
    else:
        kind, od = "?", addr
    MAP.append((soff, size, kind, od))

tot = sum(m[1] for m in MAP)
print("[*] 解码器消费流字节总数 = %d" % tot)
print("[*] 映射表（流偏移 -> 目标）:")
for soff, size, kind, od in MAP:
    print("    +0x%02x %dB  %-6s %s" % (soff, size, kind,
          ("+0x%02x" % od) if isinstance(od, int) and kind in ("entity","tblA","tblB") else od))

# ---- 用映射解 BSDATA ----
def decode(rec):
    out = {"tblA": bytearray(7), "tblB": bytearray(7), "ent": {}}
    for soff, size, kind, od in MAP:
        v = int.from_bytes(rec[soff:soff+size], "little")
        if kind == "tblA":   out["tblA"][od] = v
        elif kind == "tblB": out["tblB"][od] = v
        elif kind == "entity": out["ent"][od] = v
    return out

def gbk(bs):
    z = bytes(bs).split(b"\x00")[0]
    try: return z.decode("gbk")
    except Exception: return "<%s>" % bytes(bs).hex()

for fn in ("BSDATA1", "BSDATA2"):
    b = open(os.path.join(ORIG, fn + ".TR2"), "rb").read()
    n = len(b) // 59
    print("\n=== %s: %d B = %d x 59 (余 %d) ===" % (fn, len(b), n, len(b) % 59))
    for i in list(range(6)) + [12, 13, 16, 26, 100, 699]:
        r = b[i*59:(i+1)*59]
        d = decode(r)
        ent = d["ent"]
        print("  #%3d %s%s | ent+24国=%s +25城=%s +26功=%s +2a主=%s" % (
            i, gbk(d["tblA"]), gbk(d["tblB"]),
            ent.get(0x24), ent.get(0x25), ent.get(0x26), ent.get(0x2a)))
    if fn == "BSDATA1":
        names = []
        for i in range(n):
            d = decode(b[i*59:(i+1)*59])
            names.append(gbk(d["tblA"]) + gbk(d["tblB"]))
        bad = [i for i, s in enumerate(names) if s.startswith("<")]
        print("  [*] GBK 解码失败条数: %d / %d" % (len(bad), n))
        print("  [*] 非空姓名条数: %d" % sum(1 for s in names if s.strip()))
        json.dump(names, open(os.path.join(HERE, "_bsdata_names.json"), "w"),
                  ensure_ascii=False, indent=0)
