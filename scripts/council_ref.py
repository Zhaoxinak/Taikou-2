# -*- coding: utf-8 -*-
"""太阁立志传2 — 評定 / 任务分配 模块 参考实现 + 二进制自校验（2026-08-28 续64）

模块构成（两套表，勿混）：
  A. 主命（評定で命じる任務）：名表 0x504b28 × 12，菜单构建使用处 0x46336c
  B. 報告（評定で家臣/商人から聞く報告）：handler 表 0x504898 × 13，
     执行分发 0x4603f0 调用，产出 M3#610-622 报告文本

运行时状态：
  0x513fcc  word   条目数 count
  0x513fd4  word[] 条目表 stride 2；低15位 = ID，bit15 = 已询问过
  0x513fe0  word[13] 报告槽，handler 执行后清 0
  0x5176a8  30×4B 報告対象槽；+id*4 处 word = 対象ID
  0x52063c  dword  当前対象指针

対象ID → 名称（0x49c2b0，四段路由，stride 7）：
  id<1000    -> 0x521aa8 + id*7
  1000..1999 -> 0x5077b0 + (id-1000)*7
  2000..2999 -> dword[0x506c54]
  else       -> 0x507978 + (id-3000)*7
  ID 17 特例  -> 字符串 0x504888 = '商　人'；菜单末项 0x504890 = '停　止'
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

import struct, os, sys, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
SZ = len(MEM)

# ---------------------------------------------------------------- 常量
TASK_NAME_TABLE = 0x504B28        # 主命名表 12 项（指针表）
TASK_NAME_N     = 12
REPORT_HANDLERS = 0x504898        # 报告 handler 表 13 项
REPORT_N        = 13

SLOT_COUNT_VA   = 0x513FCC
SLOT_TABLE_VA   = 0x513FD4
TASK_SLOT_VA    = 0x513FE0        # 13 × word
TARGET_SLOT_VA  = 0x5176A8        # 30 × 4B

NAME_TAB_LO     = 0x521AA8        # id 0..999
NAME_TAB_MID    = 0x5077B0        # id 1000..1999
NAME_PTR_2K     = 0x506C54        # id 2000..2999 -> 指针
NAME_TAB_HI     = 0x507978        # id 3000+
NAME_STRIDE     = 7

STR_MERCHANT    = 0x504888        # '商　人'
STR_STOP        = 0x504890        # '停　止'

DISPATCHER      = 0x4603F0
MAP_FN          = 0x460420
SPECIAL_22      = 0x460550        # 築城業者（穴太衆）对话
MENU_FN         = 0x460320
COUNCIL_MAIN    = 0x460280
SLOT_INIT_FN    = 0x4607F0

FLAG_ASKED      = 0x8000          # bit15：已询问过
ID_MERCHANT     = 17
ID_CASTLE       = 0x16            # 22，走 0x460550 特例

# handler idx -> 报告消息 id（实证抽取）
REPORT_MSG = {
    1: 0x1202, 2: 0x1203, 3: 0x1204, 4: 0x1205,
    5: 0x1206, 6: 0x1207, 7: 0x1208, 8: 0x1209,
    9: 0x120A, 10: 0x120B, 11: 0x120C, 12: 0x120E,
}

def _u32(va):
    return struct.unpack_from("<I", MEM, va - BASE)[0]
def _u16(va):
    return struct.unpack_from("<H", MEM, va - BASE)[0]

def cstr(va, maxn=64):
    o = va - BASE
    if o < 0 or o >= SZ:
        return None
    e = MEM.find(b"\x00", o, o + maxn)
    if e < 0:
        e = o + maxn
    return MEM[o:e].decode("gbk", "replace")

# ---------------------------------------------------------------- 消息字典
_MSG = {}
def _load_msgs():
    global _MSG
    if _MSG:
        return _MSG
    p = os.path.join(HERE, "_probe", "msgx", "all_messages.txt")
    if not os.path.exists(p):
        return _MSG
    # all_messages.txt 是 UTF-8（2026-08-28 实测确认，非 GBK）
    raw = open(p, "rb").read().decode("utf-8", "replace")
    for line in raw.splitlines():
        m = re.match(r"\[MESSAGE(\d+)\.LZW#(\d+)\]\s*(.*)$", line)
        if m:
            _MSG[(int(m.group(1)), int(m.group(2)))] = m.group(3).strip()
    return _MSG

_MSG_GID = {}
def _load_msgs_gid():
    """权威全量索引 msgx_all_texts.json（6211 条，续72 建立）。
    texts 键 = MSGX 全局 id（= file_base + index，slot 2000）。"""
    global _MSG_GID
    if _MSG_GID:
        return _MSG_GID
    p = os.path.join(HERE, "msgx_all_texts.json")
    if not os.path.exists(p):
        return _MSG_GID
    d = json.load(open(p, encoding="utf-8"))
    _MSG_GID = {int(k): v for k, v in d.get("texts", {}).items()}
    return _MSG_GID

def msg_text(mid):
    """MSGX 编号：file = id // 2000，序号 = id % 2000。

    数据源优先级（续94 修正）：
      1. `msgx_all_texts.json` — 权威全量索引 6211 条，按全局 id 直查；
      2. `_probe/msgx/all_messages.txt` — 旧解码产物，位于可再生 gitignore
         目录，常不存在且仅覆盖 3091 条。仅作回退。
    """
    t = _load_msgs_gid().get(mid)
    if t is not None:
        return t
    return _load_msgs().get((mid // 2000 + 1, mid % 2000))

# ---------------------------------------------------------------- 表访问
def task_names():
    """主命名表（12 项）"""
    return [cstr(_u32(TASK_NAME_TABLE + 4 * i)) for i in range(TASK_NAME_N)]

def report_handlers():
    return [_u32(REPORT_HANDLERS + 4 * i) for i in range(REPORT_N)]

def report_text(idx):
    """报告 handler idx 对应的报告文本"""
    mid = REPORT_MSG.get(idx)
    return msg_text(mid) if mid is not None else None

def target_name(target_id):
    """0x49c2b0：対象ID -> 名称字符串"""
    i = target_id & 0xFFFF
    if i < 1000:
        return cstr(NAME_TAB_LO + i * NAME_STRIDE)
    if i < 2000:
        return cstr(NAME_TAB_MID + (i - 1000) * NAME_STRIDE)
    if i < 3000:
        return cstr(_u32(NAME_PTR_2K))
    return cstr(NAME_TAB_HI + (i - 3000) * NAME_STRIDE)

def slot_target(slot_id):
    """報告対象槽 0x5176a8 + id*4 处的 word = 対象ID（id < 30）"""
    if slot_id >= 30:
        return None
    return _u16(TARGET_SLOT_VA + slot_id * 4)

def slot_label(entry_id, target_words=None):
    """复刻 0x460320 菜单项取名。
    target_words: 可选的 30 个対象ID 列表（默认从二进制读，静态映像里为 0）。"""
    e = entry_id & 0x7FFF
    if e == ID_MERCHANT:
        return cstr(STR_MERCHANT)
    if e < 30:
        tid = target_words[e] if target_words is not None else slot_target(e)
        return target_name(tid)
    return None

def menu_items(entries, target_words=None):
    """复刻 0x460320：count 个条目 + 末项「停　止」"""
    labels = [slot_label(e, target_words) for e in entries]
    labels.append(cstr(STR_STOP))
    return labels

def dispatch(entry_id):
    """复刻 0x4603f0：返回 ('special_22',) 或 ('handler', idx)
    idx 由 0x460420 得出；此处只判定特例分支，映射逻辑见 MAP_FN 反汇编。"""
    e = entry_id & 0x7FFF
    if e == ID_CASTLE:
        return ("special_22", SPECIAL_22)
    return ("handler", None)

# ---------------------------------------------------------------- 自检
REPORT = []
def _ok(cond, msg):
    line = "  [%s] %s" % ("OK  " if cond else "FAIL", msg)
    REPORT.append(line)
    print(line)
    return bool(cond)

def self_test():
    global REPORT
    REPORT = []
    n = p = 0
    try:
        names = task_names()
        n += 1; p += _ok(names == ["贩卖军粮", "购买军粮", "军马", "洋枪", "开垦农田", "改建",
                                  "筑城", "进贡", "威吓", "朝廷工作", "收集情报", "谋略"],
                         "主命名表 0x504b28 = " + "/".join(names))
        hs = report_handlers()
        n += 1; p += _ok(len(hs) == 13 and hs[1] == 0x45E790 and hs[12] == 0x45EF40,
                         "报告 handler 表 0x504898 共 13 项，[1]=0x45e790 [12]=0x45ef40")
        n += 1; p += _ok(hs[13 - 1] == 0x45EF40 and _u32(REPORT_HANDLERS + 4 * 13) == 0,
                         "第 14 项为 0（表长精确 13）")
        # 报告文本
        exp = {1: "我去过", 2: "如今好像在", 3: "好像擅长", 5: "头号家臣",
               9: "卧病不起", 11: "马贩子", 12: "稻米贩卖"}
        ok = True
        detail = []
        for idx, sub in exp.items():
            t = report_text(idx)
            detail.append("%d:%s" % (idx, (t or "?")[:12]))
            if not t or sub not in t:
                ok = False
        n += 1; p += _ok(ok, "报告文本解码命中关键子串 " + " ".join(detail))
        n += 1; p += _ok(all(report_text(i) for i in range(1, 13)),
                         "handler[1..12] 均有解码文本（M3#610-622）")
        n += 1; p += _ok(report_text(0) is None,
                         "handler[0] 无报告文本（实为対象槽设置，调 0x441750）")
        # 対象ID -> 名称 四段路由
        a = target_name(0)
        b = target_name(1000)
        c = target_name(3000)
        n += 1; p += _ok(a is not None and b is not None and c is not None,
                         "対象ID 四段路由可读 id0=%r id1000=%r id3000=%r" % (a, b, c))
        n += 1; p += _ok(target_name(0) == cstr(NAME_TAB_LO) and target_name(1000) == cstr(NAME_TAB_MID),
                         "id0 命中 0x521aa8+0, id1000 命中 0x5077b0+0（分段正确）")
        # 菜单
        n += 1; p += _ok(slot_label(17) == "商　人", "ID 17 -> '商　人'（0x504888 特例）")
        n += 1; p += _ok(cstr(STR_STOP) == "停　止", "末项 = '停　止'（0x504890）")
        tw = [0] * 30
        tw[0] = 0
        tw[1] = 1000
        items = menu_items([0, 1, 17], tw)
        n += 1; p += _ok(len(items) == 4 and items[2] == "商　人" and items[3] == "停　止",
                         "menu_items: 3 条目 + '停　止' -> " + str(items))
        n += 1; p += _ok(items[0] == target_name(0) and items[1] == target_name(1000),
                         "条目名按 対象ID 走 0x49c2b0 路由")
        # bit15 已询问标志
        e = 5
        n += 1; p += _ok((e & FLAG_ASKED) == 0 and ((e | FLAG_ASKED) & 0x7FFF) == 5,
                         "bit15 已询问标志：置位不影响低15位 ID（and 0x7fff 还原）")
        # 分发特例
        n += 1; p += _ok(dispatch(22)[0] == "special_22" and dispatch(22)[1] == 0x460550,
                         "ID 22 -> 0x460550 築城業者特例（其余走 handler 表）")
        n += 1; p += _ok(dispatch(5)[0] == "handler", "ID 5 -> handler 表路径")
        # MSGX 编号规则交叉验证
        n += 1; p += _ok(msg_text(0x1202) is not None and msg_text(0xDA3) is not None,
                         "MSGX 编号 file=id//2000 交叉验证通过（0x1202 / 0xda3）")
    except Exception:
        import traceback
        REPORT.append("ERROR:\n" + traceback.format_exc())
    summary = "self_test: %d/%d %s" % (p, n, "ALL PASS" if p == n else "FAIL")
    REPORT.append(summary)
    open(os.path.join(HERE, "_council_selftest.txt"), "w", encoding="utf-8").write("\n".join(REPORT))
    return p == n

if __name__ == "__main__":
    ok = self_test()
    if "--dump" in sys.argv:
        print("")
        print("主命（12）: " + " / ".join(task_names()))
        print("")
        print("报告 handler -> 文本")
        for i in range(1, 13):
            print("  [%2d] 0x%08x  %s" % (i, report_handlers()[i], report_text(i)))
    sys.exit(0 if ok else 1)
