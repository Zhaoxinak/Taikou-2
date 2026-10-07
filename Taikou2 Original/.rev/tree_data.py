"""tree_data.py — 家族树数据模型 / 布局 / 二进制编码

被 build_fam_btn2.py import。本模块只产出数据(不碰 exe)。

★ v8 改版要点
  1) TREES 每项改为 (家族标题姓, [(触发姓,触发名)...], (本人姓,本人名), 节点表):
     - 一个家族可挂多个触发名(别名): 木下藤吉郎/羽柴秀吉/丰臣秀吉 同开一座丰臣家树。
       每个触发名输出一条 FAM_DIR, 共享同一 start/count/bbox/subject。
     - 「本人」不再靠触发名与节点同名自动判定, 改由 subject 显式指定。
  2) 族谱为 MOD 内置数据, 与游戏实体表无关 —— 游戏里没有的人物(阿市/茶茶/
     宁宁/见松殿…)直接写进节点表即可显示, 不需要武将卡。

串池格式(v7 沿用): 每条 = [u8 len][gbk bytes][0x00](长度前缀, TextOutA 需显式长度)。

详情记录(v11): 每节点 = [u8 len1][gbk 主行][u8 len2][gbk 档案行](len2=0 则无档案行);
  DETAILTAB 存该记录在串池内的偏移, 渲染层据此画两行(带边框详情框)。

二进制格式(全部在新节 .fdata 内, 偏移都是相对 STR_POOL 的 uint16):

FAM_DIR 每条 24 字节
    +0  name_dword  dword  触发者名(GBK 前 4B, 用于匹配当前武将)
    +4  sur_dword   dword  触发者姓
    +8  start2      u8     起始节点索引 / 2 (★族块长凑偶, 渲染层 imul 20 取字节偏移)
    +9  count       u8     本次要画的节点数 —— 开树时由动态桩从 static_n 抬到 static_n+点亮数
    +10 title_off   u16    家族标题串偏移(如 "柴田氏")
    +12 cx0/cy0/cx1/cy1  i16×4  内容包围盒(平移钳制用, 已含动态槽那一行)
    +20 subject     u8     「本人」节点在家族内的相对索引(打开时居中到它)
    +21 static_n    u8     静态人数(动态桩每次开树用它复位 count, 它是只读真值)
    +22 pad u8 / +23 pad u8

NODE_TAB 每条 10 字节
    +0  cx, +2 cy (i16 内容坐标, 头像框中心)
    +4  name_off, +6 rel_off (u16 串池偏移)
    +8  parent u8 (家族内索引, 0xFF=根), +9 flags u8
        flags: bit0-1 状态(0在世 1已故 2未出生), bit2=本人, bit3=配偶, bit4=动态子嗣槽

OIDTAB 每节点 u16 —— 该节点在游戏实体表里的人物编号(BSDATA oid), 无对应人 = 0xFFFF。
  动态桩靠它认「本人的孩子」(实体 word[+0x1d] = 父 oid)并对掉谱里已有的人。

★ 节点写法: (父索引|None=根, 姓, 名, 关系, 状态[, 是配偶])
  - 配偶节点(v9): parent=**丈夫索引**, 与丈夫同排、列丈夫右侧半格;
    渲染层对**每个**带配偶标记的节点画青色 U 形括号 —— 父母也是夫妻, 照样连。
  - 休室(离异)/儿媳等不标记 → 不画括号; 岳父/妻兄等无血缘姻亲列独立根。
  - 关系串一律**相对本人**。
  - 状态对齐 1560「尾张的鸣条」开局: 卒于 1560 前→已故; 1560 后出生→未出生。
"""
import struct
import os as _os
import json as _json
from collections import defaultdict

# ---------- 状态 ----------
S_ALIVE, S_DEAD, S_UNBORN = 0, 1, 2

# ---------- 精确/别名命中者附带的 BSDATA 档案(来自 gen_oid_map.py) ----------
#   仅取 conf in (exact, alias) 的安全命中做详情增强; fuzzy/none 一律不加,
#   否则会把父/子张冠李戴(实测 fuzzy 大量错人)。文件缺失则静默降级为纯族谱详情。
def _load_offmap():
    """-> {(姓,名): (BSDATA 档案, oid)}  仅 exact/alias 两档(其余会张冠李戴)。"""
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                      '_tree_oid_map.json')
    m = {}
    if not _os.path.exists(p):
        return m
    for e in _json.load(open(p, encoding='utf-8')):
        if e['conf'] in ('exact', 'alias') and e.get('officer'):
            m[(e['sur'], e['giv'])] = (e['officer'], e['oid'])
    return m


OFFMAP = _load_offmap()

STATE_NAME = ('在世', '已故', '未出生')

F_SUBJECT = 0x04
F_SPOUSE  = 0x08              # 配偶: 与本人平级, 渲染时画水平连线而非亲子线
F_DYN     = 0x10              # 动态子嗣槽(开树时由实体表点亮, 未点亮不进 count)

# ---------- 动态子嗣 (v13): 游戏内生的孩子要能出现在族谱里 ----------
#   每家在「本人」的子代行右侧烘死 DYN_SLOTS 个空槽(坐标/亲缘线全在构建期算好,
#   运行时只写名字串 + 把 FAM_DIR.count 从 static_n 抬到 static_n+used),
#   于是渲染层零算术 —— 手写 x86 少一处几何就越少一处崩。
#   槽的名字串是**共享可变**记录(同一次只显示一家, 槽位 j 复用): [u8 len][GBK<=14B][NUL]
DYN_SLOTS = 6
DYN_STR_SZ = 16               # 单条可变名字记录占位
DYN_REL = '子'                # 性别引擎没记(见 child-preload 计划的欠账), 族谱一律称"子"
DYN_DETAIL = u'游戏内出生之子  子  在世  随父亲住在本城'
DYN_STR_BASE = 0              # 可变名字区就放在串池最前面, 偏移构建期即定值

