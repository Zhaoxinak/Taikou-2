# P1 搬家前置: 池区间 [0x519868,0x51DC56) dword 窗口的逐点语境清单
# 输出 _reloc_manifest.json: 每处 = 节/偏移/所属指令(capstone)/窗口值/偏移量
import struct, json, pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe"
pe = pefile.PE(EXE)
BASE = pe.OPTIONAL_HEADER.ImageBase
LO, HI = 0x519868, 0x51DC56
EB = 0x519868

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

out = []
for s in pe.sections:
    nm = s.Name.rstrip(b"\0").decode()
    if nm in (".rsrc",):
        continue
    data = s.get_data()
    s_va = BASE + s.VirtualAddress
    # 本节解码指令表(线性+重同步)
    ins_map = {}
    pos, end = 0, len(data)
    while pos < end:
        prog = False
        for ins in md.disasm(data[pos:end], s_va + pos):
            prog = True
            pos = ins.address - s_va + len(ins.bytes)
            ins_map[ins.address] = ins
        if not prog:
            pos += 1
    for p in range(len(data) - 3):
        v = struct.unpack_from("<I", data, p)[0]
        if LO <= v < HI:
            va = s_va + p
            ins = None
            for back in range(0, 12):
                ins = ins_map.get(va - back)
                if ins:
                    break
            rel = v - EB
            out.append({
                "sec": nm, "off": p, "va": va, "val": v, "rel": rel,
                "ins": ("%s %s" % (ins.mnemonic, ins.op_str)) if ins else "(数据/未解码)",
                "ins_va": (ins.address if ins else 0),
            })
from collections import Counter
c = Counter(o["sec"] for o in out)
print("窗口总数:", dict(c))
# 非 .text 的单独列出(那些是 MOD 自己的常数)
for o in out:
    if o["sec"] != ".text" or o["rel"] not in (0,):
        pass
json.dump(out, open("_reloc_manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# 打印非零偏移点全集供人工复核
n0 = sum(1 for o in out if o["rel"] == 0)
print("EBASE 精确 x%d, 变体 x%d:" % (n0, len(out) - n0))
for o in out:
    if o["rel"] != 0:
        print("  [%s +0x%X] VA=0x%06X rel=%3d  in `%s` (@0x%06X)" % (
            o["sec"], o["off"], o["va"], o["rel"], o["ins"], o["ins_va"]))
