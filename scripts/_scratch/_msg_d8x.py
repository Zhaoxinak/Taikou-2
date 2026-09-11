import json
t = json.load(open(r"F:/Games/Taikou 2/scripts/msgx_all_texts.json", encoding="utf-8"))["texts"]
with open(r"F:/Games/Taikou 2/scripts/_scratch/_msg_d8x.txt", "w", encoding="utf-8") as f:
    for i in range(0xD70, 0xDA0):
        s = t.get(str(i), "")
        if s:
            f.write(f"{i:#x}={i}: {s}\n")
    f.write("--- nearby pushes in func ---\n")
    for i in (0xD85, 0xD96, 0xD97, 0xD98, 0xD9D, 0xFF, 0x16B1):
        f.write(f"{i:#x}: {t.get(str(i))}\n")
print("ok")
