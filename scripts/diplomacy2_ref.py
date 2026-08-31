# -*- coding: utf-8 -*-
"""
diplomacy2_ref.py — Reference model of the Taikou2 DIPLOMACY RELATION SYSTEM
(国関係マトリクス / 外交関係 / 主从関係 / 使者归还结算).

Reverse-engineered 2026-08-29 (续95) from the unpacked image
(scripts/_unpacked_mem.bin, flat map, off = va - 0x400000).

This CLOSES the largest remaining purely-static gap left by 续89:
    「使者抵达后的关系值变更公式 / 成功率」

--------------------------------------------------------------------------
0. TL;DR —— 关系不是存在国表里, 而是一张 49x49 上三角位域矩阵
--------------------------------------------------------------------------
  国政治表      : 0x5179b8, stride 14 B, 49 条    (索引 = (ptr-0x5179b8)/14)
  关系矩阵      : 0x51dc60, 1176 B = 49*48/2      ★ 每个「国对」1 字节
  关系名称表    : 0x5080d0, stride 5 B, 12 项
  颜色表(外交)  : 0x503e68, word[8]
  颜色表(主从)  : 0x503e78, word[4]
  矩阵初始化    : 0x47f045  (edi = 0x498 = 1176 — 尺寸实锤)

  每字节两个位域:
      bit 0..2  = 外交関係 (8 级)
      bit 3..4  = 主从関係 (4 级)
      bit 5..7  = 未用

--------------------------------------------------------------------------
1. 三件核心 API (0x49fd60 / 0x49fe70 / 0x49fd80)
--------------------------------------------------------------------------
  0x49fd80  rel_lookup(prov_a, prov_b) -> byte* | NULL
      i = a ? (a-0x5179b8)/14 : 49
      j = b ? (b-0x5179b8)/14 : 49
      if i>=49 or j>=49 or i==j : return NULL
      if i > j : swap(i, j)
      return 0x51dc60 + tri_index(i, j)

  0x49fd60  get_diplomacy(a, b) =  rec ? (rec[0] & 7) : 0
  0x49fe70  get_master_vassal(a, b)
      lv = (rec[0] >> 3) & 3
      if lv in (2,3) and idx(a) > idx(b): lv = 5 - lv      # 2<->3 镜像

  两个 setter (注意: 真实入口在 nop 滑橇之后):
  0x49fe40  set_diplomacy(a, b, v)     -> rec[0] = old ^ ((v ^ old) & 7)
  0x49ff10  set_master_vassal(a, b, v) -> 先做与 getter 相同的 2<->3 镜像,
                                          再 rec[0] = (rec[0] & 0xE7) | ((v&3) << 3)
                                          (0xE7 = ~0x18, 即清 bit3-4)
      ★ 两者都用「异或掩码」惯用法只改自己的位域, 互不影响。

--------------------------------------------------------------------------
2. 目标国可派筛选 (0x4c4270, 参数 di = 0/1/2)
--------------------------------------------------------------------------
  遍历 0x5179b8 全部 49 国, 跳过自身与国主无效者 (word[+4] >= 370),
  再按 mode 过滤 —— 注意过滤用的是【主从関係】而非外交関係:

      mode 0 (高压外交) : 接受 主从 ∉ {2 从属, 3 支配}
      mode 1 (友好外交) : 接受 主从 == 0 (空白)
      mode 2 (收集情报) : 无条件接受

  命中的国指针写入 [0x517848] 数组, 返回候选数。

--------------------------------------------------------------------------
3. 关系变更的两处已知写入点
--------------------------------------------------------------------------
  0x4c2e4e  关系初始化: 与所有有效国 set_diplomacy(3=普通) + set_master_vassal(0=空白);
                        与特定国 set_diplomacy(6=绝交)
  0x4c7734  势力灭亡:   对每个有效国 p (跳过灭亡方与国 #24),
                        若 主从(p, x)==0 且 外交(p, x) < 7:
                            set_diplomacy(p, x, 外交(p, x) + 1)     # ★ 恶化一级

--------------------------------------------------------------------------
4. 使者归还结算 (0x4b8f70 -> 0x4b91d0 -> 0x4b9228 -> 0x4b9250)
--------------------------------------------------------------------------
  武将实体 (stride 47) 字段:
      +0x16  byte : bit6-7 = 状态 (1=工作完了待报告), bit0-5 = 工作指令码
      +0x17  byte : 目标国索引
      +0x18  word : 值 / 数量
  工作指令码由 0x4c5699（工作指令生成）写入:
      高压外交=10, 友好外交=9, 谋略=13, 收集情报=12, 朝廷工作=11,
      卖出军粮=2, 购入军粮=3, 购入军马=4, 购入洋枪=5, ...

  0x4b9250 结算主分派:
      idx = work - 2; if idx > 0x2c -> 默认 handler
      jmp [ byte[0x4b985c + idx] * 4 + 0x4b981c ]     # 16 项

  work -> handler -> 功勋(ebx):
      2  0x4b9298  msg 0x922 卖出军粮   merit = val*2 + 50
      3  0x4b92cc  msg 0x923 购入军粮   merit = val*2 + 50
      4  0x4b9307  msg 0x924 购入军马   merit = val*4 + 100
      5  0x4b933c  msg 0x925 购入洋枪
      6  0x4b9370  msg 0x926/0x927 开垦农田
      7  0x4b93e8  msg 0x928/0x929 筑城
      8  0x4b945a  -
      9  0x4b94ac  msg 0x92b ★友好外交「进贡使者完成」  merit = 600
     10  0x4b94f4  msg 0x92c ★高压外交「使屈服成功」    merit = 1000
     11  0x4b953c  msg 0x92d/0x92e 朝廷工作  merit = 800(无官位) / 1000(得官位)
     12  0x4b956e  msg 0x92a 收集情报      merit = 城数*(lv+5) + 100   ★判定式
     13  0x4b960e  msg 0x92f-0x932 谋略(拉拢武将)
     18  0x4b96a6  msg 0x935 训练
     41,42 0x4b9742 -
     46  0x4b9713  msg 0x936/0x937 武者修行
      其余 0x4b9776 默认

  ★ 收集情报/外交判定式 (0x4b95a9..0x4b95f3):
        lv    = min( (general[0x10] & 3) + (general[0x0d] / 20) + 1, 7 )
        merit = count_cities(target_prov) * (lv + 5) + 100
    其中 count_cities = 0x4d9e50(prov) —— 遍历 prov[0] 链表 (node = node[+4]) 计数,
    即目标势力的【城数/据点数】。
    (除数 20 由 magic 0x66666667 + sar 3 实测确认, 非 10。)

  共通尾 0x4b97a8:
      if (extra_flag) { 0x4b3040(gen); 0x495920(gen, 7, 0x33); 音效 0x1ff }
      if (0x4b9ae0(player, gen, merit) == 0) {
          msg 0x905 (嗯，太好了。) -> 玩家
          msg 0x906 (是！)         -> 武将
          0x4b9890(gen, merit)     # ★ 功勋加算
      }

--------------------------------------------------------------------------
5. 🔴 对续89 的纠偏
--------------------------------------------------------------------------
  续89 称「0x525ea4 = 存使者对象」。实为【目标国指针】:
      - 0x4c4270 把【国指针】填入 [0x517848]
      - 0x4c41e0 取回后 mov [0x525ea4], esi
      - 0x4c5699 里 (a) mov ax,[edx+4] 取国主ID 换名, (b) (ptr-0x5179b8)/14 求国索引
        两种用法都只在「国指针」下自洽。
  使者槽是 0x525ea0 (基准 0x51eb88, stride 31)。
"""