# ---- 通用「本人 + 子嗣」块 (审查所有人的族谱) ----
#   27 家之外的人物(含玩家自创/元服后改姓/主角)过去一律回落柴田树 = 误导。
#   现在 FAM_DIR 尾上多一条**不参与姓名匹配**的通用记录, 它指向 NODE_TAB 末尾一块
#   8 节点的固定几何(本人在上, 6 个子嗣槽在下), 运行时桩把本人姓名/「X氏」标题/
#   子嗣姓名写进池首可变区并抬 count —— 谁点族谱都看得到自己的孩子。
GEN_NAME_IDX = DYN_SLOTS                  # 可变区第 6 条 = 本人姓名
GEN_TITLE_IDX = DYN_SLOTS + 1             # 第 7 条 = 标题「X氏」
GEN_RECS = DYN_SLOTS + 2                  # 池首可变区总条数
GEN_TITLE_SUFFIX = '氏'
GEN_DETAIL = u'当前查看的人物  本人  在世  下排为其游戏内子嗣'
GEN_FLAG = 1                              # FAM_DIR+22 = 1 -> 动态桩走通用分支


def dyn_str_off(j):
    return DYN_STR_BASE + j * DYN_STR_SZ

# ---------- 几何常量 (内容坐标系, 单位为物理像素) ----------
AV_W, AV_H = 26, 30          # 头像框尺寸
AV_HX, AV_HY = AV_W // 2, AV_H // 2
ROW_HI   = 100               # 该代 >=2 人时的行距
ROW_LO   = 84                # 该代 1 人时的行距(单链紧凑)
COL_W    = 70                # 列距(槽位宽)
TREE_TOP = 10                # 内容区顶部留白

# 标签紧贴头像框下沿 —— 视觉上"框 + 姓名 + 关系"必须成一组。
# 行距下限 = 连线起点(EDGE_TOP = OFS_REL+REL_H+6) + 竖线余量 + AV_HY(下一框上半)。
# REL_H / EDGE_TOP 必须与 tree_render.py 保持同步。
OFS_NAME = AV_HY + 7         # 姓名相对 cy (框下沿 = cy+15, 再下 7px)
OFS_REL  = OFS_NAME + 12     # 关系相对 cy
REL_H    = 12                # 关系字号(tree_render.FTRL 的字高, bbox 下沿用)

# ---------- 布局自洽断言 (改常量时别再算错) ----------
assert OFS_NAME > AV_HY, '姓名必须落在头像框下沿之外'
_EDGE_TOP = OFS_REL + REL_H + 6           # 连线起点(tree_render.EDGE_TOP)
_ROW_MIN = _EDGE_TOP + 7 + AV_HY          # + 竖线余量 + 下一框上半
assert ROW_LO >= _ROW_MIN, \
    'ROW_LO=%d 太挤: 关系标签会被连线穿过、或压到下一代头像框 (需 >= %d)' % (ROW_LO, _ROW_MIN)

# ======================================================================
# 史实家族树 —— 依据《信长公记》《当代记》各藩士传系谱及通行战国史料。
# 族谱是 MOD 内置数据, 游戏实体表里没有的人(阿市/宁宁/见松殿/茶茶…)
# 照样入树显示。生卒与 1560 开局对照定状态。
# 命名: 游戏字库为 GBK 汉字, 一律用汉字写法(「お市」→「阿市」, 「茶々」→「茶茶」),
#   避免平假名/々 豆腐块。
# ======================================================================

# ---- 柴田胜家 ----
# 父胜音(早逝); 兄胜久(其子胜丰过继给胜家为后); 弟胜政(贱岳后北庄从死);
# 1574 娶阿市(织田信长之妹), 携前夫浅井长政所生三女茶茶/初/江(故为养女);
# 信长是胜家妻兄兼主君, 列第二个根。
SHIBATA_NODES = [
    (None, '柴田', '胜音',   '父',   S_DEAD),
    (0,    '柴田', '胜久',   '兄',   S_ALIVE),
    (0,    '柴田', '胜家',   '本人', S_ALIVE),
    (2,    '',     '阿市',   '正室', S_ALIVE, True),
    (0,    '柴田', '胜政',   '弟',   S_ALIVE),
    (2,    '柴田', '胜丰',   '养子', S_ALIVE),      # 胜久之实子, 过继
    (3,    '',     '茶茶',   '养女', S_UNBORN),     # 1571 生(阿市前夫之女)
    (3,    '',     '初',     '养女', S_UNBORN),     # 1573 生
    (3,    '',     '江',     '养女', S_UNBORN),     # 1578 生
    (None, '织田', '信长',   '妻兄', S_ALIVE),
]

# ---- 织田信长 ----
# 父信秀(1552 卒), 母土田御前; 弟信行(1557 被杀)→已故, 弟信包(信秀四子);
# 正室浓姬(斋藤道三女); 子信忠(1557)/信雄(1558)/信孝(~1559) 开局均在世(幼年),
# 四子信秀(1566 生→未出生); 女五德(嫁池田恒兴); 孙信胜(信忠子, 1571 生)。
# ★ 夫妻连线约定(v9): 母亲标配偶挂父亲(信秀), 与父亲同排并画括号;
#   正室浓姬挂丈夫信长。儿媳(非本人正室)不标记, 挂家父位下与丈夫同排相邻。
ODA_NODES = [
    (1,    '',     '土田御前', '母',   S_ALIVE, True),
    (None, '织田', '信秀',     '父',   S_DEAD),
    (1,    '织田', '信长',     '本人', S_ALIVE),
    (2,    '',     '浓姬',     '正室', S_ALIVE, True),
    (1,    '织田', '信行',     '弟',   S_DEAD),
    (1,    '织田', '信包',     '弟',   S_ALIVE),
    (2,    '织田', '信忠',     '长子', S_ALIVE),
    (2,    '织田', '信雄',     '次子', S_ALIVE),
    (2,    '织田', '信孝',     '三子', S_ALIVE),
    (2,    '织田', '信秀',     '四子', S_UNBORN),
    (2,    '织田', '五德',     '女',   S_ALIVE),
    (6,    '织田', '信胜',     '长孙', S_UNBORN),
]

