# 太阁立志传2 Godot 复刻 - 项目记忆（索引）

> 细节在仓库文档；本文件只留跨会话必需的边界/方法论/当前状态。
> 文档链：README.md → BREAKTHROUGHS.md(倒序突破日志) → GAME_DATA_SPEC.md → BATTLE_SPEC.md → SNDATA_SPEC.md。旧文档 → docs/archive/。

## 边界
- Godot 4.7.1 自写；原版在 `<工程>/Taikou2 Original/`（仓库不打包素材）。
- 2026-08-25 起：停 UI/像素/字体，只做数值+玩法 → 汇总进 GAME_DATA_SPEC.md。
- **硬性要求**：突破/推翻旧假设即插 BREAKTHROUGHS.md 倒序条目（四段：突破/证据/仍未知/下一步）。**接手先 `grep -o '上一条（续[0-9]*）' BREAKTHROUGHS.md | grep -o '[0-9]*' | sort -n | tail -1` 取 max，新条目 max+1 防撞号**。

## 逆向方法论（核心坑，去重 · 可复用）
- 映像 `scripts/_unpacked_mem.bin`(2MB, base 0x400000, OEP 0x4f44b0)。反汇编 capstone(skipdata=True)；emu Unicorn 2.1.4（`mu.reg_write/read(UC_X86_REG_ESP)` 非 `.reg_esp`；stdcall 钩子须 `esp+=4*nargs`）。**包在系统 python3.7**（`/Library/Frameworks/Python.framework/Versions/3.7/bin/python3`）；managed venv 未装 capstone/unicorn，跑脚本用它。
- ⚠️ `_insn_addrs.pkl` 有空洞(`0x49b417..0x49b43a`)且 `_d[0/1]` 存文件偏移非 VA(须`+BASE`)。关键处用 `scripts/_lindis.py <va> <nbytes>` 现场反汇编核对。
- 🔑 定 stride 三证据：lea 系数 / 乘减序列 / 除法魔数（÷10=`0x66666667`+sar2、÷12=`0x2aaaaaab`+sar1、÷14=`0x92492493`+sar3、÷31=`0x84210843`+sar4、÷47=`0xae4c415d`）。
- 🔑 定 stride 整除性单独不足，须叠加「两样本 diff 位置 mod stride 的列对齐集中度」并查倍数确认基本周期（59 占用率 .559/热点 .341 vs 非整除 stride 全 1.000/<0.05；118 是其倍数须排除）。
- 🔴 多 struct 陷阱：「位移命中」≠「字段命中」（溯源基址寄存器）；「静态抓不到写入」常因 setter 按 `ecx=base+N` 参数化传入。
- 🔴 共享方法库陷阱：`0x49b960..0x49bda8` 通用 setter 库；偏移出现该区≠属某 struct，须绝对 xref+确认真实 this+读写方向（E8 + raw 字面双重 0 调用方 = 共享库，续191/续192 应用）。
- 🔑 抽 `call` 实参不能从单一固定起点反汇编（x86 变长指令必错位，实测 0 命中）。正解 = 枚举回溯 `back=1..span`，只接受「指令流中存在 `address==call_va`」的起点（边界对齐），取 back 最大者。
- 🔑 函数边界用「最大 call/jmp 目标 ≤ va」，别用 `push ebp;mov ebp,esp` prologue 模式（本 EXE 大量 FPO 函数无标准 prologue）。
- 🔴 emu 读内存 ≠ 读静态镜像：栈/局部缓冲地址在静态 bin 里是垃圾，校验回调实参里的字符串**必须 `mu.mem_read()`**。Unicorn 有 TB 缓存，`mem_write` 改写桩代码不一定生效 ⇒ 切换桩行为必须新建 `Uc` 实例。
- 🔑 同调用链可并存三种约定：`play_sfx` 1 栈参、`0x499780/0x499770` thiscall(无栈参+普通 ret，桩 esp+=4)、`0x4015f0` cdecl 3 参、`[0x4fb07c]` 加载回调 stdcall 3 参(callee 清栈 ret 0xc)。桩写错任一即栈崩。
- ⚠️ 连通块数/孤立像素点对转置与镜像不变 ⇒ 行主序 vs 列主序（转置）无法由数据单方面区分。

