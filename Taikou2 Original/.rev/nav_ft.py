"""ft.exe 导航探索: 进剧本 -> 截图主地图 -> 逐个点底部按钮(功能/调查/情报)并截图, 找武将详情/家中排行入口.
每步截图存 .rev/nav_*.png 供查看. 结束杀进程+还原 AVI."""
import ctypes, os, struct, time, zlib, shutil, traceback
from ctypes import wintypes
k32=ctypes.WinDLL('kernel32',use_last_error=True); u32=ctypes.WinDLL('user32'); g32=ctypes.WinDLL('gdi32')
GAME=r'F:/Games/Taikou 2\Taikou2 Original'; EXE=os.path.join(GAME,'TAIK2W95_ft.exe')
AVI=os.path.join(GAME,'OPENNING.AVI'); REV=os.path.join(GAME,'.rev')
moved=[]
class SI2(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('a',wintypes.LPVOID),('b',wintypes.LPVOID),('c',wintypes.LPVOID),
              ('x',wintypes.DWORD),('y',wintypes.DWORD),('xs',wintypes.DWORD),('ys',wintypes.DWORD),
              ('x1',wintypes.DWORD),('y1',wintypes.DWORD),('fa',wintypes.DWORD),('fl',wintypes.DWORD),
              ('sw',wintypes.WORD),('r2',wintypes.WORD),('r3',wintypes.LPVOID),('h1',wintypes.HANDLE),
              ('h2',wintypes.HANDLE),('h3',wintypes.HANDLE)]
class PI(ctypes.Structure):
    _fields_=[('hp',wintypes.HANDLE),('ht',wintypes.HANDLE),('pid',wintypes.DWORD),('tid',wintypes.DWORD)]
def wins(pid):
    out=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
    def cb(h,lp):
        p=wintypes.DWORD(); u32.GetWindowThreadProcessId(h,ctypes.byref(p))
        if p.value==pid and u32.IsWindowVisible(h):
            r=wintypes.RECT(); u32.GetClientRect(h,ctypes.byref(r)); out.append((h,r.right,r.bottom))
        return True
    u32.EnumWindows(cb,0); return out
hp=hk=main=None
try:
    if os.path.exists(AVI): shutil.move(AVI,AVI+'.nav'); moved.append(AVI)
    si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
    k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
    hp,pid=pi.hp,pi.pid; hk=k32.OpenProcess(0x1F0FFF,False,pid)
    def rd(va,n):
        b=ctypes.create_string_buffer(n); got=ctypes.c_size_t()
        return b.raw[:got.value] if k32.ReadProcessMemory(hk,ctypes.c_void_p(va),b,n,ctypes.byref(got)) else None
    t0=time.time(); last=-1; stable=0
    while time.time()-t0<45:
        for h,w,hh in wins(pid):
            if w>=800: main=h
        d=rd(0x534040,4); cnt=struct.unpack('<I',d)[0] if d else -1
        stable=stable+1 if cnt==last else 0; last=cnt
        if cnt>=71 and stable>8 and main: break
        time.sleep(0.4)
    u32.SetForegroundWindow(main); time.sleep(0.4)
    wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
    r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r)); nct=(wr.bottom-wr.top)-r.bottom
    def click(sx,sy,wait=0.6):
        # 截图以窗口左上角为原点, 故直接用窗口相对坐标点击
        u32.SetCursorPos(wr.left+sx, wr.top+sy); time.sleep(0.3)
        u32.mouse_event(2,0,0,0,0); time.sleep(0.08); u32.mouse_event(4,0,0,0,0); time.sleep(wait)
    def shot(tag):
        u32.SetForegroundWindow(main); time.sleep(0.25)
        r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r)); w,h=r.right,r.bottom
        wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
        dcv=u32.GetDC(0); mdc=g32.CreateCompatibleDC(dcv); bmp=g32.CreateCompatibleBitmap(dcv,w,h)
        g32.SelectObject(mdc,bmp); g32.BitBlt(mdc,0,0,w,h,dcv,wr.left,wr.top,0x00CC0020)
        bi=struct.pack('<IiiHHIIiiII',40,w,-h,1,24,0,0,0,0,0,0); buf=ctypes.create_string_buffer(w*h*3)
        g32.GetDIBits(mdc,bmp,0,h,buf,ctypes.create_string_buffer(bi,len(bi)),0)
        raw=b''.join(b'\x00'+buf.raw[y*w*3:(y+1)*w*3] for y in range(h))
        def ch(t,dd): c=t+dd; return struct.pack('>I',len(dd))+c+struct.pack('>I',zlib.crc32(c))
        png=b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,6))+ch(b'IEND',b'')
        open(os.path.join(REV,'nav_%s.png'%tag),'wb').write(png); print('shot',tag,flush=True)
    # 进剧本: 开始新游戏 -> 主角选择(截图确认坐标) -> 连点进入地图
    click(640,367,1.5); shot('A_newgame')
    click(640,462,2.5); shot('B_hero1')
    click(640,462,2.5); click(640,462,3.0); shot('C_map')
    # 功能 (右下)
    click(1245,760,1.2); shot('D_gongneng')
except Exception: print('EXC',traceback.format_exc(),flush=True)
finally:
    for h in (hp,hk):
        try:
            if h: k32.TerminateProcess(h,0)
        except: pass
    for f in moved:
        if os.path.exists(f+'.nav'): shutil.move(f+'.nav',f)
    print('cleanup',flush=True)