# ---- 浅井长政 ----
# 祖父胜久(小谷城主, 1521 卒)/父久政(1573 自刃, 开局在世);
# 正室阿市(1560 前后嫁); 一子万福(夭)+三女茶茶/初/江均 1560 后生;
# 岳父织田信长列第二根。
AZAI_NODES = [
    (None, '浅井', '胜久',   '祖父', S_DEAD),
    (0,    '浅井', '久政',   '父',   S_ALIVE),
    (1,    '浅井', '长政',   '本人', S_ALIVE),
    (2,    '',     '阿市',   '正室', S_ALIVE, True),
    (None, '织田', '信长',   '岳父', S_ALIVE),
    (2,    '浅井', '万福',   '长子', S_UNBORN),
    (2,    '',     '茶茶',   '长女', S_UNBORN),
    (2,    '',     '初',     '次女', S_UNBORN),
    (2,    '',     '江',     '三女', S_UNBORN),
]

# ---- 明智光秀 ----
# 父系诸说(光德/光久/纲家)不采; 妻煚子(通行记法);
# 明智秀满=从兄弟(通行说, 系谱有争); 三女伽罗奢嫁细川忠兴(忠兴入女婿位);
# 子女均 1560 后出生→未出生(十五/五郎/伽罗奢/町, 早夭诸子不采)。
AKECHI_NODES = [
    (None, '明智', '光秀',   '本人', S_ALIVE),
    (0,    '',     '煚子',   '正室', S_ALIVE, True),
    (None, '明智', '秀满',   '从兄弟', S_ALIVE),  # 独立根: 非亲子, 不画父线
    (None, '细川', '忠兴',   '女婿', S_UNBORN),   # 1563 生; 独立根
    (1,    '明智', '十五',   '长子', S_UNBORN),
    (1,    '明智', '五郎',   '次子', S_UNBORN),
    (1,    '细川', '伽罗奢', '三女', S_UNBORN),   # 1563 生
    (1,    '',     '町',     '四女', S_UNBORN),
]

# ---- 丰臣秀吉 ----
# 父木下弥次郎(日阿弥), 母天瑞院(仲, 大政所); 同母弟秀长, 异母弟木下家定/大村由己;
# 正室宁宁(高台院); 养子秀胜(姐之子)/秀秋(姐之子, 后入小早川)/秀家(后入宇喜多);
# 实子鹤松(1589-1591 夭)/弃(1593 生)均未出生。
HIDEYOSHI_NODES = [
    (1,    '',     '天瑞院',   '母',   S_ALIVE, True),
    (None, '',     '木下弥次郎', '父', S_DEAD),
    (1,    '丰臣', '秀吉',     '本人', S_ALIVE),
    (2,    '',     '宁宁',     '正室', S_ALIVE, True),
    (1,    '丰臣', '秀长',     '弟',   S_ALIVE),
    (1,    '木下', '家定',     '异母弟', S_ALIVE),
    (1,    '大村', '由己',     '异母弟', S_ALIVE),
    (2,    '羽柴', '秀胜',     '养子', S_UNBORN),  # 1569 生, 姐之子
    (2,    '小早川', '秀秋',   '养子', S_UNBORN),  # 1568 生, 姐之子
    (2,    '宇喜多', '秀家',   '养子', S_UNBORN),  # 1573 生
    (2,    '丰臣', '鹤松',     '长子', S_UNBORN),
    (2,    '丰臣', '弃',       '次子', S_UNBORN),
]

# ---- 德川家康 ----
# 父松平广忠(1549 卒), 母于大之方; 正室筑山殿(1579 被废, 开局在世);
# 子: 信康(1557 生, 在世)/秀康(1568, 后结城家)/秀忠(1579)/忠吉(1565)/
# 直政(1561, 后井伊家)均 1560 后生→未出生; 儿媳见松殿(武田信玄女)。
TOKUGAWA_NODES = [
    (1,    '',     '于大之方', '母',   S_ALIVE, True),
    (None, '松平', '广忠',     '父',   S_DEAD),
    (1,    '德川', '家康',     '本人', S_ALIVE),
    (2,    '',     '筑山殿',   '正室', S_ALIVE, True),
    (2,    '松平', '信康',     '长子', S_ALIVE),
    (2,    '',     '见松殿',   '儿媳', S_ALIVE),   # 挂家父位下, 与丈夫信康同排相邻
    (2,    '结城', '秀康',     '次子', S_UNBORN),
    (2,    '德川', '秀忠',     '三子', S_UNBORN),
    (2,    '松平', '忠吉',     '四子', S_UNBORN),
    (2,    '井伊', '直政',     '五子', S_UNBORN),
]

# ---- 武田信玄 ----
# 父信虎(1574 卒, 开局在世), 母大井之方(大井信达女);
# 正室御姬(上杉宪政姊, 1558 离婚还国→记"休室", 不画配偶括号);
# 长子义信(1567 幽死, 开局在世)+儿媳黄梅院(北条氏康女);
# 胜赖(四子, 1546 生, 生母诹访御料人); 长女见松殿(嫁松平信康);
# 仁科盛信(六子, 1557 生→开局在世)。早夭诸子(松千代/桃源院/信松尼等)不采。
TAKEDA_NODES = [
    (1,    '',     '大井之方', '母',   S_ALIVE, True),
    (None, '武田', '信虎',     '父',   S_ALIVE),
    (1,    '武田', '信玄',     '本人', S_ALIVE),
    (None, '',     '御姬',     '休室', S_ALIVE),  # 1558 离异还国: 不画括号, 独立根
    (2,    '武田', '义信',     '长子', S_ALIVE),
    (2,    '北条', '黄梅院',   '儿媳', S_ALIVE),   # 挂家父位下, 与丈夫义信同排相邻
    (2,    '武田', '胜赖',     '四子', S_ALIVE),
    (2,    '武田', '见松殿',   '长女', S_ALIVE),
    (2,    '仁科', '盛信',     '六子', S_ALIVE),
]