## 通用原语与族
- 饱和算术：`0x4ebca0`=`sat_add(a,b,cap)`；`0x4ebcd0`=`sat_sub(a,b)`。实体字段增量族 18 包装器 `byte[f]=sat_add(byte[f],delta,cap)`。
- 🔑 **技能写器族（续240）**：`0x4a3040+k*0x20`(k=0..9=技能id) = cap-3 递增器，thiscall `ecx=实体+0x0f`，对 `byte[ecx+k>>2]` 的 `(k&3)*2` 位 +1 封顶 3；全镜像调用点 19 处（k0@0x45fdc8/0x4de171…）；驱动 = `0x45fca0`(唯一调用方 0x45f3eb, mode0-2→k0/k7/k5) 与双胞胎 `0x4de0e0`(玩家对象=0x49f5e0(), mode→k5@0x4de136/k7@0x4de152/k0@0x4de16c)。功勲加算 `0x4a3210`=饱和加 `word[实体+0x26]` 上限 60000(0xea60)。
- 相性 `0x49ffc0(t,l)`：跳表 `@0x4a0028` T=[4,2,3,1,4,2,0]；setter `0x49a5a0`(ecx=base+8，写实体+0x08 字 bit11-14)。
- is_alive `0x470690`；候选池 `0x45e3e0`→`0x51e9c0`（÷47 魔数 `0xae4c415d`）。

## 关键几何（速查）
- 实体 370×47B@`0x519868`：五维`+0x0a..+0x0e`、技能`+0x0f..+0x11`、国索引`+0x24`、在城`+0x25`、主君`word+0x2a`(0xffff=浪人)、相性`+0x08`字bit11-14。
- 城表 `0x51eb88` 31B×200；国情表 `0x519548` stride5×49；国政治表 `0x5179b8` stride14×49(`byte[0xc]`=外交等级=低4位level+高4位quality)；S15 事件旗 `0x5203c0` 25B；名称总表 `0x506ca8` stride9。
- S7 每城表 `0x516a28` 200×16B：续191 钉 `+0x0f` 位域（低4位=bits0-3 setter `0x49bf50` / 高3位=0x70 bits4-6 setter `0x49bf90`，ecx←`0x516a28+16*idx` 坐实专属）。

## 资源 / 音效 / 格式（续195–197 已闭）
- **90 资源名串**：正则 `[A-F]:[A-Z0-9_]{1,12}\.[A-Z0-9]{2,3}`+NUL，全镜像 90 distinct/16 组。
- **音效**：`@0x50ba40`=40 项音效名指针表；`0x4997c0`=`play_sfx(id)`（上限 `cmp si,0x27`=39）；门控四层；emu 39/39；ID 语义 30/39。全局开关 `byte[0x520604]` bit1。
- **资源加载簇**：`0x4802e0`→`0x4ec8c0`(`add eax,2` 剥 `X:` 盘符 + `and al,0xfb` 清 bit2 + 跳表 `0x4ec948` + `call [0x4fb07c]` stdcall3参 ret 0xc)；主资源表 `@0x506ad0`=19 项 stride16。🔑 盘符是 EXE 内部逻辑代号非真实路径 ⇒ Godot 按去前缀裸名查原版目录；中文版 BGM 走 `MP3/`。
- **KOS = 1字节XOR密钥+标准WAV**：`raw[0]`=key(39/39 均 `0xAE`)，`raw[1..]` 逐字节 XOR→RIFF/WAVE；解码器 `0x499380`=`xor16(buf,key16,len)`。密钥读自文件第0字节（`0x4993a0`），全镜像无 `xor …,0xae` 立即数。
- **GAIJI.TR2 = 16×34B=544B**：`u16 LE` 源码 + 32B 16×16 1bpp（行主序 MSB 先行）；`0x48c070` 加载/`0x4f1ae6` 安装(`cmp 0xa140`/`cmp 0xa14f`)/`0x4f1a06` 取字形；GBK 码位 `0xA140..0xA14F` 被劫持作外字区。
- **TR2 四类**：`SAVEDATA`(magic `TAIKOU2_SAVEFILE`, 8槽×40960B, 续199) / `SCENARIO`(`TAIKOU2_SCENARIO`, 续165 18子解码器) / `BSDATA`(700×59B 明文主表, 续200) / `GAIJI`。**头 +0x10 4B（续202 实锤）**：`file[0x10..0x11]`=16-bit LE 校验和（解密流字节累加和 mod 0x10000，sc1=0xb84b/sc2=0x8013）、`file[0x12..0x13]`=XOR 密钥种子(key=byte[0x12]^byte[0x13]，sc1=0x0c/sc2=0x0a)；emulator 真跑 `0x47f350` 在 `0x47f4da` 捕获累加器匹配。`scripts/sndata_header_ref.py` ALL PASS。

