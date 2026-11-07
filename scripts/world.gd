extends Node3D

const MAP_DIR := "res://assets/maps/20_18"
const UNIT_SCALE := 0.01

var world := Node3D.new()
var terrain_width := 0
var terrain_grid_height := 0
var terrain_origin := Vector2.ZERO
var terrain_cell := Vector2(128.0, 128.0)
var terrain_heights: PackedFloat32Array
var terrain_present: PackedByteArray = PackedByteArray()
var map_data := {}
var materials_data := {}
var asset_map_data := {}
var _mesh_cache := {}
var _shape_cache := {}

# Меши, у которых пол имеет нормали, смотрящие вниз (backface culling делает их невидимыми сверху).
# Предвычислено анализатором геометрии glTF.

func _ready() -> void:
	var started := Time.get_ticks_msec()
	_load_data()
	add_child(world)
	_build_environment()
	_build_terrain()
	_build_meshes()
	_build_lights()
	_spawn_player()
	print("world built in ", (Time.get_ticks_msec() - started) / 1000.0, " s")
	if OS.get_environment("L2_FLOOR_PROFILE") != "":
		_floor_profile_flow()
	if OS.get_environment("L2_FLOOR_GRID") != "":
		_floor_grid_flow()
	if OS.get_environment("L2_GREEN_TRACE") != "":
		_green_trace_flow()
	if OS.get_environment("L2_TRACE_BOX") != "":
		_trace_box_flow()


## Region tracer: L2_TRACE_BOX="x1,y1,x2,y2" casts rays from the camera
## through every 8th pixel of that screen rect and reports the hit mesh,
## face, surface and resolved texture — identifies any suspect region
## (flat-color patches, missing geometry) without eyeballing.
func _trace_box_flow() -> void:
	await get_tree().create_timer(4.0).timeout
	await RenderingServer.frame_post_draw
	var p := OS.get_environment("L2_TRACE_BOX").split(",")
	var r := Rect2i(int(p[0]), int(p[1]), int(p[2]) - int(p[0]), int(p[3]) - int(p[1]))
	var cam := get_viewport().get_camera_3d()
	var space := get_world_3d().direct_space_state
	var counts := {}
	for py in range(r.position.y, r.end.y, 8):
		for px in range(r.position.x, r.end.x, 8):
			var pos := Vector2(px, py)
			var from := cam.project_ray_origin(pos)
			var dir := cam.project_ray_normal(pos)
			var q := PhysicsRayQueryParameters3D.create(from, from + dir * 500.0)
			var hit := space.intersect_ray(q)
			if hit.is_empty():
				counts["NO-HIT"] = counts.get("NO-HIT", 0) + 1
				continue
			var col = hit.get("collider")
			var owner_name := "unknown"
			if col is Node and (col as Node).has_meta("mesh_key"):
				owner_name = str((col as Node).get_meta("mesh_key"))
			var fid := int(hit.get("face_index", -1))
			var k := owner_name
			counts[k] = counts.get(k, 0) + 1
			if counts[k] <= 4:
				var surf := _surface_for_face(owner_name, fid)
				print("TRACE_BOX px(%d,%d) %s face=%d surf=%d tex=%s n=%v" % [
					px, py, owner_name, fid, surf,
					_texture_for_surface(owner_name, surf), hit.get("normal")])
	print("TRACE_BOX totals:", counts)
	get_tree().quit()
	if OS.get_environment("L2_SCREENSHOT") != "":
		_screenshot_flow()


## Green-pixel tracer: L2_GREEN_TRACE=1 renders one frame, finds green-dominant
## pixels, casts rays from the camera through them and reports the exact hit —
## mesh key, face index, resolved surface texture. Settles "what is this green
## surface" without any eyeballing.
func _green_trace_flow() -> void:
	await get_tree().create_timer(4.0).timeout
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var cam := get_viewport().get_camera_3d()
	if cam == null or img == null:
		print("GREEN_TRACE: no camera/image")
		get_tree().quit()
		return
	var w := img.get_width()
	var h := img.get_height()
	var space := get_world_3d().direct_space_state
	var counts := {}
	for py in range(0, h, 4):
		for px in range(0, w, 4):
			var c := img.get_pixel(px, py)
			if c.g <= 0.28 or c.g < c.r or c.g <= c.b * 1.12:
				continue
			var pos := Vector2(px, py)
			var from := cam.project_ray_origin(pos)
			var dir := cam.project_ray_normal(pos)
			var q := PhysicsRayQueryParameters3D.create(from, from + dir * 500.0)
			var hit := space.intersect_ray(q)
			if hit.is_empty():
				continue
			var col = hit.get("collider")
			var owner_name := "unknown"
			if col is Node and (col as Node).has_meta("mesh_key"):
				owner_name = str((col as Node).get_meta("mesh_key"))
			var fid := int(hit.get("face_index", -1))
			var k := "%s" % owner_name
			counts[k] = counts.get(k, 0) + 1
			if counts[k] <= 3:
				# face index -> surface -> texture name
				var surf := _surface_for_face(owner_name, fid)
				print("GREEN_TRACE px(%d,%d) %s face=%d surf=%d tex=%s pos=%v n=%v" % [
					px, py, owner_name, fid, surf, _texture_for_surface(owner_name, surf),
					hit.get("position"), hit.get("normal")])
	print("GREEN_TRACE totals:", counts)
	get_tree().quit()


