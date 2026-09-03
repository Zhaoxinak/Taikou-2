# 太阁立志传2 逆向工程 — AI 交接文档（Handoff）

> 给下一个接手 AI 的完整上下文。读完本文件即可独立上手，无需本会话历史。
> 最后更新：2026-09-03（BREAKTHROUGHS 顶部 = 续243，套件 166 ref 全 PASS）。

---

## 0. 一句话定性

这是对光荣老游戏 **太阁立志传2（TAIK2W95，Windows 95 版）** 的逆向工程：目标是抽取出源码级引擎重实现（Godot 4 复刻）所需的**数据格式 + 数值玩法公式**，并落成规格文档。

**当前策略（2026-08-25 起铁律）**：停 UI / 像素 / 字体，只做 **数值 + 玩法**。
**法律边界**：用户自有合法拷贝、仅本地单机；仓库**不打包**原版素材（原版文件在 `Taikou2 Original/`，已 gitignore）。

---

## 1. 当前状态（最重要）

- **静态/结构层已 100% 收口**：全部非图像原始文件均已破解且经运行期验证。自测套件 `scripts/_run_all_selfchecks.py` = **166 个 `*_ref.py` 全 PASS / 0 FAIL**。
  - ⚠️ 套件计数按 **ref 文件数**（166），不是断言数（断言总数有几千）。别看到「PASS=166」以外的数字就以为有回归。
- **仅剩「emu 运行期增强」项**（全是数值/数据，**非逻辑缺口**，不阻塞复刻）。见 §6。
- 图像类（GRP 5 文件 RGB565、PK8 颜图、纯像素 LZW）**用户 2026-08-25 明令豁免** → 保持不动，不要碰。

---

## 2. 文档权威链（照这个顺序读，勿乱跳）

| 顺序 | 文件 | 用途 |
|------|------|------|
| 1 | `README.md` | 入口 / 目录约定 / 常用命令 |
| 2 | `BREAKTHROUGHS.md` | **突破时间线（倒序，新在上）**；每个新结论先写这里（四段式） |
| 3 | `GAME_DATA_SPEC.md` | **数值/玩法权威规格**（复刻照此实现） |
| 4 | `BATTLE_SPEC.md` | 合战专篇（HJMAPDAT / per-tick 伤害 / 计略） |
| 5 | `SNDATA_SPEC.md` | SNDATA/SAVEDATA 容器与 XOR 流 / 段地图 |
| 6 | `NPK_SPEC.md` | NPK 图像格式（格式已闭，UI 暂停） |
| — | `.workbuddy/memory/MEMORY.md` | **会话索引 + 方法论硬规则 + 关键几何速查**（本文件摘自此） |
| — | `docs/archive/` | 历史过时文档，**勿当权威** |

> 每个 `scripts/*_ref.py` 是对应结论的**可复跑参考实现**（自测）。文档声称的结论都有对应的 ref 兜底。

---

## 3. 接手第一步（必做顺序）

```bash
cd "F:\Games\Taikou 2"

# 1) 取当前最大「续」编号，新条目用 max+1 防撞号（并行会话曾撞号+整份覆盖）
grep -o '上一条（续[0-9]*）' BREAKTHROUGHS.md | grep -o '[0-9]*' | sort -n | tail -1

# 2) 全量自测回归，确认 166/0 无回归
C:/Users/Administrator/AppData/Local/Programs/Python/Python312/python.exe scripts/_run_all_selfchecks.py
```

再读 `.workbuddy/memory/MEMORY.md` 的「逆向方法论」和「残留敞口」两节。

---

## 4. 逆向方法论（核心坑 · 去重 · 可复用）

- **映像**：`scripts/_unpacked_mem.bin`（2MB，base `0x400000`，平坦映射 `off = va - 0x400000`，OEP `0x4f44b0`）。
  - 反汇编用 **capstone**（`skipdata=True`）；动态仿真用 **Unicorn**（`mu.reg_write/read(UC_X86_REG_ESP)`，stdcall 钩子须 `esp += 4*nargs`）。