# ------------------------------------------------------------------ 常量 ----
PROV_TBL = 0x5179B8          # 国政治表, stride 14, 49 条
PROV_STRIDE = 14
N_PROV = 49
INVALID = 0x31               # 49 = 无效国索引

REL_MATRIX = 0x51DC60        # 关系矩阵, 1176 B
REL_MATRIX_RAW = 0x51DC5F    # 代码里 lea 用的基址 ( = REL_MATRIX - 1 )
REL_MATRIX_N = 49 * 48 // 2  # 1176

NAME_TBL = 0x5080D0          # stride 5, 12 项
NAME_STRIDE = 5
DIPL_COLOR_TBL = 0x503E68    # word[8]
MV_COLOR_TBL = 0x503E78      # word[4]

# 外交関係 8 级 (bit0-2) —— 名称表 index 0..7
DIPL_NAMES = ["盟友", "亲密", "良好", "普通", "敌视", "险恶", "绝交", "交战"]
# 主从関係 4 级 (bit3-4) —— 名称表 index 8..11
MV_NAMES = ["", "同盟", "从属", "支配"]

DIPL_COLOR = [0x0001, 0x0001, 0x0000, 0x0000, 0x0000, 0x0002, 0x0002, 0x0002]
MV_COLOR = [0x0000, 0x0004, 0x0002, 0x0001]

