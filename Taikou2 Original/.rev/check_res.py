"""读取运行中 wide.exe 的分辨率数组，验证 clamp 上限与窗口一致。
用法: python .rev/check_res.py <exe路径> [等待秒]
"""
import ctypes
import os
import struct
import subprocess
import sys
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
TH32CS_SNAPMODULE32 = 0x10
TH32CS_SNAPMODULE = 8


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.c_ulong), ('th32ModuleID', ctypes.c_ulong),
                ('th32ProcessID', ctypes.c_ulong), ('GlblcntUsage', ctypes.c_ulong),
                ('ProccntUsage', ctypes.c_ulong),
                ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
                ('modBaseSize', ctypes.c_ulong), ('hModule', ctypes.c_void_p),
                ('szModule', ctypes.c_char * 256), ('szExePath', ctypes.c_char * 260)]


def main():
    exe = sys.argv[1]
    wait = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
    p = subprocess.Popen([exe], cwd=os.path.dirname(exe))
    print('启动 pid=%d，等 %.0f 秒...' % (p.pid, wait))
    time.sleep(wait)
    if p.poll() is not None:
        print('进程已退出:', p.returncode)
        return
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, p.pid)
    me = MODULEENTRY32(); me.dwSize = ctypes.sizeof(me)
    base = 0
    if k32.Module32First(snap, ctypes.byref(me)):
        base = ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value
    k32.CloseHandle(snap)
    if not base:
        print('拿不到主模块基址'); return
    hp = k32.OpenProcess(0x0010 | 0x0400, False, p.pid)
    if not hp:
        print('OpenProcess 失败'); return

    def rd(rva, n):
        buf = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t()
        k32.ReadProcessMemory(hp, ctypes.c_void_p(base + rva), buf, n, ctypes.byref(got))
        return buf.raw

    ws = struct.unpack('<4I', rd(0x128958, 16))
    hs = struct.unpack('<4I', rd(0x129218, 16))
    idx, = struct.unpack('<I', rd(0x12C5A8, 4))
    logic_w, = struct.unpack('<I', rd(0x126CF0, 4))
    logic_h, = struct.unpack('<I', rd(0x129958, 4))
    print('当前分辨率索引 [0x52C5A8] =', idx)
    print('宽度数组 [0x528958..] =', list(ws))
    print('高度数组 [0x529218..] =', list(hs))
    print('逻辑宽 [0x526CF0] = %d   逻辑高 [0x529958] = %d' % (logic_w, logic_h))
    print()
    ok = ws[idx] >= 1600 and hs[idx] >= 800
    print('结论:', 'OK  clamp 上限已跟随大分辨率，鼠标命中坐标系与绘制一致'
          if ok else 'X  数组仍是旧值，需要进一步处理')
    k32.TerminateProcess(hp, 0)


if __name__ == '__main__':
    main()
