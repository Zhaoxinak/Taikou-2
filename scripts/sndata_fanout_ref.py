# -*- coding: utf-8 -*-
"""太閤立志伝2 —— SNDATA 49B 记录「扇出器 / 访问器 / 分派前提」参考实现（续159）

结论（2026-08-31 续159）：
1. `0x4ebfc0` = **strlen**，`0x4ebfe0` = **strcpy**（逐指令验证）
   → 推翻续158「`0x4ebfe0` = 块拷贝助手」；续158「仍未知② size 参数来源」
     **前提不成立**（strcpy 无 size 参数，null 结尾）。
2. `0x47d890` = `read_record(ctx, idx, dst)`：
   `lseek(h, 16 + idx*49, SEEK_SET)` + `read(dst, 0x31)`。
   **stride=49 / 文件头=16B / 记录长=49B** 三数由
   `lea edx,[ecx+eax+0x10]`（ecx=idx*48, eax=idx）与 `push 0x31` 直接坐实。
   ⇒ 数据源 = SNDATA 文件**按索引直接 seek+read**（非内存表）。
3. `0x47fc60` = 取记录 + **三重叠字符串视图**扇出：
   `*arg2 = word[rec+0]`(id_word)、`*arg3 = word[rec+2]`(sub_word)、`*arg4 = word[rec+4]`(flag|rel<<8)
   `strcpy(0x522c88, rec+6)`  / `strcpy(0x522c60, rec+0x13)` / `strcpy(0x522c70, rec+0x20)`
   ⇒ payload 内起点 0 / 13 / 26（相对 payload 起始）。局部帧 212B，故无越界。
4. 🔴 **P0 前提证伪：不存在 type→handler 函数指针表**
   全镜像连续代码指针扫描：>=128 项者**仅 1 张**（`@0x501004`，153 项 `jmp` thunk，
   **0/153 触及记录缓冲**）。`0x522c50..0x522d00` 字面引用仅 33 处 / 16 函数，
   且多为 `sbb/xor/adc eax, 0x522c52` 算术立即数**假阳性**。
5. 数据侧：SNDATA 833×49B payload **本质是二进制，非文本**
   （仅 14/833 条含 >=20 个 null；主要类型「三段含 null」比例 0%）。
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

import json
import os
import struct

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()

CODE_LO, CODE_HI = 0x401000, 0x4F0000

REC_STRIDE = 49
FILE_HDR = 0x10
REC_SIZE = 0x31
BUF_A, BUF_B, BUF_C = 0x522C88, 0x522C60, 0x522C70
PAYLOAD_OFFS = (6, 0x13, 0x20)          # 记录内偏移
PAYLOAD_REL = (0, 13, 26)               # 相对 payload 起点


def disas(va, n=80):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    return list(md.disasm(MEM[va - BASE: va - BASE + n * 8], va))[:n]


def txts(va, n=80):
    return [f'{i.mnemonic} {i.op_str}'.strip() for i in disas(va, n)]


def has(va, needle, n=80):
    return any(needle in t for t in txts(va, n))


# ---------------------------------------------------------------- 参考实现
def strlen_(b: bytes) -> int:
    """0x4ebfc0 —— 空指针返回 0，否则扫到首个 null。"""
    if not b:
        return 0
    i = b.find(0)
    return len(b) if i < 0 else i


def strcpy_from(buf: bytes, off: int, limit: int = None) -> bytes:
    """0x4ebfe0 —— 从 buf[off] 拷到首个 null（含），越界即到 buf 末尾。

    `limit` 模拟调用点零填充帧：超出记录长度后仍读到 0。
    """
    if off >= len(buf):
        return b''
    end = len(buf) if limit is None else min(len(buf), limit)
    i = buf.find(0, off, end)
    return buf[off: end] if i < 0 else buf[off: i]


def fan_out(record: bytes, frame_size: int = 212):
    """0x47fc60 —— 49B 记录 → 3 个头字 + 3 个重叠字符串视图。"""
    assert len(record) == REC_STRIDE, f'记录必须 {REC_STRIDE}B'
    frame = bytearray(frame_size)          # 局部帧零填充（0x47d720 初始化）
    frame[:REC_STRIDE] = record
    id_word = struct.unpack_from('<H', record, 0)[0]
    sub_word = struct.unpack_from('<H', record, 2)[0]
    flag_rel = struct.unpack_from('<H', record, 4)[0]
    views = tuple(strcpy_from(bytes(frame), o) for o in PAYLOAD_OFFS)
    return {
        'id_word': id_word,
        'type': id_word & 0xFF,
        'instance': (id_word >> 8) & 0xFF,
        'sub_word': sub_word,
        'flag': flag_rel & 0xFF,
        'rel_word': (flag_rel >> 8) & 0xFF,
        'view_a': views[0],   # payload+0
        'view_b': views[1],   # payload+13
        'view_c': views[2],   # payload+26
    }


def record_file_offset(idx: int) -> int:
    """0x47d890 的 seek 目标。"""
    return FILE_HDR + idx * REC_STRIDE


# ---------------------------------------------------------------- 自校验
def _run_tests():
    ok = []

    def chk(name, cond, extra=''):
        ok.append(bool(cond))
        print(f'  [{"OK" if cond else "FAIL"}] {name}{(" — " + extra) if extra else ""}')

    print('--- T1 0x4ebfc0 = strlen ---')
    t = txts(0x4EBFC0, 16)
    chk('空指针防护', 'test ecx, ecx' in t and 'xor ax, ax' in t)
    chk('逐字节扫 null', any('mov dl, byte ptr [ecx]' in x for x in t)
        and any('test dl, dl' in x for x in t))
    chk('计数 inc eax', any('inc eax' in x for x in t))
    chk('行为一致', strlen_(b'') == 0 and strlen_(b'ab\x00cd') == 2
        and strlen_(b'abcdef') == 6)

    print('--- T2 0x4ebfe0 = strcpy（推翻续158「块拷贝助手」）---')
    t = txts(0x4EBFE0, 18)
    chk('取 src 到 esi', 'mov esi, dword ptr [esp + 0xc]' in t)
    chk('返回 dst', 'mov eax, edx' in t)
    chk('循环写字节', any('mov byte ptr [edx], cl' in x for x in t))
    chk('末尾补 null', 'mov byte ptr [edx], 0' in t)
    chk('仅 2 参数(无 size)', 'ret' in t and not any('push 0x' in x for x in t[:3]))
    chk('行为一致', strcpy_from(b'AB\x00CD', 0) == b'AB'
        and strcpy_from(b'xy\x00', 0) == b'xy')

    print('--- T3 0x47d890 = read_record(stride=49, hdr=0x10, size=0x31) ---')
    t = txts(0x47D890, 14)
    chk('lea ecx,[eax+eax*2] (=idx*3)', 'lea ecx, [eax + eax * 2]' in t
        or 'lea ecx, [eax + eax*2]' in t)
    chk('shl ecx, 4 (=idx*48)', 'shl ecx, 4' in t)
    chk('lea edx,[ecx+eax+0x10] (=idx*49+16)',
        any('lea edx, [ecx + eax + 0x10]' in x for x in t))
    chk('push 0x31 (=记录长 49)', 'push 0x31' in t)
    chk('经函数指针 seek', any('call dword ptr [0x4fb0a8]' in x for x in t))
    chk('偏移公式', record_file_offset(0) == 16
        and record_file_offset(1) == 65
        and record_file_offset(832) == 16 + 832 * 49)

    print('--- T4 0x47fc60 = 3 头字 + 3 strcpy 重叠视图 ---')
    t = txts(0x47FC60, 40)
    chk('帧 212B', 'sub esp, 0xd4' in t)
    chk('头字 -> arg2/3/4', 'mov ax, word ptr [esp]' in t
        and 'mov dx, word ptr [esp + 2]' in t
        and 'mov cx, word ptr [esp + 4]' in t)
    chk('strcpy 起点 rec+6', 'lea edx, [esp + 6]' in t and 'push 0x522c88' in t)
    chk('strcpy 起点 rec+0x13', 'lea eax, [esp + 0x13]' in t and 'push 0x522c60' in t)
    chk('strcpy 起点 rec+0x20', 'lea ecx, [esp + 0x20]' in t and 'push 0x522c70' in t)
    chk('调 strcpy 三次', sum(1 for x in t if 'call 0x4ebfe0' in x) == 3)
    chk('起点相对 payload', [o - 6 for o in PAYLOAD_OFFS] == list(PAYLOAD_REL))

    print('--- T5 fan_out 行为 ---')
    rec = struct.pack('<HHH', 0xB84B, 0x0101, 0x0001) + b'NAME\x00' + b'\x00' * 38
    assert len(rec) == REC_STRIDE
    r = fan_out(rec)
    chk('type = id_word & 0xff', r['type'] == 0x4B, f'{r["type"]:#04x}')
    chk('instance = high byte', r['instance'] == 0xB8)
    chk('sub_word', r['sub_word'] == 0x0101)
    chk('view_a = payload+0 到 null', r['view_a'] == b'NAME')
    chk('view_b = payload+13 起(此处全 0)', r['view_b'] == b'')
    # 无 null 的二进制 payload：三视图 = payload 的**重叠后缀**，靠零填充帧收尾（不越界）
    r2 = fan_out(struct.pack('<HHH', 0, 0, 0) + b'\xff' * 43)
    chk('无null时 view_a = payload[0:43]', r2['view_a'] == b'\xff' * 43,
        f'{len(r2["view_a"])}B')
    chk('无null时 view_b = payload[13:43] (30B)', len(r2['view_b']) == 30,
        f'{len(r2["view_b"])}B')
    chk('无null时 view_c = payload[26:43] (17B)', len(r2['view_c']) == 17,
        f'{len(r2["view_c"])}B')

    print('--- T6 🔴 P0 证伪：无 type→handler 函数指针表 ---')
    runs = _scan_fptr_tables(0x400000, 0x530000, 128)
    chk('全镜像 >=128 项连续代码指针表仅 1 张', len(runs) == 1,
        f'实得 {len(runs)} 张')
    if runs:
        addr, ents = runs[0]
        chk('该表位于 0x501004', addr == 0x501004, hex(addr))
        touch = sum(1 for v in ents if _touches_buf(v))
        chk('该表 0/153 触及记录缓冲', touch == 0, f'{touch}/{len(ents)}')

    print('--- T7 数据侧：payload 是二进制，非文本 ---')
    p = os.path.join(ROOT, 'scripts', 'sndata_records.json')
    if os.path.exists(p):
        d = json.load(open(p, encoding='utf-8'))
        recs = d['scenario1']['records']
        chk('记录数 833', len(recs) == 833, str(len(recs)))
        chk('payload 均 43B',
            all(len(bytes.fromhex(r['payload_hex'])) == 43 for r in recs))
        many_null = sum(1 for r in recs
                        if bytes.fromhex(r['payload_hex']).count(0) >= 20)
        chk('含 >=20 个 null 者 < 5%', many_null < len(recs) * 0.05,
            f'{many_null}/{len(recs)}')
        # 主要类型 三段含 null 比例应为 0
        from collections import defaultdict
        per = defaultdict(lambda: [0, 0])
        for r in recs:
            pl = bytes.fromhex(r['payload_hex'])
            ty = r['id_word'] & 0xFF
            per[ty][1] += 1
            if all(0 in s for s in (pl[0:13], pl[13:26], pl[26:43])):
                per[ty][0] += 1
        top = sorted(((v[1], ty, v[0]) for ty, v in per.items()), reverse=True)[:3]
        chk('最大类型 0x0c 无文本包结构',
            all(ty != 0x0C or a == 0 for _, ty, a in top),
            ' '.join(f'{ty:#04x}:{a}/{b}' for b, ty, a in top))
    else:
        print('  [SKIP] sndata_records.json 不存在')

    n = sum(ok)
    print(f'\nRESULT: {n}/{len(ok)} checks passed')
    return n == len(ok)


def _scan_fptr_tables(lo, hi, minlen):
    runs, cur, start = [], [], None
    for off in range(lo - BASE, hi - BASE - 3, 4):
        (v,) = struct.unpack_from('<I', MEM, off)
        if v and CODE_LO <= v < CODE_HI:
            if not cur:
                start = BASE + off
            cur.append(v)
        else:
            if len(cur) >= minlen:
                runs.append((start, cur))
            cur, start = [], None
    if len(cur) >= minlen:
        runs.append((start, cur))
    return sorted(runs, key=lambda r: -len(r[1]))


def _touches_buf(va):
    return any(f'{a:#x}' in i.op_str
               for i in disas(va, 12) for a in (BUF_A, BUF_B, BUF_C))


if __name__ == '__main__':
    import sys
    sys.exit(0 if _run_tests() else 1)