# 语义常量
DIPL_NEUTRAL = 3             # 普通 (初始化值)
DIPL_SEVERED = 6             # 绝交
DIPL_WAR = 7                 # 交战 (恶化上限)
MV_NONE = 0                  # 空白
MV_ALLY = 1                  # 同盟
MV_VASSAL = 2                # 从属
MV_DOMINION = 3              # 支配

# ------------------------------------------------------------------ 工具 ----
def prov_index(ptr: int) -> int:
    """国指针 -> 索引。0 表示空指针 -> INVALID(49)。"""
    if ptr == 0:
        return INVALID
    return (ptr - PROV_TBL) // PROV_STRIDE


def prov_ptr(idx: int) -> int:
    """国索引 -> 指针。无效返回 0。"""
    if idx is None or idx >= N_PROV or idx < 0:
        return 0
    return PROV_TBL + idx * PROV_STRIDE


def tri_index(i: int, j: int) -> int:
    """标准上三角序号 (i < j)。"""
    return i * N_PROV - i * (i + 1) // 2 + (j - i - 1)


def rel_offset(i: int, j: int) -> int:
    """0x49fd80 的返回值: 关系记录地址。非法返回 0。"""
    if i >= N_PROV or j >= N_PROV or i == j:
        return 0
    if i > j:
        i, j = j, i
    return REL_MATRIX + tri_index(i, j)


def rel_lookup(a_ptr: int, b_ptr: int) -> int:
    return rel_offset(prov_index(a_ptr), prov_index(b_ptr))


# -------------------------------------------------------------- 位域存取 ----
class RelMatrix:
    """关系矩阵的内存模型 (1176 字节)。"""

    def __init__(self, size: int = REL_MATRIX_N):
        self.buf = bytearray(size)

    # -- 内部 ----------------------------------------------------------
    def _rec(self, i, j):
        off = rel_offset(i, j)
        if off == 0:
            return None
        return off - REL_MATRIX

    # -- 外交関係 8 级 (bit0-2) ----------------------------------------
    def get_diplomacy(self, i: int, j: int) -> int:
        """0x49fd60"""
        r = self._rec(i, j)
        return 0 if r is None else (self.buf[r] & 7)

    def set_diplomacy(self, i: int, j: int, v: int) -> None:
        """0x49fe40 —— 只改 bit0-2。"""
        r = self._rec(i, j)
        if r is None:
            return
        old = self.buf[r]
        self.buf[r] = (old ^ ((v ^ old) & 7)) & 0xFF

    # -- 主从関係 4 级 (bit3-4), 带 2<->3 镜像 --------------------------
    @staticmethod
    def _mirror(v: int, i: int, j: int) -> int:
        if v in (2, 3) and i > j:
            return 5 - v
        return v

    def get_master_vassal(self, i: int, j: int) -> int:
        """0x49fe70"""
        r = self._rec(i, j)
        if r is None:
            return 0
        lv = (self.buf[r] >> 3) & 3
        return self._mirror(lv, i, j)

    def set_master_vassal(self, i: int, j: int, v: int) -> None:
        """0x49ff10 —— 只改 bit3-4 (掩码 0xE7)。"""
        r = self._rec(i, j)
        if r is None:
            return
        v = self._mirror(v & 3, i, j)
        self.buf[r] = ((self.buf[r] & 0xE7) | ((v & 3) << 3)) & 0xFF

    # -- 名称 ----------------------------------------------------------
    def dipl_name(self, i: int, j: int) -> str:
        return DIPL_NAMES[self.get_diplomacy(i, j)]

    def mv_name(self, i: int, j: int) -> str:
        return MV_NAMES[self.get_master_vassal(i, j)]


