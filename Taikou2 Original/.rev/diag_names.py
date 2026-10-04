"""只读诊断: 启动 zoom.exe(无MOD), 进剧本后 dump 实体数组 0x519868(370*47) + 姓/名表,
用姓名 getter 的公式(ent+0x00=person id; 姓表0x520660/名表0x521aa8, 步长7, id<1000)在 Python 里
还原每个实体的姓名, 定位 柴田胜家/胜丰/佐久间盛政/安政/正胜 的【槽位】与其 +0x00/+0x02/+0x1d/+0x2c,
并交叉验证 "ent+0x00 == BSDATA oid"。另 dump 目标记录 0x516610..0x51661c 与 [0x516624]/[0x519227]/[0x520630]。
只读, 不写 exe; 结束杀进程 + 还原 OPENNING.AVI。"""
import ctypes, os, struct, time, shutil, traceback
from ctypes import wintypes
k32=ctypes.WinDLL('kernel32',use_last_error=True); u32=ctypes.WinDLL('user32')
GAME=r'F:/Games/Taikou 2\Taikou2 Original'; EXE=os.path.join(GAME,'TAIK2W95_zoom.exe')
AVI=os.path.join(GAME,'OPENNING.AVI'); moved=[]
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
    if os.path.exists(AVI): shutil.move(AVI,AVI+'.dbg'); moved.append(AVI)
    si=SI2(); si.cb=ctypes.sizeof(si); pi=PI()
    k32.CreateProcessA(EXE.encode(),None,None,None,False,0,None,GAME.encode(),ctypes.byref(si),ctypes.byref(pi))
    hp,pid=pi.hp,pi.pid; hk=k32.OpenProcess(0x1F0FFF,False,pid)
    def rd(va,n):
        b=ctypes.create_string_buffer(n); got=ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk,ctypes.c_void_p(va),b,n,ctypes.byref(got)): return None
        return b.raw[:got.value]
    t0=time.time(); last=-1; stable=0; main=None
    while time.time()-t0<45:
        for h,w,hh in wins(pid):
            if w>=800: main=h
        stable=stable+1 if last==last else 0; last=1
        if main: break
        time.sleep(0.4)
    print('window',main,flush=True)
    wr=wintypes.RECT(); u32.GetWindowRect(main,ctypes.byref(wr))
    r=wintypes.RECT(); u32.GetClientRect(main,ctypes.byref(r)); nct=(wr.bottom-wr.top)-r.bottom
    def click(px,py):
        u32.SetCursorPos(wr.left+px, wr.top+nct+py); time.sleep(0.35)
        u32.mouse_event(2,0,0,0,0); time.sleep(0.08); u32.mouse_event(4,0,0,0,0); time.sleep(0.45)
    click(545,310); time.sleep(1.5)
    click(640,415); time.sleep(2.5); click(640,415); time.sleep(2.5); click(640,415); time.sleep(3.0)
    EBASE,STRIDE,N=0x519868,47,0x172
    blob=rd(EBASE, STRIDE*N)
    if not blob: print('实体读取失败'); raise SystemExit
    # 姓/名表 (id<1000 段): 姓 base 0x520660, 名 base 0x521aa8, 步长7
    SUR=rd(0x520660, 1000*7); GIV=rd(0x521aa8, 1000*7)
    def gbk(b):
        if not b: return '?'
        z=b.find(b'\0'); b=b[:z] if z>=0 else b
        try: return b.decode('gbk')
        except: return b.hex()
    def name(pid_):
        if pid_<1000 and SUR and GIV:
            return gbk(SUR[pid_*7:pid_*7+7])+' '+gbk(GIV[pid_*7:pid_*7+7])
        return '(id>=1000)'
    ents=[]
    for i in range(N):
        e=blob[i*STRIDE:(i+1)*STRIDE]
        ents.append(dict(slot=i, pid=struct.unpack('<H',e[0x00:0x02])[0],
                         f2=struct.unpack('<H',e[0x02:0x04])[0],
                         f1d=struct.unpack('<H',e[0x1d:0x1f])[0],
                         st=struct.unpack('<H',e[0x2c:0x2e])[0]))
    # 目标记录 + 全局
    rec=rd(0x516610,0x20)
    print('目标记录 0x516610..:', rec.hex(' ') if rec else 'NA', flush=True)
    for g in (0x516624,0x519227,0x520630):
        v=rd(g,4); print('  [0x%06X]=%s'%(g, struct.unpack('<I',v)[0] if v else 'NA'),flush=True)
    # 定位 柴田一门 + 截图里错列的人
    want={'柴田胜家':0,'柴田胜丰':35,'佐久间盛政':38,'佐久间安政':42,'佐久间正胜':45,
          '林通胜':None,'桑折宗长':89,'伊达辉宗':99,'最上义守':115,'相马盛胤':127}
    print('\n--- 按姓名(pid=ent+0x00) 定位 ---',flush=True)
    # 建 name->slot 索引
    byname={}
    for x in ents:
        nm=name(x['pid'])
        byname.setdefault(nm,[]).append(x)
    for wn,woid in want.items():
        # 姓名表里可能带空格差异, 用去空格匹配
        hits=[x for x in ents if name(x['pid']).replace(' ','')==wn.replace(' ','')]
        if not hits:
            print('  %-6s oid=%s  未找到(姓名表可能非此段)'%(wn,woid),flush=True); continue
        for x in hits:
            print('  %-6s -> slot=%d  ent+0x00(pid)=%d  +0x02=%d  +0x1d=%d  +0x2c=0x%04x  [oid期望=%s]'%(
                wn,x['slot'],x['pid'],x['f2'],x['f1d'],x['st'],woid),flush=True)
    # 统计: ent+0x00 是否覆盖 0..N 且与 oid 一致
    pids=[x['pid'] for x in ents]
    print('\nent+0x00(pid) 去重数=%d / %d, 范围 %d..%d'%(len(set(pids)),N,min(pids),max(pids)),flush=True)
    # 柴田胜家(pid==0) 在哪个 slot? 直接找 pid==0
    s0=[x for x in ents if x['pid']==0]
    print('pid==0 的槽位:',[x['slot'] for x in s0],flush=True)
    print('slot==0 的 pid:',ents[0]['pid'],'name=',name(ents[0]['pid']),flush=True)
    # +0x02/+0x1d 是否像父亲(0xffff) 分布
    ff2=sum(1 for x in ents if x['f2']==0xffff); ff1d=sum(1 for x in ents if x['f1d']==0xffff)
    print('+0x02==0xffff 的实体数=%d ; +0x1d==0xffff 的实体数=%d'%(ff2,ff1d),flush=True)
except SystemExit: pass
except Exception: print('EXC',traceback.format_exc(),flush=True)
finally:
    for h in (hp,hk):
        try:
            if h: k32.TerminateProcess(h,0)
        except: pass
    for f in moved:
        if os.path.exists(f+'.dbg'): shutil.move(f+'.dbg',f)
    print('cleanup',flush=True)
