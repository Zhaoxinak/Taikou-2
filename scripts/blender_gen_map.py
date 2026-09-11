#!/usr/bin/env python3
"""
blender_gen_map.py — 用 Blender 生成《太阁立志传2》复刻的大地图底图（3D 地形版 v2）
用法：
  /Applications/Blender.app/Contents/MacOS/Blender --background --python scripts/blender_gen_map.py -- [season] [out]

v2 变更：
  - 材质改 Emission 平涂（太阁5 手绘风，不受光照发黑）
  - 世界背景 = 海蓝色
  - 史实河流（最上川/信浓川/利根川/木曾川/淀川/太田川/筑后川）程序生成：山源→最速下降→海
  - 山体颜色分级：低坡草→山腰棕→高处灰白→雪顶
"""
import bpy, math, sys, os

# ---------- 数据（与 scripts/gen_map_bg.py 同源） ----------
LON0, LON1, LAT0, LAT1 = 128.6, 142.2, 30.8, 41.7
MAP_W, MAP_H = 48.0, 36.0

def proj(lat, lon):
    return (lon - LON0) / (LON1 - LON0) * (MAP_W - 1), (LAT1 - lat) / (LAT1 - LAT0) * (MAP_H - 1)

_HONSHU = [
    [41.05,140.90],[40.60,139.95],[40.00,139.80],[39.30,139.85],[38.90,139.95],
    [38.60,139.50],[38.20,139.20],[37.92,139.05],[37.60,138.90],[37.45,138.60],
    [37.35,138.00],[37.25,137.35],[36.85,136.90],[36.50,136.50],[36.30,136.20],
    [36.00,136.10],[35.90,135.80],[35.65,135.55],[35.72,135.25],[35.70,134.90],
    [35.80,134.35],[35.45,133.30],[35.00,132.60],[34.60,132.00],[34.45,131.50],
    [34.42,130.90],[34.02,130.82],
    [33.90,131.15],[33.78,131.65],[33.98,132.20],[34.20,132.55],[34.38,132.95],
    [34.28,133.40],[34.18,133.85],[34.05,134.25],[34.32,134.55],[34.60,135.02],
    [34.30,134.92],[33.92,135.00],[33.62,135.60],[33.50,135.95],[33.70,136.20],
    [34.00,136.30],[34.45,136.75],[34.72,136.95],[34.70,137.80],[34.80,138.50],
    [34.70,138.95],[35.12,139.72],[35.30,139.80],[35.60,140.05],[35.75,140.85],
    [36.30,140.75],[36.80,140.85],[37.20,141.05],[38.30,141.20],[38.60,141.55],
    [39.40,142.10],[40.40,141.85],[40.85,141.75],[41.30,141.50],[40.95,141.25],
    [41.05,140.90],
]
_KYUSHU = [
    [34.02,130.82],[33.92,130.60],[33.62,130.32],[33.45,130.00],[33.05,129.60],
    [32.62,129.68],[32.30,129.98],[31.62,130.30],[31.30,130.62],[31.18,130.98],
    [31.55,131.38],[32.05,131.65],[32.70,131.90],[33.30,132.00],[33.70,131.62],
    [34.00,131.10],[34.02,130.82],
]
_SHIKOKU = [
    [34.28,134.85],[34.18,134.60],[33.98,134.42],[33.90,134.50],[33.62,134.42],
    [33.32,134.22],[33.05,133.15],[32.92,132.90],[33.10,132.50],[33.42,132.40],
    [33.82,132.72],[34.10,132.85],[34.22,133.30],[34.32,133.80],[34.42,134.30],
    [34.28,134.85],
]
_SADO = [[38.32,138.42],[38.10,138.20],[37.82,138.28],[37.92,138.48],[38.20,138.52]]

POLYS = []
for ring in (_HONSHU, _KYUSHU, _SHIKOKU, _SADO):
    POLYS.append([proj(lat, lon) for lat, lon in ring])

