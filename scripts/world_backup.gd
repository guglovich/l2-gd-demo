extends Node3D
## Builds the Dark Elf Village world from extracted JSON data at startup.

const MAP_DIR := "res://assets/maps/20_18"
const UNIT_SCALE := 0.01

var world := Node3D.new()
var terrain_width := 0
var terrain_grid_height := 0
var terrain_origin := Vector2.ZERO
var terrain_cell := Vector2(128.0, 128.0)
var terrain_heights: PackedFloat32Array
var terrain_surface: PackedByteArray
var map_data := {}
var materials_data := {}
var asset_map_data := {}
var _mesh_cache := {}


func _ready() -> void:
	var started := Time.get_ticks_msec()
	_load_data()
	add_child(world)
	_build_environment()
	_build_terrain()
	# sanity: single triangle right in front of spawn camera
	var tri_st := SurfaceTool.new()
	tri_st.begin(Mesh.PRIMITIVE_TRIANGLES)
	tri_st.set_color(Color(1, 0, 0))
	tri_st.add_vertex(Vector3(120, -40, 200))
	tri_st.add_vertex(Vector3(124, -40, 195))
	tri_st.add_vertex(Vector3(128, -40, 200))
	var tri_mesh := tri_st.commit()
	var tri_inst := MeshInstance3D.new()
	tri_inst.mesh = tri_mesh
	var tri_mat := StandardMaterial3D.new()
	tri_mat.albedo_color = Color(1, 0, 0)
	tri_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	tri_mesh.surface_set_material(0, tri_mat)
	world.add_child(tri_inst)
	_build_meshes()
	_build_lights()
	_spawn_player()
	print("world built in ", (Time.get_ticks_msec() - started) / 1000.0, " s")
	if OS.get_environment("L2_SCREENSHOT") != "":
		_screenshot_flow()
	if OS.get_environment("L2_RAYPROBE") != "":
		_rayprobe_flow()


func _screenshot_flow() -> void:
	var directory := OS.get_environment("L2_SCREENSHOT")
	await get_tree().create_timer(4.0).timeout
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	image.save_png(directory + "/shot1.png")
	await get_tree().create_timer(2.0).timeout
	image = get_viewport().get_texture().get_image()
	image.save_png(directory + "/shot2.png")
	get_tree().quit()


func _rayprobe_flow() -> void:
	await get_tree().create_timer(3.0).timeout
	await RenderingServer.frame_post_draw
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		get_tree().quit()
		return
	for p0 in [Vector3(147.77,-41,160.82), Vector3(143.77,-41,160.82), Vector3(151.77,-41,160.82), Vector3(137.77,-41,160.82), Vector3(157.77,-41,160.82)]:
		for depth in [2.0, 8.0, 20.0]:
			var space := get_world_3d().direct_space_state
			var query := PhysicsRayQueryParameters3D.create(Vector3(p0.x,p0.y,p0.z), Vector3(p0.x,p0.y-depth,p0.z))
			var hit := space.intersect_ray(query)
			if hit.is_empty():
				print("RAYPROBE @(%0.f): depth %.0f -> VOID" % [p0.x, depth])
			else:
				var cn: Object = hit["collider"]
				var pos: Vector3 = hit["position"]
				print("RAYPROBE @(%0.f): depth %.0f -> %s y=%.2f" % [p0.x, depth, cn.get_parent().name, pos.y])
	get_tree().quit()


func _load_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if parsed is Dictionary else {}


func _load_raw(path: String, expected_size: int) -> PackedByteArray:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return PackedByteArray()
	return file.get_buffer(expected_size)


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
	terrain_heights = _load_raw(MAP_DIR + "/terrain/height_world_f32.raw", stride * stride * 4).to_float32_array()
	terrain_surface = _load_raw(MAP_DIR + "/terrain/surface_present_u8.raw", terrain_width * terrain_grid_height)