- **🔑 定 stride 三证据**：lea 系数 / 乘减序列 / 除法魔数（÷10=`0x66666667`+sar2、÷12=`0x2aaaaaab`+sar1、÷14=`0x92492493`+sar3、÷31=`0x84210843`+sar4、÷47=`0xae4c415d`、÷30=`0x88888889`+sar4）。
- **🔴 多 struct 陷阱**：「位移命中」≠「字段命中」（必须溯源基址寄存器）；「静态抓不到写入」常因 setter 按 `ecx=base+N` 参数化传入。
- **🔴 共享方法库陷阱**：`0x49b960..0x49bda8` 是通用 setter 库；偏移落进该区 ≠ 属某 struct，须绝对 xref + 确认真实 `this` + 读写方向。
- **🔑 抽 call 实参**不能从单一固定起点反汇编（x86 变长指令必错位）。正解 = 枚举回溯起点，只接受「指令流中存在 `address==call_va`」的起点（边界对齐）。
- **🔑 函数边界**用「最大 call/jmp 目标 ≤ va」，别用 `push ebp;mov ebp,esp` prologue（本 EXE 大量 FPO 函数无标准 prologue）。
- **🔴 emu 读内存 ≠ 读静态镜像**：栈/局部缓冲在静态 bin 里是垃圾，校验回调实参里的字符串必须 `mu.mem_read()`。Unicorn 有 TB 缓存，改桩行为必须新建 `Uc` 实例。
- **🔑 同调用链可并存三种约定**（`play_sfx` 1 栈参 / thiscall 无栈参 / cdecl 3 参 / stdcall 3 参 callee 清栈），桩写错任一即栈崩。

---

## 5. 关键几何速查（地址→含义）

| 结构 | 地址/几何 | 关键点 |
|------|-----------|--------|
| 武将实体 | `0x519868`，370×47B | 五维 `+0x0a..+0x0e`、技能 `+0x0f..+0x11`、国索引 `+0x24`、在城 `+0x25`、主君 `word+0x2a`(0xffff=浪人)、相性 `+0x08` 字 bit11-14、**+0x20=最大体力/+0x21=现在体力** |
| 城表 | `0x51eb88`，31B×200 | |
| 国情表 | `0x519548`，stride5×49 | |
| 国政治表 | `0x5179b8`，stride14×49 | `byte[0xc]`=外交等级（低4位 level+高4位 quality） |
| S7 每城表 | `0x516a28`，200×16B | `+0x0f` 位域（低4位=flags setter `0x49bf50` / 高3位=0x70 类别 setter `0x49bf90`） |
| S15 事件旗 | `0x5203c0`，25B | |
| 名称总表 | `0x506ca8`，stride9 | |
| 技能名表 | `0x507b58`，stride5×10 | id 顺序=口才,马术,算术,剑术,忍术,兵法,洋枪,筑城,礼法,茶道 |
| 店铺主人格记录表 | `0x517850`，30×12B | `+0x07`=店主好感、`+0x08`=设施状态 word、`+0x0a`=进度计数、`+0x0b`=事件旗位域；全局当前店主指针 `[0x52063c]` |

**通用原语族**（饱和算术 + setter 库）：
- 饱和算术：`0x4ebca0`=`sat_add(a,b,cap)`；`0x4ebcd0`=`sat_sub(a,b)`。
- 技能写器族：`0x4a3040 + k*0x20`（k=0..9=技能 id）= cap-3 递增器，thiscall `ecx=实体+0x0f`，对 `byte[ecx+k>>2]` 的 `(k&3)*2` 位 +1 封顶 3。全镜像调用点 19 处。
- 店主好感 setter 三件套：`0x49bfb0`(直写 byte[ecx+7]) / `0x4a3630`(sat_add cap 0x64) / `0x44e560`(sat_sub floor 1)。
- 记录字段 setter：`0x49bfc0`(word[ecx+8]) / `0x49bfd0`(byte[ecx+0xa]) / `0x49bfe0`(byte[ecx+0xb])，均 ret 4。

**格式类**（续195–202 已闭）：KOS=1字节XOR密钥+标准WAV；TR2 四类 SAVEDATA/SCENARIO/BSDATA/GAIJI（头 +0x10 4B = 校验和 + XOR 密钥种子）；GAIJI=16×34B 外字。

---

## 6. 残留敞口（下一步可做的活）

> 全部是**数值/数据层**的 emu 运行期增强，**非逻辑缺口**。复刻不依赖它们。想做就从这里挑：

1. **`0x518588` 20×5×5 word 矩阵逐格值**：结构已闭 + 文件级占位 0xFF 坐实；值由写回器 `0x4a0ff0/0x4a1010/0x4a1030` 运行期填，须 emu 钩取。
2. **`0x462fd0` typekey map 6 项二分键值**：键数组 `[esp+0x2c]` 运行期填，emu 跑 SNDATA 加载 `0x5152d0` 可查。
3. **BSDATA 尾 5 字节 `stream 0x28..0x2c` 精确玩法语义**：统计特征化已闭（续235），须 MSGX/emu 交叉坐死。
4. **店铺记录 `+0x00..+0x06` 名前精确语义** + 买药 `0x44e350` 内 ÷50 魔数语义 + slot3/4/10 内部 msg 值（续243 遗留）。
5. **S15 段C bit1 静默事件 MSG 外置路径**；segC[3]=`0x513550` 战斗单位池运行期索引值（续227）。
6. 小项：`byte[ent+0x24]`/`0x517aa5` bonus 语义、S6/S7 关系、4 处寄存器派生站点、9 音效 ID 中 15(ZANSYU)/36(MATISIRO) 语义中置信、15 外字中 10 身份未认。

