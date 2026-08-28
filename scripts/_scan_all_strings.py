# -*- coding: utf-8 -*-
"""全映像 GBK 串扫描：输出所有 >=2 汉字的字符串及其 VA（供大模块定位用）"""
import re, sys, json
BASE = 0x400000
data = open('_unpacked_mem.bin','rb').read()
# GBK 汉字: lead 0xB0-0xF7 (常用区) 扩展 0x81-0xA0; trail 0x40-0xFE 排除 0x7F
str_re = re.compile(rb'(?:[\xb0-\xf7][\x40-\xfe]){2,}')
out = []
for m in str_re.finditer(data):
    s = m.group()
    try:
        t = s.decode('gbk')
    except Exception:
        continue
    if len(t) < 2:
        continue
    va = BASE + m.start()
    out.append((va, len(s), t))
print('total strings:', len(out))
with open('_all_strings.txt','w',encoding='utf-8') as f:
    for va, ln, t in out:
        f.write('0x%x\t%d\t%s\n' % (va, ln, t))
with open('_all_strings.json','w',encoding='utf-8') as f:
    json.dump([{'va':hex(va),'len':ln,'s':t} for va,ln,t in out], f, ensure_ascii=False)
