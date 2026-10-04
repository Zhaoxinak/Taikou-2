# -*- coding: utf-8 -*-
"""Walk a minidump's faulting-thread stack and list return addresses inside TAIK2W95."""
import struct, sys, os
sys.stdout.reconfigure(encoding='utf-8')

path = sys.argv[1]
b = open(path, 'rb').read()
assert b[:4] == b'MDMP'
ns, dr = struct.unpack_from('<II', b, 8)
st = {}
for i in range(ns):
    t, ds, rva = struct.unpack_from('<III', b, dr + i * 12)
    st[t] = (ds, rva)

def u32(o): return struct.unpack_from('<I', b, o)[0]
def u64(o): return struct.unpack_from('<Q', b, o)[0]

ds, rva = st[4]; n = u32(rva); off = rva + 4; mods = []
for k in range(n):
    base = u64(off); size = u32(off + 8); nr = u32(off + 20); nl = u32(nr)
    nm = b[nr + 4:nr + 4 + nl].decode('utf-16-le', 'replace').replace('\\', '/')
    mods.append((base, size, nm.split('/')[-1])); off += 0x6C

def mod_of(a):
    for base, size, nm in mods:
        if base <= a < base + size:
            return nm, a - base
    return None

ds, rva = st[6]; tid = u32(rva); rec = rva + 8
crva = u32(rec + 0x9C)
eip = u32(crva + 0xB8); ebp = u32(crva + 0xB4); esp = u32(crva + 0xC8)

ds, rva = st[3]; cnt = u32(rva); o = rva + 4; ENTRY = 48; found = None
for k in range(cnt):
    t = u32(o)
    if t == tid:
        stack_start = u64(o + 24); ss_size = u32(o + 32); ss_rva = u32(o + 36)
        found = (stack_start, ss_size, ss_rva); break
    o += ENTRY
print('tid=%d  EIP=%s  EBP=0x%08X  ESP=0x%08X' % (tid, mod_of(eip) or hex(eip), ebp, esp))
if not found:
    print('thread/stack not found'); sys.exit()
sst, ssz, ssrva = found
print('stack start=0x%08X size=0x%X' % (sst, ssz))
stack = b[ssrva:ssrva + ssz]
print('--- TAIK2W95 return addrs on stack (low->high) ---')
seen = 0
for i in range(0, len(stack) - 4, 4):
    val = struct.unpack_from('<I', stack, i)[0]
    m = mod_of(val)
    if m and m[0].startswith('TAIK2W95'):
        print('  stack+0x%04X (VA 0x%08X) = %s+0x%X' % (i, sst + i, m[0], m[1]))
        seen += 1
        if seen > 40:
            break
# also frame-pointer walk from EBP
def rd(va, ln):
    o2 = va - sst
    if 0 <= o2 and o2 + ln <= len(stack):
        return stack[o2:o2 + ln]
    return None
print('--- EBP-chain walk ---')
f = ebp; depth = 0
while f and 0x1000 < f < 0x7FFFFFFF and depth < 40:
    d = rd(f, 8)
    if not d: break
    ret = struct.unpack_from('<I', d, 4)[0]; nxt = struct.unpack_from('<I', d, 0)[0]
    m = mod_of(ret)
    print('  ebp=0x%08X ret=%s' % (f, ('%s+0x%X' % m) if m else hex(ret)))
    if not m or not m[0].startswith('TAIK2W95'):
        pass
    f = nxt; depth += 1
