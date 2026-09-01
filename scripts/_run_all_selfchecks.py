# -*- coding: utf-8 -*-
"""批量跑全部 *_ref.py 自检, 汇总 PASS/FAIL。"""
import os, glob, subprocess, sys, re

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
refs = sorted(glob.glob(os.path.join(BASE, "*_ref.py")))
PY = sys.executable

# 只认真正的失败信号: 非零退出码, 异常回溯, 或 "N FAIL" 中 N>0
FAILWORDS = ("Traceback", "AssertionError", "MISMATCH", "[NG]")

def real_fail_count(out: str) -> int:
    """从输出里抽 'x FAIL' / 'FAIL=x' 的数字之和 (0 表示无失败)。

    必须先消解 'FAIL=N' 再匹配 'N FAIL' —— 否则 'PASS=29  FAIL=0'
    会被 '(\\d+)\\s*FAIL' 抢先匹配成 29 个失败(实测踩过)。
    """
    n = 0
    def _take(m):
        nonlocal n
        n += int(m.group(1))
        return " "
    rest = re.sub(r"FAIL(?:ED)?\s*[=:]\s*(\d+)", _take, out, flags=re.I)
    for m in re.finditer(r"(\d+)\s*FAIL(?:ED)?\b", rest, re.I):
        n += int(m.group(1))
    return n

ok_list, bad_list = [], []
print(f"跑 {len(refs)} 个参考实现自检 ...\n")
for r in refs:
    name = os.path.basename(r)
    # ⚠️ 工程现状: ref 脚本的相对路径基准不统一 —— 多数用
    # 'scripts/_unpacked_mem.bin'(需 cwd=工程根), 少数用裸
    # '_unpacked_mem.bin'(需 cwd=scripts/)。故两种 cwd 依次重试。
    out, rc, used_cwd = "", None, None
    for cwd in (ROOT, BASE):
        try:
            p = subprocess.run([PY, r], cwd=cwd, capture_output=True,
                               timeout=180)
        except subprocess.TimeoutExpired:
            out, rc, used_cwd = "TIMEOUT", -9, cwd
            break
        out = (p.stdout or b"").decode("utf-8", "replace") + \
              (p.stderr or b"").decode("utf-8", "replace")
        rc, used_cwd = p.returncode, cwd
        if rc == 0 and "FileNotFoundError" not in out:
            break
    if rc == -9:
        bad_list.append((name, "TIMEOUT", ""))
        print(f"  [TIMEOUT] {name}")
        continue

    # 抽取结论行: 优先取带 PASS/通过/闭合 字样的行
    verdict = ""
    for line in reversed(out.strip().splitlines()):
        s = line.strip()
        if "PASS" in s.upper() or "通过" in s or "闭合" in s or "一致" in s:
            verdict = s[:70]
            break
    if not verdict:
        for line in reversed(out.strip().splitlines()):
            if line.strip():
                verdict = line.strip()[:70]
                break

    bad = (rc != 0) or any(w in out for w in FAILWORDS) or real_fail_count(out) > 0
    # 「x/y PASS」「x/y checks」「x/y 通过」形式中 x!=y 才算 fail。
    # 不可用裸 (\d+)/(\d+) 通用正则 —— 会把 '0x1202 / 0xda3' 之类
    # 十六进制地址误解析为 1202/0 而误判失败(实测踩过)。
    # ⚠️ \s* 会跨行 —— 实测把 "5/20\n  PASS" 误判成 5/20 失败
    #    （savedata_loadflow_ref.py 34/34 真通过却被误报 FAIL）。
    #    故分隔符一律用 [ \t]* 限定在同行内。
    for m in re.finditer(r"(\d+)[ \t]*/[ \t]*(\d+)[ \t]*(?:PASS|checks|通过|ALL)", out):
        if m.group(1) != m.group(2):
            bad = True
            break

    if bad:
        # 抓最后一行有用的错误信息
        errline = ""
        for line in reversed(out.strip().splitlines()):
            s = line.strip()
            if s and not s.startswith("  File "):
                errline = s[:90]
                break
        bad_list.append((name, f"rc={rc}", errline or verdict))
        print(f"  [FAIL] {name:<30} rc={rc}  {errline or verdict}")
    else:
        ok_list.append((name, verdict))
        print(f"  [ OK ] {name:<30} {verdict}")

print("\n" + "=" * 70)
print(f"结果: {len(ok_list)} PASS / {len(bad_list)} FAIL  (共 {len(refs)})")
if bad_list:
    print("\n失败项:")
    for n, rc, v in bad_list:
        print(f"  - {n}  {rc}  {v}")