# ---- 上杉谦信 ----
# 父长尾为景(1547 卒→已故); 兄宪景(关东管领, 1550 卒→已故);
# 谦信=为景四子(虎千代); 养子景胜(1556 生, 后与佐佐成政争…系诸说),
# 与三郎(今川氏真之子, 入继诸说)一并列养子位。
UESUGI_NODES = [
    (None, '长尾', '为景',   '父',   S_DEAD),
    (0,    '上杉', '宪景',   '兄',   S_DEAD),
    (0,    '上杉', '谦信',   '本人', S_ALIVE),
    (2,    '上杉', '景胜',   '养子', S_ALIVE),
    (2,    '上杉', '与三郎', '养子', S_ALIVE),
]

# ---- 北条氏康 ----
# 父氏纲(1541 卒→已故); 子氏政(长)/氏照/氏邦/氏规(长幼诸说, 取通行序);
# 长女黄梅院嫁武田义信; 孙氏直(氏政子, 1580 生→未出生)。
HOJO_NODES = [
    (None, '北条', '氏纲',   '父',   S_DEAD),
    (0,    '北条', '氏康',   '本人', S_ALIVE),
    (0,    '北条', '氏政',   '长子', S_ALIVE),
    (0,    '北条', '氏照',   '次子', S_ALIVE),
    (0,    '北条', '氏邦',   '三子', S_ALIVE),
    (0,    '北条', '氏规',   '四子', S_ALIVE),
    (0,    '武田', '黄梅院', '长女', S_ALIVE),
    (2,    '北条', '氏直',   '长孙', S_UNBORN),
]

# ---- 毛利元就 ----
# 父弘元(1533 卒)/兄兴元(1530 被杀)均已故; 元就本人 1571 卒→开局在世;
# 子: 隆元(长)/吉川元春(次)/小早川隆景(三)/穗井田元清(四, 系谱诸说);
# 孙辉元(隆元子, 1553 生→在世)。元就正室无定说, 不采。
MORI_NODES = [
    (None, '毛利', '弘元',     '父',   S_DEAD),
    (0,    '毛利', '兴元',     '兄',   S_DEAD),
    (0,    '毛利', '元就',     '本人', S_ALIVE),
    (2,    '毛利', '隆元',     '长子', S_ALIVE),
    (2,    '吉川', '元春',     '次子', S_ALIVE),
    (2,    '小早川', '隆景',   '三子', S_ALIVE),
    (2,    '穗井田', '元清',   '四子', S_ALIVE),
    (3,    '毛利', '辉元',     '长孙', S_ALIVE),
]

# ---- 吉川元春 ----
# 父元就(开局在世); 兄隆元/弟隆景并列;
# 子: 元长(长)/元氏(二, 后过继小早川隆景=小早川秀秋养父一脉的"广缘/三左卫门"前身)。
KIKKAWA_NODES = [
    (None, '毛利', '元就',   '父',   S_ALIVE),
    (0,    '吉川', '元春',   '本人', S_ALIVE),
    (0,    '毛利', '隆元',   '兄',   S_ALIVE),
    (0,    '小早川', '隆景', '弟',   S_ALIVE),
    (1,    '吉川', '元长',   '长子', S_ALIVE),
    (1,    '小早川', '元氏', '次子', S_ALIVE),
]

# ---- 小早川隆景 ----
# 父元就(在世)/兄元春; 养子秀秋(丰臣秀吉姐之子, 1568 生→未出生)。
# 隆景正室无定说, 不采。
KOBAYAKAWA_NODES = [
    (None, '毛利', '元就',     '父',   S_ALIVE),
    (0,    '小早川', '隆景',   '本人', S_ALIVE),
    (0,    '吉川', '元春',     '兄',   S_ALIVE),
    (1,    '小早川', '秀秋',   '养子', S_UNBORN),
]

# ---- 岛津贵久 ----
# 父岛津忠良(日新斋, 1496-1570→在世, 佐多氏出, 入继宗家);
# "岛津四兄弟"通行序: 义久(长)/岁久(二)/义弘(三)/家久(四);
# 家久子忠恒(1576 生→未出生)。贵久正室无通行记法, 不采。
SHIMAZU_NODES = [
    (None, '岛津', '忠良', '父',   S_ALIVE),
    (0,    '岛津', '贵久', '本人', S_ALIVE),
    (1,    '岛津', '义久', '长子', S_ALIVE),
    (1,    '岛津', '岁久', '次子', S_ALIVE),
    (1,    '岛津', '义弘', '三子', S_ALIVE),
    (1,    '岛津', '家久', '四子', S_ALIVE),
    (5,    '岛津', '忠恒', '孙',   S_UNBORN),
]

# ---- 伊达辉宗 ----
# 父晴宗(1514-1564→在世); 弟盛宗(东山敏宗说);
# 正室义姬(最上家出, 生母诸说: 义守女说/晴宗女说并存 → 不画娘家链,
#   采"最上义光之姊(或妹)"通行说, 义光列"妻兄/妻弟"位——取"妻兄"(义光 1546 生长于辉宗);
# 子: 政宗(1567 生→未出生)/小次郎(幼名权十郎, 早世)。
DATE_NODES = [
    (None, '伊达', '晴宗',   '父',   S_ALIVE),
    (0,    '伊达', '辉宗',   '本人', S_ALIVE),
    (1,    '',     '义姬',   '正室', S_ALIVE, True),
    (0,    '伊达', '盛宗',   '弟',   S_ALIVE),
    (None, '最上', '义光',   '妻兄', S_ALIVE),      # 独立根: 不画亲子线
    (1,    '伊达', '政宗',   '长子', S_UNBORN),
    (1,    '伊达', '小次郎', '次子', S_UNBORN),
]

