"""MSGX 文本容器读写（LS11 解压后的二级容器）。

布局：
    0x00  4B  "MSGX"
    0x04  u16LE count
    0x06  count × u32LE offsets   每条文本在数据区的绝对偏移
    ...   数据区，GBK 明文（无 XOR、无压缩）

改文本要点：**必须等长替换**（GBK 编码后字节数相同），这样整段的解压长度、
后续偏移表、以及 LS11 的段长都不用变，重打包零风险。
"""

import struct

MAGIC = b"MSGX"


class Msgx:
    def __init__(self, data: bytes):
        assert data[:4] == MAGIC, "不是 MSGX 容器"
        self.count = struct.unpack("<H", data[4:6])[0]
        self.offsets = list(struct.unpack("<%dI" % self.count, data[6:6 + self.count * 4]))
        ends = self.offsets[1:] + [len(data)]
        self.items = [data[a:b] for a, b in zip(self.offsets, ends)]

    def text(self, i, errors="replace"):
        # 末尾常有 0x00 / 控制码，strip 掉 \x00 再解
        return self.items[i].rstrip(b"\x00").decode("gbk", errors)

    def set_text(self, i, new_text: str):
        """等长替换。返回 True 表示成功。"""
        old = self.items[i]
        body = new_text.encode("gbk")
        tail = old[len(old.rstrip(b"\x00")):]
        cand = body + tail
        if len(cand) != len(old):
            raise ValueError(
                f"长度不符：原 {len(old)}B，新 {len(cand)}B（请调整字数使其等长）")
        self.items[i] = cand

    def pack(self) -> bytes:
        base = 6 + self.count * 4
        offs = []
        cur = base
        for it in self.items:
            offs.append(cur)
            cur += len(it)
        body = b"".join(self.items)
        return MAGIC + struct.pack("<H", self.count) + \
            struct.pack("<%dI" % self.count, *offs) + body
