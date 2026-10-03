"""LS11 读写核心 —— 光荣自研 LZ77 变体 + 256 字节频率字典。

容器布局（实测，33 个文件全通过）：
    0x000  4B  "LS11"
    0x010  256B  字典：dictionary[idx] = 实际字节（**256 元双射**，反查唯一）
    0x110  u32BE compressed_size    第一段 bit 流字节数
    0x114  u32BE decompressed_size  每段的解压长度
    0x118  u32BE data_offset        bit 流起点（不同文件可变：0x120 / 0x2c4 / 0x2400 ...）
    ...    data_offset 起：连续 bit 流

关键结构：**一个文件 = 一条连续 bit 流，里面串了 N 段**。
段之间**不留 padding 比特**，第 k 段紧接着第 k-1 段用掉的 bit 继续。
第一段恰好占 ceil(bits/8) == compressed_size 字节（TERRAIN 实测 12054 bit → 1507 B）。

索引采用 Elias gamma(n+2)：先 k 个 1、再一个 0、再 (k+1) 位有效载荷，
    index = (1 << (k+1)) - 2 + payload
反向即 k = floor(log2(index+2)) - 1。

语义：
    idx < 256        → 字面量 dictionary[idx]
    idx >= 256       → 匹配：back = idx-256，长度 = 下一个 index + 3
                       逐字节 out[pos] = out[pos-back]，允许重叠复制（LZ77）

压缩器必须恪守原版边界（实测全局极值）：
    字面量 idx <= 255 / back <= 8191 / copy_len <= 512
超出会让原版解码器行为不确定，务必别越界。
"""

MAX_BACK = 8191
MAX_LEN = 512
MIN_MATCH = 3


def _u32be(d, off):
    return (d[off] << 24) | (d[off + 1] << 16) | (d[off + 2] << 8) | d[off + 3]


def _put_u32be(buf, off, val):
    buf[off] = (val >> 24) & 0xFF
    buf[off + 1] = (val >> 16) & 0xFF
    buf[off + 2] = (val >> 8) & 0xFF
    buf[off + 3] = val & 0xFF


class BitReader:
    def __init__(self, data, bit_pos=0):
        self.d = data
        self.pos = bit_pos
        self.limit = len(data) * 8

    def bit(self):
        if self.pos >= self.limit:
            raise EOFError
        b = (self.d[self.pos >> 3] >> (7 - (self.pos & 7))) & 1
        self.pos += 1
        return b

    def eof(self):
        return self.pos >= self.limit

    def next_index(self):
        """读一个 gamma(n+2) 编码的索引。"""
        k = 0
        while self.bit() == 1:
            k += 1
        K = k + 1
        v = 0
        for _ in range(K):
            v = (v << 1) | self.bit()
        return ((1 << K) - 2) + v, self.pos


