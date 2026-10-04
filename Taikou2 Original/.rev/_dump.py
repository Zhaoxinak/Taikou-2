import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
buf = open(r"C:\Users\Administrator\AppData\Local\CrashDumps\TAIK2W95_familyb.exe.12908.dmp", 'rb').read()
nstreams, dirrva = struct.unpack_from('<II', buf, 8)
S = {}
for i in range(nstreams):
    st, dsz, rva = struct.unpack_from('<III', buf, dirrva + i * 12)
    S[st] = (rva, dsz)
rva, _ = S[5]
cnt = struct.unpack_from('<I', buf, rva)[0]
descs = [struct.unpack_from('<QII', buf, rva + 4 + i * 16) for i in range(cnt)]

def rd(a, sz):
    for va, mrva, msz in descs:
        if va <= a and a + sz <= va + msz:
            return buf[mrva + (a - va):mrva + (a - va) + sz]
    return None

rva, _ = S[3]
n = struct.unpack_from('<I', buf, rva)[0]
print('threads:', n)
for i in range(n):
    off = rva + 4 + i * 48
    tid, = struct.unpack_from('<I', buf, off)
    sva, = struct.unpack_from('<Q', buf, off + 24)
    srva, ssz = struct.unpack_from('<II', buf, off + 32)
    crva, csz = struct.unpack_from('<II', buf, off + 40)
    (EFlags, Edi, Esi, Ebx, Edx, Ecx, Eax, Ebp, Eip, SegCs, _p, Esp, SegSs) = \
        struct.unpack_from('<13I', buf, crva + 0x34)
    if tid != 38340:
        continue
    print('tid=%d EIP=%08X ESP=%08X EBP=%08X EAX=%08X EBX=%08X ECX=%08X EDX=%08X ESI=%08X EDI=%08X'
          % (tid, Eip, Esp, Ebp, Eax, Ebx, Ecx, Edx, Esi, Edi))
    print('gdi32full base guess: %08X' % (Eip - 0x664DA))
    st = rd(sva, ssz)
    print('stack %08X size %04X captured=%s' % (sva, ssz, bool(st)))
    if st:
        for j in range(0, len(st) - 3, 4):
            w, = struct.unpack_from('<I', st, j)
            if 0x400000 <= w < 0x53A000:
                tag = ''
                if 0x536000 <= w < 0x539400:
                    tag = ' [.fdata]'
                elif 0x535000 <= w < 0x536000:
                    tag = ' [cave]'
                print('  sp+%04X [%08X] -> %06X%s' % (j, sva + j, w, tag))
