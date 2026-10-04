"""ft.exe 冒烟-阶段B: 进游戏早期(点开始新游戏)后 dump 0x519868 的 370 实体,
在 Python 里逐字复刻 family_builder 的谓词, 验证:
  - 有效实体数
  - 有多少"父亲可解析"的孩子 (father 指向一个真实实体)
  - 子女最多的若干主官及其族谱(父/本人/子女 大名id), 证明逻辑选出的是真家族
只读, 不写 exe; 结束杀进程 + 还原 AVI."""
import ctypes, os, struct, time, shutil, traceback
from ctypes import wintypes
k32=ctypes.WinDLL('kernel32',use_last_error=True); u32=ctypes.WinDLL('user32')
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
hp=hk=None
try:
    if os.path.exists(AVI): shutil.move(AVI,AVI+'.ftb'); moved.append(AVI)
    si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
    k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
    hp,pid=pi.hp,pi.pid; hk=k32.OpenProcess(0x1F0FFF,False,pid)
    def rd(va,n):
        b=ctypes.create_string_buffer(n); got=ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk,ctypes.c_void_p(va),b,n,ctypes.byref(got)): return None
        return b.raw[:got.value]
    # 等标题
    t0=time.time(); last=-1; stable=0; main=None
    while time.time()-t0<45:
        for h,w,hh in wins(pid):
            if w>=800: main=h
        d=rd(0x534040,4); cnt=struct.unpack('<I',d)[0] if d else -1
        stable=stable+1 if cnt==last else 0; last=cnt
        if cnt>=71 and stable>8 and main: break
        time.sleep(0.4)
    print('标题 present=%d'%last,flush=True)
    # 点开始新游戏 -> 选主角木下藤吉郎(640,415) x3 进入剧本 (同 probe_ent3)
    wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
    r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r)); nct=(wr.bottom-wr.top)-r.bottom
    def click(px,py):
        u32.SetCursorPos(wr.left+px, wr.top+nct+py); time.sleep(0.35)
        u32.mouse_event(2,0,0,0,0); time.sleep(0.08); u32.mouse_event(4,0,0,0,0); time.sleep(0.4)
    click(545,310); time.sleep(1.5)
    click(640,415); time.sleep(2.5); click(640,415); time.sleep(2.5); click(640,415); time.sleep(3.0)
    # dump 370 实体
    EBASE,STRIDE,N=0x519868,47,0x172
    blob=rd(EBASE, STRIDE*N)
    if not blob: print('实体读取失败'); raise SystemExit
    ents=[]
    for i in range(N):
        e=blob[i*STRIDE:(i+1)*STRIDE]
        ents.append(dict(slot=i, ent=EBASE+i*STRIDE,
                         selfid=struct.unpack('<H',e[0x02:0x04])[0],
                         father=struct.unpack('<H',e[0x1d:0x1f])[0],
                         status=struct.unpack('<H',e[0x2c:0x2e])[0]))
    # 复刻 builder 门: 仅 +0x2c (test ah,80 跳; !(ah&7) 跳)
    def shown(x):
        ah=(x['status']>>8)&0xff
        return (ah&0x80)==0 and (ah&7)!=0
    live=[x for x in ents if shown(x)]
    print('通过存活/职级门(shown)的实体 %d / %d'%(len(live),N),flush=True)
    by_self={}
    for x in live:
        by_self.setdefault(x['selfid'],x)
    resolved=[x for x in live if x['father']!=0xffff and x['father'] in by_self]
    print('父亲可解析的孩子数 =',len(resolved),flush=True)
    # 每个 root 大名id 的子女数
    from collections import Counter
    kids=Counter(x['father'] for x in live if x['father']!=0xffff and shown(x))
    print('\n子女最多的 8 个主官(按大名id):',flush=True)
    for rid,cnt in kids.most_common(8):
        root=by_self.get(rid)
        if not root: continue
        father=root['father']
        children=[x['selfid'] for x in live if x['father']==rid and shown(x)]
        print(' root 大名id=%d slot=%d 父=%s 子女大名id=%s'%(rid,root['slot'],
              ('%d'%father) if father!=0xffff else '无', children),flush=True)
    # 玩家当前对象
    idc=rd(0x516624,4)
    if idc:
        cur=struct.unpack('<I',idc)[0]
        print('\n[0x516624] 当前对象=%d'%cur,flush=True)
    print('\n结论: 逻辑在真实数据上选出可解析族谱' if kids else '结论: 无子女数据',flush=True)
except SystemExit: pass
except Exception: print('EXC',traceback.format_exc(),flush=True)
finally:
    for h in (hp,hk):
        try:
            if h: k32.TerminateProcess(h,0)
        except: pass
    for f in moved:
        if os.path.exists(f+'.ftb'): shutil.move(f+'.ftb',f)
    print('cleanup',flush=True)
