# 太阁立志传2 (TAIK2W95) 逆向工程 / 数据破解文档

> 本文件记录对 1995 年 KOEI《太阁立志传2》PC 中文版（`F:/Games/Taikou2`，用户合法拷贝）的
> 全部逆向/数据提取成果。
> **法律边界**：用户已声明合法拥有该拷贝、仅本地单机复刻、不传播。本工程不打包任何原版素材，
> 运行时从用户目录读取。所有破解仅用于"引擎重实现 / 数据提取"，不用于绕过任何付费/在线验证。

---

## 0. 一句话结论

- **数据层大部分已破**：LS11 解压 100%；32×`.LZW`、GBK 文本、BSDATA、城镇坐标、TOWNMAP/SHOPMAP 布局、多数 CHIP/CHAR 图形格式、以及 **`NPKDATA.IDX`（23 条 4bpp 图像，全部解码验证）** 已破解。
- **仍依赖 EXE 的硬阻塞**（复刻「问题很多」的根因）：
  1. **引擎逻辑**：合战/单挑完整规则、SNDATA 事件语义（**数据驱动，非字节码 VM**）、运行时调色板。
  2. **EXE 加壳（FuckALI）**：已用 Unicorn **静态脱壳成功**（§2），剩余是分析解压后的引擎代码。
- **🚨 KOS 重大纠偏（2026-08-24 深夜，推翻此前全部 KOS 假设）**：`.KOS` **不是事件脚本、也不是字节码 VM**——它是 **KOEI 音效（RIFF/WAVE，mono 22050Hz 8-bit PCM）**。布局 = `byte[0]=0xAE` 标记 + `byte[1:]` 逐字节 XOR `0xAE` 的完整个 RIFF/WAVE（**39/39 校验合法**，riff_size 自洽）。此前把 `data` 段 / `0x7D` 曲线 / uint16 当"脚本/opcode"**完全是误读音频 PCM 数据**。故 `KosVm.gd`、`kos_opcodes.json`、`_verify_kos_*.gd`、`kos_message_map.json` **全部作废**。事件真相：剧情由 **EXE 引擎 + `SNDATA` 数据 + `MESSAGE*.LZW` 文本 + `.KOS` 音效(SFX)** 数据驱动，并非独立脚本文件。解码产物见 `scripts/kos_wav/*`。
- **推荐策略**：**先补全数据文件文档 + 分析脱壳后 EXE 引擎 + 再复刻玩法**（见 §0.1）。不要一边猜玩法一边堆 Godot 功能。

### 0.1 策略选择：先破 EXE 还是先复刻？

| 路径 | 适合 | 风险 |
|------|------|------|
| **A. 数据优先**（推荐先做 1–2 周） | 把剩余 `.LZW`/`.TR2`/`.GRP` 格式补文档、出图验证 | 不解决 VM/合战，Demo 仍会「像但不真」 |
| **B. EXE 优先**（A 之后或并行） | KOS VM、SNDATA 事件、合战、真调色板 | 需 x32dbg/IDA；FuckALI 无一键工具；周期难估 |
| **C. 边复刻边猜**（当前痛点来源） | 快速出 Demo | 技术债爆炸；`KosVm.gd` 等均为启发式 |

**用户（XIN）倾向 B 是合理的**。建议执行顺序：

```
阶段 0（1–3 天）  整理/统一本文档 + REPLICATION.md，跑通 52 个 _verify_*.gd
阶段 1（1–2 周）  数据文件扫尾：SNDATA 字段、GRPDATA/IDX、合战地图 HBMAP/HKMAP、END/SMODE
阶段 2（核心）    EXE 脱壳 → 字符串/导入表/API 追踪 → KOS 解释器定位 → 写 VM 规范文档
阶段 3            按 VM 规范重写 Godot 复刻（替换 KosVm 猜测逻辑）
```

**不必等阶段 2 100% 完成再动 Godot**，但 **KOS 事件 / 合战 / 多结局** 应等阶段 2 有 VM 文档后再做，否则继续踩坑。

### 0.2 什么不依赖 EXE（现在就能继续）

- LS11、MSGX/GBK、BSDATA 59B、TOWNPOS、TOWNMAP/SHOPMAP
- KOS = **音效 WAV**：`byte[0]=0xAE` 标记 + 其余 XOR `0xAE` = RIFF/WAVE（mono 22050Hz 8-bit PCM）。已 39/39 解码到 `scripts/kos_wav/`（见 `_decode_kos_wav.py`）。`TaikouKos.gd` 的"data 容器"假设废止。
- 多数 CHIP/CHAR 解码（结构已知；**色相**可能需运行时调色板）
- `rmKOEI.bin`（24KB 未加壳 PE DLL，**卸载程序 DLL**（textsub.cpp, 1996），与字体/文字解码无关——旧"字体渲染器"定位已证伪，见 `ENGINE_SPEC.md` §7.1）

### 0.3 什么必须依赖 EXE（脱壳后）

- ~~KOS opcode/VM~~ **已证伪**：`.KOS` 是音效（见 §6.1），不存在事件字节码 VM。`KosVm.gd` 等作废；事件语义看 **SNDATA（数据）+ EXE 引擎**。
- SNDATA 标志 → 剧情/事件触发条件
- 合战、知行、忍者等系统状态机
- TOWNCHIP 等 **真·16 色调色板**（若不在数据文件中内嵌）

---

## 1. 原版文件总览（共 82 个数据文件）

| 类别 | 文件 | 大小 | 状态 |
|------|------|------|------|
| 引擎 | `TAIK2W95.exe` | 451 KB | ⚠️ 加壳 (FuckALI)，见 §2 |
| 压缩数据 | `*.LZW` ×32 | — | ✅ 全部 LS11 解压成功（§3–§5） |
| 二进制数据 | `*.TR2` ×6 | — | ✅ BSDATA/SNDATA 部分破解（§5.6） |
| 图形容器 | `*.GRP` ×5 | — | ✅ 已解（§5.3） |
| 表/索引 | `*.DAT` `*.IDX` | — | ✅ TOWNPOS/TOWNTBL 已解 |
| 视频 | `*.AVI` ×5 | — | ⏸ 未处理（OP/ED/Logo） |
| 字体 | `_font_*.bmp` `_*_strip.bmp` | — | ✅ 真·位图字体（§5.5） |

---

## 2. EXE 分析（TAIK2W95.exe，451,584 B，Win32 PE）

```
MZ 头 → PE (machine=0x14c i386, subsystem=2 GUI)
节区:
  FuckALI  vsize=798720  vaddr=0x1000   rsize=0      (保留/运行时解压)
  FuckALI  vsize=450560  vaddr=0xc4000  rsize=447488 (游戏主体代码/数据)
  .rsrc    vsize=4096    vaddr=0x132000 rsize=3072   (图标/清单，价值低)
```

> ⚠️ **本节旧结论已修订（2026-08-24 `_probe_exe.py` 实测）**：原"447KB 全是乱码、读不到导入表"有误，详见 **§2.0 静态探针基线**。

**关键判定：代码段被打包/混淆（已量化确认）。**
- 节区 1（FuckALI#1，文件体 447,488 B）**熵 = 7.92** → 主体确为压缩/加密代码，运行时才解压。
- **但节区 1 内散落可读 ASCII 串（6450 条）**：数据文件名引用片段（`v:HBMAP.LZW+`、`bAM/SCENARIO`、`ffKOEILOGO.3Q`、`o_HD.GRP`、`MESSAGE1!`、`KOU2_SAVEFILE)/NEW`、`ime error 6`）与 UTF-16LE 版本资源（`Copyright 1997,2000 KOEI`、`VS_VERSION_INFO`、`APPMENU`）。→ **并非"全乱码"**。
- **导入表可静态解析**：4 个 DLL / 9 个 API（见 §2.0）。其中 `KERNEL32` 的 `VirtualProtect/VirtualAlloc/VirtualFree/LoadLibraryA/GetProcAddress` 是**加壳自解压 stub 签名**，印证"节区 0 运行时解压"。
- `FuckALI` 命名是反逆向标记（"Fuck ALI[asing/反汇编]"），典型保护器行为。

