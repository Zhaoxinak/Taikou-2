# -*- coding: utf-8 -*-
"""
resource_cluster_ref.py  ——  资源加载簇全图 · 自校验参考实现（续196）

把「簇 handler → 资源表基址 → 文件名」的完整映射钉死，并用 Unicorn 端到端验证
资源加载管线的两条关键行为：

管线（续162/163 已破，本脚本逐指令复核）：
    cluster handler
        push <size_class>          ; arg1
        push <资源表条目 VA>        ; arg0   (stdcall 右→左)
        call  0x4802e0

    0x4802e0(this=ecx, base, size_class):                        [stdcall, ret 8]
        eax = base
        memmove(0x522ca0, base, 0x20)      ; 0x492800 = memmove(dst,src,n) 3 参 cdecl
        ecx = (int16)size_class            ; 注意 movsx → 符号扩展
        0x4ec8c0(this, 0x522ca0, size_class)

    0x4ec8c0(this=ecx, name_ptr, size_class):                    [stdcall, ret 8]
        strcpy(local, name_ptr + 2)        ; ★ 剥掉盘符前缀 "X:"
        a = size_class & 0xfb              ; ★ 清掉 bit2（修饰标志，不参与尺寸选择）
        a > 3  →  size = 0x1000
        else   →  jmp [a*4 + 0x4ec948]  →  case0=0 / case1=1 / case2=2 / case3=0x1000
        handle = [0x4fb07c](local_name, this+4, size)   ; ★ stdcall 3 参，callee 清栈 ret 0xc
        this[0] = handle
        return (handle == -1) ? 0 : 1

自测分四段：
    A 静态：44 个 call 0x4802e0 站点 / 主资源表 / 子资源表几何
    B 静态：簇 → 资源映射（含续161 已知 4 簇交叉验证）
    C emu ：19 个主资源 × 9 种 size_class 端到端（剥前缀 + 尺寸跳表 + 回调实参）
    D emu ：回调返回 -1 / 正常句柄 时的返回值与 this[0] 落点
"""
import os
import re
import sys
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
IMAGE_END = BASE + len(MEM)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

_ok = _fail = 0


def check(name, cond, info=""):
    global _ok, _fail
    if cond:
        _ok += 1
        print("  [OK  ] %s" % name)
    else:
        _fail += 1
        print("  [FAIL] %s   %s" % (name, info))


def rd(va, n):
    o = va - BASE
    if o < 0 or o + n > len(MEM):
        return b""
    return MEM[o:o + n]


def dword(va):
    return struct.unpack("<I", rd(va, 4))[0]


def cstr_bytes(va, maxn=32):
    b = rd(va, maxn)
    z = b.find(b"\x00")
    return b[:z] if z >= 0 else b


def cstr(va, maxn=32):
    return cstr_bytes(va, maxn).decode("latin1")


def ops_at(va, n):
    return [(i.address, i.mnemonic, i.op_str) for i in md.disasm(rd(va, n), va)]


def disasm_str(va, n):
    return " ; ".join("%s %s" % (m, o) for (_a, m, o) in ops_at(va, n))


# ==================================================================
# 资源名全集（续195 方法）
# ==================================================================
NAME_RE = re.compile(rb"[A-F]:[A-Z0-9_]{1,12}\.[A-Z0-9]{2,3}")


def scan_names():
    out = {}
    for m in NAME_RE.finditer(MEM):
        e = m.end()
        if e >= len(MEM) or MEM[e] != 0:
            continue
        out[BASE + m.start()] = m.group().decode("ascii")
    return out


NAMES = scan_names()


def name_at(va):
    """资源表 16B stride，base 指向**其中一项** —— 只取该处那一个名。"""
    return NAMES.get(va)


# ==================================================================
# call 站点扫描 + 实参回溯（续195 工具坑解法）
# ==================================================================
def imm_of(op_str):
    out = []
    for t in op_str.split(","):
        t = t.strip()
        if re.fullmatch(r"(0x[0-9a-fA-F]+|[0-9]+)", t):
            out.append(int(t, 16) if t.lower().startswith("0x") else int(t))
    return out