# ------------------------------------------------------ 目标国可派筛选 ----
def can_dispatch(mode: int, mv_rel: int) -> bool:
    """0x4c4270 的过滤。mode: 0=高压外交 1=友好外交 2=收集情报"""
    if mode == 0:
        return mv_rel not in (MV_VASSAL, MV_DOMINION)
    if mode == 1:
        return mv_rel == MV_NONE
    if mode == 2:
        return True
    return False


# ---------------------------------------------------------- 关系变更点 ----
def init_relations(m: RelMatrix, my: int, others, foe=None) -> None:
    """0x4c2e4e —— 与所有国设为普通/无主从; 与 foe 设为绝交。"""
    for j in others:
        if j == my:
            continue
        m.set_diplomacy(my, j, DIPL_NEUTRAL)
        m.set_master_vassal(my, j, MV_NONE)
    if foe is not None:
        m.set_diplomacy(my, foe, DIPL_SEVERED)


def worsen_on_conquest(m: RelMatrix, conqueror: int, alive, skip=(24,)) -> list:
    """0x4c7734 —— 势力灭亡: 关系恶化一级。返回被变更的国索引列表。"""
    changed = []
    for p in alive:
        if p == conqueror or p in skip:
            continue
        if m.get_master_vassal(p, conqueror) != MV_NONE:
            continue
        cur = m.get_diplomacy(p, conqueror)
        if cur >= DIPL_WAR:
            continue
        m.set_diplomacy(p, conqueror, cur + 1)
        changed.append((p, cur, cur + 1))
    return changed


