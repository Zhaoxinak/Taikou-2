# modkit — 太阁立志传2（Win95）资源 MOD 工具

把 LS11 容器**解开、改内容、再装回去**的完整链路。已通过 66/66 round-trip 自检
与游戏本体实机加载验证。

## 快速开始

```bash
cd "F:\Games\Taikou 2"

python modkit/cli.py info FACE              # 看容器结构
python modkit/cli.py unpack-all             # 全部解包 -> modkit/work/<NAME>/seg_*.bin
python modkit/cli.py unpack MESSAGE1        # 只解单个

# 拿编辑器改 modkit/work/<NAME>/seg_*.bin（务必保持文件字节数不变！）

python modkit/cli.py repack MESSAGE1        # 装回 -> modkit/output/MESSAGE1.LZW
python modkit/selftest.py                   # 随时自检：应 66 通过 / 0 失败
```

改文本的现成例子：

```bash
python modkit/demo_edit_text.py             # 改一条游戏文案并回读验证
```

产物**永远落在 `modkit/output/`**，不会动 `Taikou2 Original/` 里的原版。
要装进游戏时自行复制过去，**记得先备份原文件**。

## 核心约束：等长替换

段（`seg_*.bin`）的字节数必须与原来一致，`repack` 会拦截长度变化。

原因是 TOC 里记着每段的解压长度、LS11 header 里记着段长，游戏据此分配缓冲区。
**放宽长度限制需要先确认游戏端不会越界读**，现阶段一律等长最稳。
文本类（`MSGX`）只要 GBK 编码后字数相同即可等长替换，很好满足。

## LS11 容器规格（实测）

```
0x000  4B   "LS11"
0x010  256B 字典：dictionary[idx] = 字节值（256 元双射，反查唯一）
0x110  u32BE  span(段0)        第 1 段压缩后字节数
0x114  u32BE  dec_len(段0)     第 1 段解压后字节数
0x118  u32BE  data_offset      bit 流起点（0x120 / 0x12c / 0x2400 ... 因文件而异）
0x11c  u32BE  span(段1)
0x120  TOC：每条 12 字节 = [u32BE dec_len, u32BE start_offset, u32BE span(下一段)]
       段总数 = 1 + TOC 记录数
       TOC[i] 描述第 i+2 段；第三条字段是再下一段的压缩长度（由实测反推）
```

**每段独立 pad 到整字节**（实测 pad 恒为 0/2/4/6 bit），各段可独立重压缩。

⚠️ 别信"整文件是一条连续 bit 流"—— 早期这么猜过，凑巧能对上一段就误导了结论。
真正的判据是 TOC 里明明白白记着每段的**字节**偏移。

### 索引编码 = Elias gamma(n+2)

```
编码 index n：令 x = n+2, K = floor(log2(x))
   输出 (K-1) 个 1、一个 0、再 K 位的 (x - 2^K)
解码逆向：数连续 1 得 k，吞掉 0，再读 (k+1) 位
   index = (1 << (k+1)) - 2 + payload
```

### token 语义

| index | 含义 |
|---|---|
| `< 256` | 字面量，`dictionary[index]` |
| `>= 256` | 匹配：`back = index - 256`，长度 = 紧跟的下一个 index + 3 |

复制是逐字节 `out[pos] = out[pos - back]`，**允许重叠**（标准 LZ77）。

### 必须恪守的原版边界（全局实测极值）

| 项 | 上限 |
|---|---|
| 字面量 index | 255 |
| back（回退距离） | **8191** = 2^13-1 |
| copy_len | **512** |

越界会让原版解码器行为不确定。

## MSGX 文本容器（LS11 解压后的二级容器）

```
0x00  4B  "MSGX"
0x04  u16LE count
0x06  count × u32LE offsets      每条文本的绝对偏移
...   GBK 明文（无 XOR、无压缩）
```

`MESSAGE1.LZW` 内含 1735 条，例：

```
[0]     武将的军饷。每月从城池的收入中，按俸禄支付给武将。
[1]     武将的体力。左边为现在值，右边为最大值。……
[1700]  您就是赫赫有名的%s大人呀。在下是%s，今后多多指教。
```

注意 `%s` 是运行时占位符，替换时要保留。

## 资源对照（部分）

| 容器 | 段数 | 内容 |
|---|---|---|
| `FACE.LZW` | **745** | 武将头像（每段 ~1.5KB，头 4 字节 `40 00 50 00`）|
| `TERRAIN.LZW` | 100 | 地形，每段 4096B |
| `SHOPMAP.LZW` | 138 | 商店地图 |
| `SHOPCHAR.LZW` | 111 | 商店角色图 |
| `HKMAPDAT / HKMAPNEW` | 84 | 合战地图数据 |
| `TOWNMAP.LZW` | 49 | **49 国**地图，每段 1536B |
| `PK8DATA.LZW` | 43 | — |
| `KOSENGRP.LZW` | 22 | 合战背景图 |
| `HBMAP.LZW` | 14 | — |
| `MESSAGE1-4`, `HEXMES` | 1 | `MSGX` 文本 |
| `GRPDATA`, `MAPCHIP`, `TOWNCHIP`, `*_CHAR` … | 1 | 单体图形/音乐素材 |

## 已知缺口

- **TOC 每条记录的第 3 个字段**含义是反推的（= 下一段压缩长度），尚未在原版
  汇编里取得直接证据。目前按此重建能过自检 + 实机，但留意。
- 二次压缩后体积普遍增大 5%~25%（原版压缩器更优；高冗余数据如 `FACE` 只 +0.24%）。
  实机已确认**体积变化不影响加载**，但务必保持原版备份。
- 图片段内部的像素编码（`real_assets.py` 里的 `decode_indexed_sheet` /
  `decode_koei4bpp_tile` / `decode_ega_planar_tile`）只做了**解码**，
  对应的编码器还没写。改图片需要先补这几个反向函数。
