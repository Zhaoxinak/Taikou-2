"""只读探针3: 进剧本后核对 (a)运行期 father 链 (b)姓名解析 0x521aa8/0x520660 + id*7."""
import ctypes, os, struct, time, zlib, shutil, json
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
def click(px,py):
    wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
    r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r)); nct=(wr.bottom-wr.top)-r.bottom
    u32.SetCursorPos(wr.left+px,wr.top+nct+py); time.sleep(0.35)
    u32.mouse_event(2,0,0,0,0); time.sleep(0.08); u32.mouse_event(4,0,0,0,0); time.sleep(0.4)
def gbk(b):
    b=b.split(b'\x00')[0]
    try: return b.decode('gbk')
    except: return repr(b)
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
    click(545,310); time.sleep(1.5); click(640,415); time.sleep(2.5); click(640,415); time.sleep(2.5); click(640,415); time.sleep(3.0)
    ent=rd(0x519868,47*370)
    SUR=rd(0x521aa8,7*700); GIV=rd(0x520660,7*700)
    def name_of(bid):
        if not SUR or not GIV or bid*7+7>len(SUR): return '?'
        return gbk(SUR[bid*7:bid*7+7])+gbk(GIV[bid*7:bid*7+7])
    if not ent: raise SystemExit('ent read fail')
    # 建 slot->(id,father) ; 找 father!=65535 且其 father 指向的 id 存在
    slots=[]
    for i in range(370):
        e=ent[i*47:(i+1)*47]
        bid=struct.unpack('<H',e[2:4])[0]; f=struct.unpack('<H',e[0x1d:0x1f])[0]
        slots.append((bid,f))
    idset={bid for bid,f in slots}
    withf=[(bid,f) for bid,f in slots if f not in (65535,) and f in idset]
    print('运行期 father 非空且父存在的条数=',len(withf),flush=True)
    # 与静态对照
    off={r['id']:r for r in json.load(open('data/officers.json',encoding='utf-8'))}
    okc=badc=0
    for bid,f in withf[:40]:
        s=off.get(bid)
        sf=s['father_id'] if s else None
        mark='OK' if sf==f else 'MISMATCH(static=%s)'%sf
        if sf==f: okc+=1
        else: badc+=1
        if bid in (47,274,315,320,48,49) or badc<3:
            print('  %s id=%d(%s) father=%d(%s) 静态father=%s'%(mark,bid,name_of(bid),f,name_of(f) if f in idset else '?',sf))
    print('father 链核对: OK=%d MISMATCH=%d (样本40)'%(okc,badc),flush=True)
    # 姓名解析验证几个已知
    for bid in (13,16,47,274,304):
        print('  解析 id=%d -> %r  (静态 %r)'%(bid,name_of(bid),(off[bid]['surname']+off[bid]['given']) if bid in off else '?'),flush=True)
except Exception as ex:
    import traceback; print('EXC',traceback.format_exc(),flush=True)
finally:
    if hp:
        try: k32.TerminateProcess(hp,0)
        except: pass
    for f in moved:
        if os.path.exists(f+'.probe'): shutil.move(f+'.probe',f)
    print('cleanup',flush=True)
