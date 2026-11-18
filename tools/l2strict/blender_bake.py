# Blender headless bake script (run via `blender --background --python
# blender_bake.py -- <manifest.json>`, DEVLOG-92). The manifest (built by
# baked_mesh.py) carries, per mesh object:
#   {"gltf": <import path>, "out_dir": ..., "slots": [{"slot": k,
#     "height_png": ..., "albedo_png": ..., "displace_m": ...}]}
# Pipeline (the user's work order 2026-11-19):
#   1. the LOW body is DENSIFIED to the 500-1000-tri target (per-slot
#      SIMPLE subsurf x1 + a light Displace 0.03 m — the pilasters/panels
#      get REAL geometry, not just a normal-map illusion) + Smart UV
#      Project UV2 (the unique bake unwrap; UV1 = the client tile UVs),
#   2. the HIGH source = per-slot subsurf x3 + full Displace 0.05 m; its
#      materials get the CLIENT albedo images (UV1, REPEAT) so the
#      DIFFUSE bake carries the real pattern,
#   3. bake DIFFUSE(color) + tangent NORMAL + AO through UV2 (Cycles,
#      selected->active),
#   4. export the dense low mesh (UV1 + UV2) + the three baked PNGs.
# The statistics (the user's item 2) print per stage.
import bpy
import json
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
manifest = json.load(open(argv[0]))

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=manifest["gltf"])
lows = [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


print("STATS import:", [(o.name, len(o.data.polygons), _tris(o)) for o in lows])

# ---- UV2: the unique bake unwrap -------------------------------------
for o in lows:
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    o.data.uv_layers.new(name="bakeUV")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    o.select_set(False)


def _split_by_slot(o, slot, suffix):
    part = o.copy()
    part.data = o.data.copy()
    part.name = "%s_S%d_%s" % (o.name, slot, suffix)
    bpy.context.scene.collection.objects.link(part)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(part.data)
    drop = [f for f in bm.faces if f.material_index != slot]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(part.data)
    bm.free()
    if not len(part.data.polygons):
        bpy.data.objects.remove(part)
        return None
    return part


def _displace_setup(part, uv_name, img_path, strength):
    img = bpy.data.images.load(img_path)
    tex = bpy.data.textures.new("%s_disp" % part.name, type="IMAGE")
    tex.image = img
    tex.extension = "REPEAT"
    tex.use_alpha = False
    sub = part.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    dmod = part.modifiers.new("disp", "DISPLACE")
    dmod.texture = tex
    dmod.texture_coords = "UV"
    dmod.uv_layer = uv_name
    dmod.mid_level = 0.5
    dmod.strength = strength
    return sub, dmod


slot_map = {int(s["slot"]): s for s in manifest["slots"]}

# ---- the dense LOW body (target 500-1000 tris) -------------------------
low_parts = []
for o in lows:
    uv1 = o.data.uv_layers[0].name
    for slot in range(len(o.material_slots)):
        spec = slot_map.get(slot)
        if spec is None:
            continue
        part = _split_by_slot(o, slot, "LO")
        if part is None:
            continue
        sub, dmod = _displace_setup(part, uv1, spec["height_png"],
                                    float(spec.get("displace_low_m", 0.03)))
        sub.levels = 2
        part.select_set(True)
        bpy.context.view_layer.objects.active = part
        bpy.ops.object.modifier_apply(modifier="sub")
        if dmod.strength != 0.0:
            bpy.ops.object.modifier_apply(modifier="disp")
        else:
            part.modifiers.remove(dmod)   # strength 0 = disabled, apply fails
        low_parts.append(part)
bpy.ops.object.select_all(action="DESELECT")
for p in low_parts:
    p.select_set(True)
bpy.context.view_layer.objects.active = low_parts[0]
if len(low_parts) > 1:
    bpy.ops.object.join()
low = bpy.context.view_layer.objects.active
low.name = manifest.get("export_name", "baked").replace(".gltf", "")
# NO decimate: it ate the thin cornice-ring geometry (holes, the floating
# shaft — DEVLOG-92). The dense low stays at the subsurf x2 count (~2.2k
# tris for a 140-tri prop) — above the 500-1000 band, but the props are
# few and the rings must survive.
print("STATS dense low: polys", len(low.data.polygons), "tris", _tris(low))

# Unique UV2 on the dense body (after densification). The parts inherited
# the bakeUV layer from the original (added before the split); creating
# another would leave THREE layers. The exporter emits the UV layers in
# REVERSE list order (empirical, three rebakes: layer[1] always landed as
# TEXCOORD_0 — DEVLOG-92), and the runtime contract is TEXCOORD_0 = client
# tile UVs, TEXCOORD_1 = the bake atlas — so the ATLAS layer must sit
# FIRST in the list: swap the two layers' coordinate DATA (the names
# travel with the data below).
u0 = low.data.uv_layers[0]
u1 = low.data.uv_layers[1]
n_loops = len(u0.data)
tmp = [u0.data[i].uv for i in range(n_loops)]
for i in range(n_loops):
    u0.data[i].uv = u1.data[i].uv
for i in range(n_loops):
    u1.data[i].uv = tmp[i]
u0.name = "A_atlas"
u1.name = "Z_tile"
u0.active = True
uv2_name = u0.name
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
bpy.ops.object.mode_set(mode="OBJECT")
low.select_set(False)
print("STATS uv layers:", [l.name for l in low.data.uv_layers])

# ---- the HIGH bake source ---------------------------------------------
his = []
for o in lows:
    uv1 = o.data.uv_layers[0].name
    for slot in range(len(o.material_slots)):
        spec = slot_map.get(slot)
        if spec is None:
            continue
        part = _split_by_slot(o, slot, "HI")
        if part is None:
            continue
        sub, dmod = _displace_setup(part, uv1, spec["height_png"],
                                    float(spec.get("displace_m", 0.05)))
        sub.levels = 3
        part.select_set(True)
        bpy.context.view_layer.objects.active = part
        bpy.ops.object.modifier_apply(modifier="sub")
        bpy.ops.object.modifier_apply(modifier="disp")
        # the CLIENT albedo image on the part's material (the DIFFUSE bake
        # source; UV1 tile coordinates, REPEAT — an EXPLICIT UVMap node,
        # because the active UV layer can be the bake atlas after the
        # UV2 creation and the tiling image would sample out of range)
        img = bpy.data.images.load(spec["albedo_png"])
        mat = part.material_slots[slot].material
        nt = mat.node_tree
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.name = "BAKE_ALBEDO"
        tex.image = img
        tex.extension = "REPEAT"
        uvnode = nt.nodes.new("ShaderNodeUVMap")
        uvnode.name = "BAKE_UV1"
        uvnode.uv_map = uv1
        nt.links.new(uvnode.outputs["UV"], tex.inputs["Vector"])
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        # the DIFFUSE bake through the Principled evaluated black; the EMIT
        # bake of the raw texture color is deterministic (no lighting
        # dependence). The materials are placeholders — the runtime
        # overrides every surface material on the baked variant.
        em = nt.nodes.new("ShaderNodeEmission")
        em.name = "BAKE_EMIT"
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
        outn = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if outn is not None:
            nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
        his.append(part)
bpy.ops.object.select_all(action="DESELECT")
for p in his:
    p.select_set(True)
bpy.context.view_layer.objects.active = his[0]
if len(his) > 1:
    bpy.ops.object.join()
high = bpy.context.view_layer.objects.active
print("STATS high:", len(high.data.polygons), "polys", _tris(high), "tris")
# the ORIGINAL imported meshes are leftovers (the splits copied them);
# left in the scene they occlude the AO bake to black (DEVLOG-92)
bpy.ops.object.select_all(action="DESELECT")
for o in lows:
    o.select_set(True)
bpy.context.view_layer.objects.active = lows[0]
bpy.ops.object.delete()

# ---- bake DIFFUSE(color) + NORMAL + AO through UV2 ---------------------
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
res = int(manifest.get("bake_res", 1024))
# the diffuse shading samples the ACTIVE-RENDER UV = UV1 (tile coords)
low.data.uv_layers[0].active_render = True

mat_node = {}
for slot in range(len(low.material_slots)):
    mat = low.material_slots[slot].material
    if mat is None:
        continue
    nt = mat.node_tree
    if nt is None:
        continue
    node = nt.nodes.new("ShaderNodeTexImage")
    node.name = "BAKE_TARGET"
    nt.nodes.active = node
    mat_node[slot] = node


def _bake(btype, img, pass_filter=None):
    for slot, node in mat_node.items():
        node.image = img
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    kw = {}
    if pass_filter is not None:
        kw["pass_filter"] = pass_filter
    bpy.ops.object.bake(type=btype, use_selected_to_active=True,
                        use_clear=True, margin=8, margin_type="EXTEND",
                        uv_layer=uv2_name, normal_space="TANGENT", **kw)


def _save(img, name):
    img.filepath_raw = os.path.join(manifest["out_dir"], name)
    img.file_format = "PNG"
    img.save()


os.makedirs(manifest["out_dir"], exist_ok=True)
aimg = bpy.data.images.new("baked_albedo", res, res)   # sRGB (color)
_bake("EMIT", aimg)
_save(aimg, "baked_albedo.png")
nimg = bpy.data.images.new("baked_normal", res, res)
nimg.colorspace_settings.name = "Non-Color"
_bake("NORMAL", nimg)
_save(nimg, "baked_normal.png")
oimg = bpy.data.images.new("baked_ao", res, res)
oimg.colorspace_settings.name = "Non-Color"
_bake("AO", oimg)
_save(oimg, "baked_ao.png")

# ---- export the dense low body (UV1 + UV2) ----------------------------
export_path = os.path.join(manifest["out_dir"],
                           manifest.get("export_name", "baked.gltf"))
bpy.ops.object.select_all(action="DESELECT")
low.select_set(True)
bpy.context.view_layer.objects.active = low
bpy.ops.export_scene.gltf(filepath=export_path, export_format="GLTF_SEPARATE",
                          export_apply=False, export_yup=True,
                          export_texcoords=True)
print("STATS export:", len(low.data.polygons), "polys", _tris(low), "tris")
print("BAKE_DONE", export_path)
