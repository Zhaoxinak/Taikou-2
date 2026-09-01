# -*- coding: utf-8 -*-
"""一次性补丁：把参考实现里脆弱的 open('scripts/X') 改为基于 __file__ 的绝对路径。
仅做字符串替换，不改逻辑。项目有 git，可随时回退。"""
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

import os, re, glob

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# 匹配 open('scripts/X') 或 open("scripts/X")，含可能的换行/空格
PAT = re.compile(r"open\(\s*['\"]scripts/([^'\"]+)['\"]")

HEADER = "import os\n_HERE = os.path.dirname(os.path.abspath(__file__))\n"

def fix_file(path):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if _ROOT + '/scripts/' not in src:
        return False
    new = PAT.sub(r"open(os.path.join(_HERE, r'\1')", src)
    if new == src:
        return False
    # 确保 _HERE 已定义
    if "_HERE = os.path.dirname" not in new:
        # 在首个 import 之后插入（或文件头）
        if new.lstrip().startswith("import ") or new.lstrip().startswith("from "):
            # 在第一个 import 块之后插入
            lines = new.splitlines(keepends=True)
            i = 0
            while i < len(lines) and (lines[i].lstrip().startswith(("import ", "from "))):
                i += 1
            lines.insert(i, HEADER)
            new = "".join(lines)
        else:
            new = HEADER + new
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return True

changed = []
for p in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*_ref.py"))):
    if os.path.basename(p) == "_fix_paths.py":
        continue
    if fix_file(p):
        changed.append(os.path.basename(p))

print("patched %d files:" % len(changed))
for c in changed:
    print("  ", c)
