"""tree_layout.py — 家族树「数据模型 + 布局算法」独立验证

设计要点
--------
* 树用「父索引」表达: 节点 i 的父是 nodes[i][0](None=根)。根放在最上面(最远祖先)。
* 世代 gen 由父链推导; x 用后序遍历分配槽位(叶子依次排开, 父 = 首末子中点)。
* 行距分两种: 该代只有 1 人时用紧凑距(单链直系, 参考图里也是紧贴的),
  该代有多人时用标准距(要留出横向展开的空间)。
* 状态三态(对齐参考图): S_ALIVE 在世(实线圆) / S_DEAD 已故(实线+暗色) /
  S_UNBORN 未出生(虚线圆)。

本脚本只做**纯 Python 验证**并输出 ASCII 预览, 不触碰 exe。
"""
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# 状态常量
S_ALIVE, S_DEAD, S_UNBORN = 0, 1, 2
_ST = {S_ALIVE: '在世', S_DEAD: '已故', S_UNBORN: '未出生'}

# ---------- 几何常量 (物理像素, 客户区 1280x800) ----------
R_NODE   = 17        # 节点圆半径
ROW_HI   = 74        # 该代 >=2 人时的行距
ROW_LO   = 52        # 该代 1 人时的行距(单链紧凑)
COL_W    = 96        # 列距(槽位宽)
MARGIN_T = 56        # 顶部(标题栏)留白
NAME_DY  = 22        # 姓名相对圆心的 y 偏移
REL_DY   = 40        # 关系文字相对圆心的 y 偏移

# ======================================================================
# 柴田胜家 — 上5代 / 本代(三兄弟) / 下5代 模拟数据
#   (父索引, 姓, 名, 关系, 状态)
#   索引 0 是最远的祖先(天祖), 是树根。
# ======================================================================
SHIBATA_NODES = [
    # ---- 上 5 代直系 (单链) ----
    (None, '柴田', '胜长', '天祖',   S_DEAD),
    (0,    '柴田', '胜定', '高祖',   S_DEAD),
    (1,    '柴田', '胜秀', '曾祖',   S_DEAD),
    (2,    '柴田', '胜义', '祖父',   S_DEAD),
    (3,    '柴田', '胜重', '父',     S_DEAD),
    # ---- 本代: 胜重三子 ----
    (4,    '柴田', '胜忠', '兄',     S_ALIVE),
    (4,    '柴田', '胜家', '本人',   S_ALIVE),
    (4,    '柴田', '胜次', '弟',     S_ALIVE),
    # ---- 下 1 代 ----
    (6,    '柴田', '胜丰', '养子',   S_UNBORN),
    (6,    '柴田', '胜政', '长子',   S_UNBORN),
    (6,    '柴田', '胜敏', '次子',   S_UNBORN),
    (5,    '柴田', '胜元', '侄',     S_UNBORN),
    (7,    '柴田', '胜久', '侄',     S_UNBORN),
    # ---- 下 2 代 ----
    (8,    '柴田', '忠胜', '孙',     S_UNBORN),
    (9,    '柴田', '忠家', '孙',     S_UNBORN),
    (10,   '柴田', '忠光', '孙',     S_UNBORN),
    (11,   '柴田', '忠长', '侄孙',   S_UNBORN),
    (12,   '柴田', '忠次', '侄孙',   S_UNBORN),
    # ---- 下 3 代 ----
    (13,   '柴田', '胜成', '曾孙',   S_UNBORN),
    (14,   '柴田', '胜昌', '曾孙',   S_UNBORN),
    (16,   '柴田', '胜直', '曾侄孙', S_UNBORN),
    # ---- 下 4 代 ----
    (18,   '柴田', '胜时', '玄孙',   S_UNBORN),
    (19,   '柴田', '胜信', '玄孙',   S_UNBORN),
    # ---- 下 5 代 ----
    (21,   '柴田', '胜宗', '来孙',   S_UNBORN),
]

# ======================================================================
# 其余家族(简单: 父 + N 子), 沿用原补丁的史实数据
# ======================================================================
def _simple(sur, parent_name, members):
    """members: [(姓, 名, 关系, 状态)] 第 0 项是根(触发者本人)"""
    out = []
    for i, (s, gname, rel, st) in enumerate(members):
        out.append((None if i == 0 else 0, s, gname, rel, st))
    return out