> 若要转**复刻工程**（把 GAME_DATA_SPEC 变成 Godot 代码），另起炉灶即可，逆向数据层已够用。

---

## 7. 本机环境 + git push（Windows）

- **Python**：系统 Python 3.12 `C:/Users/Administrator/AppData/Local/Programs/Python/Python312/python.exe`（capstone 5.0.7 已装）。**无 mac python3.7、无 managed venv**（旧路径记忆失效，别信）。
- **git push 卡死坑（重要）**：默认 schannel 后端在 push 的 `git-receive-pack` 认证阶段卡「remote party requests renegotiation」无限挂起（`ls-remote`/`curl` 都正常，唯 push 挂）。**正解**：
  ```bash
  git -c http.sslBackend=openssl -c http.proxy=http://127.0.0.1:7890 push origin main
  ```
  - 代理端口会变（历史 13573→4759→…），先用 `git -c http.sslBackend=openssl -c http.proxy=http://127.0.0.1:7890 ls-remote origin HEAD` 探活。
  - env 里的 `11122` 是 App 内网代理，git 走它报 TLS handshake 失败，**别用**。
  - 诊断顺序：`ls-remote` 探代理 → 挂则 `GIT_CURL_VERBOSE=1` 看「renegotiation」→ 切 openssl。

---

## 8. 硬规则（违者会被打回重做）

1. **突破/推翻旧假设 → 立即插 `BREAKTHROUGHS.md` 倒序条目**，四段式：**突破 / 证据 / 仍未知 / 下一步**。新条目编号 = 当前 max 续 + 1（§3 第 1 步先取 max）。
2. **每个结论配一个 `scripts/*_ref.py` 自测**（capstone 字节/反汇编断言），跑过 ALL PASS 才算数。
3. **收尾固定流程**：ref PASS → 文档回填（BREAKTHROUGHS + GAME_DATA_SPEC/BATTLE_SPEC/SNDATA_SPEC + 破解状态清单 §9）→ 全量套件回归 166/0 → `git checkout --` 还原被套件再生的文件（`scripts/_gaiji_preview.png`、`scripts/sndata_wordarray_payload.json`）→ commit + push（openssl 后端）。
4. **图像豁免档不动**（GRP/PK8/纯像素 LZW）。
5. **临时探针**命名 `_*.py` / `_swc_*`，**不入库**（gitignore/不 add）。
6. 并行会话可能同时改文档 → **动手前先 grep 取 max 续编号**；撞号≠错误（两轨独立收敛同结论=交叉验证）。

---

## 9. 最近几次突破（时间线尾部快照）

- **续243**（2026-09-03）：店铺设施流公式全拆 —— slot7=画师（袄绘依頼 30 门/80 贯/`+0x0a`=20+rand(41)/`+0x08`=1 制作中）+ 医师五流（就诊亲密度/免费判定 rand(100)<好感−10/诊金公式 gap×(100−亲密度)×身分/100÷10×10 min10/穷人流 cap3/买药药罐 `word[S6+0x26]>>12`）+ 教会（义工 `+0x0b` bit1/0 首回标记+魅力受益/大名情报费 5−捐/20 捐100免费/介绍信 0x1211）+ 南蛮（陌生人门 `+0x07`==0/问候 sbb/洋枪 15−好感/30）+ **字段语义归位**（`+0x08`=设施状态 word/`+0x0a`=进度计数/`+0x0b`=事件旗位域）。ref `shop_facility_flows_ref.py` 41/41。
- **续242**：店铺主人格记录表 `0x517850` 30×12B 闭合 + 入店分发器 `0x44e710` + **纠偏 `+0x07`=店主好感（非「商人资本」）** + 闇商人 #29 事件流 + `0x44e110`=通用持有物选择对话框。ref `shop_npc_record_ref.py` 80/80。
- **续239/240/241**：武将技能读·写·消费三侧闭合（读=散布内联 2-bit 提取、写=cap-3 递增器族 `0x4a3040+k*0x20`、消费=13 站点完整事件表）。
- 更早完整时间线见 `BREAKTHROUGHS.md`。

---

## 10. 给接手 AI 的建议开场

接手后先做一件小事验证流程走通（不直接啃大敞口）：挑 §6 里任一小项，用 capstone 反汇编 + 写一个 3~5 断言的 `*_ref.py`，跑套件确认 166→167 全 PASS，再插 BREAKTHROUGHS 续244 条目并 push。流程顺了再上大项。
