"""tkmon.py — 太阁2 常驻崩溃监控器 (附着式, 不启动游戏)。

与既有工具的分工:
  tkwatch.py  只读轮询埋点(族谱/成长/元服/影子档) —— 看不到崩溃现场
  dbg_crash.py 自己 CreateProcess 起游戏 —— 抢了你的操作权, 且 WOW64 CONTEXT 布局错(寄存器全错位)
  tkmon.py    ★ 你正常启动游戏, 它**附着**上去: 平时每 0.7s 打一次心跳(日期+埋点+关键计数器),
              一旦出现任何异常就抓完整现场(寄存器/EIP 反汇编/EBP 链/栈/模块归属/MOD 区归属),
              进程退出后**自动回到等待态**, 等你下次再开还能抓。

用法 (另开一个终端, 让它一直挂着):
  python .rev/tkmon.py                 # 等到天荒地老, 每次开游戏都抓
  python .rev/tkmon.py --once          # 抓到一次致命异常/进程退出就停
  python .rev/tkmon.py --quiet         # 不打心跳, 只在异常/退出时出声

输出: 控制台 + .rev/tkmon.log (追加)
"""
import ctypes, json, os, struct, sys, time
from ctypes import wintypes
from collections import deque

try:
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
except Exception:
    pass

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')

# 64 位进程必须显式声明句柄返回类型, 否则默认 c_int 会把 64 位句柄截断
for _f in ('CreateToolhelp32Snapshot', 'OpenProcess', 'OpenThread'):
    getattr(k32, _f).restype = wintypes.HANDLE
k32.DebugActiveProcess.argtypes = [wintypes.DWORD]
k32.DebugSetProcessKillOnExit.argtypes = [wintypes.BOOL]

REV = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(REV)
LOGPATH = os.path.join(REV, 'tkmon.log')

ONCE = '--once' in sys.argv
QUIET = '--quiet' in sys.argv

# ---- --trace: 在崩溃前最后一个安全点下 int3, 命中后置 TF 单步, 录最后 N 条指令 ----
def _arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

TRACE_VA = int(_arg('--trace', '0'), 0) or None
TRACE_WHEN = _arg('--when', None)          # 例如 "m[0x5205F1]==6 and d[0x54B640]>=2"
TRACE_KEEP = 400                            # 保留最后多少条指令
TRACE_MAXSTEP = 4_000_000

# ---- --probe a,b,c: 在多个地址各下 int3, 只记录"谁被命中过", 不做单步 ----
# 比单步可靠得多(单步中途 TF 会丢), 用来把崩溃夹进"两次命中之间"的区段。
PROBES = [int(x, 0) for x in (_arg('--probe', '') or '').split(',') if x.strip()]

# ---------- 常量 ----------
TH32CS_SNAPPROCESS = 0x2
TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10
PROCESS_ALL = 0x1F0FFF
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

EXC = {
    0xC0000005: 'ACCESS_VIOLATION', 0xC0000094: 'ILLEGAL_INSTRUCTION',
    0xC0000095: 'BREAKPOINT', 0xC00000FD: 'STACK_OVERFLOW',
    0xC000008E: 'DIVIDE_BY_ZERO', 0xC000001D: 'ILLEGAL_INSTRUCTION2',
    0xC0000025: 'NONCONTINUABLE', 0xC000008C: 'ARRAY_BOUNDS',
    0xC0000096: 'PRIV_INSTRUCTION', 0x80000003: 'BREAKPOINT(int3)',
    0x80000004: 'SINGLE_STEP', 0x406D1388: 'MSVC_ThreadName',
    0xC0000093: 'FLT_DENORMAL', 0xC0000417: 'FAIL_FAST',
    0xE0434352: 'CLR_EXCEPTION', 0xC0000409: 'STACK_BUFFER_OVERRUN',
    0x4000001F: 'WOW64_BREAK(=32位int3)', 0x40010005: 'CTRL_BREAK',
    0x4000001E: 'WOW64_SINGLE_STEP',
}
# ★ WOW64 陷阱: 64 位调试器调试 32 位目标时, int3 报 0x4000001F、单步报 0x4000001E,
#   不是 0x80000003/0x80000004。若把 0x4000001F 当"良性"吞掉再 NOT_HANDLED 交还,
#   就变成"自己下的断点把进程弄死"(表现为退出码 0x4000001F, 看不到任何 AV)。
BENIGN = (0x406D1388, 0x40010005)      # 纯通知型: MSVC 线程名 / Ctrl+Break
BP_EXC = (0x80000003, 0x4000001F)      # int3   (原生 / WOW64)
SS_EXC = (0x80000004, 0x4000001E)      # 单步   (原生 / WOW64)