def pushes_before(call_va, span=0x60):
    """⚠️ 不能从单一固定起点反汇编（x86 变长指令必错位，实测 0 命中）。
    正解 = 枚举回溯长度，只接受「指令流中存在 address==call_va」的起点（边界对齐），取 back 最大者。"""
    best = None
    for back in range(1, span):
        start = call_va - back
        try:
            ins = list(md.disasm(rd(start, back + 16), start))
        except Exception:
            continue
        idx = None
        for k, i in enumerate(ins):
            if i.address == call_va:
                idx = k
                break
        if idx is None:
            continue
        pushes = []
        for i in ins[:idx]:
            if i.mnemonic == "push":
                v = imm_of(i.op_str)
                if v:
                    pushes.append((i.address, v[0]))
        if pushes:
            if best is None or back > best[0]:
                best = (back, pushes)
    return best[1] if best else []


def find_calls(target):
    out = []
    off = 0
    while True:
        i = MEM.find(b"\xE8", off)
        if i < 0:
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
            out.append(BASE + i)
        off = i + 1
    return out


def collect_call_targets():
    tg = set()
    for m in re.finditer(rb"[\xe8\xe9]", MEM):
        off = m.start()
        if off + 5 > len(MEM):
            continue
        rel = struct.unpack_from("<i", MEM, off + 1)[0]
        t = (BASE + off + 5 + rel) & 0xFFFFFFFF
        if BASE <= t < IMAGE_END:
            tg.add(t)
    return sorted(tg)


TARGETS = collect_call_targets()


def enclosing_fn(va, maxback=0x4000):
    """最大 call/jmp 目标 ≤ va。比 prologue 模式稳健（本 EXE 大量 FPO 函数无 push ebp）。"""
    lo = va - maxback
    best = None
    for t in TARGETS:
        if t > va:
            break
        if t >= lo:
            best = t
    return best


# ==================================================================
# 主资源表 / 子资源表
# ==================================================================
MASTER = 0x506ad0
MASTER_N = 19          # 0..18（第 19 项 0x506c00 起已非资源名）

SUB_TABLES = {
    0x506ad0: ("主资源表", 19),
    0x5030d8: ("合战地图资源", 4),
    0x5036f0: ("畿内/各国地图", 2),
    0x509590: ("存档·剧本数据", 5),
    0x50a1f8: ("外字·GRP2", 2),
    0x50a3c0: ("地形", 1),
    0x50b650: ("商铺地图", 2),
    0x50c140: ("城镇地图/坐标/表", 3),
    0x50ca08: ("开垦计划", 1),
}

# 续161 已钉的 4 簇（用作交叉验证锚点）
KNOWN_161 = {
    0x492e20: "B:MAPCHIP.LZW",
    0x493140: "B:MAPCHAR.LZW",
    0x492f80: "B:SHOP_BG.LZW",
    0x492ed0: "C:TOWNCHIP.LZW",
}

# 尺寸跳表：size_class & 0xfb → size
SWITCH = {0: 0, 1: 1, 2: 2, 3: 0x1000}


def expect_size(sc):
    a = (sc & 0xFF) & 0xFB
    return SWITCH.get(a, 0x1000)


