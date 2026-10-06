# -*- coding: utf-8 -*-
"""verify_children.py —— M2/M3 儿童系统静态验收 (只读 big.exe, 不开游戏)

游戏里怎么测由人来做; 这里只保证「exe 里的字节就是我们打算写的那些」并给出可对照的预期值:
  C1 桩字节   : 用 child_stub.build() 现场重装配, 与 .edata 里 CHILD_PASS_VA 处逐字节比对
  C2 入口      : 直接对 exe 字节反汇编, 重取 child_pass/month_hook/load_hook 三个入口
  C3 钩子      : 两个站点 = E8 rel32 指向各自钩子; 钩子里 jmp 回原 callee
  C4 排程表    : 8B/条 (oid,slot,fslot,国,城) —— 由 _child_preload × _kin 现场重算后逐字节比对
  C5 槽合法    : 扩展槽(>=N0) / 不踩 4i 待登场区 / 静态 0x808F / 两姓名表位全 0
  C6 记账区    : 位图全 0, 六个埋点计数器全 0
  C7 INST 通道 : 0x47F7B0 序言/尾声完好, 且它写姓名/实体用的位移常量确实已被 P3a/P1 搬到新家
  C8 R1 界     : 0x4A4F1A cmp si == CAP (扩展槽被武装时 0x4A4FC0 不会收到 NULL 实体)
  C9 原语未动  : 配方用到的 6 个原生访问器与 clean_dump 一致
  C10 极性+模型: 用 ents_dump(真机) 证明 0x521AA8=姓表 / 0x520660=名表, 且 实体[2..47)==记录[14..59);
                 据此预测每个孩子预载后的 全名/年龄/状态字, 供 tkwatch 逐位对照
  C11 P3b 配对 : 休眠名预填要落在 C10 认定的姓表/名表里
  ---- M3a 随父居住 / 亲子索引 ----
  C12 kin 自洽 : _kin.json 的 S1 定位常量与本次独立重抽一致; oid->槽 表一致; 空槽恰为待登场区
  C13 游标前进 : exe 字节里 `add ebx, ESZ` 恰 1 条且紧跟唯一回边到循环头 (漏了就是载入即死循环)
  C14 place    : place_child 形态齐 —— 读 fslot/兜底城、父在场判定、+0x24 两处写、PLACE 埋点两处
  C15 语义     : 逐条重算 父 oid(BSDATA u16@+0x29) 与落点城(父在池=父的 S1 国/城; 不在池=父的 BSDATA;
                 不明其父或开关关=孩子自己), 与 exe 表项逐字段对上
  ---- M3b 私有区 + 成长结算 ----
  C16 区域     : MOD 私有区圈地干净(互不重叠/在 .edata 内/顺序单调), 成长埋点与数据区开局全 0
  C17 成长桩   : child_growth.py 现场重装配与 exe 逐字节一致; 月钩=预载+成长两段 call(17B),
                 载入钩(历史名, 实为保存侧钩)只调预载(12B, 存/读不会多算一跳); 月守卫/档位/天花板/写手/游标形态齐; 50% 起步已接上
  C18 成长预期 : 用与桩同语义的参考实现逐人算出 起步五维 -> 元服时五维/第几个月加第一点
  ---- M3b-3 培养指令 (CMD_RING 消费 + 成效公式) ----
  C20 常数表   : ACT_TAB/TEACH_TAB 落盘字节 = child_growth 定义, 且桩里的活动/教席上界 = 表长
  C21 公式     : 桩里的每个常数都能从 exe 字节反查到 (P0/T/B/亲密/现值/夹区间/硬顶), 掷骰走原生 rand,
                 Python 参考实现全枚举不越界 + 四向单调
  C22 队列     : CMD_RING 头尾开局相等(空队)、条目区全 0、桩只写 head 只读 tail (tail 留给 M3c 的 UI),
                 消费前的五道门各恰 1 处, 五个培养埋点互不重号
  ---- M3c 回家菜单「培养孩子」 ----
  C23 三处补丁 : 0x4CD563 钩子 jmp / 0x4CD390 cmp 6->7 / 0x4CD47C 表槽 7 -> 培养处理;
                 两块桩逐字节复现, 原生 7 个处理与表 0..6 槽对 clean 一字未改,
                 串池/DEC100/三级子菜单指针数组 = child_menu 定义, 面板埋点各恰 1 处
  C23r 回环    : 用 exe 里的钩子字节+跳转表+调用方预判, 对「全在6/金库隐藏5/无宁宁无探病3/最短2」
                 四种形态逐 pick 算出回到调用方的 eax 与最终处理地址: 原生项必落原生处理,
                 末项必落 0x550F90, 取消必出环
  C23s~x 对偶  : 面板的三道资格门/47*槽地址式/圈条目偏移/tail 读写约束 全部与成长桩同一条指令 —— 
                 面板能选到的孩子 == 桩会消费的孩子, 选到的指令 == 桩读得懂的指令
  ---- M6 sidecar 影子存档 ----
  C24 影子档   : 桩 881B 逐字节复现 + 两个 trampoline 形态(顶替链尾 call 0x47D850 并回跳 site+5);
                 两处派发器钩对 clean 逐字节核验后 = jmp; SC_DATA 里 路径/六段描述符/47B 归零模板
                 内容重算吻合(模板与池里扩展槽同一具身体); 头部 7 个定值字段"写了就比"两头同值,
                 动态两字段 SLOT/DIGEST 各写 1 次再读回比; 写循环只经 _lwrite、读循环只经 _lread
                 且共用同一张表; 摘要只有一份实现、两个方向各 call 它一次; 9 个 SIDECAR_* 埋点处数与语义对得上

输出: _verify_children.txt (UTF-8, 明细) + 控制台小结
"""
import json, os, re, struct, sys, pathlib

import capstone

ROOT = pathlib.Path(__file__).resolve().parent.parent
REV = ROOT / '.rev'
sys.path.insert(0, str(REV))
import child_stub as CS
import child_growth as CG

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

LY = json.load(open(REV / '_big_layout.json', encoding='utf-8'))
V = LY['v']
BATCH = os.environ.get('CHILD_BATCH', 'fam13')
PRE = json.load(open(REV / '_child_preload.json', encoding='utf-8'))
ENTRIES = PRE['batches'][BATCH]
META = PRE['meta']
def eng_age(birth):
    """年龄口径唯一真源: 引擎 getter 0x49A5C0 返回 当前年 - 生年 + 1 (虚岁)。
    桩里的档位选择与 >=15 冻结都吃这个返回值, 期望表若写成 年-生年 就整体偏小一岁。"""
    return META['start_year'] - birth + 1


# 开局日历月: 决定「第几个月涨一岁」(虚岁在新年 +1), 因而影响逐月档位轨迹。
# 未从运行时确认前按 1 月建表; 实机用 tkwatch 读 byte[0x5205F1] 后可 TKID_START_MONTH=N 重跑。
START_MONTH = int(os.environ.get('TKID_START_MONTH', '1'))


KIN = json.load(open(REV / '_kin.json', encoding='utf-8'))       # M3a 亲子索引 (gen_kin.py)
FOLLOW = LY.get('child_follow_father', True)                      # 随父居住开关 (build 时定的)

POOL, STRIDE, CAP, N0 = LY['pool_va'], LY['stride'], LY['cap'], LY['n0']
RES_LO, RES_N = LY['reserve_lo'], LY['reserve_n']
GIVT, SURT = LY['given_tab_va'], LY['surname_tab_va']       # 名表 / 姓表 (真值)
PASS = V['CHILD_PASS']
BM, SCHED = V['CHILD_BM'], V['CHILD_SCHED']
CNT = {k: V[k] for k in ('CHILD_PRELOAD', 'CHILD_REARM', 'CHILD_GENPUKU', 'CHILD_SCAN',
                         'CHILD_SKIP', 'CHILD_PLACE', 'CHILD_INIT5')}
GCV = V['CHILD_GROWTH']                          # 成长桩入口
GC = LY['growth_ctrs']                           # 20 个 4B 成长埋点 (名字->VA)


def sched_entries():
    """按 build_big 4j 的规则从两份 json 独立重算 8B 表项 (不采信构建产物)"""
    kp = {o: s for o, s in KIN['batches'][BATCH]}
    out = []
    for e in ENTRIES:
        assert kp.get(e['oid']) == e['slot'], ('kin 与 preload 的槽不符', e['oid'])
        k = KIN['kin'][str(e['oid'])]
        fslot, pv, city = ((k['fslot'], k['pv'], k['city']) if FOLLOW
                           else (CS.TERM, k['self_pv'], k['self_city']))
        out.append(dict(e, fslot=fslot, pv=pv, city=city))
    return out

R, NREC, RBLK = 59, 700, 1560
BSD = open(ROOT / 'BSDATA1.TR2.orig', 'rb').read()
CLN = open(REV / 'clean_dump.bin', 'rb').read()           # 原 exe 镜像, off = va - 0x400000
CB = 0x400000
OUT = open(REV / '_verify_children.txt', 'w', encoding='utf-8')
FAIL = []


def w(*a):
    print(*a, file=OUT)


def check(name, ok, detail=''):
    w('%-4s %s %s' % ('OK' if ok else 'FAIL', name, detail))
    if not ok:
        FAIL.append(name)
    return ok


def gbk(b):
    return b.split(b'\0')[0].decode('gbk', 'replace')


def u16r(b, o):
    return struct.unpack_from('<H', b, o)[0]


def rec(oid):
    return BSD[oid * R:oid * R + R]