# ------------------------------------------------------ 工作结算 / 功勋 ----
def mission_level(general: dict) -> int:
    """0x4b95a9..0x4b95d8 —— lv = min((g[0x10]&3) + g[0x0d]/20 + 1, 7)"""
    lv = (general.get(0x10, 0) & 3) + (general.get(0x0D, 0) // 20) + 1
    return min(lv, 7)


def intel_merit(general: dict, city_count: int) -> int:
    """0x4b95ea..0x4b95f3 —— 收集情报功勋 = 城数*(lv+5) + 100"""
    return city_count * (mission_level(general) + 5) + 100


MERIT_FIXED = {
    9: 600,      # 友好外交
    10: 1000,    # 高压外交
}
MERIT_COURT_NO_RANK = 800
MERIT_COURT_RANK = 1000

# work 指令码 -> (handler, msg, 说明)
WORK_SETTLE = {
    2: (0x4B9298, 0x922, "卖出军粮"),
    3: (0x4B92CC, 0x923, "购入军粮"),
    4: (0x4B9307, 0x924, "购入军马"),
    5: (0x4B933C, 0x925, "购入洋枪"),
    6: (0x4B9370, 0x926, "开垦农田"),
    7: (0x4B93E8, 0x928, "筑城"),
    8: (0x4B945A, None, "-"),
    9: (0x4B94AC, 0x92B, "友好外交"),
    10: (0x4B94F4, 0x92C, "高压外交"),
    11: (0x4B953C, 0x92D, "朝廷工作"),
    12: (0x4B956E, 0x92A, "收集情报"),
    13: (0x4B960E, 0x92F, "谋略"),
    18: (0x4B96A6, 0x935, "训练"),
    41: (0x4B9742, None, "-"),
    42: (0x4B9742, None, "-"),
    46: (0x4B9713, 0x936, "武者修行"),
}
DEFAULT_HANDLER = 0x4B9776

WORK_ORDER = {          # 0x4c5699 生成的指令码 (写入 武将+0x16 低6位)
    "高压外交": 10, "友好外交": 9, "谋略": 13, "收集情报": 12,
    "朝廷工作": 11, "卖出军粮": 2, "购入军粮": 3, "购入军马": 4,
    "购入洋枪": 5,
}


def settle_handler(work: int) -> int:
    """0x4b9289..0x4b9291"""
    idx = work - 2
    if idx < 0 or idx > 0x2C:
        return DEFAULT_HANDLER
    return WORK_SETTLE.get(work, (DEFAULT_HANDLER,))[0]


# ================================================================= 自检 ----
def _run_tests():
    ok = total = 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
        else:
            print(f"  [FAIL] {name}")

    # --- 地址换算 -----------------------------------------------------
    check("prov_index(0x5179b8)==0", prov_index(0x5179B8) == 0)
    check("prov_index(0)==49 (NULL)", prov_index(0) == INVALID)
    check("prov_index(+14)==1", prov_index(PROV_TBL + 14) == 1)
    check("prov_ptr(48) 回环", prov_index(prov_ptr(48)) == 48)
    check("prov_ptr(49)==0 (无效)", prov_ptr(49) == 0)

    # --- 三角矩阵 -----------------------------------------------------
    check("矩阵尺寸 1176", REL_MATRIX_N == 1176)
    check("tri(0,1)==0", tri_index(0, 1) == 0)
    check("tri(0,48)==47", tri_index(0, 48) == 47)
    check("tri(1,2)==48", tri_index(1, 2) == 48)
    # 与汇编偏移对齐: lea eax,[edi + 0x51dc5f] == REL_MATRIX + tri
    for i in range(0, 20):
        for j in range(i + 1, 49, 7):
            asm_off = j + (48 * i - i * (i - 1) // 2) - i
            check(f"asm对齐 ({i},{j})", REL_MATRIX_RAW + asm_off == REL_MATRIX + tri_index(i, j))
    check("rel_offset 对称", rel_offset(3, 7) == rel_offset(7, 3))
    check("rel_offset 自身=0", rel_offset(5, 5) == 0)
    check("rel_offset 越界=0", rel_offset(49, 1) == 0)

    # --- 位域 get/set -------------------------------------------------
    m = RelMatrix()
    m.set_diplomacy(1, 5, DIPL_SEVERED)          # 6
    check("set/get 外交=6", m.get_diplomacy(1, 5) == 6)
    m.set_master_vassal(1, 5, MV_DOMINION)       # 3
    check("主从与外交互不干扰(外交仍6)", m.get_diplomacy(1, 5) == 6)
    check("get 主从(1,5)=3", m.get_master_vassal(1, 5) == 3)
    # 镜像: (5,1) 应看到 2
    check("主从镜像 (5,1)=2", m.get_master_vassal(5, 1) == MV_VASSAL)
    check("主从镜像 (1,5)=3", m.get_master_vassal(1, 5) == MV_DOMINION)
    m.set_diplomacy(1, 5, 2)
    check("改外交后主从仍在", m.get_master_vassal(1, 5) == 3)
    # round-trip: set 用镜像, get 也用镜像 -> 一致
    for v in (0, 1, 2, 3):
        m.set_master_vassal(2, 9, v)
        check(f"主从 round-trip v={v}", m.get_master_vassal(2, 9) == v)
        check(f"主从 round-trip 反向 v={v}", m.get_master_vassal(9, 2) == (5 - v if v in (2, 3) else v))
    # 镜像只对 2/3 生效
    m.set_master_vassal(9, 2, MV_ALLY)
    check("主从=1 不镜像", m.get_master_vassal(2, 9) == MV_ALLY)
    # 掩码 0xE7 验证: 高 3 位不受影响
    m.buf[m._rec(0, 1)] = 0xE0
    m.set_master_vassal(0, 1, MV_VASSAL)
    check("set主从保留 bit5-7", (m.buf[m._rec(0, 1)] & 0xE0) == 0xE0)

    # --- 名称 ---------------------------------------------------------
    check("DIPL_NAMES 8项", len(DIPL_NAMES) == 8)
    check("MV_NAMES 4项", len(MV_NAMES) == 4)
    check("名称表 12 项 = 8+4", len(DIPL_NAMES) + len(MV_NAMES) == 12)
    check("名称表跨度", 12 * NAME_STRIDE == (0x5080F8 - 0x5080D0) + 4 * NAME_STRIDE)

    # --- 可派筛选 -----------------------------------------------------
    check("高压: 空白可派", can_dispatch(0, MV_NONE) is True)
    check("高压: 同盟可派", can_dispatch(0, MV_ALLY) is True)
    check("高压: 从属不可派", can_dispatch(0, MV_VASSAL) is False)
    check("高压: 支配不可派", can_dispatch(0, MV_DOMINION) is False)
    check("友好: 仅空白", can_dispatch(1, MV_NONE) is True and
          can_dispatch(1, MV_ALLY) is False)
    check("情报: 无条件", all(can_dispatch(2, v) for v in (0, 1, 2, 3)))

    # --- 关系变更 -----------------------------------------------------
    m2 = RelMatrix()
    init_relations(m2, 0, range(1, 49), foe=7)
    check("初始化 与1 普通", m2.get_diplomacy(0, 1) == DIPL_NEUTRAL)
    check("初始化 主从空白", m2.get_master_vassal(0, 1) == MV_NONE)
    check("初始化 与7 绝交", m2.get_diplomacy(0, 7) == DIPL_SEVERED)
    check("初始化 自身未写", rel_offset(0, 0) == 0)

    m3 = RelMatrix()
    init_relations(m3, 0, range(1, 49))
    ch = worsen_on_conquest(m3, 0, range(1, 49))
    check("灭亡恶化 全 47 国", len(ch) == 47)
    check("灭亡恶化 +1 级", m3.get_diplomacy(1, 0) == DIPL_NEUTRAL + 1)
    check("灭亡恶化 跳过 #24", all(p != 24 for p, _, _ in ch))
    # 已交战不再恶化
    m3.set_diplomacy(5, 0, DIPL_WAR)
    before = m3.get_diplomacy(5, 0)
    worsen_on_conquest(m3, 0, [5])
    check("已交战不恶化", m3.get_diplomacy(5, 0) == before)
    # 已有主从关系不恶化
    m3.set_master_vassal(6, 0, MV_VASSAL)
    before = m3.get_diplomacy(6, 0)
    worsen_on_conquest(m3, 0, [6])
    check("有主从不恶化", m3.get_diplomacy(6, 0) == before)

    # --- 工作结算 -----------------------------------------------------
    check("settle 高压外交", settle_handler(10) == 0x4B94F4)
    check("settle 友好外交", settle_handler(9) == 0x4B94AC)
    check("settle 越界->默认", settle_handler(99) == DEFAULT_HANDLER)
    check("settle work=1 ->默认", settle_handler(1) == DEFAULT_HANDLER)
    check("指令码 高压=10", WORK_ORDER["高压外交"] == 10)
    check("指令码 友好=9", WORK_ORDER["友好外交"] == 9)
    check("功勋 友好=600", MERIT_FIXED[9] == 600)
    check("功勋 高压=1000", MERIT_FIXED[10] == 1000)

    # --- 判定式 (除数 20) ---------------------------------------------
    check("lv 下限 {0x10:0,0x0d:0} ->1", mission_level({0x10: 0, 0x0D: 0}) == 1)
    check("lv 除以20 (0x0d=19->0)", mission_level({0x10: 0, 0x0D: 19}) == 1)
    check("lv 除以20 (0x0d=20->1)", mission_level({0x10: 0, 0x0D: 20}) == 2)
    check("lv 除以20 (0x0d=100->5)", mission_level({0x10: 0, 0x0D: 100}) == 6)
    check("lv &3 掩码", mission_level({0x10: 0xFF, 0x0D: 0}) == 4)
    check("lv cap 7", mission_level({0x10: 3, 0x0D: 200}) == 7)
    check("情报功勋 基础", intel_merit({0x10: 0, 0x0D: 0}, 1) == 1 * (1 + 5) + 100)
    check("情报功勋 城数缩放", intel_merit({0x10: 0, 0x0D: 0}, 10) == 10 * 6 + 100)
    check("情报功勋 lv 缩放", intel_merit({0x10: 3, 0x0D: 100}, 5) == 5 * (7 + 5) + 100)

    print(f"\nRESULT: {ok}/{total} checks passed")
    return ok == total


if __name__ == "__main__":
    _run_tests()