func _surface_for_face(mesh_key: String, fid: int) -> int:
	var mesh := _get_mesh(mesh_key)
	if mesh == null or fid < 0:
		return -1
	var acc := 0
	for si in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(si)
		var idx = arrays[Mesh.ARRAY_INDEX]
		var n := 0 if idx == null else int(idx.size()) / 3
		if fid < acc + n:
			return si
		acc += n
	return -1


func _texture_for_surface(mesh_key: String, surf: int) -> String:
	if surf < 0:
		return "?"
	var parts := mesh_key.split(":")
	var texs: Array = materials_data.get("meshes", {}).get(parts[0], {}).get(parts[1], [])
	var info = asset_map_data.get("meshes", {}).get(mesh_key, {})
	var pis: Array = info.get("primitive_material_indices", [])
	if surf >= pis.size() or pis[surf] >= texs.size():
		return "no-mapping"
	var t = texs[int(pis[surf])]
	if t == null or not (t is Dictionary):
		return "?"
	return "%s:%s" % [t.get("package", "?"), t.get("object", "?")]


## Numeric floor verifier (replaces eyeball/OCR checks): L2_FLOOR_PROFILE=
## "gx1,gy1,gx2,gy2,steps" (game units) casts straight-down rays along the
## line and prints EVERY surface hit with its height, up-normal and the mesh
## that owns the collider. Any second walkable level shows up immediately.
func _floor_profile_flow() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	var p := OS.get_environment("L2_FLOOR_PROFILE").split(",")
	var a := Vector3(float(p[0]) * UNIT_SCALE, 50.0, float(p[1]) * UNIT_SCALE)
	var b := Vector3(float(p[2]) * UNIT_SCALE, 50.0, float(p[3]) * UNIT_SCALE)
	var steps := maxi(int(p[4]), 1)
	var space := get_world_3d().direct_space_state
	print("FLOOR_PROFILE game(%.0f,%.0f)->game(%.0f,%.0f) %d steps" % [float(p[0]), float(p[1]), float(p[2]), float(p[3]), steps])
	for i in range(steps + 1):
		var t := float(i) / float(steps)
		var origin := a.lerp(b, t)
		var cur_y := 50.0
		var n := 0
		while true:
			var from := Vector3(origin.x, cur_y, origin.z)
			var q := PhysicsRayQueryParameters3D.create(from, from + Vector3(0, -200, 0))
			q.collide_with_areas = false
			var hit := space.intersect_ray(q)
			if hit.is_empty():
				if n == 0:
					print("t=%.2f game(%.0f,%.0f) NO-HIT" % [t, origin.x / UNIT_SCALE, origin.z / UNIT_SCALE])
				break
			var col = hit.get("collider")
			var owner_name := "unknown"
			if col is Node:
				var node := col as Node
				owner_name = str(node.get_meta("mesh_key")) if node.has_meta("mesh_key") else node.name
			print("t=%.2f game(%.0f,%.0f) y=%.3f ny=%.2f via %s" % [
				t, origin.x / UNIT_SCALE, origin.z / UNIT_SCALE,
				hit.get("position").y, hit.get("normal").y, owner_name])
			n += 1
			# step the origin just below this hit to reveal stacked surfaces
			cur_y = hit.get("position").y - 0.01
			if n > 6:
				break
	get_tree().quit()


