"""只读运行期探针: 验证族谱依赖的运行数据模型.
  - 启动原版 TAIK2W95_zoom.exe (跳过片头), 到标题, 点一次"开始新游戏"
  - ReadProcessMemory dump:
      * 0x516624 当前详情对象武将id
      * 0x519868 运行实体池头几条(47B stride), 看 +0x02 id / +0x1d father_id / +0x16 有效位
      * 0x524a20 BSDATA 常驻 700x59, 取信长(id13)记录 + 扫首个 father 非0xffff 的记录
  不写任何 exe; 结束杀进程 + 还原 OPENNING.AVI.
"""
import ctypes, os, struct, time, zlib, shutil, traceback
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
            r=wintypes.RECT(); u32.GetClientRect(h,ctypes.byref(r))
            out.append((h,b.value,r.right,r.bottom))
        return True
    u32.EnumWindows(cb,0); return out
hp=None; best=None
try:
    if os.path.exists(AVI): shutil.move(AVI,AVI+'.probe'); moved.append(AVI)
    si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
    k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
    hp,pid=pi.hp,pi.pid; print('pid',pid,flush=True)
    def rd(va,n):
        b=ctypes.create_string_buffer(n); got=ctypes.c_size_t()
        if not k32.ReadProcessMemory(hp,ctypes.c_void_p(va),b,n,ctypes.byref(got)): return None
        return b.raw[:got.value]
    # 关错误框 + 等标题(present>=71)
    t0=time.time(); last=-1; stable=0; main=None
    while time.time()-t0<40:
        for h,t,w,hh in wins(pid):
            if '错误' in t or 'error' in t.lower():
                u32.PostMessageW(h,0x0010,0,0)
        d=rd(0x534040,4); cnt=struct.unpack('<I',d)[0] if d else -1
        if cnt is not None and cnt==last: stable+=1
        else: stable=0
        last=cnt
        cands=[x for x in wins(pid) if x[2]>=800 and '错误' not in x[1]]
        if cands: main=max(cands,key=lambda x:x[2]*x[3])[0]
        if cnt>=71 and stable>8 and main: break
        time.sleep(0.4)
    print('标题就绪 present=%d main=%s'%(last,main),flush=True)
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
        png=b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,6))+ch(b'IEND',b'')
        open(os.path.join(REV,'probe_%s.png'%tag),'wb').write(png); print('shot',tag,w,'x',h,flush=True)
    shot('0_title')
    # 点"开始新游戏"(客户区545,310; 加非客户顶)
    if main:
        r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r))
        wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
        nct=(wr.bottom-wr.top)-r.bottom
        cx,cy=wr.left+545, wr.top+nct+310
        u32.SetCursorPos(cx,cy); time.sleep(0.4)
        u32.mouse_event(2,0,0,0,0); time.sleep(0.08); u32.mouse_event(4,0,0,0,0)
        time.sleep(3.0); shot('1_after_click')
    # dump
    idcur=rd(0x516624,4); idv=struct.unpack('<I',idcur)[0] if idcur else None
    print('[0x516624] 当前详情对象id =',idv,flush=True)
    ent=rd(0x519868,47*6)
    print('0x519868 头6实体(47B):', 'LOADED' if ent else 'READ FAIL',flush=True)
    if ent:
        for i in range(6):
            e=ent[i*47:(i+1)*47]
            print(' ent[%d] id(+2)=%d valid(+16)=%d father(+1d)=%d lord(+2a)=%d city(+25)=%d prov(+24)=%d'%
                  (i,struct.unpack('<H',e[2:4])[0],e[0x16],struct.unpack('<H',e[0x1d:0x1f])[0],
                   struct.unpack('<H',e[0x2a:0x2c])[0],e[0x25],e[0x24]))
    bs=rd(0x524a20,59*700)
    print('0x524a20 BSDATA resident:','LOADED' if bs else 'READ FAIL',flush=True)
    if bs:
        # 信长 id13
        rec=bs[13*59:14*59]
        sib=rec[0:7].split(b'\x00')[0]; gvb=rec[7:14].split(b'\x00')[0]
        print(' 信长记录 姓=%r 名=%r birth(+27)=%d father(+29)=%d'%(sib,gvb,rec[0x27],struct.unpack('<H',rec[0x29:0x2b])[0]))
        # 首个 father != 0xffff
        for i in range(700):
            r=bs[i*59:(i+1)*59]; f=struct.unpack('<H',r[0x29:0x2b])[0]
            if f not in (0xffff,0):
                print(' 首个有名存父亲记录 id=%d father=%d 姓=%r 名=%r'%(
                    struct.unpack('<H',r[0x10:0x12])[0],f,r[0:7].split(b'\x00')[0],r[7:14].split(b'\x00')[0]))
                break
        # 用姓名字典验证 father 链 (取一个有father的, 其father记录id应能对上)
except Exception:
    print('EXC',traceback.format_exc())
finally:
    if hp:
        try: k32.TerminateProcess(hp,0)
        except: pass
    for f in moved:
        if os.path.exists(f+'.probe'): shutil.move(f+'.probe',f)
    print('cleanup+restore done',flush=True)