func _height_at(x: int, y: int) -> float:
	var cx := clampi(x, 0, terrain_width)
	var cy := clampi(y, 0, terrain_grid_height)
	return terrain_heights[cy * (terrain_width + 1) + cx]


func _terrain_normal(x: int, y: int) -> Vector3:
	var left := _height_at(x - 1, y)
	var right := _height_at(x + 1, y)
	var up := _height_at(x, y - 1)
	var down := _height_at(x, y + 1)
	var cell := terrain_cell.x * UNIT_SCALE
	return Vector3(-(right - left) / (2.0 * cell), 1.0, -(down - up) / (2.0 * cell)).normalized()


func has_terrain_surface(game_x: float, game_y: float) -> bool:
	var ix := int(floor((game_x - terrain_origin.x) / terrain_cell.x))
	var iy := int(floor((game_y - terrain_origin.y) / terrain_cell.y))
	if ix < 0 or iy < 0 or ix >= terrain_width or iy >= terrain_grid_height:
		return false
	return terrain_surface[iy * terrain_width + ix] != 0


func terrain_height(game_x: float, game_y: float) -> float:
	var lx := clampf((game_x - terrain_origin.x) / terrain_cell.x, 0.0, float(terrain_width - 1))
	var ly := clampf((game_y - terrain_origin.y) / terrain_cell.y, 0.0, float(terrain_grid_height - 1))
	var ix := clampi(int(lx), 0, terrain_width - 2)
	var iy := clampi(int(ly), 0, terrain_grid_height - 2)
	var fx := lx - float(ix)
	var fy := ly - float(iy)
	var a := _height_at(ix, iy)
	var b := _height_at(ix + 1, iy)
	var c := _height_at(ix, iy + 1)
	var d := _height_at(ix + 1, iy + 1)
	return a + fx * (b - a) + fy * (c - a) + fx * fy * (a - b - c + d)


func _build_terrain() -> void:
	# Render ALL terrain quads. Only true placeholder cells (z < -80m) are gaps.
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var stride := terrain_width + 1
	var placeholder := -8000.0
	for y in range(terrain_grid_height):
		for x in range(terrain_width):
			var i00 := y * stride + x
			var z00 := terrain_heights[i00]
			var z10 := terrain_heights[i00 + 1]
			var z01 := terrain_heights[i00 + stride]
			var z11 := terrain_heights[i00 + stride + 1]
			if z00 < placeholder and z10 < placeholder and z01 < placeholder and z11 < placeholder:
				continue
			var c0 := Vector3(terrain_origin.x * UNIT_SCALE + x * terrain_cell.x * UNIT_SCALE, z00 * UNIT_SCALE, terrain_origin.y * UNIT_SCALE + y * terrain_cell.y * UNIT_SCALE)
			var c1 := Vector3(c0.x + terrain_cell.x * UNIT_SCALE, z10 * UNIT_SCALE, c0.z)
			var c2 := Vector3(c0.x + terrain_cell.x * UNIT_SCALE, z11 * UNIT_SCALE, c0.z + terrain_cell.y * UNIT_SCALE)
			var c3 := Vector3(c0.x, z01 * UNIT_SCALE, c0.z + terrain_cell.y * UNIT_SCALE)
			var u0 := Vector2(x, y) / float(terrain_width)
			var u1 := Vector2(x + 1, y) / float(terrain_width)
			var u2 := Vector2(x + 1, y + 1) / float(terrain_width)
			var u3 := Vector2(x, y + 1) / float(terrain_width)
			_tri(st, c0, c2, c1, u0, u2, u1)
			_tri(st, c0, c3, c2, u0, u3, u2)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(1.0, 1.0, 0.0)  # bright yellow — impossible to miss
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	# layers from terrain.json: Base(T_texture), Obase_1(T_oren), OG_48(T_oren), OC_05(T_oren)
	# masks from t_20_18
	var layer_files = {
		"layer_0_texture": "t_oren/Texture/Obase_1.png",
		"layer_1_texture": "t_oren/Texture/OG_48.png",
		"layer_2_texture": "t_oren/Texture/OC_05.png",
		"layer_3_texture": "t_oren/Texture/OST_11.png",
		"mask_0": "t_20_18/Texture/20_18_G1.png",
		"mask_1": "t_20_18/Texture/20_18_G.png",
		"mask_2": "t_20_18/Texture/20_18_ST.png",
	}
	st.generate_normals()
	var mesh := st.commit()
	var aabb := mesh.get_aabb()
	print("TERRAIN: surfaces=", mesh.get_surface_count(), " tris=", mesh.get_faces().size() / 3, " aabb=", aabb)
	print("TERRAIN faces[0..8]: ", mesh.get_faces().slice(0, 8))
	var mesh_inst := MeshInstance3D.new()
	mesh_inst.mesh = mesh
	mesh_inst.set_as_top_level(true)
	mesh_inst.extra_cull_margin = 1000.0
	mesh_inst.position = Vector3.ZERO
	world.add_child(mesh_inst)
	print("TERRAIN ADDED: children=", world.get_child_count(), " mesh_inst.visible=", mesh_inst.visible, " in_tree=", mesh_inst.is_inside_tree())