## 存档 / 武将主表（续199·续200·续201 已闭）
- **SAVEDATA.TR2 = 8 槽 × 40960 B**（续199 纠偏 16×20480）。槽元数据 49B：年/月/日 u16 + 主角名13 + 国13 + 地+身分17 = 49 闭合；slot0 = 1560-05-20/木下藤吉郎/尾张/清洲城步兵头。
- **BSDATA1/2.TR2 = 700 × 59 B 明文主表**（续200）。加载器 `LoadBSDATA @0x47fa90`(`push 0xa154`=41300)。`+0x27`=生年−1490、`+0x30`国/`+0x31`城(0..199 索引200条城表)/`+0x32`功勲/`+0x35`忠诚/`+0x36`主君w/`+0x38-0x39`状态字(`職位=byte[0x39]&7`)/`+0x3a>>4`主角槽+武将档。
- **SNDATA S1 = BSDATA 模板的剧本实例**（续201，64/64）：59B 流记录 ↔ 47B 实体双向映射；`entity+0x04`=同城武将单链表 next、城结构`+0x00`=链头、`+0x04`=下一城；相性存实体+0x08 字 bit11-14。

## 当前状态（2026-09-03，BREAKTHROUGHS 顶部 = 续240，本批已入库 d510d50）
- **双轨并行合并完成**：origin 轨续224-237 + 本地轨续224-227（六类顾问咨询消费链/0x462fd0 typekey map/leaf schema）**并集共存入库**（撞号不重排）；SNDATA_SPEC B 轨三节顺延 §4.0.13-4.0.15；记忆同步补交 22e5fd5。
- **静态/结构层 100% 收口**（续230-232 终审）：142 原始文件 = 56 CRACKED_NONIMAGE 全 PASS + 33 IMAGE_EXEMPT + 53 RUNTIME_ASSET + 0 UNKNOWN；自测套件 `_run_all_selfchecks.py` PASS（续240 后 = **163/0**，含新 ref）。
- 最近主破（顶部条）：续236 S7 写入路径；续237 技能 2-bit 位打包 + 名表纠错=算术/兵法；续238 S13 矩阵段文件侧终审（0x47ef00 装载几何 20×114B@pitch139、总表基址纠偏→0x518588、两剧本 S13 段全 0xFF 占位、静态解密校验和全中）；续239 技能运行时读侧闭合（读侧无统一 getter=散布内联 2-bit 提取，写侧单指令掩码 RMW 0 命中）；**续240 技能写侧闭合**（写器族 `0x4a3040+k*0x20` cap-3 递增 + §4.3.3 mode0-2 站点 `0x45fca0`/`0x4de0e0`，族调用点 19 处可枚举，功勲加算 `0x4a3210`→`word[+0x26]` 钳60000）。
- 仅余 **emu 运行期增强**（数值/数据非逻辑、不阻塞复刻），详见下方残留敞口与 `破解状态清单.md §2`。

## 残留敞口（2026-09-03 快照 · 非图像结构层已清零）
- 用户指令 = 全部**非图像**敞口；图像类（GRP 5文件 RGB565、PK8 颜图、纯像素 LZW）2026-08-25 明令豁免 → 保持不动。
- **非图像结构层零真敞口**（续231/232 终审确证 56/56 PASS）。仅剩 **emu 运行期增强**项（均数值/数据、非逻辑缺口）：
  - S15 段C bit1 静默事件 MSG 外置路径；segC[3]=`0x513550` 战斗单位池运行期索引值（续227）。
  - `0x518588` 20×5×5 word 矩阵逐格值：结构已闭（续225）+ **文件级占位 0xFF 坐实（续238，两剧本 S13 段全 FF，装载布局 25w+25w+5w+4B@每记录）**，值运行期由写回器 `0x4a0ff0/0x4a1010/0x4a1030` 填，须 emu 钩取。
  - `0x462fd0` typekey map 6 项二分键值：键数组 [esp+0x2c] 运行期填（本地轨续224），emu 跑 SNDATA 加载 0x5152d0 可查。
  - BSDATA 尾 5 字节 `stream 0x28..0x2c` 精确玩法语义：统计特征化已闭（续235），须 MSGX/emu 交叉坐死。
  - 技能读写侧均已闭（读=续239 四消费点内联、写=续240 递增器族 19 站点）；9 音效 ID 中 15(ZANSYU)/36(MATISIRO) 语义中置信（续226）。
  - 小项：`byte[ent+0x24]`/`0x517aa5` bonus 语义、S6/S7 关系、4 处寄存器派生站点、15 外字中 10 身份未认。

## ⚠️ 并行会话冲突
- 并行会话曾同时改文档致撞号+整份覆盖。**接手先 grep 取 max 续编号用 max+1**；撞号≠错误（两轨独立收敛同结论互为交叉验证）。

## Godot 约定
- 预渲染画作 LINEAR+MIPMAPS；像素 NEAREST+STRETCH_KEEP；CJK 走系统字体。
