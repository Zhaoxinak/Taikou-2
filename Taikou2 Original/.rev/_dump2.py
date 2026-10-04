import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
buf = open(sys.argv[1], 'rb').read()
nstreams, dirrva = struct.unpack_from('<II', buf, 8)
S = {}
for i in range(nstreams):
    st, dsz, rva = struct.unpack_from('<III', buf, dirrva + i * 12)
    S[st] = (rva, dsz)

# memory descriptors
rva5 = S[5][0]
cnt = struct.unpack_from('<I', buf, rva5)[0]
descs = [struct.unpack_from('<QII', buf, rva5 + 4 + i * 16) for i in range(cnt)]
def rd(a, sz):
    for va, mrva, msz in descs:
        if va <= a and a + sz <= va + msz:
            return buf[mrva + (a - va):mrva + (a - va) + sz]
    return None

# modules (empirical: stride 96? verify both)
mods = []
rva4 = S[4][0]
n4 = struct.unpack_from('<I', buf, rva4)[0]
size = len(buf)
for stride, boff, noff in ((116, 0, 20), (96, 4, 24), (108, 0, 20), (112, 0, 20)):
    got = []
    ok = True
    for i in range(n4):
        off = rva4 + 4 + i * stride
        base, = struct.unpack_from('<Q', buf, off + boff)
        nrva, = struct.unpack_from('<I', buf, off + noff)
        if nrva + 8 > size:
            ok = False
            break
        ln = struct.unpack_from('<I', buf, nrva)[0]
        if not (4 <= ln <= 2048) or nrva + 4 + ln > size:
            ok = False
            break
        name = buf[nrva+4:nrva+4+ln].decode('utf-16', 'replace')
        got.append((base, name))
    if ok and any('gdi32full' in n.lower() for b, n in got):
        mods = got
        print('module stride=%d boff=%d noff=%d ok (%d mods)' % (stride, boff, noff, len(got)))
        break
def locate(a):
    for b, n in mods:
        pass
    best = None
    for b, n in mods:
        # size not parsed; approximate by name only via exception addr fallback
        pass
    return None

# exception stream (type 6)
rva6 = S[6][0]
tid, = struct.unpack_from('<I', buf, rva6)
e = rva6 + 8
code, flags = struct.unpack_from('<II', buf, e)
rec, addr, npar = struct.unpack_from('<QQI', buf, e + 8)
params = struct.unpack_from('<15Q', buf, e + 32)
print('EXC tid=%d code=%08X addr=%08X npar=%d param0=%X param1=%08X' %
      (tid, code, addr & 0xFFFFFFFF, npar, params[0], params[1] & 0xFFFFFFFF))
g = [b for b, n in mods if 'gdi32full' in n.lower()]
if g:
    print('gdi32full base=%08X  fault=%s+0x%X' % (g[0], 'gdi32full', (addr & 0xFFFFFFFF) - g[0]))
fam = [b for b, n in mods if 'TAIK' in n]
print('exe base=%08X' % (fam[0] if fam else 0))

# thread context of exception thread
rva3 = S[3][0]
n3 = struct.unpack_from('<I', buf, rva3)[0]
for i in range(n3):
    off = rva3 + 4 + i * 48
    t, = struct.unpack_from('<I', buf, off)
    if t != tid:
        continue
    sva, = struct.unpack_from('<Q', buf, off + 24)
    srva, ssz = struct.unpack_from('<II', buf, off + 32)
    crva, csz = struct.unpack_from('<II', buf, off + 40)
    (EFlags, Edi, Esi, Ebx, Edx, Ecx, Eax, Ebp, Eip, SegCs, _p, Esp, SegSs) = \
        struct.unpack_from('<13I', buf, crva + 0x34)
    print('CTX EIP=%08X ESP=%08X EBP=%08X EAX=%08X EBX=%08X ECX=%08X EDX=%08X ESI=%08X EDI=%08X'
          % (Eip, Esp, Ebp, Eax, Ebx, Ecx, Edx, Esi, Edi))
    st = rd(sva, ssz) if ssz else None
    if st:
        for j in range(0, len(st) - 3, 4):
            w, = struct.unpack_from('<I', st, j)
            if 0x400000 <= w < 0x53A000:
                tag = '.fdata' if 0x536000 <= w < 0x539400 else ('cave' if 0x535000 <= w < 0x536000 else 'exe')
                print('  sp+0x%04X [%08X] -> %08X [%s]' % (j, sva + j, w, tag))
