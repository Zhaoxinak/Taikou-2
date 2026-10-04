# -*- coding: utf-8 -*-
import struct, sys, os
sys.stdout.reconfigure(encoding='utf-8')

def parse(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'MDMP', 'not minidump'
    nstreams, dir_rva = struct.unpack_from('<II', b, 8)
    streams = {}
    for i in range(nstreams):
        typ, dsz, rva = struct.unpack_from('<III', b, dir_rva + i * 12)
        streams[typ] = (dsz, rva)

    def u64(o): return struct.unpack_from('<Q', b, o)[0]
    def u32(o): return struct.unpack_from('<I', b, o)[0]

    modules = []
    if 4 in streams:
        dsz, rva = streams[4]
        n = u32(rva); off = rva + 4; MOD = 0x6C
        for k in range(n):
            base = u64(off); size = u32(off + 8); name_rva = u32(off + 20)
            nl = u32(name_rva)
            name = b[name_rva + 4:name_rva + 4 + nl].decode('utf-16-le', 'replace')
            modules.append((base, size, name)); off += MOD

    def mod_of(addr):
        for base, size, name in modules:
            if base <= addr < base + size:
                fn = name.replace('\\', '/').split('/')[-1]
                return '%s+0x%X' % (fn, addr - base)
        return None

    pages = []
    if 5 in streams:
        dsz, rva = streams[5]
        n = u32(rva); off = rva + 4
        for k in range(n):
            d = u32(off); r = u32(off + 4); off += 8
            pages.append((u64(r), b[r + 8:r + 8 + d]))
    elif 9 in streams:
        dsz, rva = streams[9]
        cnt = u64(rva); base_rva = u64(rva + 8); off = rva + 16; cur = base_rva
        for k in range(cnt):
            va = u64(off); ds = u64(off + 8); off += 16
            pages.append((va, b[cur:cur + ds])); cur += ds

    def read(va, n):
        for pva, pb in pages:
            if pva <= va and va + n <= pva + len(pb):
                return pb[va - pva:va - pva + n]
        return None

    if 6 not in streams:
        print(os.path.basename(path), 'no exception stream'); return
    dsz, rva = streams[6]
    tid = u32(rva); rec = rva + 8
    ecode = u32(rec); eflags = u32(rec + 4)
    exc_addr = u64(rec + 0x10)
    nparams = u32(rec + 0x18)
    infos = [u64(rec + 0x20 + 8 * i) for i in range(min(nparams, 15))]
    ctx_off = rec + 0x98                        # MINIDUMP_EXCEPTION 实占 0x98 字节
    csize = u32(ctx_off)
    crva = u32(ctx_off + 4)                     # points directly at CONTEXT record
    # WOW64_CONTEXT: SegGs@80 SegFs@84 EsDi@98 EsI@A0 Ebx@A4 Edx@A8 Ec@AC Ea@B0
    #               Ebp@B4 Eip@B8 SegCs@BC EFlag@C0 SegSs@C4 Esp@C8
    ebp = u32(crva + 0xB4); eip = u32(crva + 0xB8)
    esp = u32(crva + 0xC8); ebx = u32(crva + 0xA4)
    eax = u32(crva + 0xB0); ecx = u32(crva + 0xAC); edx = u32(crva + 0xA8)
    esi = u32(crva + 0xA0); edi = u32(crva + 0x98)

    print('===', os.path.basename(path))
    print('  ExceptionCode=0x%08X  nparams=%d' % (ecode, nparams))
    print('  ExceptionAddress=%s' % (mod_of(exc_addr & 0xFFFFFFFF) or ('0x%016X' % exc_addr)))
    print('  EIP=%s' % (mod_of(eip) or ('0x%08X' % eip)))
    print('  ESP=0x%08X EBP=0x%08X  EAX=%s' % (esp, ebp, mod_of(eax) or ('0x%08X' % eax)))
    print('  EBX=%s ECX=0x%08X EDX=0x%08X ESI=0x%08X EDI=0x%08X' %
          (mod_of(ebx) or ('0x%08X' % ebx), ecx, edx, esi, edi))
    if ecode == 0xC0000005 and nparams >= 2:
        rw = '写入' if infos[0] else '读取'
        print('  AV: %s 目标地址 0x%016X  (%s)' %
              (rw, infos[1], mod_of(infos[1] & 0xFFFFFFFF) or '未映射/堆'))

    # scan down from ESP then EBP for return addrs located inside any module's .text
    for label, sp in (('ESP', esp), ('EBP', ebp)):
        if sp < 0x1000 or sp > 0x7FFFFFFF:
            continue
        raw = read(sp, 512 * 4)
        if not raw:
            continue
        print('  --- scan from %s=0x%08X (只列 exe/较大模块命中) ---' % (label, sp))
        cnt = 0
        for i in range(len(raw) // 4):
            v = struct.unpack_from('<I', raw, i * 4)[0]
            m = mod_of(v)
            if not m:
                continue
            fn = m.split('+')[0]
            big = next((s for b, s, n in modules if n.replace('\\', '/').split('/')[-1] == fn), 0)
            if 'TAIK2W95' in m or big > 0x50000:
                print('     %s+0x%03X  0x%08X  %s' % (label, i * 4, v, m))
                cnt += 1
                if cnt > 25:
                    break
    print()

for p in sys.argv[1:]:
    parse(p)