# ---- 最上义光 ----
# 父义守(1614 卒→在世); 弟中村义康(义守次子, 中村家);
# 长子家光(生年不详, 1560 时父仅 14 岁→按未出生处理);
# 正室室町殿(义光正室=清水朝正? 无定说)不采; 爱姬(家光子)不采。
MOGAMI_NODES = [
    (None, '最上', '义守',   '父',   S_ALIVE),
    (0,    '最上', '义光',   '本人', S_ALIVE),
    (0,    '中村', '义康',   '弟',   S_ALIVE),
    (1,    '最上', '家光',   '长子', S_UNBORN),
]

# ---- 大友宗麟(义镇) ----
# 父义鉴(1550 被杀→已故); 子义统(长, 1558 生→在世)/亲直(二, 生年 1560 后→未出生)。
# 宗麟正室(毛利元就养女说)名无定说不采; 户次鉴连(高鉴)为义鉴庶弟说存疑, 不采。
OTOMO_NODES = [
    (None, '大友', '义鉴', '父',   S_DEAD),
    (0,    '大友', '宗麟', '本人', S_ALIVE),
    (1,    '大友', '义统', '长子', S_ALIVE),
    (1,    '大友', '亲直', '次子', S_UNBORN),
]

# ---- 森可成 ----
# 美浓土着、织田家臣(1523 生·1570 战死→1560 在世)。子: 长可(长子, 1558 生→在世)、
# 兰丸(三子, 1565 生→未出生)。兰丸幼名"松寿丸"、后称"成利", 与"兰丸"是同一人,
# 不再单列为"孙"(旧数据把松寿丸错挂成长可之子, 且 BSDATA 里兰丸之父=可成 id2)。
MORI_YOSINARI_NODES = [
    (None, '森', '可成',   '本人', S_ALIVE),
    (0,    '森', '长可',   '长子', S_ALIVE),
    (0,    '森', '兰丸',   '三子', S_UNBORN),
]

# ---- 真田幸隆 ----
# 血统一律以 BSDATA 为准(父字段 u16@+0x29 实测): 幸隆(oid196) 三子 = 信纲(220)/昌辉(224)/昌幸(231);
# 信之(235, 旧名信幸)与幸村(236, 即后世所称"真田幸村")的父字段都写 231 ⇒ 昌幸之子、幸隆之孙。
# 旧数据两处错: ①整缺昌幸节点; ②把"三男"记成无档案的"令辉"(游戏里 224 已有独立的"昌辉"),
#   结果 幸村 挂到昌辉(224)、信幸 经模糊档接到 196(幸隆本人) —— 整代错位。
SANADA_NODES = [
    (None, '真田', '幸隆', '本人', S_ALIVE),
    (0,    '真田', '信纲', '长子', S_ALIVE),
    (0,    '真田', '昌辉', '二郎', S_ALIVE),
    (0,    '真田', '昌幸', '三男', S_ALIVE),
    (3,    '真田', '信之', '孙',   S_UNBORN),
    (3,    '真田', '幸村', '孙',   S_UNBORN),
]

# ---- 今川义元 ----
# 父氏亲(1526 卒→已故); 子氏真(长, 1538 生→在世)。
# 义元正室(武田信虎女, 1558 离返)状态存疑不采; 弟氏尧说混乱不采。
IMAGAWA_NODES = [
    (None, '今川', '氏亲', '父',   S_DEAD),
    (0,    '今川', '义元', '本人', S_ALIVE),
    (1,    '今川', '氏真', '长子', S_ALIVE),
]

# ---- 斋藤义龙 ----
# 父道三(1561 死→开局在世); 妹浓姬(嫁织田信长)。
# 弟光明坊/大见周监理同被义龙所杀(1547/1556)→世系记法混乱, 不采。
SAITO_NODES = [
    (None, '斋藤', '道三', '父',   S_ALIVE),
    (0,    '斋藤', '义龙', '本人', S_ALIVE),
    (0,    '织田', '浓姬', '妹',   S_ALIVE),
]

# ---- 朝仓义景 ----
# 父义定(1542 战死→已故)。义景无子; 从弟朝仓宗滴为同族重臣, 系谱跨代不采。
ASAKURA_NODES = [
    (None, '朝仓', '义定', '父',   S_DEAD),
    (0,    '朝仓', '义景', '本人', S_ALIVE),
]

