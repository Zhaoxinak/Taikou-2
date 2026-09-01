# -*- coding: utf-8 -*-
"""XOR-decode SNDATA1/2 disk files and verify against known province stream offsets.
Key = header[0x12] ^ header[0x13]. Encrypted stream = file[0x598:].
Byte map (stream offsets): entity pool @22 (370x59), castle @21852 (200x26), province @27052 (49x5).
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

import os, json

BASE = _ROOT + '/Taikou2 Original'

def decode(path):
    raw = open(os.path.join(BASE, path), "rb").read()
    assert raw[:16] == b"TAIKOU2_SCENARIO", raw[:16]
    key = raw[0x12] ^ raw[0x13]
    stream = bytes(b ^ key for b in raw[0x598:])
    return raw, key, stream

for fn in ("SNDATA1.TR2", "SNDATA2.TR2"):
    raw, key, stream = decode(fn)
    print(f"\n##### {fn}: key={key:#04x} stream_len={len(stream)}")
    # province @27052, 49x5
    prov = stream[27052:27052+49*5]
    print("  province[0] raw:", list(prov[:5]), "  province[1] raw:", list(prov[5:10]))
    # entity pool @22, 370x59 -> first record 59 bytes
    ent = stream[22:22+59]
    print("  entity[0] raw(59):", list(ent))
    # castle @21852, 200x26 -> first 2 records
    cas = stream[21852:21852+200*26]
    print("  castle[0] raw(26):", list(cas[:26]))
    print("  castle[1] raw(26):", list(cas[26:52]))

# verification against province_spec
print("\n===== VERIFY province[0] vs province_spec =====")
spec = json.load(open("province_spec.json", encoding='utf-8'))
exp = spec["scenarios"]["SNDATA1"][0]
raw, key, stream = decode("SNDATA1.TR2")
prov0 = stream[27052:27052+5]
print("  decoded prov0 bytes:", list(prov0))
print("  expected byte0=%d climate=%d flag=%d packed_u16=%d" % (
    exp["byte0"], exp["climate_group"], exp["flag_byte"], exp["packed_u16"]))
ok = (prov0[0]==exp["byte0"] and prov0[1]==exp["climate_group"] and
      prov0[2]==exp["flag_byte"] and (prov0[3]|(prov0[4]<<8))==exp["packed_u16"])
print("  MATCH:", ok)
# also check province 1
exp1 = spec["scenarios"]["SNDATA1"][1]
prov1 = stream[27057:27057+5]
print("  prov1 decoded:", list(prov1), " expected byte0=%d packed=%d" % (exp1["byte0"], exp1["packed_u16"]))
