# -*- coding: utf-8 -*-
r"""
_fix_win_paths.py -- 把全工程 .py 里的 Windows 硬编码路径 / cwd 相关相对路径
统一改写为「基于 __file__ 向上找工程根」的可移植形式（tokenize 精确改写，不碰非字符串）。

背景：本工程长期在 F:/Games/Taikou 2 下开发，150+ 个脚本硬编码了该路径，
      另有部分脚本写死了大小写错误的 /Users/ts/Workbuddy/... （本卷大小写敏感），
      导致在 macOS 上几乎全部 FileNotFoundError（续195 工程卫生项）。

做法（对每个 .py，用 tokenize 只改 STRING token，按偏移倒序应用，保证不破坏其它代码）：
  1. 在「shebang + coding 声明 + 模块 docstring + from __future__」之后注入 _ROOT 定义块；
  2. 字符串字面量替换：
       F:/Games/Taikou 2            -> _ROOT
       F:/Games/Taikou 2/xxx        -> _ROOT + '/xxx'
       F:\Games\Taikou 2\xxx        -> _ROOT + '/xxx'
       /Users/.../Taikou 2/xxx      -> _ROOT + '/xxx'
       scripts/xxx                  -> _ROOT + '/scripts/xxx'
       _unpacked_mem.bin            -> _ROOT + '/scripts/_unpacked_mem.bin'
       Taikou2 Original/xxx         -> _ROOT + '/Taikou 2 Original/xxx'
  3. 幂等：已含 _find_root( 的文件跳过。
"""
import io
import os
import re
import sys
import tokenize

HERE = os.path.dirname(os.path.abspath(__file__))

INJECT = (
    "\n# <auto: portable root (injected by _fix_win_paths.py)>\n"
    "import os as _os\n"
    "def _find_root(_p):\n"
    "    for _ in range(8):\n"
    "        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):\n"
    "            return _p\n"
    "        _p = _os.path.dirname(_p)\n"
    "    return _p\n"
    "_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))\n"
    "# </auto: portable root>\n"
)

WIN = r"(?:F:/Games/Taikou 2|F:\\Games\\Taikou 2|F:\\\\Games\\\\Taikou 2)"
PATTERNS = [
    (re.compile(r"^" + WIN + r"$"), "_ROOT"),
    (re.compile(r"^" + WIN + r"/(?P<rest>.*)$"),
     lambda m: "_ROOT + '/%s'" % m.group("rest")),
    (re.compile(r"^" + WIN + r"[\\/]{1,2}(?P<rest>.*)$"),
     lambda m: "_ROOT + '/%s'" % m.group("rest").replace("\\\\", "/").replace("\\", "/")),
    (re.compile(r"^/Users/[^'\"]*?/(?:Taikou 2|main-[^/]+)/(?P<rest>.*)$"),
     lambda m: "_ROOT + '/%s'" % m.group("rest")),
    (re.compile(r"^scripts/(?P<rest>.*)$"),
     lambda m: "_ROOT + '/scripts/%s'" % m.group("rest")),
    (re.compile(r"^_unpacked_mem\.bin$"),
     "_ROOT + '/scripts/_unpacked_mem.bin'"),
    (re.compile(r"^Taikou2 Original/(?P<rest>.*)$"),
     lambda m: "_ROOT + '/Taikou2 Original/%s'" % m.group("rest")),
]


def _split_literal(text):
    """把 tokenize 给出的原始字面量切成 (prefix, quote, inner)。失败返回 None。"""
    m = re.match(r"^([rRbBuUfF]{0,3})('''|\"\"\"|'|\")", text)
    if not m:
        return None
    prefix, quote = m.group(1), m.group(2)
    inner = text[len(prefix) + len(quote):]
    if inner.endswith(quote):
        inner = inner[: -len(quote)]
    else:
        return None
    return prefix, quote, inner


def _rewrite_string(tok_text):
    """返回替换后的源码文本；不需改则返回 None。"""
    parts = _split_literal(tok_text)
    if parts is None:
        return None
    prefix, quote, inner = parts
    if "f" in prefix.lower():          # f-string 跳过，避免引号冲突
        return None
    if "'" in inner:                   # 内含单引号，跳过（替换要用单引号）
        return None
    for pat, rep in PATTERNS:
        m = pat.match(inner)
        if m:
            new = rep if isinstance(rep, str) else rep(m)
            return new
    return None