func _tri(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3,
		ua: Vector2, ub: Vector2, uc: Vector2) -> void:
	var n := Plane(a, b, c).normal
	st.set_normal(n); st.set_uv(ua); st.add_vertex(a)
	st.set_normal(n); st.set_uv(ub); st.add_vertex(b)
	st.set_normal(n); st.set_uv(uc); st.add_vertex(c)


func _load_tex(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		return load(path)
	return null


func _build_meshes() -> void:
	var placed := 0
	for actor in map_data["actors"]:
		if actor.get("class") != "StaticMeshActor" or actor.get("deleted"):
			continue
		var mesh_ref = actor.get("mesh")
		if mesh_ref == null or not (mesh_ref is Dictionary):
			continue
		var mesh_key := "%s:%s" % [mesh_ref["package"], mesh_ref["object"]]
		var mesh := _get_mesh(mesh_key)
		if mesh == null:
			continue
		var instance := MeshInstance3D.new()
		instance.mesh = mesh
		var loc: Array = actor["location"]
		var rot: Array = actor.get("rotation", [0, 0, 0])
		instance.position = Vector3(loc[0] * UNIT_SCALE, loc[2] * UNIT_SCALE, -loc[1] * UNIT_SCALE)
		instance.rotation.y = -float(rot[1]) * TAU / 65536.0
		instance.scale = Vector3.ONE * float(actor.get("draw_scale", 1.0))
		world.add_child(instance)
		instance.create_trimesh_collision()
		placed += 1
	print("placed ", placed, " static meshes")


func _get_mesh(mesh_key: String) -> Mesh:
	if _mesh_cache.has(mesh_key):
		return _mesh_cache[mesh_key]
	var info = asset_map_data.get("meshes", {}).get(mesh_key)
	if info == null:
		_mesh_cache[mesh_key] = null
		return null
	var gltf_path: String = info["gltf"]
	if not ResourceLoader.exists(gltf_path):
		_mesh_cache[mesh_key] = null
		return null
	var scene: PackedScene = load(gltf_path)
	if scene == null:
		_mesh_cache[mesh_key] = null
		return null
	var root := scene.instantiate()
	var mesh: Mesh = null
	for child in root.get_children():
		if child is MeshInstance3D:
			mesh = child.mesh
			break
	if mesh == null:
		_mesh_cache[mesh_key] = null
		return null
	var parts := mesh_key.split(":")
	var surfaces: Array = materials_data.get("meshes", {}).get(parts[0], {}).get(parts[1], [])
	var prim_indices: Array = info.get("primitive_material_indices", [])
	for si in range(mesh.get_surface_count()):
		var tex := _surface_tex(si, surfaces, prim_indices)
		if tex != null:
			var m := StandardMaterial3D.new()
			m.albedo_texture = tex
			m.roughness = 0.95
			m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
			mesh.surface_set_material(si, m)
	_mesh_cache[mesh_key] = mesh
	return mesh


func _surface_tex(si: int, surfaces: Array, prim_indices: Array) -> Texture2D:
	if si >= prim_indices.size():
		return null
	var mi := int(prim_indices[si])
	if mi < 0 or mi >= surfaces.size():
		return null
	var t = surfaces[mi]
	if t == null or not (t is Dictionary):
		return null
	var pkg: String = t.get("package", "")
	var obj: String = t.get("object", "")
	for p in [pkg, pkg.to_lower()]:
		var path := "%s/textures/%s/Texture/%s.png" % [MAP_DIR, p, obj]
		if ResourceLoader.exists(path):
			return load(path)
	return null


func _build_lights() -> void:
	var placed := 0
	for actor in map_data["actors"]:
		if actor.get("class") != "Light" or actor.get("deleted"):
			continue
		var loc: Array = actor["location"]
		var brightness := float(actor.get("light_brightness", 255.0))
		var radius := float(actor.get("light_radius", 128.0))
		var lamp := OmniLight3D.new()
		lamp.position = Vector3(loc[0] * UNIT_SCALE, loc[2] * UNIT_SCALE, -loc[1] * UNIT_SCALE)
		lamp.light_color = Color(1.0, 0.9, 0.7)
		lamp.light_energy = clampf(brightness / 64.0, 1.0, 8.0)
		lamp.omni_range = maxf(radius * UNIT_SCALE * 6.0, 3.0)
		lamp.omni_attenuation = 0.25
		lamp.shadow_enabled = false
		world.add_child(lamp)
		placed += 1
	print("placed ", placed, " map lights")


func _build_environment() -> void:
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-70.0, 160.0, 0.0)
	sun.light_energy = 3.0
	if OS.get_environment("L2_BRIGHT") != "":
		sun.light_energy = 6.0
		sun.rotation_degrees = Vector3(-55, 200, 0)
	sun.light_color = Color(0.9, 0.92, 1.0)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 160.0
	add_child(sun)
	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	if OS.get_environment("L2_BRIGHT") != "":
		environment.ambient_light_energy = 3.0
		environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		environment.ambient_light_color = Color(0.8, 0.8, 0.9)
		environment.fog_density = 0.0004
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.25, 0.35, 0.55)
	sky_mat.sky_horizon_color = Color(0.5, 0.6, 0.65)
	sky_mat.ground_bottom_color = Color(0.15, 0.18, 0.15)
	sky_mat.ground_horizon_color = Color(0.45, 0.52, 0.45)
	sky.sky_material = sky_mat
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = 2.5
	environment.fog_enabled = false
	environment.fog_light_color = Color(0.4, 0.48, 0.45)
	environment.fog_density = 0.0005
	environment.ssao_enabled = true
	environment.tonemap_mode = Environment.TONE_MAPPER_ACES
	var world_env := WorldEnvironment.new()
	world_env.environment = environment
	add_child(world_env)


func _spawn_player() -> void:
	var start := Vector3(12416.0, 20480.0, -4863.4)
	if OS.get_environment("L2_SPAWN") != "":
		var parts := OS.get_environment("L2_SPAWN").split(",")
		start = Vector3(float(parts[0]), float(parts[1]), float(parts[2]))
	var on_terrain := has_terrain_surface(start.x, start.y) and OS.get_environment("L2_SPAWN") == ""
	var floor_y := start.z * UNIT_SCALE
	if on_terrain:
		floor_y = maxf(terrain_height(start.x, start.y), start.z * UNIT_SCALE)
	var player := preload("res://scripts/player.gd").new()
	player.name = "Player"
	player.terrain = self
	player.position = Vector3(start.x * UNIT_SCALE, floor_y + 0.9, start.y * UNIT_SCALE)
	if OS.get_environment("L2_VIEW_YAW") != "":
		player.yaw = float(OS.get_environment("L2_VIEW_YAW"))
	add_child(player)
	print("player at ", player.position)
