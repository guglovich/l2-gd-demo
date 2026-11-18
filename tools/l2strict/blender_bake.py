# Blender headless bake script (run via `blender --background --python
# blender_bake.py -- <manifest.json>`, DEVLOG-90). The manifest (built by
# baked_mesh.py) carries, per mesh object:
#   {"gltf": <import path>, "out_dir": ..., "slots": [{"slot": k,
#     "height_png": <grayscale height image, REPEAT-tiled in UV tile units>}]}
# Pipeline (the user's directive, 2026-11-18 — the baked-mesh route after
# the POM pilot was reverted):
#   high-poly = the imported mesh + SIMPLE subsurf x3 + Displace along
#               normals by the per-slot height texture (the carved panels
#               become REAL geometry),
#   low-poly  = the untouched import (140 tris, UV1 = the client tile UVs)
#               + a unique UV2 unwrap (Smart UV Project) for the bakes,
#   bake      = tangent-space NORMAL + AO, high -> low through UV2,
#   export    = the low mesh as glTF (UV1 + UV2) + the two baked PNGs.
# The runtime cost stays zero (the render mesh is the original; the detail
# lives in the baked maps sampled at UV2 — no UV shift, no swimming, works
# from any angle).
import bpy
import json
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
manifest = json.load(open(argv[0]))

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=manifest["gltf"])
lows = [o for o in bpy.context.scene.objects if o.type == "MESH"]
print("imported:", [o.name for o in lows])

# ---- UV2: the unique bake unwrap -------------------------------------
for o in lows:
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    uv2 = o.data.uv_layers.new(name="bakeUV")
    uv2.active = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    o.select_set(False)

# ---- per-slot split, subsurf + displacement ---------------------------
import bmesh

slot_map = {int(s["slot"]): s for s in manifest["slots"]}
his = []
for o in lows:
    for slot in range(len(o.material_slots)):
        spec = slot_map.get(slot)
        if spec is None:
            continue
        part = o.copy()
        part.data = o.data.copy()
        part.name = "%s_S%d_HI" % (o.name, slot)
        bpy.context.scene.collection.objects.link(part)
        bm = bmesh.new()
        bm.from_mesh(part.data)
        keep = [f for f in bm.faces if f.material_index == slot]
        drop = [f for f in bm.faces if f.material_index != slot]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.to_mesh(part.data)
        bm.free()
        if not len(part.data.polygons):
            bpy.data.objects.remove(part)
            continue
        # displacement texture from the grayscale height image
        img = bpy.data.images.load(spec["height_png"])
        tex = bpy.data.textures.new("%s_disp" % part.name, type="IMAGE")
        tex.image = img
        tex.extension = "REPEAT"
        tex.use_alpha = False
        mod = part.modifiers.new("sub", "SUBSURF")
        mod.subdivision_type = "SIMPLE"
        mod.levels = 3
        mod.render_levels = 3
        dmod = part.modifiers.new("disp", "DISPLACE")
        dmod.texture = tex
        dmod.texture_coords = "UV"
        dmod.uv_layer = o.data.uv_layers[0].name   # the client tile UVs
        dmod.mid_level = 0.5
        dmod.strength = float(spec.get("displace_m", 0.05))
        part.select_set(True)
        bpy.context.view_layer.objects.active = part
        bpy.ops.object.modifier_apply(modifier="sub")
        bpy.ops.object.modifier_apply(modifier="disp")
        his.append(part)

# join the high parts into one bake source
bpy.ops.object.select_all(action="DESELECT")
for p in his:
    p.select_set(True)
bpy.context.view_layer.objects.active = his[0]
if len(his) > 1:
    bpy.ops.object.join()
high = bpy.context.view_layer.objects.active
print("high-poly tris:", len(high.data.polygons))

# ---- bake targets: one image node per material, all -> the same image --
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
res = int(manifest.get("bake_res", 1024))

bpy.ops.object.select_all(action="DESELECT")
for o in lows:
    o.select_set(True)
bpy.context.view_layer.objects.active = lows[0]
for o in lows:
    for mat in o.material_slots:
        if mat.material is None:
            continue
        nt = mat.material.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.name = "BAKE_TARGET"
        nt.nodes.active = node

def _bake(btype, img):
    for o in lows:
        for mat in o.material_slots:
            if mat.material is None:
                continue
            node = mat.material.node_tree.nodes.get("BAKE_TARGET")
            node.image = img
    # selected_to_active: the HIGH source selected, the LOW target active
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    for o in lows:
        o.select_set(True)
    bpy.context.view_layer.objects.active = lows[0]
    uv_name = lows[0].data.uv_layers[1].name
    bpy.ops.object.bake(type=btype, use_selected_to_active=True,
                        use_clear=True, margin=8, margin_type="EXTEND",
                        uv_layer=uv_name, normal_space="TANGENT")

out = manifest["out_dir"]
os.makedirs(out, exist_ok=True)
nimg = bpy.data.images.new("baked_normal", res, res)
nimg.colorspace_settings.name = "Non-Color"
_bake("NORMAL", nimg)
nimg.filepath_raw = os.path.join(out, "baked_normal.png")
nimg.file_format = "PNG"
nimg.save()
aimg = bpy.data.images.new("baked_ao", res, res)
aimg.colorspace_settings.name = "Non-Color"
_bake("AO", aimg)
aimg.filepath_raw = os.path.join(out, "baked_ao.png")
aimg.file_format = "PNG"
aimg.save()

# ---- export the low mesh (UV1 + UV2) ----------------------------------
export_path = os.path.join(out, manifest.get("export_name", "baked.gltf"))
bpy.ops.object.select_all(action="DESELECT")
for o in lows:
    o.select_set(True)
bpy.context.view_layer.objects.active = lows[0]
bpy.ops.export_scene.gltf(filepath=export_path, export_format="GLTF_SEPARATE",
                          export_apply=False, export_yup=True,
                          export_texcoords=True)
print("BAKE_DONE", export_path)
