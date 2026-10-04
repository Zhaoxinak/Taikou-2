"""启动游戏 -> 等片头自然播完 -> 截标题菜单 -> 保持运行供后续交互。
会把 pid/hwnd 写到 .rev/game_id.txt。结束时自动杀进程。"""
import ctypes, time, struct, os, zlib
from ctypes import wintypes
k32=ctypes.WinDLL('kernel32',use_last_error=True); u32=ctypes.WinDLL('user32'); g32=ctypes.WinDLL('gdi32')
EXE=r'F:/Games/Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
GAME=r'F:/Games/Taikou 2\Taikou2 Original'; REV=os.path.join(GAME,'.rev')
class SI2(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('a',wintypes.LPVOID),('b',wintypes.LPVOID),('c',wintypes.LPVOID),
              ('x',wintypes.DWORD),('y',wintypes.DWORD),('xs',wintypes.DWORD),('ys',wintypes.DWORD),
              ('x1',wintypes.DWORD),('y1',wintypes.DWORD),('fa',wintypes.DWORD),('fl',wintypes.DWORD),
              ('sw',wintypes.WORD),('r2',wintypes.WORD),('r3',wintypes.LPVOID),('h1',wintypes.HANDLE),
              ('h2',wintypes.HANDLE),('h3',wintypes.HANDLE)]
class PI(ctypes.Structure):
    _fields_=[('hp',wintypes.HANDLE),('ht',wintypes.HANDLE),('pid',wintypes.DWORD),('tid',wintypes.DWORD)]
def wins(pid):
    o=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
    def cb(h,lp):
        p=wintypes.DWORD(); u32.GetWindowThreadProcessId(h,ctypes.byref(p))
        if p.value==pid and u32.IsWindowVisible(h):
            b=ctypes.create_unicode_buffer(160); u32.GetWindowTextW(h,b,160)
            r=wintypes.RECT(); u32.GetClientRect(h,ctypes.byref(r))
            o.append((h,b.value,r.right,r.bottom))
        return True
    u32.EnumWindows(cb,0); return o
def png(hwnd,path):
    r=wintypes.RECT(); u32.GetClientRect(hwnd,ctypes.byref(r)); w,hh=r.right,r.bottom
    wr=wintypes.RECT(); u32.GetWindowRect(hwnd,ctypes.byref(wr))
    hdcW=u32.GetDC(0); mdc=g32.CreateCompatibleDC(hdcW); bmp=g32.CreateCompatibleBitmap(hdcW,w,hh)
    g32.SelectObject(mdc,bmp); g32.BitBlt(mdc,0,0,w,hh,hdcW,wr.left,wr.top,0x00CC0020)
    bi=struct.pack('<IiiHHIIiiII',40,w,-hh,1,24,0,0,0,0,0,0)
    buf=ctypes.create_string_buffer(w*hh*3)
    g32.GetDIBits(mdc,bmp,0,hh,buf,ctypes.create_string_buffer(bi,len(bi)),0)
    raw=b''.join(b'\x00'+buf.raw[y*w*3:(y+1)*w*3] for y in range(hh))
    def ch(t,dd):
        c=t+dd; return struct.pack('>I',len(dd))+c+struct.pack('>I',zlib.crc32(c))
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,hh,8,2,0,0,0))
        +ch(b'IDAT',zlib.compress(raw,6))+ch(b'IEND',b''))
    return len(raw)//3 and sum(1 for i in range(0,len(raw),3) if raw[i:i+3]!=b'\x00\x00\x00')/(len(raw)//3)
si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
hp,pid=pi.hp,pi.pid
print('pid',pid,flush=True)
main=None
for _ in range(80):
    for h,t,w,hh in wins(pid):
        if w>=800: main=h; break
    if main: break
    time.sleep(0.3)
open(os.path.join(REV,'game_id.txt'),'w').write('%d %d\n'%(pid,main))
print('main hwnd',main,flush=True)
hk=k32.OpenProcess(0x1F0FFF,False,pid)
def present():
    b=ctypes.create_string_buffer(4); got=ctypes.c_size_t()
    if not k32.ReadProcessMemory(hk,ctypes.c_void_p(0x534040),b,4,ctypes.byref(got)): return -1
    return struct.unpack('<I',b.raw)[0]
t0=time.time()
# 等片头自然播完 (KOEILOGO 15s + OPENNING 232s + 余量)
while time.time()-t0 < 258:
    time.sleep(5)
    code=wintypes.DWORD(); k32.GetExitCodeProcess(hk,ctypes.byref(code))
    if code.value!=259: print('游戏提前退出',flush=True); break
print('t=%.0fs present=%d，开始截图'%(time.time()-t0,present()),flush=True)
for i,tag in enumerate(['T1','T2','T3']):
    time.sleep(2.0)
    nb=png(main,os.path.join(REV,'title_%s.png'%tag))
    print('  %s nonblack %.0f%% present=%d'%(tag,nb*100,present()),flush=True)
print('保持运行 600s',flush=True)
try:
    for i in range(120):
        time.sleep(5)
        code=wintypes.DWORD(); k32.GetExitCodeProcess(hk,ctypes.byref(code))
        if code.value!=259: print('用户/游戏退出',flush=True); break
finally:
    try: k32.TerminateProcess(hk,0)
    except: pass
    if os.path.exists(os.path.join(REV,'game_id.txt')): os.remove(os.path.join(REV,'game_id.txt'))
    print('cleanup',flush=True)