MOUNTAINS = [
    (41.34,141.06),(39.09,140.05),(37.75,140.07),(36.62,137.60),
    (36.16,136.77),(35.36,138.73),(33.28,133.11),(32.88,131.08),
]
M_PTS = [proj(lat, lon) for lat, lon in MOUNTAINS]

# 名山 3D 参数：(x, y, 半径格, 高度幅度)
MOUNT3D = [
    (M_PTS[0][0], M_PTS[0][1], 1.9, 2.3),   # 虾夷(北海道)
    (M_PTS[1][0], M_PTS[1][1], 1.7, 2.1),   # 出羽
    (M_PTS[2][0], M_PTS[2][1], 1.5, 2.0),   # 陆奥
    (M_PTS[3][0], M_PTS[3][1], 1.6, 1.9),   # 越中
    (M_PTS[4][0], M_PTS[4][1], 1.7, 2.2),   # 加贺白山
    (M_PTS[5][0], M_PTS[5][1], 1.6, 2.4),   # 富士
    (M_PTS[6][0], M_PTS[6][1], 1.5, 1.8),   # 四国
    (M_PTS[7][0], M_PTS[7][1], 1.6, 2.0),   # 九州阿苏
]

# 史实河流源点（地图坐标，山地区域；自动沿最速下降流到海）
RIVER_SOURCES = [
    ("最上川", proj(38.30, 140.30)),   # 山形县南部
    ("信浓川", proj(36.20, 138.20)),   # 长野盆地
    ("利根川", proj(36.80, 139.00)),   # 关东山地
    ("木曾川", proj(35.80, 137.50)),   # 木曾山脉
    ("淀川",   proj(35.20, 136.10)),   # 琵琶湖
    ("太田川", proj(34.45, 132.45)),   # 广岛北部
    ("筑后川", proj(33.10, 131.10)),   # 九州中部
]

# ---------- 噪声 ----------
def hash01(ix, iy, seedv):
    h = (ix * 374761393 + iy * 668265263 + seedv * 1274126177) & 0x7FFFFFFF
    h = (h ^ (h >> 13)) * 1103515245 & 0x7FFFFFFF
    h = (h ^ (h >> 16)) & 0x7FFFFFFF
    return (h % 10000) / 10000.0

def vnoise(x, y, seedv):
    ix = math.floor(x); iy = math.floor(y)
    fx = x - ix; fy = y - iy
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    a = hash01(ix, iy, seedv); b = hash01(ix + 1, iy, seedv)
    c = hash01(ix, iy + 1, seedv); d = hash01(ix + 1, iy + 1, seedv)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy

def fbm(x, y, seedv, oct):
    v = 0.0; amp = 0.5; f = 1.0; tot = 0.0
    for _ in range(oct):
        v += amp * vnoise(x * f, y * f, seedv)
        tot += amp
        amp *= 0.5; f *= 2.0
    return v / tot