EXE_NAME = os.environ.get('TKID_EXE', 'TAIK2W95_big.exe')   # 试演档(分页)用 TKID_EXE 指到自己的 exe
d = open(ROOT / EXE_NAME, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
SECS = {}
for i in range(struct.unpack_from('<H', d, pe + 6)[0]):
    o = pe + 24 + opt + i * 40
    nm = d[o:o + 8].rstrip(b'\x00').decode()
    vsz = struct.unpack_from('<I', d, o + 8)[0]
    va, rawsz, raw = struct.unpack_from('<III', d, o + 12)
    SECS[nm] = (0x400000 + va, vsz, rawsz, raw)
w('%s %dB  分区 %s' % (EXE_NAME, len(d), {k: ('0x%06X' % v[0], '0x%X' % v[1]) for k, v in SECS.items()}))


def rd(secnm, va, n):
    sva, vsz, rawsz, raw = SECS[secnm]
    assert sva <= va < sva + max(vsz, rawsz), (secnm, hex(va))
    off = raw + (va - sva)
    assert off + n <= len(d), '越出文件 %s+%d' % (hex(off), n)
    return d[off:off + n]


T = lambda va, n: rd('.text', va, n)
E = lambda va, n: rd('.edata', va, n)


def AT(va, n):
    """按 VA 自己找分区: 0x4C4000 之后(含整个回家菜单 0x4CD339/0x4CD480 与菜单串表 0x50CAE8)
    在本 exe 里属于 **.data** 而不是 .text —— 拿 T() 读会直接断言炸, 别照着"代码在 .text"想当然。"""
    for nm, (sva, vsz, rawsz, raw) in SECS.items():
        if sva <= va < sva + max(vsz, rawsz):
            return rd(nm, va, n)
    raise KeyError('不在任何分区: %08X' % va)


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

w('\n批次 %s = %d 人 (槽 %d..%d) ; 基数 在场%d/未登场%d/已出生未登场%d/儿童%d' %
  (BATCH, len(ENTRIES), ENTRIES[0]['slot'], ENTRIES[-1]['slot'], META['live_in_scenario'],
   META['unappeared'], META['born_unappeared'], META['children']))

# ---------------- C10 先跑: 极性 + 记录->实体模型 (后面两项要用它) ----------------
w('\n--- C10 姓名表极性 / 记录->实体 线性模型 (真机 ents_dump 反证) ---')
ents = json.load(open(REV / 'ents_dump.json', encoding='utf-8'))
flags = open(ROOT / 'SNDATA1.TR2', 'rb').read()[0x14:0x14 + NREC]
live = [i for i in range(NREC) if flags[i]]
pol_a = pol_b = 0          # tabA(0x520660)=名 命中 / tabB(0x521AA8)=姓 命中
off_bad = {}               # 实体偏移 -> 与「记录同偏移-12」不符的槽数
mod_ent = mod_bad = 0
for k in range(min(370, len(live))):
    oid, e = live[k], ents[k]
    f0, f1 = gbk(rec(oid)[0:7]), gbk(rec(oid)[7:14])
    if e['given'] == f1:
        pol_a += 1
    if e['surname'] == f0:
        pol_b += 1
    raw = bytes.fromhex(e['raw'])
    same = 0
    for i in range(8, 47):
        if raw[i] == rec(oid)[i + 12]:
            same += 1
        else:
            off_bad[i] = off_bad.get(i, 0) + 1
    if same == 39:
        mod_ent += 1
    else:
        mod_bad += 1
w('槽 k 对应第 k 个在场 oid; 真机 0x520660 槽内容==记录[7:14](名) 命中 %d/%d ; '
  '0x521AA8==记录[0:7](姓) 命中 %d/%d' % (pol_a, len(live), pol_b, len(live)))
check('C10a 极性: 0x520660=名表 且 0x521AA8=姓表', pol_a >= len(live) * 0.9 and pol_b >= len(live) * 0.9)
check('C10b 搬迁映射: given_tab_va<-0x520660, surname_tab_va<-0x521AA8',
      GIVT == LY['sur_va'] and SURT == LY['giv_va'],
      '名表 0x%06X / 姓表 0x%06X' % (GIVT, SURT))
w('INST 拷贝模型 实体[8..47) == 记录[20..59) (即 ent[k]=rec[k+12]): 全符 %d 槽 / 有差 %d 槽' %
  (mod_ent, mod_bad))
w('  偏差集中在(实体偏移: 不符槽数): %s' %
  ', '.join('+0x%02x:%d' % (i, n) for i, n in sorted(off_bad.items(), key=lambda x: -x[1])[:10]))
w('  说明: 存档 dump 是引擎跑完初始化之后的样子, 个别字节(如状态高字节/主君)被后续逻辑改过是正常的。')
tot = sum(off_bad.values())
check('C10c 模型: 39 个字段里绝大多数逐槽吻合 (偏差率 %.1f%%)' % (100.0 * tot / (39 * len(live))),
      tot <= 0.10 * 39 * len(live))
check('C10d 状态字来源就是记录 +0x38/+0x39 (实例化即拷贝, 之后引擎会再改几个位)',
      off_bad.get(0x2c, 0) <= len(live) * 0.05 and off_bad.get(0x2d, 0) <= len(live) * 0.10,
      '+0x2c 偏 %d 槽 / +0x2d 偏 %d 槽 (共 %d 槽)'
      % (off_bad.get(0x2c, 0), off_bad.get(0x2d, 0), len(live)))

# ---------------- C1 桩字节 ----------------
w('\n--- C1 桩字节逐位复现 ---')
CL = {'pool': POOL, 'sched': SCHED, 'bm': BM, 'preload': CNT['CHILD_PRELOAD'],
      'rearm': CNT['CHILD_REARM'], 'scan': CNT['CHILD_SCAN'], 'skip': CNT['CHILD_SKIP'],
      'place': CNT['CHILD_PLACE'], 'init5': CNT['CHILD_INIT5'], 'growth': GCV}
ccode, cva, csrc, cins = CS.build(PASS, CL)
got = E(PASS, len(ccode))
check('C1 桩 %dB 与 build() 一致' % len(ccode), bytes(got) == ccode,
      'child_pass@0x%06X month@0x%06X load@0x%06X' % (cva['child_pass'], cva['month_hook'], cva['load_hook']))

# ---------------- C2 入口(独立反汇编 exe 字节) ----------------
w('\n--- C2 入口再定位 (只读 exe 字节) ---')
e2 = CS.entry_vas(bytes(got), PASS)
check('C2 入口与布局一致', all(e2[k] == cva[k] for k in ('child_pass', 'month_hook', 'load_hook')),
      str({k: hex(v) for k, v in e2.items()}))
check('C2b 布局里的三个入口地址 = 重定位结果',
      V['CHILD_PASS'] == cva['child_pass'] and V['CHILD_MONTH_HOOK'] == cva['month_hook']
      and V['CHILD_LOAD_HOOK'] == cva['load_hook'])

# ---------------- C3 钩子 ----------------
w('\n--- C3 两个钩子 ---')
for site, orig, ent, back, tag, hsz in (
        (CS.MONTH_SITE, CS.SITE_ORIG[CS.MONTH_SITE], cva['month_hook'], CS.MONTH_JMP,
         '月/登场例程返回后', cva['month_hook_sz']),
        (CS.LOAD_SITE, CS.SITE_ORIG[CS.LOAD_SITE], cva['load_hook'], CS.LOAD_JMP,
         '保存链尾(历史名"载入钩", 见 child_stub 方向定论)', cva['load_hook_sz'])):
    b5 = bytes(T(site, 5))
    ok = b5[:1] == b'\xE8'
    tgt = site + 5 + struct.unpack_from('<i', b5, 1)[0] if ok else -1
    i = list(md.disasm(b5, site))
    # 钩子体 = pushad(1) + N 个 call rel32(5) + popad(1) + jmp rel32(5): 月钩 N=2(17B), 保存侧钩 N=1(12B)
    hb = bytes(E(ent, hsz))
    hin = list(md.disasm(hb, ent))
    jmps = [x for x in hin if x.mnemonic in ('jmp', 'jb') and x.op_str.startswith('0x')]
    w('  %s 站点 0x%06X 原文 %s -> 现 %s ; 解码 %s %s'
      % (tag, site, orig.hex(), b5.hex(), i[0].mnemonic if i else '?', i[0].op_str if i else ''))
    w('  %s 钩子体 %dB %s : %s' % (tag, hsz, hb.hex(),
                                  ' | '.join('%s %s' % (x.mnemonic, x.op_str) for x in hin)))
    check('C3 %s 站点跳向钩子 0x%06X' % (tag, ent), tgt == ent, '实得 0x%08X' % tgt)
    check('C3 %s 钩子跳回原 callee 0x%06X' % (tag, back),
          any(x.op_str == '0x%x' % back for x in jmps), '体内 jmp %s' % [x.op_str for x in jmps])
    check('C3 %s 站点原文已被替换(不再是不装桩时的 call)' % tag, b5 != orig)
    check('C3 %s 钩子体 %dB = pushad/%s/popad/jmp 且首尾是 pushad+jmp'
          % (tag, hsz, '2 call/' if hsz == 17 else '1 call/'),
          sum(len(x.bytes) for x in hin) == hsz
          and hin[0].mnemonic in CS.PUSHAD_MN and hin[-1].mnemonic == 'jmp'
          and hin[-2].mnemonic in ('popad', 'popal'),
          '%dB 解码 %d 条' % (sum(len(x.bytes) for x in hin), len(hin)))

# ---------------- C4 排程表 ----------------
w('\n--- C4 排程表 (%dB/条: oid, slot, fslot, 国, 城) ---' % CS.ESZ)
SE = sched_entries()
want = CS.sched_bytes(SE)
sb = bytes(E(SCHED, len(want)))
check('C4 排程表 %dB 与 (preload x kin) 重算一致 ; 随父居住=%s' % (len(want), '开' if FOLLOW else '关'),
      sb == want)
rows, o = [], 0
while True:
    if u16r(sb, o) == 0xFFFF:          # 哨兵只有 4B(桩也只看 word[ebx]), 别按整条读出去
        break
    rows.append(struct.unpack_from('<HHHBB', sb, o))
    o += CS.ESZ
check('C4b 条数 %d == 批次 %d, 步长 %d 且末尾哨兵' % (len(rows), len(ENTRIES), CS.ESZ),
      len(rows) == len(ENTRIES) and o == len(rows) * CS.ESZ and sb[-4:] == b'\xff\xff\xff\xff')
check('C4c 排程表不越进桩代码区', SCHED + len(want) <= PASS,
      '0x%06X +%d <= 0x%06X' % (SCHED, len(want), PASS))
_mis = [(a, b['oid'], b['slot']) for a, b in zip(rows, SE)
        if a != (b['oid'], b['slot'], b['fslot'], b['pv'], b['city'])]
check('C4d %d 条逐字段回读全符' % len(rows), not _mis, str(_mis[:4]))

# ---------------- C5 槽 ----------------
w('\n--- C5 预载槽 ---')
bad = []
for e in ENTRIES:
    s = e['slot']
    st = struct.unpack_from('<H', E(POOL + s * STRIDE + 0x2c, 2), 0)[0]
    g7 = bytes(E(GIVT + s * 7, 7))
    u7 = bytes(E(SURT + s * 7, 7))
    inres = RES_LO <= s < RES_LO + RES_N
    ent0 = struct.unpack_from('<H', E(POOL + s * STRIDE, 2), 0)[0]
    if not (N0 <= s < CAP) or inres or st != 0x808F or g7.strip(b'\x00') or u7.strip(b'\x00'):
        bad.append((s, hex(st), g7, u7, inres))
    if s != ent0:
        w('  注: 槽 %d 实体[+0]=%d (P2 静态模板应写槽号本身)' % (s, ent0))
check('C5 %d 个槽全为扩展空槽(0x808F)且两姓名表位全 0' % len(ENTRIES), not bad, str(bad))

# ---------------- C6 记账区 ----------------
w('\n--- C6 记账区 ---')
bm = bytes(E(BM, CAP // 8))
check('C6 位图 %dB 全 0 (开局无认领)' % len(bm), bm == b'\x00' * len(bm))
zero = {}
for k, va in sorted(CNT.items()):
    zero[k] = struct.unpack_from('<I', E(va, 4), 0)[0]
check('C6b %d 个埋点计数器全 0' % len(CNT), all(v == 0 for v in zero.values()), str(zero))
check('C6c GENPUKU 埋点已埋但尚无代码写它(M4 用)',
      struct.unpack_from('<I', E(CNT['CHILD_GENPUKU'], 4), 0)[0] == 0)
for k in ('APPEAR_CNT', 'VACANT_CNT', 'MONTH_CNT', 'ARMED_CNT'):
    w('  (4i) %s @0x%06X = %d' % (k, V[k], struct.unpack_from('<I', E(V[k], 4), 0)[0]))

# ---------------- C7 INST 通道 ----------------
w('\n--- C7 实例化器 0x47F7B0 (预载器唯一的造人入口) ---')
head = list(md.disasm(bytes(T(0x47F7B0, 8)), 0x47F7B0))
check('C7a 序言 mov eax,[esp+8] (取 arg2=oid)',
      head[0].mnemonic == 'mov' and head[0].op_str == 'eax, dword ptr [esp + 8]',
      '%s %s' % (head[0].mnemonic, head[0].op_str))
d_surname = struct.unpack_from('<I', bytes(T(0x47F7F2 + 2, 4)), 0)[0]
d_given = struct.unpack_from('<I', bytes(T(0x47F805 + 2, 4)), 0)[0]
d_pool = struct.unpack_from('<I', bytes(T(0x47F832 + 2, 4)), 0)[0]
w('  0x47F7F2 lea ebx,[esi+0x%X] (姓表) / 0x47F805 lea esi,[esi+0x%X] (名表) / 0x47F832 +0x%X (实体基)'
  % (d_surname, d_given, d_pool))
check('C7b INST 的姓表位移已搬到 %06X' % SURT, d_surname == SURT)
check('C7c INST 的名表位移已搬到 %06X' % GIVT, d_given == GIVT)
check('C7d INST 的实体基位移 = 池基+2 (%06X)' % (POOL + 2), d_pool == POOL + 2)
check('C7e BSDATA 镜像基址 0x524A20 未被搬动',
      struct.unpack_from('<I', bytes(T(0x47F7C7 + 1, 4)), 0)[0] == 0x524A20)
prolog = bytes(T(0x47F7B0, 0x30))
check('C7f INST 前 0x30 字节与 clean 一致(没被别的补丁蹭到)',
      prolog == CLN[0x47F7B0 - CB: 0x47F7B0 - CB + 0x30])

# ---------------- C8 R1 ----------------
w('\n--- C8 R1 槽界 ---')
rb = bytes(T(0x4A4F1A, 5))
bound = struct.unpack_from('<H', rb, 3)[0]
check('C8 0x4A4F1A cmp si, %d == CAP %d' % (bound, CAP), rb[:3] == b'\x66\x81\xfe' and bound == CAP, rb.hex())

# ---------------- C9 配方原语 ----------------
w('\n--- C9 配方用到的原生访问器 (应与 clean_dump 完全一致) ---')
for nm, va in (('INST', CS.INST), ('bit15清', CS.A_BIT15), ('bit7清', CS.A_BIT7CLR),
               ('nibble置', CS.A_NIBSET), ('bit4', CS.A_BIT4), ('rank', CS.A_RANK),
               ('登场登记 0x4A4FC0', 0x4A4FC0)):
    a = bytes(T(va, 24))
    b_ = CLN[va - CB: va - CB + 24]
    check('C9 %-22s @0x%06X 未改' % (nm, va), a == b_, a[:8].hex())
w('  登场标志表 0x519288 未随搬家(在 .data), 桩里用的是原常量 FLAGTAB=0x%X' % CS.FLAGTAB)

# ---------------- C11 P3b 预填配对 ----------------
w('\n--- C11 休眠名预填 (槽 371..462) 是否落在正确的表里 ---')
dorm = json.load(open(REV / '_dormants.json', encoding='utf-8'))
mis = []
for dd in dorm:
    s = dd['slot']
    u7 = gbk(bytes(E(SURT + s * 7, 7)))
    g7 = gbk(bytes(E(GIVT + s * 7, 7)))
    if (u7, g7) != (dd['sur'], dd['giv']):
        mis.append((s, u7, g7, dd['sur'], dd['giv']))
check('C11 %d 个休眠名预填落在「姓表=姓 / 名表=名」' % len(dorm), not mis, str(mis[:6]))

# ---------------- C12..C15 M3a 亲子索引 / 随父居住 ----------------
w('\n--- C12 亲子索引 (_kin.json) 自身对账 ---')
import gen_kin as GK
recs = GK.s1_records(1)
D = GK.bsd(1)
oid2slot = {u16r(recs[i], GK.S1_OID): i for i in range(len(recs)) if u16r(recs[i], GK.S1_OID) != 0xFFFF}
km = KIN['meta']
check('C12a kin 的 S1 定位常量 = %s (本次独立重抽 %d 条)' %
      ({k: hex(km[k]) for k in ('stream_base', 's1_stream_off', 's1_file_off')}, len(recs)),
      (km['stream_base'], km['s1_stream_off'], km['s1_file_off']) == (GK.STREAM_BASE, GK.S1_STREAM_OFF,
                                                                      GK.STREAM_BASE + GK.S1_STREAM_OFF)
      and len(recs) == GK.NAT)
check('C12b 独立重抽的 oid->槽 与 kin 一致 (%d 人)' % len(oid2slot),
      {int(k): v for k, v in KIN['oid2slot'].items()} == oid2slot)
check('C12c 空槽恰为 4i 待登场区 %d..%d' % (RES_LO, RES_LO + RES_N - 1),
      km['empty_slots'] == list(range(RES_LO, RES_LO + RES_N)) and len(oid2slot) == RES_LO)

w('\n--- C13 主循环游标必须前进 (M2 漏过 add ebx => 载入即死循环) ---')
mins = list(md.disasm(bytes(E(PASS, len(ccode))), PASS))
adv = [i for i in mins if i.mnemonic == 'add' and i.op_str == 'ebx, %d' % CS.ESZ]
heads = [i for i in mins if i.mnemonic == 'movzx' and i.op_str.endswith('[ebx]')]
head = min(heads, key=lambda i: i.address) if heads else None
back = [i for i in mins if i.mnemonic == 'jmp' and head and i.op_str == '0x%x' % head.address]
check('C13 add ebx,%d 恰 1 条, 其后紧跟唯一回边 -> 循环头 0x%06X' % (CS.ESZ, head.address if head else 0),
      len(adv) == 1 and len(back) == 1 and back[0].address == adv[0].address + adv[0].size,
      'add@%s back@%s head@%s' % ([hex(i.address) for i in adv], [hex(i.address) for i in back],
                                  hex(head.address) if head else '-'))

w('\n--- C14 place_child 随父居住 (从 exe 字节反汇编) ---')


def need(mn, pat):
    return [i for i in mins if i.mnemonic == mn and all(p in i.op_str for p in pat)]


_w24 = need('mov', ['word ptr [esi + 0x24]'])
check('C14a 孩子 国|城 那个 word(+0x24) 写两次: 动态 dx(父之城) + 静态 ax(兜底)',
      len(_w24) == 2 and [i.op_str.split(', ')[1] for i in _w24] == ['dx', 'ax'],
      ' '.join('%08X %s' % (i.address, i.op_str) for i in _w24))
check('C14b 动态源 = 父实体 +0x24 (读的是父亲**现在**所在国/城)',
      len(need('mov', ['dx, word ptr [eax + 0x24]'])) == 1)
check('C14c fslot/兜底城取表项 +4/+6, 父亲在场判定 test dh,0x80 共 2 处',
      len(need('movzx', ['word ptr [ebx + 4]'])) == 1 and len(need('movzx', ['word ptr [ebx + 6]'])) == 1
      and len(need('test', ['dh, 0x80'])) == 2)
check('C14d PLACE 埋点自增 2 处 (动态/静态各一; 每次复臂都记账, 便于你测随父搬家)',
      len(need('inc', ['dword ptr [0x%x]' % CNT['CHILD_PLACE']])) == 2)
_ic = {}
for i in mins:
    # ★ op_str 可能是 `dword ptr [0x...]`(间接 call), 直接 int() 会炸 —— 只看直接 call
    if i.mnemonic == 'call' and i.op_str.startswith('0x') and \
            PASS <= int(i.op_str, 16) < PASS + len(ccode):
        _ic[int(i.op_str, 16)] = _ic.get(int(i.op_str, 16), 0) + 1
# 桩内部互调账本: 期望表只写"为什么是这个数", 实际值由上面从 exe 反汇编得出。
#   0x54C8AC make_child : 2  (两条出生路径都汇到这里)
#   0x54C90D place_child: 2  (make_child 末尾 + rearm) —— C14e 的题眼就在这里
#   0x54C94B init_stats : 1  (make_child 里 INST 之后那一次)
#   0x54C988 debug_log  : 2  (进出各一处打点, stdcall ret 4)
#   0x54C800 child_pass : 2  (月钩 + 载入钩各自 call 回预载入口)
_MK, _PL, _INI = 0x54C8AC, 0x54C90D, 0x54C94B
_EXP_IC = {_MK: 2, _PL: 2, _INI: 1, cva['debug_log']: 2, PASS: 2}
check('C14e 桩内互调 9 处 / 5 个被调方: make_child 2 + place_child 2(make_child 末尾 + rearm) '
      '+ init_stats 1 + debug_log 2 + child_pass 2(月钩/载入钩)',
      _ic == _EXP_IC, '实际 %s / 期望 %s' % ({hex(a): c for a, c in _ic.items()},
                                           {hex(a): c for a, c in _EXP_IC.items()}))

w('\n--- C14f init_stats 五维 50% 起步 (make_child 里 INST 之后) ---')
_w24i = need('mov', ['byte ptr [edx], cl'])
check('C14f 起步算法形态: oid*0x3b + 记录五维基址 0x524a36 + (v+1)>>1 + 下限 5 + 5 次循环',
      len(need('imul', ['eax, eax, 0x3b'])) == 1
      and len(need('add', ['eax, 0x524a36'])) == 1
      and len(need('shr', ['ecx, 1'])) == 1 and len(need('cmp', ['ecx, 5'])) == 1
      and len(need('mov', ['edi, 5'])) == 1 and len(_w24i) == 1,
      'imul/add/shr/cmp/mov edi,5/mov[edx],cl = %d/%d/%d/%d/%d/%d'
      % (len(need('imul', ['eax, eax, 0x3b'])), len(need('add', ['eax, 0x524a36'])),
         len(need('shr', ['ecx, 1'])), len(need('cmp', ['ecx, 5'])),
         len(need('mov', ['edi, 5'])), len(_w24i)))
check('C14g INIT5 埋点已埋且恰 1 处自增 (开局 0; 游戏里应 = PRELOAD)',
      len(need('inc', ['dword ptr [0x%x]' % CNT['CHILD_INIT5']])) == 1
      and struct.unpack_from('<I', E(CNT['CHILD_INIT5'], 4), 0)[0] == 0)
check('C14h make_child 在 INST 之后才做起步折半 (先拷成年值再改, 顺序反了就是把成年值改了)',
      [i.address for i in mins if i.mnemonic == 'call' and i.op_str == '0x%x' % CS.INST][0]
      < min(i.address for i in mins if i.mnemonic == 'imul'))

# 「同国多数城」: gen_kin 给**城字段 0xff(未设定)**的孩子找落脚城用的规则, 这里用 S1 在场者
# **独立再算一遍**(不 import 它的结果 —— 探针纪律: 新字段/新规则至少两条独立证据), 平票取城号小者。
_tally_g = {}
for _rr in recs:
    if u16r(_rr, GK.S1_OID) == 0xFFFF:
        continue
    _g, _c = _rr[GK.S1_PV], _rr[GK.S1_CITY]
    if _g < 0x31 and _c < 0xc8:
        _row = _tally_g.setdefault(_g, {})
        _row[_c] = _row.get(_c, 0) + 1
GUO_CITY = {g: min(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0] for g, cnt in _tally_g.items()}

w('\n--- C15 表项语义: 每个孩子的落点确实是**他父亲**的城 ---')
bad = []
for r in SE:
    k = KIN['kin'][str(r['oid'])]
    own = (D[r['oid'] * GK.R + GK.BS_PV], D[r['oid'] * GK.R + GK.BS_CITY])
    fo = k['father_oid']
    fb = u16r(D, r['oid'] * GK.R + GK.BS_FATHER)
    if fb != 0xFFFF:
        if k['father_bsd'] != fb:
            bad.append(('BSDATA 父字段与 kin 不符', r['oid'], fb, k['father_bsd']))
        if fo != fb:
            bad.append(('父取错(应优先 BSDATA 那条)', r['oid'], fb, fo))
    if not FOLLOW:                       # 开关关掉: 表项就该写回孩子自己的城(等于不搬家)
        exp, tag = own, '自身(开关关)'
    elif fo is None:
        exp, tag = own, '自身(不明其父)'
    elif fo in oid2slot:
        exp, tag = (recs[oid2slot[fo]][GK.S1_PV], recs[oid2slot[fo]][GK.S1_CITY]), '父 S1'
        if r['fslot'] != oid2slot[fo]:
            bad.append(('fslot 不是父亲所在槽', r['oid'], r['fslot'], oid2slot[fo]))
        if u16r(recs[r['fslot']], GK.S1_OID) != fo:
            bad.append(('fslot 那格的 oid 不指回父亲', r['oid'], r['fslot']))
    else:
        exp, tag = (D[fo * GK.R + GK.BS_PV], D[fo * GK.R + GK.BS_CITY]), '父 BSDATA'
    if exp[1] == 0xFF:                     # 城"未设定" => gen_kin 落**同国多数城**(上面独立重算的那张表)
        _g = exp[0] if exp[0] in GUO_CITY else own[0]
        if _g in GUO_CITY:
            exp, tag = (_g, GUO_CITY[_g]), tag + '->同国多数城'
    if (r['pv'], r['city']) != exp:
        bad.append(('兜底城 != %s 的国/城' % tag, r['oid'], (r['pv'], r['city']), exp))
check('C15 %d 条表项的父亲与落点全部自洽 (不符 %d 处)' % (len(SE), len(bad)), not bad, str(bad[:6]))
check('C15b 落点里没有残留 0xff 城 (0xff = 不属于任何城 => 面板"同城筛"永远看不到他, 也过不了挂载的 城<0xc8 门) '
      '%d/%d 人' % (sum(1 for r in SE if r['city'] != 0xFF), len(SE)),
      all(r['city'] != 0xFF for r in SE),
      '国->众数城 覆盖 %d 国; 残留槽 %s' % (len(GUO_CITY), [r['slot'] for r in SE if r['city'] == 0xFF][:8]))
w('  随父居住: 父在原生池 %d/%d (运行时每月读父亲现城) ; 兜底城来源 %s'
  % (sum(1 for r in SE if r['fslot'] != 0xFFFF), len(SE),
     {t: sum(1 for r in SE if KIN['kin'][str(r['oid'])]['pv_src'] == t)
      for t in ('s1', 'bsd', 'self', 'guo')}))

# ---------------- C16 M3b 数据区 (成长桩/埋点/KID_TAB/CMD_RING/菜单数组) ----------------
w('\n--- C16 M3b MOD 私有区重排: 圈地是否干净、是否全零 ---')
SECSZ, SECVA = LY['section_sz'], LY['section_va']
MODB = LY['mod_base']
GC = LY['growth_ctrs']
KESZ = LY['kid_esz']
regs = [('预载桩(child_pass+两钩子)', PASS, cva['stub_end'] - PASS),
        ('成长桩(实字节)', V['CHILD_GROWTH'], LY.get('growth_stub_sz', 0)),
        ('成长埋点', V['GROWTH_CNT'], LY['menu']['cnt_bytes']),
        ('KID_TAB', V['KID_TAB'], CAP * KESZ),
        ('CMD_RING', V['CMD_RING'], 0x220),
        ('MENU_PTR', V['MENU_PTR'], 0x40),
        ('MENU_CODE', V['MENU_CODE'], 0x20),
        ('PANEL', V['PANEL'], 0x20),
        ('ACT_TAB', V['ACT_TAB'], 0x28),
        ('TEACH_TAB', V['TEACH_TAB'], 0x8)]
ov, non_in = [], []
for i, (n1, a1, s1) in enumerate(regs):
    for n2, a2, s2 in regs[i + 1:]:
        if a1 < a2 + s2 and a2 < a1 + s1:
            ov.append((n1, n2))
    if not (SECVA <= a1 and a1 + s1 <= SECVA + SECSZ):
        non_in.append(n1)
check('C16a %d 块区域互不重叠' % len(regs), not ov, str(ov))
check('C16b 全部落在 .edata 内 (0x%06X..0x%06X)' % (SECVA, SECVA + SECSZ), not non_in, str(non_in))
check('C16c 区域顺序单调 (布局即文档, 别靠巧合)',
      [a for _, a, _ in regs] == sorted(a for _, a, _ in regs),
      ' '.join('%s=0x%06X' % (n, a) for n, a, _ in regs[1:]))
# 偏移不写死: build_big 里成长桩位是 M(0x1420)(月钩长到 0x20 后顺延的), 这里只核"相对次序"
# —— 预载桩之后、埋点表之前, 且埋点表就是 build 记的 M(0x2000)。
check('C16d 成长桩区在预载桩之后、埋点表之前 (0x%X..0x%X)'
      % (V['CHILD_GROWTH'] - MODB, V['GROWTH_CNT'] - MODB),
      cva['stub_end'] <= V['CHILD_GROWTH'] and V['GROWTH_CNT'] == MODB + 0x2000
      and MODB + 0x1400 <= V['CHILD_GROWTH'] < V['GROWTH_CNT'],
      '预载尾 0x%06X / 成长桩 %06X / 埋点 %06X' % (cva['stub_end'], V['CHILD_GROWTH'], V['GROWTH_CNT']))
check('C16e 位图/排程表未被新区域挤掉 (0x100..0x180 / 0x180..0x1200)',
      V['CHILD_BM'] == MODB + 0x100 and V['CHILD_SCHED'] == MODB + 0x180
      and V['CHILD_BM'] + CAP // 8 <= V['CHILD_SCHED'] and SCHED + len(want) <= PASS,
      '排程表尾 0x%06X <= 预载桩 0x%06X' % (SCHED + len(want), PASS))
check('C16f 吃到 M(0x%X) 且余量 >= 0 (MOD_SZ 0x%X)' % (LY['mod_used_upto'], LY['mod_sz']),
      LY['mod_used_upto'] <= LY['mod_sz'],
      '余 %dB' % (LY['mod_sz'] - LY['mod_used_upto']))
# 埋点表: 每条 4B, 条数上限 = 构建器记下的 cnt_bytes (0x2000..0x2100 = 64 槽, M3c 分页两个埋点后从 32 抬到 64)
check('C16g 成长埋点 %d 个 ×4B 装得进 %d 字节区 (尾 0x%06X <= KID_TAB 0x%06X)'
      % (len(GC), LY['menu']['cnt_bytes'], V['GROWTH_CNT'] + LY['menu']['cnt_bytes'], V['KID_TAB']),
      len(GC) * 4 <= LY['menu']['cnt_bytes']
      and V['GROWTH_CNT'] + LY['menu']['cnt_bytes'] <= V['KID_TAB'],
      '%d 槽用去 %dB / 区 %dB' % (LY['menu']['cnt_bytes'] // 4, len(GC) * 4, LY['menu']['cnt_bytes']))
gv = [GC[n] for n in GC]
check('C16h 埋点地址连续 4B 递增、无空洞', gv == sorted(gv) and all(b - a == 4 for a, b in zip(gv, gv[1:])),
      '%06X..%06X' % (gv[0], gv[-1]))
zeros = {}
for n, va in GC.items():
    zeros[n] = struct.unpack_from('<I', E(va, 4), 0)[0]
check('C16i 成长埋点 %d 个开局全 0' % len(GC), all(v == 0 for v in zeros.values()),
      str({k: v for k, v in zeros.items() if v}))
for nm, va, sz in (('KID_TAB', V['KID_TAB'], CAP * KESZ), ('CMD_RING', V['CMD_RING'], 0x220),
                   ('MENU_PTR', V['MENU_PTR'], 0x40), ('MENU_CODE', V['MENU_CODE'], 0x20),
                   ('PANEL', V['PANEL'], 0x20)):
    blk = bytes(E(va, min(sz, 0x400)))              # 抽查前 1KB (整块全零由 build 保证)
    check('C16j %s 开局全 0 (抽查 %dB)' % (nm, len(blk)), blk == b'\x00' * len(blk))
w('  KID_TAB %d 槽 × %dB = %dB @0x%06X..0x%06X ; CMD_RING 头 8B + 64 条 ×8B @0x%06X'
  % (CAP, KESZ, CAP * KESZ, V['KID_TAB'], V['KID_TAB'] + CAP * KESZ, V['CMD_RING']))
w('  KID_TAB 字段口径(唯一真源=child_growth.py): +0 亲密 +2 投入 +4 增量位图(byte) +5 自然保底累加器 '
  '+6 活动 +7 剩余天 +8 教席 +9 上次结算月+1(0=从未) +10 元服归属')

# ---------------- C17 M3b-2 成长结算桩 ----------------
w('\n--- C17 成长桩 child_growth_pass: 字节复现 / 月钩两段式 / 语义形态 ---')
GL = {'sched': SCHED, 'pool': POOL, 'kid_tab': V['KID_TAB'], 'esz': CS.ESZ,
      'ring': V['CMD_RING'], 'bm': V['CHILD_BM'],
      'act_tab': V['ACT_TAB'], 'teach_tab': V['TEACH_TAB'],
      'c_pass': GC['GROWTH_PASS'], 'c_settled': GC['GROWTH_SETTLED'], 'c_dupm': GC['GROWTH_DUPM'],
      'c_freeze': GC['GROWTH_FREEZE'], 'c_full': GC['GROWTH_FULL'], 'c_natural': GC['GROWTH_NATURAL'],
      'c_cmd': GC['GROWTH_CMD'], 'c_roll': GC['GROWTH_ROLL'], 'c_fail': GC['GROWTH_FAIL'],
      'c_ok': GC['GROWTH_OK'], 'c_reject': GC['GROWTH_REJECT'],
      # ---- M4 元服支 ----
      'puku_age': LY.get('genpuku_age', CG.AGE_PUKU), 'genpuku': V['CHILD_GENPUKU'],
      'c_mount': GC['GROWTH_PUKU_MOUNT'], 'c_ronin': GC['GROWTH_PUKU_RONIN'],
      # ---- M3d 三通道埋点 ----
      'teach_lord': GC['TEACH_LORD'], 'teach_parent': GC['TEACH_PARENT'],
      'teach_shope': GC['TEACH_SHOPE'],
      # debug_log 桩 VA (stdcall ret 4; 缺失会让 CG.build 的 %-替换 KeyError)
      'debug_log': V.get('DEBUG_LOG', 0x54C988)}
PUKU_AGE = LY.get('genpuku_age', CG.AGE_PUKU)


def capimm(v):
    """值 -> capstone 的立即数写法: <10 十进制, >=10 0x%x (桩里写 0xf / 表里比 0xf)。
    与下方 imm(s)(字符串->值) 反向; 两者一起才覆盖 capstone 的双口径。"""
    return str(v) if v < 10 else '0x%x' % v

gcode, gva, gsrc, gins = CG.build(GCV, GL)
ggot = bytes(E(GCV, len(gcode)))
preload_sz = cva['stub_end'] - PASS
check('C17a 成长桩 %dB @0x%06X 与 child_growth.build() 逐字节一致' % (len(gcode), GCV),
      ggot == gcode, '桩尾 0x%06X / 埋点 0x%06X' % (GCV + len(gcode), V['GROWTH_CNT']))
# ---- 成长桩的语义形态: 全部从 **exe 字节** 反汇编出来核 (不是从源码核) ----
mins_g = list(md.disasm(ggot, GCV))
assert sum(len(i.bytes) for i in mins_g) == len(ggot), '成长桩反汇编没吃满'


def needg(mn, pat):
    return [i for i in mins_g if i.mnemonic == mn and all(p in i.op_str for p in pat)]


check('C17b 成长桩落在预留窗口 0x1400..0x2000 内且不碰埋点 (%d B, 用 %d%%)'
      % (len(gcode), 100 * len(gcode) // (V['GROWTH_CNT'] - MODB - 0x1400)),
      MODB + 0x1400 <= GCV and GCV + len(gcode) <= V['GROWTH_CNT'] and PASS + preload_sz <= GCV,
      '0x%06X..0x%06X vs 埋点 0x%06X' % (GCV, GCV + len(gcode), V['GROWTH_CNT']))
check('C17c 只结算"儿童态且在岗"的孩子: 低半字==0xb 判据 + bit15 判据各 1',
      len(needg('and', ['al, 0xf'])) == 1 and len(needg('cmp', ['al, 0xb'])) == 1
      and len(needg('movzx', ['byte ptr [esi + 0x2d]'])) == 1
      and len(needg('test', ['al, 0x80'])) == 1)
_date_ld = needg('movzx', ['byte ptr [0x5205f1]'])
check('C17d 月守卫: 读 0x5205f1 -> 下一条就是 +1 -> 与 KID_TAB+9 比 -> 不等才写回 (读档/同月双触发都不白涨)',
      len(_date_ld) == 1 and len(mins_g) > mins_g.index(_date_ld[0])
      and mins_g[mins_g.index(_date_ld[0]) + 1].mnemonic == 'inc'
      and mins_g[mins_g.index(_date_ld[0]) + 1].op_str == 'eax'
      and len(needg('cmp', ['al, byte ptr [edi + 9]'])) == 1
      and len(needg('mov', ['byte ptr [edi + 9], al'])) == 1)
_PUKU_CMP = [i for i in mins_g if i.mnemonic == 'cmp'
             and i.op_str == 'eax, %s' % capimm(PUKU_AGE)]
check('C17e 年龄走原生 getter 0x49A5C0 且 >=元服线(虚岁 %d)进 M4 支 (阈值可用 KID_AGE_GENPUKU 抬)'
      % PUKU_AGE,
      len(needg('call', ['0x49a5c0'])) == 1 and len(_PUKU_CMP) == 1
      and mins_g[mins_g.index(_PUKU_CMP[0]) + 1].mnemonic == 'jae',
      '门后一条: %s' % (mins_g[mins_g.index(_PUKU_CMP[0]) + 1].op_str if _PUKU_CMP else '-'))
check('C17f 三档月增 14/35/52 (0xe/0x23/0x34) 与边界 7/12, 攒满 100(0x64) 才加点且带进位',
      len(needg('mov', ['dword ptr [esp + 0xc], 0xe'])) == 1
      and len(needg('mov', ['dword ptr [esp + 0xc], 0x23'])) == 1
      and len(needg('mov', ['dword ptr [esp + 0xc], 0x34'])) == 1
      and len(needg('cmp', ['eax, 7'])) == 1 and len(needg('cmp', ['eax, 0xc'])) == 1
      and len(needg('cmp', ['eax, 0x64'])) == 1 and len(needg('sub', ['eax, 0x64'])) == 1
      and len(needg('mov', ['byte ptr [edi + 5], al'])) == 2)
check('C17g 天花板 = 该孩自己 BSDATA 记录的五维 (oid*0x3b + 0x524a36), 扫 5 维取差距最大者',
      len(needg('imul', ['eax, eax, 0x3b'])) == 1 and len(needg('add', ['eax, 0x524a36'])) == 1
      and len(needg('movzx', ['byte ptr [esi + ecx + 0xa]'])) >= 1
      and len(needg('movzx', ['byte ptr [edx + ecx]'])) >= 1
      and len(needg('cmp', ['dword ptr [esp], 5'])) >= 1,
      'imul eax,3b=%d add 524a36=%d read child dim[esi+ecx+0xa]=%d read BSDATA dim[edx+ecx]=%d loop5=%d'
      % (len(needg('imul', ['eax, eax, 0x3b'])), len(needg('add', ['eax, 0x524a36'])),
         len(needg('movzx', ['byte ptr [esi + ecx + 0xa]'])),
         len(needg('movzx', ['byte ptr [edx + ecx]'])), len(needg('cmp', ['dword ptr [esp], 5']))))
check('C17h +1 走原生字段写手 (0x4A2F80 + d*0x20, ecx=字段指针, push 1) —— 不自加、上限由引擎管; '
      '自然/父自动/主角自动/培养指令圈 四处各一条',
      len(needg('mov', ['eax, 0x4a2f80'])) == 4 and len(needg('imul', ['ecx, ecx, 0x20'])) == 3
      and len(needg('imul', ['ecx, edi, 0x20'])) == 1
      and len(needg('lea', ['ecx, [esi + ecx + 0xa]'])) >= 1 and len(needg('push', ['1'])) == 5
      and len(needg('call', ['eax'])) == 4,
      '写手表址 %d / 自然段取址 %d / 培养段取址 %d / lea %d / push 1 %d / call eax %d'
      % (len(needg('mov', ['eax, 0x4a2f80'])), len(needg('imul', ['ecx, ecx, 0x20'])),
         len(needg('imul', ['ecx, edi, 0x20'])), len(needg('lea', ['ecx, [esi + ecx + 0xa]'])),
         len(needg('push', ['1'])), len(needg('call', ['eax']))))
check('C17i 增量位图按维置位 (mov edx,1 / shl edx,cl / or) —— 自然(edi)/父自动(edi)/主角自动(edi)/培养指令圈(esi) 四处',
      len(needg('shl', ['edx, cl'])) == 4 and len(needg('mov', ['edx, 1'])) == 4
      and len(needg('or', ['byte ptr [edi + 4], dl'])) == 3
      and len(needg('or', ['byte ptr [esi + 4], dl'])) == 1,
      'shl=%d mov1=%d or[edi+4]=%d or[esi+4]=%d'
      % (len(needg('shl', ['edx, cl'])), len(needg('mov', ['edx, 1'])),
         len(needg('or', ['byte ptr [edi + 4], dl'])), len(needg('or', ['byte ptr [esi + 4], dl']))))
_gcnt = {n: len(needg('inc', ['dword ptr [0x%x]' % GC[n]])) for n in
         ('GROWTH_PASS', 'GROWTH_SETTLED', 'GROWTH_DUPM', 'GROWTH_FREEZE', 'GROWTH_FULL',
          'GROWTH_NATURAL', 'GROWTH_CMD', 'GROWTH_ROLL', 'GROWTH_FAIL', 'GROWTH_OK',
          'GROWTH_REJECT', 'GROWTH_PUKU_MOUNT', 'GROWTH_PUKU_RONIN')}
# MOUNT 两处是设计使然: 随父挂载成功 + 挂本国国主成功 都算"挂上了人"; 其余各一处
_exp_g = dict((n, 1) for n in _gcnt)
_exp_g['GROWTH_PUKU_MOUNT'] = 2
_bad_g = {n: (_gcnt[n], _exp_g[n]) for n in _gcnt if _gcnt[n] != _exp_g[n]}
check('C17j %d 个成长埋点的自增处数 = 语义 (MOUNT 两条路各一处) %s' % (len(_gcnt), _gcnt),
      not _bad_g, str(_bad_g))
_np = [i for i in mins_g if i.mnemonic == 'push']
_pop = [i for i in mins_g if i.mnemonic == 'pop']
_a4, _a8 = needg('add', ['esp, 4']), needg('add', ['esp, 8'])
# ★ ret 4 自清方必须把 debug_log 算进来: 它是 stdcall(1 枚 marker 实参, 尾部 ret 4), 4 个调用点各入 1 枚,
#   栈由它自己清。2026-10-07 事故簿第 2 条 —— 源码曾在这几处再补一条 add esp,4, ESP 逐次漂移 => 月边界必崩,
#   所以这里用恒等式钉死: add esp,4 必须恰是 rand x3 + 国主 x1 = 4, 多一条就是旧病复发。
_RET4 = (CG.NIB_SET, CG.EXCL_SET, CG.DAIMYO_SET, GL['debug_log'])
_r4 = len([i for i in mins_g if i.mnemonic == 'call'
           and i.op_str in ('0x%x' % v for v in _RET4)])
_rax = len(needg('call', ['eax']))                       # 五维写手表: 表项本身也是 ret 4 的 thiscall
check('C17k 栈帧平衡 (sub/add esp 0x10 各 1, 4 帧 push + 元服 3 保护 push + 实参 push = %d 枚, '
      '有效 12(静态 13) pop, 一个 ret) ; 全桩恒等式 push = (pop-1 互斥分支) + add esp,4 清 %d + add esp,8 清 %d + ret 4 自清 %d'
      % (len(_np), len(_a4), 2 * len(_a8), _r4 + _rax),
      len(needg('sub', ['esp, 0x10'])) == 1 and len(needg('add', ['esp, 0x10'])) == 1
      and len([i for i in mins_g if i.mnemonic == 'ret']) == 1
      # 非 ('1','0x64') 的 push = 4 枚 debug_log marker + 0xff(NIB_SET) + 0(EXCL_SET) + 17 枚寄存器 = 23
      and len([i for i in _np if i.op_str not in ('1', '0x64')]) == 23
      and len([i for i in _np if i.op_str == '1']) == 5       # DAIMYO_SET 1 + 五维写手 4
      and len([i for i in _np if i.op_str == '0x64']) == 3
      and len(_a4) == 4          # rand(培养) + rand(父自动) + rand(主角自动) + 0x4A5290(本人)
      and len(_a8) == 2          # 0x4A5100(本人,主人) + 0x4b5620(qualify)
      and len(_pop) in (12, 13)  # 有效 12 = 4帧+cg_t_lord4+cg_t_father1+元服3; 静态 13: cg_t_const_parent 与 cg_t_father success 互斥各一 pop edx, 静态多计 1
      # 栈帧恒等式: -1 抵消 cg_t_const_parent/cg_t_father success 互斥分支重复计入的 1 条 pop edx (入口仅 1 次 push edx)
      and len(_np) == (len(_pop) - 1) + len(_a4) + 2 * len(_a8) + _r4 + _rax,
      'push %s / pop %d / add esp 4 x%d, 8 x%d / ret4 %d + call eax %d'
      % (sorted(i.op_str for i in _np), len(_pop), len(_a4), len(_a8), _r4, _rax))
_gadv = needg('add', ['ebx, %d' % CS.ESZ])
# 循环头有两处(排程表 / 指令圈都从 [ebx] 取头), 自然段循环头 = 紧跟哨兵 cmp 的那条
_sen = [i for i in mins_g if i.mnemonic == 'cmp' and i.op_str == 'ax, -1']
_gh = [i for i in mins_g if i.mnemonic == 'movzx' and i.op_str.endswith('[ebx]')]
_gs = [i for i in _gh if _sen and mins_g[mins_g.index(i) + 1] is _sen[0]]
_gback = [i for i in mins_g if i.mnemonic == 'jmp' and _gs and i.op_str == '0x%x' % _gs[0].address]
check('C17l 成长桩游标前进 1 条 + 唯一回边 (同 M2 的血泪教训)',
      len(_gadv) == 1 and len(_gs) == 1 and len(_gback) == 1
      and _gback[0].address == _gadv[0].address + _gadv[0].size)
_mh = list(md.disasm(bytes(E(V['CHILD_MONTH_HOOK'], 17)), V['CHILD_MONTH_HOOK']))
_mc = [i for i in _mh if i.mnemonic == 'call']
check('C17m 月钩 = pushad / call 预载 / call 成长 / popad / jmp 原 callee (17B, 顺序不能反: 先保证在场再结算)',
      len(_mc) == 2 and int(_mc[0].op_str, 16) == PASS and int(_mc[1].op_str, 16) == GCV,
      ' | '.join('%s %s' % (i.mnemonic, i.op_str) for i in _mh))
_lh = list(md.disasm(bytes(E(V['CHILD_LOAD_HOOK'], 12)), V['CHILD_LOAD_HOOK']))
_lc = [i for i in _lh if i.mnemonic == 'call']
check('C17n 保存侧钩(历史名"载入钩")**不**调成长桩 (一次存/读不会多算一跳)', len(_lc) == 1 and int(_lc[0].op_str, 16) == PASS,
      ' | '.join('%s %s' % (i.mnemonic, i.op_str) for i in _lh))
w('  桩源码 (与落盘字节同源):')
for ln in gsrc.splitlines():
    w('    ' + ln)

# ---------------- C18 自然保底预期 (参考实现 = 桩同语义; 数值并入下方一张表) ----------------
w('\n--- C18 自然保底预期 (与桩同语义的参考实现; 元服线 %d 岁, 档位 %s/月, 满 %d 进 1 点) ---'
  % (CG.AGE_FREEZE, '/'.join(map(str, CG.RATES)), CG.ACC_FULL))
w('「龄」一列按引擎 getter 0x49A5C0 口径 = 当前年 - 生年 + 1 (虚岁), 与桩里档位选择/冻结判据完全同源')
w('「第N月」以开局月 = %d 月起算 (虚岁每逢新年 +1); 实机若开局月不同, 用 TKID_START_MONTH 重跑本表'
  % START_MONTH)
growth_pred = {}
_bad_sim = []
for e in SE:
    oid, s = e['oid'], e['slot']
    rr = rec(oid)
    adult = [rr[0x16 + d] for d in range(CG.NDIM)]
    age = eng_age(1490 + (struct.unpack_from('<H', rr, 0x27)[0] & 0x7F))
    sim = CG.simulate(age, adult, START_MONTH)
    st = CG.start_stats(adult)
    if any(st[d] > adult[d] for d in range(CG.NDIM)):
        _bad_sim.append((oid, st, adult))
    growth_pred[s] = {'age_engine': age, 'adult': adult, 'start': st, 'final': sim['final'],
                      'points': sim['points'], 'by_dim': sim['by_dim'], 'full': sim['full'],
                      'months': sim['months'], 'first_hit': sim['hits'][0] if sim['hits'] else None,
                      'acc_end': sim['acc_end']}
check('C18 参考实现自洽: 每人 起步<=终值<=成年值+5 且 终值>=起步 (越界 %d 处)' % len(_bad_sim),
      all(p['final'][d] >= p['start'][d] and p['final'][d] <= p['adult'][d] + CG.START_FLOOR
          for p in growth_pred.values() for d in range(CG.NDIM)), str(_bad_sim[:4]))
_tot = sum(p['points'] for p in growth_pred.values())
_zero = [p for p in growth_pred.values() if not p['points']]
check('C18b %d 人合计自然点数 %d (元服前) ; 0 点人数 %d (开局即 >=15) ; 触顶人次 %d'
      % (len(growth_pred), _tot, len(_zero), sum(1 for p in growth_pred.values() if p['full'])),
      _tot > 0, 'tkwatch 对 GROWTH_NATURAL 的上界 = %d (元服前只增不减)' % _tot)

w('\n--- 一张表看全: 预载后预期 + 成长预期 (开局/读档钩子跑完后; 记录->实体 = +12 位移, 见 C10c) ---')
w('状态字/余位 = 实体 +0x2c 期望值; tkwatch 读到必须一模一样 (余位只剩 5,6,11,12,13,14 这几位)')
w('国/城 = 预载桩**应当**写进实体 +0x24/+0x25 的值 (随父居住: 父在池则每月跟父现城, 表里是首月值)')
w('五维 = 开局应为「起步」列 (50%% 折半, 下限 %d); 之后每月按档位涨, 元服前跑到「终值」列' % CG.START_FLOOR)
w('%-4s %-4s %-10s %-4s %-8s %-10s %-7s %-5s %s' %
  ('槽', 'oid', '全名', '龄', '状态字', '余位', '国/城', '父槽', '生年/登场/父/母'))
pred = {}
for e in SE:
    oid, s = e['oid'], e['slot']
    rr = rec(oid)
    sur, giv = gbk(rr[0:7]), gbk(rr[7:14])
    birth = 1490 + (struct.unpack_from('<H', rr, 0x27)[0] & 0x7F)
    appear = 1560 + ((struct.unpack_from('<H', rr, 0x27)[0] >> 7) & 0x3F)
    st0 = struct.unpack_from('<H', rr, 0x2c + 12)[0]      # INST 把记录 +0x38 拷进实体 +0x2c
    fin = (st0 & 0x7870) | 0x1B                           # 配方: 位15/7/8..10 清, 低半字=b, 位4 置
    free = fin & 0x7860                                   # 只可能来自记录的位: 5,6,11..14
    k = KIN['kin'][str(oid)]
    g = growth_pred[s]
    pred[s] = {'oid': oid, 'name': sur + giv, 'birth': birth, 'age': g['age_engine'],
               'status': fin, 'raw_status': st0, 'free_bits': '0x%04X' % free, 'lord': 0xFFFF,
               'pv': e['pv'], 'city': e['city'], 'fslot': e['fslot'],
               'father_oid': k['father_oid'], 'father': k['father_name'],
               'father_ent': u16r(rr, GK.BS_FATHER),
               'mother_oid': k.get('mother_oid'), 'mother': k.get('mother_name', ''),
               'mother_src': k.get('mother_src', ''), 'mslot': k.get('mslot', 0xFFFF),
               'tree_fam': k.get('tree_fam', ''), 'tree_rel': k.get('tree_rel', ''),
               'adult': g['adult'], 'start': g['start'], 'final': g['final'],
               'points': g['points'], 'by_dim': g['by_dim'], 'full': g['full'],
               'months_to_puku': g['months'], 'first_hit_month': g['first_hit'],
               'acc_end': g['acc_end']}
    _mo = ('母%s(%s)' % (k['mother_name'], k['mother_src']) if k['mother_oid'] is not None
           else '母未知(%s)' % ('族谱正室在本作无档案' if k['mother_src'] else 'BSDATA 无母字段'))
    w('%-4d %-4d %-10s %-4d %-8s %-10s %-3d/%-3d %-5s 生%d 登场年%d 父%s(%s) %s'
      % (s, oid, sur + giv, g['age_engine'], '0x%04X' % fin, '0x%04X' % free,
         e['pv'], e['city'], ('%d' % e['fslot']) if e['fslot'] != 0xFFFF else '-',
         birth, appear, k['father_name'] or '不明', k['father_src'], _mo))
    w('     五维 成年 %s | 起步 %s | 元服前 %s (+%d 点: %s) 首加点 %s%s'
      % ('-'.join(map(str, g['adult'])), '-'.join(map(str, g['start'])),
         '-'.join(map(str, g['final'])), g['points'],
         ' '.join('%d:%d' % (d, n) for d, n in enumerate(g['by_dim']) if n) or '无',
         ('第%d月第%d维' % (g['first_hit'][0], g['first_hit'][2])) if g['first_hit'] else '无',
         '' if not g['full'] else '  [全维触顶 %d 次]' % g['full']))
    assert (fin & 0x879F) == 0x001B, ('recipe invariant broken at slot %d: %04X' % (s, fin))
_m = [p for p in pred.values() if p['mother_oid'] is not None]
_f = sum(1 for p in pred.values() if p['father_oid'] is not None)
check('C19 亲子覆盖: 父 %d/%d ; 母 %d/%d (%s)。母只有族谱配偶边一个来源 —— BSDATA 记录里没有母字段, '
      '且本作女性档案极少(全 700 条内联名里搜"宁宁/浓姬/阿松/筑山殿"命中 0)'
      % (_f, len(pred), len(_m), len(pred),
         '、'.join('%s<=母%s@槽%s' % (p['name'], p['mother'],
                                    p['mslot'] if p['mslot'] != 0xFFFF else '(预载槽)')
                   for p in _m) or '本批全无母'), _f > 0)
json.dump(pred, open(REV / '_child_expect.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------------- C20 M3b-3: 成效公式的两张常数表 ----------------
w('\n--- C20 M3b-3 活动/教席常数表: 落盘字节 = child_growth 定义, 且桩按表读 ---')
atab = bytes(E(V['ACT_TAB'], len(CG.ACTS) * 4))
ttab = bytes(E(V['TEACH_TAB'], len(CG.TEACHERS)))
check('C20a ACT_TAB %d 条 ×4B @0x%06X 逐字节 = CG.ACTS' % (len(CG.ACTS), V['ACT_TAB']),
      atab == CG.act_tab_bytes(),
      ' '.join('%s=%s+%d%%' % (n, CG.DIM_NAME[d], b) for n, d, b in CG.ACTS))
check('C20b TEACH_TAB %d 条 ×1B @0x%06X 逐字节 = CG.TEACHERS' % (len(CG.TEACHERS), V['TEACH_TAB']),
      ttab == CG.teach_tab_bytes(), ' '.join('%s+%d%%' % nt for nt in CG.TEACHERS))
_a_dim = [atab[i * 4] for i in range(len(CG.ACTS))]
_a_b = [atab[i * 4 + 1] for i in range(len(CG.ACTS))]
check('C20c 表内容自洽: 主加维全在 0..%d、B 基础在 1..%d、空槽位(第3/4字节)为 0' % (CG.NDIM - 1, CG.B_TIER_MAX),
      all(0 <= d < CG.NDIM for d in _a_dim) and all(0 < b <= CG.B_TIER_MAX for b in _a_b)
      and atab[2::4] == b'\x00' * len(CG.ACTS) and atab[3::4] == b'\x00' * len(CG.ACTS),
      'dim=%s B=%s' % (_a_dim, _a_b))
# 桩里的上界必须等于表长 —— 加活动/教席却忘了改桩, 就会从这里红
check('C20d 桩的活动上界/教席上界 = 表长 (改表必须同步桩)',
      len(needg('cmp', ['eax, 0x%x' % len(CG.ACTS)])) == 1
      and len(needg('cmp', ['ecx, %d' % len(CG.TEACHERS)])) == 1
      and len(needg('movzx', ['edi, byte ptr [eax*4 + 0x%x]' % V['ACT_TAB']])) == 1
      and len(needg('movzx', ['edx, byte ptr [eax*4 + 0x%x]' % (V['ACT_TAB'] + 1)])) == 1
      and len(needg('movzx', ['ecx, byte ptr [ecx + 0x%x]' % V['TEACH_TAB']])) == 1)

# ---------------- C21 M3b-3: 成功率公式 (桩里的常数 = Python 参考实现的常数) ----------------
w('\n--- C21 M3b-3 成效公式: P = 夹到 [%d,%d] 的 (P0 + T + B + 亲密/10 - 现值/4) ---'
  % (CG.P_MIN, CG.P_MAX))
_pf = {'P0': ('add', 'edx, 0x%x' % CG.P0), 'B 上限': ('cmp', 'edx, 0x%x' % CG.B_TIER_MAX),
       'B 夹顶': ('mov', 'edx, 0x%x' % CG.B_TIER_MAX), '亲密夹顶': ('cmp', 'ecx, 0x%x' % CG.P_CAP_RAND),
       '亲密×': ('imul', 'ecx, ecx, 0x%x' % CG.BOND_MUL),
       '亲密>>': ('shr', 'ecx, 0x%x' % CG.BOND_SHR),
       '现值>>': ('shr', 'ecx, %d' % CG.D_SHIFT), 'P 下限': ('cmp', 'edx, %d' % CG.P_MIN),
       'P 夹底': ('mov', 'edx, %d' % CG.P_MIN), 'P 上限': ('cmp', 'edx, 0x%x' % CG.P_MAX),
       'P 夹顶': ('mov', 'edx, 0x%x' % CG.P_MAX), '掷骰模': ('push', '0x%x' % CG.P_CAP_RAND),
       '硬顶': ('cmp', 'ecx, 0x%x' % CG.STAT_CEIL)}
_miss = [k for k, (mn, p) in _pf.items() if len(needg(mn, [p])) < 1]
check('C21a 公式每个常数都能在 exe 字节里找到 (缺: %s)' % (_miss or '无'), not _miss,
      'P0=%d T=%s B=%s+%d×档(<=\\%d) 亲密/10 现值/%d 夹[%d,%d]'
      % (CG.P0, [t for _n, t in CG.TEACHERS], _a_b, CG.B_TIER_STEP, CG.B_TIER_MAX,
         1 << CG.D_SHIFT, CG.P_MIN, CG.P_MAX))
check('C21b 掷骰走引擎原生 rand 0x4EBD60 且 cdecl 自清栈 (你能改 0x50DE48 的种子反推结果); '
      '桩里 add esp,4 共 4 发 = rand(培养) + 0x4A5290(M4) + rand(父自动) + rand(主角自动) (M3d)',
      len(needg('call', ['0x4ebd60'])) == 3 and len(needg('add', ['esp, 4'])) == 4
      and len(needg('cmp', ['eax, dword ptr [esp + 8]'])) == 1)
_rolls = needg('call', ['0x4ebd60'])
_bad_dir = []
for r in _rolls:
    j = mins_g.index(r)
    seq = mins_g[j:j + 4]
    ok = (len(seq) == 4 and seq[1].mnemonic == 'add' and seq[1].op_str == 'esp, 4'
          and seq[2].mnemonic == 'cmp' and seq[2].op_str.startswith('eax,')
          and seq[3].mnemonic == 'jae')
    if not ok:
        _bad_dir.append('%s->%s' % (r.op_str, ' / '.join('%s %s' % (i.mnemonic, i.op_str) for i in seq[1:])))
check('C21c 判定方向 = 每次 rand(100) 都遵循 rand < P 才算成功 (call 后紧跟 add esp,4 / cmp eax,P / jae 失败)',
      not _bad_dir, '异常路径: %s' % _bad_dir)
_oob = []
for a in range(len(CG.ACTS)):
    for t in range(len(CG.TEACHERS)):
        for tier in range(4):
            for bond in (0, 1, 9, 10, 11, 50, 99, 100, 101):
                for cur in (0, 1, 4, 5, 33, 64, 99, 100, 101):
                    P, _ = CG.prob(a, t, tier, bond, cur)
                    if not (CG.P_MIN <= P <= CG.P_MAX):
                        _oob.append((a, t, tier, bond, cur, P))
check('C21d 全枚举 P 落在夹区间内 (违例 %d)' % len(_oob), not _oob, str(_oob[:4]))
_mono = []
for a in range(len(CG.ACTS)):
    # 教席按**加成值**排序比 (表里 TEACHERS 的书写顺序不是强度顺序: 主角 20 > 父 15 > 师匠 12 …)
    _ts = sorted(range(len(CG.TEACHERS)), key=lambda i: CG.TEACHERS[i][1])
    for k in range(len(_ts) - 1):
        if CG.prob(a, _ts[k + 1], 3, 100, 50)[0] < CG.prob(a, _ts[k], 3, 100, 50)[0]:
            _mono.append(('教席', a, CG.TEACHERS[_ts[k]][0], CG.TEACHERS[_ts[k + 1]][0]))
    for tier in range(3):
        if CG.prob(a, 1, tier + 1, 100, 50)[0] < CG.prob(a, 1, tier, 100, 50)[0]:
            _mono.append(('档次', a, tier))
    for cur in (0, 40, 80):
        if CG.prob(a, 1, 3, 100, cur + 4)[0] > CG.prob(a, 1, 3, 100, cur)[0]:
            _mono.append(('现值', a, cur))
    for bd in (0, 40, 90):
        if CG.prob(a, 1, 3, bd + 10, 50)[0] < CG.prob(a, 1, 3, bd, 50)[0]:
            _mono.append(('亲密', a, bd))
check('C21f 单调性: 教席↑ / 档次↑ / 现值↓ 抬高 P / 亲密↑ 四向都不反序 (违例 %d)' % len(_mono),
      not _mono, str(_mono[:4]))
_rng = {}
for a in range(len(CG.ACTS)):
    lo = CG.prob(a, 0, 0, 0, CG.STAT_CEIL)[0]
    hi = CG.prob(a, CG.TEACHERS.index(max(CG.TEACHERS, key=lambda x: x[1])), 3, 100, 0)[0]
    _rng[CG.ACTS[a][0]] = (lo, hi)
check('C21g 每个活动都有可测区间 (最差 自学+无亲密+满值 < 最好 主角+亲密满+低值)',
      all(lo < hi for lo, hi in _rng.values()),
      ' '.join('%s %d~%d%%' % (k, v[0], v[1]) for k, v in _rng.items()))

# ---------------- C22 M3b-3: 指令圈结构与埋点身份式 ----------------
w('\n--- C22 M3b-3 CMD_RING: 队列形态 + 五个新埋点的身份式 ---')
_hdr = struct.unpack_from('<2I', E(V['CMD_RING'], 8), 0)
check('C22a CMD_RING 头 (head,tail)@0x%06X 开局 = %s (相等即空队, 月钩判空成立)' % (V['CMD_RING'], _hdr),
      _hdr[0] == _hdr[1] == 0)
check('C22b 64 条 ×8B 条目区 @0x%06X 开局全 0 (首条 slot 读 0 也不会误当有效指令 —— 空队靠 head==tail)'
      % (V['CMD_RING'] + 8),
      bytes(E(V['CMD_RING'] + 8, 64 * 8)) == b'\x00' * (64 * 8))
check('C22c 桩只写 head、只读 tail (tail 是 UI 的接口, M3c 才写) —— head 写回 1 处 / tail 读 2 处',
      len(needg('mov', ['dword ptr [0x%x], eax' % V['CMD_RING']])) == 1
      and len(needg('cmp', ['eax, dword ptr [0x%x]' % (V['CMD_RING'] + 4)])) == 2)
_gates = [('龄<15(培养段用 cl)', needg('cmp', ['cl, 0xb'])),
          ('bit15 在岗(培养段)', needg('test', ['byte ptr [ebp + 0x2d], 0x80'])),
          ('儿童位图', needg('bt', ['0x%x' % V['CHILD_BM']])),
          ('活动上界', needg('cmp', ['eax, 0x%x' % len(CG.ACTS)])),
          ('教席上界', needg('cmp', ['ecx, %d' % len(CG.TEACHERS)]))]
w('  消费前门: %s' % ' / '.join('%s(%d)' % (n, len(v)) for n, v in _gates))
# 位图门的跳转形态坑: 我们写 `jnc`, capstone 规范化成 `jae` —— 两者同 opcode 0x73 (CF==0 则跳),
# 所以不能按助记符数, 只能核 bt 之后那条条件跳转是否落在 reject 汇合点(= REJECT 埋点自增处)。
_bt = needg('bt', ['0x%x' % V['CHILD_BM']])[0]
_after_bt = mins_g[mins_g.index(_bt) + 1]
_rej_va = next(i.address for i in mins_g
               if i.mnemonic == 'inc' and i.op_str == 'dword ptr [0x%x]' % GC['GROWTH_REJECT'])
check('C22d 门各恰 1 处 + 硬顶读现值 2 处(一次算 D、一次掷骰后再判) + 位图门不过就汇到 REJECT',
      all(len(v) == 1 for _n, v in _gates)
      and len(needg('movzx', ['ecx, byte ptr [ebp + edi + 0xa]'])) == 2
      and _after_bt.mnemonic in ('jae', 'jnc') and _after_bt.op_str == '0x%x' % _rej_va,
      'bt 后一条 = %s %s (capstone 把 jnc 规范成同 opcodes 的 jae, 按助记符数会误报)'
      % (_after_bt.mnemonic, _after_bt.op_str))
_new = ('GROWTH_CMD', 'GROWTH_ROLL', 'GROWTH_FAIL', 'GROWTH_OK', 'GROWTH_REJECT')
_dup = [n for n in _new if [GC[m] for m in _new].count(GC[n]) > 1]
_out = [n for n in _new if not (V['GROWTH_CNT'] <= GC[n] < V['GROWTH_CNT'] + LY['menu']['cnt_bytes'])]
check('C22e 培养段五个埋点: 互不重号、都在 %d 字节埋点区内、各恰 1 处自增 (手测身份式 %s)'
      % (LY['menu']['cnt_bytes'], ' / '.join(['CMD = ROLL + REJECT', 'ROLL = OK + FAIL'])),
      not _dup and not _out
      and all(len(needg('inc', ['dword ptr [0x%x]' % GC[n]])) == 1 for n in _new),
      ' '.join('%s=%06X' % (n, GC[n]) for n in _new) + (' 重复%s 出界%s' % (_dup, _out)))
w('  身份式(手测时拿这三对数自证桩没漏记/重记): 每下一条指令 CMD+1; 过门就 ROLL+1, 没过门 REJECT+1;')
w('  掷了骰必落 OK 或 FAIL 之一 => OK + FAIL = ROLL, 且 OK <= 指令数; 若 CMD != ROLL+REJECT 就是有分支漏埋')
w('  手测配方: 给 %d 种活动各下 1 条(教席=自学) => CMD+=%d, ROLL+REJECT 应等于 %d; '
  '想必中就选 茶道/读兵书 + 主角教席 + 亲密拉满 + 低现值 (P 顶到 %d%%)'
  % (len(CG.ACTS), len(CG.ACTS), len(CG.ACTS), CG.P_MAX))

# ---------------- C26 M3d 教席三通道 ----------------
w('\n--- C26 M3d 教席三通道: 主角/父 T 能力驱动 + 长辈自动教席 (TEACH_LORD/PARENT) ---')
check('C26a 教席分发: 主角(1)/父(2) 走能力驱动, 其余(0/3/4)走常数表',
      len(needg('cmp', ['ecx, 1'])) == 1 and len(needg('cmp', ['ecx, 2'])) == 1
      and len(needg('movzx', ['ecx, byte ptr [ecx + 0x%x]' % V['TEACH_TAB']])) == 1,
      'teacher==1/2 分支 + 常数表读恰 1 处 (其余仍查 TEACH_TAB)')
check('C26b 主角 T 能力驱动: 取主角实体 0x49f5e0(2处) + min(30, 主维*25/100 + 身分)',
      len(needg('call', ['0x%x' % CG.PLAYER_ENT])) == 2
      and len(needg('imul', ['eax, eax, 0x19'])) == 2
      and len(needg('cmp', ['eax, 0x1e'])) == 2 and len(needg('mov', ['eax, 0x1e'])) == 2
      and len(needg('and', ['edx, 0x700'])) == 2
      and len(needg('cmp', ['dl, 7'])) == 2 and len(needg('cmp', ['dl, 6'])) == 2,
      '主角教席两处(指令圈 + 自动); 身分加成 大名7(+10)/重臣6(+5)')
check('C26c 父 T 能力驱动: 从排程表 fslot 推父实体 + min(28, 最高维*22/100)',
      len(needg('imul', ['edx, edx, 0x16'])) == 2
      and len(needg('cmp', ['eax, 0x1c'])) == 2 and len(needg('mov', ['eax, 0x1c'])) == 2
      and len(needg('mov', ['ecx, 0xf'])) == 1,
      '父教席两处(指令圈 + 自动); fslot==0xffff 退常数 15 (cg_t_const_parent 一处)')
check('C26d 资格判定 0x4b5620 复用(父同城才自动教)',
      len(needg('call', ['0x%x' % CG.QUALIFY])) == 1, 'cg_at_father 一处')
check('C26e 三通道埋点: TEACH_LORD/TEACH_PARENT 各恰 2 处自增, TEACH_SHOPE 仍 0',
      len(needg('inc', ['dword ptr [0x%x]' % GC['TEACH_LORD']])) == 2
      and len(needg('inc', ['dword ptr [0x%x]' % GC['TEACH_PARENT']])) == 2
      and len(needg('inc', ['dword ptr [0x%x]' % GC['TEACH_SHOPE']])) == 0,
      'SHOPE 待 M3c UI 选店, 本轮回常数表')
_tr = [(1, 80, None, 7, min(CG.T_LORD_CAP, 80 * CG.T_LORD_MUL // 0x64 + 0xa)),
       (1, 40, None, 0, min(CG.T_LORD_CAP, 40 * CG.T_LORD_MUL // 0x64)),
       (2, None, (50, 60, 70, 80, 90), 0, min(CG.T_FATH_CAP, 90 * CG.T_FATH_MUL // 0x64)),
       (2, None, (10, 10, 10, 10, 10), 0, min(CG.T_FATH_CAP, 10 * CG.T_FATH_MUL // 0x64)),
       (0, None, None, 0, CG.TEACHERS[0][1]),
       (4, None, None, 0, CG.TEACHERS[4][1])]
_mis = [(t, CG.T_of(t, p, f, ic), exp) for (t, p, f, ic, exp) in _tr if CG.T_of(t, p, f, ic) != exp]
check('C26f Python 参考 T_of 与文档公式(PLAN §2.4)逐值一致 (违例 %d)' % len(_mis), not _mis, str(_mis[:4]))

# ---------------- C23 M3c: 回家菜单「培养孩子」 ----------------
w('\n--- C23 M3c 回家菜单: 三处补丁字节 / 两块桩逐字节复现 / 四种 count 形态回环 ---')
import child_menu as CM
MU = LY['menu']
HVA, FVA = MU['hook_va'], MU['foster_va']
# ML 全部从 _big_layout.json 取 (与 build_big 同一张表, 换 CAP/偏移不用改本脚本)
ML = {'menu_ptr': V['MENU_PTR'], 'menu_code': V['MENU_CODE'], 'str_va': V['MENU_STR'],
      'pool': LY['pool_va'], 'bm': V['CHILD_BM'], 'kid': V['KID_TAB'], 'ring': V['CMD_RING'],
      'name_buf': V['NAME_BUF'], 'slot_arr': V['SLOT_ARR'], 'sub_ptr': V['SUB_PTR'],
      'act_ptr': V['ACT_PTR'], 'teach_ptr': V['TEACH_PTR'], 'tier_ptr': V['TIER_PTR'],
      'dec100': V['DEC100'],
      # 名字反的(老工具遗留): child_menu 的 giv 喂"抄姓"循环 => 姓表 = surname_tab_va; sur 喂"抄名"循环
      'giv': LY['surname_tab_va'], 'sur': LY['given_tab_va'],
      'cap': CAP, 'c_menu': GC['MENU_COUNT'], 'c_panel': GC['PANEL_OPEN'],
      'c_push': GC['CMD_PUSH'], 'c_notcity': GC['KID_NOTSAME_CITY'],
      'c_nav': GC['PAGE_NAV'], 'c_rows': GC['PAGE_ROWS'],
      'last_slot': GC['KID_LAST_SLOT'], 'last_act': GC['KID_LAST_ACT']}
# M3c-2: 培养详情面板的五个参数槽 + 入口 (与 build_big 同一张表)
PD = LY['panel']
ML.update({'kd_ent': PD['kd']['ent'], 'kd_slot': PD['kd']['slot'],
           'kd_act': PD['kd']['act'], 'kd_teach': PD['kd']['teach'],
           'kd_tier': PD['kd']['tier'], 'kd_show': PD['code_va']})
ML.update(CM.scratch_layout(V['MENU_SCR']))
# M5: 每月 1 次 / 花费 / 反馈 的地址与入口 (全部从 _big_layout.json 的 'm5' 表取)
_M5 = LY['m5']
ML.update({'f_ym': _M5['fo']['ym'], 'f_cnt': _M5['fo']['cnt'],
           'f_days': _M5['fo']['days'], 'f_gold': _M5['fo']['gold'],
           'msg_act': _M5['fo']['msg_act'], 'msg_slot': _M5['fo']['msg_slot'],
           'act_days': _M5['fo']['act_days'],
           # M5b: 菜单里复跑预载桩用的入口 (孩子所在城同步)
           'child_pass': V['CHILD_PASS'],
           'cost_arr': _M5['fo']['cost_arr'], 'msg_str': _M5['msg_str_va'],
           'confirm_ptr': _M5['fo']['confirm'],
           'deny_month_ptr': _M5['fo']['deny_month'],
           'deny_time_ptr': _M5['fo']['deny_time'],
           'deny_gold_ptr': _M5['fo']['deny_gold'],
           'kd_msg': _M5['msg_kd']})
hcode, _hsrc = CM.build_hook(HVA, ML)
fcode, _fsrc = CM.build_foster(FVA, ML)
hgot, fgot = bytes(E(HVA, len(hcode))), bytes(E(FVA, len(fcode)))
check('C23a 钩子 %dB @0x%06X 与 child_menu.build_hook() 逐字节一致' % (len(hcode), HVA),
      hgot == hcode, '钩尾 0x%06X' % (HVA + len(hcode)))
check('C23b 培养处理 %dB @0x%06X 与 child_menu.build_foster() 逐字节一致' % (len(fcode), FVA),
      fgot == fcode, '处理尾 0x%06X / MOD 尾 0x%06X' % (FVA + len(fcode), MODB + LY['mod_sz']))
# 0x47BED0 实机约定 (入口 mov edx,[esp+4] / test dx,dx / 拷贝循环 cmp ax,dx): arg1 = 条目数,
# arg2 = 串指针数组, arg3 = 样式。末推 = arg1, 必须是 ecx(=cnt+1); 把 s_flag(样式 2/4) 推在
# 末位会导致菜单只画 2 项且样式参数错 —— 2026-10-06 自宅界面卡死的根因, 此处钉死防回归。
_hins = list(md.disasm(hgot, HVA))
_dl = [i for i in _hins if i.mnemonic == 'call' and i.op_str == '0x%x' % CM.DIALOG]
_jh = _hins.index(_dl[0]) if _dl else 0
_hpre = [(x.mnemonic, x.op_str) for x in _hins[max(0, _jh - 3):_jh]] if _dl else []
check('C23b2 对话框实参顺序 (样式, 指针数组, 条目数): 末推=arg1=条目数, 0x47BED0 用 dx 作拷贝上界',
      len(_dl) == 1 and _hpre == [('push', 'dword ptr [0x%x]' % ML['s_flag']),
                                  ('push', 'edx'), ('push', 'ecx')],
      '实际 %s' % (_hpre,))
check('C23c 两块不重叠、处理 16B 对齐、都在 MOD_SZ 内',
      HVA + len(hcode) <= FVA and FVA % 0x10 == 0 and FVA + len(fcode) <= MODB + LY['mod_sz'],
      '钩 0x%06X(%dB) 处理 0x%06X(%dB) 余 %dB' % (HVA, len(hcode), FVA, len(fcode),
                                                  MODB + LY['mod_sz'] - FVA - len(fcode)))

# ---- 三处补丁: 站点原字节(对 clean) + 现字节(对目标) ----
HS, CL, T8 = CM.HOOK_MENU_SITE, CM.CODE_LIMIT_SITE, CM.TABLE8_SITE
check('C23d 钩站点 0x%06X: clean 上是 %s (= push ecx/push edx/push edi + call 前 2 字节), big 上 jmp 钩子'
      % (HS, CM.HOOK_MENU_ORIG.hex()),
      CLN[HS - CB:HS - CB + 5] == CM.HOOK_MENU_ORIG
      and bytes(AT(HS, 5)) == CM.jmp_rel(HS, HVA),
      'big=%s' % bytes(AT(HS, 5)).hex())
_hi = list(md.disasm(bytes(AT(HS, 5)), HS))[0]
check('C23e 钩子把原生 call 0x47BED0 整段接管: 被覆盖的 call 起点 0x%06X 之后无其他入口'
      % CM.DIALOG,
      _hi.mnemonic == 'jmp' and _hi.op_str == '0x%x' % HVA, '%s %s' % (_hi.mnemonic, _hi.op_str))
_win = bytearray(AT(0x4CD38E, 0x12))
check('C23f 上界 0x4CD390 = %d (clean 上 %d): 除这一个字节外与 clean 逐字节相同'
      % (_win[2], CLN[CL - CB]),
      _win[2] == 7 and CLN[CL - CB] == 6 and (lambda x: (x.__setitem__(2, 6), bytes(x))[1])(
          bytearray(_win)) == CLN[0x4CD38E - CB:0x4CD38E - CB + 0x12])
_c4 = {i.address: i for i in md.disasm(bytes(AT(0x4CD38E, 0x12)), 0x4CD38E)}
check('C23g 0x4CD38E 反汇编形态 = cmp eax,7 / ja 出环 0x%06X / movsx / jmp [eax*4+0x4CD460]'
      % CM.MENU_EXIT,
      _c4[0x4CD38E].op_str == 'eax, 7'
      and _c4[0x4CD391].mnemonic == 'ja' and _c4[0x4CD391].op_str == '0x%x' % CM.MENU_EXIT
      and _c4[0x4CD397].op_str == 'dword ptr [eax*4 + 0x4cd460]',
      ' '.join('%s %s' % (_c4[a].mnemonic, _c4[a].op_str) for a in sorted(_c4)))
_tbl = list(struct.unpack_from('<8I', bytes(AT(0x4CD460, 32)), 0))
_tab_cln = list(struct.unpack_from('<8I', CLN[0x4CD460 - CB:0x4CD460 - CB + 32], 0))
check('C23h 跳转表 0..6 槽逐字节未动 (原生 7 个处理一个没换)', _tbl[:7] == _tab_cln[:7],
      ' '.join('%d=%08X' % (i, v) for i, v in enumerate(_tbl)))
check('C23i 第 8 槽 = 培养处理: clean 上 0x%06X 是 4 字节对齐 NOP(90 90 90 90), big 上 = 0x%06X'
      % (T8, FVA), CLN[T8 - CB:T8 - CB + 4] == b'\x90' * 4 and _tbl[7] == FVA)
_drift = [hex(h) for h in _tbl[:7] if CLN[h - CB:h - CB + 8] != bytes(AT(h, 8))]
check('C23j 原生 7 个处理入口前 8 字节均未被本轮补丁蹭到', not _drift, str(_drift))

# ---- 弹窗容量: 上限是引擎事实, 从 big.exe 里现读, 不抄文档 ----
_dl = list(md.disasm(bytes(AT(0x47BE09, 0xC)), 0x47BE09))
_capmap = {i.address: i for i in _dl}
check('C23k 0x47BED0 的 12 项硬门仍在 (count<=0 或 >12 -> 返回 0xffff)',
      _capmap[0x47BE0C].mnemonic == 'jle' and _capmap[0x47BE0E].op_str == 'di, 0xc'
      and _capmap[0x47BE12].mnemonic == 'jg',
      ' '.join('%s %s' % (_capmap[a].mnemonic, _capmap[a].op_str) for a in sorted(_capmap)))

# ---- 构建器能发哪些指令码: 从它自己的字节里读 (立即数 store + 寄存器 store 两种形式) ----
# capstone 口径坑: 立即数 <10 渲染成十进制, >=10 渲染成 0x.. => 一律走 imm() 两式解析
def imm(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith('0x') else int(s, 10)


_bld = list(md.disasm(bytes(AT(0x4CD480, 0xD0)), 0x4CD480))
_ba = {i.address: i for i in _bld}
_codes = sorted({imm(i.op_str.rsplit(', ', 1)[1]) for i in _bld
                 if i.mnemonic == 'mov' and i.op_str.startswith('word ptr [esp')
                 and '+ 0xc]' in i.op_str})
# 码 1 金库 **不是立即数**写进去的, 而是 `mov word[esp+0xe], di` —— 只扫立即数就会漏 (踩过一次)
_rst = [i for i in _bld if i.mnemonic == 'mov' and i.op_str == 'word ptr [esp + 0xe], di']
_prev_edi = [i for i in _bld if i.mnemonic == 'mov' and i.op_str == 'edi, 1'
             and _bld.index(i) < _bld.index(_rst[0])] if _rst else []
check('C23l2 金库项(码 1)确由本构建器发出: `mov edi,1` 在 `mov word[esp+0xe], di` 之前, '
      '门 = `test cl,4`(byte[0x516638]&4) 置位则整条消失且 edi 停在 1',
      len(_rst) == 1 and len(_prev_edi) == 1
      and _ba[0x4CD498].op_str == 'cl, 4' and _ba[0x4CD4A7].mnemonic == 'jne',
      'store@0x%08X / mov edi,1@0x%08X / 门 jne -> %s' % (
          _rst[0].address if _rst else 0, _prev_edi[0].address if _prev_edi else 0,
          _ba[0x4CD4A7].op_str if 0x4CD4A7 in _ba else '?'))
if _rst and _prev_edi:
    _codes = sorted(set(_codes) | {1})
_lbl = {}
for c in _codes:
    _lbl[c] = gbk(bytes(AT(CM.CODE_STR_TAB + c * CM.CODE_STR_STRIDE, CM.CODE_STR_STRIDE))).strip()
w('  构建器 0x4CD480 会写的指令码 (exe 现读): %s' % ' '.join('%d=%s' % (c, _lbl[c]) for c in _codes))
check('C23l 原生码全在 0..6 且不含 7 (码 7 是我们独占的新路径)',
      _codes and max(_codes) <= 6 and 7 not in _codes, str(_codes))
check('C23m 原生构建器最多 %d 项, 我们追加 1 项 => 弹窗最多 %d 项, 远低于 12 硬门'
      % (CM.HOME_ITEM_MAX, CM.HOME_ITEM_MAX + 1), CM.HOME_ITEM_MAX + 1 <= MU['item_max'],
      '拷贝区实测: 串指针 +0x%X(0x40B) / 指令码 +0x%X(0x20B), 各容 16 项'
      % (V['MENU_PTR'] - MODB, V['MENU_CODE'] - MODB))

# ---- 四种 count 形态回环: 用 big.exe 里的钩子字节 + 表 + 调用方预判, 逐形态算落到哪个处理 ----
hm = list(md.disasm(hgot, HVA))
assert sum(len(i.bytes) for i in hm) == len(hgot), '钩子反汇编没吃满'


def needm(mn, *pats):
    return [i for i in hm if i.mnemonic == mn and all(p in i.op_str for p in pats)]


# 钩子决定量: 码 7 / 序号->码翻译基址 / 取消哨兵 / 追加项串指针 —— 全从 exe 反汇编里读
import re as _re
_imms = [imm(_re.match(r'eax, (.+)$', i.op_str).group(1))
         for i in hm if i.mnemonic == 'mov' and _re.match(r'eax, (0x[0-9a-f]+|\d+)$', i.op_str)]
FOSTER_CODE = [v for v in _imms if v != 0xffffffff]
check('C23n 钩子对调用方只回三种 eax: 取消 0xffffffff / 培养码 %s / 其余查码表自译'
      % FOSTER_CODE, len(FOSTER_CODE) == 1 and 0xffffffff in _imms, str([hex(v) for v in _imms]))
FOSTER_CODE = FOSTER_CODE[0]
_xl = needm('movzx', '[ecx*2 + 0x%x]' % V['MENU_CODE'])
check('C23n2 钩子自译: 序号->码 查的是我们自己拷的码表 0x%06X (原生 0x4CD583 那条已绕开)'
      % V['MENU_CODE'], len(_xl) == 1, _xl[0].op_str if _xl else '无')
_ap = [i for i in hm if i.mnemonic == 'mov' and 'dword ptr [edx + eax], 0x' in i.op_str]
_apva = imm(_ap[0].op_str.rsplit(', ', 1)[1]) if _ap else 0
_w0 = gbk(bytes(E(V['MENU_STR'], CM.STR_ROW))).strip()
check('C23o 追加项只有一项: 串池第 %d 行「%s」@0x%06X (%d 行 x %dB @0x%06X)'
      % (CM.S_HOME, _w0, _apva, MU['str_n'], MU['str_row'], V['MENU_STR']),
      len(_ap) == 1 and _apva == V['MENU_STR'] + CM.S_HOME * CM.STR_ROW, _w0)
check('C23n3 钩子按 count 比序号决定分支 (cmp cx,[s_cnt] -> 相等就是末项 -> 码 %d), '
      '翻译用码表步长 2 (ecx*2 寻址)' % FOSTER_CODE,
      len(needm('cmp', 'cx, word ptr [0x%x]' % ML['s_cnt'])) == 1
      and len(_xl) == 1)
check('C23p 码 %d 三处吻合: 钩子给的 eax / 0x4CD390 的上界 / 跳转表第 %d 槽 -> 0x%06X'
      % (FOSTER_CODE, FOSTER_CODE, _tbl[FOSTER_CODE]),
      FOSTER_CODE == 7 == _win[2] and _tbl[FOSTER_CODE] == FVA,
      '钩子 eax=%d / cmp 界=%d / 表[%d]=0x%08X' % (FOSTER_CODE, _win[2], FOSTER_CODE, _tbl[FOSTER_CODE]))
# 收尾必须是原生那五条指令的逐字节复刻 (pop edi/esi/ebp + add esp,0x24 + ret = 0x4CD577..0x4CD57D, 7 字节)
_epi_native = CLN[0x4CD577 - CB:0x4CD577 - CB + 7]
check('C23n4 钩子收尾 = 原生收尾逐字节 (%s): 帧/寄存器复原后才 ret, 循环状态与进来时一致'
      % _epi_native.hex(), hgot[-len(_epi_native):] == _epi_native, hgot[-7:].hex())
check('C23n5 对话框调用形态与原生同规格: 3 push + call 0x%06X + add esp,0x14 (两枚 0 参数由原生残段留在栈上)'
      % CM.DIALOG,
      len(needm('call', '0x%x' % CM.DIALOG)) == 1
      and len([i for i in hm if i.mnemonic == 'push']) == 3
      and len(needm('add', 'esp, 0x14')) == 1
      and len(needm('cmp', 'ax, -1')) == 1)
_pre = {i.address: i for i in md.disasm(bytes(AT(CM.MENU_CALL, 0x30)), CM.MENU_CALL)}
_pfx = {a: imm(_pre[a].op_str.split(', ')[1]) for a in (0x4CD36F, 0x4CD381)}
check('C23q 调用方预判仍在: ax==0xffff(取消) 与 ax==4(离开) 都直去 0x%06X, 不查表'
      % CM.MENU_PRE_EXIT,
      _pre[0x4CD36F].mnemonic == 'cmp' and _pfx[0x4CD36F] == 0xffff
      and _pfx[0x4CD381] == 4
      and _pre[0x4CD37B].op_str == '0x%x' % CM.MENU_PRE_EXIT
      and _pre[0x4CD385].op_str == '0x%x' % CM.MENU_PRE_EXIT,
      ' '.join('%s %s' % (_pre[a].mnemonic, _pre[a].op_str)
               for a in (0x4CD36F, 0x4CD37B, 0x4CD381, 0x4CD385)))


def route(codes, pick):
    """按 big.exe 里的字节解释一次「选了第 pick 项」: 返回 (回到调用方的 ax, 最终处理地址或说明)"""
    if pick is None:                                   # 取消
        return 0xffff, '出环@0x%06X (调用方 ax==0xffff 分支)' % CM.MENU_PRE_EXIT
    eax = FOSTER_CODE if pick == len(codes) else codes[pick]
    if eax == 4:
        return eax, '出环@0x%06X (原生「离开」, 表槽 4 也指 0x%06X)' % (CM.MENU_PRE_EXIT, _tbl[4])
    if eax > _win[2]:
        return eax, 'ja 出环 0x%06X' % CM.MENU_EXIT
    return eax, ('表槽%d -> 0x%08X%s' % (eax, _tbl[eax],
                                        ' [MOD 培养处理]' if eax == FOSTER_CODE else ' [原生]'))


FORMS = [('甲 全在(6 项)', [0, 1, 2, 3, 5, 4]), ('乙 金库隐藏(5 项)', [0, 2, 3, 5, 4]),
         ('丙 无宁宁/无探病(3 项)', [0, 1, 4]), ('丁 最短(2 项)', [0, 4])]
_native_dst = {'表槽%d -> 0x%08X [原生]' % (i, v) for i, v in enumerate(_tbl[:7]) if i != 4}
_mine_dst = '表槽%d -> 0x%08X [MOD 培养处理]' % (FOSTER_CODE, FVA)
bad, rows = [], []
for nm, cs in FORMS:
    if len(cs) + 1 > MU['item_max']:
        bad.append('%s 项数 %d 超弹窗上限' % (nm, len(cs) + 1))
    for pk in range(len(cs) + 1):
        _eax, _dst = route(cs, pk)
        rows.append('  %s pick=%d -> eax=%d -> %s' % (nm, pk, _eax, _dst))
        if pk == len(cs):
            if _dst != _mine_dst:
                bad.append('%s 末项没落到培养处理: %s' % (nm, _dst))
        elif _eax != 4 and _dst not in _native_dst:
            bad.append('%s pick=%d 落点异常: %s' % (nm, pk, _dst))
    _eax, _dst = route(cs, None)
    rows.append('  %s 取消   -> ax=0xffff -> %s' % (nm, _dst))
    if '出环' not in _dst:
        bad.append('%s 取消没出环: %s' % (nm, _dst))
for r in sorted(rows):
    w(r)
check('C23r 四种 count 形态逐 pick 回环: 原生项 -> 原生处理(表 0..6), 末项 -> 0x%06X, 取消 -> 出环'
      % FVA, not bad, str(bad))

# ---- 面板选到的孩子必须正是桩会消费的孩子: 三道门与成长桩同写法 ----
mf = list(md.disasm(fgot, FVA))
assert sum(len(i.bytes) for i in mf) == len(fgot), '培养处理反汇编没吃满'
_gm = [('儿童态 nibble=0xb', 'cmp', (', 0xb',)),
       ('+0x2d 高位为 1 就跳过(在岗门)', 'test', ('0x2d], 0x80',)),
       ('儿童位图 bt', 'bt', ())]


def _hit(ins, mn, pats):
    return [i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pats)]


def _hitx(ins, mn, exact):
    """精确操作数匹配: capstone 把 <10 的立即数渲染成十进制, 子串匹配会误命中 (如 '4' 命中 0x550e30)"""
    return [i for i in ins if i.mnemonic == mn and i.op_str == exact]


_sh = []
for nm, mn, pats in _gm:
    f, g = _hit(mf, mn, pats), _hit(mins_g, mn, pats)
    _sh.append('%s: 培养%d/成长%d' % (nm, len(f), len(g)))
    if len(f) < 1 or len(g) < 1:
        bad.append('门两边不同缺 %s 培养%d 成长%d' % (nm, len(f), len(g)))
w('  三道资格门命中数(培养/成长): %s' % ' ; '.join(_sh))
check('C23s 面板的三道资格门与成长桩同一条指令 (面板能选到的孩子 == 桩会消费的孩子)',
      not [b for b in bad if b.startswith('门两边不同缺')],
      'bit7 语义两头一致: 置 1 则跳过该槽 (jnz), 与 child_growth.py:211 同写法')
check('C23s2 同城筛用的是主角实体 +0x24 的同一个 word (孩子 +0x24 == esp+4 里存的父城)',
      len(_hit(mf, 'cmp', ('dx, word ptr [esp + 4]',))) == 1
      and len(_hit(mf, 'movzx', ('eax, word ptr [esi + 0x24]',))) == 1,
      '面板入口把 esi(主角实体) 的 +0x24 存进局部, 扫描时逐个孩子比它')


def _slot_addr_seq(ins, reg):
    """槽 -> 实体指针 的四指令地址式: lea <reg>,[eax+eax*2] / shl / sub / add <reg>,池基"""
    k = [j for j, i in enumerate(ins)
         if i.mnemonic == 'add' and i.op_str == '%s, 0x%x' % (reg, LY['pool_va'])]
    if not k or k[0] < 3:
        return []
    return [(ins[j].mnemonic, ins[j].op_str) for j in range(k[0] - 3, k[0] + 1)]


_f_addr, _g_addr = _slot_addr_seq(mf, 'ecx'), _slot_addr_seq(mins_g, 'ebp')
check('C23t 槽->实体 的地址式与成长桩同一条流水线 (%s)' % ' / '.join('%s %s' % x for x in _f_addr),
      len(_f_addr) == 4 and len(_g_addr) == 4
      and _f_addr == [(m, o.replace('ebp', 'ecx')) for m, o in _g_addr],
      '培养 %s vs 成长 %s (两边都是 47*槽 + 池基 0x%06X)' % (_f_addr, _g_addr, LY['pool_va']))
_bm = '0x%x' % V['CHILD_BM']
_bm_all = [i for i in mf if _bm in i.op_str]
_bm_wr = [i for i in _bm_all if 'ptr [' in i.op_str.split(', ', 1)[0]]
check('C23u 儿童位图 @0x%06X 在面板里只出现 %d 次、且没有一次是写它 (位图归预载/成长桩)'
      % (V['CHILD_BM'], len(_bm_all)), len(_bm_all) == 1 and not _bm_wr,
      ' / '.join('%s %s' % (i.mnemonic, i.op_str) for i in _bm_all))


def _offs(ins, reg):
    """把 `[reg]` / `[reg + N]` 的内存写读按偏移收出来 (capstone: 位移 <10 用十进制)。
    只收纯数字位移; [reg+reg2+N] 这类双寄存器寻址(读五维)不是圈条目偏移, 跳过。"""
    out = set()
    for i in ins:
        head = 'ptr [%s' % reg
        if head in i.op_str:
            seg = i.op_str.split(head, 1)[1]
            if seg.startswith(']'):
                out.add(0)
            elif seg.startswith(' + '):
                num = seg[3:].split(']')[0].strip()
                try:
                    out.add(imm(num))
                except ValueError:
                    pass  # [reg + reg2 + N] 双寄存器寻址, 非圈条目偏移
    return out


_wr, _rd = _offs(mf, 'eax'), _offs(mins_g, 'ebx')
check('C23v 圈条目偏移两头吻合: 培养写 %s, 成长读 %s (必须含 +0 槽 / +1 活动 / +2 教席 / +3 档次)'
      % (sorted(_wr), sorted(_rd)), {0, 1, 2, 3} <= _wr and {0, 1, 2, 3} <= _rd,
      '写%s 读%s' % (sorted(_wr), sorted(_rd)))
_tl = V['CMD_RING'] + 4
_tl_rd = [i for i in mf if i.mnemonic == 'mov' and i.op_str.endswith('dword ptr [0x%x]' % _tl)]
_tl_wr = [i for i in mf if i.op_str.startswith('dword ptr [0x%x], ' % _tl)]
_head = [i for i in mf if 'dword ptr [0x%x]' % V['CMD_RING'] in i.op_str]
check('C23w UI 只动 tail(读 2 次: 取槽位 + 自增回写; 写 1 次), 全程不提 head 0x%06X —— 与 C22c 对偶'
      % V['CMD_RING'],
      len(_tl_rd) == 2 and len(_tl_wr) == 1 and not _head,
      'tail 读%d 写%d, head 提及%d' % (len(_tl_rd), len(_tl_wr), len(_head)))
check('C23x 写入位下标两头同构: 培养 (tail&0x3f)<<3 + 圈条目基 0x%06X / 成长 lea ebx,[eax*8 + 同基]'
      % (V['CMD_RING'] + 8),
      len(_hit(mf, 'and', ('0x3f',))) == 1 and len(_hit(mf, 'shl', ('eax, 3',))) >= 1
      and _hit(mf, 'add', ('0x%x' % (V['CMD_RING'] + 8),))
      and _hit(mins_g, 'lea', ('ebx, [eax*8 + 0x%x]' % (V['CMD_RING'] + 8),)),
      '培养 and 0x3f -> shl eax,3 -> add eax,0x%06X ; 成长 lea ebx,[eax*8 + 0x%06X]'
      % (V['CMD_RING'] + 8, V['CMD_RING'] + 8))

# 数据区: 串池 / DEC100 / 三级静态子菜单指针数组 = 模块定义 (名字只有一个来源)
_sp = bytes(E(V['MENU_STR'], MU['str_n'] * MU['str_row']))
check('C23y 串池 %d 行 x %dB @0x%06X 逐字节 = child_menu.str_pool_bytes()'
      % (MU['str_n'], MU['str_row'], V['MENU_STR']), _sp == CM.str_pool_bytes(),
      ' | '.join(gbk(_sp[i * CM.STR_ROW:(i + 1) * CM.STR_ROW]) for i in range(MU['str_n'])))
check('C23z DEC100 200B @0x%06X = "00".."99" (姓名行的年龄后缀查它, 桩里不做除法)'
      % V['DEC100'], bytes(E(V['DEC100'], 0xC8)) == CM.dec100_bytes())
check('C23z1 年龄取自原生 getter 0x%06X 且一律 movzx eax,ax (它把 eax 当 16 位累加用, 高 16 位是垃圾), '
      '再钳到 %d' % (CM.AGE_GET, CM.AGE_GET_MASK),
      len(_hit(mf, 'call', ('0x%x' % CM.AGE_GET,))) == 1
      and len(_hit(mf, 'movzx', ('eax, ax',))) >= 1
      and len(_hit(mf, 'cmp', ('eax, 0x%x' % CM.AGE_GET_MASK,))) == 1)
_sub = {'一级(活动)': (V['ACT_PTR'], CM.S_ACT0, len(CG.ACTS)),
        '二级(教席)': (V['TEACH_PTR'], CM.S_TEACH0, len(CG.TEACHERS)),
        '三级(档次)': (V['TIER_PTR'], CM.S_TIER0, len(CM.TIER_NAMES))}
_mis = []
for nm, (va, first, n) in _sub.items():
    got = list(struct.unpack_from('<%dI' % (n + 1), bytes(E(va, (n + 1) * 4)), 0))
    want = list(struct.unpack('<%dI' % (n + 1), CM.submenu_ptr_bytes(V['MENU_STR'], first, n)))
    if got != want:
        _mis.append((nm, ['%08X' % g for g in got], ['%08X' % x for x in want]))
    for p in got:
        if not (V['MENU_STR'] <= p < V['MENU_STR'] + MU['str_n'] * MU['str_row']
                and (p - V['MENU_STR']) % MU['str_row'] == 0):
            _mis.append((nm, '%08X 不在串池行首' % p))
    w('  %s: %d 项 + 暂不培养 = %s' % (nm, n,
        ' / '.join(gbk(bytes(E(p, CM.STR_ROW))) for p in got)))
check('C23z2 三级静态子菜单指针数组逐项落在串池行首 (= child_menu.submenu_ptr_bytes, 串名唯一源)',
      not _mis, str(_mis))
# M5 起培养处理里一共 8 次 0x47BED0: 三级子菜单 3 个 + 选孩子 1 个 (原 4)
#                                   + 提交前的确认框 1 个 + 三道门禁被拒时的提示框 3 个
_N_DLG = 9
check('C23z3 培养处理共 %d 次弹窗 (三级子菜单 3 + 选孩子 1 + M5 确认 1 + 门禁拒绝 3) '
      '且全部用 flag=4 (独立子菜单口径, 见 0x445758/0x412E64)' % _N_DLG,
      len(_hitx(mf, 'push', '4')) == _N_DLG and len(_hit(mf, 'call', ('0x%x' % CM.DIALOG,))) == _N_DLG
      and len(_hit(mf, 'add', ('esp, 0x14',))) == _N_DLG,
      'push 4 x%d / call 0x%06X x%d' % (len(_hitx(mf, 'push', '4')), CM.DIALOG,
                                        len(_hit(mf, 'call', ('0x%x' % CM.DIALOG,)))))
# ★ M5 费用确认框是 3 项: [0] 费用行(这条活动要多少天/多少金) [1] 就这么办 [2] 再想想。
#   只有选中 1 才真的办 —— 用 cmp ax,1 + jne, 不能照抄旧写的 test ax,ax(费用行在 0 号位)。
_c1 = _hitx(mf, 'cmp', 'ax, 1')
check('C23z3b M5 费用确认框按 cmp ax,1 判办不办 (只有「就这么办」生效; '
      '选中费用行/再想想/取消 0xffff 一律放弃), 恰 1 处',
      len(_c1) == 1 and mf[mf.index(_c1[0]) + 1].mnemonic == 'jne',
      'cmp 后一条: %s' % (mf[mf.index(_c1[0]) + 1].mnemonic if _c1 else '-'))
# 确认框是 3 项 -> push 3 恰 1 次, 指针数组用 FOSTER 区那个 3 槽暂存 (不用构建期的旧 2 槽 confirm_ptr)
check('C23z3b2 确认框 3 项 (push 3 恰 1 处) 且指针来自运行时拼的 cost_arr 0x%06X' % _M5['fo']['cost_arr'],
      len(_hitx(mf, 'push', '3')) == 1
      and len(_hitx(mf, 'push', '0x%x' % _M5['fo']['cost_arr'])) == 1,
      'push 3 x%d / push cost_arr x%d' % (len(_hitx(mf, 'push', '3')),
                                          len(_hitx(mf, 'push', '0x%x' % _M5['fo']['cost_arr']))))
# 费用行 = 池首 + (MS_COST0 + act) * 行宽 —— 三处相邻 dword 写正好 = 指针数组 [0..2]
_roww = _M5['msg_row']
_c0 = _M5['ms_cost0']
_ca = _M5['fo']['cost_arr']
check('C23z3c 费用行地址 = %s + act*%d (%s) -> 三槽指针数组 [0]=费用行 [1]=就这么办 [2]=再想想'
      % ('0x%06X' % _c0, _roww, ' / '.join(CM.MSG_STRINGS[CM.MS_COST0:CM.MS_COST0 + 3])),
      len(_hitx(mf, 'imul', 'eax, ecx, %s' % (('%d' % _roww) if _roww < 10 else ('0x%x' % _roww)))) == 1
      and len(_hitx(mf, 'add', 'eax, 0x%x' % _c0)) == 1
      and len(_hitx(mf, 'mov', 'dword ptr [0x%x], eax' % _ca)) == 1
      and len(_hitx(mf, 'mov', 'dword ptr [0x%x], 0x%x' % (_ca + 4, _M5['ms_ok']))) == 1
      and len(_hitx(mf, 'mov', 'dword ptr [0x%x], 0x%x' % (_ca + 8, _M5['ms_cancel']))) == 1
      and len(CM.MSG_STRINGS) == CM.MS_NONE + 1,
      '串池 %d 条 / 期望 %d' % (len(CM.MSG_STRINGS), CM.MS_NONE + 1))
# 每条活动一条费用串, 且天/金与 child_growth 的表逐条对得上 (换表就炸, 不给口径漂移留口子)
_cbad = []
for _i, (_nm, _d, _b) in enumerate(CG.ACTS):
    _s = CM.MSG_STRINGS[CM.MS_COST0 + _i]
    _want = u'%s：%d天/%d文' % (_nm, CG.ACT_DAYS[_i], CG.ACT_DAYS[_i] * CG.GOLD_PER_DAY)
    _got = gbk(bytes(E(_M5['ms_cost0'] + _i * _roww, _roww)))
    if _s != _want or _got != _want:
        _cbad.append((_i, _s, _got, _want))
check('C23z3d 10 条费用串与 child_growth.ACT_DAYS/GOLD_PER_DAY 逐条一致且已落进串池 (%s)'
      % ' / '.join(CM.MSG_STRINGS[CM.MS_COST0:CM.MS_COST0 + 3]),
      not _cbad, str(_cbad[:3]))
# ★★ 今日事故簿: 0x4A0D50 是 cdecl, 调用方必须 add esp,8 —— 漏了就是"日期狂奔"
_adv = _hit(mf, 'call', ('0x%x' % CG.ADVANCE_DAY,))
check('C23z3e 推天数走 0x%06X: 恰 1 处, 且紧跟 add esp,8 (cdecl 调用方清栈) —— '
      '漏这条 => pop ecx 每轮捡回残留实参 0x18 => 死循环 + 日期永远停不下来' % CG.ADVANCE_DAY,
      len(_adv) == 1 and mf[mf.index(_adv[0]) + 1].mnemonic == 'add'
      and mf[mf.index(_adv[0]) + 1].op_str == 'esp, 8'
      and len(_hitx(mf, 'add', 'esp, 8')) == 1,
      'call 后一条: %s' % (('%s %s' % (mf[mf.index(_adv[0]) + 1].mnemonic,
                                      mf[mf.index(_adv[0]) + 1].op_str)) if _adv else '-'))
# ★★ 今日事故簿三: 反馈小框的两处形态错 (2026-10-07 实机反馈「培养后界面怎么乱了」)
#   ① 串池行 = [GBK][NUL][pad], **没有长度前缀**。照抄 kid_panel 自己那套池的解码
#      (`mov ecx,[eax]` + `and ecx,0xff`) 就会把汉字高字节(0xb4/0xd5/...)当成长度,
#      一次 TextOut 糊出 180~213 字节 = 连画 8 行串池 -> 屏幕上几串跨行乱字。
#   ② 居中写成 (wx0 + MW)/2 而不是 (wx0 + wx1)/2 -> 三行文字全甩到黑框左边外侧,
#      框里空空如也 (名字之所以还能看见, 是因为它落在框外)。
_kb = bytes(E(_M5['msg_kd'], 0x340))
import kid_panel as _KPi        # 就地导入: 本节的 r_wx1 地址要与面板桩同源, 不能另抄一份
_wx1va = _KPi.RSTATE_VA + _KPi.RS['WX1']
_nlen = _kb.count(b'\x83\xe1\xff')          # and ecx, 0xff
_nneg = _kb.count(b'\x6a\xff')              # push -1
_nscan = _kb.count(b'\x80\x3c\x0f\x00')     # cmp byte ptr [edi + ecx], 0   (数到 NUL)
_nbound = _kb.count(b'\x83\xf9' + bytes([CM.MS_STR_ROW]))   # cmp ecx, 行宽
check('C23z3g 反馈小框两行台词不传 -1 (本机 TextOutA 传 -1 一个字都不画),'
      ' 也不把首字节当长度: 自己数到 NUL 且带行宽上界',
      _nlen == 0 and _nneg == 0 and _nscan == 2 and _nbound == 2,
      'and ecx,0xff x%d / push -1 x%d / 数 NUL x%d / 行宽界 x%d'
      % (_nlen, _nneg, _nscan, _nbound))
_ncen = _kb.count(b'\x03\x05' + _wx1va.to_bytes(4, 'little'))   # add eax, dword ptr [wx1]
check('C23z3h 反馈小框三行居中一律 (wx0+wx1)/2 —— add eax,[0x%06X] 恰 3 处'
      ' (写成 (wx0+MW)/2 时文字会跑到框外)' % _wx1va,
      _ncen == 3, 'add eax,[wx1] x%d' % _ncen)
# ★ 槽守卫必须 = 姓名表有效行数(654), 不能图省事写 0x40: 本批孩子实体在槽 463..476,
#   守卫写小 => kd_msg 头两行就 jae 走人 => 反馈框永远不弹 (比乱码更难查, 因为"什么都没发生")。
_gmax = None
for _k in range(0x28):
    if _kb[_k] == 0x3d:
        _gmax = int.from_bytes(_kb[_k + 1:_k + 5], 'little')
        break
check('C23z3i 反馈小框的槽守卫 = 姓名表行数 %d (0x%X), 不是随手写的小常数'
      % (_KPi.NAME_TAB_ROWS, _KPi.NAME_TAB_ROWS),
      _gmax == _KPi.NAME_TAB_ROWS and _KPi.SLOT_MAX_MSG == _KPi.NAME_TAB_ROWS,
      'cmp eax, 0x%X' % (_gmax if _gmax is not None else 0))
_gd = _hitx(mf, 'test', 'ecx, ecx')
check('C23z3f 天数为 0 时不进推进循环 (test ecx,ecx + je, 防 dec 绕回 4G 次)',
      len(_gd) == 1 and mf[mf.index(_gd[0]) + 1].mnemonic == 'je',
      'test 后一条: %s' % (mf[mf.index(_gd[0]) + 1].mnemonic if _gd else '-'))
# ★★ M5b 事故 (2026-10-07 实机): 「每次进城回家, 点培养孩子就不行了, 非要等下一个月」。
#   名单按「孩子所在城 == 主角所在城」筛, 而孩子的城只在 child_pass 里随父亲同步
#   (make_child 首建 + 月钩 rearm) => 主角一移动, 孩子还挂在上一个城, 名单空到下次月钩。
#   修法 = 扫名单之前复跑一遍 child_pass (自包含 + 幂等, rearm 路径里就有 place_child)。
_cp_ = _hit(mf, 'call', ('0x%x' % PASS,))
_kd_ = _hit(mf, 'call', ('0x%x' % _M5['msg_kd'],))
_ks_ = _hit(mf, 'call', ('0x%x' % LY['panel']['code_va'],))
_ad_ = _hit(mf, 'call', ('0x%x' % CG.ADVANCE_DAY,))
check('C23z3j 菜单一开先复跑 child_pass 同步孩子所在城 (在扫名单/弹详情面板之前)'
      ' —— 否则主角换城后名单空到下次月钩',
      len(_cp_) == 1 and len(_ks_) == 1 and mf.index(_cp_[0]) < mf.index(_ks_[0]),
      'call child_pass x%d @%s < call kd_show @%s'
      % (len(_cp_), hex(_cp_[0].address) if _cp_ else '-',
         hex(_ks_[0].address) if _ks_ else '-'))
check('C23z3k 孩子台词框必须在推天数之前弹出 (0x4A0D50 会触发原生每日事件的对话,'
      ' 否则玩家看到的是「大名的对话后孩子才出现」)',
      len(_kd_) == 1 and len(_ad_) == 1 and mf.index(_kd_[0]) < mf.index(_ad_[0]),
      'kd_msg @%s < ADVANCE_DAY @%s'
      % (hex(_kd_[0].address) if _kd_ else '-', hex(_ad_[0].address) if _ad_ else '-'))
# ★ M5b: 首屏一个孩子都扫不到时明说一句。原来是静默 return, 玩家只看到"点了没反应",
#   连"是没孩子"还是"门禁拦了"都分不出来 —— 就是前两轮实机反馈卡住的歧义点。
_none_va = _M5['msg_str_va'] + CM.MS_NONE * CM.MS_STR_ROW
_none_b = bytes(E(_none_va, CM.MS_STR_ROW))
check('C23z3l 首屏扫不到孩子时弹「%s」而非静默回菜单 (提示串已落池并被打死地址引用)'
      % CM.MSG_STRINGS[CM.MS_NONE],
      CM.MSG_STRINGS[CM.MS_NONE] == u'此城还没有可培养的孩子'
      and _none_b.split(b'\x00')[0] == CM.MSG_STRINGS[CM.MS_NONE].encode('gbk')
      and len(_hitx(mf, 'push', '0x%x' % _none_va)) == 1
      and len(_hitx(mf, 'cmp', 'dword ptr [esp + 0x2c], 0')) == 2,
      '串[%d] @0x%06X = %r / push x%d / 空页判定 x%d'
      % (CM.MS_NONE, _none_va, _none_b.split(b'\x00')[0].decode('gbk', 'replace'),
         len(_hitx(mf, 'push', '0x%x' % _none_va)),
         len(_hitx(mf, 'cmp', 'dword ptr [esp + 0x2c], 0'))))
# 三道门禁被拒时各弹一次「单选项」提示框 (arg1=1, 只有「知道了」), 与四级菜单的动态 count 写法不同
check('C23z3c 三道门禁拒绝框 + 「此城无孩子」各 1 次单选项弹窗 (push 1 + call DIALOG 相邻), 合计 4 次',
      len(_hitx(mf, 'push', '1')) >= 4
      and sum(1 for a, b in zip(mf, mf[1:])
              if a.mnemonic == 'push' and a.op_str == '1'
              and b.mnemonic == 'call' and b.op_str == '0x%x' % CM.DIALOG) == 4,
      'push1+call 相邻 x%d' % sum(1 for a, b in zip(mf, mf[1:])
                                  if a.mnemonic == 'push' and a.op_str == '1'
                                  and b.mnemonic == 'call' and b.op_str == '0x%x' % CM.DIALOG))
check('C23z4 每层取消都退回出口 (cmp ax,-1 -> je cm_exit), 取消不落圈; 越界也一律拒绝 (cmp ax,表长 -> jae)',
      len(_hitx(mf, 'cmp', 'ax, -1')) == 4 and len(_hit(mf, 'jae', ())) >= 4,
      'cmp ax,-1 x%d / jae x%d (含扫描侧 2 条)' % (len(_hitx(mf, 'cmp', 'ax, -1')),
                                                  len(_hit(mf, 'jae', ()))))
_pi = CM.cap_imm(CM.PAGE_KIDS)
check('C23z5 一级"选孩子"每页压在 PAGE_KIDS=%d (cmp [esp+0xc],%s), 加两行导航 = %d <= 弹窗硬门 %d, '
      '且验收用的每页数 == 构建档记的 %s'
      % (CM.PAGE_KIDS, _pi, CM.PAGE_KIDS + 2, MU['item_max'], MU.get('page_kids')),
      len(_hitx(mf, 'cmp', 'dword ptr [esp + 0xc], %s' % _pi)) == 1
      and CM.PAGE_KIDS + 2 <= MU['item_max'] and MU.get('page_kids') == CM.PAGE_KIDS,
      '原生 0x47BE00: cmp di,0xc / jg 0x47BE8A -> or ax,0xffff, 连窗口都不建 => 总数必须 <=12。'
      'TKID_PAGE_KIDS 只改每页数, 构建与验收两边必须同一个值')
# 分页导航: 哨兵写进行表 + 靠哨兵分派 (行号在"只有单侧导航"时会撞车, 所以不用行号)
_sa = 'word ptr [eax*2 + 0x%x]' % V['SLOT_ARR']
_z5b = [('下一页哨兵 0xfffe', len(_hit(mf, 'mov', (_sa, '0xfffe'))), 1),
        ('上一页哨兵 0xfffd', len(_hit(mf, 'mov', (_sa, '0xfffd'))), 1),
        ('按行读回哨兵', len(_hit(mf, 'movzx', ('edx, ' + _sa))), 1),
        ('cmp edx, 0xfffe', len(_hitx(mf, 'cmp', 'edx, 0xfffe')), 1),
        ('cmp edx, 0xfffd', len(_hitx(mf, 'cmp', 'edx, 0xfffd')), 1),
        ('起点 += 一页', len(_hitx(mf, 'add', 'dword ptr [esp + 0x2c], %s' % _pi)), 1),
        ('起点 -= 一页', len(_hitx(mf, 'sub', 'dword ptr [esp + 0x2c], %s' % _pi)), 1),
        ('行号变量 +0x34 不提', len([i for i in mf if '0x34]' in i.op_str]), 0)]
check('C23z5b 导航用行内哨兵(0xfffe/0xfffd)自证身份: %s' % ' ; '.join('%s=%d' % (n, g) for n, g, _ in _z5b),
      all(g == want for _, g, want in _z5b),
      '两条导航各写一次哨兵, 选中后先读哨兵再分派; 只有单侧导航时也不会把"上一页"当成"下一页"')
_pg = [i for i in mf if i.mnemonic == 'mov' and i.op_str == 'dword ptr [esp + 8], 0']
_back = [i for i in mf if i.mnemonic == 'jmp' and _pg and i.op_str == '0x%x' % _pg[0].address]
check('C23z5c 页首复位点唯一(%s), 且"下一页/上一页"两条分支各跳回它一次(共 %d 条 jmp), 换页后整池重扫'
      % (_pg[0].op_str if _pg else '?', len(_back)),
      len(_pg) == 1 and len(_back) == 2,
      'cm_page 把 行表计数/指针数组计数/同城累计 清零, 起点 L_START 保留')


def _sim_pages(total, page=None):
    """照 SRC_FOSTER 的控制流正向走一遍: 每页都整池重扫 (cm_scan), 绝对起点 L_START 只加减不做乘除。
    返回 [(本页孩子的绝对下标, 有下一页, 有上一页, 起点)] —— 与 cm_same/cm_scan_end 四道门一一对应。"""
    page = CM.PAGE_KIDS if page is None else page
    out, start = [], 0
    while True:
        rows, match = [], 0
        for idx in range(total):                            # cm_scan -> cm_same
            if idx >= start and len(rows) < page:            # L_MATCH>=L_START 且 行表未满
                rows.append(idx)
            match += 1                                       # cm_count: 同城累计不分页
        nxt = match > len(rows) + start                      # cm_scan_end: 还有下一页吗
        out.append((rows, nxt, start > 0, start))
        if not nxt:
            return out
        start += page


def _sim_click(pages, pi, which):
    """按哨兵分派一次点击: 返回跳去的页号 (kid 返回 None)"""
    _rows, _nxt, _prv, _start = pages[pi]
    if which == 0xFFFE and _nxt:
        return pi + 1
    if which == 0xFFFD and _prv:
        return pi - 1
    return None


_sim_bad = []
for _n in (0, 1, 9, 10, 11, 19, 20, 21, 29, 40):
    _pages = _sim_pages(_n)
    _flat = [i for p in _pages for i in p[0]]
    if _n and (sorted(_flat) != list(range(_n)) or len(_flat) != len(set(_flat))):
        _sim_bad.append('N=%d 覆盖 %d/%d 且%s' % (_n, len(set(_flat)), _n,
                                                  '无重复' if len(_flat) == len(set(_flat)) else '有重复'))
    for _pi, (_rows, _nxt, _prv, _start) in enumerate(_pages):
        _cnt = len(_rows) + (1 if _nxt else 0) + (1 if _prv else 0)
        if _cnt > MU['item_max']:
            _sim_bad.append('N=%d 第%d页 %d 行 > 硬门 %d' % (_n, _pi, _cnt, MU['item_max']))
        if len(_rows) > CM.PAGE_KIDS:
            _sim_bad.append('N=%d 第%d页 孩子 %d > PAGE_KIDS' % (_n, _pi, len(_rows)))
        if _nxt != (_pi + 1 < len(_pages)):
            _sim_bad.append('N=%d 第%d页 下一页旗 %s 与实际页数 %d 不符' % (_n, _pi, _nxt, len(_pages)))
        if _prv != (_start > 0) or _prv != (_pi > 0):
            _sim_bad.append('N=%d 第%d页 上一页旗 %s (起点 %d)' % (_n, _pi, _prv, _start))
        # 行表 -> 哨兵 -> 分派: 逐行验证"选中这一行去做什么", 单侧导航时也不能走歪
        _nav = (['next'] if _nxt else []) + (['prev'] if _prv else [])
        _tbl = [(i, 'kid') for i in _rows] + \
               [(0xFFFE if t == 'next' else 0xFFFD, t) for t in _nav]
        for _ri, (_sent, _want) in enumerate(_tbl):
            if _want == 'kid' and _sent >= LY['cap']:
                _sim_bad.append('N=%d 第%d页 第%d行 槽值 %s 撞哨兵区' % (_n, _pi, _ri, _sent))
            _go = 'next' if _sent == 0xFFFE else ('prev' if _sent == 0xFFFD else 'kid')
            if _go != _want:
                _sim_bad.append('N=%d 第%d页 第%d行 分派 %s != %s' % (_n, _pi, _ri, _go, _want))
            if _go != 'kid':
                _t = _sim_click(_pages, _pi, _sent)
                if _t is None or not (0 <= _t < len(_pages)):
                    _sim_bad.append('N=%d 第%d页 %s 跳到 %s (越界或原地)' % (_n, _pi, _go, _t))
    # 点"上一页"能退回去、退回去还能再往前
    if len(_pages) > 1:
        _last = len(_pages) - 1
        if _sim_click(_pages, _last, 0xFFFD) != _last - 1:
            _sim_bad.append('N=%d 末页上一页退不回第 %d 页' % (_n, _last - 1))
        if _sim_click(_pages, 0, 0xFFFD) is not None:
            _sim_bad.append('N=%d 首页不该有上一页' % _n)
        if _sim_click(_pages, _last, 0xFFFE) is not None:
            _sim_bad.append('N=%d 末页不该有下一页' % _n)
check('C23z5d 分页仿真 N in {0,1,9,10,11,19,20,21,29,40}: 每页 <=12 行、孩子 <=%d、全员可达不重复、'
      '导航只在需要时出现、点两侧导航都落在正确页' % CM.PAGE_KIDS,
      not _sim_bad, ' | '.join(_sim_bad[:6])
      or '19 人 -> 10+下一页 / 9+上一页(共 2 页); 29 人 -> 3 页; <=10 人无导航行, 与改造前逐字节同行为')
check('C23z5e 孩子槽撞不上哨兵: 槽上界 CAP=%d < 0xFFFD' % LY['cap'], LY['cap'] <= 0xFFFD)
_navtxt = []
for _nm, _si in (('下一页', CM.S_NEXT), ('上一页', CM.S_PREV)):
    _b = bytes(E(V['MENU_STR'] + _si * MU['str_row'], MU['str_row'])).split(b'\0')[0]
    _navtxt.append('%s@行%d=%s' % (_nm, _si, gbk(_b)))
    if gbk(_b) != _nm:
        _navtxt.append('X')
check('C23z5f 导航两行的字面在 exe 串池里读得回来 (%s), 且指针各写一次指向自己的行首' % ' / '.join(_navtxt),
      'X' not in _navtxt
      and len([i for i in mf if i.mnemonic == 'mov' and i.op_str.startswith(
          'dword ptr [eax*4 + 0x%x], 0x%x' % (V['SUB_PTR'], V['MENU_STR'] + CM.S_NEXT * MU['str_row']))]) == 1
      and len([i for i in mf if i.mnemonic == 'mov' and i.op_str.startswith(
          'dword ptr [eax*4 + 0x%x], 0x%x' % (V['SUB_PTR'], V['MENU_STR'] + CM.S_PREV * MU['str_row']))]) == 1,
      '串池 %d 行 x %dB 的第 %d/%d 行' % (MU['str_n'], MU['str_row'], CM.S_NEXT, CM.S_PREV))

# 埋点: 面板侧计数各恰 1 处自增/写入, 且与成长桩埋点不重号
_c23 = [('PANEL_OPEN(面板开合)', 'PANEL_OPEN', 1), ('CMD_PUSH(下指令)', 'CMD_PUSH', 1),
        ('KID_NOTSAME_CITY(同城筛)', 'KID_NOTSAME_CITY', 1),
        ('PAGE_NAV(下一页/上一页被点)', 'PAGE_NAV', 2)]     # 2 = 两条导航分支各一次
_inc = {n: _hit(mf, 'inc', ('dword ptr [0x%x]' % GC[k],)) for n, k, _ in _c23}
_exp23 = {n: want for n, _, want in _c23}
_m23 = [n for n, l in _inc.items() if len(l) != _exp23[n]]
_out23 = [n for n, k, _ in _c23 if not (MODB <= GC[k] < MODB + LY['mod_sz'])]
_dup23 = sorted({n for n in GC if list(GC.values()).count(GC[n]) > 1})
check('C23z6 面板 %d 个自增埋点处数与语义吻合、都在 MOD 区内的 %d 字节埋点表里、全表 %d 个埋点两两不重号'
      % (len(_c23), LY['menu']['cnt_bytes'], len(GC)), not _m23 and not _out23 and not _dup23,
      '次数 %s 出界%s 重号%s' % ({n: len(l) for n, l in _inc.items()}, _out23, _dup23))
_rw23 = _hit(mf, 'mov', ('dword ptr [0x%x], eax' % GC['PAGE_ROWS'],))
# 「四级选项弹窗」的判据 = 紧邻前一条 push 的**条数实参**对得上源码常量:
#     选孩子 = push eax (扫出来的行数, 运行时算); 活动 / 教席 / 档次 = push (N+1) 的编译期常量。
#   别拿"所有 DIALOG 调用"当分母: M5b 加的「此城还没有可培养的孩子」提示框在 cm_scan_end,
#     地址比 PAGE_ROWS 写入点还低, 会把这条断言带偏; 三拒绝框(push 1)、M5 确认框(push 3)同理。
#   也别拿"紧邻前一条是 push ecx"当判据: 四级收尾分别是 push eax / 0xb / 6 / 5, 没有一个是 ecx。
def _imm23(v):
    return ('0x%x' if v >= 10 else '%d') % v          # 与 capstone 的渲染口径一致
_opt23_ops = {'eax',
              _imm23(len(CG.ACTS) + 1), _imm23(len(CG.TEACHERS) + 1), _imm23(len(CM.TIER_NAMES) + 1)}
_opt23 = [c for c in _hit(mf, 'call', ('0x%x' % CM.DIALOG,))
          if mf[mf.index(c) - 1].mnemonic == 'push' and mf[mf.index(c) - 1].op_str in _opt23_ops]
check('C23z8 PAGE_ROWS 读数恰 1 处、写在四级对话框call的第一次之前、且它不跟任何自增混用 (取最大值不是求和)',
      len(_rw23) == 1 and len(_opt23) == 4
      and not _hit(mf, 'inc', ('dword ptr [0x%x]' % GC['PAGE_ROWS'],))
      and _rw23[0].address < min(i.address for i in _opt23)
      and MODB <= GC['PAGE_ROWS'] < MODB + LY['mod_sz'],
      'PAGE_ROWS=%06X 处数%d / 四级弹窗 %d 个, 首次 @0x%06X'
      % (GC['PAGE_ROWS'], len(_rw23), len(_opt23),
         min(i.address for i in _opt23) if _opt23 else -1))
_l23 = {n: len(_hit(mf, 'mov', ('dword ptr [0x%x], ecx' % GC[n],)))
        for n in ('KID_LAST_SLOT', 'KID_LAST_ACT')}
check('C23z7 KID_LAST_SLOT / KID_LAST_ACT 各写 1 处 (手测时读这两个就知道"最后一条指令"下了什么)'
      , all(v == 1 for v in _l23.values()), str(_l23))
w('  手测身份式: PANEL_OPEN = 走进培养面板的次数(一弹表就 +1); 四级里任一层按取消都不落圈;')
w('  走完四层才 CMD_PUSH+1, 同时 KID_LAST_SLOT/KID_LAST_ACT 记下这一条; 空城/非同城看 KID_NOTSAME_CITY')
w('  下完指令等一个月: GROWTH_CMD+1, ROLL+REJECT=CMD, OK+FAIL=ROLL (见 C22e)')


# ---------------- C24 M6: sidecar 影子存档 (TKMODSAVE_<槽>.DAT) ----------------
w('\n--- C24 M6 影子存档: 两派发器钩 / 桩字节复现 / SC_DATA 三块 / 头字段"写了就比"两头吻合 ---')
import re as _re
import child_save as SV
SC = LY['sc']
SCVA, SDVA = SC['code_va'], SC['data_va']
# SV 的 giv/sur 沿用老工具的反名字: blocks() 里 'giv' 喂姓行、'sur' 喂名行 (与 C23 的 ML 同口径)
SDL = {'pool': POOL, 'stride': STRIDE, 'n0': N0, 'cap': CAP,
       'giv': SURT, 'sur': GIVT, 'bm': BM, 'kid_tab': V['KID_TAB'], 'kid_esz': KESZ,
       'ring': V['CMD_RING'], 'sect_va': SECVA, 'sect_sz': SECSZ,
       'data_delta': SDVA - SCVA, '_slot': 3,
       'ctr': {nm: GC[nm] for nm in SV.SC_CTRS}}
scode, sva, _ssrc, _sins = SV.build(SCVA, SDL)
# 下面全部从 **exe 字节** 反汇编, 不采信模块返回值 (桩复现只证明"是我们写的", 语义要另证)
_exi = list(md.disasm(bytes(E(SCVA, SC['code_sz'])), SCVA))
check('C24a 影子桩 %dB @0x%06X 与 child_save.build() 逐字节一致, 且 exe 里反汇编吃满全块'
      % (sva['size'], SCVA),
      bytes(E(SCVA, sva['size'])) == scode and sva['size'] == SC['code_sz']
      and sum(len(i.bytes) for i in _exi) == SC['code_sz']
      and (sva['tramp_load'], sva['sc_save'], sva['sc_load'])
          == (SC['tramp_load'], SC['sc_save'], SC['sc_load'])
      and sva['code_end'] <= SDVA and SDVA + SC['data_sz'] <= MODB + LY['mod_sz'],
      '尾 0x%06X / SC_DATA 0x%06X / MOD 尾 0x%06X' % (sva['code_end'], SDVA, MODB + LY['mod_sz']))

# ---- C24b 两处派发器钩: clean 上就是链尾那发 call 0x47D850, big 上是 jmp 到桩 ----
_hops = [('保存', SC['site_save'], SCVA, SC['orig_save']),
         ('载入', SC['site_load'], SC['tramp_load'], SC['orig_load'])]
for _nm, _site, _tgt, _org in _hops:
    _o, _c = bytes.fromhex(_org), bytes(AT(_site, 5))
    _d = list(md.disasm(_c, _site))[0]
    check('C24b %s派发器 0x%06X: clean=%s(链尾 call 0x47D850) -> big=%s 解码 = jmp 0x%06X, 站点+5=0x%06X'
          % (_nm, _site, _o.hex(), _c.hex(), _tgt, _site + 5),
          CLN[_site - CB:_site - CB + 5] == _o and _c == CM.jmp_rel(_site, _tgt)
          and _d.mnemonic == 'jmp' and _d.op_str == '0x%x' % _tgt,
          '%s %s' % (_d.mnemonic, _d.op_str))
# 桩顶替的是原生链尾那发 close, 不是把它跳过: 两个 trampoline 各自重放 call 0x47D850 再 jmp 回 site+5
for _nm, _site, _ent in (('保存', SC['site_save'], SC['sc_save']),
                         ('载入', SC['site_load'], SC['sc_load'])):
    _base = SCVA if _nm == '保存' else SC['tramp_load']
    _txt = ['%s %s' % (i.mnemonic, i.op_str) for i in _exi if _base <= i.address < _base + 16][:6]
    check('C24c %s trampoline @0x%06X = pushal/mov esi,ecx/call 0x%06X/popal/call 0x47D850/jmp 0x%06X'
          % (_nm, _base, _ent, _site + 5),
          _txt[0].startswith('pusha') and _txt[1] == 'mov esi, ecx'
          and _txt[2] == 'call 0x%x' % _ent and _txt[3].startswith('popa')
          and _txt[4] == 'call 0x%x' % SV.CLOSE_FN and _txt[5] == 'jmp 0x%x' % (_site + 5),
          ' | '.join(_txt))

# ---- C24d SC_DATA: 路径 / 六段描述符表 / 归零模板 ----
_pb, _bt = SV.path_bytes(), SV.blktab_bytes(SDL)
check('C24d 路径模板 %s @0x%06X: 第 %d 字节是槽号数字(开局写死 0), 且 %d 字节内 NUL 收尾'
      % (SC['path'], SDVA + SV.D_PATH, SC['path_digit'], SV.PATH_SZ),
      bytes(E(SDVA + SV.D_PATH, SV.PATH_SZ)) == _pb
      and SC['path_digit'] == SV.PATH_DIGIT and _pb[SV.PATH_DIGIT:SV.PATH_DIGIT + 1] == b'0'
      and _pb[11:15] == b'.DAT' and len(_pb) == SV.PATH_SZ)
_bts = bytes(E(SDVA + SV.D_BLK, 0x38))
_pairs = [struct.unpack_from('<II', _bts, o) for o in range(0, 0x38, 8)]
check('C24e 描述符表 %dB @0x%06X = 6 段 + 终止(len=0), 且两方向同一张表 (与布局 blocks 逐项吻合)'
      % (len(_bt), SDVA + SV.D_BLK),
      _bts == _bt and [tuple(x) for x in _pairs[:6]] == [tuple(x) for x in SC['blocks']]
      and _pairs[6] == (0, 0) and sum(sz for _, sz in _pairs[:6]) == SC['payload_sz'],
      ' '.join('%06X+%d' % p for p in _pairs))
# 段地址/长度独立重算 (不采信 blktab_bytes): 影子档就是"原生序列化器吃不到的那几块内存"
_want_bl = [(POOL + STRIDE * N0, STRIDE * (CAP - N0)), (SURT, 7 * (CAP - N0)),
            (GIVT, 7 * (CAP - N0)), (BM, CAP // 8), (V['KID_TAB'], CAP * KESZ),
            (V['CMD_RING'], SV.RING_SZ)]
_misbl = [(i, a, s, _pairs[i]) for i, (a, s) in enumerate(_want_bl) if _pairs[i] != (a, s)]
check('C24f 六段按本脚本自己的常量重算 = 扩展槽实体/姓行/名行/儿童位图/KID_TAB/指令环',
      not _misbl, str(_misbl))
check('C24g 影子档 %dB = 头 0x%X + %s ; 每段长度须能塞进 16 位计数且全在 .edata 内'
      % (SC['file_sz'], SC['hdr_sz'], ' + '.join('%dB' % s for _, s in _want_bl)),
      SC['file_sz'] == SC['hdr_sz'] + SC['payload_sz'] == SC['hdr_sz'] + sum(s for _, s in _want_bl)
      and all(0 < s <= 0xFFFF for _, s in _want_bl)
      and all(SECVA <= a and a + s <= SECVA + SECSZ for a, s in _want_bl),
      '手测: 存档后游戏目录应出现 %s, 大小 %d B' % (SC['path'], SC['file_sz']))
_tmpl = bytes(E(SDVA + SV.D_TMPL, SV.ENT_SZ))
_p370 = bytes(E(POOL + STRIDE * N0, STRIDE))
check('C24h 归零模板 47B @0x%06X: 状态字 +0x2c=0x808F(空槽态), 且与池里扩展槽同一具身体(只 id word 不同)'
      % (SDVA + SV.D_TMPL),
      len(_tmpl) == 47 and u16r(_tmpl, 0x2c) == SV.VACANT_STATE
      and _tmpl[2:] == _p370[2:] and u16r(_p370, 0) == N0,
      '模板 id=%d 池[%d].id=%d' % (u16r(_tmpl, 0), N0, u16r(_p370, 0)))
_zs = {k: bytes(E(SDVA + v, n)) for k, v, n in
       (('头缓冲', SV.D_HDR, SV.HDR_SZ), ('句柄/槽号', SV.D_HND, 8),
        ('摘要/游标', SV.D_DIG, 8), ('OFSTRUCT', SV.D_OFS, SV.OFS_SZ))}
check('C24i SC_DATA 的运行期字段开局全 0 (%s)' % ' '.join(_zs),
      all(v == b'\x00' * len(v) for v in _zs.values()),
      str({k: v[:4].hex() for k, v in _zs.items() if v.strip(b'\x00')}))


# ---- C24j 头部字段: 保存侧写下的立即数 == 载入侧比对的立即数 (两方向不可能各说各话) ----
def _imm_map(ins_list, mns):
    st, cp = {}, {}
    for i in ins_list:
        m = _re.match(r'^(?:word|dword) ptr \[0x([0-9a-f]+)\], (0x[0-9a-f]+|\d+)$', i.op_str)
        if not m:
            continue
        d = st if i.mnemonic == mns[0] else cp if i.mnemonic == mns[1] else None
        if d is not None:
            d.setdefault(int(m.group(1), 16), set()).add(int(m.group(2), 0))
    return st, cp


_ST, _CMP = _imm_map(_exi, ('mov', 'cmp'))
_HB = SDVA + SV.D_HDR
_HDF = [('MAGIC', SV.HD_MAGIC, SC['magic'], True), ('VER', SV.HD_VER, SC['ver'], True),
        ('CAP', SV.HD_CAP, CAP, True), ('N0', SV.HD_N0, N0, True),
        ('PAYLOAD', SV.HD_PAYLOAD, SC['payload_sz'], True),
        ('COMMIT', SV.HD_COMMIT, SC['commit'], True),
        ('RECN', SV.HD_RECN, CAP - N0, False)]
_bad = []
for _fn, _off, _want, _must_cmp in _HDF:
    _a = _HB + _off
    if _ST.get(_a, set()) != {_want} or (_must_cmp and _CMP.get(_a, set()) != {_want}):
        _bad.append('%s@+%02X 写%s 比%s 期望{%X}' % (_fn, _off, sorted(map(hex, _ST.get(_a, ()))),
                                                     sorted(map(hex, _CMP.get(_a, ()))), _want))
check('C24j 头部 %d 个定值字段: 写了就比, 立即数两头同值 (MAGIC/VER/CAP/N0/PAYLOAD/COMMIT 各 1 写 1 比; RECN 只记不判)'
      % len(_HDF), not _bad, ' ; '.join(_bad))
_out_hdr = [hex(a) for a in list(_ST) + list(_CMP) if not (_HB <= a < _HB + SV.HDR_SZ)
            and a >= SDVA and a < SDVA + SV.D_TMPL]
check('C24k 头缓冲 0x30 之外的定值写/比一个也没有 (句柄/槽号/摘要/游标只能动态来, 防把常量误写进 scratch)',
      not _out_hdr, str(_out_hdr))
_reg_st = {}
for i in _exi:
    m = _re.match(r'^(?:word|dword) ptr \[0x([0-9a-f]+)\], (?:[a-d]x|e[a-d]x)$', i.op_str)
    if m and i.mnemonic == 'mov':
        _reg_st.setdefault(int(m.group(1), 16), 0)
        _reg_st[int(m.group(1), 16)] += 1
check('C24l 动态两字段 SLOT(+08)/DIGEST(+10) 各由寄存器写 1 次, 载入侧再读回来比 (槽号比 [slot]、摘要比刚算出的值)',
      _reg_st.get(_HB + SV.HD_SLOT) == 1 and _reg_st.get(_HB + SV.HD_DIGEST) == 1
      and len(_hit(_exi, 'movzx', ('[0x%x]' % (_HB + SV.HD_SLOT),))) == 1
      and len(_hit(_exi, 'cmp', ('[0x%x]' % (_HB + SV.HD_DIGEST),))) == 1
      and len(_hit(_exi, 'cmp', ('eax, dword ptr [0x%x]' % (SDVA + SV.D_SLOT),))) == 1,
      str({hex(k): v for k, v in sorted(_reg_st.items())}))

# ---- C24m 方向不可能漂移: 写循环只经 _lwrite, 读循环只经 _lread, 两者读同一张表 ----
_heads = [i.address for i in _exi if i.mnemonic == 'mov'
          and i.op_str == 'eax, 0x%x' % (SDVA + SV.D_BLK)]


def _dcalls(seg):
    """段内的直接 call 目标 = 桩内部函数(这里是 sc_w / sc_r 两枚包装)"""
    return sorted({int(i.op_str, 16) for i in seg
                   if i.mnemonic == 'call' and not i.op_str.startswith('dword ptr')})


def _iat(addr):
    """从函数入口读到第一个 ret, 取它经由的 IAT (证明这枚包装到底调的是谁)"""
    seg = []
    for i in _exi:
        if i.address >= addr:
            seg.append(i)
            if i.mnemonic == 'ret':
                break
    return sorted({int(i.op_str.split('[')[1].rstrip(']'), 16) for i in seg
                   if i.mnemonic == 'call' and i.op_str.startswith('dword ptr')})


_seg_w = [i for i in _exi if _heads[0] <= i.address < _heads[1]]
_W = _dcalls(_seg_w)
_seg_r = [i for i in _exi if _heads[1] <= i.address < (_W[0] if _W else SCVA + SC['code_sz'])]
_R = _dcalls(_seg_r)
check('C24m 两方向共用同一张描述符表(两处 `mov eax, 表` @0x%06X/0x%06X), 且写循环只经 _lwrite、读循环只经 _lread'
      % (_heads[0], _heads[1]),
      len(_heads) == 2 and len(_W) == 1 and len(_R) == 1 and _W[0] != _R[0]
      and _iat(_W[0]) == [SV.TH_LWRITE] and _iat(_R[0]) == [SV.TH_LREAD],
      '写环->%s=%s 读环->%s=%s' % (['%06X' % x for x in _W], [hex(x) for x in _iat(_W[0]) if _W],
                                  ['%06X' % x for x in _R], [hex(x) for x in _iat(_R[0]) if _R]))

# ---- C24n 闸门口径: 每方向只在该派发器链尾触发一次; 载入看引擎预校验门 ----
check('C24n 载入方向先过原生预校验门 [obj+0x8c]==0 (门不过就一个字节不碰), 两方向都读 [obj+0x96] 取本槽记录基址'
      , len(_hit(_exi, 'cmp', ('[esi + 0x%x], 0' % SC['gate'],))) == 1
      and SC['gate'] == SV.OBJ_GATE
      and len(_hit(_exi, 'mov', ('eax, dword ptr [esi + 0x%x]' % SC['recbase'],))) == 2
      and SC['recbase'] == SV.OBJ_RECBASE,
      '门 1 处 / 记录基址读 2 处')
_c24o = {'cmp eax,记录头': len(_hit(_exi, 'cmp', ('eax, 0x%x' % SC['rec_hdr'],))),
         'sub eax,记录头': len(_hit(_exi, 'sub', ('eax, 0x%x' % SC['rec_hdr'],))),
         'mov ecx,槽宽': len(_hit(_exi, 'mov', ('ecx, 0x%x' % SC['rec_size'],))),
         'cmp edx,8(上界)': len(_hitx(_exi, 'cmp', 'edx, 8')),          # ★ <10 渲染成十进制
         'or dl,0x30(数字)': len(_hit(_exi, 'or', ('dl, 0x30',))),
         'mov byte[路径+10],dl': len(_hit(_exi, 'mov', ('byte ptr [0x%x], dl' % (SDVA + SV.D_PATH + SV.PATH_DIGIT),)))}
check('C24o 槽号解析 = 减记录头 %d、逐次减槽宽 0x%X、上界 %d 槽, 命中后 or dl,0x30 写进路径第 %d 字节 (一槽一份文件)'
      % (SC['rec_hdr'], SC['rec_size'], SC['slot_max'], SC['path_digit']),
      all(v == 1 for v in _c24o.values())
      and SC['rec_hdr'] == SV.REC_HDR and SC['rec_size'] == SV.REC_SIZE
      and SC['slot_max'] == SV.SLOT_MAX and SC['path_digit'] == SV.PATH_DIGIT,
      ' ; '.join('%s=%d' % kv for kv in sorted(_c24o.items())))
# 打开标志不是"看文本里有几条 mov edx"就算数: 必须真是喂给 OpenFile 的那一枚参数
_tgts24 = sorted({int(i.op_str, 16) for i in _exi
                  if i.mnemonic == 'call' and not i.op_str.startswith('dword ptr')})
_openw = [t for t in _tgts24 if _iat(t) == [SV.TH_OPENFILE]]
_addrv = [i.address for i in _exi]
_ix = {a: k for k, a in enumerate(_addrv)}


def _feeds_open(txt):
    """该指令之后 1 拍就是 call sc_open => 它设的 edx 就是 OpenFile 的 code 参数"""
    out = []
    for i in _exi:
        if '%s %s' % (i.mnemonic, i.op_str) != txt:
            continue
        nxt = _exi[_ix[i.address] + 1] if _ix[i.address] + 1 < len(_exi) else None
        out.append(nxt is not None and nxt.mnemonic == 'call'
                   and nxt.op_str == '0x%x' % _openw[0])
    return out


check('C24o2 打开标志真的喂给 OpenFile: 保存 `mov edx,0x1002`(读写+创建, 会截断) 1 枚, '
      '载入 `xor edx,edx`(OF_READ) 1 枚; 第二枚 xor edx,edx 是 sc_slotpath 的槽号累加器, 与打开无关'
      , len(_openw) == 1 and _feeds_open('mov edx, 0x1002') == [True]
      and sorted(_feeds_open('xor edx, edx')) == [False, True],
      '0x1002->open %s / xor edx->open %s / sc_open @0x%06X'
      % (_feeds_open('mov edx, 0x1002'), _feeds_open('xor edx, edx'), _openw[0] if _openw else 0))
# 摘要两头共用一份实现: 桩里只有一段摘要, 保存算一次写进头、载入算一次比头
_dgva = [i.address for i in _exi if i.mnemonic == 'mov' and i.op_str == 'edi, 0x%x' % POOL]
_dgcal = [i for i in _exi if i.mnemonic == 'call' and _dgva and i.op_str == '0x%x' % _dgva[0]]
check('C24p 摘要实现只有一份(基址=池 0x%06X、条数=N0=%d、每条 12 步混合、步长 47 且跳过 +4..+7 派生指针), 保存/载入各 call 它一次'
      % (POOL, N0),
      len(_dgva) == 1 and len(_dgcal) == 2
      and len(_hit(_exi, 'mov', ('ebp, 0x%x' % N0,))) == 1
      and len(_hit(_exi, 'add', ('edi, 8',))) == 1 and len(_hit(_exi, 'add', ('edi, 3',))) == 1
      and len([i for i in _exi if i.mnemonic == 'rol' and i.op_str == 'ebx, 3']) == 4
      and len(_hitx(_exi, 'mov', 'ecx, 9')) == 1,
      '摘要入口 0x%06X 被 call %d 处 (1 首双字 + 9 双字 + 1 字 + 1 字节 = 12 步)'
      % (_dgva[0] if _dgva else 0, len(_dgcal)))
# 埋点: 9 个新计数器都在 0x80 表内, 且自增点位置/次数符合"每方向各一条流水"的设计
_inc24 = {nm: len(_hit(_exi, 'inc', ('dword ptr [0x%x]' % GC[nm],))) for nm in SV.SC_CTRS}
_exp24 = {'SIDECAR_SAVE': 1, 'SIDECAR_SAVED': 1, 'SIDECAR_WERR': 2,   # WERR: OpenFile 失败 / 写不满
          'SIDECAR_SLOT': 2, 'SIDECAR_LOAD': 1, 'SIDECAR_RESTORE': 1,  # SLOT: 两方向各一处解析失败
          'SIDECAR_MISS': 1, 'SIDECAR_REJECT': 1, 'SIDECAR_GATE': 1}
_off24 = [nm for nm in SV.SC_CTRS if not (V['GROWTH_CNT'] <= GC[nm] < V['GROWTH_CNT'] + LY['menu']['cnt_bytes'])]
_wrong24 = {nm: (_inc24[nm], _exp24[nm]) for nm in SV.SC_CTRS if _inc24[nm] != _exp24[nm]}
check('C24q M6 埋点 %d 个全在 %d 字节表内、自增点处数与语义吻合 (合计 %d 处): %s'
      % (len(SV.SC_CTRS), LY['menu']['cnt_bytes'], sum(_inc24.values()),
         ' '.join('%s=%d' % (n, c) for n, c in _inc24.items())),
      not _off24 and not _wrong24 and len(GC) * 4 <= LY['menu']['cnt_bytes'],
      '出界%s 处数不符%s' % (_off24, _wrong24))
w('  手测身份式: 按一次保存 -> SIDECAR_SAVE+1, 全段写完 -> SIDECAR_SAVED+1 (两者相等才叫落地);')
w('  读档读到影子档 -> SIDECAR_LOAD+1, 摘要全过并回填 -> SIDECAR_RESTORE+1 (= 孩子保住了);')
w('  没有影子档(老存档)=MISS, 有但校验不过=REJECT, 原生预校验失败=GATE, 解析不出槽号=SLOT, 写失败=WERR')
w('  影子档落在游戏目录(CWD, 与 SAVEDATA.TR2 同目录): %s, 期望 %d B; 存档前后各读一次 SIDECAR_* 即可判定'
  % (SC['path'], SC['file_sz']))

# ================= C25 M4: 到龄自动元服 + 归属 (D2) =================
w('\n--- C25 M4 元服: 引擎归属簇站点 / 调用约定实证 / 桩侧形态 / 逐孩元服月与归属预测 ---')
CASTLE_LINK = 0x4A0540        # 0x4A5100 内部: 主人城的家臣链表 (节点 = 实体 +4..+7, 已在链上则不动)
LORD_TAB, INVAL_SET, GUO_SET, CITY_SET, RANK_SET = 0x5179b8, 0x49A730, 0x49A750, 0x49A760, 0x49A7E0
LORD_W0 = 0x5179c5            # 国主表里那一字节 (bit4 = 该国空置标记)


def _t(i):
    return ('%s %s' % (i.mnemonic, i.op_str)).strip()      # 无操作数时 (ret/nop) 不留尾空格


def _epi(lst, want):
    """lst 里第一发 ret 之前(含 ret)的最后 len(want) 条 = want ?  (窗口尾部常有编译器垫的 nop)"""
    k = next((x for x, v in enumerate(lst) if v.startswith('ret')), -1)
    return len(want) - 1 <= k and lst[k - len(want) + 1:k + 1] == want


def _has(lst, want):
    """lst 里连续出现 want 这一段 ? (多出口函数要认的不是第一发 ret)"""
    return any(lst[i:i + len(want)] == want for i in range(len(lst) - len(want) + 1))


# 元服支的指令窗口: 从 FREEZE 自增(该支唯一入口后的第一条)到游标前进(cg_advance)之前
_i_fr = [i for i in mins_g if i.mnemonic == 'inc' and i.op_str == 'dword ptr [0x%x]' % GC['GROWTH_FREEZE']][0]
_i_adv = [i for i in mins_g if i.mnemonic == 'add' and i.op_str == 'ebx, %d' % CS.ESZ][0]
PSL = [i for i in mins_g if _i_fr.address <= i.address < _i_adv.address]
w('  元服支 %d 条 @0x%06X..0x%06X (唯一入口 = 龄 >= 元服线 %d 的那发 jae)'
  % (len(PSL), _i_fr.address, _i_adv.address, PUKU_AGE))

_ps, _pp = [i for i in PSL if i.mnemonic == 'push'], [i for i in PSL if i.mnemonic == 'pop']
_pe4 = [i for i in PSL if i.mnemonic == 'add' and i.op_str == 'esp, 4']
_pe8 = [i for i in PSL if i.mnemonic == 'add' and i.op_str == 'esp, 8']
_acc = ('0x%x' % CG.NIB_SET, '0x%x' % CG.EXCL_SET, '0x%x' % CG.DAIMYO_SET,
        '0x%x' % GL['debug_log'])          # debug_log 也是 stdcall ret 4, 实参自己清
_pr4 = [i for i in PSL if i.mnemonic == 'call' and i.op_str in _acc]
check('C25k 元服支栈自洽: push %d 枚 = pop %d + add esp,8 清 %d + add esp,4 清 %d + ret 4 访问器自清 %d '
      '(3 枚寄存器保护 push 全部配对 pop, 不污染月钩调用方的栈)'
      % (len(_ps), len(_pp), 2 * len(_pe8), len(_pe4), len(_pr4)),
      len(_ps) == len(_pp) + 2 * len(_pe8) + len(_pe4) + len(_pr4)
      and all(sum(1 for i in _ps if i.op_str == r) == 1 for r in ('ebx', 'edi'))
      and sum(1 for i in _ps if i.op_str == 'esi') == 3          # 1 枚保护 + 挂载/国主各 1 枚本人实参
      and sorted(i.op_str for i in _pp) == ['ebx', 'edi', 'esi']
      # 10 枚 = 保护 3(ebx/edi/esi) + 挂载实参 eax,esi + 国主实参 esi + 访问器 3 枚 + debug_log marker 0x45
      and len(_ps) == 10 and len(_pp) == 3 and len(_pr4) == 4,
      'push %s / pop %s' % (sorted(i.op_str for i in _ps), sorted(i.op_str for i in _pp)))

# ---- C25a 归属簇站点: 要么与 clean 逐字节一致, 要么只允许"已登记的搬家/改界"差异 ----
_EXPDIFF = {CG.LORD_OR_RONIN: ({0x3A, 0x3B, 0x4D, 0x4E, 0x4F},
                               'P2 改界 0x172->0x%X 的 imm16(国主槽上界) + P1 搬家旧池基的 imm32' % CAP)}
for _nm, _va, _n in (('nibble:=0xf', CG.NIB_SET, 0x20), ('bit4 排除', CG.EXCL_SET, 0x20),
                     ('bit7 无效', INVAL_SET, 0x20), ('bit11 大名一族', CG.DAIMYO_SET, 0x20),
                     ('身分码', RANK_SET, 0x20), ('国写手', GUO_SET, 0x20), ('城写手', CITY_SET, 0x20),
                     ('进城链表', CASTLE_LINK, 0x40), ('挂载 0x4A5100', CG.MOUNT, 0xB4),
                     ('国主/浪人 0x4A5290', CG.LORD_OR_RONIN, 0xB8)):
    _a, _b = bytes(AT(_va, _n)), CLN[_va - CB:_va - CB + _n]
    _df = {o for o in range(_n) if _a[o] != _b[o]}
    _wd, _why = _EXPDIFF.get(_va, (set(), '应当一字未改'))
    check('C25a %-18s @0x%06X 差异集 = %s' % (_nm, _va, _why or '空'),
          _df == _wd, '实差 %s' % (sorted(hex(x) for x in _df) or '无'))
_ax = bytes(AT(CG.LORD_OR_RONIN, 0xB8))
check('C25a2 0x4A5290 的国主槽上界已被 P2 抬到 CAP(0x%X) => 扩展槽人物当国主时, 孩子也能挂上他 '
      '(clean 处为 0x172=%d)' % (CAP, N0),
      struct.unpack_from('<H', _ax, 0x3A)[0] == CAP and struct.unpack_from('<H', CLN[0x4A52CA - CB:], 0)[0] == N0
      and struct.unpack_from('<I', _ax, 0x4D)[0] == POOL,
      'big=%04X clean=%04X 池基=%08X' % (struct.unpack_from('<H', _ax, 0x3A)[0], N0,
                                        struct.unpack_from('<I', _ax, 0x4D)[0]))


# ---- C25b 调用约定拿引擎自己的调用点当证据 (不是我们自己选的) ----
#  只认"从函数头线性反汇编能走到的 call"——裸扫 e8 字节会把 rol/add 的操作数误当相对 call (实测 64 处假阳).
for _nm, _fn, _flen, _tgt, _exp in (
        ('0x4A5100 挂载', 0x4A5220, 0x70, CG.MOUNT, 'add esp, 8'),
        ('0x4A5100 挂载', 0x4A5290, 0xB8, CG.MOUNT, 'add esp, 8'),
        ('0x4A5290 国主/浪人', 0x4A4FC0, 0x60, CG.LORD_OR_RONIN, 'add esp, 4'),
        ('0x4A0540 进城链表', CG.MOUNT, 0xB4, CASTLE_LINK, 'add esp, 0xc')):
    _di = list(md.disasm(bytes(AT(_fn, _flen)), _fn))
    _lst = [_t(i) for i in _di]
    _k = [i for i, x in enumerate(_lst) if x == 'call 0x%x' % _tgt]
    check('C25b %-16s 在 0x%06X 内 %d 发, 紧跟 %s => cdecl、调用方清栈 (桩照同一写法)'
          % (_nm, _fn, len(_k), _exp),
          len(_k) >= 1 and all(i + 1 < len(_lst) and _lst[i + 1] == _exp for i in _k),
          ' '.join('%08X->%s' % (_di[i].address, _lst[i + 1] if i + 1 < len(_lst) else '?') for i in _k))
check('C25b2 三个状态访问器(0x49A6B0/0x49A6D0/0x49A800)都是 thiscall+单栈参 `ret 4` => ecx=实体 + push 值',
      all(_epi([_t(i) for i in md.disasm(bytes(AT(v, 0x20)), v)], ['ret 4'])
          for v in (CG.NIB_SET, CG.EXCL_SET, CG.DAIMYO_SET)))

# ---- C25c 挂载/兜底内部形状 (我们依赖的门、参槽位、成功返回值) ----
_mt = [_t(i) for i in md.disasm(bytes(AT(CG.MOUNT, 0xB4)), CG.MOUNT)]
check('C25c 0x4A5100: 序言 push ecx / mov ecx,[esp+0xc] => 第2参=主人(转成 ecx this), 第1参 [esp+0x14]=本人; '
      '成功 mov eax,1; 尾声 pop edi/pop esi/mov eax,1/pop ebx/pop ecx/ret (自己不清参, 全 caller 清)',
      _mt[0] == 'push ecx' and _mt[1] == 'mov ecx, dword ptr [esp + 0xc]'
      and 'mov esi, dword ptr [esp + 0x14]' in _mt and 'mov eax, 1' in _mt
      and _has(_mt, ['pop edi', 'pop esi', 'mov eax, 1', 'pop ebx', 'pop ecx', 'ret'])
      and _mt.count('ret') == 5 and _mt.count('xor eax, eax') == 4,
      ' | '.join(_mt[:2]))
_GATES = [('bit15=0 主人要在场', 'test ah, 0x80'), ('身分码!=0', 'test ah, 7'),
          ('城<0xc8', 'cmp bl, 0xc8'), ('国<0x31', 'cmp cl, 0x31')]
check('C25c2 主人四道门全在 (%s) => 父亲不合格就返回 0, 桩立刻改走国主/浪人, 不会静默失败'
      % ' '.join(x for _n, x in _GATES), all(x in _mt for _n, x in _GATES))
check('C25c3 0x4A5100 内部恰 1 发进城链表 + 国/城都走原生写手 + 清 bit7 + 本人身分码==0 时置 1(家臣); '
      '且全程不写 +0x2a(主君) => 与引擎自己挂的家臣一模一样',
      _mt.count('call 0x%x' % CASTLE_LINK) == 1 and 'add esp, 0xc' in _mt
      and 'call 0x%x' % GUO_SET in _mt and 'call 0x%x' % CITY_SET in _mt
      and 'call 0x%x' % RANK_SET in _mt and 'call 0x%x' % INVAL_SET in _mt
      and 'push 0' in _mt and not [x for x in _mt if '+ 0x2a]' in x],
      ' '.join(x for x in _mt if x.startswith('call')))
_GATES = [('bit15=0 主人要在场', 'test ah, 0x80'), ('身分码!=0', 'test ah, 7'),
          ('城<0xc8', 'cmp bl, 0xc8'), ('国<0x31', 'cmp cl, 0x31')]
check('C25c2 主人四道门全在 (%s) => 父亲不合格就返回 0, 桩立刻改走国主/浪人, 不会静默失败'
      % ' '.join(x for _n, x in _GATES), all(x in _mt for _n, x in _GATES))
check('C25c3 0x4A5100 内部恰 1 发进城链表 + 国/城都走原生写手 + 本人身分码==0 时置 1(家臣)',
      _mt.count('call 0x%x' % CASTLE_LINK) == 1 and 'add esp, 0xc' in _mt
      and 'call 0x%x' % GUO_SET in _mt and 'call 0x%x' % CITY_SET in _mt
      and 'call 0x%x' % RANK_SET in _mt and 'call 0x%x' % INVAL_SET in _mt,
      ' '.join(x for x in _mt if x.startswith('call')))
_rt = [_t(i) for i in md.disasm(bytes(AT(CG.LORD_OR_RONIN, 0xB8)), CG.LORD_OR_RONIN)]
while _rt and _rt[-1] == 'nop':          # 0x4A5290 是单出口函数, 尾巴上的 nop 是编译器填充
    _rt.pop()
check('C25c4 0x4A5290: 本国国主 = 表 0x%X 步长 18 取槽 word[+4], 不合格则浪人化(身分码:=0 / 国:=0xff / 城=0x49F940(所属)-0x38)'
      % LORD_TAB,
      'lea eax, [ecx*2 + 0x%x]' % LORD_TAB in _rt and 'mov ax, word ptr [eax + 4]' in _rt
      and _rt.count('call 0x%x' % CG.MOUNT) == 1 and 'push 0xff' in _rt and 'call 0x%x' % RANK_SET in _rt
      and _epi(_rt, ['pop esi', 'pop ebx', 'ret']), ' | '.join(_rt[:5]))
_i_iv = max(i for i, x in enumerate(_rt) if x == 'call 0x%x' % INVAL_SET)   # 浪人尾巴最后一发访问器
_tail = _rt[_i_iv + 1:]
_w_eax = [x for x in _tail if re.match(r'^(mov|xor|add|sub|inc|dec|and|or|lea|shl|shr|not|neg|pop|push|call)\b', x)
          and re.search(r'\b(eax|al|ah)\b', x)]
check('C25c4b 返回值口径 = 桩里 `test eax,eax; je 浪人` 的依据: 挂上国主那发 MOUNT 后 jne 到尾声(eax=1); '
      '浪人尾巴最后一发是 INVAL_SET(0) 把 eax 清成 0, 其后 %d 条无一条再写 eax' % len(_tail),
      not _w_eax and _tail[-1] == 'ret', ' | '.join(_w_eax or _tail))
_dsp = list(md.disasm(bytes(AT(0x4A4FC0, 0x40)), 0x4A4FC0))
check('C25c5 派发器 0x4A4FC0 的门是 `test byte[+0x2d],7`(=身分码): 我们的孩子身分码==0 => 只走不挂载的短路径 '
      '(前 5 条里连 0x4A5100 的影子都没有) =>  PLAN §S4 的"call 0x4A4FC0"不能用作归属, M4 直调 0x4A5100/0x4A5290',
      _t(_dsp[2]) == 'test byte ptr [esi + 0x2d], 7'
      and _t(_dsp[3]) == 'jne 0x4a4fe2'
      and 'call 0x%x' % CG.MOUNT not in [_t(i) for i in _dsp[:5]],
      ' | '.join(_t(i) for i in _dsp[:5]))

# ---- C25d 桩侧调用序列与实参顺序 ----
_mc = [i for i in PSL if i.mnemonic == 'call' and i.op_str == '0x%x' % CG.MOUNT]
_rc = [i for i in PSL if i.mnemonic == 'call' and i.op_str == '0x%x' % CG.LORD_OR_RONIN]


def _around(ins, back, fwd):
    k = mins_g.index(ins)
    return [_t(x) for x in mins_g[k - back:k]], [_t(x) for x in mins_g[k + 1:k + 1 + fwd]]


_bm, _am = _around(_mc[0], 2, 1) if _mc else ([], [])
_br, _ar = _around(_rc[0], 1, 1) if _rc else ([], [])
check('C25d 桩里挂载 = push 父 / push 本人 / call 0x4A5100 / add esp,8 (与 0x4A5290 内部那一发同形同序); '
      '兜底 = push 本人 / call 0x4A5290 / add esp,4',
      len(_mc) == 1 and len(_rc) == 1 and _bm == ['push eax', 'push esi'] and _am == ['add esp, 8']
      and _br == ['push esi'] and _ar == ['add esp, 4'],
      ' | '.join(_bm + ['call mount'] + _am + ['||'] + _br + ['call lord'] + _ar))
_k290 = _rt.index('call 0x%x' % CG.MOUNT)
check('C25d2 对照引擎自己那一发(0x4A5290 内): push 国主 / push 本人 / call 0x4A5100 / add esp,8 (本人总在最后一个 push) '
      '=> 桩里 push eax(父)/push esi(本人) 同形同序',
      _rt[_k290 - 2:_k290] == ['push edx', 'push esi']
      and _rt[_k290 + 1] == 'add esp, 8', ' | '.join(_rt[_k290 - 2:_k290 + 2]))

# ---- C25e 访问器各只碰它那一位 + push 0xff 的算术对账 ----
_ni = [_t(i) for i in md.disasm(bytes(AT(CG.NIB_SET, 0x14)), CG.NIB_SET)]
check('C25e 0x49A6B0 = xor 掩法只碰状态字低 4 位 (and eax,0xf -> xor word[+0x2c],ax) + ret 4',
      'and eax, 0xf' in _ni and 'xor word ptr [ecx + 0x2c], ax' in _ni and _epi(_ni, ['ret 4']),
      ' | '.join(_ni))
check('C25e2 语义对账: NIB_SET(0xff) 对**任意**旧低字节都把 nibble 拧成 0xf (256 值全算), 高 12 位一字不动',
      all(((0xff ^ dl) & 0xf) ^ (dl & 0xf) == 0xf for dl in range(256)), '旧 nibble 0..f -> 恒 0xf')
for _nm, _va, _want, _n in (('bit4 解除排除', CG.EXCL_SET, 'and word ptr [ecx + 0x2c], 0xffef', 0x18),
                            ('bit11 大名一族', CG.DAIMYO_SET, 'or byte ptr [ecx + 0x2d], 8', 0x18),
                            ('bit7 无效清', INVAL_SET, 'and word ptr [ecx + 0x2c], 0xff7f', 0x18)):
    _x = [_t(i) for i in md.disasm(bytes(AT(_va, _n)), _va)]
    check('C25e3 %-14s 内含 %s 且 ret 4' % (_nm, _want), _want in _x and 'ret 4' in _x, ' | '.join(_x[:4]))

# 极性: 这三家写法一样 `test eax,eax / je 后段 / 置位 / ret 4 / 清位 / ret 4` => 传 0 走"清", 传 1 走"置"
_pol = []
for _nm, _va, _setop in (('bit4 排除', CG.EXCL_SET, 'or byte ptr [ecx + 0x2c], 0x10'),
                         ('bit11 大名一族', CG.DAIMYO_SET, 'or byte ptr [ecx + 0x2d], 8'),
                         ('bit7 无效', INVAL_SET, 'or byte ptr [ecx + 0x2c], 0x80')):
    _x = [_t(i) for i in md.disasm(bytes(AT(_va, 0x20)), _va)]
    _pol.append((_nm, _x[:4] == ['mov eax, dword ptr [esp + 4]', 'test eax, eax', 'je 0x%x' % (_va + 15), _setop]))
_ke = [i for i in mins_g if i.mnemonic == 'call' and i.op_str == '0x%x' % CG.EXCL_SET][0]
_kd = [i for i in mins_g if i.mnemonic == 'call' and i.op_str == '0x%x' % CG.DAIMYO_SET][0]
check('C25e4 三个访问器极性一致 (前 4 条 = 取参/判 0/je 到清位段/置位段): %s => 桩里 %s / %s'
      % (' '.join('%s:%s' % (n, 'ok' if ok else 'NG') for n, ok in _pol),
         'EXCL 传 0(解除排除)', 'DAIMYO 传 1(补大名一族)'),
      all(ok for _n, ok in _pol)
      and [_t(x) for x in mins_g[mins_g.index(_ke) - 2:mins_g.index(_ke)]] == ['mov ecx, esi', 'push 0']
      and [_t(x) for x in mins_g[mins_g.index(_kd) - 2:mins_g.index(_kd)]] == ['mov ecx, esi', 'push 1'])

# ---- C25f 元服支除了归属码不直写任何东西 ----
_st = [i for i in PSL if i.mnemonic in ('mov', 'inc', 'sub', 'add', 'or', 'and', 'bts', 'btc', 'btr')
       and ('ptr [edi' in i.op_str or 'ptr [esi' in i.op_str or 'ptr [ebx' in i.op_str)]
_bad = [_t(i) for i in _st if not (i.mnemonic == 'mov' and i.op_str.startswith('word ptr [edi + 0xa],'))]
check('C25f 元服支对实体/私有区的直写只有归属码一条 (%d 处) => 五维/点数/累加器/位图一条不碰, '
      '状态位全部交给引擎原语(§S4 的"自己拉属性"是错的)' % len(_st), not _bad and len(_st) == 3, str(_bad))
check('C25f2 整个成长桩只有一发 nibble 写 (0x49A6B0) => 元服后 0xf 不会被桩改回 0xb, 一次元服就是永久',
      len([i for i in mins_g if i.mnemonic == 'call' and i.op_str == '0x%x' % CG.NIB_SET]) == 1
      and len([i for i in mins_g if i.mnemonic == 'call' and i.op_str == '0x%x' % CG.EXCL_SET]) == 1)
_bt_ = [i for i in mins_g if i.mnemonic in ('bt', 'bts', 'btr') and '0x%x' % BM in i.op_str]
check('C25f3 桩里没有一发位图写 (bts/btr) => 元服后槽仍算"我们的孩子": 面板按位图认领、影子档按位图整段存回, '
      '归属码留着给 D2 面板显示 (%d 处只读 bt)' % len(_bt_),
      len(_bt_) == 1 and _bt_[0].mnemonic == 'bt', ' '.join(_t(i) for i in _bt_))

# ---- C25g 原生成人 nibble 基准 (真机 ents_dump) ----
_nibh = {}
for _e in ents:
    _v = u16r(bytes.fromhex(_e['raw']), 0x2c) & 0xf
    _nibh[_v] = _nibh.get(_v, 0) + 1
check('C25g 原生 %d 实体状态字低 nibble 直方图 %s => 0x%X 就是原生成人态基准, 0x%X(我们的儿童态) 原生从不出现'
      % (len(ents), _nibh, CG.NIBBLE_ADULT, CG.NIBBLE_CHILD),
      _nibh.get(CG.NIBBLE_ADULT, 0) >= len(ents) - 5 and _nibh.get(CG.NIBBLE_CHILD, 0) == 0)

# ---- C25h 三条归属路汇合: 人次一次、埋点身份式成立 ----
_gen_va = [i for i in PSL if i.mnemonic == 'inc'
           and i.op_str == 'dword ptr [0x%x]' % V['CHILD_GENPUKU']][0].address
_mnt = 'dword ptr [0x%x]' % GC['GROWTH_PUKU_MOUNT']
_rni = 'dword ptr [0x%x]' % GC['GROWTH_PUKU_RONIN']
_trace = []
for _i in PSL:
    if _i.mnemonic == 'mov' and _i.op_str.startswith('word ptr [edi + 0xa],'):
        _c = int(_i.op_str.rsplit(', ', 1)[1], 0)
        _k = mins_g.index(_i)
        _inc = [x.op_str for x in mins_g[_k:_k + 3] if x.mnemonic == 'inc']
        _trace.append((_c, _inc[0] if _inc else '-'))
check('C25h 归属码 1/2/3 各一处且紧跟对应人次 (1,2->MOUNT / 3->RONIN); 汇合点 CHILD_GENPUKU 恰 1 处、'
      '两条 jmp + 一路直落 = 3',
      sorted(c for c, _x in _trace) == [CG.PUKU['follow'], CG.PUKU['lord'], CG.PUKU['ronin']]
      and all((c == CG.PUKU['ronin'] and x == _rni) or (c in (1, 2) and x == _mnt) for c, x in _trace)
      and len([i for i in mins_g if i.mnemonic == 'inc' and i.op_str == 'dword ptr [0x%x]' % V['CHILD_GENPUKU']]) == 1
      and len([i for i in PSL if i.mnemonic == 'jmp' and i.op_str == '0x%x' % _gen_va]) == 2,
      ' '.join('%d->%s' % (c, x) for c, x in _trace))
check('C25h2 身份式由此结构保证(手测整轮成立): GROWTH_FREEZE == CHILD_GENPUKU (支首条就是 FREEZE 自增, '
      '且元服后 nibble=0xf 永久出桩) ; MOUNT + RONIN == CHILD_GENPUKU (三路各计一次再汇合)',
      _t(mins_g[mins_g.index(_i_fr)]) == 'inc ' + 'dword ptr [0x%x]' % GC['GROWTH_FREEZE']
      and mins_g.index(_i_fr) + 1 == mins_g.index([i for i in PSL if i.mnemonic == 'push'][0])
      and len([i for i in mins_g if i.mnemonic == 'inc' and i.op_str == _mnt]) == 2)

# ---- C25i 预载桩: 已元服的孩子不再复臂 (否则会被拉回儿童态再元服一次) ----
_cj = [i for i in cins if i.mnemonic == 'cmp' and i.op_str == 'al, %s' % capimm(CG.NIBBLE_ADULT)]
_je = cins[cins.index(_cj[0]) + 1] if _cj else None
_aadv = [i for i in cins if i.mnemonic == 'add' and i.op_str == 'ebx, %d' % CS.ESZ][0]
_first_b = [i for i in cins if i.mnemonic == 'push' and i.op_str == '0xb'][0]
check('C25i 预载桩 ours 分支先查 nibble==0xf 就 je 到 after(=%06X) => 元服后的成人不被复臂拉回儿童态、'
      '也不被重实例化; 且这道门排在任何 push 0xb 之前' % _aadv.address,
      len(_cj) == 1 and _je is not None and _je.mnemonic == 'je'
      and _je.op_str == '0x%x' % _aadv.address and _cj[0].address < _first_b.address,
      ' | '.join(_t(i) for i in cins[cins.index(_cj[0]) - 2:cins.index(_cj[0]) + 2]) if _cj else '-')
check('C25i2 成长桩入口门是 `cmp al,0xb`(!=0xb 一律跳过) => 与预载桩的 0xf 门同一把尺, 元服者两头都出列',
      len([i for i in mins_g if i.mnemonic == 'cmp' and i.op_str == 'al, %s' % capimm(CG.NIBBLE_CHILD)]) == 1)

# ---- C25j 逐孩: 元服月 / 归属码 / 元服后状态字 预测 (参考实现 = puku_month + 引擎门) ----
check('C25j 龄口径唯一: 逐孩 eng_age(birth) == 预载 json 的 age_engine (%d 孩)' % len(SE),
      all(eng_age(e['birth']) == e.get('age_engine') for e in SE))
_puku_bad = []
w('  槽   %-10s %-3s %-6s %-6s %-6s %-9s %-10s %s'
  % ('全名', '龄', '元服月', '成长月', '父槽', '预期归属', '预期状态字', '预期国/城 + bit11'))
for e in SE:
    s = e['slot']
    _age = eng_age(e['birth'])
    _m = CG.puku_month(_age, START_MONTH, PUKU_AGE)
    _mo = growth_pred[s]['months'] + 1        # 成长桩跑到元服前月数 + 1 == 元服月 (两条独立实现同口径)
    if _m != _mo:
        _puku_bad.append((s, _age, _m, _mo))
    _fs, fin = e['fslot'], pred[s]['status']
    # 元服支动到的位只有这 5 处(逐条对着引擎字节核过): 低 nibble:=f(NIB_SET) / bit4 清(EXCL_SET 0) /
    # 身分码 8..10 由 RANK_SET 覆写(0xF8E0 掩掉它 + bit4) / bit11 或上去(DAIMYO_SET 1, 仅随父且父=大名) /
    # bit7 由挂载内部 INVAL_SET(0) 再清一次(本来就是 0)。其余位一律原样留着。
    _keep = fin & 0xF8E0
    _p = {'puku_month': _m, 'puku_age_used': PUKU_AGE, 'puku_code': None, 'daimyo_bit': 0,
          'status_after': None, 'guo_city_after': None, 'puku_note': ''}
    if _fs == 0xFFFF:
        _p['puku_code'] = '%d 或 %d' % (CG.PUKU['lord'], CG.PUKU['ronin'])
        _p['status_after'] = '0x%04X 或 0x%04X' % (_keep | 0x010F, _keep | 0x000F)
        _p['puku_note'] = '无父(表 fslot=ffff) => 走 0x4A5290: 本国国主挂上=2(家臣0x100), 查不到=3(浪人, 身分码0/国ff)'
        _p['guo_city_after'] = '看国主'
    else:
        _r = bytes.fromhex(ents[_fs]['raw'])
        _w = u16r(_r, 0x2c)
        _ok = not (_w & 0x8000) and ((_w >> 8) & 7) and _r[0x25] < 0xc8 and _r[0x24] < 0x31
        _dm = ((_w >> 8) & 7) == 7
        if not _ok:
            _p['puku_code'] = '%d 或 %d (主人四道门不过)' % (CG.PUKU['lord'], CG.PUKU['ronin'])
            _p['status_after'] = '0x%04X 或 0x%04X' % (_keep | 0x010F, _keep | 0x000F)
        else:
            _p['puku_code'] = str(CG.PUKU['follow'])
            _p['daimyo_bit'] = 0x800 if _dm else 0
            _p['status_after'] = '0x%04X' % (_keep | 0x010F | _p['daimyo_bit'])
            _p['guo_city_after'] = '%d/%d (随父 = 主人国/城)' % (_r[0x24], _r[0x25])
            _p['puku_note'] = '父%s 分=%d%s' % (ents[_fs].get('surname', '') + ents[_fs].get('given', ''),
                                                (_w >> 8) & 7, ' 大名=>补bit11' if _dm else '')
    pred[s].update(_p)
    w('  %-4d %-10s %-3d %-6d %-6d %-9s %-10s %s %s'
      % (s, pred[s]['name'], _age, _m, growth_pred[s]['months'], _fs if _fs != 0xFFFF else '-',
         _p['puku_code'], _p['status_after'], _p['guo_city_after']))
    w('       %s' % (_p['puku_note'] or '父合格 => 0x4A5100 挂进父家'))
check('C25j2 puku_month 与成长曲线 simulate 同一口径: 逐孩 元服月 == 元服前成长月数 + 1 (%d 孩, 违例 %d)'
      % (len(SE), len(_puku_bad)), not _puku_bad, str(_puku_bad[:4]))
_m1 = sorted(s for s in pred if pred[s]['puku_month'] == 1)
_aged = sorted(s for s in pred if pred[s]['age'] >= PUKU_AGE)
check('C25j3 开局到龄(虚岁>=%d) %d 人 = puku_month==1 的 %d 人 = 首月 CHILD_GENPUKU 期望 (槽 %s)'
      % (PUKU_AGE, len(_aged), len(_m1), _m1), _m1 == _aged and len(_m1) >= 1,
      'tkwatch: 首月后 CHILD_GENPUKU=%d, GROWTH_FREEZE=%d, MOUNT+RONIN=%d' % (len(_m1), len(_m1), len(_m1)))
_mon = {}
for s, v in pred.items():
    _mon.setdefault(v['puku_month'], []).append(s)
w('  元服月份分布: %s' % ' '.join('第%d月%d人(槽%s)' % (k, len(v), sorted(v))
                                for k, v in sorted(_mon.items())))
w('  累计曲线(手测对照): 第 k 月结束时 CHILD_GENPUKU 应 = #{puku_month<=k} = %s'
  % ' '.join('%d:%d' % (k, sum(1 for v in pred.values() if v['puku_month'] <= k))
             for k in sorted(_mon)))
json.dump(pred, open(REV / '_child_expect.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
w('  已并入预期表 _child_expect.json 的 puku_month / puku_code / status_after / daimyo_bit / guo_city_after')


# ---------------- C26 M3c-2: 培养详情 GDI 面板 ----------------
w('\n--- C27 M3c-2 培养详情面板: 桩字节复现 / 复用族谱段 / P 推导与成长桩逐条同式 / 串池 ---')
import kid_panel as KP
PC = PD['code_va']
KL = {'pool': LY['pool_va'], 'sched': V['CHILD_SCHED'], 'kid': V['KID_TAB'],
      'act_tab': V['ACT_TAB'], 'teach_tab': V['TEACH_TAB'], 'esz': CS.ESZ,
      'player_ent': CG.PLAYER_ENT}
for _k in KP.KD:
    KL['kd_' + _k] = PD['kd'][_k]
# 标签一律按下标取 (M5 又加了进度表四行: str_cnt/str_dims/str_puku/str_left)
_STRKEYS = {'str_title': KP.S_TITLE, 'str_p': KP.S_P, 'str_bond': KP.S_BOND,
            'str_hint': KP.S_HINT, 'str_cnt': KP.S_CNT, 'str_dims': KP.S_DIMS,
            'str_puku': KP.S_PUKU, 'str_left': KP.S_LEFT}
for _nm, _i in _STRKEYS.items():
    _e = PD['strings'][_i]
    assert _e['name'] == KP.STRINGS[_i], (_nm, _e['name'])
    KL[_nm], KL['len_' + _nm[4:]] = _e['va'], _e['len']
assert all(k in KL for k in list(_STRKEYS) + ['len_' + k[4:] for k in _STRKEYS]), sorted(KL)
# M5: 进度表读本月计数 / 反馈小框读台词串池与两张姓名表 (giv=姓表, sur=名表 —— 与 child_menu 同源)
KL.update({'giv': LY['surname_tab_va'], 'sur': LY['given_tab_va'],
           'age_puku': LY.get('genpuku_age', CG.AGE_PUKU),
           'f_cnt': _M5['fo']['cnt'],
           'msg_act': _M5['fo']['msg_act'], 'msg_slot': _M5['fo']['msg_slot'],
           'msg_str': _M5['msg_str_va'], 'msg_row': _M5['msg_row'],
           'msg_line0': _M5['ms_line0'],
           'msg_hint_off': _M5['ms_hint'] * _M5['msg_row'],
           'cost_arr': _M5['fo']['cost_arr'], 'msg_str_n': _M5['msg_str_n']})
kcode, _ksrc, _kENT = KP.build_panel(PC, KL)
kgot = bytes(E(PC, len(kcode)))
check('C27a 面板桩 %dB @0x%06X 与 kid_panel.build_panel() 逐字节一致' % (len(kcode), PC),
      kgot == kcode, '桩尾 0x%06X / MOD 尾 0x%06X' % (PC + len(kcode), MODB + LY['mod_sz']))
# M5: 反馈小框入口必须就是 child_menu 里 call %(kd_msg)s 用的那个地址, 否则提交后跳错地方
check('C27a2 反馈小框入口 0x%06X 与 _big_layout.json 的 m5.msg_kd 一致' % _kENT['msg'],
      _kENT['msg'] == _M5['msg_kd'], 'layout 0x%06X' % _M5['msg_kd'])
# 三块 (串池 / 参数区 / 代码) 必须互不重叠且整块落在 MOD 区内 —— 不写死先后顺序,
# 换偏移时只看"有没有压到别人", 免得挪一次就得改断言。
_blk = sorted([('串池', PD['str_va'], PD['str_sz']),
               ('参数区', PD['data_va'], PD['data_sz']),
               ('代码', PC, len(kcode))], key=lambda t: t[1])
_ovl = [(a[0], b[0]) for a, b in zip(_blk, _blk[1:]) if a[1] + a[2] > b[1]]
check('C27b 三块互不重叠且整块落在 MOD 区内 (%s)'
      % ' < '.join('%s 0x%06X+%dB' % (nm, va, sz) for nm, va, sz in _blk),
      not _ovl and _blk[0][1] >= MODB and _blk[-1][1] + _blk[-1][2] <= MODB + LY['mod_sz'],
      '重叠 %s / MOD 尾 0x%06X' % (_ovl, MODB + LY['mod_sz']))
KP.selfcheck_panel(kgot, PC, KL)
w('  [形态自检] kid_panel.selfcheck_panel 通过 (五段 / 守卫 / DC 配对 / 栈帧)')
kins = list(md.disasm(kgot, PC))

# ---- C27c: 串池每条 [u8 长度][GBK][NUL], 长度前缀与实字节一致 ----
_kbad = []
for _e in PD['strings']:
    raw = bytes(E(_e['va'] - 1, 1 + _e['len'] + 1))
    if raw[0] != _e['len'] or raw[-1] != 0 or raw[1:-1] != _e['name'].encode('gbk'):
        _kbad.append((_e['name'], raw.hex()))
check('C27c 串池 %d 条: 每条 [u8 长度][GBK][NUL] 且与声明长度逐字吻合' % len(PD['strings']),
      not _kbad, str(_kbad[:3]))
check('C27d 五维标签顺序 = child_growth.DIM_NAME (%s)' % '/'.join(CG.DIM_NAME),
      [e['name'] for e in PD['strings'][KP.S_DIM0:KP.S_DIM0 + 5]] == list(CG.DIM_NAME),
      str([e['name'] for e in PD['strings'][KP.S_DIM0:KP.S_DIM0 + 5]]))
# ---- C27e: 五维标签指针表落盘正确 (指向各条的长度字节处, 桩里 inc 后取字节) ----
_stb = [struct.unpack_from('<I', bytes(E(PD['strtab'] + i * 4, 4)))[0] for i in range(5)]
check('C27e KD_STRTAB 5 项 = 五维串的长度字节地址 (0x%s)' % ' '.join('%06X' % x for x in _stb),
      _stb == [PD['strings'][KP.S_DIM0 + i]['va'] - 1 for i in range(5)],
      str([hex(x) for x in _stb]))

# ---- C27f: 复用的族谱段 call 目标必须落在 .fdata(0x536000) 内且是那五段的真址 ----
_rr = PD['reuse']
_calls = [i for i in kins if i.mnemonic == 'call' and i.op_str.startswith('0x')]
_cva = sorted({int(i.op_str, 16) for i in _calls})
check('C27f 复用的 5 个族谱段全部落在 .fdata 内且地址与 tree_blobs.json 一致 (%s)'
      % ' '.join('%s=0x%06X' % (k, v) for k, v in sorted(_rr.items())),
      all(0x536000 <= v < 0x536000 + 0x17000 for v in _rr.values())
      and set(_rr.values()) <= set(_cva),
      '桩内 call 目标 %s' % [hex(x) for x in _cva])
# ---- C27g: GDI 槽位调用全部指向 GDI_TAB 内已声明的槽 ----
_sl = PD['gdi']['slots']
_gdi_calls = [i for i in kins if i.mnemonic == 'call' and i.op_str.startswith('dword ptr [0x')]
_gv = sorted({int(i.op_str[len('dword ptr [0x'):-1], 16) for i in _gdi_calls})
_expect_slots = sorted(PD['gdi']['tab'] + 4 * s for s in _sl.values())
check('C27g 全部 GDI 调用走 GDI_TAB 槽位 (tab 0x%06X, 命中槽 %s)'
      % (PD['gdi']['tab'], [hex(x) for x in _gv]),
      set(_gv) <= set(_expect_slots), str([hex(x) for x in _gv]))

# ---- C27h: ★ 面板算 P 与成长桩 cg_t_* 逐条同式 (本轮最重要的那条约束) ----
def _pn(mn, *pats):
    return [i for i in kins if i.mnemonic == mn and all(q in i.op_str for q in pats)]
# 成长桩侧的同一组形态 (mins_g = 已反汇编的成长桩)
_stub = {
    'R = bond*103': (len(_pn('imul', 'ecx, eax, 0x67')) == 1,
                     len([i for i in mins_g if i.mnemonic == 'imul' and '0x67' in i.op_str])),
    'R >>= 10': (len(_pn('shr', 'ecx, 0xa')) == 1,
                 len([i for i in mins_g if i.mnemonic == 'shr' and i.op_str == 'ecx, 0xa'])),
    '+P0': (len(_pn('add', 'edx, 0xa')) == 1,
            len([i for i in mins_g if i.mnemonic == 'add' and i.op_str == 'edx, 0xa'])),
    'cur/4': (len(_pn('shr', 'ecx, 2')) == 1,
              len([i for i in mins_g if i.mnemonic == 'shr' and i.op_str == 'ecx, 2'])),
    'clamp 下界 5': (len(_pn('cmp', 'edx, 5')) == 1,
                     len([i for i in mins_g if i.mnemonic == 'cmp' and i.op_str == 'edx, 5'])),
    'clamp 上界 85': (len(_pn('cmp', 'edx, 0x55')) == 1,
                      len([i for i in mins_g if i.mnemonic == 'cmp' and i.op_str == 'edx, 0x55'])),
    '主角 T 主维*25/100': (len(_pn('imul', 'eax, eax, 0x19')) == 1,
                          len([i for i in mins_g if i.mnemonic == 'imul'
                               and i.op_str == 'eax, eax, 0x19'])),
    '父 T 最高维*22/100': (len(_pn('imul', 'edx, edx, 0x16')) == 1,
                          len([i for i in mins_g if i.mnemonic == 'imul'
                               and i.op_str == 'edx, edx, 0x16'])),
    'T 上限 30': (len(_pn('cmp', 'eax, 0x1e')) == 1,
                  len([i for i in mins_g if i.mnemonic == 'cmp' and i.op_str == 'eax, 0x1e'])),
    'T 上限 28': (len(_pn('cmp', 'eax, 0x1c')) == 1,
                  len([i for i in mins_g if i.mnemonic == 'cmp' and i.op_str == 'eax, 0x1c'])),
    'B += tier*5': (len(_pn('imul', 'ecx, ecx, 5')) == 1,
                    len([i for i in mins_g if i.mnemonic == 'imul'
                         and i.op_str == 'ecx, ecx, 5'])),
    'B 上限 15': (len(_pn('cmp', 'edx, 0xf')) == 1,
                  len([i for i in mins_g if i.mnemonic == 'cmp' and i.op_str == 'edx, 0xf'])),
}
_bad = {k: (a, b) for k, (a, b) in _stub.items() if not a or b < 1}
check('C27h 面板 P 推导与成长桩 cg_t_* 逐条同式 (%d 条形态): 面板有且桩里也有' % len(_stub),
      not _bad, str(_bad))
# 数值同式: 用 child_growth 的参考实现与面板共享的常数逐项对表
check('C27i 面板与桩共用同一组常数 (T_LORD_MUL=%d T_FATH_MUL=%d T_LORD_CAP=%d T_FATH_CAP=%d '
      'ID_MASK=0x%X BOND_MUL=%d P0=%d P_MIN=%d P_MAX=%d)'
      % (CG.T_LORD_MUL, CG.T_FATH_MUL, CG.T_LORD_CAP, CG.T_FATH_CAP, CG.ID_MASK,
         CG.BOND_MUL, CG.P0, CG.P_MIN, CG.P_MAX),
      CG.T_LORD_MUL == 0x19 and CG.T_FATH_MUL == 0x16 and CG.T_LORD_CAP == 0x1e
      and CG.T_FATH_CAP == 0x1c and CG.ID_MASK == 0x700 and CG.BOND_MUL == 0x67
      and (CG.P0, CG.P_MIN, CG.P_MAX) == (10, 5, 85), '常数表被改过 -> 面板与桩要同步改')

# ---- C27j: cm_foster 里 call 面板前必须把五个参数都写好 ----
_fins = list(md.disasm(fgot, FVA))
_kc = [i for i in _fins if i.mnemonic == 'call' and i.op_str == '0x%x' % PC]
check('C27j cm_foster 内恰一处 call 详情面板 0x%06X' % PC, len(_kc) == 1,
      '命中 %d' % len(_kc))
_kj = _fins.index(_kc[0])
_wr = {k: [i for i in _fins[:_kj]
           if i.mnemonic == 'mov' and i.op_str == 'dword ptr [0x%x], ecx' % PD['kd'][k]]
       for k in ('ent', 'slot', 'act', 'teach', 'tier')}
check('C27k 五个参数在 call 之前各写一次 (ent/slot/act/teach/tier)',
      all(len(v) == 1 for v in _wr.values()),
      str({k: len(v) for k, v in _wr.items()}))
check('C27l 面板参数取自 cm_foster 的栈槽: ent=[esp+0x10] slot=[esp+0x14] act=[esp+0x18] '
      'teach=[esp+0x1c] tier=[esp+0x20]',
      all(any(i.mnemonic == 'mov' and i.op_str == 'ecx, dword ptr [esp + 0x%x]' % o
              for i in _fins[:_kj]) for o in (0x10, 0x14, 0x18, 0x1c, 0x20)),
      '栈槽读取缺失')
w('  手测: 回家 -> 培养孩子 -> 选完 孩子/活动/教席/档次 后应弹出 420x300 详情面板')
w('  (五维条 + 成功率 + 亲密), ESC 或单击关闭; 关掉才写 CMD_RING => CMD_PUSH 不涨 = 面板拦住了')
w('  ★ 面板上的 P 与桩实际掷骰用的是同一条式; 关掉 GDI 未解析时(从未开过族谱)会自动跳过, 不崩')

w('\n--- 埋点速查: 手测读这些地址 (M2 预载 / M3 成长+面板 / M4 元服 / M6 影子档 都已生效) ---')
w('%-18s %-10s %s' % ('埋点', '地址', '本轮期望'))
LIVE = {'GROWTH_PASS': '每趟月钩 +1 => = 走过的月数 (读档不涨)',
        'GROWTH_SETTLED': '每孩每结算月 +1 => = 在场孩数 x 月数 (元服后的孩子 nibble=0xf 出桩, 次月起不再计)',
        'GROWTH_DUPM': '同月二次触发才涨 (正常应一直 0)',
        'GROWTH_FREEZE': 'M4 起 = 元服人次 (每人只涨一次, 与 CHILD_GENPUKU 恒等; 不再是"人数 x 月数")',
        'GROWTH_FULL': '全维触顶才涨 (本批期望恒 0; 涨了 = 天花板算错)',
        'GROWTH_NATURAL': '自然加点次数, 上界 = 上表合计点数',
        'GROWTH_CMD': '每消费一条培养指令 +1 (M3c 面板按下才算, 本轮手动 poke CMD_RING 也会涨)',
        'GROWTH_ROLL': '过了五道门真掷了骰的次数; CMD - ROLL = REJECT',
        'GROWTH_REJECT': '被门拒掉(非儿童/不在岗/不在位图/活动或教席越界/已触顶)',
        'GROWTH_FAIL': 'rand(100) >= P 的落空次数; OK + FAIL = ROLL',
        'GROWTH_OK': '加成成功次数; 想核对就在同一月读该维是否 +1',
        'CHILD_INIT5': '开局/读档每人 +1 => 应 = 孩数 x 触发趟数',
        'MENU_COUNT': '每次弹回家菜单 +1 (含原生项的选择) => = 你进「回家」的总次数',
        'PANEL_OPEN': '培养孩子面板一弹 +1 => = 你选中「培养孩子」的次数(之后取消也算)',
        'KID_NOTSAME_CITY': '扫描中遇到"孩子在别的城"一次 +1 => 面板只列本城孩子, 这个数解释为什么少',
        'CMD_PUSH': '走完四级选完 +1 => = 你真正下成的指令条数',
        'KID_LAST_SLOT': '最后一条指令的孩子槽 (0 表示还没下过)',
        'KID_LAST_ACT': '最后一条指令的活动号 0..9',
        'SIDECAR_SAVE': '按一次保存 +1 => 与 SIDECAR_SAVED 相等才算影子档真落地',
        'SIDECAR_SAVED': '影子档 头+6 段全部写满并关闭 => = 你按保存的次数 (M6)',
        'SIDECAR_WERR': '影子档没落地: OpenFile 失败 或 某段没写满 (期望恒 0)',
        'SIDECAR_SLOT': '[obj+0x96] 解析不出 0..7 槽 (期望恒 0; 涨了=钩点上下文变了)',
        'SIDECAR_LOAD': '读档时影子档被打开 => 与 SIDECAR_RESTORE 相等才算孩子真回来',
        'SIDECAR_RESTORE': '长度+头+摘要全过、6 段已回填 => 扩展槽人物与培养状态保住了',
        'SIDECAR_MISS': '该槽没有影子档(老存档/换机) => 扩展槽归零, 原生部分照常读',
        'SIDECAR_REJECT': '有文件但校验不过(半截写/贴错档/容量档不符) => 归零不猜',
        'SIDECAR_GATE': '原生预校验失败([obj+0x8c]!=0): 桩一个字节不碰 => = 坏存档次数',
        'GROWTH_PUKU_MOUNT': 'M4 元服"挂上了人"的人次 = 随父成功 + 挂本国国主成功 两条路; = CHILD_GENPUKU - RONIN',
        'GROWTH_PUKU_RONIN': 'M4 元服走成浪人的人次 (无父/父不合格且本国查不到国主)',
        'CHILD_GENPUKU': 'M4 元服总人次; 身份式 = GROWTH_FREEZE = MOUNT + RONIN; 首月期望 = 开局到龄人数 (见 C25j3)'}
for n in list(GC):                          # json 保序 => 就是 build 里 GROWTH_CTRS 的下标序
    w('%-18s 0x%06X  %s' % (n, GC[n], LIVE.get(n, '(M3b-3/M3c/M4 才写)')))
for n, va in (('CHILD_PRELOAD', V['CHILD_PRELOAD']), ('CHILD_REARM', V['CHILD_REARM']),
              ('CHILD_SCAN', V['CHILD_SCAN']), ('CHILD_SKIP', V['CHILD_SKIP']),
              ('CHILD_PLACE', V['CHILD_PLACE']), ('CHILD_GENPUKU', V['CHILD_GENPUKU']),
              ('CHILD_INIT5', CNT['CHILD_INIT5'])):
    w('%-18s 0x%06X  %s' % (n, va, LIVE.get(n, '预载桩侧, 语义见 CHILD_STATE_RECIPE.md')))

w('\n桩源码 (与落盘字节同源, 便于人工复读):')
for ln in csrc.splitlines():
    w('  ' + ln)
OUT.close()
n_ok = sum(1 for ln in open(REV / '_verify_children.txt', encoding='utf-8') if ln.startswith('OK '))
print('批次 %s / %d 人 : 通过 %d 项, 失败 %d 项%s' %
      (BATCH, len(ENTRIES), n_ok, len(FAIL), ' -> ' + ', '.join(FAIL) if FAIL else ''))
print('明细 -> .rev/_verify_children.txt ; 预期表 -> .rev/_child_expect.json')
sys.exit(1 if FAIL else 0)
