"""只读探针2: 点选主角进入剧本后 dump 运行实体+BSDATA 验证族谱数据模型.
坐标: 客户区像素(=截图像素); zoom 版内部 ÷2 映射到 640x400 逻辑.
"""
import ctypes, os, struct, time, zlib, shutil
from ctypes import wintypes
k32=ctypes.WinDLL('kernel32',use_last_error=True); u32=ctypes.WinDLL('user32'); g32=ctypes.WinDLL('gdi32')
GAME=r'F:/Games/Taikou 2\Taikou2 Original'; EXE=os.path.join(GAME,'TAIK2W95_zoom.exe')
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
            r=wintypes.RECT(); u32.GetClientRect(h,ctypes.byref(r)); out.append((h,b.value,r.right,r.bottom))
        return True
    u32.EnumWindows(cb,0); return out
hp=None; main=None
def rd(va,n):
    b=ctypes.create_string_buffer(n); got=ctypes.c_size_t()
    return b.raw[:got.value] if k32.ReadProcessMemory(hp,ctypes.c_void_p(va),b,n,ctypes.byref(got)) else None
def shot(tag):
    if not main: return
    u32.SetForegroundWindow(main); time.sleep(0.3)
    r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r)); w,h=r.right,r.bottom
    wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
    dcv=u32.GetDC(0); mdc=g32.CreateCompatibleDC(dcv); bmp=g32.CreateCompatibleBitmap(dcv,w,h)
    g32.SelectObject(mdc,bmp); g32.BitBlt(mdc,0,0,w,h,dcv,wr.left,wr.top,0x00CC0020)
    bi=struct.pack('<IiiHHIIiiII',40,w,-h,1,24,0,0,0,0,0,0); buf=ctypes.create_string_buffer(w*h*3)
    g32.GetDIBits(mdc,bmp,0,h,buf,ctypes.create_string_buffer(bi,len(bi)),0)
    raw=b''.join(b'\x00'+buf.raw[y*w*3:(y+1)*w*3] for y in range(h))
    def ch(t,dd): c=t+dd; return struct.pack('>I',len(dd))+c+struct.pack('>I',zlib.crc32(c))
    open(os.path.join(REV,'probe_%s.png'%tag),'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,6))+ch(b'IEND',b''))
    print('shot',tag,flush=True)
def click(px,py):
    wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
    r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r)); nct=(wr.bottom-wr.top)-r.bottom
    u32.SetCursorPos(wr.left+px,wr.top+nct+py); time.sleep(0.35)
    u32.mouse_event(2,0,0,0,0); time.sleep(0.08); u32.mouse_event(4,0,0,0,0); time.sleep(0.4)
try:
    if os.path.exists(AVI): shutil.move(AVI,AVI+'.probe'); moved.append(AVI)
    si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
    k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
    hp,pid=pi.hp,pi.pid; print('pid',pid,flush=True)
    t0=time.time(); last=-1; stable=0
    while time.time()-t0<45:
        for h,t,w,hh in wins(pid):
            if '错误' in t: u32.PostMessageW(h,0x0010,0,0)
        d=rd(0x534040,4); cnt=struct.unpack('<I',d)[0] if d else -1
        stable=stable+1 if cnt==last else 0; last=cnt
        cands=[x for x in wins(pid) if x[2]>=800 and '错误' not in x[1]]
        if cands: main=max(cands,key=lambda x:x[2]*x[3])[0]
        if cnt>=71 and stable>8 and main: break
        time.sleep(0.4)
    print('title present=%d'%last,flush=True)
    click(545,310); time.sleep(1.5)          # 开始新游戏
    shot('2_selhero'); click(640,415); time.sleep(2.5)  # 木下藤吉郎
    shot('3_after_hero'); click(640,415); time.sleep(2.5) # 可能再确认
    shot('4_more'); click(640,415); time.sleep(3.0)
    shot('5_more2')
    idv=struct.unpack('<I',rd(0x516624,4))[0] if rd(0x516624,4) else None
    print('[0x516624]=',idv,flush=True)
    ent=rd(0x519868,47*8)
    nz=sum(1 for i in range(8) if ent and any(ent[i*47:(i+1)*47]))
    print('0x519868 前8实体非零条数=',nz,flush=True)
    if ent and nz:
        for i in range(8):
            e=ent[i*47:(i+1)*47]
            print(' ent[%d] id=%d valid=%d father=%d lord=%d'%(i,struct.unpack('<H',e[2:4])[0],e[0x16],struct.unpack('<H',e[0x1d:0x1f])[0],struct.unpack('<H',e[0x2a:0x2c])[0]))
    bs=rd(0x524a20,59*700)
    if bs:
        rec=bs[13*59:14*59]
        print(' 信长@0x524a20 姓=%r 名=%r birth=%d father=%d'%(rec[0:7].split(b'\x00')[0],rec[7:14].split(b'\x00')[0],rec[0x27],struct.unpack('<H',rec[0x29:0x2b])[0]))
except Exception as ex:
    print('EXC',ex,flush=True)
finally:
    if hp:
        try: k32.TerminateProcess(hp,0)
        except: pass
    for f in moved:
        if os.path.exists(f+'.probe'): shutil.move(f+'.probe',f)
    print('cleanup',flush=True)
