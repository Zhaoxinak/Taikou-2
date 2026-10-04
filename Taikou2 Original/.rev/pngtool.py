"""pngtool.py — 零依赖 PNG 裁剪 / 放大 / 像素统计

为什么要自己写: 本机没有 PIL(且无外网), 但验证 GDI 画面时经常需要
「把截图某个角落放大看一眼」。tk_shot.py 产出的 PNG 是固定格式
(RGB8, filter 0, 非隔行), 直接手解就很省事。

用法:
    python pngtool.py crop  in.png out.png X Y W H [SCALE]
    python pngtool.py stat  in.png X Y W H        # 统计区域内的颜色分布
    python pngtool.py diff  a.png b.png           # 两图差异像素数
"""
import struct
import sys
import zlib


def read_png(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'\x89PNG\r\n\x1a\n', 'not png'
    p = 8
    idat = b''
    w = h = bitd = ctype = None
    while p < len(d):
        ln = struct.unpack_from('>I', d, p)[0]
        typ = d[p + 4:p + 8]
        body = d[p + 8:p + 8 + ln]
        if typ == b'IHDR':
            w, h, bitd, ctype = struct.unpack_from('>IIBB', body, 0)
        elif typ == b'IDAT':
            idat += body
        elif typ == b'IEND':
            break
        p += 12 + ln
    assert bitd == 8, 'only 8-bit supported'
    nch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * nch
    out = bytearray(h * stride)
    prev = bytearray(stride)
    q = 0
    for y in range(h):
        ft = raw[q]; q += 1
        line = bytearray(raw[q:q + stride]); q += stride
        if ft == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif ft != 0:
            raise ValueError('filter %d' % ft)
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, nch, out


def write_png(path, w, h, nch, buf):
    ctype = {1: 0, 3: 2, 4: 6, 2: 4}[nch]
    rows = b''.join(b'\x00' + bytes(buf[y * w * nch:(y + 1) * w * nch]) for y in range(h))
    def chunk(t, b):
        return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b))
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(rows, 6)) + chunk(b'IEND', b''))
    open(path, 'wb').write(png)


def crop(inp, outp, x, y, w, h, scale=1):
    sw, sh, nch, buf = read_png(inp)
    x = max(0, x); y = max(0, y)
    w = min(w, sw - x); h = min(h, sh - y)
    dw, dh = w * scale, h * scale
    out = bytearray(dw * dh * nch)
    for j in range(dh):
        sy = y + j // scale
        for i in range(dw):
            sx = x + i // scale
            s = (sy * sw + sx) * nch
            d = (j * dw + i) * nch
            out[d:d + nch] = buf[s:s + nch]
    write_png(outp, dw, dh, nch, out)
    print('crop %s (%d,%d %dx%d) -> %s %dx%d scale=%d' % (inp, x, y, w, h, outp, dw, dh, scale))


def stat(inp, x, y, w, h):
    sw, sh, nch, buf = read_png(inp)
    cnt = {}
    for j in range(y, min(y + h, sh)):
        for i in range(x, min(x + w, sw)):
            s = (j * sw + i) * nch
            k = tuple(buf[s:s + 3])
            cnt[k] = cnt.get(k, 0) + 1
    tot = sum(cnt.values())
    print('%s 区域(%d,%d %dx%d) 共 %d px, 不同颜色 %d 种' % (inp, x, y, w, h, tot, len(cnt)))
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])[:12]:
        print('   RGB%-18s %7d  %5.1f%%' % (str(k), v, 100.0 * v / tot))


def diff(a, b):
    wa, ha, nca, ba = read_png(a)
    wb, hb, ncb, bb = read_png(b)
    assert (wa, ha) == (wb, hb) and nca == ncb, 'size mismatch'
    n = sum(1 for i in range(0, len(ba), nca) if ba[i:i + nca] != bb[i:i + nca])
    print('%s vs %s: %d / %d 像素不同 (%.2f%%)' % (a, b, n, wa * ha, 100.0 * n / (wa * ha)))


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'crop':
        crop(sys.argv[2], sys.argv[3], *[int(v) for v in sys.argv[4:8]],
             scale=int(sys.argv[8]) if len(sys.argv) > 8 else 1)
    elif c == 'stat':
        stat(sys.argv[2], *[int(v) for v in sys.argv[3:7]])
    elif c == 'diff':
        diff(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
