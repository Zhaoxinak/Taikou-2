import re, os, csv

d = open('TAIK2W95_HD.exe', 'rb').read()

def off2rva(raw):
    # .text: VA 0x1000 raw 0x400 ; .data: VA 0xc4000 raw 0xc4000
    if raw < 0xc4000:
        return raw - 0x400 + 0x1000
    return raw - 0xc4000 + 0xc4000

real = {x.upper(): os.path.getsize(x) for x in os.listdir('.') if os.path.isfile(x)}

rows = []
for m in re.finditer(rb'([@A-Z]):([!-~]{1,60}?)\x00', d):
    raw = m.start()
    name = m.group(2).decode('latin1')
    rows.append((raw, off2rva(raw), m.group(1).decode('latin1'), name))
rows.sort()

# 过滤：只保留"资源清单"区域（rva >= 0x100000）且名字像文件名
res = [r for r in rows if r[1] >= 0x100000 and re.match(r'^[A-Z0-9_]{1,20}\.[A-Z0-9]{2,4}$', r[3], re.I)]

out = []
for raw, rva, pfx, name in res:
    exists = name.upper() in real
    out.append({
        'prefix': pfx,
        'name': name,
        'exe_offset': hex(raw),
        'rva': hex(rva),
        'on_disk': 'yes' if exists else 'no',
        'disk_size': real.get(name.upper(), ''),
    })

with open('.rev/resource_manifest.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['prefix', 'name', 'exe_offset', 'rva', 'on_disk', 'disk_size'])
    w.writeheader()
    w.writerows(out)

# markdown 版
from collections import OrderedDict
by = OrderedDict()
for o in out:
    by.setdefault(o['prefix'], []).append(o)
lines = ['# 太阁立志传2 (TAIK2W95_HD.exe) 内置资源清单', '',
         '从脱壳版可执行文件中提取的 `<前缀>:<文件名>` 引用表，共 %d 条。' % len(out),
         '`on_disk=yes` 表示当前目录已存在同名文件（可直接替换做 mod）。', '']
for p in sorted(by):
    lines.append('## 前缀 `%s:`（%d 项）' % (p, len(by[p])))
    lines.append('')
    lines.append('| 文件名 | EXE 偏移 | RVA | 磁盘存在 | 大小 |')
    lines.append('|---|---|---|---|---|')
    for o in by[p]:
        lines.append('| %s | %s | %s | %s | %s |' % (o['name'], o['exe_offset'], o['rva'], o['on_disk'], o['disk_size']))
    lines.append('')
open('.rev/resource_manifest.md', 'w', encoding='utf-8').write('\n'.join(lines))

print('清单条目:', len(out), ' 前缀:', sorted(by))
print('已写出 .rev/resource_manifest.csv 与 .rev/resource_manifest.md')
