"""Decode all 39 .KOS files (KOEI SFX) to standard .wav.

Discovery (2026-08-24): .KOS are NOT event scripts. Layout:
    byte[0] = 0xAE marker (type tag)
    byte[1:] = XOR(0xAE) of a complete RIFF/WAVE (mono, 22050 Hz, 8-bit PCM)
The decoded payload is already a valid WAV container, so extraction is trivial.

Output: scripts/kos_wav/<NAME>.wav  +  scripts/kos_wav_manifest.json
"""
import os
import json
import struct

SRC = r"F:\Games\Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "kos_wav")
KEY = 0xAE
MARKER = 0xAE


def decode_kos(path: str) -> bytes | None:
    raw = open(path, "rb").read()
    if not raw or raw[0] != MARKER:
        return None
    payload = bytes(b ^ KEY for b in raw[1:])
    if payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        return None
    return payload


def describe_wav(payload: bytes) -> dict:
    rate = ch = bits = datasize = None
    pos = 12
    while pos + 8 <= len(payload):
        cid = payload[pos:pos + 4]
        sz = struct.unpack("<I", payload[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            af, ch, rate = struct.unpack("<HHI", payload[pos + 8:pos + 16])
            bits = struct.unpack("<H", payload[pos + 8 + 14:pos + 8 + 16])[0]
        elif cid == b"data":
            datasize = sz
        pos += 8 + sz
    return {"rate": rate, "channels": ch, "bits": bits, "data_bytes": datasize,
            "wav_size": len(payload)}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    kos = sorted(f for f in os.listdir(SRC) if f.upper().endswith(".KOS"))
    manifest = {"note": ".KOS = KOEI SFX; byte0=0xAE marker, rest=XOR(0xAE) of RIFF/WAVE",
                "count": len(kos), "files": []}
    ok = fail = 0
    for f in kos:
        src = os.path.join(SRC, f)
        payload = decode_kos(src)
        if payload is None:
            fail += 1
            manifest["files"].append({"name": f, "ok": False})
            continue
        wav_name = os.path.splitext(f)[0] + ".wav"
        open(os.path.join(OUT, wav_name), "wb").write(payload)
        meta = describe_wav(payload)
        meta["name"] = f
        meta["wav"] = wav_name
        meta["ok"] = True
        manifest["files"].append(meta)
        ok += 1
    json.dump(manifest, open(os.path.join(OUT, "_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"KOS->WAV: OK={ok}  FAIL={fail}  -> {OUT}")


if __name__ == "__main__":
    main()