# ---------- 结构 ----------
class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [('ExceptionCode', wintypes.DWORD), ('ExceptionFlags', wintypes.DWORD),
                ('ExceptionRecord', ctypes.c_void_p), ('ExceptionAddress', ctypes.c_void_p),
                ('NumberParameters', wintypes.DWORD),
                ('ExceptionInformation', ctypes.c_ulonglong * 15)]

class EXC_INFO(ctypes.Structure):
    _fields_ = [('ExceptionRecord', EXCEPTION_RECORD), ('dwFirstChance', wintypes.DWORD)]

class LOAD_DLL_INFO(ctypes.Structure):
    _fields_ = [('hFile', wintypes.HANDLE), ('lpBaseOfDll', ctypes.c_void_p),
                ('dwDebugInfoFileOffset', wintypes.DWORD), ('nDebugInfoSize', wintypes.DWORD),
                ('lpImageName', ctypes.c_void_p), ('fUnicode', wintypes.WORD)]

class THREADENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                ('th32ThreadID', wintypes.DWORD), ('th32OwnerProcessID', wintypes.DWORD),
                ('tpBasePri', wintypes.LONG), ('tpDeltaPri', wintypes.LONG),
                ('dwFlags', wintypes.DWORD)]

class EXIT_PROCESS_INFO(ctypes.Structure):
    _fields_ = [('dwExitCode', wintypes.DWORD)]

class UNION(ctypes.Union):
    _fields_ = [('Exception', EXC_INFO), ('LoadDll', LOAD_DLL_INFO),
                ('ExitProcess', EXIT_PROCESS_INFO),
                ('raw', ctypes.c_byte * 256)]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [('dwDebugEventCode', wintypes.DWORD), ('dwProcessId', wintypes.DWORD),
                ('dwThreadId', wintypes.DWORD), ('u', UNION)]

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
                ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]

class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD), ('GlblcntUsage', wintypes.DWORD),
                ('ProccntUsage', wintypes.DWORD), ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
                ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HANDLE),
                ('szModule', wintypes.WCHAR * 256), ('szExePath', wintypes.WCHAR * 260)]

# WOW64_CONTEXT (64 位调试器读 32 位目标): 只有 Dr0-Dr3 + Dr6-Dr7, 没有 Dr4/Dr5
class WOW64_CONTEXT(ctypes.Structure):
    _fields_ = [('ContextFlags', wintypes.DWORD),
                ('Dr0', wintypes.DWORD), ('Dr1', wintypes.DWORD), ('Dr2', wintypes.DWORD),
                ('Dr3', wintypes.DWORD), ('Dr6', wintypes.DWORD), ('Dr7', wintypes.DWORD),
                ('FloatSave', ctypes.c_byte * 112),
                ('SegGs', wintypes.DWORD), ('SegFs', wintypes.DWORD),
                ('SegEs', wintypes.DWORD), ('SegDs', wintypes.DWORD),
                ('Edi', wintypes.DWORD), ('Esi', wintypes.DWORD), ('Ebx', wintypes.DWORD),
                ('Edx', wintypes.DWORD), ('Ecx', wintypes.DWORD), ('Eax', wintypes.DWORD),
                ('Ebp', wintypes.DWORD), ('Eip', wintypes.DWORD),
                ('SegCs', wintypes.DWORD), ('EFlags', wintypes.DWORD),
                ('Esp', wintypes.DWORD), ('SegSs', wintypes.DWORD),
                ('Extended', ctypes.c_byte * 512)]

# 原生 x86 CONTEXT (带 Dr4/Dr5) —— 只在 WOW64 布局明显不合理时兜底试
class X86_CONTEXT(ctypes.Structure):
    _fields_ = [('ContextFlags', wintypes.DWORD),
                ('Dr0', wintypes.DWORD), ('Dr1', wintypes.DWORD), ('Dr2', wintypes.DWORD),
                ('Dr3', wintypes.DWORD), ('Dr4', wintypes.DWORD), ('Dr5', wintypes.DWORD),
                ('Dr6', wintypes.DWORD), ('Dr7', wintypes.DWORD),
                ('FloatSave', ctypes.c_byte * 112),
                ('SegGs', wintypes.DWORD), ('SegFs', wintypes.DWORD),
                ('SegEs', wintypes.DWORD), ('SegDs', wintypes.DWORD),
                ('Edi', wintypes.DWORD), ('Esi', wintypes.DWORD), ('Ebx', wintypes.DWORD),
                ('Edx', wintypes.DWORD), ('Ecx', wintypes.DWORD), ('Eax', wintypes.DWORD),
                ('Ebp', wintypes.DWORD), ('Eip', wintypes.DWORD),
                ('SegCs', wintypes.DWORD), ('EFlags', wintypes.DWORD),
                ('Esp', wintypes.DWORD), ('SegSs', wintypes.DWORD),
                ('Extended', ctypes.c_byte * 512)]