OTHER_TREES = [
    ('织田', '信长', _simple('织田', '信长', [
        ('织田', '信长', '本人', S_ALIVE), ('织田', '信忠', '长子', S_UNBORN),
        ('织田', '信雄', '次子', S_UNBORN), ('织田', '信孝', '三子', S_UNBORN)])),
    ('毛利', '元就', _simple('毛利', '元就', [
        ('毛利', '元就', '本人', S_ALIVE), ('毛利', '隆元', '长子', S_ALIVE),
        ('吉川', '元春', '次子', S_ALIVE), ('小早川', '隆景', '三子', S_ALIVE),
        ('穗井田', '元清', '四子', S_UNBORN)])),
    ('北条', '氏康', _simple('北条', '氏康', [
        ('北条', '氏康', '本人', S_ALIVE), ('北条', '氏政', '长子', S_ALIVE),
        ('北条', '氏照', '次子', S_UNBORN), ('北条', '氏邦', '三子', S_UNBORN),
        ('北条', '氏规', '四子', S_UNBORN), ('北条', '氏尧', '五子', S_UNBORN)])),
    ('岛津', '贵久', _simple('岛津', '贵久', [
        ('岛津', '贵久', '本人', S_ALIVE), ('岛津', '义久', '长子', S_ALIVE),
        ('岛津', '义弘', '次子', S_ALIVE), ('岛津', '岁久', '三子', S_ALIVE),
        ('岛津', '家久', '四子', S_UNBORN)])),
    ('武田', '信玄', _simple('武田', '信玄', [
        ('武田', '信玄', '本人', S_ALIVE), ('武田', '义信', '长子', S_ALIVE),
        ('武田', '胜赖', '次子', S_UNBORN), ('仁科', '盛信', '三子', S_UNBORN)])),
    ('德川', '家康', _simple('德川', '家康', [
        ('德川', '家康', '本人', S_ALIVE), ('德川', '信康', '长子', S_UNBORN),
        ('德川', '秀康', '次子', S_UNBORN), ('德川', '秀忠', '三子', S_UNBORN)])),
    ('真田', '幸隆', _simple('真田', '幸隆', [
        ('真田', '幸隆', '本人', S_ALIVE), ('真田', '信纲', '长子', S_ALIVE),
        ('真田', '昌辉', '次子', S_ALIVE), ('真田', '昌幸', '三子', S_UNBORN)])),
    ('伊达', '晴宗', _simple('伊达', '晴宗', [
        ('伊达', '晴宗', '本人', S_ALIVE), ('伊达', '辉宗', '长子', S_ALIVE),
        ('留守', '政景', '次子', S_UNBORN), ('石川', '昭光', '三子', S_UNBORN)])),
    ('大友', '宗麟', _simple('大友', '宗麟', [
        ('大友', '宗麟', '本人', S_ALIVE), ('大友', '义统', '长子', S_UNBORN),
        ('大友', '亲家', '次子', S_UNBORN), ('大友', '亲盛', '三子', S_UNBORN)])),
    ('森', '可成', _simple('森', '可成', [
        ('森', '可成', '本人', S_ALIVE), ('森', '长可', '长子', S_UNBORN),
        ('森', '兰丸', '次子', S_UNBORN)])),
    ('最上', '义守', _simple('最上', '义守', [
        ('最上', '义守', '本人', S_ALIVE), ('最上', '义光', '长子', S_ALIVE),
        ('中野', '义时', '次子', S_UNBORN)])),
    ('吉川', '元春', _simple('吉川', '元春', [
        ('吉川', '元春', '本人', S_ALIVE), ('吉川', '元长', '长子', S_UNBORN),
        ('繁泽', '元氏', '次子', S_UNBORN), ('吉川', '广家', '三子', S_UNBORN)])),
]

TREES = [('柴田', '胜家', SHIBATA_NODES)] + OTHER_TREES


# ======================================================================
def layout(nodes):
    """-> (gen[], slot[], kids{}, y[])  slot 为列槽位(整数), y 为物理像素"""
    n = len(nodes)
    kids = defaultdict(list)
    roots = []
    for i, nd in enumerate(nodes):
        p = nd[0]
        if p is None:
            roots.append(i)
        else:
            kids[p].append(i)
    gen = [0] * n
    order = []

    def dfs(i, g):
        gen[i] = g
        order.append(i)
        for c in kids[i]:
            dfs(c, g + 1)
    for r in roots:
        dfs(r, 0)

    slot = [0] * n
    cur = [0]

    def place(i):
        if not kids[i]:
            slot[i] = cur[0]
            cur[0] += 1
        else:
            for c in kids[i]:
                place(c)
            slot[i] = (slot[kids[i][0]] + slot[kids[i][-1]]) / 2.0
    for r in roots:
        place(r)

    # 每代人数 -> 行距; y 累加
    maxg = max(gen)
    per_gen = [0] * (maxg + 1)
    for g in gen:
        per_gen[g] += 1
    y = [0] * n
    acc = MARGIN_T
    for g in range(maxg + 1):
        for i in range(n):
            if gen[i] == g:
                y[i] = acc
        acc += ROW_LO if per_gen[g] <= 1 else ROW_HI
    return gen, slot, kids, y, per_gen


def render_ascii(nodes, gen, slot, kids, y, per_gen, title):
    """打印 ASCII 预览(缩进表示层次)"""
    print('=' * 78)
    print('[%s]  %d 人 / %d 代' % (title, len(nodes), len(per_gen)))
    print('  每代人数: %s   行距: %s' % (per_gen,
          [ROW_LO if c <= 1 else ROW_HI for c in per_gen]))
    print('-' * 78)
    for i, nd in enumerate(nodes):
        _, sur, giv, rel, st = nd
        depth = gen[i]
        pad = ''
        # 用父链的槽位关系画一个粗略的树形前缀
        print('  g%-2d x%-5.1f y%-4d %-5s%-4s [%-6s] %-4s %s'
              % (gen[i], slot[i], y[i], sur, giv, rel, _ST[st],
                 ('父=%d' % nd[0]) if nd[0] is not None else '根'))
    print()


if __name__ == '__main__':
    tot = 0
    for sur, giv, nodes in TREES:
        gen, slot, kids, y, per_gen = layout(nodes)
        ncol = max(slot) + 1
        w = ncol * COL_W
        h = y[-1] + REL_DY + 8 if y else 0
        print('%-4s %-4s  %2d人 %d代  列数%-3d  画布 %dx%d  pid范围=%d..%d'
              % (sur, giv, len(nodes), len(per_gen), ncol, w, h,
                 min(x[0] if x[0] is not None else -1 for x in nodes),
                 max(i for i, _ in enumerate(nodes))))
        tot += len(nodes)
        if sur == '柴田':
            render_ascii(nodes, gen, slot, kids, y, per_gen, sur + giv)
    print('全部家族合计 %d 人' % tot)