## Dense grid scan: L2_FLOOR_GRID="gx1,gy1,gx2,gy2,nx,ny" casts nx*ny
## straight-down rays over the rect and prints ONE LINE per ray:
## gx gy topY ny mesh ok|gap — gap = no walkable floor in [-50,-42] m band.
func _floor_grid_flow() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	var p := OS.get_environment("L2_FLOOR_GRID").split(",")
	var a := Vector2(float(p[0]), float(p[1]))
	var b := Vector2(float(p[2]), float(p[3]))
	var nx := maxi(int(p[4]), 2)
	var ny := maxi(int(p[5]), 2)
	var space := get_world_3d().direct_space_state
	print("FLOOR_GRID ", OS.get_environment("L2_FLOOR_GRID"))
	for iy in range(ny):
		var gy: float = lerpf(a.y, b.y, float(iy) / float(ny - 1))
		for ix in range(nx):
			var gx: float = lerpf(a.x, b.x, float(ix) / float(nx - 1))
			# descend through overlying structures (canopy etc.) until the
			# first walkable hit inside the road-deck band
			var cur_y := 40.0
			var best_y := NAN
			var best_n := 0.0
			var best_mesh := "NO-HIT"
			for attempt in range(8):
				var from := Vector3(gx * UNIT_SCALE, cur_y, gy * UNIT_SCALE)
				var q := PhysicsRayQueryParameters3D.create(from, from + Vector3(0, -200, 0))
				var hit := space.intersect_ray(q)
				if hit.is_empty():
					break
				var y: float = hit.get("position").y
				var nyn: float = hit.get("normal").y
				var col = hit.get("collider")
				var owner_name := "unknown"
				if col is Node and (col as Node).has_meta("mesh_key"):
					owner_name = str((col as Node).get_meta("mesh_key"))
				if y > -80.0 and y < -15.0 and absf(nyn) > 0.5:
					# report the topmost standable surface BELOW the canopy
					# zone (MT_Out hangs at +10..+45 over the village)
					best_y = y
					best_n = nyn
					best_mesh = owner_name
					break
				cur_y = y - 0.01
			var walkable: bool = not is_nan(best_y)
			print("%.0f %.0f %.3f %.2f %s %s" % [gx, gy, best_y, best_n, best_mesh, "ok" if walkable else "gap"])
	get_tree().quit()


func _screenshot_flow() -> void:
	var d := OS.get_environment("L2_SCREENSHOT")
	await get_tree().create_timer(4.0).timeout
	await RenderingServer.frame_post_draw
	var cam = get_viewport().get_camera_3d()
	print("DEBUG camera global_pos: ", cam.global_position if cam else "no camera")
	print("DEBUG camera rotation: ", cam.global_rotation if cam else "no camera")
	get_viewport().get_texture().get_image().save_png(d + "/shot1.png")
	await get_tree().create_timer(2.0).timeout
	get_viewport().get_texture().get_image().save_png(d + "/shot2.png")
	get_tree().quit()


func _load_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null: return {}
	var r = JSON.parse_string(f.get_as_text())
	return r if r is Dictionary else {}


func _load_data() -> void:
	map_data = _load_json(MAP_DIR + "/map.json")
	materials_data = _load_json(MAP_DIR + "/materials.json")
	asset_map_data = _load_json(MAP_DIR + "/asset_map.json")
	var td := _load_json(MAP_DIR + "/terrain/terrain.json")
	terrain_width = int(td["source_height_size"][0])
	terrain_grid_height = int(td["source_height_size"][1])
	terrain_origin = Vector2(float(td["origin_game_xy"][0]), float(td["origin_game_xy"][1]))
	terrain_cell = Vector2(float(td["cell_size_game_xy"][0]), float(td["cell_size_game_xy"][1]))
	var stride := terrain_width + 1
	var f := FileAccess.open(MAP_DIR + "/terrain/height_world_f32.raw", FileAccess.READ)
	if f: terrain_heights = f.get_buffer(stride * stride * 4).to_float32_array()
	var pf := FileAccess.open(MAP_DIR + "/terrain/surface_present_u8.raw", FileAccess.READ)
	if pf: terrain_present = pf.get_buffer(int(td["source_height_size"][0]) * int(td["source_height_size"][1]))


func _height_at(x: int, y: int) -> float:
	return terrain_heights[clampi(y, 0, terrain_grid_height) * (terrain_width + 1) + clampi(x, 0, terrain_width)]


func terrain_height(gx: float, gy: float) -> float:
	var lx := clampf((gx - terrain_origin.x) / terrain_cell.x, 0.0, terrain_width - 1.0)
	var ly := clampf((gy - terrain_origin.y) / terrain_cell.y, 0.0, terrain_grid_height - 1.0)
	var ix := int(lx)
	var iy := int(ly)
	var fx := lx - ix
	var fy := ly - iy
	var a := _height_at(ix, iy)
	var b := _height_at(ix + 1, iy)
	var c := _height_at(ix, iy + 1)
	var d := _height_at(ix + 1, iy + 1)
	return a + fx * (b - a) + fy * (c - a) + fx * fy * (a - b - c + d)


func has_terrain_surface(gx: float, gy: float) -> bool:
	var cx := int((gx - terrain_origin.x) / terrain_cell.x)
	var cy := int((gy - terrain_origin.y) / terrain_cell.y)
	if cx < 0 or cy < 0 or cx >= terrain_width or cy >= terrain_grid_height:
		return false
	if terrain_present.size() == int(terrain_grid_height) * terrain_width:
		return terrain_present[cy * terrain_width + cx] == 1
	return true


## Find a staged texture PNG by package/object with the case fallbacks
## used by the staging pipeline (Linux file names are lowercase).
func _find_texture_path(pkg: String, obj: String) -> String:
	if pkg == "" or obj == "":
		return ""
	for cand in ([pkg, pkg.to_lower()]):
		var tp := "%s/textures/%s/Texture/%s.png" % [MAP_DIR, cand, obj]
		if FileAccess.file_exists(tp):
			return tp
		tp = "%s/textures/%s/Texture/%s.png" % [MAP_DIR, cand, obj.to_lower()]
		if FileAccess.file_exists(tp):
			return tp
	return ""