CONTEXT_FULL = 0x10007

k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
k32.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]

# ---------- 布局 / 埋点 ----------
LY = {}
try:
    LY = json.load(open(os.path.join(REV, '_big_layout.json'), encoding='utf-8'))
except Exception as e:
    print('!! 读不到 _big_layout.json (%s) —— 埋点读数将不可用, 崩溃现场仍然抓' % e)

V = LY.get('v', {})
GROWTH = LY.get('growth_ctrs', {})
MOD_BASE = LY.get('mod_base', 0x54B600)
MOD_SZ = LY.get('mod_sz', 0x8000)
POOL_VA = LY.get('pool_va', 0x53C000)
STRIDE = LY.get('stride', 47)
CAP = LY.get('cap', 1024)
DATE_Y, DATE_M, DATE_D = 0x5205F0, 0x5205F1, 0x5205F2

# 五个阶段标记 (build_big.py 落点: F/E/D/G/H)
PHASE = [
    ('F', MOD_BASE + 0x76, '游戏入口 @0x4F44B0'),
    ('E', MOD_BASE + 0x75, '日推进外层 @0x4A0D50'),
    ('G', MOD_BASE + 0x77, '日推进·每日早期 @0x4A0E41'),
    ('D', MOD_BASE + 0x74, '日推进·每日晚期 @0x4A0E47'),
    ('H', MOD_BASE + 0x78, '月边界 @0x4A0DED'),
]
# 心跳要盯的计数器 (太多会刷屏, 挑最有用的)
HEART = []
for _n in ('BGM_CNT', 'APPEAR_CNT', 'MONTH_CNT', 'ARMED_CNT', 'CHILD_GENPUKU',
           'CHILD_PRELOAD', 'CHILD_SCAN', 'CHILD_PLACE'):
    if _n in V:
        HEART.append((_n, V[_n]))
for _n in ('GROWTH_PASS', 'GROWTH_SETTLED', 'GROWTH_CMD', 'GROWTH_ROLL', 'GROWTH_OK',
           'GROWTH_FAIL', 'GROWTH_REJECT', 'PANEL_OPEN', 'CMD_PUSH', 'MENU_COUNT',
           'KID_NOTSAME_CITY', 'PAGE_ROWS', 'PAGE_NAV'):
    if _n in GROWTH:
        HEART.append((_n, GROWTH[_n]))

# MOD 区命名 (便于一眼看出崩在哪段桩里)
MOD_LABELS = sorted(((va, nm) for nm, va in V.items() if MOD_BASE <= va < MOD_BASE + MOD_SZ),
                    key=lambda x: x[0])

# ---------- 输出 ----------
_ring = deque(maxlen=300)
_fh = None

def L(msg=''):
    _ring.append(msg)
    try:
        print(msg, flush=True)
    except Exception:
        pass
    if _fh:
        try:
            _fh.write(msg + '\n'); _fh.flush()
        except Exception:
            pass

# ---------- 进程/模块 ----------
def find_game_pids():
    out = []
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1 or snap == 0xFFFFFFFFFFFFFFFF:
        return out
    try:
        pe = PROCESSENTRY32W(); pe.dwSize = ctypes.sizeof(pe)
        if k32.Process32FirstW(snap, ctypes.byref(pe)):
            while True:
                nm = pe.szExeFile
                if nm.upper().startswith('TAIK2W95'):
                    out.append((pe.th32ProcessID, nm))
                if not k32.Process32NextW(snap, ctypes.byref(pe)):
                    break
    finally:
        k32.CloseHandle(snap)
    return out

def enum_modules(pid):
    mods = []
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == -1 or snap == 0xFFFFFFFFFFFFFFFF:
        return mods
    try:
        me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me)
        if k32.Module32FirstW(snap, ctypes.byref(me)):
            while True:
                base = ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value or 0
                mods.append((base, me.modBaseSize, me.szModule))
                if not k32.Module32NextW(snap, ctypes.byref(me)):
                    break
    finally:
        k32.CloseHandle(snap)
    return sorted(mods)

def main_image_size(exe_path):
    try:
        d = open(exe_path, 'rb').read(0x400)
        e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
        opt = e_lfanew + 24
        magic, = struct.unpack_from('<H', d, opt)
        return struct.unpack_from('<I', d, opt + (56 if magic == 0x10B else 72))[0]
    except Exception:
        return 0

# ---------- 内存 ----------
_hp = [None]