**后果**：静态文件里读不到引擎逻辑、菜单文本、事件解释器、场景绘制代码。

**脱壳手册（接手者按此操作）**：

| 步骤 | 工具 | 操作 |
|------|------|------|
| 1 | 备份 | 复制 `TAIK2W95.exe` → `TAIK2W95.exe.bak` |
| 2 | 环境 | Win10/11 + **256 色兼容模式**（社区补丁见 [太阁2 介绍页](http://chiuinan.github.io/game/game/intro/ch/c32/tk2.htm)） |
| 3 | 调试器 | **x32dbg**（32 位）或 OllyDbg；加载 exe，在 `VirtualProtect` / `LoadLibrary` 下断 |
| 4 | 找 OEP | FuckALI 节 `rsize=447488` 为压缩体；跟踪解压 stub，找跳转到 `.text` 的 JMP（常见 pattern：POPAD + 远跳转） |
| 5 | Dump | OEP 处 **Scylla** 或 x64dbg 插件 dump 进程映像 + 重建 IAT |
| 6 | 验证 | 对 dump 跑 `strings`：应出现大量 GBK 菜单/错误提示；搜 `.KOS`、`LS11`、`MESSAGE` |
| 7 | 归档 | 将 dump、IAT 修复日志、OEP RVA 写入本文档 §2.1 |

**已知社区 EXE 补丁**（光碟检查 / 256 色，非脱壳）：

```
TAIK2W95.EXE  75 7A → 90 90  （及其他偏移，见 chiuinan 页面）
```

**GitHub `cool-lab/fuckali`**：与本案 **FuckALI 节名相同但未必同款** packer，勿盲目运行；仅作参考。

**当前静态分析结果（2026-08-24，已升级为 `_probe_exe.py` 自动化基线，详见 §2.0）**：

```
文件大小: 451,584 B
SHA256 : 2a9bac1e1130d5f48d6d1d184e5917d654a4bafe84cf5ad7083b0b90f7ff13eb
节区   : FuckALI#0(rsize0,运行时解压) / FuckALI#1(熵7.92,打包主体) / .rsrc(版本资源+导入表)
导入表 : 4 DLL / 9 API 可静态解析（KERNEL32 组=加壳 stub 签名）
可读串 : 6450 ASCII + UTF-16LE 版本资源（节区1内散落数据文件名引用；非"全乱码"）
EXE 内无 KOS 文件头魔数 ae fc e7 e8 e8
rmKOEI.bin: 独立 24KB PE DLL（卸载程序 textsub.cpp，含 GBK 卸载字符串 + 文件操作 API；**非字体渲染器**，旧定位已证伪，见 `ENGINE_SPEC.md` §7.1）
```

### 2.0 静态探针基线（`_probe_exe.py`，2026-08-24）

`scripts/_probe_exe.py` 用纯标准库解析 PE，产出脱壳前快照 `scripts/_probe_exe_baseline.json`。
脱壳后对其 dump 再跑一次，diff 两份 JSON 即可验证脱壳是否成功（导入表/字符串是否暴露）。

**实测结论：**

| 项目 | 值 |
|------|-----|
| 文件大小 | 451,584 B |
| SHA256 | `2a9bac1e1130d5f48d6d1d184e5917d654a4bafe84cf5ad7083b0b90f7ff13eb`（与 §2.1 一致） |
| PE | PE32 / i386 / GUI 子系统 / ImageBase `0x00400000` / 入口 RVA `0x001311a0` |
| 节区 0 `FuckALI` | vsize 798,720 / vaddr `0x1000` / **rsize 0**（运行时解压目标，无文件体） |
| 节区 1 `FuckALI` | vsize 450,560 / vaddr `0xc4000` / rsize 447,488 / **熵 7.92** ← 打包主体 |
| 节区 2 `.rsrc` | vsize 4,096 / vaddr `0x132000` / rsize 3,072 / 熵 3.44（版本资源 + 导入表物理位置） |

**导入表（4 DLL / 9 API，静态可解析）：**

| DLL | API |
|-----|-----|
| KERNEL32.DLL | LoadLibraryA, GetProcAddress, VirtualProtect, VirtualAlloc, VirtualFree, ExitProcess |
| GDI32.dll | BitBlt |
| USER32.dll | GetDC |
| WINMM.dll | timeGetTime |

> `KERNEL32` 这组 = **加壳 stub 经典签名**（分配内存 → 改保护 → 解析 API → 解压节区 0）。

**可读字符串（节区 1 内 6450 条 ASCII + .rsrc 内 UTF-16LE 版本资源）：**
- 文件名引用片段（引擎加载清单，确认以下均为真数据文件）：
  `v:HBMAP.LZW+` · `bAM/SCENARIO` · `ffKOEILOGO.3Q` · `o_HD.GRP` · `MESSAGE1!` · `KOU2_SAVEFILE)/NEW` · `ime error 6` · `TOWN` · `MAPQ` · `2W95.EXE`
- 版本资源（UTF-16LE）：`Copyright(C) 1997,2000 KOEI CO., LTD.` · `VS_VERSION_INFO` · `APPMENU` · `APPVERSION` · `TAIK2WIN95` · `FileVersion` · `ProductVersion`
- **KOS 文件头魔数 `ae fc e7 e8 e8` 在 EXE 中不存在**（与旧结论一致）→ KOS 由引擎运行时解密，不在 EXE 静态体。

**后续线索引擎：**
- 节区 1 的文件名片段前缀（`v:`/`bAM/`/`ff`/`o_`/`+`/`!`）疑似引擎内部 tag 或经简单变换；完整解码待脱壳后在内存态提取。
- 这些引用已交叉验证数据破解目标（HBMAP.LZW、SCENARIO=SNDATA、MESSAGE1=对话、KOEILOGO、HD.GRP 等均被引擎加载）。

---

### 2.1 EXE 脱壳进度

| 项目 | 状态 | 备注 |
|------|------|------|
| 原始样本 SHA256 | ✅ | `2a9bac1e1130d5f48d6d1d184e5917d654a4bafe84cf5ad7083b0b90f7ff13eb`（探针复核一致） |
| 节区熵（打包量化） | ✅ | 节区 1 熵 **7.92** → 确认压缩/加密主体 |
| 导入表（静态） | ✅ | 4 DLL / 9 API 已解析，见 §2.0（KERNEL32 组 = 加壳 stub 签名） |
| 静态可读字符串 | ✅ | 6450 ASCII + UTF-16LE 版本资源（**推翻"全乱码"旧说**，见 §2.0） |
| KOS 魔数在 EXE 中 | ✅ | 不存在 → KOS 运行时解密，不在静态体 |
| **脱壳方式** | ✅ | **Unicorn 原生执行 stub 静态脱壳**（无需 x32dbg！见 §2.2） |
| **OEP RVA** | ✅ | **`0xf44b0`（VA `0x4f44b0`）** — 反汇编为 MSVC CRT 启动帧，确认真代码 |
| **脱壳 dump** | ✅ | `scripts/_unpacked_mem.bin`（2MB 原始内存映像，基址 0x400000） |
| 脱壳后字符串 | ✅ | **9218** ASCII 串（≫500 目标）；暴露**完整文件清单 89 个 / KOS 39 个** |
| KOS 解释器 RVA | 🔶 | 代码已解压，下一步对 `.KOS` 加载/CreateFile 交叉引用定位 |

---

### 2.2 脱壳成功（2026-08-24，Unicorn 静态模拟）—— 最大阻塞已破

**结论：无需 x32dbg / 无需 Windows，已纯静态把 EXE 解压出来。** 之前文档假设"必须 x32dbg 手工脱壳"，实测发现脱壳 stub 是**自包含 x86 代码**（自定义 LZ77 + 位流，与 LS11 同族），可在 Unicorn 引擎里原生执行，把压缩体解压进内存。

**stub 架构（入口 RVA 0x1311a0，反汇编见 `scripts/_stub_disasm.txt`）：**
1. `PUSHA` → 源 `ESI=0x4c4000`（压缩体）/ 目标 `EDI=0x401000`（ImageBase+0x1000）
2. 位累加器 `EBX`（耗尽时从流重载 32 位，同 LS11）驱动 literal / back-reference 解压
3. 重定位修复：扫描 `E8/E9 + 0x1C` 模式改写相对偏移
4. 手动解析导入表：`LoadLibraryA` / `GetProcAddress` → 写 IAT（槽位 `0x532a28/2c/30/3c`）
5. `mov ebp,[0x532a30]` 取 OEP → `VirtualProtect` → `jmp 0xf44b0`

**脱壳脚本 `scripts/_unpack_exe.py`：**
- 把 PE 按 VA 映射到 `0x400000`，hook 掉 stub 的 4 个 API 调用（返回桩值），`emu_start` 从入口跑到 OEP 自动停。
- 执行 ~1553 万条指令后命中 OEP，dump 内存到 `scripts/_unpacked_mem.bin`。
- 验证：OEP 处反汇编为 MSVC CRT 启动（`push ebp; mov ebp,esp; push -1; push 0x4fcf58; push 0x4f4db8; mov eax,fs:[0]; mov fs:[0],esp`），确系真代码；dump 熵/OEP 后 64KB=5.28 正常代码段。

**解压后暴露的关键情报（均为复刻金矿）：**
- **完整文件清单 89 个**（见 `scripts/_unpacked_filelist.txt`），按 `A:/B:/C:/F:` 前缀分类：
  - `A:` 46 个 = **KOS 音效 39 个**（全到齐：`A:CANCEL.KOS` `A:CLICK.KOS` `A:GIHEI.KOS` `A:GINOUUP.KOS` `A:IATSU.KOS` `A:IDOU.KOS` `A:KAKEI.KOS` `A:KOUGEKI1/2.KOS` `A:NINJA.KOS` `A:NIGERU.KOS` …）
  - `B:` 17 个 = 消息/图形/音乐（`MESSAGE1-4.LZW` `GRPDATA.LZW` `MMLDATA.LZW` `TERRAIN.LZW` `SHOP*`）
  - `C:` 21 个 = 城镇/合战图形（`TOWNMAP/TOWNCHIP/TOWNCHAR.LZW` `HJ*/HK*/HB*MAP/CHAR.LZW` `HJMAPDAT.DAT`）
  - `F:` 4 个 = 二进制表（`BSDATA1/2.TR2` `SNDATA1/2.TR2`）
- **真实导入表**：`MP3.DLL`（音乐）、`DispatchMessageA`/`CreateDIBitmap`/`MultiByteToWideChar`/`LCMapStringA` 等。

**下一步（阶段 2 核心）：**
1. 在 `_unpacked_mem.bin`（IDA/Ghidra 以 0x400000 基址加载）里**定位 KOS 解释器**：交叉引用 `.KOS` 字符串 / `CreateFile`/`ReadFile` 调用点，反汇编 VM 主循环 → 写 `KOS_VM_SPEC.md`。
2. SNDATA 标志语义、合战/单挑规则皆可从这份真代码提取。
3. 可选：把内存映像**重建成合法 PE**（修 PE 头 + 节表）以便静态工具直接打开。

---

## 3. LS11 解压算法（✅ 已破解，100% 验证）

光荣自研 LZ77 变体 + 256 字节频率字典。全部 32 个 `.LZW` 解压长度与原文件声明 100% 吻合。

```
文件结构:
  0x00  "LS11" (4B) + 12 个零
  0x10  字典 256 字节
  0x110 压缩长度  uint32 大端
  0x114 解压长度  uint32 大端
  0x118 数据偏移  uint32 大端 (通常 0x120)
位流解码:
  段1 = 连续读 '1' 直到遇 '0'（该 '0' 也计入段1长度）
  段2 = 紧接着读 段1长度 个比特
  索引 = (1<<段1长度)-2 + 段2值
  索引 < 256  → 输出 dictionary[索引]
  索引 ≥ 256  → 回退: offset = 索引-256, length = 下一索引+3
实现:
  Python:  scripts/real_assets.py  (ls11_decompress)
  Godot:   scripts/TaikouLZW.gd
```

---

## 4. .LZW 文件破解总表（32 个，全部解码成功）

| 文件 | 解压B | 头魔数 | 判定 | 内容 |
|------|------:|--------|------|------|
| `MESSAGE1.LZW` | 63286 | `MSGX` | 文本 | 1735 条系统/帮助文本 |
| `MESSAGE2.LZW` | 63045 | `MSGX` | 文本 | 系统文本 |
| `MESSAGE3.LZW` | 70904 | `MSGX` | 文本 | 系统文本 |
| `MESSAGE4.LZW` | 39383 | `MSGX` | 文本 | 系统文本 |
| `HEXMES.LZW` | 6881 | `MSGX` | 文本 | **283 条战斗文本**（新发现） |
| `TOWNCHIP.LZW` | 43648 | `0b ff..` | 图形 | 341 张 16×16 城镇瓦片 (KOEI 4bpp) |
| `TOWNCHAR.LZW` | 27136 | `ff ff..` | 图形 | 城镇角色精灵 (EGA) |
| `HBCHAR.LZW` | 49152 | `ff ff..` | 图形 | 384 张 16×16 战斗精灵 (EGA) |
| `HBCHAR2.LZW` | 27584 | `ff ff..` | 图形 | 战斗精灵补充 |
| `HJCHAR.LZW` | 38464 | `ff ff..` | 图形 | 合战角色精灵 |
| `HKCHAR.LZW` | 42560 | `ff ff..` | 图形 | 角色精灵 |
| `MAPCHAR.LZW` | 35840 | `ff ff..` | 图形 | 地图角色精灵 |
| `SHOPCHAR.LZW` | 27648 | `ff ff..` | 图形 | 商店角色精灵 |
| `MAPCHIP.LZW` | 45056 | `55 7d..` | 图形 | 88 张 16×16 地形 (裸 RGB565) |
| `FACE.LZW` | 1621 | `40 00..` | 元数据 | 武将肖像 64×80 索引/指针表（像素在别处） |
| `TOWNMAP.LZW` | 1536 | `00 0a..` | **布局** | **48×32 城镇场景瓦片索引图** ✅ |
| `SHOPMAP.LZW` | 1024 | `a6 01..` | **布局** | **32×32 商店室内布局** ✅ |
| `TERRAIN.LZW` | 4096 | `6b 6b..` | 数据 | 64×64 单值(0x6b) 地形/遮罩（含义待定） |
| `HKMAP.LZW` | 52320 | `79 9b..` | 图形 | 合战地图 |
| `HBMAP.LZW` | 17926 | `04 00..` | 图形 | 战斗地图 |
| `HJMAP.LZW` | 46080 | `41 51..` | 图形 | 地图 |
| `HKMAPDAT.LZW` | 1765 | `10 10..` | 数据 | 合战地图数据（与 HKMAPNEW 相同） |
| `HKMAPNEW.LZW` | 1765 | `10 10..` | 数据 | 合战地图数据（副本） |
| `ANMSEQ.LZW` | 31941 | `ANMX` | 动画 | 动画序列表（§5.4） |
| `GRPDATA.LZW` | 40322 | `IDX` | 图形 | **IDX 容器 ✅已破解**：139 条目，每条目 6B 头(type=3,w,h)+3bpp(8色)像素 |
| `GRPDATA2.LZW` | 7128 | `ff ff..` | 图形 | LS11 解压为 `0xFF` 垃圾，**非 IDX 容器**（纠正旧假设） |
| `HGRP.LZW` | 37912 | `IDX` | 图形 | **IDX 容器 ✅已破解**：126 条目，同上格式 |
| `KOSENGRP.LZW` | 41600 | `ff ff..` | 图形 | LS11 解压为 `0xFF` 垃圾，**非 IDX 容器**（纠正旧假设；KOS 实为音效） |
| `SHOP_BG.LZW` | 65152 | `00 00..` | 图形 | 商店背景 |
| `SHOP_OBJ.LZW` | 55552 | `00 00..` | 图形 | 商店物件 |
| `SHOP_MSK.LZW` | 14240 | `ff ff..` | 图形 | 商店遮罩 |
| `PK8DATA.LZW` | 737 | `ac 00..` | 数据 | 小数据表（含义待定） |

---

## 5. 已破解的关键数据结构

### 5.1 文本（GBK，MSGX 容器）
- **解码器**：`"MSGX"` + `uint16 LE` 消息条数 N + `N×uint32 LE` 指针表；消息靠指针界定，`0x00` 终止。
- **字符编码**：字节 `<0x80` → ASCII；字节 `≥0x80` → 大端 2 字节 GBK；`0x00` 终止。
- **`MESSAGE1-4.LZW`**：共 1735+ 条系统/帮助/界面文本。样例：
  `武将的军饷。每月从城池的收入中，按俸禄支付给武将。`
- **`HEXMES.LZW`（新发现）**：283 条**战斗文本**。样例：
  `没有可以移动的场所。` / `%s阵亡！` / `我要死在这里吗┅┅，完了！` / `攻击吗？`

### 5.2 场景布局（⭐ 本会话重大突破）
之前所有画面布局都是手摆猜测；现发现**官方布局图**：
- **`TOWNMAP.LZW`** = 1536 字节 = **48×32 网格**，每格一个 `TOWNCHIP` 瓦片索引（值 0–~32）。
  用真实 TOWNCHIP 瓦片渲染 → `assets/decoded_townmap.png`（768×512）。
  结构：上方 ~21 行是地面/建筑瓦片，接着一条 `4444…` 带（道路/边界），下方为透明背景。
- **`SHOPMAP.LZW`** = 1024 字节 = **32×32 网格**，商店室内布局 → `assets/decoded_shopmap.png`。
- **应用**：复刻城下町/城内/商店画面时，应直接加载这两张布局图，而非程序化生成。

### 5.3 图形瓦片 / 精灵（✅ 已破解，真像素）
- `TOWNCHIP`：341 张 16×16，KOEI 4bpp 位平面交错（TOWNCHIP/HJMAP 等共用解码）。
- `HBCHAR`/`HBCHAR2`/`HJCHAR`/`HKCHAR`/`TOWNCHAR`/`MAPCHAR`/`SHOPCHAR`：
  16×16，EGA 4 平面位图。
- `MAPCHIP`：88 张 16×16，裸 RGB565 地形（世界地图用）。
- `FACE.LZW`：64×80 武将肖像的**元数据/指针表**（1621B）；实际像素在其它 GRP 中，尚未定位。
- `GRP`：`KOEILOGO`/`ACERTWP`/`PRESS` = 6B 头 + RGB565 640×400；
  `SMODE` = 6B 头 + 8bpp + 512B 调色板 + 尾部。
- **`NPKDATA.IDX`（✅ 已完全破解，2026-08-24）**：23 条图像，**全部 4bpp**，
  16 色 LE-16bit RGB444 调色板（@0x10）+ kaodata 风格 4bpp 控制位流像素（@0x30）。
  **推翻此前"部分 8bpp"误判**（那是用垃圾调色板产生的填满假阳性；文件尺寸均不足 8bpp 下限）。
  全部 23 条解码恰好填满原生 `W*H`。完整规范见 **`NPK_SPEC.md`**，解码器 `scripts/_decode_npk.py`。

### 5.4 动画序列（ANMSEQ.LZW）
- 头 `"ANMX"`（41 4e 4d 58），随后 4 字节记录序列：`08 00 VV 08`，`VV` 每次 +8
  （44, 52, 60, 68, 76, 84 …）→ 动画帧对应的精灵偏移表。
- 解压 31941B，约 7985 条记录（含头部），为角色/特效动画帧索引。

### 5.5 字体系统（✅ 2026-08-24 完全破解，3 字体文件，68.4% MESSAGE 覆盖）

**重大发现**：游戏实际使用 **3 个字体文件**，每个覆盖 GBK 范围的不同区段：

| 文件 | 解压大小 | 字形数 | 字节/字形 | GBK 范围 | 用途 |
|------|---------|--------|----------|----------|------|
| `HKCHAR.LZW` | 42560B | 1330 | 32B (1-plane EGA) | **0xB0A1-0xBEAE** | 主字体（战斗外） |
| `HJCHAR.LZW` | 38464B | 1202 | 32B (1-plane EGA) | **0xBEAF-0xCAD7** | 合战字体 |
| `HBCHAR2.LZW` | 27584B | 431 | 64B (2-plane OR) | 自定义名表序 | 姓名/地名专用 |
| `TOWNCHAR.LZW` | 27136B | 848 | 32B | 0xB0A1-0xB3D1 | 城字体（备用设计） |
| `MAPCHAR.LZW` | 35840B | 1120 | 32B | 0xB0A1-0xB4A8 | 地图字体（备用设计） |
| `SHOPCHAR.LZW` | 27648B | 864 | 32B | 0xB0A1-0xB3E0 | 商店字体（备用设计） |

> **🚨 关键纠偏（2026-08-25 推翻 2026-08-24 全部 HKCHAR/HJCHAR/HBCHAR2 "字体" 结论）**：**.LZW `*CHAR` 系列**全部是**精灵（角色头像/战斗小图）**，**不是 CJK 字体**。游戏 CJK 文字由 **Win32 GDI + 系统字体**（脱壳 EXE 导入表 `MultiByteToWideChar`+`LCMapStringA`+`CreateDIBitmap`）实时渲染。

#### 5.5.1 🚨 像素级证据：CHAR 系列 vs 系统字体（scripts/_definit_match.py）

| 文件 | 解压B | 字形数 | glyph 0 vs 假设字符 | 最高 match | 结论 |
|------|-------|--------|---------------------|-----------|------|
| `HKCHAR.LZW` | 42560 | 1330(32B) | 啊(0xB0A1) | **0.381** | ❌ 随机重叠 |
| `HJCHAR.LZW` | 38464 | 1202(32B) | 啊(0xB0A1) | **0.368** | ❌ 随机重叠 |
| `TOWNCHAR.LZW` | 27136 | 848(32B) | 啊(0xB0A1) | **0.350** | ❌ 随机重叠 |
| `MAPCHAR.LZW` | 35840 | 1120(32B) | 啊(0xB0A1) | **0.359** | ❌ 随机重叠 |
| `SHOPCHAR.LZW` | 27648 | 864(32B) | — | — | ❌ 同上 |
| `HBCHAR2.LZW` | 27584 | 431(64B) | 北(名表[0]) | **0.206** | ❌ 随机重叠 |
| `HBCHAR.LZW` | 49152 | 384(128B 4-plane) | — | — | 角色精灵 ✅ |

> 0.2-0.4 match = 16×16 稀疏位图随机重叠。**CJK 正确匹配应 ≥0.85**。
> `HKCHAR`/`HBCHAR2` 前 8 字节均为 `ffffffffffffffff`（顶部实心块），不是 CJK 字符的"北/啊"。

#### 5.5.2 🚨 假阳性来源

`scripts/_probe/font_atlas/hbchar2_64byte_vs_system.png` "前 20 字形与系统字体 100% 匹配" 实为**人眼对比 + 字符名文字标签**（非像素对比）。
像素级对比 16×16 系统字体（simsun.ttc/msyh.ttc）后得分仅 0.2-0.3。
`HKCHAR_gbk_order_test.png` 同理：黄色字形是系统字体覆盖层，白色游戏字形实为密块/随机纹路。

#### 5.5.3 真实 CJK 渲染机制（脱壳 EXE 导入表 + 字符串双重确认 ✅）

EXE 导入表与 `.rdata` 字符串均确认 GDI 文本渲染路径：

- **GDI32.dll** 导入：`CreateFontA` ✅、`TextOutA` ✅、`GetTextMetricsA` ✅、`SetTextColor` ✅、`CreateDIBitmap` ✅、`CreateDIBSection` ✅
- **KERNEL32/GDI 字符串**：`MultiByteToWideChar`、`WideCharToMultiByte`、`LCMapStringW`、`LCMapStringA`
- **文件加载字符串**（注意 `C:`/`B:` 盘符前缀 = 安装盘/CD-ROM，典型 DOS/Win95 资源加载）：
  `C:HBCHAR.LZW` `C:HBCHAR2.LZW` `C:HJCHAR.LZW` `C:HKCHAR.LZW` `C:TOWNCHAR.LZW`
  `B:MAPCHAR.LZW` `B:SHOPCHAR.LZW`（全部是 **C:/B: 盘路径的图形资源**，不是字体文件）

```
GBK 字节流 → MultiByteToWideChar(GBK→Unicode) → LCMapStringA
            → GDI CreateFontA + TextOutA(系统字体 宋体/simsun.ttc) → DIB → BitBlt
```

→ **Godot 复刻不需要提取位图字体，直接加载 CJK 系统字体即可**（msyh.ttc / Noto Sans CJK SC）。
→ **`*CHAR.LZW` 文件 = 角色/地图/商店精灵表**（运行时从 C:/B: 盘加载的位图资源），复刻时按精灵提取，不要当字体用。

#### 5.5.4 `.LZW` CHAR 系列真实身份（按 doc 原分类，全部是角色精灵）

| 文件 | 格式 | 用途 |
|------|------|------|
| `HBCHAR.LZW` | 4-plane EGA 16×16, 384 字形 × 128B | 战斗武将头像/小图 |
| `HBCHAR2.LZW` | 2-plane OR 16×16, 431 字形 × 64B | 战斗精灵补充 |
| `HJCHAR.LZW` | 1-plane 16×16, 1202 字形 × 32B | 合战场景角色/物品精灵 |
| `HKCHAR.LZW` | 1-plane 16×16, 1330 字形 × 32B | 城镇/主菜单角色精灵 |
| `TOWNCHAR.LZW` | 1-plane 16×16, 848 字形 × 32B | 城镇角色精灵 |
| `MAPCHAR.LZW` | 1-plane 16×16, 1120 字形 × 32B | 地图角色精灵 |
| `SHOPCHAR.LZW` | 1-plane 16×16, 864 字形 × 32B | 商店角色精灵 |

> 32B/glyph 的"1-plane 16×16"解码仍适用（这些是单色精灵），但用途是**角色站立图/头像**，不是字形。

#### 5.5.5 🚨 已作废产物（2026-08-24 错误结论）

- `scripts/_probe/font_atlas/HKCHAR_final.png`, `HJCHAR_final.png`, `HBCHAR2_final.png`（所谓"字体图集"实为精灵）
- `scripts/_probe/font_atlas/complete_font_mapping.json`（2653 条假 GBK 映射）
- `scripts/TaikouText.gd`（位图字体渲染类，应删除/改用系统字体）
- `scripts/_build_complete_font.py`, `_build_final_font.py`, `_verify_font_range.py`, `_check_all_fonts.py` 等
- §5.5.1-5.5.3 旧版（68.4% MESSAGE 覆盖）全部作废

#### 5.5.6 Godot 真实字体策略（推荐 ✅）

不再做位图字体提取。Godot 直接加载 CJK 系统字体：

```gdscript
# 项目根目录加载 msyh.ttc 或 Noto Sans CJK SC
var font = FontFile.new()
font.load_dynamic_font("res://fonts/msyh.ttc")
# Godot 4.7 Theme 默认即可渲染中文
```

**优势**：
- 完整覆盖 GBK Level 1+2（21003 字符），不再 68.4%
- 无需逆向 EXE 字体加载代码
- 抗锯齿/缩放由 Godot 自由控制
- 与原版 Win95 GDI 渲染视觉效果接近（同样用系统宋体）

#### 5.5.7 EXE 精灵加载代码（已定位，仅供 CHAR 精灵加载参考）

- **精灵加载器 0x424120**：读取 `C:HBCHAR.LZW`（VA `0x5030e8`）→ LS11 解压 → `0x424320` blit
- **运行时表 0x519868**：370 条目 × 47B（stride 0x2f），dump 中全零（运行时填充）。588 处交叉引用
- **0x443100 = 随机选择器**（非字符查找）：调缓存构建→`rand()%count`→索引 0x51e9c0 表→字形指针→`0x4432e0` 渲染
- **0x4ebd30 = MSVC rand() LCG**：乘数 0x41c64e6d，增量 0x3039
- **0x4ebd60 = `rand() % param`**
- **名称表 0x506ca8**：370 条目 × 9B 静态数据（省名 0-48 + 城名 49-291 + 角色类型 292-369）—— 这是**精灵选择表**（随机遭遇/事件），不是字体映射表



### 5.6 武将 / 剧本 / 城镇数据
- **`BSDATA1/2.TR2`**：700 武将 × 59 字节。名字**明文 GBK**（0–12 字节：姓 + `00` + 名 + `00`），
  其余字节为属性/标志。例：`林` + `通胜`（第一条记录 c1 d6 … cd a8 ca a4）。
- **`SNDATA1/2.TR2`**（40856B，两文件结构相同、数据不同，**非**互为副本；记录区差异 ~96%）✅**结构已破解 + 字段部分映射（2026-08-25 EXE 反汇编权威确认）**：
  - **文件布局**：`[0:16]` ASCII `"TAIKOU2_SCENARIO"` 签名 → `[16:]` **833 条 × 49 字节**记录 → `[40833:40856]` 23 字节尾（场景1=全 `0x0C` / 场景2=全 `0x0A`）。校验 `16 + 833×49 + 23 = 40856` 精确。
  - **记录尺寸 49 经 EXE 双重确认**：加载器 `0x47f394`→`0x47f5b0` 调 `push 0x31`(=49) 读入缓冲 `0x519640`；生成器 `0x4a633e` 用 `mov ebx,0x31` 循环 49 次填 `0x519640`。
  - **加载链（0x47f394）**：读 16B 签名 → 读 2B 头(`esi+0x90`) + 2B 头(`esi+0x94`) → 二者 XOR 校验 → **`push 0x2bc`(=700) 读 700 字节入 `0x519288`**（700 = 武将总数，疑为每武将 1 字节场景状态/存活标志）→ 读 49B/记录入 `0x519640` → 调 `0x47d960`/`0x47df00`/… 解析。
  - **记录存于对象偏移 `0x8e`**（record[0]=obj[0x8e]）。字段解析函数 **`0x47d960`/`0x47d9b0`** 明确读取：
    | record 偏移 | 类型 | 说明 |
    |---|---|---|
    | `[0:2]` | word | 记录头/主 ID（场景1=`4b b8`=0x4bb8，场景2=`13 80`=0x8013） |
    | `[4:6]` | word | 次字段（记录0=`01 01`=0x0101） |
    | `[6]` | byte | 标志位（记录0=`01`） |
    | `[12:14]` | word | 关联字段（记录0=`01 00`=0x0001） |
  - **其余 42 字节**：由 `0x47dba0`(从常量表 `0x5205f0`/`0x521aa8`/`0x520660` 拷默认) + 多条 `0x47dXXX` 子函数解析，散布于对象 `0x10`–`0x18`/`0x3c`–`0x3e` 等派生字段；**完整逐字节语义待更深入反汇编**（Task #23）。
  - **字节 `0x0a`–`0x0d` 呈相同值分布**（主导 `0x0c`≈250、次 `0xf3`≈100、再 `0x0f`≈30）→ 这是**旗标/状态区**（非独立字段），`0x0c`=空/默认、`0xf3`/`0x0f`=特定类型。
  - **记录类型聚类**：~119 条全 `0c0c0c0c`(空槽) + ~50 条 `f3f3f3f3`(类型F3) + 其余为实体数据（记录0–~49 多为旗标块，记录50+ 为变长实体数据）。
  - **生成器 `0x4a633e`**：从源表 `0x5179b8`(stride 14, 370 条目) 循环生成 49B 缓冲，每字节 = `rand()%0x1e+1` 或 `0x1f`（依 `[src+0xd]&3`）；**疑为随机遭遇名显示**（关联 0x443100 随机选择器），非核心场景存档。
- **`TOWNTBL.DAT` / `TOWNPOS.DAT`**：城镇索引表 / 92 城坐标（`uint8(x,y)`，48×37 网格）。
- **`GAIJI.TR2`**（544B）：生僻字 1bpp 字形位图表（`70 76 00 80 00 80 1f fc …`），
  用于渲染标准字体外的罕用汉字。

### 5.7 战斗/合战地图（✅ 2026-08-24 loader 破解 + 结构确认）

| 文件 | 压缩 | 解压 | 类型（已确认） |
|---|---|---|---|
| `HBMAP.LZW` | 123077 | **17926** | 战斗/单挑地图像素（256×70 8bpp 见连续地形），Godot 直接贴图 |
| `HKMAP.LZW` | 28551 | **52320** | 合战地图图形（✅ **8bpp 单图位图**，候选 240×218 / 480×109；**非瓦片集**；→对象 0x524990） |
| `HJMAP.LZW` | 28351 | **46080** | HJ 地图图形（✅ **180 张 ×16×16×8bpp 瓦片集**；→对象 0x524990） |
| `HKCHAR.LZW` | 18038 | **42560** | 合战武将精灵（EGA 4 平面 16×16 已知；条件加载→0x524918/0x524990） |
| `HJCHAR.LZW` | 14038 | **38464** | 武将精灵（✅ 0x436534 分配 0x9640=38464 确证 →0x524918；EGA 4 平面 16×16） |
| `HGRP.LZW` | 23784 | **37912** | 通用图形容器（→对象 0x5249c0；GRP 8 色 3bpp 已知） |
| `HKMAPDAT.LZW` | 65646 | **1765** | 合战小配置（**= HKMAPNEW.LZW**，非 HJMAPDAT 压缩版） |
| `HKMAPNEW.LZW` | 65646 | **1765** | 与 HKMAPDAT.LZW 完全相同（同图新旧版） |
| `HJMAPDAT.DAT` | 裸 | **64600 = 38×1700** | **HJ 数据地图：38 张 × 1700B 记录**（✅结构已破） |
| `HBOBJ.DAT` | 裸 | 5120 | 战斗物体（0x424000 loader，`C:HBOBJ.DAT`@0x503108） |
| `TOWNMAP.LZW` | 36939 | — | 城内地图 |
| `SHOPMAP.LZW` | 34049 | — | 商店地图 |

#### 5.7.1 EXE loader 定位（脱壳内存 `_unpacked_mem.bin`，基址 0x400000）
> **🚨 纠偏（本回合推翻上回合"指针表间接访问"结论）**：字符串 VA 实际比 `.rdata` 偏移 +2（因 `C:` 前缀，如 `C:HJMAPDAT.DAT` 的 VA=0x5036f0、字符串体 `HJMAPDAT.DAT` 在其 +2）。代码用 `push 0x5036f0` **立即数直接引用**，位于 `.text`（0x42391f 等处）。**不存在指针表间接寻址**。

| 资源字符串 | 实际 VA | loader 函数 | 说明 |
|---|---|---|---|
| `C:HBMAP.LZW` | 0x5030d8 | ~0x423917（成员函数 `mov ebp,ecx`=this） | 战斗地图对象构造器；设 0xa2/0xac 等字段；尺寸常量 0x14/0x28/0xa/0x8/0x30/0x40 |
| `C:HBOBJ.DAT` | 0x503108 | ~0x424000 | 战斗物体加载（`0x42402d`/`0x424047` 引用） |
| `C:HKMAP.LZW`+`C:HJMAP.LZW` | 0x5034e0/0x5034c0 | ~0x43385b | 合战地图像素；分配 0x7580(30080)/0x7d00(32000) 缓冲 |
| `C:HJMAPDAT.DAT` | 0x5036f0 | ~0x43a4e1 | **数据地图加载器**（见 5.7.2） |
| `C:HKMAPNEW.LZW` | 0x503700 | ~0x43a580 | 分配 0x6a4(=1700) 缓冲，与 HJMAPDAT 同 record 尺寸 |

统一加载原语 `0x4802e0(this, 4, "C:XXX")` 返回句柄；`0x4411b0(this, size, dstPtr)` 把加载缓冲的 `size` 字节拷入对象成员（A/B/C 三段）。`0x4fb09c`/`0x4fb0a8` 为最终处理/拷贝。

#### 5.7.2 HJMAPDAT.DAT 结构（✅ 已确认，三段全破译）
- **文件 = 64600 B = 38 记录 × 1700 B**（`64600 / 1700 = 38.0` 精确）。
- 每条记录 = **A 头 180 B**（→0x512e58） + **B 地形 760 B**（→0x512868） + **C 部署 760 B**（→0x512b60）；`180+760+760=1700` ✓。
- **网格 stride 确凿**：C/B 缓冲访问码 `arg1 + arg2*40`（`lea eax,[eax+eax*4]`→arg2*5，再 `*8`=arg2*40），配合 B 缓冲 `add edi,0x28`(=40) 行步进 → **40 列**；760/40 = **19 行** → B/C 皆为 **40×19，1 字节/格**。
- **A 头 = 20×9 分类网格**（180 = 20×9）：访问码 `arg1 + arg2*20`（stride 20）→ 20 列 9 行。每格 = `(hi_nibble<<4)|lo_nibble`，`lo_nibble`=分类 0–7；高 4 位访问器 `0x4390c0`(`shr 4`) 证实每格可装**两个** 0–7 分类，但**全部 38 记录高 4 位=0**（仅用低 4 位单分类）。推测为**半分辨率（每 A 格=2×2 战斗格）区域/目标/部署区掩码**。
- **B 地形**：每字节 = `(modifier<<4)|terrain`；`terrain`=低 4 位（0–15，16 类候选地形），`modifier`=高 4 位（高程/旗标，多数=0，复杂图 1–8）。实测每图仅用**子集**（rec0 用 {0,1,2,3,4,5,6,7,13,14,15}）；`5`(草/平原) 主导，`0`(深水)、`13`(墙) `14`(门) `15`(城/设施) 稳定出现。
- **C 部署层 = 40×19 ASCII 字符网格（✅ 本回合破解，推翻"二进制单位ID"旧说）**：每格一个 ASCII 码（255=空占 ~64%；可见字符=单位类型/阵型/标记码）。
  - 解密器 `0x438fa0` 特判 `al∈{'/','1','7','9'}`(0x2f,0x31,0x37,0x39)、`0x438fc0` 特判 `al∈{'+','-','3','5'}`(0x2b,0x2d,0x33,0x35) → 这些是 **ASCII 字面比较**，确证 C 层是**文本编码**而非数值 ID。
  - 实测字符：`I/J/K/H/G/F/A`(兵种码)、`2/3/8/9`(变体/数量)、`<`/`>`(朝向/分界)、`+`/`-`/`=`/`@`/`$`/`%`/`&`/`'`/`(`(阵型/标记)、`?`(未知)。左/右两簇=**两军对垒**阵型。
  - 字符→精灵映射在 `0x512f10`（2 字节/项查表，`0x4390f0` 读取）→ 由 HJMAP/HKMAP 瓦片集渲染。
- **变体选择（0x43a4e1 loader）**：`V = (rand() % T) + T`，难度表 `0x503740`(10 阈值)/`0x503750`(10 值)；第 V 条记录偏移 `= V × 1700` → **难度决定 38 张图中选用哪张**。

#### 5.7.3 渲染产物（可视觉核验，配色为文档分类色，非游戏调色板）
- `scripts/_probe/battle_maps/hjmapdat_terrain_40x19.png` — 38 图地形（低 4 位，16 类分类色）
- `scripts/_probe/battle_maps/hjmapdat_modifier_40x19.png` — 38 图修饰（高 4 位）
- `scripts/_probe/battle_maps/hjmapdat_unit_40x19.png` — 38 图 C 层（**ASCII 码→亮度**，即部署字符网格的结构预览）
- `scripts/_probe/battle_maps/hjmapdat_A_zones_20x9.png` — **38 图 A 头（20×9 分类区，0–7 分类色）**（✅ 本回合新增）
- `scripts/_probe/battle_maps/hjmapdat_record0_explained.png` — **rec0 三栏对照**：B 地形(色) / C 部署(ASCII 叠字) / A 区(20×9)（✅ 本回合新增）
- 分析脚本：`_trace_battlemap_ptrtab.py` / `_disasm_battlemap_loaders.py` / `_disasm_battlemap_linear.py` / `_trace_battlemap_buffers.py` / `_analyze_hjmapdat_records.py` / `_atlas_hjmapdat.py` / `_disasm_unit_buffer.py` / `_disasm_unit_semantics.py` / `_disasm_a_hdr_and_stride8.py` / `_atlas_hjmapdat_final.py`

#### 5.7.4 待办（剩余）
- ✅ **C 层部署语义**：已破（40×19 ASCII 部署字符网格；255=空；解密器 `0x438fa0`/`0x438fc0` 证实 ASCII 字面比较；字符→精灵查表 `0x512f10`）。
- ✅ **A 头语义**：已破（20×9 分类网格，stride 20；每格 0–7 分类；高 4 位访问器 `0x4390c0` 证实可装双分类但当前高 4 位=0）。
- 🚧 **战斗瓦片调色板**：HKMAP/HJMAP 为 8bpp 外置调色板（EXE `.rdata` VA `0x505c00–0x505e00` 含多个 256 色块，最佳对齐 `0x505c8c`；索引 0/255 为透明）。**需肉眼确认配色/朝向**（见 §5.7.6 候选图集）。
- 🚧 **HKCHAR/HJCHAR 尺寸**：42560/38464 均非 16×16 整除（疑 2 平面或非标）；HGRP=37912。
- 🚧 **HBOBJ.DAT**：5120 B（0x424000 loader），结构未破。
- 🚧 **字符→精灵映射表 `0x512f10`**：2 字节/项，需完整转储确认每个 ASCII 码对应的精灵索引（即可从 HJMAP/HKMAP 瓦片集渲染真实部队）。

#### 5.7.5 战斗瓦片图形（HKMAP/HJMAP）结构（✅ 2026-08-25 本回合破解）
> 误判纠正：`0x433780` 是**通用 LZW→对象加载原语**（同时服务 HKMAP/HJMAP/HJCHAR/HKCHAR/HGRP，字符串 `C:HKMAP.LZW`/`C:HJMAP.LZW`/`C:HKCHAR.LZW`/`C:HJCHAR.LZW`/`C:HGRP.LZW` 见 VA 0x5034e0/0x5034c0/0x5034f0/0x5034d0/0x503500）。`0x524978` 仅是 loader 内的**解码暂存缓冲**，真实像素在对象 `0x524990`(HKMAP/HJMAP) / `0x524918`(HJCHAR，0x436534 分配 0x9640=38464 确证) / `0x5249c0`(HGRP)。`0x436xxx` 是**武将单挑精灵绘制**路径（`mov ecx,0x524918` + `call 0x438c60`），非战斗地图瓦片。

**结构（经 `ls11_decompress` 解压 + ASCII 自校验）：**
| 文件 | 解压 | 结构（已确认） |
|---|---|---|
| `HJMAP.LZW` | 46080 | **180 张 × 16×16 × 8bpp 瓦片集**（46080/256=180 整数；distinct=256；ASCII 预览可见清晰精灵轮廓 `@`/`%` 块状占位） |
| `HKMAP.LNK`→`HKMAP.LZW` | 52320 | **单张 8bpp 位图**：因式分解 240×218 / 480×109（W≤480）；**不能整除 16×16**（52320/256=204.375）→ **非瓦片集** |
| `HKCHAR.LZW` | 42560 | 合战武将精灵：332×128B 4 平面（历史结论，本回合 distinct=226） |
| `HJCHAR.LZW` | 38464 | 武将精灵：distinct=191（`38464/256=150.25`、`/128=300.5` → 非 16×16 整除，疑含 2 平面或非标尺寸，待确认） |

**待用户视觉确认：**
- `HKMAP` 位图朝向：**240×218**（接近正方形） vs **480×109**（宽幅横条）——两者皆 52320B，需用户看 `HKMAP_240x218.png` / `HKMAP_480x109.png` 判读。
- `HJMAP` 瓦片语义：180 张 16×16 精灵是地形瓦片 / 单位图标 / 特效帧？需看 `HJMAP_16x16_8bpp_tiles.png`。
- **调色板未知**：上述为灰度结构预览（索引→亮度），真实配色需定位战斗瓦片专用调色板（疑在 NPKDATA 或某 .BIN）。

#### 5.7.5.1 调色板定位（🚧 2026-08-25 进行中）
- **LS11 文件头确认无内嵌调色板**：`LS11` 头 = magic(4) + 0x04–0x10(全0) + **0x10–0x110 256B LZW 字典** + `0x110`=压缩尺寸 + `0x114`=解压尺寸 + `0x118`=数据偏移(288)。解压流 = 纯像素（HJMAP 46080 = 精确 180×256，无调色板余量）→ **调色板必为外部**。
- **索引分布**：`index 0`(11574, 25%) 与 `index 255`(11107, 24%) 占 ~49% → 疑为**透明/空标记**；可见像素用 1–254。
- **候选调色板已定位（EXE .rdata，文件偏移 0x105c00–0x105e00，VA 0x505c00–0x505e00）**：该区含多个 256 色块（distinct=256）。最佳对齐 1024B RGBQUAD 块 **VA 0x505c8c**（reserved₀=229，接近但未达 256 → 疑为 768B RGB 三元组或非 4 对齐布局，待确认）。
- **验证方法（自校验，因无法看图）**：空间相干性度量（正确调色板→平滑精灵；渐变块→相干≈4；乱序块→相干≈230）。全 EXE 扫描 1024/768B 块：渐变块相干过低、乱序块过高，无法单靠指标锁定 → **需用户肉眼确认**。
- **候选图集（交用户判读）**：`HJMAP_palFINAL_0x105c8c.png` / `HJMAP_alt_0x105c80.png` / `HJMAP_alt_0x105d00.png` / `HJMAP_vga.png`（VGA 默认 256 色猜测）；HKMAP 对应 `*_240x218.png` 变体。
- **IAT 限制**：本脱壳 dump 的导入表 RVA=0、虚函数指针（如 `[0x4fb09c]`→0x3000）未重建 → 无法靠代码追踪直接取调色板，改用结构扫描 + 候选渲染。
- 工具脚本：`_trace_hkmap_consumers.py` / `_resolve_finalize.py` / `_scan_dib_palette.py` / `_scan_all_palettes.py` / `_scan_palette_v2.py` / `_find_battle_palette.py` / `_render_palette_candidates.py` / `_render_final_palettes.py`

#### 5.7.6 渲染产物（可视觉核验）
- `scripts/_probe/battle_maps/hjmapdat_terrain_40x19.png` / `_modifier_40x19.png` / `_unit_40x19.png` — 38 图数据地图（✅）
- `scripts/_probe/battle_tiles/HJMAP_16x16_8bpp_tiles.png` — 180 张 16×16 8bpp 瓦片（灰度结构预览）
- `scripts/_probe/battle_tiles/HKMAP_240x218.png` / `HKMAP_480x109.png` — 候选位图朝向
- 分析脚本：`_probe_battle_tiles.py` / `_verify_hjmap_ascii.py` / `_atlas_battle_tiles_final.py` / `_disasm_hkmap_loader.py` / `_disasm_battle_draw.py` / `_disasm_battle_render.py`
- **HKMAP/HJMAP 像素瓦片**：分配 30080/32000，需反汇编 0x43385b 确认瓦片尺寸/调色板 → Godot 贴图。
- HBMAP.LZW 17926B 地形纹理由 Godot 复刻直接贴图即可。

---

## 6. 尚未破解 / 阻塞项

### 6.1 `.KOS` 是音效，不是事件脚本（39 个）—— 2026-08-24 推翻旧假设

**真相（Python 批量验证 39 文件）**：

- 全部 39 个 `.KOS`：`byte[0] = 0xAE`（类型标记），`byte[1:]` 逐字节 **XOR `0xAE`** 后 = 一个**完整且合法的 RIFF/WAVE**。
- 音频参数统一为 **mono / 22050 Hz / 8-bit PCM**（老式音效格式）；`riff` size 字段与文件长度自洽。
- 文件名语义是**战斗/交互音效**：`CANCEL`/`CLICK`/`KOUGEKI1·2`(攻击)/`SEIKOU`(成功)/`SHIPPAI`(失败)/`KAMINARI`(雷)/`KEMURI`(烟)/`NINJA`/`IKARI`(怒)/`KAKEI`…

**为什么之前全错了**：

- 旧 `_build_kos_opcodes.py` 跳过前 20 字节再 XOR，搜 `data` 子串（RIFF 的 data 块），把 **PCM 采样当字节码**扫 uint16 → 纯噪声映射。
- 旧 `TaikouKos.gd` 的 `data` 魔数容器 = RIFF 的 `data` chunk；`0x7D` 集中 = 某音效的高频静默采样值。**没有"脚本""opcode""VM"**。

**影响（必须清理）**：

- `KosVm.gd`、`kos_opcodes.json`、`kos_story_flag_map.json`、`kos_effect_map.json`、`kos_message_map.json`、`_verify_kos_*.gd`（全部 16 个）**基于错误前提，全部作废**，不应再作为规范引用。
- `REPLICATION.md` §3/§7.3 中"KOS 事件/台词/VM"相关描述需重写：城内事件播放的是 **KOS 音效**，台词来自 **MESSAGE*.LZW**（已破解的 GBK 文本），事件触发由 **SNDATA + EXE** 驱动。

**交付物（已落盘）**：`scripts/_decode_kos_wav.py` → `scripts/kos_wav/*.wav`（39 个可播放音效）+ `scripts/kos_wav/_manifest.json`。

### 6.2 EXE 脱壳（FuckALI 保护器）—— ✅ 已完成（2026-08-24，纯静态 Unicorn 模拟）

- **已破**：用 Unicorn 引擎原生执行脱壳 stub（自研 LZ77 + 位流解压，与 LS11 同族）→ 命中 OEP `VA 0x4f44b0` → dump 2MB 解压内存 `_unpacked_mem.bin`。**无需调试器/Windows**。
- **已得**：9218 ASCII 串、完整文件清单 89 个、**KOS 解密密钥 = XOR `0xAE`**（印证 §6.1）、菜单/系统字符串、MP3.DLL 等真实导入表。
- **剩余**：分析解压后的 **EXE 引擎代码**——事件/SNDATA 解释、合战规则、调色板——见 §6.3 与 §7。

### 6.3 其他未映射
- `GRPDATA`/`HGRP`（IDX 容器）✅**已破解**：139 / 126 条目，6B 头(`type=3`,w,h)+3bpp(8色)像素（详见 `ENGINE_SPEC.md` §3，含非图片 ASCII 验证）。`GRPDATA2`/`KOSENGRP` 经 LS11 解压为 `0xFF` 垃圾，**非 IDX 容器**（纠正旧假设）。
- **战斗/合战地图** ✅ **结构破解**（2026-08-24：loader 定位 + HJMAPDAT 38×1700、40×19 网格、16 地形类）→ 详见 §5.7。
- `TERRAIN`（64×64 全 0x6b）含义待定。
- `SNDATA` 字段语义（✅结构已破：16B 签名 + 833×49B 记录 + 23B 尾，反汇编 stride 确认；字段偏移/类型 ⬜ Task #23）。
- `FACE` 肖像像素所在的具体 GRP 文件。

---

## 7. 工作优先级（2026-08-24 修订）

| 阶段 | 优先级 | 动作 | 产出 | 依赖 EXE |
|------|--------|------|------|----------|
| 0 | 🔴 | 统一 `REVERSE_ENGINEERING.md` + `REPLICATION.md` | 交接文档 | 否 |
| 1 | 🔴 | 跑通 52×`_verify_*.gd`，记录失败项 | 回归清单 | 否 |
| 2 | ✅ | **EXE 脱壳**（Unicorn 静态，§2） | `_unpacked_mem.bin` + OEP `0x4f44b0` | 是 |
| 3 | ✅ | KOS 音效解码（XOR 0xAE → RIFF/WAVE） | `scripts/kos_wav/*.wav`（39 个） | 否 |
| 3b | ✅ | 分析解压后 EXE 引擎：事件/SNDATA 解释、合战规则、调色板 | `ENGINE_SPEC.md`（✅已建，2026-08-24） | 是 |
| 4 | 🔴 | **字体加载器逆向**：反汇编 `0x424120` + Unicorn 实跑 dump `0x519868` → GBK→字形索引映射 | 字形码表 | 是 |
| 5 | 🔴 | 用字形映射解码 SNDATA 字段 → 场景/武将名/事件文本 | `sndata_decoded.json` | 是 |
| 6 | ✅ | HJMAPDAT 合战数据地图结构（38×1700、40×19、16 地形） | §5.7 + 3 张预览 PNG | 是 |
| 7 | 🟡 | 用 TOWNMAP/SHOPMAP 替换 Godot 城内手摆布局 | 场景 PR | 否 |
| 8 | 🟢 | Godot 玩法扩展（合战/多结局） | — | **等字体+ SNDATA 解码** |

**暂停或降级的 Godot 工作**（直到阶段 3 有 VM 文档）：

- 继续堆 `KosVm.gd` 启发式 opcode
- 硬编码剧情分支（应改 SNDATA 驱动）
- 合战系统实现

---

## 8. 工具与产物

- `scripts/real_assets.py` —— Python 解码库（LSLA 解压 + 位平面 + 调色板 + 精灵导出）
- `scripts/TaikouLZW.gd` / `TaikouImage.gd` / `GameAssets.gd` —— Godot 端已接好的真素材管道
- `assets/decoded_townmap.png` —— 真实城镇场景布局（TOWNCHIP 瓦片）
- `assets/decoded_shopmap.png` —— 真实商店室内布局
- `assets/sprites/` —— 384 帧真实 HBCHAR 精灵（透明 PNG）
- `assets/castle_town_real.png` 等 —— 此前用真瓦片拼的预览

> 最后更新：**2026-08-24**（策略修订：EXE 优先路径 + KOS 纠偏）  
> 配套复刻进度见同目录 **`REPLICATION.md`**（Godot Demo / 接手清单）。
