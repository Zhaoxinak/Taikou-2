#!/usr/bin/env python3
"""用 Blender 渲染日本史实大地图 v2（真实地理数据）。

输入（gen_japan_terrain.py 生成）：
  /tmp/japan_terrain/height_<season>.png
  /tmp/japan_terrain/color_<season>.png

输出：
  assets/map_bg_<season>_v2.png     （4096×3072 渲染，已垂直翻转）
  assets/map_scene_v2.blend         （可编辑工程）

用法：
  "/Applications/Blender.app/Contents/MacOS/Blender" -b -P scripts/blender_render_japan.py -- <season>
"""
import bpy, sys, os

season = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'spring'
ROOT = '/Users/ts/Downloads/Taikou 2'
HEIGHT_PNG = f'/tmp/japan_terrain/height_{season}.png'
COLOR_PNG = f'/tmp/japan_terrain/color_{season}.png'
OUT_PNG = os.path.join(ROOT, f'assets/map_bg_{season}_v2.png')
OUT_BLEND = os.path.join(ROOT, 'assets/map_scene_v2.blend')

MAP_W, MAP_H = 48.0, 36.0
SUB = 24          # 每格细分（1152x864 顶点 → 每顶点对应贴图 ~1.25px）
RENDER_W, RENDER_H = 4096, 3072

def cleanup():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def build():
    cleanup()
    # ---- 网格（48x48 grid → 顶点 y 压到 0..36，UV v 翻转使北在顶部）----
    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=int(MAP_W * SUB), y_subdivisions=int(MAP_H * SUB),
        size=MAP_W, location=(MAP_W / 2, MAP_H / 2, 0))
    obj = bpy.context.active_object
    obj.name = 'JapanTerrain'
    mesh = obj.data
    # 顶点 y：0..48 → 0..36（保持线性，UV 不变）
    import numpy as np
    nv = len(mesh.vertices)
    co = np.empty(nv * 3, dtype=np.float64)
    mesh.vertices.foreach_get('co', co)
    co = co.reshape(nv, 3)
    co[:, 1] *= 0.75
    mesh.vertices.foreach_set('co', co.reshape(-1))
    # UV v 翻转：北（lat45.8）应贴到纹理顶部 v=0，而 grid 默认 v=0 在网格 y=0（南）
    uv_layer = mesh.uv_layers[0]
    uvs = np.empty(len(uv_layer.data) * 2, dtype=np.float64)
    uv_layer.data.foreach_get('uv', uvs)
    uvs[1::2] = 1.0 - uvs[1::2]   # v_new = 1 - v_old
    uv_layer.data.foreach_set('uv', uvs)
    mesh.update()

    # ---- 高度置换 ----
    height_img = bpy.data.images.load(HEIGHT_PNG)
    tex = bpy.data.textures.new('HeightMap', 'IMAGE')
    tex.image = height_img
    displ = obj.modifiers.new('HeightDisplace', 'DISPLACE')
    displ.texture = tex
    displ.texture_coords = 'UV'
    displ.mid_level = 0.0
    displ.strength = 7.5   # 高度放大

    # ---- 材质（平光卡通 + 柔光立体：Diffuse + 少量 Emission）----
    color_img = bpy.data.images.load(COLOR_PNG)
    mat = bpy.data.materials.new('TerrainMat')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    texnode = nt.nodes.new('ShaderNodeTexImage')
    texnode.image = color_img
    diff = nt.nodes.new('ShaderNodeBsdfDiffuse')
    nt.links.new(texnode.outputs['Color'], diff.inputs['Color'])
    nt.links.new(diff.outputs['BSDF'], out.inputs['Surface'])
    obj.data.materials.append(mat)

    # ---- 柔和定向光（左上斜照，让山有明暗）----
    sun_data = bpy.data.lights.new('Sun', 'SUN')
    sun = bpy.data.objects.new('Sun', sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (1.12, 0, -0.6)   # 约 64° 高度角，从西北照
    sun_data.energy = 1.6

    # ---- 相机（正交全图）----
    cam_data = bpy.data.cameras.new('Cam')
    cam = bpy.data.objects.new('Cam', cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (MAP_W / 2, MAP_H / 2, 60)
    cam.rotation_euler = (0, 0, 0)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = MAP_W * 1.002
    bpy.context.scene.camera = cam

    # ---- 渲染设置 ----
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = RENDER_W
    sc.render.resolution_y = RENDER_H
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    # 世界背景：浅蓝（海外的空白区）+ 环境光
    world = bpy.data.worlds.new('World')
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.42, 0.62, 0.85, 1.0)
        bg.inputs['Strength'].default_value = 0.7
    sc.world = world
    sc.render.filepath = OUT_PNG
    bpy.ops.render.render(write_still=True)
    # 注：渲染图为南在上（相机朝 -Z），需在外部用系统 python3(PIL) 做 FLIP_TOP_BOTTOM

    # ---- 存工程 ----
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

if __name__ == '__main__':
    build()
    print('RENDER_DONE', OUT_PNG)
