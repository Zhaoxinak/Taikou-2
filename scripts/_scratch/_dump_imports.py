
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>
import struct
mem=open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read()
BASE=0x400000
# IAT around 0x4fb000
# Original exe TAIK2W95.exe headers
pe=open(r"F:/Games/Taikou2/TAIK2W95.exe","rb").read()
print("PE header magic:", pe[:2])
# DOS header e_lfanew at 0x3c
lfanew=struct.unpack("<I", pe[0x3c:0x40])[0]
print("lfanew", hex(lfanew))
# PE signature
print("PE sig:", pe[lfanew:lfanew+4])
opt_off=lfanew+4+0x14
print("optional header off", hex(opt_off))
# data directory: import at offset 0x80 from optional header start
import_rva=struct.unpack("<I", pe[opt_off+0x80:opt_off+0x84])[0]
import_size=struct.unpack("<I", pe[opt_off+0x84:opt_off+0x88])[0]
print("import rva", hex(import_rva), "size", import_size)
# section headers at opt_off + size_of_optional_header
sec_off=opt_off+struct.unpack("<H", pe[lfanew+4+0x14-2:lfanew+4+0x14])[0]
print("section headers off", hex(sec_off))
# dump import descriptors
print("\n=== import descriptors ===")
for i in range(0, import_size, 20):
    off=import_rva+i
    # need to convert RVA to file offset
    # find section
    for s in range(3):
        sbase=sec_off+s*0x28
        vaddr=struct.unpack("<I", pe[sbase+0xc:sbase+0x10])[0]
        vsize=struct.unpack("<I", pe[sbase+0x8:sbase+0xc])[0]
        foff=struct.unpack("<I", pe[sbase+0x14:sbase+0x18])[0]
        if vaddr<=off<vaddr+vsize:
            fa=foff+(off-vaddr)
            desc=pe[fa:fa+20]
            if desc==b'\x00'*20: continue
            origt=struct.unpack("<I", desc[0x0c:0x10])[0]
            name_rva=struct.unpack("<I", desc[0xc:0x10])[0]
            ft_rva=struct.unpack("<I", desc[0:4])[0]
            # name
            for s2 in range(3):
                sb2=sec_off+s2*0x28
                va2=struct.unpack("<I", pe[sb2+0xc:sb2+0x10])[0]
                vs2=struct.unpack("<I", pe[sb2+0x8:sb2+0xc])[0]
                fo2=struct.unpack("<I", pe[sb2+0x14:sb2+0x18])[0]
                if va2<=name_rva<va2+vs2:
                    name_fo=fo2+(name_rva-va2)
                    name=pe[name_fo:name_fo+64].split(b'\x00')[0].decode('latin1')
                    print(f"  dll={name} orig_first_thunk={origt:#x} first_thunk={ft_rva:#x}")
                    # dump thunk RVAs
                    thunk_fo=fo2+(ft_rva-va2) if va2<=ft_rva<va2+vs2 else None
                    if thunk_fo:
                        for j in range(200):
                            tv=struct.unpack("<I", pe[thunk_fo+j*4:thunk_fo+j*4+4])[0]
                            if tv==0: break
                            if tv&0x80000000:
                                print(f"    [{j}] ord {tv&0xffff}")
                            else:
                                # name thunk
                                for s3 in range(3):
                                    sb3=sec_off+s3*0x28
                                    va3=struct.unpack("<I", pe[sb3+0xc:sb3+0x10])[0]
                                    vs3=struct.unpack("<I", pe[sb3+0x8:sb3+0xc])[0]
                                    fo3=struct.unpack("<I", pe[sb3+0x14:sb3+0x18])[0]
                                    if va3<=tv<va3+vs3:
                                        hint_fo=fo3+(tv-va3)
                                        hint=struct.unpack("<H", pe[hint_fo:hint_fo+2])[0]
                                        fn=pe[hint_fo+2:hint_fo+64].split(b'\x00')[0].decode('latin1')
                                        print(f"    [{j}] {fn}")
                                        break
            break
