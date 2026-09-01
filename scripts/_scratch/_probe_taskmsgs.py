# -*- coding: utf-8 -*-
"""13 个任务 handler 的消息 ID 抽取 + 解码。
方法：跟踪 push 立即数栈，遇消息函数调用即记录参数（调用后清空栈）。
映射 off = va - 0x400000；MSGX: file = id//2000, idx = id%2000。
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import struct, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
SZ = len(MEM)

# ---------------------------------------------------------------- 消息字典
MSG = {}
mpath = os.path.join(HERE, "_probe", "msgx", "all_messages.txt")
if os.path.exists(mpath):
    # 注意：all_messages.txt 是 UTF-8，不是 GBK（2026-08-28 实测确认）
    raw = open(mpath, "rb").read().decode("utf-8", "replace")
    for line in raw.splitlines():
        m = re.match(r"\[MESSAGE(\d+)\.LZW#(\d+)\]\s*(.*)$", line)
        if m:
            MSG[(int(m.group(1)), int(m.group(2)))] = m.group(3).strip()

def msg_text(mid):
    f = mid // 2000
    i = mid % 2000
    return MSG.get((f + 1, i))

OUT = []
def emit(s=""):
    OUT.append(s)

emit("消息字典载入: %d 条" % len(MSG))

def insns(start, hi, maxb=None):
    off = start - BASE
    n = maxb if maxb else (hi - start + 0x40)
    src = bytes(MEM[off:off + n])
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    except Exception:
        return []
    res = []
    for ins in md.disasm(src, start):
        if ins.address > hi:
            break
        res.append((ins.address, ins.size, ins.mnemonic, ins.op_str))
    return res

MSG_FNS = {0x47B900, 0x47BCC0, 0x47BA40, 0x47B180,
           0x47B210, 0x47BE00, 0x47B1D0, 0x47B350}

def harvest(va_start, va_end, label):
    ins = insns(va_start, va_end)
    out = []
    pending = []
    for (a, s, m, o) in ins:
        if m == "push":
            if o.startswith("0x"):
                try:
                    pending.append((a, int(o, 16)))
                except ValueError:
                    pending.append((a, None))
            else:
                pending.append((a, None))
        elif m == "call":
            tgt = None
            if o.startswith("0x"):
                try:
                    tgt = int(o, 16)
                except ValueError:
                    pass
            if tgt in MSG_FNS:
                args = [(aa, v) for (aa, v) in pending if v is not None]
                out.append((a, tgt, args))
            pending = []
        elif m.startswith("ret"):
            pending = []
    return out

def report(label, va_start, va_end):
    hits = harvest(va_start, va_end, label)
    emit("")
    emit("=" * 76)
    emit("%s   [0x%08x..0x%08x]" % (label, va_start, va_end))
    seen = set()
    for (a, tgt, args) in hits:
        for (aa, v) in args:
            t = msg_text(v)
            if t is None:
                continue
            key = (v,)
            if key in seen:
                continue
            seen.add(key)
            emit("  @0x%08x  msg 0x%04x (M%d#%d)  %s"
                 % (aa, v, v // 2000 + 1, v % 2000, t[:78]))
    if not seen:
        emit("  (无解码到文本的 msgid)")

# ---------------------------------------------------------------- 13 handler
HANDLERS = [
    (0, "贩卖军粮", 0x45E700, 0x45E790),
    (1, "购买军粮", 0x45E790, 0x45E870),
    (2, "军马",     0x45E870, 0x45E8E0),
    (3, "洋枪",     0x45E8E0, 0x45E970),
    (4, "开垦农田", 0x45E970, 0x45E9F0),
    (5, "改建",     0x45E9F0, 0x45EA90),
    (6, "筑城",     0x45EA90, 0x45EB80),
    (7, "进贡",     0x45EB80, 0x45EC10),
    (8, "威吓",     0x45EC10, 0x45ED80),
    (9, "朝廷工作", 0x45ED80, 0x45EDF0),
    (10, "收集情报", 0x45EDF0, 0x45EEC0),
    (11, "谋略",    0x45EEC0, 0x45EF40),
    (12, "(无表项)", 0x45EF40, 0x45F040),
]
for (idx, name, s, e) in HANDLERS:
    report("handler[%d] %s" % (idx, name), s, e)

# ---------------------------------------------------------------- 菜单/分配
report("任务分配菜单（读 0x504b28 处）", 0x463300, 0x463420)
report("任务模块主体", 0x460200, 0x460900)

open(os.path.join(HERE, "_taskmsgs.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("done, msg dict=%d" % len(MSG))
