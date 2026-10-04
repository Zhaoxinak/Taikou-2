# -*- coding: utf-8 -*-
"""probe_ft.py —— 只读内存探针(不改动游戏/不启动游戏)

用途: 钉死“调查卡正在显示的武将”到底存在哪个全局。
用法: 用 TAIK2W95_ft.exe 进游戏 -> 选中并“调查”柴田胜家(卡开着别关) ->
      在另一个终端执行:  python .rev/probe_ft.py
脚本只 OpenProcess(PROCESS_VM_READ) + ReadProcessMemory, 纯读, 立即退出。
"""
import ctypes, ctypes.wintypes as wt, sys

BASE = 0x400000
EBASE, ESTRIDE, ECOUNT = 0x519868, 47, 0x172
SUR_BASE, GIV_BASE, NAME_STRIDE = 0x520660, 0x521aa8, 7

# 候选“当前武将”全局: 名字 -> 绝对VA(读 dword; 有的按 slot 解释, 有的按 entity 指针解释)
SLOT_CANDIDATES = {          # 视为 槽id(word/dword) -> entity = EBASE + slot*47
    "0x516618 (rec+8)":   0x516618,
    "0x516624 (rec+0x14)":0x516624,
    "0x51661a (rec+a)":   0x51661a,
    "0x51661c (rec+14)":  0x51661c,
    "0x516610 (rec+0)":   0x516610,
    "0x516614 (rec+4)":   0x516614,
    "0x516616 (rec+6)":   0x516616,
    "0x516620 (rec+0x10)":0x516620,
    "0x516622":           0x516622,
    "0x516626":           0x516626,
    "0x516628":           0x516628,
    "0x51662a":           0x51662a,
}
PTR_CANDIDATES = {           # 视为 实体指针(dword) 直接用
    "0x520648 (list sel)":0x520648,
    "0x519227 (unit ptr)":0x519227,
    "0x516624d":          0x516624,
}

k32 = ctypes.windll.kernel32
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, wt.LPVOID, wt.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

def find_pid():
    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    GetWindowTextW = user32.GetWindowTextW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    found = []
    def cb(hwnd, lparam):
        buf = ctypes.create_unicode_buffer(256)
        GetWindowTextW(hwnd, buf, 256)
        t = buf.value or ""
        if ("太阁" in t) or ("太閤" in t) or ("TAIK" in t.upper()):
            pid = wt.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                found.append((pid.value, t))
        return True
    EnumWindows(WNDENUMPROC(cb), 0)
    return found

def rd(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got))
    return buf.raw[:got.value] if ok else b""

def name_of_idx(h, idx):
    if idx is None or idx < 0 or idx >= 1000:
        return "?"
    sur = rd(h, SUR_BASE + idx*NAME_STRIDE, 7).split(b"\x00")[0]
    giv = rd(h, GIV_BASE + idx*NAME_STRIDE, 7).split(b"\x00")[0]
    try:
        return sur.decode("gbk") + " " + giv.decode("gbk")
    except Exception:
        return repr(sur) + repr(giv)

def ent_name(h, ent_va):
    w = rd(h, ent_va, 2)
    if len(w) < 2:
        return "?"
    idx = int.from_bytes(w, "little")
    return "%s (nameidx=%d)" % (name_of_idx(h, idx), idx)

def main():
    procs = find_pid()
    if not procs:
        print("没找到游戏窗口(标题含 太阁/TAIK)。请确认游戏正在运行。")
        return
    pid, title = procs[0]
    print("attach pid=%d title=%r  (只读)" % (pid, title))
    h = k32.OpenProcess(0x0010, False, pid)  # PROCESS_VM_READ
    if not h:
        print("OpenProcess 失败 err=%d" % ctypes.GetLastError())
        return
    print("\n== 目标: 找出‘调查卡正在显示的武将(应为 柴田胜家)’所在全局 ==")
    print("\n-- 按 槽id 解释 --")
    for label, va in SLOT_CANDIDATES.items():
        raw = rd(h, va, 4)
        if len(raw) < 2:
            print("  %-22s @%08x  <读失败>" % (label, va)); continue
        slot = int.from_bytes(raw[:2], "little")
        line = "  %-22s @%08x  word=%d" % (label, va, slot)
        if 0 <= slot < ECOUNT:
            line += "  -> ent %s" % ent_name(h, EBASE + slot*ESTRIDE)
        print(line)
    print("\n-- 按 实体指针 解释 --")
    for label, va in PTR_CANDIDATES.items():
        raw = rd(h, va, 4)
        if len(raw) < 4:
            print("  %-22s @%08x  <读失败>" % (label, va)); continue
        p = int.from_bytes(raw, "little")
        line = "  %-22s @%08x  dword=%08x" % (label, va, p)
        if EBASE <= p < EBASE + ECOUNT*ESTRIDE:
            line += "  (在实体数组内) -> %s" % ent_name(h, p)
        print(line)
    # 顺带 dump 记录 0x516610..0x51662c 原始字节
    print("\n-- 原始记录 0x516610..0x51662c --")
    blob = rd(h, 0x516610, 0x20)
    for i in range(0, len(blob), 4):
        print("  +%02x @%08x: %s" % (i, 0x516610+i, blob[i:i+4].hex()))
    k32.CloseHandle(h)
    print("\n请把上面‘-> ent … = 柴田胜家’那一行的 label 告诉我, 我据此把根解析钉死。")

if __name__ == "__main__":
    main()
