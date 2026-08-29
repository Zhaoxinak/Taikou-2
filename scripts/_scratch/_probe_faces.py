"""Probe FACE.LZW portrait validity per face_id."""
import os
import struct
import sys

DATA = r"F:\Games\Taikou2"
sys.path.insert(0, os.path.dirname(__file__))

from _graph_probe import ls11  # noqa: E402


def unpack_npk(src: bytes, line: int, height: int) -> bytes:
    dest = bytearray(line * height)
    filled = 0
    pos = 0
    bitflag = 0
    dest_len = line * height
    while pos < len(src) and filled < dest_len:
        if (bitflag & 0xFF00) == 0:
            if pos >= len(src):
                break
            bitflag = 0xFF00 | src[pos]
            pos += 1
        if bitflag & 1:
            if pos >= len(src):
                break
            b = src[pos]
            pos += 1
            run_size = (b & 0x1F) + 1
            run_offset = ((b & 0x60) >> 5) + 1
            run_offset = run_offset * line if (b & 0x80) else run_offset * 4
            for _ in range(run_size * 4):
                if filled >= dest_len or filled - run_offset < 0:
                    break
                dest[filled] = dest[filled - run_offset]
                filled += 1
        else:
            if pos + 1 >= len(src):
                break
            b1 = src[pos]
            b2 = src[pos + 1]
            pos += 2
            for _ in range(4):
                if filled >= dest_len:
                    break
                d = ((b1 & 0x80) >> 4) | ((b1 & 0x08) >> 1) | ((b2 & 0x80) >> 6) | ((b2 & 0x08) >> 3)
                dest[filled] = d
                filled += 1
                b1 = (b1 << 1) & 0xFF
                b2 = (b2 << 1) & 0xFF
        bitflag >>= 1
    return bytes(dest[:filled])


def try_face(face_comp: bytes, meta: bytes, face_id: int) -> bool:
    rec_off = face_id * 12
    if rec_off + 12 > len(meta):
        return False
    w, h = 64, 80
    need = w * h
    for slot in range(3):
        pack = struct.unpack_from("<I", meta, rec_off + slot * 4)[0]
        offset = pack & 0xFFFF
        size = (pack >> 16) & 0xFFFF
        if size == 0 or offset + size > len(face_comp):
            continue
        blob = face_comp[offset : offset + size]
        idx = unpack_npk(blob, w, h)
        if len(idx) >= need:
            return True
    return False


def main() -> None:
    face_comp = open(os.path.join(DATA, "FACE.LZW"), "rb").read()
    decomp = ls11(face_comp)
    meta = decomp[4:]
    entries = len(meta) // 12
    print("meta entries", entries)
    ok = [i for i in range(entries) if try_face(face_comp, meta, i)]
    print("valid portraits", len(ok), "max_id", max(ok) if ok else -1)
    for fid in [13, 16, 79, 128, 134, 200]:
        print(f"face {fid}:", try_face(face_comp, meta, fid))


if __name__ == "__main__":
    main()
