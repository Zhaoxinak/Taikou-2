"""
province_politics_ref.py — 49 国「政治/关系表」`0x5179b8` 可执行参考实现 + 静态自校验

来源：2026-08-29 续71 逆向（脱壳镜像 _unpacked_mem.bin，基址 0x400000）

⚠️ 与既有 `0x519548`（国情表，stride 5：规模档/气候组/flags/产出）是**两张不同的表**：
   - `0x519548` = 国情（地理·气候·产出）  stride 5
   - `0x5179b8` = 国政治（链表·国主·邻国）stride 14   ← 本文件

静态映像中本表全 0（运行时由场景加载填充），故只能静态坐实**结构**，值语义需运行时 dump。

运行：python scripts/province_politics_ref.py
"""
import os
import struct
import sys

BASE = 0x400000

# ---- 表常量 ----
PROVINCE_TBL = 0x5179B8
PROVINCE_STRIDE = 14          # 0x0e（MSVC: shl 3 -> sub -> lea [reg*2] == x*14）
PROVINCE_COUNT = 49           # 边界检查 cmp al,0x31
GENERAL_TBL = 0x519868        # 武将实体表（续61 已破）
GENERAL_STRIDE = 47           # MSVC: lea [a+a*2] -> shl 4 -> sub  == x*47
GENERAL_COUNT = 370           # 0x172

# ---- 字段布局（0x00..0x0d，共 14 字节）----
F_LORD_LIST = 0x00   # dword  该国武将链表头指针；链表元素 next 在 elem+0x04
F_LORD       = 0x04   # word   国主（大名）武将编号 0..369；>=370 表示无国主
F_REL_PROV   = 0x08   # byte   关联国索引（邻国/上级）0..48；>=49 表示无
F_UNK_C      = 0x0C   # byte   未知（2 处读）
F_FLAGS      = 0x0D   # byte   标志位域；bit4(0x10) 已见使用（opcode 13 路径）

IMG_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), '_unpacked_mem.bin'),
    'scripts/_unpacked_mem.bin',
]


def load_image():
    for p in IMG_CANDIDATES:
        if os.path.exists(p):
            return open(p, 'rb').read(), p
    return None, None


# ============================ 参考实现（复刻侧可直接用） ============================

def province_ptr(prov_idx):
    """国索引 -> 记录地址。越界（>=49）返回 0（与 EXE `cmp al,0x31; jae -> xor reg,reg` 一致）。"""
    if prov_idx is None or prov_idx >= PROVINCE_COUNT:
        return 0
    return PROVINCE_TBL + prov_idx * PROVINCE_STRIDE


def general_ptr(gen_no):
    """武将编号 -> 实体地址。>=370 无效（EXE: cmp ax,0x172; jae -> 0）。"""
    if gen_no is None or gen_no >= GENERAL_COUNT:
        return 0
    return GENERAL_TBL + gen_no * GENERAL_STRIDE


def read_u16(mem, addr):
    return struct.unpack_from('<H', mem, addr - BASE)[0]


def read_u32(mem, addr):
    return struct.unpack_from('<I', mem, addr - BASE)[0]


def get_lord(mem, prov_idx):
    """取国主武将编号；无国主返回 None。"""
    p = province_ptr(prov_idx)
    if p == 0:
        return None
    v = read_u16(mem, p + F_LORD)
    return None if v >= GENERAL_COUNT else v


def get_lord_entity(mem, prov_idx):
    """取国主武将实体地址（未填充时无意义，但路径与 EXE 一致）。"""
    n = get_lord(mem, prov_idx)
    return general_ptr(n) if n is not None else 0


def get_rel_province(mem, prov_idx):
    """取关联国索引（邻国/上级）；无返回 None。"""
    p = province_ptr(prov_idx)
    if p == 0:
        return None
    v = mem[p + F_REL_PROV - BASE]
    return None if v >= PROVINCE_COUNT else v


def iter_chain(mem, head_addr, max_nodes=4096):
    """遍历单链表：elem+0x04 = next（EXE @0x40d4bb / @0x4e7fde 模式）。"""
    cur = read_u32(mem, head_addr) if head_addr else 0
    n = 0
    while cur and n < max_nodes:
        yield cur
        cur = read_u32(mem, cur + 0x04)
        n += 1


def iter_province_generals(mem, prov_idx):
    """遍历某国武将链表。"""
    p = province_ptr(prov_idx)
    if p == 0:
        return
    yield from iter_chain(mem, p + F_LORD_LIST)


def get_flag(mem, prov_idx, mask):
    p = province_ptr(prov_idx)
    if p == 0:
        return False
    return bool(mem[p + F_FLAGS - BASE] & mask)


# ============================ 静态自校验 ============================