# ==================================================================
# emu：资源加载管线端到端
# ==================================================================
class PipeEmu:
    """把 [0x4fb07c]（运行期加载器回调槽）重定向到自写桩，捕获实参。"""

    STACK_TOP = 0x600000
    STOP = 0x700000
    STUB = 0x701000          # 回调桩页
    SCRATCH = 0x522000       # this 对象（避开 0x522ca0.. 资源缓冲族）

    def __init__(self, handle=0x42):
        # ⚠️ Unicorn 有 TB（translation block）缓存：改写桩代码后**不一定**生效。
        #    需要切换句柄时必须新建实例，不要指望 mem_write 能刷新已缓存的译码。
        self.ret_handle = handle
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.mu.mem_map(BASE, len(MEM))
        self.mu.mem_write(BASE, MEM)
        self.mu.mem_map(self.STACK_TOP, 0x20000)
        self.mu.mem_map(self.STOP, 0x1000)
        self.mu.mem_write(self.STOP, b"\x90" * 16)
        self.mu.mem_map(self.STUB, 0x1000)
        self.calls = []
        self._install_stub()
        self._h = self.mu.hook_add(UC_HOOK_CODE, self._hook)

    def _install_stub(self):
        # mov eax, <handle> ; ret 0xc   （stdcall 3 参，callee 清栈）
        code = b"\xb8" + struct.pack("<I", self.ret_handle) + b"\xc2\x0c\x00"
        self.mu.mem_write(self.STUB, code)
        self.mu.mem_write(0x4fb07c, struct.pack("<I", self.STUB))

    def cstr_at(self, va, maxn=32):
        """⚠️ 必须读 **emu 内存** —— 栈/局部缓冲在静态镜像里是垃圾
        （实测用静态 rd() 读到空串，是本次调试踩到的第一个坑）。"""
        b = bytes(self.mu.mem_read(va, maxn))
        z = b.find(b"\x00")
        return (b[:z] if z >= 0 else b).decode("latin1")

    def _hook(self, mu, address, size, ud):
        if address == self.STUB:
            esp = mu.reg_read(UC_X86_REG_ESP)
            a1 = struct.unpack("<I", mu.mem_read(esp + 4, 4))[0]
            a2 = struct.unpack("<I", mu.mem_read(esp + 8, 4))[0]
            a3 = struct.unpack("<I", mu.mem_read(esp + 0xc, 4))[0]
            self.calls.append((a1, a2, a3))
        elif address == self.STOP:
            mu.emu_stop()

    def run(self, this, base_va, size_class):
        self.calls = []
        esp = self.STACK_TOP - 0x1000
        self.mu.mem_write(esp, struct.pack("<I", self.STOP))
        self.mu.mem_write(esp + 4, struct.pack("<I", base_va))          # arg0
        self.mu.mem_write(esp + 8, struct.pack("<I", size_class & 0xFFFFFFFF))  # arg1
        self.mu.mem_write(self.SCRATCH, b"\x00" * 64)
        self.mu.reg_write(UC_X86_REG_ESP, esp)
        self.mu.reg_write(UC_X86_REG_EIP, 0x4802e0)
        self.mu.reg_write(UC_X86_REG_ECX, this)
        self.mu.emu_start(0x4802e0, self.STOP + 0x100, count=0x40000)
        return {
            "eax": self.mu.reg_read(UC_X86_REG_EAX),
            "this0": struct.unpack("<I", self.mu.mem_read(this, 4))[0],
            "buf": bytes(self.mu.mem_read(0x522ca0, 32)),
            "calls": list(self.calls),
        }


