#!/usr/bin/env python3
"""把大地图工程按专业方式整理拆分（v3）。

将 map_scene_v2.blend 的单一大网格 + 单贴图场景，重构为：

  JAPAN_MAP（根集合）
  ├── 01_TERRAIN        地形置换网格（TER_terrain_mesh，带高度置换+光照材质）
  ├── 02_LAYERS         10 个独立图层平面（LAY_01_sea … LAY_10_ships），
  │                     每层独立对象/独立材质/独立贴图，可单独隐藏/编辑/替换
  ├── 03_MARKERS        史实定位标记（Empty，可快速跳转定位）
  │   ├── MTN_*   60 座名山
  │   ├── RIV_*   28 条河流（源头）
  │   ├── LAK_*   13 个湖泊
  │   └── PRT_*   20 个港口
  └── 04_CAMERA_LIGHT   相机 + 太阳光

图层叠加顺序 = 原合成图绘制顺序，叠加结果与原图逐像素一致（已验证 max diff=0）。

用法：
  "/Applications/Blender.app/Contents/MacOS/Blender" -b -P scripts/blender_organize_map.py
输出：assets/map_scene_v3.blend
"""
import bpy, os, sys

ROOT = '/Users/ts/Downloads/Taikou 2'
SRC = os.path.join(ROOT, 'assets/map_scene_v2.blend')
OUT = os.path.join(ROOT, 'assets/map_scene_v3.blend')
LAYER_DIR = '/tmp/japan_terrain/layers_winter'
SEASON = 'winter'

sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import japan_geo_data as G

MAP_W, MAP_H = 48.0, 36.0
LAYER_Z0 = 50.0        # 图层平面基准高度（高于地形置换，正交相机合成出图）
LAYER_ZSTEP = 0.02     # 每层递增高差：确定 EEVEE 透明混合顺序（sea 最低 → ships 最高）
MARK_Z = 3.0           # 标记高度

# 图层顺序与命名（语义序号）
LAYERS = [
    ('01', 'sea', '海面（含浅海/近岸渐变）'),
    ('02', 'land', '陆地基础（植被/纬度色差/高度着色/纸纹）'),
    ('03', 'beach', '沙滩带'),
    ('04', 'forest', '森林斑块'),
    ('05', 'mountains', '卡通山体（60 座史实名山）'),
    ('06', 'rivers', '河流河道（28 条）'),
    ('07', 'lakes', '湖泊（13 个）'),
    ('08', 'river_edges', '河岸浅色带'),
    ('09', 'ports', '港口（栈桥+小屋，20 个）'),
    ('10', 'ships', '装饰船只（12 艘）'),
]


def grid_to_world(px, py):
    """投影坐标(0..47,0..35) → 网格世界坐标（北=+Y，与地形网格 UV 一致）"""
    return px / 47.0 * MAP_W, MAP_H * (1.0 - py / 35.0)


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    scene = bpy.context.scene

    # ---------- 集合层级 ----------
    root = bpy.data.collections.new('JAPAN_MAP')
    c_terrain = bpy.data.collections.new('01_TERRAIN')
    c_layers = bpy.data.collections.new('02_LAYERS')
    c_markers = bpy.data.collections.new('03_MARKERS')
    c_cam = bpy.data.collections.new('04_CAMERA_LIGHT')
    root.children.link(c_terrain)
    root.children.link(c_layers)
    root.children.link(c_markers)
    root.children.link(c_cam)
    scene.collection.children.link(root)

    # 把现有对象从默认集合移入
    for o in list(scene.collection.objects):
        if o.name == 'JapanTerrain':
            o.name = 'TER_terrain_mesh'
            c_terrain.objects.link(o)
        elif o.name in ('Sun', 'Cam'):
            o.name = 'LGT_sun' if o.name == 'Sun' else 'CAM_main'
            c_cam.objects.link(o)
        scene.collection.objects.unlink(o)

    # ---------- 图层平面 ----------
    layer_mats = []
    for idx, (seq, key, desc) in enumerate(LAYERS):
        obj_name = f'LAY_{seq}_{key}'
        png = os.path.join(LAYER_DIR, f'{key}.png')
        layer_z = LAYER_Z0 + idx * LAYER_ZSTEP
        bpy.ops.mesh.primitive_plane_add(size=2, location=(MAP_W/2, MAP_H/2, layer_z))
        plane = bpy.context.active_object
        plane.name = obj_name
        plane.scale = (MAP_W/2, MAP_H/2, 1)
        # UV v 翻转（与地形网格一致：北在顶部）
        mesh = plane.data
        uv = mesh.uv_layers[0]
        import numpy as np
        uvs = np.empty(len(uv.data) * 2, dtype=np.float64)
        uv.data.foreach_get('uv', uvs)
        uvs[1::2] = 1.0 - uvs[1::2]
        uv.data.foreach_set('uv', uvs)
        mesh.update()
        # 材质：贴图直出（Emission 不受光照）+ 透明度经 Transparent 混合
        mat = bpy.data.materials.new(f'MAT_{obj_name}')
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(png)
        emi = nt.nodes.new('ShaderNodeEmission')
        emi.inputs['Strength'].default_value = 1.0
        transp = nt.nodes.new('ShaderNodeBsdfTransparent')
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(tex.outputs['Color'], emi.inputs['Color'])
        nt.links.new(tex.outputs['Alpha'], mix.inputs['Fac'])
        nt.links.new(transp.outputs['BSDF'], mix.inputs[1])
        nt.links.new(emi.outputs['Emission'], mix.inputs[2])
        nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
        mat.blend_method = 'BLEND'
        if hasattr(mat, 'use_backface_culling'):
            mat.use_backface_culling = False
        plane.data.materials.append(mat)
        if hasattr(plane, 'shadow_mode'):
            plane.shadow_mode = 'NONE'   # 图层平面不投射阴影
        c_layers.objects.link(plane)
        layer_mats.append((obj_name, key, desc))

    # ---------- 定位标记（Empty）----------
    def make_marker(name, px, py, size, col):
        wx, wy = grid_to_world(px, py)
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = 'SPHERE'
        e.empty_display_size = size
        e.location = (wx, wy, MARK_Z)
        e.color = col
        c_markers.objects.link(e)
        return e

    for name, lat, lon, w in G.MOUNTAINS:
        px, py = G.proj(lat, lon)
        make_marker(f'MTN_{name}', px, py, 0.8 + w * 0.3, (0.9, 0.6, 0.2, 1))
    for name, pts in G.RIVERS:
        px, py = G.proj(pts[0][0], pts[0][1])
        make_marker(f'RIV_{name}', px, py, 0.7, (0.3, 0.7, 1.0, 1))
    for name, lat, lon, rx, ry in G.LAKES:
        px, py = G.proj(lat, lon)
        make_marker(f'LAK_{name}', px, py, 0.9, (0.2, 0.5, 0.9, 1))
    for name, lat, lon, typ in G.PORTS:
        px, py = G.proj(lat, lon)
        make_marker(f'PRT_{name}', px, py, 0.8, (0.9, 0.3, 0.3, 1))

    # ---------- 保存 ----------
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print('ORGANIZED_DONE', OUT)
    print('LAYERS:', [m[0] for m in layer_mats])
    print('MARKERS:', len([o for o in c_markers.objects]))


if __name__ == '__main__':
    main()