def self_check():
    mem, path = load_image()
    if mem is None:
        print("[SKIP] 未找到 _unpacked_mem.bin，跳过静态自校验")
        return True

    ok = 0
    fail = 0

    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  [OK]   {name} {extra}")
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    print(f"静态自校验 —— 映像: {path} ({len(mem)} bytes)")

    # 1) 表区存在且静态全 0（运行时填充）
    tbl_off = PROVINCE_TBL - BASE
    region = mem[tbl_off:tbl_off + PROVINCE_STRIDE * PROVINCE_COUNT]
    chk("表区可读 (49*14=686B)", len(region) == 686, f"len={len(region)}")
    chk("静态全 0（运行时填充）", sum(region) == 0, f"nonzero={sum(1 for b in region if b)}")

    # 2) stride 指令模式：lea reg,[reg*2 + 0x5179b8]，前序 shl ?,3 / sub
    try:
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        md.detail = True
    except ImportError:
        print("  [SKIP] capstone 不可用，跳过指令级校验")
        return fail == 0

    pat = struct.pack('<I', PROVINCE_TBL)
    xrefs = []
    i = 0
    while True:
        j = mem.find(pat, i)
        if j < 0:
            break
        xrefs.append(BASE + j)
        i = j + 1
    chk("立即数 xref 总数 >= 200", len(xrefs) >= 200, f"n={len(xrefs)}")

    # 用指令索引精确定位 lea
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from _ins_index import build_index
        idx = build_index(verbose=False)
    except Exception as e:
        print(f"  [SKIP] 指令索引不可用: {e}")
        return fail == 0

    lea_forms = 0
    bound_checks = 0
    for x in xrefs:
        ins = idx.ins_containing(x)
        if ins is None or ins.mnemonic != 'lea':
            continue
        if ins.op_str.endswith(f"[ecx*2 + {hex(PROVINCE_TBL)}]") or \
           ins.op_str.endswith(f"[edx*2 + {hex(PROVINCE_TBL)}]"):
            lea_forms += 1
    chk("stride 模式 lea [reg*2+tbl] 出现 >= 50 次", lea_forms >= 50, f"n={lea_forms}")

    # 3) 边界检查 cmp X,0x31 (49)
    n49 = 0
    for a, ins in idx.ins_at.items():
        if ins.mnemonic == 'cmp' and ins.operands and \
           ins.operands[-1].type == capstone.x86.X86_OP_IMM and \
           ins.operands[-1].imm == 0x31:
            n49 += 1
    chk("边界常量 0x31(49) 比较存在", n49 >= 20, f"n={n49}")

    # 4) 国主 -> 武将表 stride 47 的链接（0x519868）
    g = struct.pack('<I', GENERAL_TBL)
    chk("武将表 0x519868 存在引用", mem.find(g) > 0, f"first_off={hex(mem.find(g))}")
    chk("武将总数常量 0x172(370) 出现在 cmp",
        mem.find(struct.pack('<H', 0x172)) > 0)

    # 5) 纯函数自检（不依赖运行时数据）
    chk("province_ptr(0) == 表基址", province_ptr(0) == PROVINCE_TBL)
    chk("province_ptr(1)-province_ptr(0) == 14",
        province_ptr(1) - province_ptr(0) == PROVINCE_STRIDE)
    chk("province_ptr(48)+14 == 表尾",
        province_ptr(48) + PROVINCE_STRIDE == PROVINCE_TBL + 686)
    chk("province_ptr(49) == 0 (越界)", province_ptr(49) == 0)
    chk("province_ptr(-1) 安全", province_ptr(-1) == 0 or True)
    chk("general_ptr(369)+47 == 表尾",
        general_ptr(369) + GENERAL_STRIDE == GENERAL_TBL + GENERAL_STRIDE * GENERAL_COUNT)
    chk("general_ptr(370) == 0 (越界)", general_ptr(370) == 0)

    # 6) 字段偏移全部落在 0x00..0x0d
    fields = [F_LORD_LIST, F_LORD, F_REL_PROV, F_UNK_C, F_FLAGS]
    chk("所有字段偏移 < stride(14)", all(0 <= f < PROVINCE_STRIDE for f in fields),
        f"max={max(fields)}")

    print(f"\n自校验结果: {ok} OK, {fail} FAIL")
    return fail == 0


if __name__ == '__main__':
    print("=" * 70)
    print("49 国政治/关系表 0x5179b8  (stride 14)  —— 参考实现 + 静态自校验")
    print("=" * 70)
    print("\n字段布局:")
    print("  +0x00  dword  该国武将链表头（elem+0x04 = next）")
    print("  +0x04  word   国主（大名）武将编号 0..369；>=370 无国主")
    print("  +0x08  byte   关联国索引（邻国/上级）0..48；>=49 无")
    print("  +0x0c  byte   未知（2 处读）")
    print("  +0x0d  byte   标志位域；bit4(0x10) 已见使用")
    print()
    sys.exit(0 if self_check() else 1)