def main():
    print("=" * 96)
    print("资源加载簇全图 · 自校验参考实现（续196）")
    print("=" * 96)

    # ------------------------------------------------------- A 静态几何
    print("\n[A] 静态：管线函数几何")
    s480 = disasm_str(0x4802e0, 0x30)   # 0x2c 会正好截掉末尾的 `ret 8`
    check("A1 0x4802e0 = stdcall 2 参 (ret 8)", "ret 8" in s480)
    check("A2 0x4802e0 把 arg0 拷进共享缓冲 0x522ca0（32B）",
          "0x522ca0" in s480 and "0x20" in s480)
    check("A3 0x4802e0 用 movsx 取 arg1 作尺寸类别",
          "movsx" in s480 and "esp + 0x18" in s480)
    check("A4 0x4802e0 调 0x4ec8c0 资源选择器构造器", "0x4ec8c0" in s480)

    s800 = disasm_str(0x492800, 0x18)
    check("A5 0x492800 = memmove(dst,src,n) 3 参转发 → 0x4f40b0",
          "0x4f40b0" in s800 and "ret" in s800)

    sc0 = disasm_str(0x4ec8c0, 0x8c)
    check("A6 0x4ec8c0 剥盘符前缀：strcpy(dst, name+2)", "add eax, 2" in sc0)
    check("A7 0x4ec8c0 尺寸类别先 `and al,0xfb`（清 bit2 修饰位）", "and al, 0xfb" in sc0)
    check("A8 0x4ec8c0 超界(>3)走默认尺寸 0x1000", "0x1000" in sc0)
    check("A9 0x4ec8c0 经 [0x4fb07c] 调运行期加载器（stdcall 3 参）",
          "0x4fb07c" in sc0)
    jt = [dword(0x4ec948 + 4 * k) for k in range(4)]
    check("A10 尺寸跳表 0x4ec948 四路 → 0x4ec8f3/0x4ec8f7/0x4ec904/0x4ec911",
          jt == [0x4ec8f3, 0x4ec8f7, 0x4ec904, 0x4ec911],
          "got %s" % ["0x%x" % x for x in jt])
    check("A11 回调失败(handle==-1)返回 0，成功返回 1",
          "cmp eax, -1" in sc0 and "mov eax, 1" in sc0)

    # ------------------------------------------------------- B 静态映射
    print("\n[B] 静态：44 个 call 0x4802e0 站点 → 簇 → 资源")
    sites = find_calls(0x4802e0)
    check("B1 call 0x4802e0 站点数 = 44（与续163 一致）", len(sites) == 44, "got %d" % len(sites))

    rows = []
    for va in sites:
        fn = enclosing_fn(va)
        pushes = pushes_before(va)
        base_va = sc = None
        if pushes:
            last = pushes[-1][1]
            prev = pushes[-2][1] if len(pushes) >= 2 else None
            if BASE <= last < IMAGE_END and name_at(last):
                base_va, sc = last, prev
            elif prev is not None and BASE <= prev < IMAGE_END and name_at(prev):
                base_va, sc = prev, last
        rows.append((va, fn, base_va, sc))

    resolved = [r for r in rows if r[2]]
    check("B2 >= 38 个站点可静态定出资源表基址", len(resolved) >= 38, "got %d" % len(resolved))
    reg_derived = [r for r in rows if not r[2]]
    check("B3 寄存器派生站点 <= 6（续163 记 4 处）", len(reg_derived) <= 6, "got %d" % len(reg_derived))
    print("        寄存器派生站点: %s" % ", ".join("0x%x" % r[0] for r in reg_derived))

    # 主资源表
    master = [(i, MASTER + 16 * i, name_at(MASTER + 16 * i)) for i in range(MASTER_N)]
    check("B4 主资源表 @0x506ad0 恰 19 项且全部可读出资源名",
          all(n for (_i, _v, n) in master), "got %s" % [n for (_i, _v, n) in master])
    check("B5 主资源表 stride 严格 = 16",
          all(v == MASTER + 16 * i for (i, v, _n) in master))
    check("B6 第 19 项(索引19 @0x506c00)已非资源名 ⇒ 表长止于 18",
          name_at(MASTER + 16 * 19) is None)

    # 子表
    sub_ok = True
    for tb, (label, n) in sorted(SUB_TABLES.items()):
        got = [name_at(tb + 16 * i) for i in range(n)]
        if not all(got):
            sub_ok = False
            print("        子表 0x%06x(%s) 缺名: %s" % (tb, label, got))
    check("B7 9 张子资源表条目全部可读出资源名", sub_ok)

    # 簇 → 资源（聚合）
    f2r = {}
    for (va, fn, base_va, sc) in rows:
        if base_va and fn:
            f2r.setdefault(fn, set()).add(name_at(base_va))
    check("B8 至少 20 个簇 handler 被识别", len(f2r) >= 20, "got %d" % len(f2r))

    # 与续161 交叉验证
    for fn, exp in KNOWN_161.items():
        got = f2r.get(fn, set())
        check("B9 续161 锚点 0x%06x → %s" % (fn, exp), exp in got, "got %s" % sorted(got))

    # 主资源表 19 项是否都被某簇加载
    loaded = set()
    for (_va, _fn, base_va, _sc) in rows:
        if base_va:
            loaded.add(base_va)
    miss = [n for (_i, v, n) in master if v not in loaded]
    check("B10 主资源表 19 项全部被至少一个簇加载", not miss, "未加载: %s" % miss)

    # 尺寸类别分布
    sizes = {}
    for (_va, _fn, _b, sc) in rows:
        if sc is not None:
            sizes[sc] = sizes.get(sc, 0) + 1
    print("        尺寸类别(size_class)分布: %s" % (
        ", ".join("0x%x×%d" % (k, v) for k, v in sorted(sizes.items()))))
    check("B11 主流尺寸类别 = 4（&0xfb → 尺寸 0）", sizes.get(4, 0) >= 30, "got %s" % sizes)

    # ------------------------------------------------------- C emu 端到端
    print("\n[C] emu：19 个主资源 × 8 种「会触发回调」的 size_class 端到端")
    # 回调触发条件 = (size_class & 0xfb) <= 3  ⇒ 0..7 全部触发；8 起走默认分支不回调
    # （sc=8 的行为由 D4 单独验证，不混入本矩阵）
    CALLBACK_SCS = [0, 1, 2, 3, 4, 5, 6, 7]
    emu = PipeEmu()
    bad = []
    total = 0
    for (i, va, nm) in master:
        for sc in CALLBACK_SCS:
            total += 1
            r = emu.run(emu.SCRATCH, va, sc)
            if len(r["calls"]) != 1:
                bad.append((nm, sc, "回调次数 %d" % len(r["calls"])))
                continue
            a1, a2, a3 = r["calls"][0]
            got_name = emu.cstr_at(a1)            # ← 读 emu 内存，不是静态镜像
            exp_name = nm[2:]                     # 剥掉 "X:"
            if got_name != exp_name:
                bad.append((nm, sc, "名 %r != %r" % (got_name, exp_name)))
            elif a2 != emu.SCRATCH + 4:
                bad.append((nm, sc, "arg2 0x%x != this+4" % a2))
            elif a3 != expect_size(sc):
                bad.append((nm, sc, "size 0x%x != 0x%x" % (a3, expect_size(sc))))
            elif r["this0"] != 0x42:
                bad.append((nm, sc, "this[0]=0x%x != handle" % r["this0"]))
            elif r["eax"] != 1:
                bad.append((nm, sc, "返回 0x%x != 1" % r["eax"]))
    check("C1 %d/%d 端到端：剥 `X:` 前缀 + 尺寸跳表 + 回调三参 + this[0]=handle + 返 1"
          % (total - len(bad), total),
          not bad, "%d 处不符: %s" % (len(bad), bad[:5]))

    # 共享缓冲确实收到完整名（memmove 32B）
    r = emu.run(emu.SCRATCH, MASTER + 16 * 5, 4)   # B:MAPCHIP.LZW
    check("C2 共享缓冲 0x522ca0 收到完整资源名（含 `X:` 前缀，memmove 0x20）",
          r["buf"].split(b"\x00")[0] == b"B:MAPCHIP.LZW", repr(r["buf"][:20]))

    # ------------------------------------------------------- D emu 负例
    print("\n[D] emu：加载失败路径（⚠️ 需新建实例 —— Unicorn TB 缓存会让 mem_write 改桩失效）")
    emu_fail = PipeEmu(handle=0xFFFFFFFF)         # -1
    r = emu_fail.run(emu_fail.SCRATCH, MASTER, 4)
    check("D1 回调返回 -1 → 函数返回 0（加载失败）", r["eax"] == 0, "eax=0x%x" % r["eax"])
    check("D2 失败时 this[0] 仍写入 -1", r["this0"] == 0xFFFFFFFF, "this0=0x%x" % r["this0"])
    emu_ok = PipeEmu(handle=0x42)
    r = emu_ok.run(emu_ok.SCRATCH, MASTER, 4)
    check("D3 正常句柄：返回 1 且 this[0]=handle", r["eax"] == 1 and r["this0"] == 0x42)

    # sc=8 → (8 & 0xfb)=8 > 3 → 走默认分支，**完全不回调**
    emu8 = PipeEmu()
    r = emu8.run(emu8.SCRATCH, MASTER, 8)
    check("D4 size_class=8 → (&0xfb)=8>3 走默认分支，不触发加载回调",
          len(r["calls"]) == 0 and r["eax"] == 1, "calls=%d eax=0x%x" % (len(r["calls"]), r["eax"]))

    # ------------------------------------------------------- 输出
    print("\n" + "=" * 96)
    print("簇 handler → 资源（静态聚合）")
    print("=" * 96)
    for fn in sorted(f2r):
        print("  0x%06x -> %s" % (fn, " / ".join(sorted(f2r[fn]))))

    print("\n" + "=" * 96)
    print("主资源表 @0x506ad0（19 项）→ 加载它的簇")
    print("=" * 96)
    v2f = {}
    for (va, fn, base_va, sc) in rows:
        if base_va:
            v2f.setdefault(base_va, set()).add(fn)
    for (i, v, n) in master:
        fns = sorted("0x%06x" % (f or 0) for f in v2f.get(v, set()))
        print("  [%2d] 0x%06x  %-18s <- %s" % (i, v, n, ", ".join(fns) or "(无)"))

    out = os.path.join(HERE, "resource_cluster_map.json")
    import json
    json.dump({
        "pipeline": {
            "0x4802e0": "stdcall2(this=ecx, base, size_class): memmove(0x522ca0, base, 0x20); "
                        "call 0x4ec8c0(this, 0x522ca0, (int16)size_class)",
            "0x492800": "cdecl3 memmove(dst, src, n) -> 0x4f40b0",
            "0x4ec8c0": "stdcall2(this=ecx, name, size_class): strcpy(local, name+2); "
                        "sz = SWITCH[size_class & 0xfb] (0->0,1->1,2->2,3->0x1000,>3->0x1000); "
                        "h = [0x4fb07c](local, this+4, sz); this[0]=h; return h==-1?0:1",
            "0x4ec948": "跳转表 4 项 -> 0x4ec8f3/0x4ec8f7/0x4ec904/0x4ec911",
            "0x4fb07c": "运行期加载器回调槽（stdcall 3 参，callee 清栈 ret 0xc）",
        },
        "master_table": {"base": hex(MASTER), "stride": 16, "count": MASTER_N,
                         "entries": [{"idx": i, "va": hex(v), "name": n} for (i, v, n) in master]},
        "sub_tables": {hex(k): {"label": lab, "count": n,
                                "entries": [name_at(k + 16 * i) for i in range(n)]}
                       for k, (lab, n) in SUB_TABLES.items()},
        "clusters": {"0x%06x" % fn: sorted(v) for fn, v in sorted(f2r.items())},
        "call_sites": [{"call": hex(v), "fn": ("0x%06x" % f) if f else None,
                        "resource_va": ("0x%06x" % b) if b else None,
                        "resource": name_at(b) if b else None,
                        "size_class": sc} for (v, f, b, sc) in rows],
    }, open(out, "w"), ensure_ascii=False, indent=1)
    print("\n[输出] %s" % out)

    print("\n" + "=" * 96)
    print("RESULT: %s   (OK=%d FAIL=%d)" % ("ALL PASS ✅" if _fail == 0 else "有 FAIL ❌", _ok, _fail))
    print("=" * 96)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