func _build_terrain() -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var stride := terrain_width + 1
	var ph := -8000.0
	var quads := 0
	var ox: float = terrain_origin.x * UNIT_SCALE
	var oz: float = terrain_origin.y * UNIT_SCALE
	var cw: float = terrain_cell.x * UNIT_SCALE
	var ch: float = terrain_cell.y * UNIT_SCALE
	var inv_w := 1.0 / float(terrain_width)
	for y in range(terrain_grid_height):
		for x in range(terrain_width):
			var i00 := y * stride + x
			# L2 QuadVisibilityBitmap: present=0 quads are NOT rendered — the
			# client cuts the terrain under the village, the tunnel and the
			# cave chambers (static meshes enclose those volumes). The
			# heightfield keeps real heights in the cut (leftover data) and
			# the masks keep meadow weights there — rendering those quads
			# leaked grass into caves. The 2026-11-06 "voids" measured under
			# this filter were caused by the broken 0fcf0d0 mesh staging
			# (missing inlet floor), not by the filter; with the UModel
			# meshes restored the profiles are clean.
			var q := y * terrain_width + x
			if terrain_present.size() == terrain_grid_height * terrain_width \
					and terrain_present[q] != 1:
				continue
			# corners in cyclic order: (x,y) (x+1,y) (x+1,y+1) (x,y+1);
			# heights z0 z1 z3 z2 respectively
			var zs := [
				terrain_heights[i00],
				terrain_heights[i00 + 1],
				terrain_heights[i00 + stride + 1],
				terrain_heights[i00 + stride],
			]
			# A present=1 quad whose corners still hold placeholder heights
			# (3 such quads on the map) would draw a spike into the void.
			var real := []
			for i in range(4):
				if zs[i] >= ph:
					real.append(i)
			if real.size() < 4:
				continue
			quads += 1
			var cs := [
				Vector3(ox + x * cw, zs[0] * UNIT_SCALE, oz + y * ch),
				Vector3(ox + (x + 1) * cw, zs[1] * UNIT_SCALE, oz + y * ch),
				Vector3(ox + (x + 1) * cw, zs[2] * UNIT_SCALE, oz + (y + 1) * ch),
				Vector3(ox + x * cw, zs[3] * UNIT_SCALE, oz + (y + 1) * ch),
			]
			var us := [
				Vector2(x, y) * inv_w,
				Vector2(x + 1, y) * inv_w,
				Vector2(x + 1, y + 1) * inv_w,
				Vector2(x, y + 1) * inv_w,
			]
			if real.size() == 4:
				_emit_tri(st, cs[0], cs[2], cs[1], us[0], us[2], us[1])
				_emit_tri(st, cs[0], cs[3], cs[2], us[0], us[3], us[2])
			else:
				_emit_tri(st, cs[real[0]], cs[real[1]], cs[real[2]],
						us[real[0]], us[real[1]], us[real[2]])
	var mat := ShaderMaterial.new()
	var shader := load("res://scripts/terrain.gdshader") as Shader
	mat.shader = shader
	# Original 8 terrain color layers with per-layer masks and UV scales
	# from terrain.json "layers" (verified mappings by the strict pipeline).
	var layers: Array = map_data.get("terrain_layers", [])
	var td2 := _load_json(MAP_DIR + "/terrain/terrain.json")
	if layers.is_empty():
		layers = td2.get("layers", [])
	for li in range(mini(layers.size(), 8)):
		var l: Dictionary = layers[li]
		var tex: Dictionary = l.get("texture", {})
		var mask: Dictionary = l.get("mask", {})
		var tp := _find_texture_path(tex.get("package", ""), tex.get("object", ""))
		var mp := _find_texture_path(mask.get("package", ""), mask.get("object", ""))
		if tp != "":
			var img := Image.new()
			if img.load(tp) == OK:
				mat.set_shader_parameter("layer_%d_texture" % li, ImageTexture.create_from_image(img))
		if mp != "":
			var mimg := Image.new()
			if mimg.load(mp) == OK:
				mat.set_shader_parameter("mask_%d" % li, ImageTexture.create_from_image(mimg))
		# Layer tiling per L2: uv = quad * 64/Scale — detail layers (small
		# Scale) tile DENSELY, the base layer (Scale 128) sparsely
		# (Obase 2.56 m/repeat, OG grass 0.64 m/repeat). tile_uv spans the
		# whole tile (256 quads): shader scale = 256 * 64 / Scale = 16384/Scale.
		var sc: Array = l.get("scale", [128.0, 128.0, 76.0])
		var uscale: Vector2 = Vector2(16384.0 / float(sc[0]), 16384.0 / float(sc[1]))
		mat.set_shader_parameter("layer_%d_uv_scale" % li, uscale)
		mat.set_shader_parameter("layer_%d_uv_offset" % li, Vector2.ZERO)
	mat.set_shader_parameter("do_debug",
			1.0 if OS.get_environment("L2_TERRAIN_DEBUG") == "uv" else 0.0)
	if OS.get_environment("L2_TERRAIN_DEBUG") != "":
		for li in range(8):
			var t = mat.get_shader_parameter("layer_%d_texture" % li)
			var s = mat.get_shader_parameter("layer_%d_uv_scale" % li)
			print("TERRAIN LAYER %d: tex=%s scale=%s" % [li, t.resource_path if t else "NONE", s])
	st.set_material(mat)
	st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var tshape := mi.mesh.create_trimesh_shape()
	# UE2 collision is winding-agnostic; many L2 deck faces point DOWN.
	# Without backface collision the character falls through rendered floors.
	tshape.backface_collision = true
	col.shape = tshape
	body.add_child(col)
	body.add_child(mi)
	body.set_meta("mesh_key", "terrain")
	world.add_child(body)
	print("terrain: ", quads, " quads")


