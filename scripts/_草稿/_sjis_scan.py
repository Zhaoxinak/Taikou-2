# -*- coding: utf-8 -*-
"""Extract Shift-JIS (cp932) strings from a binary and filter for battle terms."""
import sys, re

def sjis_runs(b):
    """Yield (decoded_str, file_offset) for Shift-JIS runs len>=2."""
    out = []
    i = 0
    n = len(b)
    cur = bytearray()
    cur_start = -1
    def flush():
        nonlocal cur, cur_start
        if len(cur) >= 2:
            try:
                s = cur.decode("cp932")
                out.append((s, cur_start))
            except Exception:
                pass
        cur = bytearray()
        cur_start = -1
    while i < n:
        c = b[i]
        is_lead = (0x81 <= c <= 0x9F) or (0xE0 <= c <= 0xEF)
        if is_lead and i + 1 < n:
            t = b[i+1]
            if 0x40 <= t <= 0xFC and t != 0x7F:
                if cur_start < 0:
                    cur_start = i
                cur += bytes([c, t])
                i += 2
                continue
        # also include ASCII printable runs adjacent? keep only SJIS here
        flush()
        i += 1
    flush()
    return out

def main():
    path = sys.argv[1]
    b = open(path, "rb").read()
    runs = sjis_runs(b)
    # battle-term keyword set (unit types / formations / tactics)
    kws = ["足軽","騎馬","鉄砲","鉄炮","弓","水軍","洋槍","槍","歩兵","騎兵",
           "鶴翼","魚鱗","偃月","方円","方円","鋒矢","長蛇","車懸","藤蔓","北斗","蓮華","陣形","陣",
           "火計","伏兵","斎壇","斉壇","影武者","流言","募兵","十文字","釣瓶","威圧","混乱","突撃",
           "防柵","計略","戦法","兵法","攻城","野戦","合戦","一騎","隊","兵"]
    hits = []
    for s, off in runs:
        for k in kws:
            if k in s:
                hits.append((off, s))
                break
    print(f"file={path}  sjis_runs={len(runs)}  battle_term_hits={len(hits)}")
    seen = set()
    for off, s in hits:
        if s in seen:
            continue
        seen.add(s)
        if len(seen) > 200:
            break
        print(f"  {off:#08x}  {s}")

if __name__ == "__main__":
    main()
