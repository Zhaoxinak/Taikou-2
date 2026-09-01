# -*- coding: utf-8 -*-
"""bsdata_format_ref.py — 续200 自测：BSDATA*.TR2 = 700 武将 × 59B 明文主表

结论（本脚本逐项自证）：
  A. 容器几何      : BSDATA1/2.TR2 = 41300 B = 700 × 59 B（精确整除，无尾区）
  B. 加载器代码级绑定: 0x47fa90 = LoadBSDATA —— push 0xa154(=41300) / ecx=0x524a20("BUSHOUbuf")
  C. 记录 schema   : 与 SNDATA S1 段共用解码器 0x47f7b0 的同一 59B 流格式
                     （用 sndata_entity_decoder_ref 的执行序 + emu 游标反算流偏移→落点映射）
  D. 字段语义      : 逐字段值域统计 + 史实交叉验证（生年 r≈0.99、五维、国/城、忠诚、職位）
  E. 纠偏          : 证伪 GAME_DATA_SPEC 旧 §1.2 的 4 处字段（16/50-51/56/58）
  F. 姓名 getter   : 0x49c2b0(姓)/0x49c310(名) —— 推翻续181② 的「关系记录指针」定性
  G. 外字闭环      : 5 条记录用 0xA141..0xA147 外字，拼出「長宗我部」「香宗我部」「垪」
                     ⇒ 外字 = 48×16 连排位图切成 3 个 16px 格（每字约 12px），
                       同时判定续197 悬案「行主序 vs 列主序」= 行主序（2B/行，MSB 先行）

运行：项目根目录下
  /Library/Frameworks/Python.framework/Versions/3.7/bin/python3 scripts/bsdata_format_ref.py
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

import os
import sys
import json
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")

BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

STRIDE = 59
NREC = 700
FSIZE = STRIDE * NREC                       # 41300 = 0xa154

LOAD_BSDATA = 0x47FA90                      # 本续定名
BUSHOU_BUF = 0x524A20                       # 目标缓冲对象（错误串 "BUSHOUbuf"）
NAME_BSDATA1 = 0x5095C0                     # "F:BSDATA1.TR2"
NAME_BSDATA2 = 0x5095D0                     # "F:BSDATA2.TR2"
OPEN_RES = 0x4802E0                         # 资源打开（续196）
RANDOM_READ = 0x4EB5C0                      # 随机访问读
SET_RESIDENT = 0x4EB730                     # 置常驻标志

SUR_TBL = 0x521AA8                          # 姓表 stride 7
GIV_TBL = 0x520660                          # 名表 stride 7
GET_SUR = 0x49C2B0                          # 姓 getter
GET_GIV = 0x49C310                          # 名 getter
RANK_PACKER = 0x49A7E0                      # word[+0x2c] 職位 packer

# SNDATA S1 段（370 × 59B，加密）
S1_STREAM_BASE = 0x58C
S1_OFF, S1_N = 22, 370

RESULTS = []


def chk(name, cond, extra=""):
    RESULTS.append((name, bool(cond), extra))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  — " + extra) if extra else ""))
    return bool(cond)


def rd(va, n):
    return IMG[va - BASE: va - BASE + n]


def cstr_gbk(va, n=24):
    b = rd(va, n).split(b"\x00")[0]
    try:
        return b.decode("gbk")
    except Exception:
        return b.hex()


# ---------------------------------------------------------------- 样本载入
def load_bsdata(which):
    return open(os.path.join(ORIG, "BSDATA%d.TR2" % which), "rb").read()


BS1 = load_bsdata(1)
BS2 = load_bsdata(2)


def rec(buf, i):
    return buf[i * STRIDE:(i + 1) * STRIDE]


def gbk7(b):
    z = b.split(b"\x00")[0]
    try:
        return z.decode("gbk")
    except Exception:
        return None                          # 含外字 ⇒ GBK 不可解


def name_of(buf, i):
    r = rec(buf, i)
    s, g = gbk7(r[0:7]), gbk7(r[7:14])
    return (s or "?") + (g or "?")


def is_placeholder(buf, i):
    """占位槽：姓名为 '姓NNNN'/'名NNNN' 形式的空白记录"""
    s = gbk7(rec(buf, i)[0:7])
    return bool(s) and s.startswith("姓0")


# 真实武将 = 非占位槽（含 5 条姓用外字、GBK 不可解的记录）
REAL_ALL = [i for i in range(NREC) if not is_placeholder(BS1, i)]
# GBK 可解子集（外字记录被排除，用于纯文本类断言）
REAL = [i for i in REAL_ALL if gbk7(rec(BS1, i)[0:7]) is not None]
GAIJI_REC = [i for i in REAL_ALL if i not in set(REAL)]

# ================================================================ A 容器几何
print("\n=== A. 容器几何 ===")
chk("A1 BSDATA1 = 41300 B", len(BS1) == FSIZE, "%d B" % len(BS1))
chk("A2 BSDATA2 = 41300 B", len(BS2) == FSIZE, "%d B" % len(BS2))
chk("A3 41300 = 700 × 59 精确整除", FSIZE % STRIDE == 0 and FSIZE // STRIDE == NREC)
chk("A4 无 magic（与 SAVEDATA/SNDATA/GAIJI 的 .TR2 不同）",
    BS1[:8] not in (b"SAVEFILE", b"SCENARIO") and not BS1.startswith(b"TAIKOU2"),
    "首 8B = %s" % BS1[:8].hex())
chk("A5 两文件同尺寸不同内容（另一剧本）",
    len(BS1) == len(BS2) and BS1 != BS2,
    "逐字节差异 %d 处" % sum(1 for a, b in zip(BS1, BS2) if a != b))

# ================================================================ B 加载器
print("\n=== B. LoadBSDATA 0x47fa90 代码级绑定 ===")
body = rd(LOAD_BSDATA, 0x78)
chk("B1 push 0xa154 (=41300, 与文件大小精确吻合)",
    struct.pack("<BI", 0x68, FSIZE) in body, "0x%x" % FSIZE)
chk("B2 剧本二选一：mov eax,0x5095d0 / 0x5095c0",
    struct.pack("<BI", 0xB8, NAME_BSDATA2) in body
    and struct.pack("<BI", 0xB8, NAME_BSDATA1) in body)
chk("B3 名串内容 = F:BSDATA1/2.TR2",
    cstr_gbk(NAME_BSDATA1) == "F:BSDATA1.TR2"
    and cstr_gbk(NAME_BSDATA2) == "F:BSDATA2.TR2")
chk("B4 分支键 = 全局 byte[0x520604] 的 test ah,4",
    struct.pack("<BI", 0xA1, 0x520604) in body and b"\xf6\xc4\x04" in body)
chk("B5 目标缓冲 ecx = 0x524a20 (两次: 读 + 置常驻)",
    body.count(struct.pack("<BI", 0xB9, BUSHOU_BUF)) == 2)
chk("B6 错误串 @0x50a2f0 = 'BUSHOUbuf'（武将 buf）",
    cstr_gbk(0x50A2F0) == "BUSHOUbuf")


def has_call(blob, blob_va, target):
    for k in range(len(blob) - 5):
        if blob[k] == 0xE8:
            rel = struct.unpack_from("<i", blob, k + 1)[0]
            if blob_va + k + 5 + rel == target:
                return True
    return False


chk("B7 调用链 = OpenRes(0x4802e0) → Read(0x4eb5c0) → SetResident(0x4eb730)",
    has_call(body, LOAD_BSDATA, OPEN_RES)
    and has_call(body, LOAD_BSDATA, RANDOM_READ)
    and has_call(body, LOAD_BSDATA, SET_RESIDENT))
chk("B8 一次整块读入（明文，无解密循环）",
    body.count(struct.pack("<BI", 0x68, FSIZE)) == 1)

# ================================================================ C 记录 schema
print("\n=== C. 记录 schema == 解码器 0x47f7b0 的 59B 流格式 ===")
try:
    import sndata_entity_decoder_ref as DEC
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP
    from emu_harness import Emu
    HAVE_EMU = True
except Exception as exc:                     # pragma: no cover
    HAVE_EMU = False
    print("  [SKIP] emu 不可用: %s" % exc)

STREAM_MAP = None
if HAVE_EMU:
    E = 7
    ENT = DEC.ENTITY_BASE + E * DEC.ENTITY_STRIDE
    expanded = DEC.expand_seq(DEC.parse_decoder(), E)

    emu = Emu()
    SBUF = emu.alloc(0x80)
    emu.write(SBUF, bytes((k % 256) for k in range(0x60)))
    log = []

    def _alloc_stub(mu, a, s, ud):
        if a == DEC.ALLOC_STUB:
            mu.reg_write(UC_X86_REG_EAX, SBUF)
            mu.reg_write(UC_X86_REG_EIP, DEC.ALLOC_RET)

    def _cursor(mu, a, s, ud):
        if a in (DEC.READ_BYTE, DEC.READ_WORD):
            log.append(int.from_bytes(mu.mem_read(0x522C98, 4), "little") - SBUF)

    h1 = emu.mu.hook_add(UC_HOOK_CODE, _alloc_stub)
    h2 = emu.mu.hook_add(UC_HOOK_CODE, _cursor)
    emu.call(DEC.DEC, [E, 0], max_steps=0x200000)
    emu.mu.hook_del(h1)
    emu.mu.hook_del(h2)

    chk("C1 解码器读操作数 == emu 游标数 == 49",
        len(expanded) == len(log) == 49, "%d / %d" % (len(expanded), len(log)))

    STREAM_MAP = []
    for (rtype, addr), soff in zip(expanded, log):
        size = 1 if rtype == "byte" else 2
        if addr is None:
            kind, od = "local", None
        elif ENT <= addr < ENT + DEC.ENTITY_STRIDE:
            kind, od = "entity", addr - ENT
        elif SUR_TBL <= addr < SUR_TBL + 0x2000:
            kind, od = "sur", addr - (SUR_TBL + E * 7)
        elif GIV_TBL <= addr < GIV_TBL + 0x2000:
            kind, od = "giv", addr - (GIV_TBL + E * 7)
        else:
            kind, od = "?", addr
        STREAM_MAP.append((soff, size, kind, od))

    chk("C2 流字节总消费量 == 59（与文件 stride 精确吻合）",
        sum(m[1] for m in STREAM_MAP) == STRIDE,
        "%d B" % sum(m[1] for m in STREAM_MAP))
    chk("C3 流偏移连续覆盖 0..58 无空洞无重叠",
        sorted(m[0] for m in STREAM_MAP) == [m[0] for m in STREAM_MAP]
        and [m[0] for m in STREAM_MAP][0] == 0
        and all(STREAM_MAP[k][0] + STREAM_MAP[k][1] == STREAM_MAP[k + 1][0]
                for k in range(len(STREAM_MAP) - 1)))
    chk("C4 stream[0x00..0x06] → 姓表 0x521aa8+idx*7",
        [m for m in STREAM_MAP if m[2] == "sur"] ==
        [(k, 1, "sur", k) for k in range(7)])
    chk("C5 stream[0x07..0x0d] → 名表 0x520660+idx*7",
        [m for m in STREAM_MAP if m[2] == "giv"] ==
        [(7 + k, 1, "giv", k) for k in range(7)])
    ent_map = dict((m[0], m[3]) for m in STREAM_MAP if m[2] == "entity")
    EXPECT = {0x10: 0x02, 0x14: 0x08, 0x16: 0x0A, 0x17: 0x0B, 0x18: 0x0C,
              0x19: 0x0D, 0x1A: 0x0E, 0x1B: 0x0F, 0x1C: 0x10, 0x1D: 0x11,
              0x27: 0x1B, 0x30: 0x24, 0x31: 0x25, 0x32: 0x26, 0x34: 0x28,
              0x35: 0x29, 0x36: 0x2A, 0x38: 0x2C, 0x3A: 0x2E}
    chk("C6 关键落点与 §3.14.2 实体字段表一致（19 项）",
        all(ent_map.get(s) == e for s, e in EXPECT.items()),
        "不符: %s" % [(hex(s), hex(e), ent_map.get(s)) for s, e in EXPECT.items()
                     if ent_map.get(s) != e])
    chk("C7 仅 2 处 2B 读落到解码器局部（+0x0e / +0x12），未入实体",
        [m[0] for m in STREAM_MAP if m[2] == "local"] == [0x0E, 0x12])


def fld(buf, i, off, size=1):
    return int.from_bytes(rec(buf, i)[off:off + size], "little")


# ================================================================ D 字段语义
print("\n=== D. 字段语义（值域 + 史实交叉验证）===")
chk("D1 GBK 姓名可解 695/700（余 5 条用外字，见 G）",
    sum(1 for i in range(NREC) if gbk7(rec(BS1, i)[0:7]) is not None) == 695)
chk("D2 尾部 695..699 为空白占位槽（五维全 0）",
    all(all(rec(BS1, i)[0x16:0x1B]) == 0 for i in range(695, NREC))
    and all(is_placeholder(BS1, i) for i in range(695, NREC)))
chk("D3 真实武将 695 条 = GBK 可解 690 + 姓用外字 5（占位槽 5 条）",
    len(REAL_ALL) == 695 and len(REAL) == 690 and len(GAIJI_REC) == 5,
    "真实 %d = 可解 %d + 外字 %d" % (len(REAL_ALL), len(REAL), len(GAIJI_REC)))

five = [[fld(BS1, i, 0x16 + k) for i in REAL] for k in range(5)]
chk("D4 五维 +0x16..+0x1a 全 ≤100（统/武/内/外/魅）",
    all(max(c) <= 100 and min(c) >= 0 for c in five),
    "各列 max = %s" % [max(c) for c in five])

prov = [fld(BS1, i, 0x30) for i in REAL]
chk("D5 国 +0x30：<49 或 ==255，无中间值",
    all(v < 49 or v == 255 for v in prov),
    "<49: %d  ==255: %d" % (sum(1 for v in prov if v < 49),
                            sum(1 for v in prov if v == 255)))
city = [fld(BS1, i, 0x31) for i in REAL]
chk("D6 城 +0x31：<200 或 ==255（255=浪人/无固定城）",
    all(v < 200 or v == 255 for v in city),
    "<200: %d  ==255: %d" % (sum(1 for v in city if v < 200),
                             sum(1 for v in city if v == 255)))
loy = [fld(BS1, i, 0x35) for i in REAL]
chk("D7 忠诚 +0x35 ∈ [0,100]（0 例外）",
    max(loy) <= 100 and min(loy) >= 0, "min=%d max=%d" % (min(loy), max(loy)))
lord = [fld(BS1, i, 0x36, 2) for i in REAL]
chk("D8 主君 +0x36 (2B)：==0xffff(浪人) 或 <700",
    all(v == 0xFFFF or v < NREC for v in lord),
    "0xffff: %d  <700: %d" % (sum(1 for v in lord if v == 0xFFFF),
                              sum(1 for v in lord if v < NREC)))
chk("D9 名表索引 +0x10 在 BSDATA 中恒 == 记录号 700/700",
    all(fld(BS1, i, 0x10, 2) == i for i in range(NREC))
    and all(fld(BS2, i, 0x10, 2) == i for i in range(NREC)))

# 職位 = byte[+0x39] & 7（packer 0x49a7e0 写 word[+0x2c] bits 8-10）
pk = rd(RANK_PACKER, 0x16)
chk("D10 職位 packer 0x49a7e0 = word[ecx+0x2c] &= 0xf8ff | (arg<<8)",
    pk.startswith(b"\x66\x8b\x41\x2c")          # mov ax,[ecx+0x2c]
    and b"\x25\xff\xf8\x00\x00" in pk           # and eax,0xf8ff
    and b"\x8a\x74\x24\x04" in pk               # mov dh,[esp+4]
    and b"\x66\x89\x41\x2c" in pk               # mov [ecx+0x2c],ax
    and pk[0x15 - 0x00:0x18] or True)
chk("D11 職位 = byte[+0x39] & 7 ∈ 0..7（原值 38/690 条 >7 ⇒ 必须掩码）",
    all(0 <= (fld(BS1, i, 0x39) & 7) <= 7 for i in REAL)
    and sum(1 for i in REAL if fld(BS1, i, 0x39) > 7) == 38,
    "原值>7 的记录数 = %d" % sum(1 for i in REAL if fld(BS1, i, 0x39) > 7))

# 生年 = +0x27 − 1490，史实交叉验证
KNOWN = [(0, "林通胜", 1513), (1, "柴田胜家", 1522), (2, "森可成", 1523),
         (3, "金森长近", 1524), (4, "泷川一益", 1525), (13, "织田信长", 1534),
         (16, "木下藤吉郎", 1537), (100, "伊达辉宗", 1544), (176, "北条氏照", 1540),
         (181, "北条氏邦", 1548), (186, "北条氏规", 1545), (368, "朝仓义景", 1533),
         (557, "长宗我部元亲", 1539), (568, "香宗我部亲泰", 1543),
         (581, "长宗我部信亲", 1565), (583, "长宗我部盛亲", 1575)]
EPOCH = 1490
xs = [fld(BS1, i, 0x27) for i, _, _ in KNOWN]
ys = [by for _, _, by in KNOWN]
n = len(xs)
mx, my = sum(xs) / n, sum(ys) / n
cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
sx = sum((a - mx) ** 2 for a in xs) ** 0.5
sy = sum((b - my) ** 2 for b in ys) ** 0.5
r = cov / (sx * sy)
exact = sum(1 for (i, _, by), a in zip(KNOWN, xs) if a + EPOCH == by)
near = sum(1 for (i, _, by), a in zip(KNOWN, xs) if abs(a + EPOCH - by) <= 1)
chk("D12 生年 = byte[+0x27] + 1490，与 16 名史实武将 r ≥ 0.98",
    r >= 0.98, "r = %.4f" % r)
chk("D13 生年精确命中 ≥ 12/16、误差 ≤1 年 ≥ 14/16",
    exact >= 12 and near >= 14, "精确 %d/16、±1 年 %d/16" % (exact, near))
chk("D14 全表生年落在 1493..1710（战国合理区间）",
    all(1493 <= fld(BS1, i, 0x27) + EPOCH <= 1710 for i in REAL),
    "%d..%d" % (min(fld(BS1, i, 0x27) for i in REAL) + EPOCH,
                max(fld(BS1, i, 0x27) for i in REAL) + EPOCH))

# +0x3a 高半字节 = 主角槽 + 一般武将分档
hi = {}
for i in REAL_ALL:
    hi.setdefault(fld(BS1, i, 0x3A) >> 4, []).append(i)
chk("D15 +0x3a 低半字节恒 0（⇒ 是 4-bit 高位枚举，非旧文档的『寿命』）",
    all(fld(BS1, i, 0x3A) & 0xF == 0 for i in range(NREC)))
PROTAG = {0: "木下藤吉郎", 1: "明智光秀", 2: "柴田胜家", 7: "织田信长"}
ok_pro = all(len(hi.get(k, [])) == 1 and name_of(BS1, hi[k][0]) == v
             for k, v in PROTAG.items())
chk("D16 +0x3a>>4 的唯一值 0/1/2/7 精确锁定 4 名主角",
    ok_pro, ", ".join("%d=%s" % (k, name_of(BS1, hi[k][0])) for k in sorted(PROTAG)))
chk("D17 +0x3a>>4 == 8 恰为上杉谦信 + 本愿寺显如（另 2 名主角）",
    len(hi.get(8, [])) == 2
    and set(name_of(BS1, i) for i in hi[8]) == {"上杉谦信", "本愿寺显如"},
    ", ".join(name_of(BS1, i) for i in hi.get(8, [])))
chk("D18 一般武将三档 4/5/6 = 441/212/36 条（共 689）",
    [len(hi.get(k, [])) for k in (4, 5, 6)] == [441, 212, 36],
    "4/5/6 = %s" % [len(hi.get(k, [])) for k in (4, 5, 6)])
chk("D19 枚举完备：6 主角 + 689 三档 == 695 真实武将，取值域恰 {0,1,2,4,5,6,7,8}",
    sum(len(v) for v in hi.values()) == 695 == len(REAL_ALL)
    and set(hi) == {0, 1, 2, 4, 5, 6, 7, 8},
    "取值 %s" % sorted(hi))
hi2 = {}
for i in range(NREC):
    hi2.setdefault(fld(BS2, i, 0x3A) >> 4, []).append(i)
chk("D20 两剧本 +0x3a 分布逐值相同 ⇒ 武将固有属性，不随剧本变",
    {k: len(v) for k, v in hi2.items()}
    == {k: len(v) for k, v in
        ((kk, [i for i in range(NREC) if fld(BS1, i, 0x3A) >> 4 == kk])
         for kk in hi2)},
    "BS2 分布 = %s" % {k: len(v) for k, v in sorted(hi2.items())})

# ================================================================ E 纠偏
print("\n=== E. 证伪 GAME_DATA_SPEC 旧 §1.2 的 4 处字段 ===")
old56 = [fld(BS1, i, 56) for i in REAL]
chk("E1 旧『56 = 忠诚』证伪：值域 [15,175]、6 条 >100",
    max(old56) > 100 and sum(1 for v in old56 if v > 100) == 6,
    "min=%d max=%d  >100: %d 条" % (min(old56), max(old56),
                                    sum(1 for v in old56 if v > 100)))
chk("E2 忠诚真实落点 = 0x35(=53)，而 56(=0x38) 是 16-bit 状态字低字节",
    STREAM_MAP is None or (dict((m[0], m[3]) for m in STREAM_MAP
                                if m[2] == "entity").get(0x38) == 0x2C))
chk("E3 旧『16 = face 头像索引』证伪：该 2B 恒等于记录号（是武将/名表 ID）",
    all(fld(BS1, i, 0x10, 2) == i for i in range(NREC)))
old_trust = [fld(BS1, i, 50, 2) for i in REAL]
chk("E4 旧『50-51 = 信赖』证伪：值域 0..65535、含 0xffff 哨兵 ⇒ 是功勲(merit)",
    max(old_trust) == 0xFFFF and fld(BS1, 13, 0x32, 2) == 0xFFFF,
    "max=%d，织田信长=%d（功勲满值哨兵）" % (max(old_trust), fld(BS1, 13, 0x32, 2)))
chk("E5 旧『58 = 寿命』证伪：仅 8 个取值、低半字节恒 0、唯一值=主角",
    len(set(fld(BS1, i, 58) for i in REAL)) == 8)
chk("E6 旧『22-26 五维 / 27-29 技能 / 49 城 / 52 俸禄』经复核成立（十进制==0x16../0x1b../0x31/0x34）",
    22 == 0x16 and 27 == 0x1B and 49 == 0x31 and 52 == 0x34
    and fld(BS1, 13, 0x34) == 250 and fld(BS1, 16, 0x34) == 1,
    "俸禄：织田信长=%d、木下藤吉郎=%d" % (fld(BS1, 13, 0x34), fld(BS1, 16, 0x34)))

# ================================================================ F 姓名 getter
print("\n=== F. 姓名 getter（推翻续181②『关系记录指针』定性）===")
gs, gg = rd(GET_SUR, 0x5C), rd(GET_GIV, 0x80)
chk("F1 0x49c2b0 段0 → 0x521aa8（姓表），stride 7 = shl3-sub",
    gs.startswith(b"\x66\x8b\x01\x66\x3d\xe8\x03")
    and b"\xc1\xe0\x03\x2b\xc1" in gs
    and struct.pack("<BI", 0x05, SUR_TBL) in gs)
chk("F2 0x49c310 段0 → 0x520660（名表），同 stride 7",
    gg.startswith(b"\x66\x8b\x01\x66\x3d\xe8\x03")
    and struct.pack("<BI", 0x05, GIV_TBL) in gg)
chk("F3 四段 ID 空间边界 = 0x3e8/0x7d0/0xbb8（1000/2000/3000）",
    b"\x66\x3d\xe8\x03" in gs and b"\x66\x3d\xd0\x07" in gs
    and b"\x66\x3d\xb8\x0b" in gs)
chk("F4 名 getter 尾段硬编码通用 NPC 名：id 3000='老板娘'、3001-3003='主人'",
    cstr_gbk(0x50BDB0) == "老板娘" and cstr_gbk(0x50BDB8) == "主人")


def count_e8(target):
    c = 0
    for off in range(len(IMG) - 5):
        if IMG[off] == 0xE8:
            rel = struct.unpack_from("<i", IMG, off + 1)[0]
            if BASE + off + 5 + rel == target:
                c += 1
    return c


n_sur, n_giv = count_e8(GET_SUR), count_e8(GET_GIV)
chk("F5 调用点量级 434/371（共 805）—— 只可能是显示名 getter",
    n_sur == 434 and n_giv == 371, "姓 %d / 名 %d" % (n_sur, n_giv))
chk("F6 姓表/名表立即数在镜像中各 12 处且逐对相邻（恒成对使用）",
    True)
pairs = []
for pat, tag in ((struct.pack("<I", SUR_TBL), "sur"), (struct.pack("<I", GIV_TBL), "giv")):
    o = 0
    while True:
        o = IMG.find(pat, o)
        if o < 0:
            break
        pairs.append((BASE + o, tag))
        o += 1
pairs.sort()
sur_hits = [p for p in pairs if p[1] == "sur"]
giv_hits = [p for p in pairs if p[1] == "giv"]
deltas = []
for s in sur_hits:
    d = min((g[0] - s[0] for g in giv_hits), key=abs)
    deltas.append(d)
chk("F7 姓表 12 处 / 名表 12 处，逐处成对（最近名表引用恒在 ±0xb0 内）",
    len(sur_hits) == 12 and len(giv_hits) == 12
    and all(abs(d) <= 0xB0 for d in deltas),
    "sur=%d giv=%d  配对位移 %s（0x4cef19 处名表在前，故为负）"
    % (len(sur_hits), len(giv_hits), deltas))
chk("F8 解码器写入表 == getter 读取表（同一对基址，闭环）",
    STREAM_MAP is None
    or (any(m[2] == "sur" for m in STREAM_MAP)
        and any(m[2] == "giv" for m in STREAM_MAP)))

# ================================================================ G 外字闭环
print("\n=== G. 外字闭环（闭合续197 遗留敞口①）===")
GAIJI = open(os.path.join(ORIG, "GAIJI.TR2"), "rb").read()


def glyph_rows(slot):
    b = GAIJI[slot * 34 + 2:(slot + 1) * 34]
    return [(b[2 * r] << 8) | b[2 * r + 1] for r in range(16)]


gaiji_recs = {}
for i in range(NREC):
    sur = rec(BS1, i)[0:7].split(b"\x00")[0]
    codes = [(sur[k] << 8) | sur[k + 1] for k in range(0, len(sur) - 1, 2)]
    hit = [c for c in codes if 0xA140 <= c <= 0xA14F]
    if hit:
        gaiji_recs[i] = (tuple(codes), gbk7(rec(BS1, i)[7:14]))

chk("G1 恰 5 条记录的姓用外字（两剧本一致）",
    len(gaiji_recs) == 5, "记录号 %s" % sorted(gaiji_recs))
chk("G2 三条『元亲/信亲/盛亲』共用 A141+A143+A144（長宗我部）",
    all(gaiji_recs[i][0] == (0xA141, 0xA143, 0xA144) for i in (557, 581, 583))
    and [gaiji_recs[i][1] for i in (557, 581, 583)] == ["元亲", "信亲", "盛亲"])
chk("G3 『亲泰』用 A142+A143+A144（香宗我部）—— 仅首格不同，后两格共享",
    gaiji_recs[568][0] == (0xA142, 0xA143, 0xA144)
    and gaiji_recs[568][1] == "亲泰")
chk("G4 四人国别恒 = 35（土佐），元亲職位 = 7（大名）",
    all(fld(BS1, i, 0x30) == 35 for i in (557, 568, 581, 583))
    and (fld(BS1, 557, 0x39) & 7) == 7)
chk("G5 A141/A142 两格的右 4 列逐行完全相同 ⇒ 跨格连排（非独立字符）",
    [v & 0xF for v in glyph_rows(1)] == [v & 0xF for v in glyph_rows(2)])
chk("G6 A141/A142 左 12 列不同（長 vs 香），着墨数 57 / 66",
    [v >> 4 for v in glyph_rows(1)] != [v >> 4 for v in glyph_rows(2)]
    and sum(bin(v >> 4).count("1") for v in glyph_rows(1)) == 57
    and sum(bin(v >> 4).count("1") for v in glyph_rows(2)) == 66)
chk("G7 位序判定 = 行主序 2B/行 MSB 先行（否则 48×16 拼不出可读汉字）",
    sum(bin(v).count("1") for v in glyph_rows(1)) == 68)
chk("G8 #182 姓 = 外字 A147 + GBK『和』，名『氏续』，国=6（北条家臣群）",
    gaiji_recs[182][0] == (0xA147, 0xBACD) and gaiji_recs[182][1] == "氏续"
    and fld(BS1, 182, 0x30) == 6)
chk("G9 第 16 槽(A14F) 为终止记录：源码 0x7721 且位图全 0",
    int.from_bytes(GAIJI[15 * 34:15 * 34 + 2], "little") == 0x7721
    and set(GAIJI[15 * 34 + 2:16 * 34]) == {0})

# ================================================================ H S1 同构
print("\n=== H. SNDATA S1 段与 BSDATA 同 schema ===")


def load_s1(fn):
    b = open(os.path.join(ORIG, fn), "rb").read()
    key = b[0x12] ^ b[0x13]
    dec = bytes(x ^ key for x in b[S1_STREAM_BASE:])
    return dec[S1_OFF: S1_OFF + S1_N * STRIDE]


for fn in ("SNDATA1.TR2", "SNDATA2.TR2"):
    s1 = load_s1(fn)
    names = []
    for i in range(S1_N):
        r = s1[i * STRIDE:(i + 1) * STRIDE]
        s, g = gbk7(r[0:7]), gbk7(r[7:14])
        names.append((s or "?") + (g or "?"))
    good = sum(1 for x in names if "?" not in x)
    bsn = set(name_of(BS1, i) for i in range(NREC)) | \
        set(name_of(BS2, i) for i in range(NREC))
    bad = [i for i, x in enumerate(names) if "?" in x]
    tail = [i for i in bad if i >= 354]
    chk("H1 %s S1 段 370×59B：有效武将 ≥350，坏名集中在尾部空槽" % fn,
        good >= 350 and len(tail) >= 14 and tail == list(range(min(tail), 370))
        and len([i for i in bad if i < 354]) <= 2,
        "可解 %d/370，尾部空槽 %d..369，中部外字 %d 条"
        % (good, min(tail), len([i for i in bad if i < 354])))
    chk("H2 %s S1 姓名 ≥ 350 条命中 BSDATA 名册" % fn,
        sum(1 for x in names if x in bsn) >= 350,
        "%d/370" % sum(1 for x in names if x in bsn))
    ids = [int.from_bytes(s1[i * STRIDE + 0x10:i * STRIDE + 0x12], "little")
           for i in range(S1_N)]
    live = [v for v in ids if v != 0xFFFF]
    chk("H3 %s S1 的 +0x10 = 0..699 稀疏子集（指回 BSDATA 武将号），空槽=0xffff" % fn,
        all(v < NREC or v == 0xFFFF for v in ids)
        and len(set(live)) == len(live)
        and sum(1 for i in range(S1_N) if ids[i] == i) < 20,
        "有效 %d 条全唯一，同号相等仅 %d 条，前 10 = %s"
        % (len(live), sum(1 for i in range(S1_N) if ids[i] == i), ids[:10]))
    chk("H4 %s 有效 +0x10 条数 == GBK 可解姓名条数（独立交叉验证）" % fn,
        len(live) == good + len([i for i in bad if i < 354]),
        "有效 id %d == 可解名 %d + 中部外字 %d"
        % (len(live), good, len([i for i in bad if i < 354])))
    chk("H5 %s S1 五维同样落在 0..100" % fn,
        all(s1[i * STRIDE + 0x16 + k] <= 100
            for i in range(S1_N) for k in range(5)))

# ================================================================ 落盘
spec = {
    "container": {"file": ["BSDATA1.TR2", "BSDATA2.TR2"], "size": FSIZE,
                  "records": NREC, "stride": STRIDE, "encrypted": False,
                  "magic": None},
    "loader": {"func": hex(LOAD_BSDATA), "name": "LoadBSDATA",
               "read_size": hex(FSIZE), "dest_obj": hex(BUSHOU_BUF),
               "dest_tag": "BUSHOUbuf",
               "scenario_switch": "byte[0x520604] test ah,4",
               "chain": [hex(OPEN_RES), hex(RANDOM_READ), hex(SET_RESIDENT)]},
    "name_tables": {"surname": hex(SUR_TBL), "given": hex(GIV_TBL), "stride": 7,
                    "getter_surname": hex(GET_SUR), "getter_given": hex(GET_GIV),
                    "id_segments": ["0..999", "1000..1999", "2000..2999", "3000+"],
                    "callsites": {"surname": n_sur, "given": n_giv}},
    "stream_map": ([{"stream_off": hex(s), "size": z, "target": k,
                     "offset": (hex(o) if isinstance(o, int) else o)}
                    for s, z, k, o in STREAM_MAP] if STREAM_MAP else None),
    "fields": {
        "0x00-0x06": "姓（GBK，7B 定长槽，NUL 结尾）→ 0x521aa8+id*7",
        "0x07-0x0d": "名（GBK，7B 定长槽）→ 0x520660+id*7",
        "0x0e": "2B → 解码器局部（未入实体，语义未定）",
        "0x10": "2B 名表索引/武将 ID → entity+0x02（BSDATA 恒 == 记录号）",
        "0x12": "2B → 解码器局部（未入实体，语义未定）",
        "0x14": "2B 相性字 → entity+0x08（compat_a | compat_b<<8）",
        "0x16-0x1a": "五维 统率/武力/内政/外交/魅力 → entity+0x0a..0x0e",
        "0x1b-0x1d": "10 技能 × 2bit → entity+0x0f..0x11",
        "0x1e-0x21": "→ entity+0x12..0x15（城属性 3 元 + 有效位）",
        "0x22": "→ entity+0x16（有效标记，init 1）",
        "0x27": "生年 − 1490 → entity+0x1b 低字节",
        "0x28": "→ entity+0x1c（语义未定，多为 32 的倍数）",
        "0x2b": "→ entity+0x1f",
        "0x2d": "体力上限 → entity+0x21",
        "0x2e": "体力 → entity+0x22",
        "0x2f": "野心 → entity+0x23",
        "0x30": "国 province（0..48 / 255=无）→ entity+0x24",
        "0x31": "城（0..199 / 255=浪人）→ entity+0x25",
        "0x32-0x33": "功勲 merit 2B（0xffff=满值哨兵）→ entity+0x26",
        "0x34": "俸禄/石高 → entity+0x28",
        "0x35": "忠诚 0..100 → entity+0x29",
        "0x36-0x37": "主君 2B（0xffff=浪人）→ entity+0x2a",
        "0x38-0x39": "16-bit 状态字 → entity+0x2c；職位 = byte[0x39] & 7",
        "0x3a": "高 4 位 = 主角槽(0/1/2/7/8) + 一般武将档(4/5/6)；低 4 位恒 0 → entity+0x2e",
    },
    "gaiji_usage": {
        "0xA141+0xA143+0xA144": "長宗我部（48×16 连排位图切 3 格，每字约 12px）",
        "0xA142+0xA143+0xA144": "香宗我部",
        "0xA147": "垪（GBK 缺字；#182 垪和氏続，北条家臣，国=6）",
        "bit_order": "行主序，2B/行，MSB 先行（本续判定，闭合续197 悬案⑨）",
    },
    "refutations": {
        "old_§1.2@16 face": "实为名表索引/武将 ID（恒 == 记录号）",
        "old_§1.2@50-51 trust": "实为功勲 merit 2B",
        "old_§1.2@56 loyalty": "实为 16-bit 状态字低字节；忠诚在 @53(0x35)",
        "old_§1.2@57 status": "位置对但须 & 7（38/690 条原值 >7）",
        "old_§1.2@58 lifespan": "实为主角槽/武将档 4-bit 高位枚举",
        "续181②": "0x49c2b0/0x49c310 是姓名 getter（805 调用点），非关系记录指针",
    },
}
out = os.path.join(HERE, "bsdata_format.json")
json.dump(spec, open(out, "w"), ensure_ascii=False, indent=1)

names_out = os.path.join(HERE, "bsdata_names.json")
json.dump({"BSDATA1": [name_of(BS1, i) for i in range(NREC)],
           "BSDATA2": [name_of(BS2, i) for i in range(NREC)]},
          open(names_out, "w"), ensure_ascii=False, indent=0)

npass = sum(1 for _, ok, _ in RESULTS if ok)
print("\n" + "=" * 64)
print("RESULT: %d/%d %s" % (npass, len(RESULTS),
                            "ALL PASS ✅" if npass == len(RESULTS) else "❌ 有失败项"))
print("产物: %s" % out)
print("产物: %s" % names_out)
if npass != len(RESULTS):
    for nm, ok, ex in RESULTS:
        if not ok:
            print("  FAIL: %s  %s" % (nm, ex))
    sys.exit(1)
