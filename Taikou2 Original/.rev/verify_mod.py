"""真机验证：让游戏本体去读 modkit 重打包出来的 LS11 文件。

流程：
  1. 备份被替换的原版文件
  2. 把 modkit/output/ 里的产物覆盖进游戏目录
  3. 临时移走 OPENNING.AVI 跳过开场动画（否则要等 4 分钟）
  4. 启动游戏，轮询 present 计数；跑起来就截图
  5. finally 里无条件还原所有东西

判据：**present 计数能持续增长且截图非黑** = 游戏接受了这个文件。
"""

import ctypes
import os
import shutil
import struct
import sys
import time
import zlib
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32")
g32 = ctypes.WinDLL("gdi32")

GAME = r"F:\Games\Taikou 2\Taikou2 Original"
EXE = os.path.join(GAME, "TAIK2W95_zoom.exe")
TARGET = "MESSAGE1.LZW"
SRC_NEW = r"F:\Games\Taikou 2\modkit\output\MESSAGE1.LZW"
AVI = os.path.join(GAME, "OPENNING.AVI")


class SI2(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPVOID), ("lpDesktop", wintypes.LPVOID),
                ("lpTitle", wintypes.LPVOID), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                ("lpReserved2", wintypes.LPVOID), ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


def main():
    backup = os.path.join(GAME, TARGET + ".modkit_bak")
    avi_moved = False
    hp = None
    try:
        if not os.path.exists(SRC_NEW):
            print("缺少产物，先跑 python modkit/demo_edit_text.py")
            return 1
        shutil.copy2(os.path.join(GAME, TARGET), backup)
        shutil.copy2(SRC_NEW, os.path.join(GAME, TARGET))
        print(f"已替换 {TARGET}（原版备份为 {TARGET}.modkit_bak）")
        if os.path.exists(AVI):
            shutil.move(AVI, AVI + ".bak")
            avi_moved = True
            print("已临时移走 OPENNING.AVI")

        si = SI2()
        si.cb = ctypes.sizeof(si)
        pi = PI()
        ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                                GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
        print("CreateProcess", ok, "pid", pi.dwProcessId, flush=True)
        if not ok:
            print("CreateProcess 失败", ctypes.get_last_error())
            return 1
        hp, pid = pi.hProcess, pi.dwProcessId

        def rd(va, n):
            b = ctypes.create_string_buffer(n)
            got = ctypes.c_size_t()
            if not k32.ReadProcessMemory(hp, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
                return None
            return b.raw[:got.value]

        # 等 present 计数起来；中途进程若自杀立刻发现
        t0 = time.time()
        last = -1
        while time.time() - t0 < 90:
            d = rd(0x534040, 4)
            cnt = struct.unpack("<I", d)[0] if d else -1
            code = wintypes.DWORD()
            k32.GetExitCodeProcess(hp, ctypes.byref(code))
            if code.value != 259:                       # STILL_ACTIVE
                print(f"进程已退出 code=0x{code.value:x}  t={time.time()-t0:.1f}s present={cnt}")
                return 2
            if cnt != last:
                print(f"[{time.time()-t0:6.1f}] present={cnt}", flush=True)
                last = cnt
                if cnt >= 120:
                    break
            time.sleep(0.4)
        print(f"present 最终 {last}", flush=True)

        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def cb(h, lp):
            p = wintypes.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid and u32.IsWindowVisible(h):
                b = ctypes.create_unicode_buffer(64)
                u32.GetWindowTextW(h, b, 64)
                if b.value.strip():
                    found.append(h)
            return True

        u32.EnumWindows(cb, 0)
        if not found:
            print("没有窗口")
            return 3
        hwnd = found[0]
        u32.SetForegroundWindow(hwnd)
        time.sleep(1.0)

        r = wintypes.RECT()
        u32.GetClientRect(hwnd, ctypes.byref(r))
        w, hh = r.right, r.bottom
        wr = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(wr))
        hdcW = u32.GetDC(0)
        mdc = g32.CreateCompatibleDC(hdcW)
        bmp = g32.CreateCompatibleBitmap(hdcW, w, hh)
        g32.SelectObject(mdc, bmp)
        g32.BitBlt(mdc, 0, 0, w, hh, hdcW, wr.left, wr.top, 0x00CC0020)
        bi = struct.pack("<IiiHHIIiiII", 40, w, -hh, 1, 24, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(w * hh * 3)
        g32.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
        raw = b"".join(b"\x00" + buf.raw[y * w * 3:(y + 1) * w * 3] for y in range(hh))

        def chunk(t, dd):
            c = t + dd
            return struct.pack(">I", len(dd)) + c + struct.pack(">I", zlib.crc32(c))

        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, hh, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
        out = r"F:\Games\Taikou 2\Taikou2 Original\.rev\verify_mod_menu.png"
        open(out, "wb").write(png)
        nonblack = sum(1 for px in range(0, len(raw), 3) if raw[px:px + 3] != b"\x00\x00\x00")
        total = len(raw) // 3
        print(f"截图 {out} {len(png)}B  客户区 {w}x{hh}  非黑占比 {nonblack/total:.1%}")
        return 0 if nonblack / total > 0.2 else 4
    finally:
        if hp is not None:
            try:
                k32.TerminateProcess(hp, 0)
            except Exception:
                pass
        if avi_moved and os.path.exists(AVI + ".bak"):
            shutil.move(AVI + ".bak", AVI)
            print("已还原 OPENNING.AVI")
        try:
            shutil.copy2(backup, os.path.join(GAME, TARGET))
            os.remove(backup)
            print(f"已还原 {TARGET}")
        except Exception as e:
            print("!! 还原失败:", e)


if __name__ == "__main__":
    sys.exit(main())
