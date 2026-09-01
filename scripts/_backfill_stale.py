# -*- coding: utf-8 -*-
"""回填陈旧 still_unknown: 已被后续续号破解但仍挂未破的条目。"""
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

EDITS = [
    ("diplomacy_spec.json",
     "AI 主动外交决策（续89 遗留，仍未破）",
     "✅ [已破·续104] AI 主动外交决策: 0x4a0d50→0x4a6ba0→0x4a70b0(49省派发)→0x4a84e0(外交决策)。"
     "先由 0x4a8840/0x49faf0 建国力表 0x5259e8(上限60000); Loop1 在 get_master_vassal==2 省中"
     "选国力最强者 → set_master_vassal(0)+set_diplomacy(min(rel+2,7))+MSGX 0xd1f; "
     "Loop2 对邻接省(mv==1)同法 +MSGX 0xd1e。确定性无 RNG。"
     "🔴 续96 设想的「AI 调 0x4b5bcb/0x4b6095」路径不存在(两者零直接调用方)。"
     "产物 ai_diplomacy_ref.py"),

    ("duel2_spec.json",
     "体力 word[0x514995]/[0x514835] 的**初始值**赋值点（全镜像只有读/dec/cmp，初值走运行时间接填充）",
     "✅ [已破·续121] 体力机制: 存储 word[0x514995](攻)/word[0x514835](守); "
     "0x466340 主循环每 tick dec(0x46636d/0x46637b); 归零则 0x466490 分胜负; "
     "getter 0x466e40 依 this+0x10 选攻/守返回。**初值=角色体力**, 由决斗编排器 0x46bc00 → "
     "设置链(0x46baa0/0x46bbb0/0x46ba20) 经计算偏移写入(全镜像绝对写仅命中 dec)。"
     "产物 duel_hp_ref.py (17/17)"),

    ("duel_spec.json",
     "体力上限与初始值（word[0x514995]/[0x514835] 的初始赋值 = 寄存器间接写入, 静态映像无绝对 store, 需 emu）",
     "✅ [已破·续121] 同 duel2_spec: 初值 = 战斗员『体力』状态值, 写入于 0x46bc00 编排链(计算偏移, "
     "非绝对 store); 每 tick 行动方 -1; 任一归零即 0x466490 分胜负。无独立『上限』字段。"
     "产物 duel_hp_ref.py (17/17)"),

    ("promote3_spec.json",
     "byte[+0x2d] bit3 在继承取名分支中的确切含义",
     "✅ [已破·续122/127] +0x2d 是 16-bit 状态字 +0x2c 的高字节, 位域定案: "
     "低3位=身分码(0..7, 消费者 0x447843/0x4d3f07); bit3(0x08)=flag(🔴 续122 原判『无消费方』有误, "
     "实锤消费者 0x4a3ddf/0x4e9beb); bit4=谋反标记 F4(near-dead, 0 调用); "
     "bit5-6=F2B 序列関係 2-bit 枚举(0..3); bit7=已故/除籍。"
     "产物 entity_status2d_highbits_ref.py (149/149)"),
]

for fn, old, new in EDITS:
    p = _ROOT + '/scripts/' + fn
    d = json.load(open(p, encoding="utf-8"))
    key = None
    for k in ("still_unknown", "open_questions"):
        if k in d and any(old == str(x)[:len(old)] or old in str(x) for x in d[k]):
            key = k
            break
    if key is None:
        print(f"  [SKIP] {fn}: 未找到目标条目")
        continue
    hit = 0
    for i, x in enumerate(d[key]):
        if old in str(x):
            d[key][i] = new
            hit += 1
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    d2 = json.load(open(p, encoding="utf-8"))
    print(f"  [OK] {fn} [{key}] 替换 {hit} 条 -> 已闭 {sum(1 for x in d2[key] if str(x).startswith('✅'))}/{len(d2[key])}")
