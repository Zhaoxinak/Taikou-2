#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_payload_capture.py  --  续229 攻关：SNDATA 215 型逐字节字段名枚举
=====================================================================================
方法（承接续228「唯一真·余步」）：emu 真实跑主循环 `0x4e8600`，对每条记录(代表 type)
经扇出 `0x47fc60` 把 49B 记录铺进三视缓冲(0x522c88/0x522c60/0x522c70)，再走类别簇 handler
消费 payload。钩：
  - MEM_READ  落在三视缓冲(0x522c60..0x522c88+43) ⇒ 记录 (payload_off, pc, val)
  - MEM_WRITE 落在已知游戏表(实体/城/国/国情/名/S7/S15/扇出) ⇒ 记录 (table, off, pc)
聚合出「type → payload 字节偏移 → 目标游戏表/字段」地图，即字面字段名。

关键修复（续195 阶段2 崩溃根因）：IAT `0x4fb000..0x4fb1f8` 是未解析占位 0x3000，须按各
Win32 API 真实 arity 生成 `ret N` 桩（否则 stdcall callee 清栈错 → 栈漂移 → EIP 跳进数据区）。
I/O 四桩(OpenFile/_llseek/_lread/_lclose)用 续194 读管线逻辑扩展为「按文件名喂任意原版文件」。
"""
import os, struct, json, argparse, glob
from collections import defaultdict
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN  = os.path.join(ROOT, "scripts", "_unpacked_mem.bin")
SND_PATH = os.path.join(ROOT, "Taikou2 Original", "SNDATA1.TR2")
BASE = 0x400000

# ---- Win32 API arity (stdcall 参数个数) —— 本工程 IAT 实际引用者 ----
API_ARITY = {
 'GetDeviceCaps':2,'GetStockObject':1,'RealizePalette':1,'SelectPalette':2,'DeleteObject':1,'GetTextMetricsA':2,
 'GetPaletteEntries':3,'CreateDIBitmap':6,'CreateCompatibleDC':1,'SetMapMode':2,'SelectObject':2,'DeleteDC':1,
 'CreateFontA':14,'GetDIBits':7,'TextOutA':4,'BitBlt':9,'SetBkMode':2,'PatBlt':5,'SetTextColor':2,
 'SetStretchBltMode':2,'CreateDIBSection':7,'AnimatePalette':3,'SetDIBColorTable':4,'CreatePalette':1,
 'GetSystemPaletteEntries':4,'GetObjectA':3,
 'ExitProcess':1,'GetTickCount':0,'GetVersionExA':1,'WriteFile':5,'OpenFile':3,'GetCurrentDirectoryA':2,
 'GetLocalTime':1,'GlobalAlloc':2,'GetDriveTypeA':1,'_lwrite':3,'GlobalUnlock':1,'GlobalLock':1,'_lclose':1,
 '_lread':3,'GlobalFree':1,'_llseek':3,'LoadLibraryA':1,'GetStringTypeW':4,'GetStringTypeA':4,'LCMapStringW':5,
 'LCMapStringA':5,'IsBadCodePtr':1,'IsBadWritePtr':2,'IsBadReadPtr':2,'SetUnhandledExceptionFilter':1,
 'GetModuleFileNameA':3,'GetFileType':1,'GetStdHandle':1,'SetHandleCount':1,'GetProcAddress':2,'GetOEMCP':0,
 'GetACP':0,'GetCPInfo':2,'WideCharToMultiByte':8,'GetEnvironmentStringsW':0,'GetEnvironmentStrings':0,
 'FreeEnvironmentStringsW':1,'MultiByteToWideChar':6,'FreeEnvironmentStringsA':1,'UnhandledExceptionFilter':1,
 'VirtualAlloc':3,'VirtualFree':3,'HeapCreate':3,'HeapDestroy':1,'HeapSize':2,'GetCurrentProcess':0,
 'TerminateProcess':2,'HeapReAlloc':4,'GetVersion':0,'GetCommandLineA':0,'GetStartupInfoA':1,'GetModuleHandleA':1,
 'HeapAlloc':3,'RtlUnwind':4,'HeapFree':3,
 'InvalidateRect':3,'UpdateWindow':1,'ClientToScreen':2,'GetClientRect':2,'MessageBoxA':4,'GetWindowThreadProcessId':2,
 'SetWindowsHookExA':4,'ReleaseDC':2,'GetDC':1,'MoveWindow':6,'SetCursor':1,'wvsprintfA':3,'EndDialog':2,
 'PostMessageA':4,'DialogBoxParamA':5,'WinHelpA':4,'CreateWindowExA':11,'RegisterClassA':1,'LoadIconA':2,
 'LoadCursorA':2,'DestroyCursor':1,'ShowWindow':2,'DispatchMessageA':1,'TranslateMessage':1,'DestroyWindow':1,
 'CallNextHookEx':4,'PostQuitMessage':1,'BeginPaint':2,'EndPaint':2,'DefWindowProcA':4,'GetWindowRect':2,
 'SystemParametersInfoA':4,'GetSystemMetrics':1,'GetCursorPos':1,'ScreenToClient':2,'PeekMessageA':5,'SetWindowPos':6,
 'UnhookWindowsHookEx':1,
 'mciSendCommandA':4,'timeGetTime':0,
}

# ---- 已知游戏表范围（VA）----
TABLES = [
    ("entity",   0x519868, 0x519868 + 47*370),
    ("castle",   0x51eb88, 0x51eb88 + 31*200),
    ("country",  0x519548, 0x519548 + 5*49),
    ("copol",    0x5179b8, 0x5179b8 + 14*49),
    ("name",     0x506ca8, 0x506ca8 + 0x4000),
    ("s7",       0x516a28, 0x516a28 + 16*200),
    ("s15",      0x5203c0, 0x5203c0 + 0x40),
    ("fanout",   0x522c60, 0x522c88 + 43),
    # 续160/162 资源/加载表
    ("resbuf",   0x522ca0, 0x522ca0 + 0x40),
    ("loadtab_a",0x524978, 0x524978 + 0x200),
    ("loadtab_b",0x524918, 0x524918 + 0x200),
    ("loadtab_c",0x524740, 0x524740 + 0x200),
    ("bsdata_buf",0x524a20,0x524a20 + 0x200),
    ("cursor",   0x509684, 0x509684 + 0x40),
    # 续165 S6/S17、续220 S15 segC[3] 单位池
    ("s6",       0x516610, 0x516610 + 0x200),
    ("s17",      0x517c70, 0x517c70 + 0x200),
    ("unitpool", 0x513550, 0x513550 + 0x200),
    # 续228 队列
    ("queue",    0x526c00, 0x526c58 + 0x40),
]
STRIDE = {"entity":47, "castle":31, "country":5, "copol":14, "s7":16}

def r32(mu,a): return struct.unpack_from("<I", mu.mem_read(a,4),0)[0]
def w32(mu,a,v): mu.mem_write(a, struct.pack("<I", v & 0xffffffff))

def type_of(idx, SND):
    rec = SND[16+idx*49: 16+idx*49+2]
    return struct.unpack_from("<H", rec, 0)[0] & 0xff

class Emu:
    def __init__(self):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        with open(BIN,"rb") as f: self.code = f.read()
        assert len(self.code) >= 0x200000
        self.mu.mem_map(BASE, len(self.code))
        self.mu.mem_write(BASE, self.code)
        self.STACK_TOP = 0x600000
        self.mu.mem_map(self.STACK_TOP, 0x40000)
        self.STOP = 0x700000
        self.mu.mem_map(self.STOP, 0x1000)
        self.mu.mem_write(self.STOP, b"\x90\x90\x90\x90")
        self.last=[0]
        self.mu.hook_add(UC_HOOK_CODE, lambda mu,a,s,u: self.last.__setitem__(0,a))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default="", help="逗号分隔 type(hex 无0x) 白名单；空=全部")
    ap.add_argument("--limit", type=int, default=0, help="最多处理多少 type（0=全部）")
    args = ap.parse_args()
    SND = open(SND_PATH,"rb").read()
    assert len(SND) >= 16+833*49, f"SNDATA 长度异常 {len(SND)}"
    N = 833
    e = Emu()

    # ---- 文件映射：原版目录下所有文件按大写裸名载入内存，供 OpenFile 桩按名喂 ----
    file_map = {}
    orig_dir = os.path.join(ROOT, "Taikou2 Original")
    for p in glob.glob(os.path.join(orig_dir, "*")):
        if os.path.isfile(p):
            file_map[os.path.basename(p).upper()] = open(p,"rb").read()
    file_map["SNDATA1.TR2"] = SND
    file_map["SNDATA2.TR2"] = open(os.path.join(orig_dir,"SNDATA2.TR2"),"rb").read()

    # ---- IAT 桩：每个槽指向一个 `ret N` 指令（no-op，按 arity 清栈）----
    STUB0 = 0xC00000
    e.mu.mem_map(STUB0, 0x20000)
    iat = json.load(open(os.path.join(ROOT,"scripts","iat_map.json"),encoding='utf-8'))
    slots = iat.get('slots', {})
    stubp = STUB0
    for slot_addr, info in slots.items():
        sa = int(slot_addr,16)
        ar = API_ARITY.get(info.get('api'), 3)
        if ar==0:
            e.mu.mem_write(stubp, b"\xc3")
        else:
            e.mu.mem_write(stubp, struct.pack("<BH", 0xc2, ar*4))   # ret imm16
        e.mu.mem_write(sa, struct.pack("<I", stubp))
        stubp += 8

    # ---- I/O 四桩：slot 指向 RET_PAGE 的 `ret`；在 on_code 里按地址识别并做真实喂数据 ----
    RET_PAGE = STUB0 + 0x10000
    e.mu.mem_write(RET_PAGE, b"\xc3")           # 仅占位；实际在 on_code 改写 EIP/ESP
    io_slots = {0x4fb07c:'OpenFile', 0x4fb0a8:'_llseek', 0x4fb0a0:'_lread', 0x4fb09c:'_lclose'}
    for sa in io_slots:
        e.mu.mem_write(sa, struct.pack("<I", RET_PAGE))

    # 全镜像 scratch（吸收堆式读写）—— 用 0xA00000..0xBFFFFF 空闲区（0x526c00 落在代码区 0x400000..0x600000）
    e.mu.mem_map(0x800000, 0x200000)
    e.mu.mem_map(0xA00000, 0x1000)

    # ---- 钩子 ----
    q=[0]; qidx=[0]; cur_idx=[0]; cursor_done=[False]
    last_io_slot=[None]
    STUB_ADDRS = {RET_PAGE, 0x47d720, 0x47fe00, 0x47b160, 0x47b390, 0x47fb80}
    mode_cur=[0]
    cur_type=[None]
    reads=defaultdict(lambda: defaultdict(list))   # type -> (buf,off) -> [(pc,val)]
    writes=defaultdict(lambda: defaultdict(list))  # type -> table -> [(off,pc)]
    cur = {"name":None,"data":b"","pos":0}

    def io_openfile(mu):
        sp = mu.reg_read(UC_X86_REG_ESP)
        ret = r32(mu, sp)                       # 返回地址在 [esp]
        name_ptr = r32(mu, sp+4)
        raw = mu.mem_read(name_ptr, 80)
        name = b""
        for b in raw:
            if b==0: break
            name += bytes([b])
        nm = name.decode('latin1','replace').upper()
        if ':' in nm: nm = nm.split(':',1)[1]
        nm = nm.strip().upper()
        cur["name"]=nm; cur["data"]=file_map.get(nm, b""); cur["pos"]=0
        mu.reg_write(UC_X86_REG_EAX, 1)          # HFILE=1
        mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)   # ret + 3 参
    def io_llseek(mu):
        sp = mu.reg_read(UC_X86_REG_ESP)
        ret = r32(mu, sp)
        off = r32(mu, sp+8); origin = r32(mu, sp+0xc)
        L = len(cur["data"])
        if origin==0: cur["pos"]=off
        elif origin==1: cur["pos"]+=off
        elif origin==2: cur["pos"]=L+off
        if cur["pos"]<0: cur["pos"]=0
        if cur["pos"]>L: cur["pos"]=L
        mu.reg_write(UC_X86_REG_EAX, cur["pos"]); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
    def io_lread(mu):
        sp = mu.reg_read(UC_X86_REG_ESP)
        ret = r32(mu, sp)
        dst = r32(mu, sp+8); cnt = r32(mu, sp+0xc)
        L = len(cur["data"]); p = cur["pos"]
        n = min(cnt, L-p)
        if n<0: n=0
        if n>0: mu.mem_write(dst, cur["data"][p:p+n])
        cur["pos"]=p+n
        mu.reg_write(UC_X86_REG_EAX, n); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
    def io_lclose(mu):
        sp = mu.reg_read(UC_X86_REG_ESP)
        ret = r32(mu, sp)
        mu.reg_write(UC_X86_REG_EAX, 0); mu.reg_write(UC_X86_REG_ESP, sp+8); mu.reg_write(UC_X86_REG_EIP, ret)

    def on_code(mu, address, size, ud):
        e.last[0]=address
        if address in STUB_ADDRS:
            sp = mu.reg_read(UC_X86_REG_ESP)
            if address==RET_PAGE:
                slot = last_io_slot[0]
                if slot=='OpenFile': io_openfile(mu)
                elif slot=='_llseek': io_llseek(mu)
                elif slot=='_lread': io_lread(mu)
                elif slot=='_lclose': io_lclose(mu)
                return
            elif address==0x47d720:
                ret=r32(mu,sp); mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP,sp+12); mu.reg_write(UC_X86_REG_EIP,ret)
            elif address==0x47fe00:
                ret=r32(mu,sp); v=q[qidx[0]] if qidx[0]<len(q) else -1; qidx[0]+=1
                if v<0: cursor_done[0]=True
                cur_idx[0]=v if v>=0 else cur_idx[0]
                mu.reg_write(UC_X86_REG_EAX,v & 0xffffffff); mu.reg_write(UC_X86_REG_ESP,sp+4); mu.reg_write(UC_X86_REG_EIP,ret)
            elif address==0x47b160:
                ret=r32(mu,sp); mu.reg_write(UC_X86_REG_ESP,sp+4); mu.reg_write(UC_X86_REG_EIP,ret)
            elif address==0x47b390:
                ret=r32(mu,sp); mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP,sp+4); mu.reg_write(UC_X86_REG_EIP,ret)
            elif address==0x47fb80:
                ret=r32(mu,sp); mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP,sp+4); mu.reg_write(UC_X86_REG_EIP,ret)
        # 检测 `call [0x4fb0xx]`（opcode ff 15 imm32）：记录槽，交由 RET_PAGE 处理
        code = mu.mem_read(address, 6)
        if code[0]==0xff and code[1]==0x15:
            slot = struct.unpack_from("<I", code, 2)[0]
            if slot in io_slots:
                last_io_slot[0] = io_slots[slot]
                # 不改 EIP；让其自然跳到 RET_PAGE（=ret 字节），由 on_code(RET_PAGE) 接管


    def on_mem_read(mu, access, address, size, value, ud):
        t = cur_type[0]
        if t is None: return
        for base,name in ((0x522c60,'bufC'),(0x522c88,'bufA'),(0x522c70,'bufB')):
            if base <= address < base+43:
                off = address-base
                val = struct.unpack_from("<I", mu.mem_read(address, min(size,4)),0)[0] if size<=4 else 0
                reads[t][(name,off)].append((e.last[0], val))
                return

    def on_mem_write(mu, access, address, size, value, ud):
        t = cur_type[0]
        if t is None: return
        for name,b0,b1 in TABLES:
            if b0 <= address < b1:
                writes[t][name].append((address-b0, e.last[0]))
                return

    e.mu.hook_add(UC_HOOK_CODE, on_code)
    e.mu.hook_add(UC_HOOK_MEM_READ, on_mem_read)
    e.mu.hook_add(UC_HOOK_MEM_WRITE, on_mem_write)

    for je_addr in (0x4e8663, 0x4e8670):
        b0 = e.mu.mem_read(je_addr,1)[0]
        nop_len = 6 if b0==0x0f else 2
        e.mu.mem_write(je_addr, b"\x90"*nop_len)

    def run_one():
        e.mu.reg_write(UC_X86_REG_ESP, 0x638000)
        e.mu.mem_write(0x638000, struct.pack("<I", e.STOP))
        e.mu.reg_write(UC_X86_REG_EIP, 0x4e8600)
        e.mu.emu_start(0x4e8600, e.STOP+1, count=0x400000)

    rep={}
    for idx in range(N):
        t=type_of(idx,SND)
        if t not in rep: rep[t]=idx
    print(f"distinct types={len(rep)}")

    wl = set()
    if args.types:
        wl = set(int(x,16) for x in args.types.split(','))
    items = sorted(rep.items())
    if args.limit: items = items[:args.limit]
    processed=0
    for t, idx in items:
        if wl and t not in wl: continue
        cur_type[0]=t
        for mode in (0,1):
            mode_cur[0]=mode
            q=[idx]; qidx[0]=0; cursor_done[0]=False; cur_idx[0]=idx
            e.mu.mem_write(0x5205fe, struct.pack("<H", mode))
            e.mu.mem_write(0x522c60, b"\x00"*0x60); e.mu.mem_write(0x522c88, b"\x00"*0x40)
            try:
                run_one()
            except Exception as ex:
                print(f"  ** type=0x{t:02x} mode={mode} 崩溃 last=0x{e.last[0]:06x}: {ex}")
        processed+=1
        if processed % 20 == 0:
            print(f"  ... {processed}/{len(rep)} types")
    summary={}
    for t in sorted(reads):
        ro = {f"{n}@{o}": [pc for pc,_ in v][:5] for (n,o),v in reads[t].items()}
        wo = {name: sorted(set(off for off,_ in lst))[:20] for name,lst in writes[t].items()}
        summary[f"0x{t:02x}"] = {"payload_reads": ro, "table_writes": wo}
    with open(os.path.join(ROOT,"scripts","sndata_payload_capture.json"),"w",encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(f"落盘 scripts/sndata_payload_capture.json (types={len(summary)})")

if __name__=="__main__":
    main()