def _offset_of(src_text, rc):
    """按 tokenize 的 (row,col) 求「字符」偏移。

    ⚠️ 必须用解码后的 str 计算：tokenize 的 col 是字符列号，不是 UTF-8 字节号。
       早期版本用 bytes 计算偏移，导致所有含中文的文件替换错位、语法崩坏（已修）。
    """
    row, col = rc
    lines = src_text.split("\n")
    off = 0
    for idx in range(row - 1):
        off += len(lines[idx]) + 1
    return off + col


def _insert_offset(src_text):
    """计算 _ROOT 注入点（字符偏移）：shebang+coding+docstring+__future__ 之后。"""
    lines = src_text.split("\n")
    off = 0
    i = 0
    if lines and lines[0].startswith("#!"):
        off += len(lines[0]) + 1
        i = 1
    if i < len(lines) and lines[i].lstrip().startswith("#") and "coding" in lines[i]:
        off += len(lines[i]) + 1
        i += 1
    base = off

    try:
        toks = list(tokenize.tokenize(io.BytesIO(src_text.encode("utf-8")).readline))
    except Exception:
        return base
    n = len(toks)
    k = 0
    skip = (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING, tokenize.NEWLINE, tokenize.INDENT)
    while k < n and toks[k].type in skip:
        k += 1
    if k < n and toks[k].type == tokenize.STRING:
        base = max(base, _offset_of(src_text, toks[k].end))
        k += 1
    while k < n:
        while k < n and toks[k].type in skip:
            k += 1
        if k >= n:
            break
        t = toks[k]
        if t.type == tokenize.NAME and t.string == "from":
            j = k + 1
            while j < n and toks[j].type in (tokenize.COMMENT, tokenize.NL):
                j += 1
            if j < n and toks[j].type == tokenize.NAME and toks[j].string == "__future__":
                while j < n and toks[j].type != tokenize.NEWLINE:
                    j += 1
                if j < n:
                    base = max(base, _offset_of(src_text, toks[j].end))
                    k = j + 1
                    continue
        break
    return base


def fix_file(path):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        src = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if "_find_root(" in src:
        return False  # 幂等
    try:
        toks = list(tokenize.tokenize(io.BytesIO(raw).readline))
    except Exception:
        return False

    edits = []  # (start_off, end_off, new_text)
    for i, t in enumerate(toks):
        if t.type != tokenize.STRING:
            continue
        new = _rewrite_string(t.string)
        if new is None:
            continue
        # ⚠️ 隐式字符串拼接（"a" "b"）不能只改其中一段，否则语法崩 —— 整组跳过
        #    （前向 + 后向都要查：只查前向会漏掉「多段拼接的最后一段」）
        j = i + 1
        while j < len(toks) and toks[j].type in (tokenize.NL, tokenize.COMMENT):
            j += 1
        if j < len(toks) and toks[j].type == tokenize.STRING:
            continue
        j = i - 1
        while j >= 0 and toks[j].type in (tokenize.NL, tokenize.COMMENT):
            j -= 1
        if j >= 0 and toks[j].type == tokenize.STRING:
            continue
        edits.append((_offset_of(src, t.start), _offset_of(src, t.end), new))
    if not edits:
        return False

    out = src
    for s, e, new in sorted(edits, reverse=True):
        out = out[:s] + new + out[e:]
    ins = _insert_offset(out)
    out = out[:ins] + INJECT + out[ins:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    return len(edits)


def main():
    only = set(sys.argv[1:]) or None
    total = patched = edits = 0
    for dirpath, _dirnames, filenames in os.walk(HERE):
        for fn in sorted(filenames):
            if not fn.endswith(".py") or fn == os.path.basename(__file__):
                continue
            if only and fn not in only:
                continue
            p = os.path.join(dirpath, fn)
            total += 1
            try:
                n = fix_file(p)
            except Exception as exc:  # noqa
                print("SKIP", os.path.relpath(p, HERE), exc)
                continue
            if n:
                patched += 1
                edits += n
    print(f"_fix_win_paths: patched {patched}/{total} files, {edits} string literals rewritten")


if __name__ == "__main__":
    main()
