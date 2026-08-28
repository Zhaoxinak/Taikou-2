"""分析真实 TOWNCHIP/HBCHAR 瓦片，按统计特征分类（地面/建筑/树/角色），
供拼真实场景时挑选，不靠肉眼。"""
import sys
sys.path.insert(0, "scripts")
from real_assets import decode_townchip, decode_hbchar, decode_ega_sprite
from PIL import Image
import statistics


def tile_stats(img, ti, cols, tw=16, th=16):
    tx = (ti % cols) * tw
    ty = (ti // cols) * th
    region = img.crop((tx, ty, tx + tw, ty + th))
    px = region.load()
    alphas = []
    cols_rgb = []
    for y in range(th):
        for x in range(tw):
            r, g, b, a = px[x, y]
            alphas.append(a)
            if a > 0:
                cols_rgb.append((r, g, b))
    if not cols_rgb:
        return None
    # 主色
    cr = sum(c[0] for c in cols_rgb) / len(cols_rgb)
    cg = sum(c[1] for c in cols_rgb) / len(cols_rgb)
    cb = sum(c[2] for c in cols_rgb) / len(cols_rgb)
    # 颜色数（量化到 4bit）
    qs = set((c[0] >> 4, c[1] >> 4, c[2] >> 4) for c in cols_rgb)
    opaque = sum(1 for a in alphas if a > 128)
    return {
        "n": ti, "alpha": opaque / (tw * th),
        "mean": (cr, cg, cb),
        "colors": len(qs),
    }


def main():
    timg, tn, _ = decode_townchip()
    himg, hn, hb_raw = decode_hbchar()

    print("=== TOWNCHIP 瓦片分类（前 60 张，按不透明度/颜色数）===")
    rows = []
    for ti in range(min(tn, 341)):
        s = tile_stats(timg, ti, 17)
        if s:
            rows.append(s)
    # 地面候选：不透明 + 颜色少 + 偏土色
    ground = [s for s in rows if s["alpha"] > 0.9 and s["colors"] <= 6
              and s["mean"][0] > s["mean"][2] and 40 < s["mean"][0] < 200]
    build = [s for s in rows if s["alpha"] > 0.9 and s["colors"] >= 7]
    print("地面候选(前10):", [s["n"] for s in ground][:10])
    print("建筑候选(前10):", [s["n"] for s in build][:10])
    # 打印前 40 张明细
    for s in rows[:40]:
        print(f"  #{s['n']:3d} a={s['alpha']:.2f} colors={s['colors']:2d} mean=({s['mean'][0]:3.0f},{s['mean'][1]:3.0f},{s['mean'][2]:3.0f})")

    print("\n=== HBCHAR 精灵（抽 16 帧看主色，找'人形'）===")
    for fi in [0, 1, 16, 32, 48, 64, 80, 96, 112, 128, 160, 200, 256, 320, 360, 383]:
        sp = decode_ega_sprite(hb_raw, fi)
        s = tile_stats(sp, 0, 1, 16, 16)
        if s:
            print(f"  f{fi:3d}: a={s['alpha']:.2f} colors={s['colors']:2d} mean=({s['mean'][0]:3.0f},{s['mean'][1]:3.0f},{s['mean'][2]:3.0f})")


if __name__ == "__main__":
    main()
