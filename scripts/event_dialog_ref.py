"""
event_dialog_ref.py — 事件系统 §3.7 子项：武将闲谈对话生成器 `0x4547f0` + MSGX 全局 id 规则

来源：2026-08-29 续72 逆向（脱壳镜像 _unpacked_mem.bin，基址 0x400000）

🔴 对既有文档的纠偏（勿被旧记误导）：
  - §3.7.5 原记 `0x4547f0` 为「个人遭遇事件处理器」，所列消息码含 `0x403/0x405`。
    实测：`0x4547f0` 内 push 的消息码为 **0x505/0x509/0x512/0x514/0x516/0x518/0x51a/0x51c**，
    **不含 0x403/0x405**；文本内容全是「闲谈/情报对话」（米价、城况、卖物、主公评价），
     ⇒ 实为**武将闲谈对话生成器**，非「遭遇事件处理器」。
  - MSGX 全局 id 是 **4 文件 × 2000 槽**（不是按实际条数累加）：
    MESSAGE1=0..1999 / MESSAGE2=2000..3999 / MESSAGE3=4000..5999 / MESSAGE4=6000..7999。
    证据：`scripts/_probe/msgx/all_messages4.txt` 中 MESSAGE4#0 标注 `(id=0x1770)` = 6000。

🚫 结论性负结果：`0x50dab0`（27 类 × 4B）的 4 字节语义**静态不可破**——
   全镜像仅 1 处 xref（`0x4eb38f: push 0x50dab0; call 0x47ad90`），整块传给通用 UI 列表函数
   `0x4f1d37`，该函数只做渲染/布局，无任何代码按字段读取 ⇒ 无字段语义可提取。

运行：python scripts/event_dialog_ref.py
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

BASE = 0x400000

# ---- MSGX 全局 id 分配（2000 槽/文件）----
MSGX_SLOT = 2000
MSGX_FILES = ['MESSAGE1.LZW', 'MESSAGE2.LZW', 'MESSAGE3.LZW', 'MESSAGE4.LZW']
MSGX_BASE = {f: i * MSGX_SLOT for i, f in enumerate(MSGX_FILES)}
MSGX_TOTAL = 6211

# ---- 事件/场景类型学（27 类，名称指针表 0x50da38，有效索引 2..28）----
EVENT_TAXONOMY = {
    2: '寺院', 3: '历史事件', 4: '木下藤吉郎的主题', 5: '大商人',
    6: '新武将的主题', 7: '柴田胜家的主题', 8: '明智光秀的主题', 9: '普通的城镇',
    10: '京都', 11: '界镇', 12: '城内', 13: '自宅',
    14: '茶会', 15: '会议', 16: '酒馆', 17: '剑术道场',
    18: '教堂-旅店-医生', 19: '行军', 20: '战斗', 21: '个人战斗',
    22: '墨俣筑城', 23: '阿市的悲剧', 24: '金崎撤退战', 25: '本能寺大火',
    26: '游戏开始', 27: '开始', 28: '结局',
}
EVENT_TAXONOMY_TBL = 0x50DA40
EVENT_LIST_TBL = 0x50DAB0      # 27 × 4B（语义静态不可破，见文件头）
EVENT_TYPE_LOOKUP_FN = 0x4EAF70

# ---- 武将闲谈对话消息码（`0x4547f0` 实测 8 处 push）----
# 口吻对规律（⚠️ 适用范围有限，勿外推）：
#   仅在 **0x512..0x51d** 段成立 —— 偶数 id = 直率/粗鲁口吻，奇数 id = 谦让/文雅口吻，
#   两者是同一对话的两种说法（对应武将性格/口吻字段）。逐对已核对：
#     0x512/3 买我的 / 买在下的   0x514/5 投缘 / 死不足惜   0x516/7 合不来（两种措辞）
#     0x518/9 家臣与主公不合      0x51a/b 情同手足 / 特别投缘 0x51c/d 没有节操
#   ✗ 不适用于 0x505（米价）与 0x509（城况）：其 ±1 邻居 0x504「难得难得，喝吧」、
#     0x508「买军马…」是**不同话题**，不是口吻变体。
SMALLTALK_MSGS = {
    0x505: ('米价情报', '对对，这一带的米价就是这样。'),
    0x509: ('城况情报', '对了，最近去了%s家的%s城，是这种情况。'),
    0x512: ('兜售物品', '啊，有人买我的%s吗┅┅'),
    0x514: ('主公投缘', '我和我家主公最是投缘。'),
    0x516: ('与主公不合', '┅┅只是在这里说说，我和主公真是合不来。'),
    0x518: ('家臣与主公不合', '┅┅这话只能在这里说，我家的%s与我家主公好像合不来，性格相差太大。'),
    0x51A: ('主公与某家交好', '我家主公与%s情同手足，关系不一样。'),
    0x51C: ('贬评某人', '┅┅这话只能在这里说，%s没有节操，不能信任。'),
}
SMALLTALK_FN = 0x4547F0
SMALLTALK_PUSHES = [0x4548B7, 0x4548EF, 0x45491A, 0x45494B,
                    0x454985, 0x454A95, 0x454B1A, 0x454BFD]


def msgx_global_id(file_idx, local_idx):
    """(文件序号 0..3, 文件内序号) -> 全局 MSGX id"""
    if not (0 <= file_idx < len(MSGX_FILES)):
        return None
    return file_idx * MSGX_SLOT + local_idx


def load_texts(path=_ROOT + '/scripts/msgx_all_texts.json'):
    if not os.path.exists(path):
        return {}
    d = json.load(open(path, encoding='utf-8'))
    return {int(k): v for k, v in d.get('texts', {}).items()}


def tone_variant(msg_id):
    """返回同一对话的另一口吻变体 id：偶数<->奇数互换。"""
    return msg_id + 1 if msg_id % 2 == 0 else msg_id - 1


# ============================ 静态自校验 ============================

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

    here = os.path.dirname(os.path.abspath(__file__))
    texts = load_texts(os.path.join(here, 'msgx_all_texts.json'))
    print(f"文本索引: {len(texts)} 条")

    chk("MSGX 文本总数 == 6211", len(texts) == MSGX_TOTAL, f"n={len(texts)}")
    chk("2000 槽规则: MESSAGE4 base == 6000", MSGX_BASE['MESSAGE4.LZW'] == 6000)
    chk("2000 槽规则: MESSAGE4#0 id == 0x1770", msgx_global_id(3, 0) == 0x1770)
    chk("全局 id 换算 (f=1,#0) == 2000", msgx_global_id(1, 0) == 2000)
    chk("越界文件号返回 None", msgx_global_id(9, 0) is None)

    # 闲谈消息码：全部有文本，且与硬编码一致
    miss = [hex(m) for m in SMALLTALK_MSGS if m not in texts]
    chk("8 个闲谈消息码全部有文本", not miss, f"缺={miss}")
    for mid, (tag, expect) in SMALLTALK_MSGS.items():
        got = texts.get(mid, '')
        chk(f"  0x{mid:03x} {tag} 文本匹配", got == expect, f"{got[:26]}")

    # 口吻对规律：偶数 id 与 +1 都存在
    pairs_ok = all((m + 1 if m % 2 == 0 else m) in texts for m in SMALLTALK_MSGS)
    chk("口吻对规律: 偶/奇变体均在索引内", pairs_ok)
    chk("tone_variant(0x514) == 0x515", tone_variant(0x514) == 0x515)
    chk("tone_variant(0x515) == 0x514", tone_variant(0x515) == 0x514)

    # 类型学
    chk("事件类型学 27 类", len(EVENT_TAXONOMY) == 27, f"n={len(EVENT_TAXONOMY)}")
    chk("类型学索引连续 2..28",
        sorted(EVENT_TAXONOMY) == list(range(2, 29)))

    # 负结果：0x50dab0 仅 1 处 xref
    img = os.path.join(here, _ROOT + '/scripts/_unpacked_mem.bin')
    if os.path.exists(img):
        mem = open(img, 'rb').read()
        pat = struct.pack('<I', EVENT_LIST_TBL)
        n = 0
        i = 0
        while True:
            j = mem.find(pat, i)
            if j < 0:
                break
            n += 1
            i = j + 1
        chk("🚫 负结果: 0x50dab0 仅 1 处 xref", n == 1, f"n={n}")
        off = EVENT_LIST_TBL - BASE
        region = mem[off:off + 108]
        chk("🚫 负结果: 27×4B 区非零（有数据但无人读字段）",
            sum(region) > 0, f"nonzero={sum(1 for b in region if b)}")
    else:
        print("  [SKIP] 无映像，跳过 xref 校验")

    print(f"\n自校验结果: {ok} OK, {fail} FAIL")
    return fail == 0


if __name__ == '__main__':
    print("=" * 70)
    print("事件系统 §3.7 子项 —— 武将闲谈对话 `0x4547f0` + MSGX id 规则")
    print("=" * 70)
    print("\n武将闲谈消息码（0x4547f0 实测 8 处 push）:")
    t = load_texts(_ROOT + '/scripts/msgx_all_texts.json')
    for mid, (tag, _) in sorted(SMALLTALK_MSGS.items()):
        alt = tone_variant(mid)
        print(f"  0x{mid:03x} [{tag}]  {t.get(mid,'')}")
        print(f"        变体 0x{alt:03x}: {t.get(alt,'')}")
    print()
    raise SystemExit(0 if self_check() else 1)
