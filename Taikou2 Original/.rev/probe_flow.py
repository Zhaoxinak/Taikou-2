import ctypes, os, struct, time, zlib, shutil, traceback
from ctypes import wintypes
k32=ctypes.WinDLL('kernel32',use_last_error=True); u32=ctypes.WinDLL('user32'); g32=ctypes.WinDLL('gdi32')
GAME=r'F:/Games/Taikou 2\Taikou2 Original'; EXE=os.path.join(GAME,'TAIK2W95_zoom.exe')
AVI=os.path.join(GAME,'OPENNING.AVI'); LOG=os.path.join(GAME,'.rev','flow.log')
lg=open(LOG,'w',encoding='utf-8')
def P(*a): lg.write(' '.join(str(x) for x in a)+'\n'); lg.flush()
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
moved=[]; hp=None
try:
    if os.path.exists(AVI): shutil.move(AVI,AVI+'.bak2'); moved.append(AVI)
    si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
    k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
    hp=pi.hp; pid=pi.pid; P('pid',pid)
    # 前 25 秒：持续关掉任何「错误」对话框，并记录窗口演化
    t0=time.time(); seen=set()
    while time.time()-t0 < 25:
        for h,title,w,hh in wins(pid):
            key=(title,w,hh)
            if key not in seen:
                seen.add(key); P('[%.1fs] win %r %dx%d'%(time.time()-t0,title,w,hh))
            if '错误' in title or 'error' in title.lower():
                u32.PostMessageW(h,0x0010,0,0)          # WM_CLOSE
                P('   -> 已发出关闭给错误框')
        time.sleep(0.5)
    P('--- 25s 后窗口列表 ---')
    for h,title,w,hh in wins(pid): P('   %r %dx%d'%(title,w,hh))
    # 挑主窗口：客户区最大
    cand=[t for t in wins(pid) if t[3]>100 and '错误' not in t[1]]
    if not cand: raise SystemExit('no main window')
    hwnd=max(cand,key=lambda t:t[2]*t[3]); P('主窗口',repr(hwnd[1]),hwnd[2],'x',hwnd[3])
    def shot(tag):
        r=wintypes.RECT(); u32.GetClientRect(hwnd[0],ctypes.byref(r)); w,hh=r.right,r.bottom
        wr=wintypes.RECT(); u32.GetWindowRect(hwnd[0],ctypes.byref(wr))
        hdcW=u32.GetDC(0); mdc=g32.CreateCompatibleDC(hdcW); bmp=g32.CreateCompatibleBitmap(hdcW,w,hh)
        g32.SelectObject(mdc,bmp); g32.BitBlt(mdc,0,0,w,hh,hdcW,wr.left,wr.top,0x00CC0020)
        bi=struct.pack('<IiiHHIIiiII',40,w,-hh,1,24,0,0,0,0,0,0)
        buf=ctypes.create_string_buffer(w*hh*3)
        g32.GetDIBits(mdc,bmp,0,hh,buf,ctypes.create_string_buffer(bi,len(bi)),0)
        raw=b''.join(b'\x00'+buf.raw[y*w*3:(y+1)*w*3] for y in range(hh))
        def ch(t,dd):
            c=t+dd; return struct.pack('>I',len(dd))+c+struct.pack('>I',zlib.crc32(c))
        png=(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,hh,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,6))+ch(b'IEND',b''))
        o=os.path.join(GAME,'.rev','flow_%s.png'%tag); open(o,'wb').write(png)
        nb=sum(1 for px in range(0,len(raw),3) if raw[px:px+3]!=b'\x00\x00\x00')/(len(raw)//3)
        P('shot',tag,len(png),'nonblack %.1f%%'%(nb*100))
    shot('A')
except Exception:
    P('EXC', traceback.format_exc())
finally:
    if hp:
        try: k32.TerminateProcess(hp,0)
        except: pass
    for f in moved:
        if os.path.exists(f+'.bak2'): shutil.move(f+'.bak2',f)
    P('restored'); lg.close()
