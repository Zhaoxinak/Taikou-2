"""ft.exe 冒烟-阶段A: 启动 -> 跳过片头 -> 等标题 -> 截图 -> 确认进程存活(未 0xC0000602 崩溃).
验证洞页/节复用没破坏 PE 加载, 且被改的热路径(经 0x4624f0 分派)不炸主流程."""
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
            b=ctypes.create_unicode_buffer(128); u32.GetWindowTextW(h,b,128)
            r=wintypes.RECT(); u32.GetClientRect(h,ctypes.byref(r))
            out.append((h,b.value,r.right,r.bottom))
        return True
    u32.EnumWindows(cb,0); return out
hp=None; hk=None; main=None
try:
    if os.path.exists(AVI): shutil.move(AVI,AVI+'.ft'); moved.append(AVI)
    si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
    ok=k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
    print('CreateProcess',bool(ok),'pid',pi.pid,flush=True)
    hp,pid=pi.hp,pi.pid
    hk=k32.OpenProcess(0x1F0FFF,False,pid)
    def rd(va,n):
        b=ctypes.create_string_buffer(n); got=ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk,ctypes.c_void_p(va),b,n,ctypes.byref(got)): return None
        return b.raw[:got.value]
    def alive():
        c=wintypes.DWORD(); k32.GetExitCodeProcess(hk,ctypes.byref(c)); return c.value==259, c.value
    t0=time.time(); last=-1; stable=0
    while time.time()-t0<45:
        al,code=alive()
        if not al: print('!! 进程已退出 exitcode=0x%08X @%.1fs'%(code,time.time()-t0),flush=True); raise SystemExit
        for h,t,w,hh in wins(pid):
            if '错误' in t or 'error' in t.lower(): u32.PostMessageW(h,0x0010,0,0)
        d=rd(0x534040,4); cnt=struct.unpack('<I',d)[0] if d else -1
        stable = stable+1 if cnt==last else 0
        last=cnt
        cands=[x for x in wins(pid) if x[2]>=800 and '错误' not in x[1]]
        if cands: main=max(cands,key=lambda x:x[2]*x[3])[0]
        if cnt>=71 and stable>8 and main: break
        time.sleep(0.4)
    al,code=alive(); print('[%.1fs] present=%d main=%s alive=%s'%(time.time()-t0,last,main,al),flush=True)
    def shot(tag):
        if not main: print('no main win, skip shot',flush=True); return
        u32.SetForegroundWindow(main); time.sleep(0.3)
        r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r)); w,h=r.right,r.bottom
        wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
        dcv=u32.GetDC(0); mdc=g32.CreateCompatibleDC(dcv); bmp=g32.CreateCompatibleBitmap(dcv,w,h)
        g32.SelectObject(mdc,bmp); g32.BitBlt(mdc,0,0,w,h,dcv,wr.left,wr.top,0x00CC0020)
        bi=struct.pack('<IiiHHIIiiII',40,w,-h,1,24,0,0,0,0,0,0); buf=ctypes.create_string_buffer(w*h*3)
        g32.GetDIBits(mdc,bmp,0,h,buf,ctypes.create_string_buffer(bi,len(bi)),0)
        raw=b''.join(b'\x00'+buf.raw[y*w*3:(y+1)*w*3] for y in range(h))
        def ch(t,dd): c=t+dd; return struct.pack('>I',len(dd))+c+struct.pack('>I',zlib.crc32(c))
        png=b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,6))+ch(b'IEND',b'')
        p=os.path.join(REV,'ft_%s.png'%tag); open(p,'wb').write(png)
        nb=sum(1 for i in range(0,len(raw),3) if raw[i:i+3]!=b'\x00\x00\x00')/(len(raw)//3)
        print('shot',tag,w,'x',h,'nonblack %.1f%%'%(nb*100),flush=True)
    shot('title')
    time.sleep(2); shot('title2')
    al,code=alive(); print('结尾存活 =',al,flush=True)
except SystemExit: pass
except Exception: print('EXC',traceback.format_exc(),flush=True)
finally:
    for h in (hp,hk):
        try:
            if h: k32.TerminateProcess(h,0)
        except: pass
    for f in moved:
        if os.path.exists(f+'.ft'): shutil.move(f+'.ft',f)
    print('cleanup+restore done',flush=True)
