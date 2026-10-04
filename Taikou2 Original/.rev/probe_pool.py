# 实体池扩容安全性静态探测：
#  1) 穷举 exe 代码段内所有 0x172(370) 立即数引用点（越界校验/循环计数）
#  2) 穷举 0x519868(池基址)/0x51DC56(池尾)/池尾之后各全局表的引用点
#  3) 结论：370 是散布在几百处代码里的硬编码上界，还是可单点改的循环常数
import struct, pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe"  # 原版加壳(FuckALI)，用已解壳的 zoom
pe = pefile.PE(EXE)
BASE = pe.OPTIONAL_HEADER.ImageBase
text = None
for s in pe.sections:
    if s.Name.rstrip(b"\0") == b".text":
        text = s
    print(s.Name.rstrip(b"\0").decode(), "VA=0x%X size=0x%X raw=0x%X" %
          (BASE + s.VirtualAddress, s.Misc_VirtualSize, s.SizeOfRawData))

code = text.get_data()
t_va = BASE + text.VirtualAddress
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

WATCH = {0x172: "ECOUNT 370(上界/循环数)"}
ADDRS = {
    0x519868: "EBASE 实体池基址",
    0x519288: "700B 登场标志数组",
    0x51DC56: "EBASE_END 池尾",
    0x51DC5C: "S6 全局(画面/视口)",
    0x51DC60: "49国外交矩阵",
    0x51EB88: "城表(200)",
    0x51E9C0: "候选池数组(游戏自用+MOD复用)",
    0x520660: "姓表",
    0x521AA8: "名表",
    0x5179B8: "49国政治表",
    0x5197B0: "S5 六人名单",
}

hits_imm = {}   # value -> [va]
hits_addr = {}  # value -> [va]
md.detail = True
n = 0
# 原始字节扫描: 指令流中每个 4 字节 LE 窗口 == 目标地址 即算引用
# (覆盖 imm32 与 mod=00.rm=100 的 SIB 拆散编码两种情况)
import re
targets = set(ADDRS)
addr_hits = {v: [] for v in targets}
buf = code
for v in targets:
    pat = struct.pack('<I', v)
    start = 0
    while True:
        k = buf.find(pat, start)
        if k < 0: break
        addr_hits[v].append(t_va + k)
        start = k + 1
# 0x172 作为 32 位 imm 也查一遍(避免 2 字节噪声, 只查 dword 窗口==0x172)
pat172 = struct.pack('<I', 0x172)
hits172 = []
start = 0
while True:
    k = buf.find(pat172, start)
    if k < 0: break
    hits172.append(t_va + k)
    start = k + 1
# 2 字节 72 01(16位 imm cmp ax,172h)——噪声大, 只统计条数
import array
cnt16 = buf.count(b'\x72\x01')

print("\n== .text 内 4 字节 LE 窗口引用统计 ==")
for v in sorted(addr_hits):
    lst = addr_hits[v]
    print("0x%08X %-28s x%4d  前8处(.text偏移): %s" % (
        v, ADDRS[v], len(lst), " ".join("%06X" % (a - t_va) for a in lst[:8])))
print("0x00000172(dword) x%4d   0x0172(2字节 72 01, 含噪声) x%d" % (len(hits172), cnt16))
for i in range(0, min(len(hits172), 240), 12):
    print("   +" + " ".join("%06X" % (a - t_va) for a in hits172[i:i + 12]))

