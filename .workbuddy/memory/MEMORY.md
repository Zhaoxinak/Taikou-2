# 太阁立志传2 Godot 复刻 - 项目记忆（索引）

> 细节在仓库文档；本文件只留跨会话必需的边界/方法论/当前状态。
> 文档链：README.md → BREAKTHROUGHS.md(倒序突破日志) → GAME_DATA_SPEC.md → BATTLE_SPEC.md → SNDATA_SPEC.md。旧文档 → docs/archive/。

## 边界
- Godot 4.7.1 自写；原版在 `<工程>/Taikou2 Original/`（仓库不打包素材）。
- 2026-08-25 起：停 UI/像素/字体，只做数值+玩法 → 汇总进 GAME_DATA_SPEC.md。
- **硬性要求**：突破/推翻旧假设即插 BREAKTHROUGHS.md 倒序条目（四段：突破/证据/仍未知/下一步）。**接手先 `grep -o '上一条（续[0-9]*）' BREAKTHROUGHS.md | grep -o '[0-9]*' | sort -n | tail -1` 取 max，新条目 max+1 防撞号**（并行轨曾撞号，本轨改号续167）。

## 逆向方法论（核心坑，去重）
- 映像 `scripts/_unpacked_mem.bin`(2MB, base 0x400000, OEP 0x4f44b0)。反汇编 capstone(skipdata=True，全镜像调用点计数必须 capstone)；emu Unicorn 2.1.4（`mu.reg_write/read(UC_X86_REG_ESP)` 非 `.reg_esp`；stdcall 钩子须 `esp+=4*nargs`）。
- ⚠️ `_insn_addrs.pkl` 有空洞(`0x49b417..0x49b43a`)且 `_d[0/1]` 存文件偏移非 VA(须`+BASE`)。关键处用 `scripts/_lindis.py` 现场反汇编核对。
- ⚠️ capstone 共享 `Cs` 禁嵌套 `disasm()`（先物化 list）；`X86_OP_MEM` 顶层不导出。
- 🔑 定 stride 三证据：lea 系数 / 乘减序列 / 除法魔数（÷10=`0x66666667`+sar2、÷12=`0x2aaaaaab`+sar1、÷14=`0x92492493`+sar3、÷31=`0x84210843`+sar4、÷47=`0xae4c415d`）。
- 🔴 多 struct 陷阱：「位移命中」≠「字段命中」（溯源基址寄存器）；「静态抓不到写入」常因 setter 按 `ecx=base+N` 参数化传入（沿 call 下探找 `push <base>; call helper`）。
- 🔴 共享方法库陷阱：`0x49b960..0x49bda8` 通用 setter 库；偏移出现该区≠属某 struct，须绝对 xref+确认真实 this+读写方向（续155/续191 均应用）。
- 🔑 bitset 定语义须扫 setter；整字覆盖 vs 带掩码=位域/标量分水岭；先查文档/数据分布再定语义，禁止猜表形状。

## 通用原语与族
- 饱和算术：`0x4ebca0`=`sat_add(a,b,cap)`；`0x4ebcd0`=`sat_sub(a,b)`。
- 实体字段增量族 18 包装器 `byte[f]=sat_add(byte[f],delta,cap)`（功勲/忠诚/体力/野心）。
- 相性 `0x49ffc0(t,l)`：跳表 `@0x4a0028` T=[4,2,3,1,4,2,0]（非单调须照抄）；setter `0x49a5a0`(ecx=base+8)。
- is_alive `0x470690`；候选池 `0x45e3e0`→`0x51e9c0`（÷47 魔数 `0xae4c415d`）。

## 关键几何（速查）
- 实体 370×47B@`0x519868`：五维`+0x0a..+0x0e`、技能`+0x0f..+0x11`、国索引`+0x24`、在城`+0x25`、主君`word+0x2a`(0xffff=浪人)。
- 城表 `0x51eb88` 31B×200（城指针-0x51eb88 得索、×16+0x516a28 得 S7 条目）；国情表 `0x519548` stride5×49；国政治表 `0x5179b8` stride14×49(`byte[0xc]`=外交等级=低4位level+高4位quality)；S15 事件旗 `0x5203c0` 25B(段A/B 14bit定名，段C 6B待破)；名称总表 `0x506ca8` stride9。
- 国名/城町名/别名 getter：`0x49b400`/`0x49b140`/`0x49b440`（岐阜/长滨/安土/大阪，共用 S15 段A/B bit）。
- S7 每城表 `0x516a28` 200×16B：续155 钉结构；续191 钉 `+0x0f` 位域（低4位=bits0-3 setter `0x49bf50` / 高3位=0x70 bits4-6 setter `0x49bf90`，与 test 0x70 互证；ecx←`0x516a28+16*idx` 坐实专属）。

## 当前状态（2026-09-01，续193 为止）
- 已破解约 19 模块（经济/单挑/合战/事件/内政/外交/评定/晋升/城表/武将/国情/SNDATA/S7…），详见 `破解状态清单.md §1`。
- 最新五项：**续189** P0 49B payload 全量指纹(171型，type=0x01=43独立布尔开关)；**续190** #89 合战5标志精确语义(9/9)；**续191** S7 `+0x0f` 位域语义(8/8，ecx←S7基坐实专属)；**续192** S7 `+0x08` 状态机归属判定(4/4：共享库非 S7)；**续193** emu 仿真骨架 `emu_harness.py` 落地(Unicorn 2.1.4，叶子函数自测 ALL PASS) + S15 段C 运行期再验证(5/5，布局=byte[+0x13+idx] 与续151 一致)。
- **⚠️ S15 段C 语义已于 续151 定名**（segC[0]=S13目标索引/segC[1]‖[2]=16-bit打包参数/segC[3]=表@0x513550索引/segC[4]=×1000喂S13初始化/segC[5]=事件内计数），`scripts/s15_segc_ref.py` 存证；续193 仅 emu 再验证 + 补 usage-pattern(25 call-site 中 idx/val 多为运行时变量→可变状态槽)，非新命名。
- **残留敞口（全须 emu，静态已到极限；现已有 emu_harness 基础设施）**：① P0 49B 字段命名(type=0x01 的43布尔各=？/ benum 索引落点实体·城·国表，须 emu 钩 `0x47fc60`/`0x4e8604` 抓消费者)；② #19 兵种中文名(emu 抓精灵 label)；③ #89 consumer 门控(钩 5 全局 MEM_READ 抓读者)；④ S7 `+0x04`/`+0x0c` 写入路径(emu 钩 `0x516a28` 抓读者/写者)；⑤ 段C「事件id×slot×val」全映射(须 emu 钩 `0x49c500` 在事件解释器运行期抓，须先解决解释器 boot/回调)。

## ⚠️ 并行会话冲突
- 并行会话曾同时改 BREAKTHROUGHS/GAME_DATA_SPEC/MEMORY 致撞号+整份覆盖。**接手先 grep 取 max 续编号用 max+1**；撞号≠错误（两轨独立收敛同结论互为交叉验证）。

## Godot 约定
- 预渲染画作 LINEAR+MIPMAPS；像素 NEAREST+STRETCH_KEEP；CJK 走系统字体。
