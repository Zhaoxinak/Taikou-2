import os, sys
sys.path.insert(0, '.')
from real_assets import ls11_decompress

ROOT = 'F:/Games/Taikou2'
TARGETS = {1745, 180, 760, 768, 1024, 256 * 3, 256 * 4}

print(f"{'name':24} {'raw':>9} {'lzw?':5} {'dec':>9}  note")
print('-' * 70)
matches = []
for fn in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, fn)
    if not os.path.isfile(p):
        continue
    raw = open(p, 'rb').read()
    dec = None
    islzw = False
    try:
        if len(raw) > 0x110:
            d = ls11_decompress(raw)
            if d and len(d) != len(raw):
                dec = d
                islzw = True
    except Exception:
        pass
    sz = len(dec) if dec is not None else len(raw)
    tag = ''
    if sz in TARGETS:
        tag = '  <<< TARGET'
        matches.append((fn, sz, islzw))
    print(f"{fn:24} {len(raw):>9} {str(islzw):5} {sz:>9}{tag}")

print()
print("=== TARGET MATCHES ===")
for fn, sz, islzw in matches:
    print(f"  {fn:24} dec={sz} lzw={islzw}")
