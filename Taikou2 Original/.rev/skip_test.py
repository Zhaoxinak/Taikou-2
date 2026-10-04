import ctypes, time, struct, sys
from ctypes import wintypes
k32=ctypes.WinDLL('kernel32',use_last_error=True); u32=ctypes.WinDLL('user32')
EXE=r'F:/Games/Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
GAME=r'F:/Games/Taikou 2\Taikou2 Original'
class SI2(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('a',wintypes.LPVOID),('b',wintypes.LPVOID),('c',wintypes.LPVOID),
              ('x',wintypes.DWORD),('y',wintypes.DWORD),('xs',wintypes.DWORD),('ys',wintypes.DWORD),
              ('x1',wintypes.DWORD),('y1',wintypes.DWORD),('fa',wintypes.DWORD),('fl',wintypes.DWORD),
              ('sw',wintypes.WORD),('r2',wintypes.WORD),('r3',wintypes.LPVOID),('h1',wintypes.HANDLE),
              ('h2',wintypes.HANDLE),('h3',wintypes.HANDLE)]
class PI(ctypes.Structure):
    _fields_=[('hp',wintypes.HANDLE),('ht',wintypes.HANDLE),('pid',wintypes.DWORD),('tid',wintypes.DWORD)]
def procs():
    class PE(ctypes.Structure):
        _fields_=[('dwSize',wintypes.DWORD),('c1',wintypes.DWORD),('pid',wintypes.DWORD),
                  ('hid',ctypes.c_size_t),('mid',wintypes.DWORD),('th',wintypes.DWORD),
                  ('ppid',wintypes.DWORD),('pri',ctypes.c_long),('fl',wintypes.DWORD),('nm',ctypes.c_wchar*260)]
    h=k32.CreateToolhelp32Snapshot(0x2,0); r={}; pe=PE(); pe.dwSize=ctypes.sizeof(PE)
    if k32.Process32FirstW(h,ctypes.byref(pe)):
        while True:
            r[pe.pid]=pe.nm
            if not k32.Process32NextW(h,ctypes.byref(pe)): break
    k32.CloseHandle(h); return r
def kill_games():
    n=0
    for p,nm in procs().items():
        if 'TAIK2W95' in nm.upper():
            h=k32.OpenProcess(1,False,p)
            if h: k32.TerminateProcess(h,0); k32.CloseHandle(h); n+=1
    if n: time.sleep(0.6)
    return n
def win_of(pid):
    o=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
    def cb(h,lp):
        p=wintypes.DWORD(); u32.GetWindowThreadProcessId(h,ctypes.byref(p))
        if p.value==pid and u32.IsWindowVisible(h):
            b=ctypes.create_unicode_buffer(160); u32.GetWindowTextW(h,b,160)
            r=wintypes.RECT(); u32.GetClientRect(h,ctypes.byref(r))
            if r.right>200: o.append((h,b.value,r.right,r.bottom))
        return True
    u32.EnumWindows(cb,0); return o
print('清理残留游戏进程:',kill_games(),flush=True)
si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
hp,pid=pi.hp,pi.pid
print('游戏 pid',pid,flush=True)
hk=k32.OpenProcess(0x1F0FFF,False,pid)
def present():
    b=ctypes.create_string_buffer(4); got=ctypes.c_size_t()
    if not k32.ReadProcessMemory(hk,ctypes.c_void_p(0x534040),b,4,ctypes.byref(got)): return -1
    return struct.unpack('<I',b.raw)[0]
hwnd=None
for _ in range(60):
    w=win_of(pid)
    if w: hwnd=w[0][0]; print('窗口 %08x %r %dx%d'%(hwnd,w[0][1],w[0][2],w[0][3]),flush=True); break
    time.sleep(0.3)
if not hwnd: print('no window'); sys.exit(1)
def key(v): u32.keybd_event(v,0,0,0); time.sleep(0.05); u32.keybd_event(v,0,2,0)
def click():
    r=wintypes.RECT(); u32.GetWindowRect(hwnd,ctypes.byref(r))
    u32.SetCursorPos((r.left+r.right)//2,(r.top+r.bottom)//2); time.sleep(0.2)
    u32.mouse_event(2,0,0,0,0); time.sleep(0.06); u32.mouse_event(4,0,0,0,0)
t0=time.time()
print('起始 present =',present(),flush=True)
for t,label,fn in [(6,'click',click),(10,'ESC',lambda:key(0x1B)),(14,'ENTER',lambda:key(0x0D)),
                   (18,'SPACE',lambda:key(0x20)),(22,'X',lambda:key(0x58)),(27,'click2',click)]:
    while time.time()-t0<t: time.sleep(0.3)
    b=present(); fn(); time.sleep(2.0); a=present()
    print('  t=%4.1fs %-7s present %d -> %d %s'%(time.time()-t0,label,b,a,'  <== 有反应!' if a-b>3 else ''),flush=True)
prev=present()
for i in range(6):
    time.sleep(3); cur=present()
    print('  观察 [%4.1fs] present=%d %s'%(time.time()-t0,cur,'<== 已在跑界面' if cur-prev>3 else ''),flush=True)
    prev=cur
k32.TerminateProcess(hk,0); k32.CloseHandle(hk)
print('结束，清理:',kill_games(),flush=True)