## Emit one terrain triangle. Normals are regenerated later by
## SurfaceTool.generate_normals().
func _emit_tri(st: SurfaceTool, p1: Vector3, p2: Vector3, p3: Vector3,
		uv1: Vector2, uv2: Vector2, uv3: Vector2) -> void:
	st.set_uv(uv1); st.add_vertex(p1)
	st.set_uv(uv2); st.add_vertex(p2)
	st.set_uv(uv3); st.add_vertex(p3)


func _build_meshes() -> void:
	var placed := 0
	var skipped: Array[String] = []
	for actor in map_data["actors"]:
		if actor.get("class") != "StaticMeshActor" or actor.get("deleted"): continue
		var mr = actor.get("mesh")
		if mr == null or not (mr is Dictionary): continue
		var key := "%s:%s" % [mr["package"], mr["object"]]
		# The road-strip family (Btm_Obj01/02/03) = the curb boxes decoded
		# from the variable-length packed records. Their unpacked shape (a
		# 2-m-thick box) renders as raised walls over the road; in the
		# original the border strips are flush inlays. Skip the render and
		# the collision until the packed decompressor yields the real thin
		# slabs — the road surface = the Bridge deck below.
		if key in _ROAD_STRIP_SKIP:
			continue
		var mesh := _get_mesh(key)
		if mesh == null:
			skipped.append(key)
			continue
		var inst := MeshInstance3D.new()
		inst.mesh = mesh
		var loc: Array = actor["location"]
		var rot: Array = actor.get("rotation", [0, 0, 0])
		var pos_z: float = loc[2]
		# Village floor slabs (O_De_01/02/03) read at Z -5541 but their top
		# surface then sits at -56 m — 11.6 m BELOW the village floor level
		# (-44.8, set by the bridge deck -44.05 and PlayerStart Zs -4478..-4493).
		# -5541 + 1161 = -4380 lands the slab top exactly on the floor level,
		# in the Z family of the other floor meshes (Bridge -4288, Btm_Obj01
		# -4508, O_DE_Btm -4952). Experimental shift pending engine-RE of the
		# discrepancy.
		if mr["object"] in ["O_De_01", "O_De_02", "O_De_03"]:
			pos_z = loc[2] + 1161.0
		inst.position = Vector3(loc[0] * UNIT_SCALE, pos_z * UNIT_SCALE, loc[1] * UNIT_SCALE)
		inst.transform.basis = _ue_basis(int(rot[0]), int(rot[1]), int(rot[2]))
		inst.scale = Vector3.ONE * float(actor.get("draw_scale", 1.0))
		world.add_child(inst)
		placed += 1
		if not _shape_cache.has(key):
			var mshape := mesh.create_trimesh_shape()
			# UE2 collision is winding-agnostic; many L2 deck faces point DOWN
			# (inverted winding). Without backface collision the character
			# falls through rendered floors — the "hollow second tier" bug.
			mshape.backface_collision = true
			_shape_cache[key] = mshape
		var body := StaticBody3D.new()
		var col := CollisionShape3D.new()
		col.shape = _shape_cache[key]
		body.add_child(col)
		body.position = inst.position
		body.transform.basis = inst.transform.basis
		body.scale = inst.scale
		body.set_meta("mesh_key", key)
		world.add_child(body)
	print("placed ", placed, " static meshes, ", _shape_cache.size(), " collision shapes")
	if not skipped.is_empty():
		print("SKIPPED (mesh failed to load): ", skipped)