class BitWriter:
    def __init__(self):
        self.bits = bytearray()

    def put_bit(self, b):
        self.bits.append(b)

    def put_index(self, n):
        """写 gamma(n+2)：k 个 1 + 一个 0 + (k+1) 位载荷。"""
        if n < 0:
            raise ValueError("index must be non-negative")
        x = n + 2
        K = x.bit_length() - 1          # floor(log2(x))
        for _ in range(K - 1):
            self.bits.append(1)
        self.bits.append(0)
        v = x - (1 << K)
        for i in range(K - 1, -1, -1):
            self.bits.append((v >> i) & 1)

    def to_bytes(self):
        out = bytearray((len(self.bits) + 7) // 8)
        for i, b in enumerate(self.bits):
            if b:
                out[i >> 3] |= 0x80 >> (i & 7)
        return bytes(out)

    def __len__(self):
        return len(self.bits)


# --------------------------------------------------------------------------
# 解压
# --------------------------------------------------------------------------

def decompress_block(br, dictionary, want_len):
    """从当前 bit 位置解出一段。返回 (数据, 用掉的 bit 数)。"""
    out = bytearray(want_len)
    pos = 0
    start = br.pos
    try:
        while pos < want_len:
            idx, _ = br.next_index()
            if idx < 256:
                out[pos] = dictionary[idx]
                pos += 1
            else:
                back = idx - 256
                lenidx, _ = br.next_index()
                length = lenidx + 3
                for _ in range(length):
                    if pos >= want_len:
                        break
                    src = pos - back
                    out[pos] = out[src] if src >= 0 else 0
                    pos += 1
    except EOFError:
        pass
    return bytes(out[:pos]), br.pos - start


# --------------------------------------------------------------------------
# 压缩
# --------------------------------------------------------------------------

def build_reverse_dict(dictionary):
    """字节 -> 索引。字典是双射，反查唯一。"""
    rev = {}
    for i, b in enumerate(dictionary):
        rev[b] = i
    if len(rev) != 256:
        raise ValueError("字典非 256 元双射，无法安全编码")
    return rev


def compress_block(data, rev_dict, max_back=MAX_BACK, max_len=MAX_LEN):
    """贪心 LZ77。返回 BitWriter（bit 精确，段间拼接由调用方负责）。"""
    bw = BitWriter()
    n = len(data)
    head = {}                      # 3 字节前缀 -> 最近位置
    pos = 0
    while pos < n:
        best_len, best_back = 0, 0
        lo = max(0, pos - max_back)
        key = bytes(data[pos:pos + MIN_MATCH])
        cand = head.get(key)
        if cand is not None and cand >= lo:
            start = cand
            maxchk = min(max_len, n - pos)
            l = 0
            while l < maxchk and data[start + l] == data[pos + l]:
                l += 1
            if l >= MIN_MATCH:
                best_len, best_back = l, pos - start
        # 推进 head（只记最近一次，够用且与贪心一致）
        if pos + MIN_MATCH <= n:
            head[key] = pos
        if best_len >= MIN_MATCH:
            bw.put_index(best_back + 256)
            bw.put_index(best_len - MIN_MATCH)
            # 把跨过的中间位置也登记，提升后续命中率
            for m in range(pos + 1, min(pos + best_len, n - MIN_MATCH + 1)):
                head[bytes(data[m:m + MIN_MATCH])] = m
            pos += best_len
        else:
            bw.put_index(rev_dict[data[pos]])
            pos += 1
    return bw


# --------------------------------------------------------------------------
# 容器层
# --------------------------------------------------------------------------

class LS11File:
    def __init__(self, raw: bytes):
        if raw[0:4] != b"LS11":
            raise ValueError("不是 LS11 容器")
        self.raw = raw
        self.dictionary = raw[0x10:0x110]
        self.compressed_size = _u32be(raw, 0x110)
        self.decompressed_size = _u32be(raw, 0x114)
        self.data_offset = _u32be(raw, 0x118)
        self.rev_dict = build_reverse_dict(self.dictionary)
        # TOC：0x120 起每条 12 字节 = [u32BE 解压长度, u32BE 起始偏移, u32BE 未明]
        # 段总数 = 1 + TOC 记录数；第 1 段由 header 描述，第 i>=2 段由 TOC[i-2] 描述。
        toc_size = self.data_offset - 0x120
        assert toc_size >= 0 and toc_size % 12 == 0, f"TOC 尺寸异常 {toc_size}"
        self.toc_records = []
        for i in range(toc_size // 12):
            o = 0x120 + i * 12
            self.toc_records.append((_u32be(raw, o), _u32be(raw, o + 4), _u32be(raw, o + 8)))
        self.segments = []
        self._load()

    def segment_sizes(self):
        """每段的解压长度：第 1 段取 header，其余取 TOC。"""
        sizes = [self.decompressed_size]
        sizes.extend(r[0] for r in self.toc_records)
        return sizes

    def segment_offsets(self):
        """每段 bit 流起始的**字节**偏移（相对文件开头）。"""
        offs = [self.data_offset]
        offs.extend(r[1] for r in self.toc_records)
        return offs

    @property
    def stream(self):
        return self.raw[self.data_offset:]

    @property
    def head_bytes(self):
        return self.raw[:self.data_offset]

    def _load(self):
        """逐段解压。

        实测结论：**每段独立字节对齐** —— 每段各自压缩后 pad 到整字节
        （实测 pad 恒为 0/2/4/6 bit），TOC 里记的就是各段起始的字节偏移。
        曾经误判为"整文件一条连续 bit 流"，是幸存者偏差，勿回到那个假设。
        """
        self.segments = []
        self.seg_bits = []
        for want, off in zip(self.segment_sizes(), self.segment_offsets()):
            br = BitReader(self.raw, off * 8)
            seg, used = decompress_block(br, self.dictionary, want)
            self.segments.append(seg)
            self.seg_bits.append(used)

    def repack(self) -> bytes:
        """按当前 segments 重压缩。

        逐段独立压缩 -> 各自 pad 到字节 -> 依次拼接，然后重建 TOC 与 header：
            header[0x110] = span(段0)
            header[0x114] = dec_len(段0)
            header[0x118] = data_offset（header 长度，不变）
            header[0x11c] = span(段1)
            TOC[i]        = [dec_len(段i+1), off(段i+1), span(段i+2)]
        TOC 第三字段的含义由实测反推（= 下一段压缩后字节数），照此重建即可。
        """
        sizes = self.segment_sizes()
        if len(self.segments) != len(sizes):
            raise ValueError(f"段数必须保持 {len(sizes)}，收到 {len(self.segments)}")
        bodies, spans = [], []
        for seg, want in zip(self.segments, sizes):
            if len(seg) != want:
                raise ValueError(f"段长度必须保持 {want}，收到 {len(seg)}"
                                 f"（改动请保持等长替换）")
            body = compress_block(seg, self.rev_dict).to_bytes()
            bodies.append(body)
            spans.append(len(body))

        data_offset = self.data_offset
        offs = [data_offset]
        for s in spans[:-1]:
            offs.append(offs[-1] + s)

        head = bytearray(self.raw[:data_offset])
        _put_u32be(head, 0x110, spans[0])
        _put_u32be(head, 0x114, sizes[0])
        _put_u32be(head, 0x118, data_offset)
        _put_u32be(head, 0x11c, spans[1] if len(spans) > 1 else 0)
        for i in range(len(self.toc_records)):
            o = 0x120 + i * 12
            _put_u32be(head, o, sizes[i + 1])
            _put_u32be(head, o + 4, offs[i + 1])
            _put_u32be(head, o + 8,
                       spans[i + 2] if i + 2 < len(spans) else self.toc_records[i][2])
        return bytes(head) + b"".join(bodies)


def load(path) -> LS11File:
    with open(path, "rb") as f:
        return LS11File(f.read())