def in_poly(px, py, pts):
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]; xj, yj = pts[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / ((yj - yi) + 1e-12) + xi:
            inside = not inside
        j = i
    return inside

def is_land(x, y):
    for poly in POLYS:
        if in_poly(x, y, poly):
            return True
    return False

# ---------- 地形高度 ----------
def terrain_height(x, y):
    h = 0.26
    h += fbm(x * 0.85, y * 0.85, 7, 4) * 0.55
    h += fbm(x * 2.6, y * 2.6, 11, 3) * 0.10
    for mx, my, r, amp in MOUNT3D:
        d2 = (x - mx) ** 2 + (y - my) ** 2
        if d2 < (r * 2.2) ** 2:
            h += amp * math.exp(-d2 / (2 * r * r))
    return h

# ---------- 河流生成（最速下降） ----------
def gen_rivers():
    rivers = []
    for name, src in RIVER_SOURCES:
        pts = [src]
        x, y = src
        for _ in range(120):
            if not is_land(x, y) or terrain_height(x, y) < 0.34:
                break
            # 梯度下降（数值差分，略平滑）
            eps = 0.22
            hx = terrain_height(x + eps, y) - terrain_height(x - eps, y)
            hy = terrain_height(x, y + eps) - terrain_height(x, y - eps)
            norm = math.sqrt(hx * hx + hy * hy) + 1e-9
            sx = -hx / norm * 0.5
            sy = -hy / norm * 0.5
            nx, ny = x + sx, y + sy
            if abs(nx - x) < 0.05 and abs(ny - y) < 0.05:
                break
            x, y = nx, ny
            pts.append((x, y))
        rivers.append((name, pts))
    return rivers

# ---------- 季节调色板 ----------
PALETTES = {
    "spring": dict(
        sea=(0.09, 0.31, 0.52), beach=(0.93, 0.87, 0.66),
        grass=(0.47, 0.64, 0.33), grass2=(0.40, 0.57, 0.27),
        forest=(0.20, 0.40, 0.22), rock=(0.57, 0.49, 0.39),
        snow=(0.96, 0.97, 0.98), ice=(0.78, 0.80, 0.84),
        river=(0.16, 0.38, 0.56),
    ),
    "summer": dict(
        sea=(0.07, 0.34, 0.55), beach=(0.95, 0.90, 0.70),
        grass=(0.37, 0.61, 0.26), grass2=(0.30, 0.53, 0.21),
        forest=(0.15, 0.35, 0.17), rock=(0.60, 0.52, 0.42),
        snow=(0.94, 0.96, 0.97), ice=(0.75, 0.78, 0.83),
        river=(0.14, 0.40, 0.58),
    ),
    "autumn": dict(
        sea=(0.11, 0.32, 0.50), beach=(0.88, 0.80, 0.60),
        grass=(0.71, 0.63, 0.31), grass2=(0.61, 0.53, 0.25),
        forest=(0.59, 0.39, 0.17), rock=(0.58, 0.50, 0.40),
        snow=(0.96, 0.97, 0.98), ice=(0.78, 0.80, 0.84),
        river=(0.15, 0.35, 0.52),
    ),
    "winter": dict(
        sea=(0.15, 0.29, 0.46), beach=(0.86, 0.84, 0.78),
        grass=(0.82, 0.84, 0.80), grass2=(0.74, 0.78, 0.74),
        forest=(0.42, 0.50, 0.48), rock=(0.70, 0.70, 0.68),
        snow=(0.97, 0.98, 0.99), ice=(0.86, 0.88, 0.90),
        river=(0.25, 0.38, 0.55),
    ),
}

def lerp3(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

# ---------- 顶点上色 ----------
def land_color(x, y, h, pal, rivers):
    # 河流：点到河段距离 < 宽
    rw = 0.44
    for name, pts in rivers:
        for i in range(len(pts) - 1):
            a = pts[i]; b = pts[i + 1]
            seg = (b[0] - a[0], b[1] - a[1])
            L2 = seg[0] ** 2 + seg[1] ** 2
            if L2 < 1e-9:
                continue
            t = ((x - a[0]) * seg[0] + (y - a[1]) * seg[1]) / L2
            t = max(0.0, min(1.0, t))
            cx = a[0] + t * seg[0]; cy = a[1] + t * seg[1]
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if d < rw:
                return pal["river"]
    # 近海沙滩
    near_sea = False
    for dx, dy in ((0.26, 0), (-0.26, 0), (0, 0.26), (0, -0.26)):
        if not is_land(x + dx, y + dy):
            near_sea = True
            break
    if near_sea and h < 0.72:
        return pal["beach"]
    # 森林斑块
    if h < 0.85 and fbm(x * 0.55 + 9.0, y * 0.55 + 3.0, 21, 3) > 0.62:
        return pal["forest"]
    # 山体
    if h > 1.05:
        t = min(1.0, (h - 1.05) / 1.15)
        if t < 0.55:
            return lerp3(pal["rock"], pal["ice"], t / 0.55)
        return lerp3(pal["ice"], pal["snow"], (t - 0.55) / 0.45)
    # 草地明暗
    g = fbm(x * 1.3 + 5.0, y * 1.3 + 8.0, 13, 3)
    return lerp3(pal["grass"], pal["grass2"], g)

# ---------- 场景构建 ----------
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(confirm=False)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

def build_terrain(season, rivers):
    pal = PALETTES[season]
    NX, NY = 480, 360
    verts = []
    colors = []
    for j in range(NY + 1):
        for i in range(NX + 1):
            x = i / NX * MAP_W
            y = j / NY * MAP_H
            if not is_land(x, y):
                z = 0.0
                c = pal["sea"]
            else:
                z = terrain_height(x, y)
                c = land_color(x, y, z, pal, rivers)
            verts.append((x, y, z))
            colors.append(c)
    faces = []
    for j in range(NY):
        for i in range(NX):
            a = j * (NX + 1) + i
            b = a + 1
            c = a + NX + 1
            d = c + 1
            faces.append((a, b, d, c))
    mesh = bpy.data.meshes.new('JapanTerrain')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    if hasattr(mesh, 'color_attributes'):
        attr = mesh.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    else:
        attr = mesh.vertex_colors.new(name='Col')
    for fi, f in enumerate(faces):
        for k, vi in enumerate(f):
            c = colors[vi]
            attr.data[fi * 4 + k].color = (c[0], c[1], c[2], 1.0)
    obj = bpy.data.objects.new('Japan', mesh)
    bpy.context.scene.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.update()
    return obj

def build_material():
    mat = bpy.data.materials.new('Land')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emis = nt.nodes.new('ShaderNodeEmission')
    col = nt.nodes.new('ShaderNodeVertexColor')
    col.layer_name = 'Col'
    nt.links.new(col.outputs[0], emis.inputs['Color'])
    nt.links.new(emis.outputs[0], out.inputs['Surface'])
    return mat

def setup_world_sea():
    world = bpy.data.worlds['World']
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg is not None:
        bg.inputs['Color'].default_value = (0.09, 0.31, 0.52, 1.0)
        bg.inputs['Strength'].default_value = 1.0

def setup_camera():
    cam_data = bpy.data.cameras.new('Cam')
    cam_obj = bpy.data.objects.new('Cam', cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = (MAP_W / 2, MAP_H / 2, 140.0)
    cam_obj.rotation_euler = (0, 0, 0)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = MAP_W * 1.004
    bpy.context.scene.camera = cam_obj

def render(season, out):
    scene = bpy.context.scene
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except (TypeError, ValueError):
        scene.render.engine = 'BLENDER_EEVEE'
    # 关闭 AgX 色彩管理（保持顶点色原色）
    try:
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0.0
    except Exception:
        pass
    scene.render.resolution_x = 4096
    scene.render.resolution_y = 3072
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    # Blender 相机朝 -Z 渲染图像垂直翻转（顶部=南），用系统 python3(PIL) 转回北在上
    import subprocess
    subprocess.run(['python3', '-c',
        'from PIL import Image; im=Image.open(%r).transpose(Image.FLIP_TOP_BOTTOM); im.save(%r)' % (out, out)])
    print("RENDERED:", out)

# ---------- main ----------
def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    season = argv[0] if argv and argv[0] in PALETTES else 'spring'
    out = argv[1] if len(argv) > 1 else None
    if out is None:
        out = os.path.join(os.path.dirname(__file__), '..', 'assets', 'map_bg_%s_blender.png' % season)
    clear_scene()
    rivers = gen_rivers()
    print("RIVERS:", [(n, len(p)) for n, p in rivers])
    obj = build_terrain(season, rivers)
    mat = build_material()
    obj.data.materials.append(mat)
    setup_world_sea()
    setup_camera()
    render(season, os.path.abspath(out))

main()