# ======================================================================
# 组装: (家族标题姓, [(触发姓, 触发名)...], (本人姓, 本人名), 节点表)
#   - 第 0 家必须是柴田(FAM_DIR 首条 = 调试兜底树)。
#   - 触发名与游戏活名表前 4 字节(两个汉字)比对, 三字名截前二字。
# ======================================================================
TREES = [
    ('柴田', [('柴田', '胜家')],           ('柴田', '胜家'), SHIBATA_NODES),
    ('织田', [('织田', '信长')],           ('织田', '信长'), ODA_NODES),
    ('浅井', [('浅井', '长政')],           ('浅井', '长政'), AZAI_NODES),
    ('明智', [('明智', '光秀')],           ('明智', '光秀'), AKECHI_NODES),
    ('丰臣', [('木下', '藤吉郎'), ('羽柴', '秀吉'), ('丰臣', '秀吉')],
                                         ('丰臣', '秀吉'), HIDEYOSHI_NODES),
    ('德川', [('德川', '家康'), ('松平', '元康')],
                                         ('德川', '家康'), TOKUGAWA_NODES),
    ('武田', [('武田', '信玄'), ('武田', '晴信')],
                                         ('武田', '信玄'), TAKEDA_NODES),
    ('上杉', [('上杉', '谦信'), ('长尾', '虎千代')],
                                         ('上杉', '谦信'), UESUGI_NODES),
    ('北条', [('北条', '氏康')],           ('北条', '氏康'), HOJO_NODES),
    ('毛利', [('毛利', '元就')],           ('毛利', '元就'), MORI_NODES),
    ('吉川', [('吉川', '元春')],           ('吉川', '元春'), KIKKAWA_NODES),
    ('小早川', [('小早川', '隆景')],       ('小早川', '隆景'), KOBAYAKAWA_NODES),
    ('岛津', [('岛津', '贵久')],           ('岛津', '贵久'), SHIMAZU_NODES),
    ('伊达', [('伊达', '辉宗')],           ('伊达', '辉宗'), DATE_NODES),
    ('最上', [('最上', '义光')],           ('最上', '义光'), MOGAMI_NODES),
    ('大友', [('大友', '宗麟')],           ('大友', '宗麟'), OTOMO_NODES),
    ('森',   [('森', '可成')],             ('森', '可成'),   MORI_YOSINARI_NODES),
    ('真田', [('真田', '幸隆')],           ('真田', '幸隆'), SANADA_NODES),
    ('今川', [('今川', '义元')],           ('今川', '义元'), IMAGAWA_NODES),
    ('斋藤', [('斋藤', '义龙'), ('斋藤', '义隆')],
                                         ('斋藤', '义龙'), SAITO_NODES),
    ('朝仓', [('朝仓', '义景')],           ('朝仓', '义景'), ASAKURA_NODES),
]


# ======================================================================
# 布局
# ======================================================================
def layout(nodes):
    """-> (gen[], slot[], per_gen[])   slot 是列槽位(可为 .5, 父居中于子)

    配偶约定(v9): 带配偶标记的节点 parent=丈夫索引 —— 与丈夫**同代同排**,
    slot=丈夫+1 整格(COL_W=70, 四字姓名不叠字); 妻子的子女排在亲生子女之后,
    连线由渲染层从妻子节点自己垂下。
    """
    n = len(nodes)
    spouse_of = {}                     # 丈夫索引 -> 妻子索引
    kids = defaultdict(list)
    roots = []
    for i, nd in enumerate(nodes):
        is_sp = len(nd) > 5 and bool(nd[5])
        if is_sp:
            assert nd[0] is not None, '配偶节点必须挂丈夫(parent=丈夫索引)'
            spouse_of[nd[0]] = i
            continue
        if nd[0] is None:
            roots.append(i)
        else:
            kids[nd[0]].append(i)
    gen = [0] * n

    def dfs(i, g):
        gen[i] = g
        w = spouse_of.get(i)
        if w is not None:
            gen[w] = g
        for c in kids[i]:
            dfs(c, g + 1)
        if w is not None:
            for c in kids[w]:
                dfs(c, g + 1)
    for r in roots:
        dfs(r, 0)

    slot = [0.0] * n
    cur = [0]

    def place(i):
        w = spouse_of.get(i)
        cl = kids[i] + (kids[w] if w is not None else [])
        if not cl:
            slot[i] = float(cur[0]); cur[0] += 1
        else:
            for c in cl:
                place(c)
            slot[i] = (slot[cl[0]] + slot[cl[-1]]) / 2.0
        if w is not None:
            slot[w] = slot[i] + 1.0
            cur[0] = max(cur[0], slot[w] + 1)     # 妻子槽位不许被后续兄弟占用
    for r in roots:
        place(r)

    maxg = max(gen)
    per_gen = [0] * (maxg + 1)
    for g in gen:
        per_gen[g] += 1
    return gen, slot, per_gen


def build_layouts():
    """-> [ dict(title, triggers, rows, bbox, subject, static_n, dyn_at) ]

    rows 里每项: (cx, cy, name_str|None, rel_str, parent_index_or_FF, flags, sg, dyn)
      dyn = None 真人节点 / 0..DYN_SLOTS-1 动态子嗣槽 / -1 对齐填充(永不显示)
    坐标是**内容坐标系**(左上角不固定), 运行时加平移量后才是屏幕坐标。
    """
    out = []
    for title, triggers, subj, nds in TREES:
        assert nds[0][0] is None or True   # 根不强制在第 0 位
        gen, slot, per_gen = layout(nds)
        gaps = [ROW_LO if c <= 1 else ROW_HI for c in per_gen]
        rel_y = [0.0] * len(nds)
        a = 0.0
        for g in range(len(per_gen)):
            for i in range(len(nds)):
                if gen[i] == g:
                    rel_y[i] = a
            a += gaps[g]
        cys = [int(round(TREE_TOP + AV_HY + rel_y[i])) for i in range(len(nds))]
        rows = []
        si = -1
        for i, nd in enumerate(nds):
            p, s, g, rt, st = nd[:5]
            is_spouse = bool(nd[5]) if len(nd) > 5 else False
            cx = int(round(slot[i] * COL_W + COL_W / 2))
            cy = cys[i]
            name = (s + g) if s else g
            flags = st | (F_SUBJECT if (s, g) == subj else 0) | (F_SPOUSE if is_spouse else 0)
            if flags & F_SUBJECT:
                assert si < 0, '%s氏: 本人节点重名/多命中' % title
                si = i
            rows.append((cx, cy, name, rt, 0xFF if p is None else p, flags, (s, g), None))
        assert si >= 0, '%s氏: 找不到本人节点 %r' % (title, subj)
        static_n = len(rows)

        # ---- 动态子嗣槽: 「本人」下一代那一行的最右边接着排 ----
        #   该行的其它分支(兄弟/侄)也算进来, 所以取"同 cy 那一行的最大列槽 + 1"起排,
        #   保证孩子生多少个都不会跟已有的框叠在一起。
        nxt = [i for i in range(len(nds)) if gen[i] == gen[si] + 1]
        if nxt:
            dyn_cy = cys[nxt[0]]
        else:
            dyn_cy = cys[si] + ROW_HI
            nxt = [i for i in range(len(nds)) if cys[i] == dyn_cy]
        base = (max(slot[i] for i in nxt) + 1.0) if nxt else slot[si] + 1.0
        dyn_at = len(rows)
        for j in range(DYN_SLOTS):
            rows.append((int(round((base + j) * COL_W + COL_W / 2)), dyn_cy,
                         None, DYN_REL, si, S_ALIVE | F_DYN, None, j))
        # 块长凑偶: FAM_DIR.start 存的是"块长/2"(u8), 渲染层 imul 20 拿字节偏移
        pad = None
        if len(rows) % 2:
            pad = (rows[dyn_at][0], dyn_cy, ' ', ' ', 0xFF, 0, None, -1)
            rows.append(pad)

        xs = [r[0] for r in rows if r[7] != -1]
        ys = [r[1] for r in rows if r[7] != -1]
        bbox = (min(xs) - AV_HX, min(ys) - AV_HY,
                max(xs) + AV_HX, max(ys) + OFS_REL + REL_H)
        out.append(dict(title=title + '氏', triggers=list(triggers), subject=si,
                        rows=rows, bbox=bbox, static_n=static_n, dyn_at=dyn_at,
                        subj_oid=(OFFMAP.get(rows[si][6]) or (None, None))[1]))
    return out


