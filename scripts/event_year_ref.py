"""
event_year_ref.py — 事件系统 §3.7 子项：时间全局编码 + 按年触发 + 本能寺台词序列

来源：2026-08-29 续75 逆向

## ① 时间全局编码（✅ 新发现）
| 全局 | 语义 | 编码 |
|---|---|---|
| `byte[0x5205f0]` | **年** | **从 1560 起的偏移量**，非绝对年份（`add reg, 0x618` = +1560） |
| `byte[0x5205f1]` | 月 | 未最终定序（见下） |
| `byte[0x5205f2]` | 日 | 未最终定序（见下） |

- 证据：`0x403ec0: add esi, 0x618` / `0x404304: add eax, 0x618; cmp ax, 0x640`（1600）
  / `0x40c318: add eax, 0x618; cmp ax, 0x61e`（1566）
- 可表示范围：1560 .. 1560+255 = 1815。
- ⚠️ 月/日顺序：本能寺 handler 区 `0x41b8f0` 读序为 `[0x5205f0]`年 → `[0x5205f2]` → `[0x5205f1]`
  （edx←`[0x5205f2]`，eax←`[0x5205f1]`），怀疑 `+0x5f1`=月 / `+0x5f2`=日，但**未拿到常量比对实证**，
  本文件不做定序断言。

## ② 🚫 结论性发现：不存在集中的「历史事件年表」
- 史实事件**不是**由「年份 → 事件」表驱动，而是**分散的硬编码 cmp 判定**
  （与 §3.7.6 本能寺「按年触发硬编码 handler 模式」一致，本次推广到全镜像）。
- 全镜像 `0x5205f0` 共 **57 处** xref，其中构成年份阈值判定的仅 **9 处**（见 YEAR_CHECKS）。
- ⇒ §3.7.7 待破项「史实事件**按年触发**的总调度（年/月全局 + 事件表）」应改为：
  **无总调度表，逐个事件自行 cmp 判定**；欲穷举事件须逐个追 handler，非查一张表。

## ③ 🔴 纠偏：`0x447780` 不是按年调度器
- 初判「`push 0x62e`(1582) → `call 0x447780`」为按年触发，实为**误判**。
- `0x447780` 实际是**消息显示封装**：
  ```asm
  mov eax,[esp+0xc]; mov ecx,[esp+0x8]; mov edx,[esp+0x4]
  push eax; push ecx; push edx
  call 0x493500        ; ← MSGX 查找（§3.14 已知魔数 0x10624dd3）
  add esp,4; push eax
  mov eax,[0x52063c]; push eax
  call 0x47b8d0        ; 显示消息
  ```
- 实证：`push 0x62e` 的 1582 是**消息 ID**，msg#1582 = 「以这样的身体状况，不能用真刀比赛。等你体力完全恢复了再来吧。」（剑术道场），与年份无关。
- 同理 `push 0x627` 的 1575 = msg#1575「来剑术道场，有什么事啊？」。

## ④ 本能寺之变：完整触发链与台词（✅ 全闭合）
- 链：`0x41aa70`（本能寺主流程，2 处 caller `0x4135e2` / `0x4179bc`）
      → `0x41ab51` 起依次显示消息 `0x1ad6..0x1ad9` → `call 0x41c160`（过场动画）
      → 依 `word[0x520604] & 0x3000 == 0x1000` 分支 → `0x4088d0(0x517c70, 0xf)`
- 台词序列见 `HONNOJI_MSGS`（msg 6866..6879，实测均已取到文本）。

运行：python scripts/event_year_ref.py
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

# ---- 时间全局 ----
YEAR_GLOBAL = 0x5205F0      # byte, 年 = 值 + 1560
MON_OR_DAY_A = 0x5205F1
MON_OR_DAY_B = 0x5205F2
YEAR_BASE = 1560

# ---- 全镜像年份阈值判定点（9 处）----
# (代码地址, 判定值, 是否 +1560 后比较, 跳转)
YEAR_CHECKS = [
    (0x4042FC, 1600, True,  'jne', '==1600 年特判'),
    (0x40C310, 1566, True,  'jb',  '<1566 年'),
    (0x440C62,    3, False, 'jne', '年偏移==3 → 1563'),
    (0x4A5370, 1560, True,  'je',  '==1560 年（剧本起始年?）'),
    (0x4BB3E2,    3, False, 'jne', '年偏移==3 → 1563'),
    (0x4A4DA4,    0, False, 'jne', '年偏移==0 → 1560'),
    (0x49A5E0, 1490, False, 'jb',  'cmp 1490（疑非年份）'),
    (0x4A0D6F,   24, False, 'mov', 'cmp 24（疑非年份）'),
    (0x4E880F,    7, False, 'je',  'cmp 7（疑非年份）'),
]

# ---- 本能寺之变 消息序列（msg 6866..6879）----
HONNOJI_START = 0x1AD2
HONNOJI_END = 0x1ADF
HONNOJI_FLOW = 0x41AA70          # 主流程函数
HONNOJI_MSG_CALL = 0x41AB51      # 消息段起点
HONNOJI_CUTSCENE = 0x41C160      # 过场动画 handler
HONNOJI_BRANCH_MASK = 0x3000
HONNOJI_BRANCH_VAL = 0x1000      # word[0x520604] & 0x3000 == 0x1000


def load_texts(path=_ROOT + '/scripts/msgx_all_texts.json'):
    if not os.path.exists(path):
        return {}
    d = json.load(open(path, encoding='utf-8'))
    return {int(k): v for k, v in d.get('texts', {}).items()}


def year_from_byte(b):
    """byte[0x5205f0] -> 公历年份"""
    return b + YEAR_BASE


def byte_from_year(y):
    return y - YEAR_BASE


def honnoji_script(texts):
    return [(m, texts.get(m, '')) for m in range(HONNOJI_START, HONNOJI_END + 1)]


def self_check():
    ok = fail = 0

    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  [OK]   {name} {extra}")
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    t = load_texts()
    print(f"文本索引: {len(t)} 条")

    # 时间编码
    chk('年偏移 0 → 1560', year_from_byte(0) == 1560)
    chk('年偏移 40 → 1600', year_from_byte(40) == 1600)
    chk('1582 → 偏移 22', byte_from_year(1582) == 22)
    chk('1600 → 偏移 40', byte_from_year(1600) == 40)

    # 年份判定点
    chk('年份判定点 9 处', len(YEAR_CHECKS) == 9, f"n={len(YEAR_CHECKS)}")
    chk('含 1600 判定', any(v == 1600 for _, v, _, _, _ in YEAR_CHECKS))
    chk('含 1566 判定', any(v == 1566 for _, v, _, _, _ in YEAR_CHECKS))

    # 纠偏：0x62e / 0x627 是消息 ID
    chk('🔴 0x62e(1582) 是消息ID且有文本', 1582 in t and len(t[1582]) > 4,
        t.get(1582, '')[:26])
    chk('🔴 msg1582 内容为体力/真刀（非年份事件）',
        '真刀' in t.get(1582, ''))
    chk('🔴 0x627(1575) 是消息ID', 1575 in t, t.get(1575, '')[:26])

    # 本能寺
    scr = honnoji_script(t)
    missing = [m for m, s in scr if not s]
    chk('本能寺 14 条消息全部有文本', not missing, f"缺={[hex(x) for x in missing]}")
    chk('首条为「报告！刚刚捉到一个人」', scr[0][1].startswith('报告'), scr[0][1][:20])
    chk('含「蓝色桔梗旗帜，是明智光秀。」',
        any('蓝色桔梗旗帜' in s for _, s in scr))
    chk('末条为「我们直奔二条城吧！！」', '二条城' in scr[-1][1], scr[-1][1][:24])

    print(f"\n自校验结果: {ok} OK, {fail} FAIL")
    return fail == 0


if __name__ == '__main__':
    print("=" * 70)
    print("时间全局编码 + 按年触发 + 本能寺之变")
    print("=" * 70)
    t = load_texts()
    print("\n=== 本能寺之变 台词序列 ===")
    for m, s in honnoji_script(t):
        print(f"  0x{m:x} ({m}): {s}")
    print()
    raise SystemExit(0 if self_check() else 1)