## UE2 FRotationMatrix closed form, matching AActor::LocalToWorld in engine.dll
## (see Docs/DEVLOG.md 2026-11-02). Angles are UE uint16 wraps; rows X/Y/Z are
## UE axes; Godot columns are C*row where C swaps y/z (UE->Godot mapping).
## Rotation is unit-scale: draw_scale is applied separately. Do NOT replace
## this with a Roll*Pitch*Yaw Euler product — it is not equivalent.
func _ue_basis(pitch: int, yaw: int, roll: int) -> Basis:
	var tau := PI * 2.0
	var ap := float(pitch & 0xFFFF) * tau / 65536.0
	var ay := float(yaw & 0xFFFF) * tau / 65536.0
	var ar := float(roll & 0xFFFF) * tau / 65536.0
	var cp := cos(ap); var sp := sin(ap)
	var cy := cos(ay); var sy := sin(ay)
	var cr := cos(ar); var sr := sin(ar)
	# rows of UE2 FRotationMatrix
	var x := Vector3(cp * cy, cp * sy, sp)
	var y := Vector3(sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
	var z := Vector3(-cr * sp * cy - sr * sy, -cr * sp * sy + sr * cy, cr * cp)
	# Godot basis columns = C * row, C swaps y and z
	return Basis(
		Vector3(x.x, x.z, x.y),
		Vector3(z.x, z.z, z.y),
		Vector3(y.x, y.z, y.y))


func _get_mesh(key: String) -> Mesh:
	if _mesh_cache.has(key): return _mesh_cache[key]
	var info = asset_map_data.get("meshes", {}).get(key)
	if info == null: _mesh_cache[key] = null; return null
	var gp: String = info["gltf"]
	if not ResourceLoader.exists(gp): _mesh_cache[key] = null; return null
	var scene: PackedScene = load(gp)
	if scene == null: _mesh_cache[key] = null; return null
	var root := scene.instantiate()
	var mesh: Mesh = null
	for c in root.get_children():
		if c is MeshInstance3D: mesh = c.mesh; break
	if mesh == null: _mesh_cache[key] = null; return null
	var parts := key.split(":")
	var texs: Array = materials_data.get("meshes", {}).get(parts[0], {}).get(parts[1], [])
	var pis: Array = info.get("primitive_material_indices", [])
	for si in range(mesh.get_surface_count()):
		if si >= pis.size(): break
		var mi := int(pis[si])
		if mi < 0 or mi >= texs.size(): continue
		var t = texs[mi]
		if t == null or not (t is Dictionary): continue
		var tpkg: String = t.get("package", "")
		var tobj: String = t.get("object", "")
		var tp: String = "%s/textures/%s/Texture/%s.png" % [MAP_DIR, tpkg, tobj]
		if not FileAccess.file_exists(tp):
			tp = "%s/textures/%s/Texture/%s.png" % [MAP_DIR, tpkg.to_lower(), tobj]
		if FileAccess.file_exists(tp):
			var m := StandardMaterial3D.new()
			var tex := ImageTexture.new()
			var img := Image.new()
			var err := img.load(tp)
			if err != OK:
				print("DIAG mesh %s surf %d: image load failed for %s err=%d" % [key, si, tp, err])
			else:
				tex = ImageTexture.create_from_image(img)
				m.albedo_texture = tex
				m.roughness = 0.95
				# Alpha-scissor ONLY for foliage: in L2 textures the alpha
				# channel is often a mask (specular/blend), not transparency —
				# applying it to structures made the bridge edges see-through.
				var is_foliage := "tree" in parts[0].to_lower() \
						or parts[0].begins_with("Field_Deco")
				if is_foliage and img.detect_alpha():
					m.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
					m.alpha_scissor_threshold = 0.35
					m.cull_mode = StandardMaterial3D.CULL_DISABLED
				elif key in _down_floor_meshes:
					# Пол с нормалями вниз в экспорте — невидим сверху (backface culling).
					# Делаем поверхность двусторонней, чтобы пол был виден и по нему можно ходить.
					m.cull_mode = StandardMaterial3D.CULL_DISABLED
				mesh.surface_set_material(si, m)
				if key == "Oren_DEV_S:O_DE_Bridge" and si == 10:
					print("DIAG bridge floor surface %d: texture applied" % [si])
	_mesh_cache[key] = mesh
	return mesh

# Меши, у которых пол имеет нормали, смотрящие вниз (backface culling делает их невидимыми сверху).
# Предвычислено анализатором геометрии glTF.
# The road-strip family skipped from the render/collision: the curb boxes
# decoded from the variable-length packed records render as 2-m-thick walls
# over the road; the original has them as flush border inlays. Skipped until
# the packed decompressor yields the real thin slabs.
var _ROAD_STRIP_SKIP := [
	"Oren_DEV_S:O_DE_Btm_Obj02", "Oren_DEV_S:O_DE_Btm_Obj03",
]
var _down_floor_meshes := [
	"Door_Set_S:DE_Agit01_door", "Door_Set_S:DE_Agit02_door",
	"Field_Deco_Artifact_S:world_obj17", "Field_Deco_Artifact_S:world_obj18",
	"Field_Deco_Artifact_S:world_obj19", "Field_Deco_Artifact_S:world_obj20",
	"Field_Deco_Artifact_S:world_obj21", "Field_Deco_Artifact_S:world_obj22",
	"Manor_system_object_S:Manor_DarkElf",
	"Oren_DEV_S:O_DE_Azit01", "Oren_DEV_S:O_DE_Azit02",
	"Oren_DEV_S:O_DE_Bank", "Oren_DEV_S:O_DE_Bank_Set",
	"Oren_DEV_S:O_DE_Board", "Oren_DEV_S:O_DE_Bridge",
	"Oren_DEV_S:O_DE_Btm", "Oren_DEV_S:O_DE_CH_Btm",
	"Oren_DEV_S:O_DE_CH_body", "Oren_DEV_S:O_DE_CH_side",
	"Oren_DEV_S:O_DE_Center_obj", "Oren_DEV_S:O_DE_H01",
	"Oren_DEV_S:O_DE_H02", "Oren_DEV_S:O_DE_H03", "Oren_DEV_S:O_DE_H04",
	"Oren_DEV_S:O_DE_Lamp01", "Oren_DEV_S:O_DE_Lamp02",
	"Oren_DEV_S:O_DE_MT_In", "Oren_DEV_S:O_DE_MT_Out",
	"Oren_DEV_S:O_DE_MT_obj01", "Oren_DEV_S:O_DE_Pir01",
	"Oren_DEV_S:O_DE_Pir02", "Oren_DEV_S:O_DE_SH",
	"Oren_DEV_S:O_DE_SH_Set", "Oren_DEV_S:O_DE_WH",
	"Oren_DEV_S:O_DE_inlet", "Oren_DEV_S:O_De_01",
	"Oren_DEV_S:O_De_02", "Oren_DEV_S:O_De_03",
	"Oren_tree_S:Oren_Darkelf_tree01", "Oren_tree_S:Oren_Darkelf_tree02",
	"Oren_tree_S:Oren_Darkelf_tree03", "Oren_tree_S:Oren_Darkelf_tree09",
	"Oren_tree_S:Oren_Darkelf_tree11", "Oren_tree_S:Oren_Darkelf_tree12",
	"World_BulletinBoard_S:O_DE_BulletinBody",
	"field_deco_S:deco_Doren_stone001", "field_deco_S:deco_Doren_stone002",
	"field_deco_S:deco_Doren_stone003", "field_deco_S:deco_Doren_stone004",
	"field_deco_S:deco_Doren_stone005", "field_deco_S:deco_Doren_stone006",
	"field_deco_S:deco_Doren_stone007", "field_deco_S:deco_Doren_stone008",
	"field_deco_S:deco_Doren_stone009", "field_deco_S:deco_Doren_stone010",
	"interior_B_delf_s:interior_B_delf_store_01",
	"interior_B_delf_s:interior_B_delf_store_02",
	"interior_B_delf_s:interior_B_delf_store_03",
	"interior_B_delf_s:interior_B_delf_store_04",
	"interior_B_delf_s:interior_B_delf_store_05",
	"interior_B_delf_s:interior_B_delf_store_06",
	"interior_B_delf_s:interior_B_delf_store_07",
	"interior_B_delf_s:interior_B_delf_store_08",
	"interior_B_delf_s:interior_B_delf_store_09",
	"interior_B_delf_s:interior_B_delf_store_10",
	"interior_B_delf_s:interior_B_delf_store_12",
	"interior_B_delf_s:interior_B_delf_store_13",
	"interior_B_delf_s:interior_B_delf_store_14",
	"interior_B_delf_s:interior_B_delf_store_15",
	"interior_B_delf_s:interior_B_delf_store_16",
	"interior_B_delf_s:interior_B_delf_store_18",
	"interior_B_delf_s:interior_B_delf_store_19",
	"interior_B_delf_s:interior_B_delf_store_20",
	"interior_B_delf_s:interior_B_delf_store_22",
	"interior_B_delf_s:interior_B_delf_store_23",
	"interior_B_delf_s:interior_B_delf_store_25",
	"interior_B_delf_s:interior_B_delf_store_26",
	"interior_B_delf_s:interior_B_delf_store_27",
	"interior_B_delf_s:interior_B_delf_store_28",
	"interior_B_delf_s:interior_B_delf_store_29",
	"interior_B_delf_s:interior_B_delf_store_31",
	"interior_B_delf_s:interior_B_delf_store_33",
	"sylen_temple_s:silen_statue", "sylen_temple_s:sylentemple_deco01",
	"sylen_temple_s:sylentemple_deco05", "sylen_temple_s:sylentemple_deco06",
	"sylen_temple_s:sylentemple_deco07", "sylen_temple_s:sylentemple_deco08",
	"sylen_temple_s:sylentemple_deco09", "sylen_temple_s:sylentemple_ent_main",
	"sylen_temple_s:sylentemple_ent_stair", "sylen_temple_s:sylentemple_ent_stair02",
	"sylen_temple_s:sylentemple_outdeco03", "sylen_temple_s:sylentemple_outdeco04",
	"sylen_temple_s:sylentemple_outdeco05", "sylen_temple_s:sylentemple_pir",
	"sylen_temple_s:sylentemple_pir02", "sylen_temple_s:sylentemple_side_ent",
	"sylen_temple_s:sylentemple_sidedoor01", "sylen_temple_s:sylentemple_sidedoor02",
	"sylen_temple_s:sylentemple_skin",
]


func _build_lights() -> void:
	var placed := 0
	for actor in map_data["actors"]:
		if actor.get("class") != "Light" or actor.get("deleted"): continue
		var loc: Array = actor["location"]
		var lamp := OmniLight3D.new()
		lamp.position = Vector3(loc[0] * UNIT_SCALE, loc[2] * UNIT_SCALE, loc[1] * UNIT_SCALE)
		lamp.light_color = Color(1.0, 0.9, 0.7)
		lamp.light_energy = clampf(float(actor.get("light_brightness", 255.0)) / 64.0, 1.0, 8.0)
		lamp.omni_range = maxf(float(actor.get("light_radius", 128.0)) * UNIT_SCALE * 6.0, 3.0)
		lamp.omni_attenuation = 0.25
		lamp.shadow_enabled = false
		world.add_child(lamp)
		placed += 1
	print("placed ", placed, " map lights")


func _build_environment() -> void:
	var bright := OS.get_environment("L2_BRIGHT") != ""
	var sun := DirectionalLight3D.new()
	# THE MAP'S OWN SUN (NSun0: Rotation [-5944,-39696,0], placed NE-high at
	# (242, 264343, 24510)): the UE forward row_x maps to the Godot direction
	# (-0.663, -0.539, -0.519) — the light travels SW-down, exactly opposite
	# the sun actor's NE-high placement. Verified: sun.look_at(direction).
	sun.position = Vector3.ZERO
	add_child(sun)
	sun.look_at(Vector3(-0.663, -0.539, -0.519), Vector3.UP)
	sun.light_energy = 5.0
	sun.shadow_enabled = true
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	# Sky/lighting is FROZEN until the user opens the lighting stage
	# (AGENTS.md "Task discipline"). Do not tune these values.
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.2, 0.3, 0.5)
	sky_mat.sky_horizon_color = Color(0.45, 0.5, 0.55)
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 2.0
	if bright:
		# Diagnostic: flat white ambient + shadowless sun so black regions are
		# recognisable as missing geometry rather than shadowed dark textures.
		# Must switch the ambient source explicitly — color/energy are ignored
		# while ambient_light_source is AMBIENT_SOURCE_SKY.
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color.WHITE
		env.ambient_light_energy = 1.0
		sun.light_energy = 0.6
		sun.shadow_enabled = false
	env.fog_enabled = false
	# Zone lighting/fog from the map data (all 9 ZoneInfo actors carry the
	# same values; see assets/maps/20_18/zones.json):
	#   AmbientVector (0.395) x AmbientBrightness (60/255) = dark ambient
	#   DistanceFogColor BGRA 23 1d 18 00 = RGB(24, 29, 35) dark blue
	#   DistanceFogStart 100 units (1 m) / End 10000 units (100 m)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.395, 0.395, 0.395)
	env.ambient_light_energy = 60.0 / 255.0 * 2.0
	env.fog_mode = Environment.FOG_MODE_DEPTH
	env.fog_light_color = Color8(24, 29, 35)
	env.fog_depth_begin = 1.0
	env.fog_depth_end = 100.0
	env.fog_depth_curve = 1.0
	env.fog_sky_affect = 0.0
	env.fog_enabled = true
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


func _spawn_player() -> void:
	# Spawn on the road deck over the hole cutout, west entrance.
	# Surface under (7400, 17650) is the road deck top at z ~= -4404.5 (measured
	# from glTF triangles in tmp/ent_scan.py); 10+ m clearance overhead.
	var start := Vector3(7400.0, 17650.0, -4404.5)
	var spawn_env := OS.get_environment("L2_SPAWN")
	if spawn_env != "":
		var sp := spawn_env.split(",")
		start = Vector3(float(sp[0]), float(sp[1]), float(sp[2]))
	var floor_y := start.z
	if has_terrain_surface(start.x, start.y):
		floor_y = terrain_height(start.x, start.y)
	else:
		print("spawn cell has no terrain surface, using deck height")
	var player := preload("res://scripts/player.gd").new()
	player.terrain = self
	player.position = Vector3(start.x * UNIT_SCALE, floor_y * UNIT_SCALE + 0.9, start.y * UNIT_SCALE)
	if OS.get_environment("L2_VIEW_YAW") == "":
		player.yaw = -PI / 2  # face the bridge into the village (east, west entrance)
	add_child(player)
	print("player spawned at ", player.position, " terrain_height=", floor_y * UNIT_SCALE)
