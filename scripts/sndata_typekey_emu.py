# -*- coding: utf-8 -*-
"""续227 emu 探针：直接调用 0x462fd0（六类解析器），扫 id 值域，提取完整 id->type(class) 映射。
0x49f6b0 返回全局当前记录指针 0x516610，故只要把 id 写到 word[0x516610] 即可驱动解析器。
纯 emu，不 boot 主循环。"""
from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL,
                     UC_HOOK_MEM_WRITE_UNMAPPED, UC_HOOK_MEM_READ_UNMAPPED)
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP
import struct

BASE = 0x400000
RESOLVER = 0x462fd0
RESOLVER_RET = 0x4630b7   # ret 之前
REC_PTR = 0x516610        # 0x49f6b0 返回的全局当前记录指针
ENT_IDX = 0x516624        # 0x49f5e0 用的当前实体 idx
GLOBAL_FLAG = 0x516638    # 0x462fd0 在 class1 分支 test byte[0x516638],4

def load_image():
    with open("_unpacked_mem.bin", "rb") as f:
        return f.read()

MEM = load_image()
N = len(MEM)

def make_uc():
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    # map image
    uc.mem_map(BASE, N + 0x1000, UC_PROT_ALL)
    uc.mem_write(BASE, MEM)
    # IAT stub page @0x3000 (续209 通则: 任意 IAT call 直接 ret 兜底)
    uc.mem_map(0x3000, 0x1000, UC_PROT_ALL)
    uc.mem_write(0x3000, b"\xc3" * 0x1000)   # 0xc3 = ret
    # 运行期堆区（enqueue/name 副作用写入的缓冲通常不在静态映像内；放在映像末尾 0x602000 之上）
    uc.mem_map(0x604000, 0x400000, UC_PROT_ALL)  # 0x604000..0xA04000 零填充
    # stack
    STACK = 0xC00000
    uc.mem_map(STACK, 0x10000, UC_PROT_ALL)
    uc.reg_write(UC_X86_REG_ESP, STACK + 0x8000)
    # 运行期堆/未映射副作用（enqueue/alloc 写入我们不关心的缓冲）—— class 结果来自二分搜索，与之无关。
    # 关键修复：不能只返回 True 跳过——rep stosd 串存会破坏循环计数，且二分搜索的读若返回 0 会污染比较。
    # 改为惰性映射一个零填充页到故障地址，让访存真正完成（脏数据落在我们不关心的缓冲上，无害）。
    mapped_pages = set()
    def _skip(mu, access, address, size, value, data):
        page = address & ~0xfff
        if page not in mapped_pages:
            try:
                mu.mem_map(page, 0x1000, UC_PROT_ALL)
                mapped_pages.add(page)
            except Exception:
                pass
        return True
    uc.hook_add(UC_HOOK_MEM_WRITE_UNMAPPED | UC_HOOK_MEM_READ_UNMAPPED, _skip)
    return uc

def resolve(uc, idval, ent_idx=0, ent_high=0):
    # 写当前记录 id
    uc.mem_write(REC_PTR, struct.pack("<H", idval & 0xffff))
    # 清 class1 门控位（bit2 of byte[0x516638]），保证 class1 参与
    b = uc.mem_read(GLOBAL_FLAG, 1)[0]
    uc.mem_write(GLOBAL_FLAG, bytes([b & ~0x04]))
    # 设置实体 idx 与实体 0x2c 高位（class2 依赖）
    uc.mem_write(ENT_IDX, struct.pack("<H", ent_idx & 0xffff))
    ent_base = 0x519868 + ent_idx * 47
    cur = uc.mem_read(ent_base + 0x2c, 2)
    uc.mem_write(ent_base + 0x2c, struct.pack("<H", (struct.unpack("<H", cur)[0] & 0x00ff) | (ent_high << 8)))
    try:
        uc.emu_start(RESOLVER, RESOLVER_RET)
        eax = uc.reg_read(UC_X86_REG_EAX) & 0xffff
        return eax
    except Exception as e:
        eip = uc.reg_read(UC_X86_REG_EIP)
        return ("ERR", f"{str(e)[:30]}@0x{eip:x}")

def main():
    import sys
    hi = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0xff
    lo = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    # Pass A: 无实体（entity 0x2c 高位=0 -> class2 跳过）
    resA = {}
    for i in range(lo, hi + 1):
        uc = make_uc()
        resA[i] = resolve(uc, i, ent_idx=0, ent_high=0)
    # Pass B: 实体激活（entity 0x2c 高位=1 -> class2 参与）
    resB = {}
    for i in range(lo, hi + 1):
        uc = make_uc()
        resB[i] = resolve(uc, i, ent_idx=0, ent_high=1)
    # 汇总
    from collections import defaultdict
    byclassA = defaultdict(list)
    byclassB = defaultdict(list)
    diff = []
    for i in range(lo, hi + 1):
        byclassA[resA[i]].append(i)
        byclassB[resB[i]].append(i)
        if resA[i] != resB[i]:
            diff.append((i, resA[i], resB[i]))
    print(f"=== 续227 id->type 映射 (id 0x{lo:04x}..0x{hi:04x}) ===")
    print("PassA (无实体/class2 跳过):")
    for c in sorted(byclassA, key=lambda x: (x if isinstance(x,int) else 999,)):
        ids = byclassA[c]
        label = {0:"势(0)",1:"米(1)",2:"家(2)",3:"大(3)",4:"持(4)",5:"属(5)",0xffff:"未处理(ffff)"}.get(c, str(c))
        print(f"  class {label}: {len(ids)} 个 id  e.g. {ids[:12]}{'...' if len(ids)>12 else ''}")
    print("PassB (实体激活/class2 参与):")
    for c in sorted(byclassB, key=lambda x: (x if isinstance(x,int) else 999,)):
        ids = byclassB[c]
        label = {0:"势(0)",1:"米(1)",2:"家(2)",3:"大(3)",4:"持(4)",5:"属(5)",0xffff:"未处理(ffff)"}.get(c, str(c))
        print(f"  class {label}: {len(ids)} 个 id  e.g. {ids[:12]}{'...' if len(ids)>12 else ''}")
    print(f"class2 翻转 (PassA->PassB): {len(diff)} 个")
    for d in diff[:40]:
        print(f"    id=0x{d[0]:04x}: A={d[1]} B={d[2]}")
    # 特殊 id 检查
    for special in [1,2,3,9]:
        print(f"  id={special}: PassA={resA[special]} PassB={resB[special]}")

if __name__ == "__main__":
    main()
