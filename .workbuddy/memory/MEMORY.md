# 太阁立志传2 Godot 复刻 - 项目记忆（索引）

> 细节一律在仓库文档，本文件只留跨会话必需的边界/方法论/待破清单。
> **文档链**：`BREAKTHROUGHS.md`(时间线增量·接手第一读) → `GAME_DATA_SPEC.md`(单一复刻文档) → `BATTLE_SPEC.md` → `HANDOFF.md` → `REVERSE_ENGINEERING.md` → `HJMAPDAT_SPEC.md`/`NPK_SPEC.md`

## 边界
- Godot 4.7.1 代码自写；原版数据从 `F:/Games/Taikou2` 读（用户合法拷贝·本地单机）；仓库不打包素材。
- **2026-08-25 起**：停 UI/像素/字体，只做「数值+玩法」→ 汇总进 `GAME_DATA_SPEC.md`，美术用户自配。
- **用户硬性要求**：每次突破或推翻旧假设，立刻在 `BREAKTHROUGHS.md`「任务清单」下方插 dated 条目（四段：突破内容/证据/仍未知/下一步）+ 打勾，倒序（新在上）。

## 逆向方法论（必守）
- 映像 `scripts/_unpacked_mem.bin`（2MB，base 0x400000，OEP 0x4f44b0）。
- 全镜像仅 80 处标准栈帧序言 → **函数边界必须由「所有 call rel32 目标」推导**；线性反汇编逐 4KB + `va+=1` 重同步。
- 工具：`_fdis.py`(符号反汇编，**只吃 call-target 函数头**)、`_lindis.py`、`_profile_all_funcs.py`、`_string_pool_scan.py`(串池+stride)、`_xref_reads.py`(读地址穷举)、`_emu_battle.py`/`economy_price_probe.py`(Unicorn 2.1.4 范式)。capstone 需 `from capstone.x86 import *`。
- 大量数值表**静态全 0、运行时托管填充**（C++ 对象+虚表）→ 静态走不通就 Unicorn 实跑。
- **🔑 禁止「猜表形状」，必须穷举**：串池扫描一次挖出 11 张名表，推翻此前「兵种名不在 EXE」；数值表同法（穷举读地址而非假设结构）。
- 教训：切片伪像会造假表；xref 只抓绝对立即数；已四次误判「唯一 xref 的静态表」语义 → 先确认引用函数真起点。

## 已破（速查，细节见文档）
格式 LS11/MSGX/GRP/IDX/SMODE/TOWNCHIP/KOS；BSDATA 700武将×59B(home_city+status→派生归属)、TOWNPOS 92城、SNDATA XOR流地图+833×49B明文层、SAVEDATA 16×20480B槽；名表 `0x506ca8` stride9×370；`HJMAPDAT.DAT` 38×1700B；per-tick 伤害 `0x42d270`(Unicorn 双证)；天气/季节/气候 §3.9；**49国国情 `0x519548` 字段全闭合**（`province_ref.py`，雪国36）；合戦布陣+計略 §3.10；静态中文名表 11 张 §3.11；地形攻防系数 §3.12；技能/官位/授艺、经济(买价=基价×1.5 已验)、事件 27 类型。
**阵形名确认不存在于 EXE**（2014 条 CJK 串零命中）⇒ `byte[p+4]` 只是内部编号，复刻可自命名。

## 仍待破
1. 国情 `+0` 低4位可读名 / `+2` 其它 bit / `0x47e440` 11B 扩展字段名。
2. SNDATA 流尾实体（200/30/20…）逐字段；商品基价 `0x513ea8`；物品池种子。
3. 评价词 8 组↔10 字段绑定（emu `0x47ca70`）；逐事件 handler。

## Godot 侧约定
预渲染画作 LINEAR+MIPMAPS；像素艺术 NEAREST+STRETCH_KEEP；mipmap 只在 Image 上生成；CJK 走系统字体（**所有 `*CHAR.LZW` 是角色精灵不是字体**）。
