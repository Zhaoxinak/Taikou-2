# .data 占用空洞分析: 找出"实体池搬家/扩容"可用的连续空闲 VA
# 占用证据 = ① .text 内任意 4 字节 LE 窗口落在 .data 范围(含 imm32 与 SIB disp)
#           ② .data 静态映像非零字节(初始化的持久数据)
#           ③ 其余段(.rsrc/.idata/.fdata)不管
import struct, pefile

EXE = r"F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe"
pe = pefile.PE(EXE)
BASE = pe.OPTIONAL_HEADER.ImageBase
secs = {s.Name.rstrip(b"\0").decode(): s for s in pe.sections}
text, data = secs[".text"], secs[".data"]
t = text.get_data()
d = data.get_data()
d_va = BASE + data.VirtualAddress
d_end = d_va + data.Misc_VirtualSize

occupied = bytearray(data.Misc_VirtualSize)
def mark(va, size):
    if va >= d_va and va < d_end:
        for i in range(min(size, d_end - va)):
            occupied[va - d_va + i] = 1

# 1) 静态非零字节 -> 按其所在"已证实全局块"太粗, 只把连续非零块标 1
k = 0
while k < len(d):
    if d[k]:
        j = k
        while j < len(d) and d[j]:
            j += 1
        # 非零 run: 保守只当"数据存在", 标全段(初始化区不可用)
        occupied[k:j] = b"\x01" * (j - k)
        k = j
    else:
        k += 1

# 2) .text 引用的全局指针: 所有 4B 窗口在 .data VA 区间者, 标记该地址起 64B(字段访问窗口)
lo, hi = d_va, d_end
refs = {}
import re
# 用正则先粗筛含 0x4C..0x53 高位模式的 dword? 直接全窗口更快: 0xC3000 次循环可接受
pat = bytearray(t)
for pos in range(0, len(t) - 3):
    v = struct.unpack_from("<I", t, pos)[0]
    if lo <= v < hi:
        refs.setdefault(v, []).append(pos)
        # 访问器一般 v+disp: 标 v..v+0x40
        mark(v, 0x40)
# 2b) v-base 的短 dword(如 [reg+0x?]) 无法定位, 已由非零标记兜底
# 3) 空洞清单: 连续 occupied==0 且 >=256B
holes = []
k = 0
while k < len(occupied):
    if not occupied[k]:
        j = k
        while j < len(occupied) and not occupied[j]:
            j += 1
        if j - k >= 256:
            holes.append((d_va + k, j - k))
        k = j
    else:
        k += 1
holes.sort(key=lambda h: -h[1])
print("引用点 dword 总数:", len(refs))
print("== 空洞 top20 (VA, size) ==")
for va, sz in holes[:20]:
    print("  0x%08X  %6d B" % (va, sz))
print("总计空洞:", sum(s for _, s in holes), "B / .data", len(occupied), "B")
# 实体池搬家需求: 460*47=21620B 连续
need = 460 * 47
big = [h for h in holes if h[1] >= need]
print("能容纳 %d 实体(47B)的单体空洞: %s" % (460, big if big else "无"))