# ======================================================================
# 二进制编码
# ======================================================================
def _detail(title, name, rt, flags, sg):
    """点击节点时自绘的详情 -> (主行, 档案行)。
    主行恒在(族谱身份); 档案行仅 exact/alias 命中者有(BSDATA 数值), 否则 ''。
    绝不塞 fuzzy/none —— 会张冠李戴到别人。"""
    line1 = '%s  %s  %s  【%s】' % (name, rt, STATE_NAME[flags & 3], title)
    line2 = ''
    o = (OFFMAP.get(sg) or (None, None))[0]
    if o:
        seg = []
        by = o.get('birth_year')
        if by and by > 0:
            seg.append('生%d' % by)
        if o.get('rank_name'):
            seg.append(o['rank_name'])
        f = [o.get('lead'), o.get('martial'), o.get('domestic'),
             o.get('diplomacy'), o.get('charm')]
        if any(v is not None for v in f):
            seg.append('统武政外魅' + '/'.join(str(v) if v is not None else '?'
                                               for v in f))
        line2 = ' '.join(seg)
    while len(line1.encode('gbk')) > 250:
        line1 = line1[:-1]
    while len(line2.encode('gbk')) > 250:
        line2 = line2[:-1]
    return line1, line2


def encode():
    """-> dict(dir, nodes, pool, detail, oids, meta, dyn_*, ndir, nnode)"""
    layouts = build_layouts()
    pool = bytearray(b'\x00' * (GEN_RECS * DYN_STR_SZ))   # 可变区钉在池首(6 子嗣 + 本人 + 标题)
    off = {}

    def intern(t):
        """长度前缀: [u8 len][bytes][NUL] —— TextOutA 必须拿到显式字符数"""
        if t in off:
            return off[t]
        b = t.encode('gbk')
        assert len(b) < 256, '单串超 255B: %r' % t
        off[t] = len(pool)
        pool.extend(bytes([len(b)]) + b + b'\x00')
        assert len(pool) < 65536, '串池超过 64KB'
        return off[t]

    def detail_rec(line1, line2):
        """详情记录: [u8 len1][gbk1][u8 len2][gbk2] —— 直接追加到同一串池(不去重,
        保证两段相邻), 渲染层据此画两行(档案行 len2=0 则只画主行)。返回记录起始偏移。"""
        b1 = line1.encode('gbk')
        b2 = line2.encode('gbk') if line2 else b''
        assert len(b1) < 256 and len(b2) < 256, '详情单行超 255B'
        o = len(pool)
        pool.extend(bytes([len(b1)]) + b1 + bytes([len(b2)]) + b2)
        assert len(pool) < 65536, '串池超过 64KB'
        return o

    dyn_detail = detail_rec(DYN_DETAIL, '')

    dir_b = bytearray()
    node_b = bytearray()
    detail_b = bytearray()
    oid_b = bytearray()
    meta = []
    for L in layouts:
        start = len(node_b) // 10
        assert start % 2 == 0, '%s氏: 族块长未凑偶, start/2 编码会错' % L['title']
        static_n = L['static_n']
        for cx, cy, name, rt, par, flags, sg, dj in L['rows']:
            if dj is None:                                 # 真人节点
                doff = detail_rec(*_detail(L['title'], name, rt, flags, sg))
                noff = intern(name)
                oid = (OFFMAP.get(sg) or (None, None))[1]
            elif dj >= 0:                                   # 动态子嗣槽(名字运行时写进池首)
                noff, doff, oid = dyn_str_off(dj), dyn_detail, None
            else:                                           # 对齐填充, 永不进 count
                noff, doff, oid = intern(' '), dyn_detail, None
            node_b.extend(struct.pack('<hhHHBB', cx, cy, noff, intern(rt), par, flags))
            detail_b.extend(struct.pack('<H', doff))
            oid_b.extend(struct.pack('<H', 0xFFFF if oid is None else oid))
        assert len(node_b) % 10 == 0, '节点表切不齐'
        assert static_n + DYN_SLOTS < 256 and start // 2 < 256
        title_off = intern(L['title'])
        for tgiv, tsur in [(g, s) for s, g in L['triggers']]:
            dir_b.extend(struct.pack(
                '<II',
                struct.unpack('<I', (tgiv.encode('gbk') + b'\0\0\0\0')[:4])[0],
                struct.unpack('<I', (tsur.encode('gbk') + b'\0\0\0\0')[:4])[0]))
            dir_b.extend(struct.pack('<BBH', start // 2, static_n, title_off))
            dir_b.extend(struct.pack('<hhhh', *L['bbox']))
            # +20 本人槽 / +21 静态人数(开树时由它复位 count) / +22,+23 保留
            dir_b.extend(struct.pack('<BBBB', L['subject'], static_n, 0, 0))
            assert len(dir_b) % 24 == 0
        meta.append(dict(L, start=start, n=len(L['rows'])))

    # ---- 通用块: 27 家之外所有人的树 = 本人 + 最多 6 个游戏内子嗣 ----
    #   几何在这里烘死(运行时桩零算术), 名字/标题走池首可变区, 所以整棵树可以
    #   只靠"写 8 条串 + 抬 count"就画出来。触发键 (0,0) 永不匹配任何活名,
    #   渲染层的姓名扫描会跳过它, 只有兜底路径按 GENERIC_DIR 直接指过来。
    gen_start = len(node_b) // 10
    assert gen_start % 2 == 0, '通用块起点未凑偶, start/2 编码会错'
    gen_doff = detail_rec(GEN_DETAIL, '')
    GEN_SUBJ_CX, GEN_SUBJ_CY = 210, 25
    GEN_ROW_CX0, GEN_ROW_CY = 35, GEN_SUBJ_CY + ROW_HI + 20   # 125
    node_b.extend(struct.pack('<hhHHBB', GEN_SUBJ_CX, GEN_SUBJ_CY,
                              dyn_str_off(GEN_NAME_IDX), intern('本人'),
                              0xFF, S_ALIVE | F_SUBJECT))
    detail_b.extend(struct.pack('<H', gen_doff))
    oid_b.extend(struct.pack('<H', 0xFFFF))
    for j in range(DYN_SLOTS):
        node_b.extend(struct.pack('<hhHHBB', GEN_ROW_CX0 + j * COL_W, GEN_ROW_CY,
                                  dyn_str_off(j), intern(DYN_REL),
                                  0, S_ALIVE | F_DYN))
        detail_b.extend(struct.pack('<H', dyn_detail))
        oid_b.extend(struct.pack('<H', 0xFFFF))
    # 块长凑偶(8 节点已偶, 这条只是把"填充永不显示"的约定写满)
    node_b.extend(struct.pack('<hhHHBB', GEN_SUBJ_CX, GEN_SUBJ_CY,
                              intern(' '), intern(' '), 0xFF, 0))
    detail_b.extend(struct.pack('<H', dyn_detail))
    oid_b.extend(struct.pack('<H', 0xFFFF))
    generic_dir = len(dir_b)
    dir_b.extend(struct.pack('<II', 0, 0))                   # 不参与姓名匹配
    dir_b.extend(struct.pack('<BBH', gen_start // 2, 1, dyn_str_off(GEN_TITLE_IDX)))
    dir_b.extend(struct.pack('<hhhh',
                             GEN_ROW_CX0 - AV_HX, GEN_SUBJ_CY - AV_HY,
                             GEN_ROW_CX0 + (DYN_SLOTS - 1) * COL_W + AV_HX,
                             GEN_ROW_CY + OFS_REL + REL_H))
    dir_b.extend(struct.pack('<BBBB', 0, 1, GEN_FLAG, 0))
    assert len(dir_b) % 24 == 0 and len(node_b) % 10 == 0

    return dict(dir=bytes(dir_b), nodes=bytes(node_b), pool=bytes(pool),
                detail=bytes(detail_b), oids=bytes(oid_b),
                ndir=len(dir_b) // 24, nnode=len(node_b) // 10, meta=meta,
                dyn_str_base=DYN_STR_BASE, dyn_str_sz=DYN_STR_SZ,
                dyn_slots=DYN_SLOTS, dyn_detail=dyn_detail,
                # 姓名扫描的界限只数史实家族; 通用记录(触发键 0,0)靠 GENERIC_DIR 直达,
                # 不参与扫描 —— 省一个"活名恰好全零"的隐患。
                scan_ndir=generic_dir // 24,
                generic_dir=generic_dir,
                gen_start=gen_start, gen_static_n=1, gen_slots=DYN_SLOTS,
                gen_dyn_at=1, gen_name_idx=GEN_NAME_IDX,
                gen_title_idx=GEN_TITLE_IDX, gen_flag=GEN_FLAG,
                gen_recs=GEN_RECS,
                gen_detail_off=gen_doff, gen_title_suffix=GEN_TITLE_SUFFIX)


def preview():
    """ASCII 预览(自测用)"""
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for L in build_layouts():
        b = L['bbox']
        print('=== %s  触发%s  %d 人(静态%d+动态槽%d)  内容框 %s (%dx%d)  本人#%d oid=%s ==='
              % (L['title'], '/'.join(s + g for s, g in L['triggers']),
                 len(L['rows']), L['static_n'], DYN_SLOTS,
                 b, b[2] - b[0], b[3] - b[1], L['subject'], L['subj_oid']))
        for i, (cx, cy, nm, rt, par, fl, sg, dj) in enumerate(L['rows']):
            tag = '' if dj is None else (' (填充)' if dj < 0 else ' 动态#%d' % dj)
            print('  #%-2d (%4d,%4d) %-10s %-6s %-4s %s%s%s%s'
                  % (i, cx, cy, nm if nm is not None else '(运行时)', rt,
                     STATE_NAME[fl & 3],
                     '' if par == 0xFF else 'p=%d' % par,
                     ' ★本人' if fl & F_SUBJECT else '',
                     ' ♀配偶' if fl & F_SPOUSE else '', tag))
    e = encode()
    print()
    print('FAM_DIR %d 条 %dB | NODE_TAB %d 条 %dB | OIDTAB %dB | STR_POOL %dB | 合计 %dB'
          % (e['ndir'], len(e['dir']), e['nnode'], len(e['nodes']), len(e['oids']),
             len(e['pool']),
             len(e['dir']) + len(e['nodes']) + len(e['pool'])))


if __name__ == '__main__':
    preview()