def readmem(addr, n):
    if not _hp[0]:
        return b''
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(_hp[0], ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return b''

def rd32(va):
    d = readmem(va, 4)
    return struct.unpack('<I', d)[0] if len(d) == 4 else None

# ---------- 归属 ----------
class Attr:
    def __init__(self, pid, exe_path):
        self.mods = enum_modules(pid)
        self.main_sz = main_image_size(exe_path)
        self.main_base = 0x400000
        for b, s, n in self.mods:
            if n.upper().startswith('TAIK2W95'):
                self.main_base = b
                if not self.main_sz:
                    self.main_sz = s
                break

    def where(self, a):
        if not a:
            return ''
        for b, s, n in self.mods:
            if b and b <= a < b + s:
                return '%s+0x%X' % (n, a - b)
        return ''

    def full(self, a):
        """模块归属 + 主模块 RVA + MOD 区桩归属, 一次说清。"""
        s = self.where(a)
        if self.main_base <= a < self.main_base + (self.main_sz or 0):
            s += '  [MAIN RVA=0x%X]' % (a - self.main_base)
        if MOD_BASE <= a < MOD_BASE + MOD_SZ:
            lab, lv = '', 0
            for va, nm in MOD_LABELS:
                if va <= a and va >= lv:
                    lv, lab = va, nm
            s += '  [MOD+0x%X%s]' % (a - MOD_BASE, (' ≈%s' % lab) if lab else '')
        if POOL_VA <= a < POOL_VA + STRIDE * CAP:
            s += '  [实体池 槽%d +%d]' % ((a - POOL_VA) // STRIDE, (a - POOL_VA) % STRIDE)
        return s

# ---------- 上下文 ----------
def get_ctx(tid, attr):
    """用两种 CONTEXT 布局各解一遍, 取 EIP 落在已知模块里的那个(防 WOW64 布局错位)。"""
    h = k32.OpenThread(0x1F03FF, False, tid)
    if not h:
        return None, ''
    try:
        buf = ctypes.create_string_buffer(ctypes.sizeof(X86_CONTEXT))
        c = ctypes.cast(buf, ctypes.POINTER(WOW64_CONTEXT))
        c[0].ContextFlags = CONTEXT_FULL
        ok = False
        wg = getattr(k32, 'Wow64GetThreadContext', None)
        if wg:
            ok = bool(wg(h, ctypes.cast(buf, ctypes.POINTER(WOW64_CONTEXT))))
        if not ok:
            ok = bool(k32.GetThreadContext(h, ctypes.cast(buf, ctypes.POINTER(WOW64_CONTEXT))))
        if not ok:
            return None, ''
        w = ctypes.cast(buf, ctypes.POINTER(WOW64_CONTEXT))[0]
        x = ctypes.cast(buf, ctypes.POINTER(X86_CONTEXT))[0]
        sw, sx = attr.where(w.Eip), attr.where(x.Eip)
        # 主模块范围命中优先; 否则谁有归属用谁; 都没有就用 WOW64
        def score(s, eip):
            if attr.main_base <= eip < attr.main_base + (attr.main_sz or 0):
                return 3
            return 2 if s else 0
        use_w = score(sw, w.Eip) >= score(sx, x.Eip)
        return (w if use_w else x), ('WOW64' if use_w else 'x86')
    finally:
        k32.CloseHandle(h)


def set_ctx(tid, c):
    """写回线程上下文 (单步/断点回退用)。"""
    h = k32.OpenThread(0x1F03FF, False, tid)
    if not h:
        return False
    ok = False
    ws = getattr(k32, 'Wow64SetThreadContext', None)
    if ws:
        ok = bool(ws(h, ctypes.byref(c)))
    if not ok:
        ok = bool(k32.SetThreadContext(h, ctypes.byref(c)))
    k32.CloseHandle(h)
    return bool(ok)

# ---------- 反汇编 ----------
try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    _md = Cs(CS_ARCH_X86, CS_MODE_32)
except Exception:
    _md = None

def disasm(addr, n=24):
    code = readmem(addr, n)
    if not code:
        return ['   (读不到 %d 字节)' % n]
    if _md:
        try:
            return ['   0x%08X  %-8s %s %s' % (i.address, i.mnemonic, i.op_str, '')
                    for i in _md.disasm(code, addr)]
        except Exception:
            pass
    return ['   0x%08X  %s' % (addr, code.hex(' '))]

def backtrack(attr, esp, st):
    """EBP 链断了(EBP=0)时的兜底: 扫栈上每个 dword, 若它前面恰好是一条 call/jmp 的结尾,
    就认定它是返回地址, 并把那条指令(连同间接调用的目标值)打出来。"""
    L('栈扫描回溯 (call/jmp 结尾匹配):')
    seen = set()
    hits = 0
    for i in range(0, min(256, len(st)) - 3, 4):
        v = struct.unpack('<I', st[i:i + 4])[0]
        if not v or v in seen:
            continue
        if not attr.where(v):
            continue
        code = readmem(v - 16, 16)
        if len(code) < 16:
            continue
        ins = None
        if _md:
            try:
                for x in _md.disasm(code, v - 16):
                    if x.address + x.size == v:
                        ins = x
            except Exception:
                ins = None
        else:                                  # 无 capstone: 只认两种最常见的
            if code[11] == 0xE8:
                ins = type('I', (), {'mnemonic': 'call', 'op_str': 'rel32', 'address': v - 5})()
            elif code[10] == 0xFF and code[11] in (0x15, 0x25):
                ins = type('I', (), {'mnemonic': 'call/jmp', 'op_str': 'dword ptr [0x%x]'
                                     % struct.unpack('<I', code[12:16])[0], 'address': v - 6})()
        if not ins or ins.mnemonic not in ('call', 'call/jmp', 'jmp', 'lcall'):
            continue
        seen.add(v); hits += 1
        line = '   #%02d [栈+0x%02X] ret=0x%08X  调用点 0x%08X: %s %s' \
               % (hits - 1, i, v, ins.address, ins.mnemonic, ins.op_str)
        # 间接调用: 把槽里的真值读出来 —— 是 0 就是真凶
        if ins.op_str.startswith('dword ptr [0x'):
            try:
                slot = int(ins.op_str[ins.op_str.index('0x'):].rstrip(']'), 16)
            except Exception:
                slot = 0
            if slot:
                pv = rd32(slot)
                line += '\n        槽 0x%08X = %s%s' % (
                    slot, ('0x%08X' % pv) if pv is not None else '读不到',
                    '   <<<< 槽为 NULL, 跳到了 0' if pv == 0 else '')
        L(line)
        if hits >= 12:
            break
    if not hits:
        L('   (没扫到可识别的返回地址 —— 栈已被冲掉或 ESP 不可信)')

def thread_dump(attr, tag):
    """采全部线程的 EIP/ESP —— 用来判断"崩的线程"到底是不是主线程/被单步的那个线程。"""
    tids = []
    snap = k32.CreateToolhelp32Snapshot(0x4, 0)          # TH32CS_SNAPTHREAD
    if snap != -1 and snap != 0xFFFFFFFFFFFFFFFF:
        try:
            te = THREADENTRY32(); te.dwSize = ctypes.sizeof(te)
            if k32.Thread32First(snap, ctypes.byref(te)):
                while True:
                    if te.th32OwnerProcessID == CUR_PID[0]:
                        tids.append(te.th32ThreadID)
                    if not k32.Thread32Next(snap, ctypes.byref(te)):
                        break
        finally:
            k32.CloseHandle(snap)
    L('  -- 全线程快照 (%s): %d 个线程' % (tag, len(tids)))
    for t in tids:
        c, _lay = get_ctx(t, attr)
        if not c:
            L('     tid=%-6d (读不到上下文)' % t)
            continue
        L('     tid=%-6d EIP=0x%08X %-46s ESP=0x%08X EBP=0x%08X TF=%d'
          % (t, c.Eip, attr.full(c.Eip), c.Esp, c.Ebp, (c.EFlags >> 8) & 1))

CUR_PID = [0]

def probe_slots(attr):
    """通用体检: IAT/函数指针槽若被填成 0, 任何一次 call 都会炸到 EIP=0。"""
    L('IAT / 函数指针槽体检 (0x4FB000..0x4FB200 区间里值为 0 的槽):')
    zeros = []
    va = 0x4FB000
    while va < 0x4FB200:
        pv = rd32(va)
        if pv == 0:
            zeros.append(va)
        va += 4
    if not zeros:
        L('   无 (该区间所有槽都非零)')
    else:
        L('   !! %d 个槽为 NULL: %s' % (len(zeros), ' '.join('0x%08X' % z for z in zeros[:24])))

# ---------- 现场快照 ----------
def snapshot(attr):
    y, m, d = readmem(DATE_Y, 1), readmem(DATE_M, 1), readmem(DATE_D, 1)
    # 0x5205F2 语义未坐实(月/日候选), 单列出来不写死
    date = ('%d年%d月' % (1560 + y[0], m[0])) if y and m else '日期?'
    if d:
        date += '(0x5205F2=%d?)' % d[0]
    fired = []
    for nm, va, desc in PHASE:
        v = readmem(va, 1)
        v = v[0] if v else 0
        if v == 0xFF:
            fired.append(nm)
    return date, fired

def dump_state(attr, title='当前状态'):
    date, fired = snapshot(attr)
    L('  · %s: %s | 阶段标记已触发: %s' % (title, date, ''.join(fired) or '(无)'))
    row = []
    for nm, va in HEART:
        v = rd32(va)
        if v is None:
            continue
        if v:                       # 只报非零, 免得刷屏
            row.append('%s=%d' % (nm, v))
    if row:
        L('    计数器(非零): ' + '  '.join(row))

def dump_crash(ev, r, attr, tag):
    c = r.ExceptionCode
    addr = r.ExceptionAddress or 0
    ctx, lay = get_ctx(ev.dwThreadId, attr)
    L('')
    L('=' * 76)
    L('### %s  %s (0x%08X)  首次=%s  tid=%d  [CONTEXT=%s]'
      % (tag, EXC.get(c, hex(c)), c, bool(ev.u.Exception.dwFirstChance),
         ev.dwThreadId, lay or '?'))
    L('异常地址 0x%08X   %s' % (addr, attr.full(addr)))
    if c == 0xC0000005 and r.NumberParameters:
        op = r.ExceptionInformation[0]; tgt = r.ExceptionInformation[1]
        L('  操作=%s (0读 1写 8执行)  目标=0x%08X  %s'
          % (op, tgt, attr.full(tgt)))
    if ctx:
        L('EAX=%08X EBX=%08X ECX=%08X EDX=%08X'
          % (ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx))
        L('ESI=%08X EDI=%08X EBP=%08X ESP=%08X EIP=%08X EFL=%08X'
          % (ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp, ctx.Eip, ctx.EFlags))
    dump_state(attr, '崩溃时')
    eip = ctx.Eip if ctx else addr
    L('EIP 处指令:')
    for ln in disasm(eip, 24):
        L(ln)
    esp = ctx.Esp if ctx else 0
    L('栈顶 (ESP 起 256B):')
    st = readmem(esp, 256)
    for i in range(0, min(256, len(st)) - 3, 4):
        v = struct.unpack('<I', st[i:i + 4])[0]
        L('   [0x%08X] %08X  %s' % (esp + i, v, attr.full(v)))
    L('EBP 链回溯:')
    ebp = ctx.Ebp if ctx else 0
    if not ebp or ebp & 3:
        L('   (EBP=0x%08X, 链不可用 —— 走下面的栈扫描)' % (ctx.Ebp if ctx else 0))
    for i in range(14):
        if not ebp or ebp & 3:
            break
        d = readmem(ebp, 8)
        if len(d) < 8:
            break
        prev, ret = struct.unpack('<II', d)
        L('   #%02d ret=0x%08X  %s' % (i, ret, attr.full(ret)))
        if prev <= ebp:
            break
        ebp = prev
    backtrack(attr, esp, st)
    probe_slots(attr)
    if TRACE_RING:
        L('--- 单步取证的末尾指令 (崩前最后 %d 条) ---' % len(TRACE_RING))
        L('   (EIP 序列: ' + ' '.join('%X' % x for x in list(TRACE_RING)[-40:]) + ')')
        for k, a in enumerate(list(TRACE_RING)[-60:]):
            code = readmem(a, 8)
            txt = ''
            if _md and code:
                try:
                    it = next(_md.disasm(code, a), None)
                    txt = ('%s %s' % (it.mnemonic, it.op_str)) if it else ''
                except Exception:
                    txt = ''
            L('   %-4d 0x%08X  %-20s %-32s %s'
              % (k, a, code.hex(), txt, attr.full(a)))
    L('=' * 76)
    L('')

TRACE_RING = None          # 单步取证时启用

class _Rd:
    """给 --when 表达式用: m[va] 读 1 字节, d[va] 读 4 字节。"""
    def __getitem__(self, va):
        b = readmem(va, 1)
        return b[0] if b else 0

class _Rd4:
    def __getitem__(self, va):
        return rd32(va) or 0

def _cond_ok():
    if not TRACE_WHEN:
        return True
    try:
        return bool(eval(TRACE_WHEN, {'__builtins__': {}}, {'m': _Rd(), 'd': _Rd4()}))
    except Exception as e:
        L('  !! --when 求值失败: %r' % e)
        return False

def _wpm(va, data):
    old = wintypes.DWORD()
    k32.VirtualProtectEx(_hp[0], ctypes.c_void_p(va), len(data), 0x40, ctypes.byref(old))
    w = ctypes.c_size_t(0)
    ok = k32.WriteProcessMemory(_hp[0], ctypes.c_void_p(va), data, len(data), ctypes.byref(w))
    k32.VirtualProtectEx(_hp[0], ctypes.c_void_p(va), len(data), old.value, ctypes.byref(old))
    return bool(ok)

# ---------- 主循环 ----------
def watch(pid, name):
    global TRACE_RING
    CUR_PID[0] = pid
    attr = Attr(pid, os.path.join(GAME, name))
    L('  模块 %d 个, 主模块 %s @0x%08X size=0x%X'
      % (len(attr.mods), name, attr.main_base, attr.main_sz))
    if not k32.DebugActiveProcess(pid):
        L('  !! DebugActiveProcess 失败 err=%d (已在被调试? 权限?)' % ctypes.get_last_error())
        return False, False
    k32.DebugSetProcessKillOnExit(False)     # 我们退出时不要把游戏一起带走
    L('  ✓ 已附着, 开始监控 (平时只打心跳, 异常即抓现场)')

    # ---- --trace 断点准备 ----
    bp_orig, bp_armed = b'\x00', False
    hits, steps, pending, tracing = [0], [0], [False], [False]
    armed_once = [False]
    if TRACE_VA:
        bp_orig = readmem(TRACE_VA, 1) or b'\x00'
        if _wpm(TRACE_VA, b'\xCC'):
            bp_armed = True
            L('  [trace] 断点已下 @0x%08X (原字节 %s), 命中条件 %s'
              % (TRACE_VA, bp_orig.hex(), TRACE_WHEN or '(无条件, 首次命中即开始)'))

    # ---- --probe 多点探针 ----
    probe_orig, probe_off = {}, []
    for va in PROBES:
        ob = readmem(va, 1) or b'\x00'
        if _wpm(va, b'\xCC'):
            probe_orig[va] = ob
            L('  [probe] 断点 @0x%08X (原字节 %s)' % (va, ob.hex()))
        else:
            L('  [probe] 断点写入失败 @0x%08X' % va)

    fatal = False
    exited = False
    last_hb = 0.0
    last_sig = None
    t0 = time.time()
    ev = DEBUG_EVENT()
    while True:
        if k32.WaitForDebugEvent(ctypes.byref(ev), 120):
            code = ev.dwDebugEventCode
            cont = DBG_CONTINUE
            if code == 6:                     # LOAD_DLL
                b = ev.u.LoadDll.lpBaseOfDll or 0
                nm = ''
                try:
                    p = ev.u.LoadDll.lpImageName
                    if p:
                        far = ctypes.c_void_p()
                        if k32.ReadProcessMemory(_hp[0], ctypes.c_void_p(p),
                                                 ctypes.byref(far), ctypes.sizeof(far), None):
                            raw = readmem(far.value or 0, 520)
                            nm = (raw.decode('utf-16-le', 'ignore') if ev.u.LoadDll.fUnicode
                                  else raw.decode('latin1', 'ignore')).split('\0')[0]
                except Exception:
                    pass
                if nm:
                    attr.mods.append((b, 0x100000, os.path.basename(nm)))
                    if not QUIET:
                        L('  [dll] 0x%08X %s' % (b, os.path.basename(nm)))
            elif code == 1:                   # EXCEPTION
                r = ev.u.Exception.ExceptionRecord
                c = r.ExceptionCode
                _pa = r.ExceptionAddress or 0
                _p = _pa if _pa in probe_orig else (_pa - 1 if (_pa - 1) in probe_orig else None)
                if _p is not None and c in BP_EXC:
                    _wpm(_p, probe_orig[_p])
                    probe_off.append(_p)
                    ctx = get_ctx(ev.dwThreadId, attr)[0]
                    if ctx:
                        ctx.Eip = _p
                        set_ctx(ev.dwThreadId, ctx)
                        L('  [probe] 命中 0x%08X  tid=%d  EAX=%08X ECX=%08X EDX=%08X EBX=%08X '
                          'ESI=%08X EDI=%08X EBP=%08X ESP=%08X'
                          % (_p, ev.dwThreadId, ctx.Eax, ctx.Ecx, ctx.Edx, ctx.Ebx,
                             ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp))
                    cont = DBG_CONTINUE
                elif TRACE_VA and c in BP_EXC and (
                        r.ExceptionAddress in (TRACE_VA, TRACE_VA + 1)):
                    # 我们下的断点: 还原原字节 + 回退 EIP + 置 TF 单步
                    bp_armed = False
                    _wpm(TRACE_VA, bp_orig)
                    ctx = get_ctx(ev.dwThreadId, attr)[0]
                    ctx.Eip = TRACE_VA
                    ctx.EFlags |= 0x100
                    set_ctx(ev.dwThreadId, ctx)
                    hits[0] += 1
                    L('  [trace] 命中 0x%08X (第 %d 次) tid=%d ESP=0x%08X'
                      % (TRACE_VA, hits[0], ev.dwThreadId, ctx.Esp))
                    thread_dump(attr, '断点命中时')
                    if not _cond_ok():
                        L('  [trace] 条件未满足 (仍照常录 EIP)')
                    else:
                        L('  [trace] 条件满足')
                    tracing[0] = True
                    armed_once[0] = True
                    if TRACE_RING is None:
                        TRACE_RING = deque(maxlen=TRACE_KEEP)
                    L('  [trace] 开始单步取证 (只单步 tid=%d)' % ev.dwThreadId)
                    pending[0] = True
                    cont = DBG_CONTINUE
                elif TRACE_VA and c in SS_EXC and (pending[0] or tracing[0] or armed_once[0]):
                    if pending[0]:
                        _wpm(TRACE_VA, b'\xCC')      # 重新装弹
                        bp_armed = True
                        pending[0] = False
                    # ★ 一旦断点命中过就一律录 EIP (不再受 --when 约束) ——
                    #   否则条件判错时会把唯一的现场白丢一次(已踩过)。
                    if armed_once[0]:
                        c2 = get_ctx(ev.dwThreadId, attr)[0]
                        if c2:
                            TRACE_RING.append(c2.Eip)
                        steps[0] += 1
                        if steps[0] >= TRACE_MAXSTEP:
                            tracing[0] = False
                            L('  [trace] 已达 %d 步上限, 停止单步' % TRACE_MAXSTEP)
                    cont = DBG_CONTINUE
                elif c in BENIGN:
                    cont = DBG_EXCEPTION_NOT_HANDLED
                elif c in BP_EXC + SS_EXC:
                    # 不是我们下的断点: 交还程序, 别用 DBG_CONTINUE 越过它
                    L('  [int3/单步] 0x%08X  %s (非本监控器所设, 交还程序)'
                      % (r.ExceptionAddress or 0, attr.full(r.ExceptionAddress or 0)))
                    cont = DBG_EXCEPTION_NOT_HANDLED
                else:
                    dump_crash(ev, r, attr,
                               '致命异常' if not ev.u.Exception.dwFirstChance else '首次异常')
                    if not ev.u.Exception.dwFirstChance:
                        fatal = True
                    cont = DBG_EXCEPTION_NOT_HANDLED
            elif code == 5:                   # EXIT_PROCESS
                ec = ev.u.ExitProcess.dwExitCode
                L('')
                L('>>> 进程退出  退出码=0x%08X (%d)  %s'
                  % (ec, ec, EXC.get(ec, '正常/其它')))
                dump_state(attr, '退出时')
                L('')
                exited = True
            k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, cont)
            if exited:
                return True, fatal
            if fatal and ONCE:
                return False, True
            continue

        # ---- 空闲: 心跳 + 探针重新装弹(没开 TF, 只能懒重装) ----
        now = time.time()
        if probe_off:
            for _p in probe_off:
                _wpm(_p, b'\xCC')
            probe_off.clear()
        if not QUIET and now - last_hb >= 0.7:
            last_hb = now
            try:
                date, fired = snapshot(attr)
                vals = tuple(rd32(va) for _n, va in HEART)
                sig = (date, ''.join(fired), vals)
                if sig != last_sig:
                    last_sig = sig
                    row = '  '.join('%s=%s' % (HEART[i][0], v)
                                    for i, v in enumerate(vals) if v)
                    L('[%6.1fs] %s 阶段[%s] %s' % (now - t0, date, ''.join(fired) or '-', row))
            except Exception:
                pass

def main():
    global _fh
    _fh = open(LOGPATH, 'a', encoding='utf-8', errors='replace')
    L('')
    L('=== tkmon 启动 %s ===' % time.strftime('%Y-%m-%d %H:%M:%S'))
    L('等待 TAIK2W95* 进程 (你正常开游戏即可, 我会自动附着; Ctrl-C 结束)')
    seen_bad = set()
    try:
        while True:
            pids = find_game_pids()
            pids = [p for p in pids if p[0] not in seen_bad]
            if pids:
                pid, name = pids[-1]
                L('')
                L('>>> 发现游戏 %s (pid=%d), 附着中...' % (name, pid))
                hp = k32.OpenProcess(PROCESS_ALL, False, pid)
                if not hp:
                    L('  !! OpenProcess 失败 err=%d' % ctypes.get_last_error())
                    seen_bad.add(pid); time.sleep(1.0); continue
                _hp[0] = hp
                try:
                    done, fatal = watch(pid, name)
                finally:
                    k32.CloseHandle(hp); _hp[0] = None
                L('  (本次会话结束, 回到等待; 你再开一次我继续抓)')
                seen_bad.add(pid)
                if fatal and ONCE:
                    L('=== --once: 已捕获致命异常, 停止 ===')
                    return
            time.sleep(0.6)
    except KeyboardInterrupt:
        L('=== tkmon 停止 ===')

if __name__ == '__main__':
    main()
