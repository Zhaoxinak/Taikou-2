"""把自制 PNG (RGB8, 行滤波=0) 解码成 ASCII 预览 + 像素统计, 用于无图形界面下确认画面内容"""
import sys, zlib, struct

def decode(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'\x89PNG\r\n\x1a\n'
    i = 8; idat = b''; w = h = None
    while i < len(d):
        ln = struct.unpack('>I', d[i:i+4])[0]
        t = d[i+4:i+8]; body = d[i+8:i+8+ln]
        if t == b'IHDR':
            w, h, bd, ct = struct.unpack('>IIBB', body[:10])
            assert bd == 8 and ct == 2, (bd, ct)
        elif t == b'IDAT':
            idat += body
        i += 12 + ln
    raw = zlib.decompress(idat)
    stride = 1 + w*3
    rows = []
    for y in range(h):
        assert raw[y*stride] == 0, 'filter!=0 不支持'
        rows.append(raw[y*stride+1:(y+1)*stride])
    return w, h, rows

RAMP = ' .:-=+*#%@'

def preview(path, cols=100, rows_out=38):
    w, h, rows = decode(path)
    colors = {}
    nonblack = 0
    for y in range(0, h, 3):
        r = rows[y]
        for x in range(0, w, 3):
            px = (r[x*3], r[x*3+1], r[x*3+2])
            colors[px] = colors.get(px, 0) + 1
            if px[0] + px[1] + px[2] > 24: nonblack += 1
    total = len(range(0, h, 3)) * len(range(0, w, 3))
    print('== %s  %dx%d  采样颜色数=%d  非黑占比=%.1f%%' %
          (path, w, h, len(colors), 100.0*nonblack/total))
    top = sorted(colors.items(), key=lambda kv: -kv[1])[:6]
    print('   主色:', ['#%02X%02X%02X x%d' % (c[0], c[1], c[2], n) for c, n in top])
    cw, ch = w/cols, h/rows_out
    out = []
    for ry in range(rows_out):
        line = ''
        for rx in range(cols):
            x0, x1 = int(rx*cw), max(int(rx*cw)+1, int((rx+1)*cw))
            y0, y1 = int(ry*ch), max(int(ry*ch)+1, int((ry+1)*ch))
            tot = 0; cnt = 0
            for y in range(y0, min(y1, h), 2):
                r = rows[y]
                for x in range(x0, min(x1, w)):
                    tot += (r[x*3]*299 + r[x*3+1]*587 + r[x*3+2]*114)//1000
                    cnt += 1
            v = tot//max(cnt, 1)
            line += RAMP[min(9, v*len(RAMP)//256)]
        out.append(line)
    print('\n'.join(out))

for p in sys.argv[1:]:
    preview(p)
