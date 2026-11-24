extends Node3D

const MAP_DIR := "res://assets/maps/20_18"
# DEVLOG-107: the multi-tile world. Each tile builds under its own Node3D
# parent positioned at the tile's terrain origin (20_18 = (0,0), 20_17 =
# (0,-32768) — north of the village tile); the tile-local actor/BSP
# coordinates need no offsets. terrain_height/has_terrain_surface resolve
# the tile covering the world point. The 20_18-scoped extras (the temple,
# the road brushes, the Center_obj fix) stay on the root tile.
const TILES := [
	{"dir": "res://assets/maps/20_18", "root": true, "weather": "overcast"},
	{"dir": "res://assets/maps/20_17", "root": false, "weather": "overcast"},
	{"dir": "res://assets/maps/21_18", "root": false, "weather": "overcast"},
	{"dir": "res://assets/maps/19_18", "root": false, "weather": "overcast"},
	{"dir": "res://assets/maps/19_19", "root": false, "weather": "overcast"},
	{"dir": "res://assets/maps/18_19", "root": false, "weather": "overcast"},
	# DEVLOG-136/138/139: 20_19 = the control map (the comparison closed in
	# DEVLOG-137). The per-tile "weather" keys are the BAKE SOURCE for the
	# world cloudiness atlas now (tmp/bake_cloud_atlas.py): a tile's own
	# weather ("default" — the clear meadow sky, its region mask = the
	# bright-meadow coverage) vs the world-base overcast. The runtime has
	# NO per-tile weather: one dome for the whole map, the clouds differ
	# geographically (the user's DEVLOG-139 order), the sun works with the
	# clouds, no fog.
	{"dir": "res://assets/maps/20_19", "root": false, "weather": "default"},
]
var active_dir := MAP_DIR
var active_root := true
var tiles: Array[Dictionary] = []
# DEVLOG-110: the lamp proximity gate — 19_18 carries 1755 Light actors
# (20_18 134, 20_17 10, 21_18 2); the compatibility renderer builds the
# per-object light lists EVERY frame, so the far lamps are hidden and
# only the ones within LAMP_ACTIVE_DIST of the player stay lit.
const LAMP_ACTIVE_DIST := 250.0
var _lamps: Array[OmniLight3D] = []
var _player: Node3D = null
var _lamp_timer := 0.0
# the Engine.get_physics_frames() counter AT the player spawn — the settle
# anchor: 720 ticks measured FROM THE SPAWN, not from the settle start
# (the frames between the spawn and the settle loop carry a machine-
# dependent tick drift — the first-frame shader-compile hitch — and 12 s of
# tumbling down the descent stairs amplifies it into a different place)
var _spawn_physics_frame := -1
# DEVLOG-120: the day/night cycle (the user's directive 2026-11-21): a game
# day = 4 REAL hours (24 game hours), the night = 1 of them (6 game hours:
# 22:30..04:30). The sun rises in the east (+X) at 04:30, passes the ZENITH
# at 13:30 ("в 1-2ч дня солнце ровно над головой"), sets in the west (-X)
# at 22:30. The FULL moon rides the anti-sun (it rises in the east at
# sunset — physically consistent) and lights the night. The weather is
# OVERCAST: the sun energy capped at 2.8 (the old fixed 5.0 read too hot).
var _tod_clock := 12.0        # game hours 0..24
var _tod_rate := 1.0          # L2_TIME_SCALE multiplier (1 = real time)
var _bright_mode := false     # the L2_BRIGHT diagnostic freezes the cycle
var _last_light_tick := -1    # the 4 Hz light-direction quantization tick
var _sun: DirectionalLight3D
var _moon: DirectionalLight3D
var _moon_quad: MeshInstance3D
# DEVLOG-139/142: the world cloudiness atlas (the game-unit rect it
# covers; row 0 = the atlas south edge). Baked by tmp/bake_cloud_atlas.py
# from the tiles' weather region masks — 0 = the clear sky, 0.7 = the DE
# semi-transparent overcast. The rect extends 1500 m godot beyond the
# built world (the dome's cloud-plane distance saturates at 1500 m, so
# the low sky — the neighbor territories' weather — lands inside).
const CLOUD_ATLAS_RECT := Rect2(-215536.0, -182768.0, 431072.0, 398304.0)
var _cloud_img: Image
var _sky_dome: MeshInstance3D
var _sky_dome_mat: ShaderMaterial
var _sky_mat: ProceduralSkyMaterial
var _env_ref: Environment
const UNIT_SCALE := 0.01

var world := Node3D.new()
var terrain_width := 0
var terrain_grid_height := 0
var terrain_origin := Vector2.ZERO
var terrain_cell := Vector2(128.0, 128.0)
var terrain_heights: PackedFloat32Array
var terrain_present: PackedByteArray = PackedByteArray()
# DEVLOG-132 A/B diagnostic: L2_TERRAIN_FLATNORM=1 rebuilds the terrain with
# the OLD per-face flat normals (generate_normals()) instead of the smooth
# heightfield grid — one launch localizes whether the missing sun on the
# grass follows the normals path or the shadow map (L2_SUN_NOSHADOW).
var _terrain_flat_normals := false
var map_data := {}
var materials_data := {}
var asset_map_data := {}
var bsp_data := {}
var _mesh_cache := {}
var _shape_cache := {}
# DEVLOG-86: the foliage (vegetation) batching — actor transforms per mesh
# key rendered as one MultiMeshInstance3D, plus the trunk AABBs (the bark
# surfaces only) for the tree cylinder colliders.
var _veg_batch := {}
# DEVLOG-144: the DE village lantern plafond centers (the mesh-local AABB
# center of the DE_V_cube_deco3 surface) — the omni anchors for the
# lantern lights; keyed by the mesh key.
var _plafond_center := {}
# DEVLOG-165: derived native-floor coverage mask (client DE_V_floor02 geometry).
var _native_floor_mask: Texture2D = null
# DEVLOG-159: exact client-derived candle light positions in mesh-local
# glTF meters. Table candles = top-center of each candle's geometry island;
# door candles = the two bright wax/flame UV anchors of doordeco mapped onto
# its quad. UModel confirmed store_07/08/19/20 candle sections are empty
# (0 verts) in the client, so they are NOT invented here.
var _candle_local_positions := {
	"interior_B_delf_s:interior_B_delf_store_17": [
		Vector3(0.2753, -0.0217, 0.2871),
		Vector3(-0.2268, -0.0422, -0.2366),
	],
	"interior_B_delf_s:interior_B_delf_store_03": [
		Vector3(0.8455, -0.2605, 0.3655),
		Vector3(-0.2175, -0.2605, -0.8775),
	],
	"interior_B_delf_s:interior_B_delf_store_06": [
		Vector3(0.2807, -0.0562, 0.4187),
	],
	"interior_B_delf_s:interior_B_delf_store_09": [
		Vector3(-0.4211, -0.1047, -0.5210),
	],
	"interior_B_delf_s:interior_B_delf_store_10": [
		Vector3(0.0104, 0.1311, -0.0097),
	],
	"interior_B_delf_s:interior_B_delf_store_13": [
		Vector3(0.8455, -0.2605, 0.3655),
		Vector3(-0.2111, -0.2605, -0.8720),
	],
	"interior_B_delf_s:interior_B_delf_store_15": [
		Vector3(0.0003, 0.2063, -0.0011),
	],
	"interior_B_delf_s:interior_B_delf_store_23": [
		Vector3(-0.0420, -0.0562, 0.0195),
	],
}
# DEVLOG-147 rev4: the static mesh keys whose surfaces are ALL
# StandardMaterial3D placeholders (no staged PBR/analytic set) — they move
# to RENDER LAYER 2, lit exclusively by the lantern omnis (cull_mask = 2);
# the pool-capable ShaderMaterial surfaces stay on layer 1 lit only by the
# shader pools. Mixed keys get a per-key split (main / grey meshes).
var _placeholder_keys := {}
var _static_split := {}
# DEVLOG-148: the lantern omnis (always-on, layer-2-only) — for the shadow
# distance gate below (32 cube-shadow omnis overflow the compat shadow
# atlas: the middle lanterns' shadows were silently dropped).
var _lantern_omnis: Array[OmniLight3D] = []
# DEVLOG-162: two real shadow-casting candle omnis track the player-nearest
# candles. The shader pool skips those two indices, so nearby candle light is
# occluded by walls instead of leaking through them.
var _candle_carriers: Array[OmniLight3D] = []
# DEVLOG-163: one billboard transform per candle for the client's five-frame
# flame animation (FX_E_T flame_a01..a05).
var _candle_flame_transforms: Array[Transform3D] = []
# DEVLOG-158 rev2: the lamp frame/socket pool gain — the collar band sits
# ~0.15 m under the plafond center where the DEVLOG-151 near-field cap
# (latt <= 0.18) pins the pool; the gain lifts it for the frame clones
# ONLY (every other material keeps 1.0). L2_FRAME_POOL_GAIN overrides for
# the calibration sweep.
var _frame_pool_gain := 3.0 \
		if OS.get_environment("L2_FRAME_POOL_GAIN") == "" \
		else float(OS.get_environment("L2_FRAME_POOL_GAIN"))
# DEVLOG-150: the shadow carriers — two REAL shadow-casting omnis parked
# at the two registered lanterns nearest to the player. Their light
# replaces the pools at those two indices (lantern_shadow0/1 skip), so
# the character finally casts a shadow on the ground: a shader pool is
# pure math and cannot know about occluders, which is why the last
# iteration shipped no shadows at all. Same position/curve/energy as the
# pool => the retarget swaps are seamless; the shadow map is what changes.
var _carrier_lights: Array[OmniLight3D] = []
# DEVLOG-150: one-shot boot log for the first carrier park.
var _carrier_parked := false
# DEVLOG-150: the last applied lamp day/night factor (the carriers ride it).
var _lamp_f := 1.0
# DEVLOG-149: the lantern day/night state + the crystal-pulse materials.
var _lamp_f_prev := -1.0
var _plafond_mats: Array[Material] = []
var _plafond_t := 0.0
var _foliage_trunk := {}

# Меши, у которых пол имеет нормали, смотрящие вниз (backface culling делает их невидимыми сверху).
# Предвычислено анализатором геометрии glTF.

func _process(delta: float) -> void:
	# the day/night clock: 24 game hours per 4 real hours = 1/600 game-h
	# per real second. The L2_BRIGHT diagnostic bypasses the cycle (its
	# flat-white ambient must survive untouched).
	if not _bright_mode:
		_tod_clock = fmod(_tod_clock + delta / 600.0 * _tod_rate, 24.0)
		_update_daynight()
	# DEVLOG-149: the lantern crystal breathes (the emissive pulse — the
	# user: "кристаллы в фонарях должны хотя бы светиться, а не быть
	# статик текстурой")
	if _plafond_mats.size() > 0:
		_plafond_t += delta
		var glow := 1.35 + 0.45 * sin(_plafond_t * 1.7)
		for m in _plafond_mats:
			m.set_shader_parameter("emission_energy", glow)
	# DEVLOG-150: the shadow carriers retarget EVERY frame (two distance
	# scans over ~32 lanterns; the skip push is cached inside
	# L2ProcTex.set_lantern_shadow). The curve/energy match makes the
	# retarget invisible; only the shadow map presence changes.
	if _player != null and _carrier_lights.size() == 2:
		var lps := L2ProcTex.lantern_positions()
		var n := lps.size()
		var b0 := -1
		var b1 := -1
		var d0 := 1e12
		var d1 := 1e12
		var pp0 := _player.global_position
		for i in n:
			var dd := lps[i].distance_squared_to(pp0)
			if dd < d0:
				d1 = d0
				b1 = b0
				d0 = dd
				b0 = i
			elif dd < d1:
				d1 = dd
				b1 = i
		var c0: OmniLight3D = _carrier_lights[0]
		var c1: OmniLight3D = _carrier_lights[1]
		if b0 >= 0:
			c0.position = lps[b0]
			c0.light_energy = 10.0 * _lamp_f
			if not _carrier_parked:
				_carrier_parked = true
				print("shadow carriers parked at ", lps[b0],
						" and ", lps[b1] if b1 >= 0 else Vector3.ZERO)
		else:
			c0.light_energy = 0.0
		if b1 >= 0:
			c1.position = lps[b1]
			c1.light_energy = 10.0 * _lamp_f
		else:
			c1.light_energy = 0.0
		L2ProcTex.set_lantern_shadow(b0, b1)
	# DEVLOG-162: candle carriers — same nearest-two swap, warm and short
	# range. Their shadow maps occlude walls; the shader pool skips them.
	if _player != null and _candle_carriers.size() == 2:
		var cps := L2ProcTex.candle_positions()
		var cb0 := -1
		var cb1 := -1
		var cd0 := 1e12
		var cd1 := 1e12
		var ppc := _player.global_position
		for i in cps.size():
			var dd := cps[i].distance_squared_to(ppc)
			if dd < cd0:
				cd1 = cd0
				cb1 = cb0
				cd0 = dd
				cb0 = i
			elif dd < cd1:
				cd1 = dd
				cb1 = i
		var cc0: OmniLight3D = _candle_carriers[0]
		var cc1: OmniLight3D = _candle_carriers[1]
		if cb0 >= 0:
			cc0.position = cps[cb0]
			cc0.light_energy = 0.35
		else:
			cc0.light_energy = 0.0
		if cb1 >= 0:
			cc1.position = cps[cb1]
			cc1.light_energy = 0.35
		else:
			cc1.light_energy = 0.0
		L2ProcTex.set_candle_shadow(cb0, cb1)
	_lamp_timer += delta
	if _lamp_timer < 0.5 or _player == null:
		return
	_lamp_timer = 0.0
	var pp := _player.global_position
	var d2 := LAMP_ACTIVE_DIST * LAMP_ACTIVE_DIST
	for lamp in _lamps:
		lamp.visible = lamp.global_position.distance_squared_to(pp) < d2
	# DEVLOG-151: the lantern shadow distance gate REMOVED — the lantern
	# omnis are shadowless (see the creation comment); the carriers own
	# the character shadows with guaranteed atlas slots.


func _ready() -> void:
	var started := Time.get_ticks_msec()
	_load_data()
	add_child(world)
	_build_environment()
	for t in tiles:
		_activate(t)
		_build_terrain()
		_build_meshes()
		_build_bsp()
		_build_lights()
		print("tile %s built (origin %s)" % [t["dir"], t["origin"]])
	_activate(tiles[0])
	print("world built in ", (Time.get_ticks_msec() - started) / 1000.0, " s")
	# DEVLOG-147: every tile's meshes registered their lantern plafonds by
	# now — push the pool uniforms into every tracked PBR material (the
	# cache originals, the per-BSP duplicates; apply_lanterns prints the
	# count).
	L2ProcTex.apply_lanterns()
	L2ProcTex.apply_candles()
	# DEVLOG-162: two nearest candles become real shadowed omnis. Their pool
	# indices are skipped in l2_surface_pbr, so the warm light near the player
	# is occluded by walls instead of leaking through them.
	if L2ProcTex.candles_size() > 0 and OS.get_environment("L2_NO_CANDLE_CARRIERS") == "":
		for i in range(2):
			var cl := OmniLight3D.new()
			cl.light_color = Color(1.0, 0.58, 0.22)
			cl.light_energy = 0.35
			cl.omni_range = 2.5
			cl.omni_attenuation = 2.0
			cl.shadow_enabled = OS.get_environment("L2_NO_CANDLE_SHADOW") == ""
			cl.light_cull_mask = 3
			world.add_child(cl)
			_candle_carriers.append(cl)
		print("candle carriers: ", _candle_carriers.size(), " shadowed omnis ready")
	_build_candle_flames()
	for m in L2ProcTex.tracked_materials():
		if m.has_meta("l2_plafond"):
			_plafond_mats.append(m)
	print("lantern crystals: ", _plafond_mats.size(), " glass materials (the emissive pulse)")
	# DEVLOG-150: the two shadow carriers (see the state comment + _process).
	# omni_attenuation = 2.0 = the pool's curve (Godot's
	# get_omni_attenuation decay 2) — pool and omni are one function.
	# L2_NO_CARRIER_SHADOW=1 = the numeric A/B diagnostic (the shadow
	# pixel-diff against the same camera; the normal scene is untouched).
	for ci in 2:
		var carrier := OmniLight3D.new()
		carrier.light_color = Color(0.6, 0.75, 1.0)
		carrier.omni_range = 22.0
		carrier.omni_attenuation = 2.0
		carrier.shadow_enabled = OS.get_environment("L2_NO_CARRIER_SHADOW") == ""
		# DEVLOG-151 rev2: the specular ZERO — 0.15 still read as "блики от
		# фонарей" at the plaza camera angles (the user's verdict).
		carrier.light_specular = 0.0
		carrier.light_cull_mask = 3  # layers 1|2 — the PBR surfaces AND the placeholders
		carrier.light_energy = 0.0
		world.add_child(carrier)
		_carrier_lights.append(carrier)
	print("shadow carriers: 2 omnis ready (the nearest-lantern tracking)")
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
	if OS.get_environment("L2_TRACE_RAY") != "":
		_trace_ray_flow()
	if OS.get_environment("L2_TRACE_COLOR") != "":
		_trace_color_flow()
	if OS.get_environment("L2_LIGHT_CAP_AUDIT") != "":
		_light_cap_audit()
	if OS.get_environment("L2_SCREENSHOT") != "":
		_screenshot_flow()
	if OS.get_environment("L2_BURST") != "":
		_burst_flow()


## Region tracer: L2_TRACE_BOX="x1,y1,x2,y2" casts rays from the camera
## through every 8th pixel of that screen rect and reports the hit mesh,
## face, surface and resolved texture — identifies any suspect region
## (flat-color patches, missing geometry) without eyeballing.
func _trace_box_flow() -> void:
	for i in 10:
		await get_tree().process_frame
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
			elif col is Node:
				owner_name = "<%s>%s" % [(col as Node).get_class(), (col as Node).name]
			elif col != null:
				owner_name = "<non-node>"
			var fid := int(hit.get("face_index", -1))
			var k := owner_name
			counts[k] = counts.get(k, 0) + 1
			if counts[k] <= 400:
				var surf := _surface_for_face(owner_name, fid)
				print("TRACE_BOX px(%d,%d) %s face=%d surf=%d tex=%s n=%v" % [
					px, py, owner_name, fid, surf,
					_texture_for_surface(owner_name, surf), hit.get("normal")])
	print("TRACE_BOX totals:", counts)
	get_tree().quit()


## Single-ray probe: L2_TRACE_RAY="ux1,uy1,z1,ux2,uy2,z2" (game units: UE x,
## UE y, UE height) casts one ray (up to 8 hits stepping past each) and
## prints the hits' mesh, face, surface texture, position, normal. Locates
## any suspect wall (a plug, a stray cap) to the exact face.
func _trace_ray_flow() -> void:
	for i in 10:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var p := OS.get_environment("L2_TRACE_RAY").split(",")
	# Godot axes: X = UE x, Y = UE height (z), Z = UE y (the level BSP
	# convention — every builder emits [x, z, y] * SCALE)
	var from := Vector3(float(p[0]) * UNIT_SCALE, float(p[2]) * UNIT_SCALE,
			float(p[1]) * UNIT_SCALE)
	var to := Vector3(float(p[3]) * UNIT_SCALE, float(p[5]) * UNIT_SCALE,
			float(p[4]) * UNIT_SCALE)
	var space := get_world_3d().direct_space_state
	var cur := from
	for n in range(8):
		var q := PhysicsRayQueryParameters3D.create(cur, to)
		var hit := space.intersect_ray(q)
		if hit.is_empty():
			print("TRACE_RAY %d: NO-HIT (from %v to %v)" % [n, cur, to])
			break
		var col = hit.get("collider")
		var owner_name := "unknown"
		if col is Node and (col as Node).has_meta("mesh_key"):
			owner_name = str((col as Node).get_meta("mesh_key"))
		elif col is Node:
			owner_name = "<%s>%s" % [(col as Node).get_class(), (col as Node).name]
		var fid := int(hit.get("face_index", -1))
		var surf := _surface_for_face(owner_name, fid)
		var pos: Vector3 = hit.get("position")
		print("TRACE_RAY %d: %s face=%d surf=%d tex=%s pos=g(%.0f,%.0f,%.0f) n=%v" % [
			n, owner_name, fid, surf, _texture_for_surface(owner_name, surf),
			pos.x / UNIT_SCALE, pos.y / UNIT_SCALE, pos.z / UNIT_SCALE,
			hit.get("normal")])
		cur = pos + (to - from).normalized() * 0.05
	get_tree().quit()


## Green-pixel tracer: L2_GREEN_TRACE=1 renders one frame, finds green-dominant
## pixels, casts rays from the camera through them and reports the exact hit —
## mesh key, face index, resolved surface texture. Settles "what is this green
## surface" without any eyeballing.
func _green_trace_flow() -> void:
	for i in 10:
		await get_tree().process_frame
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


## Color tracer: L2_TRACE_COLOR="r,g,b,tol" finds pixels near that color and
## reports what they hit — settles "what surface is this patch" numerically.
func _trace_color_flow() -> void:
	for i in 10:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var cam := get_viewport().get_camera_3d()
	if cam == null or img == null:
		print("TRACE_COLOR: no camera/image")
		get_tree().quit()
		return
	var p := OS.get_environment("L2_TRACE_COLOR").split(",")
	var target := Color(float(p[0]), float(p[1]), float(p[2]))
	var tol := float(p[3]) if p.size() > 3 else 0.06
	var w := img.get_width()
	var h := img.get_height()
	var space := get_world_3d().direct_space_state
	var counts := {}
	for py in range(0, h, 6):
		for px in range(0, w, 6):
			var c := img.get_pixel(px, py)
			if absf(c.r - target.r) > tol or absf(c.g - target.g) > tol \
					or absf(c.b - target.b) > tol:
				continue
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
			elif col is Node:
				owner_name = "<%s>" % (col as Node).get_class()
			var fid := int(hit.get("face_index", -1))
			var k := owner_name
			counts[k] = counts.get(k, 0) + 1
			if counts[k] <= 3:
				var surf := _surface_for_face(owner_name, fid)
				print("TRACE_COLOR px(%d,%d) %s face=%d surf=%d tex=%s pos=%v n=%v" % [
					px, py, owner_name, fid, surf, _texture_for_surface(owner_name, surf),
					hit.get("position"), hit.get("normal")])
	print("TRACE_COLOR totals:", counts)
	get_tree().quit()


## DEVLOG-153: load the BSP collision mesh for the trace helpers (the BSP
## colliders carry mesh_key "BSP:<Polys>" / "LevelBSP" but live outside
## asset_map, so _get_mesh cannot see them). Same _D preference as the
## builder — the collision trimesh comes from the rendered variant.
var _bsp_trace_mesh_cache := {}

func _bsp_trace_mesh(mesh_key: String) -> Mesh:
	if _bsp_trace_mesh_cache.has(mesh_key):
		return _bsp_trace_mesh_cache[mesh_key]
	var gp := ""
	if mesh_key.begins_with("BSP:"):
		gp = "%s/meshes_bsp/BSP_%s.gltf" % [active_dir, mesh_key.substr(4)]
	elif mesh_key == "LevelBSP":
		gp = "%s/meshes_bsp/LevelBSP.gltf" % active_dir
	var mesh: Mesh = null
	if gp != "":
		var gdp := gp.replace(".gltf", "_D.gltf")
		if ResourceLoader.exists(gdp):
			gp = gdp
		if ResourceLoader.exists(gp):
			var scene: PackedScene = load(gp)
			if scene != null:
				var root := scene.instantiate()
				for c in root.get_children():
					if c is MeshInstance3D:
						mesh = c.mesh
						break
				root.free()
	_bsp_trace_mesh_cache[mesh_key] = mesh
	return mesh


func _surface_for_face(mesh_key: String, fid: int) -> int:
	var mesh := _get_mesh(mesh_key)
	if mesh == null:
		mesh = _bsp_trace_mesh(mesh_key)
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
	# DEVLOG-153: the BSP brush / LevelBSP colliders are NOT in asset_map —
	# the old helper returned surf=-1 tex=? for EVERY BSP hit, which masqueraded
	# as "lost surf records" in the DEVLOG-148 plaza diagnosis. Map them here.
	if mesh_key.begins_with("BSP:"):
		var polys := mesh_key.substr(4)
		for br in bsp_data.get("brushes", []):
			if br.get("polys") == polys:
				for f in br.get("faces", []):
					if f.get("prim") == surf and f.get("tex") != null:
						return "%s:%s" % [f["tex"][0], f["tex"][1]]
		return "?"
	if mesh_key == "LevelBSP":
		var lb := _load_json(active_dir + "/levelbsp.json")
		var ss: Array = lb.get("surfaces", [])
		if surf < ss.size() and ss[surf].get("tex") != null:
			return "%s:%s" % [ss[surf]["tex"][0], ss[surf]["tex"][1]]
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
			if OS.get_environment("L2_FLOOR_GRID_INTERIOR") != "":
				cur_y = -44.5
			if OS.get_environment("L2_FLOOR_GRID_START_Y") != "":
				cur_y = float(OS.get_environment("L2_FLOOR_GRID_START_Y"))
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


## The temporal-flicker capture (the white-flash diagnostic, 2026-11-15):
## L2_BURST=<seconds> + L2_BURST_DIR=<abs dir> walks the character
## (L2_AUTORUN=1) and saves a frame every ~0.1 s for N seconds — the
## analysis finds the flash frames and the flipped pixels.
## Wait until exactly N physics ticks of game time have passed SINCE THE
## SPAWN (anchored at _spawn_physics_frame, not at the settle start — see
## the member comment). Awaiting RENDER frames made the game time depend
## on the renderer speed: 90 awaited frames = 720 ticks on llvmpipe (the
## 8-tick catch-up cap) but ~90 on a fast renderer — the descent slide and
## the framing varied with the machine (DEVLOG-110/111). The last frame
## may overshoot by < 8 ticks (the max_physics_steps_per_frame cap,
## default 8 — do NOT raise it: a higher cap trades exactness for speed).
func _await_settle_ticks(ticks: int) -> void:
	var base := _spawn_physics_frame
	if base < 0:
		base = Engine.get_physics_frames()
	var target := base + ticks
	while Engine.get_physics_frames() < target:
		await get_tree().physics_frame


func _burst_flow() -> void:
	var d := OS.get_environment("L2_BURST_DIR")
	var secs := float(OS.get_environment("L2_BURST"))
	await _await_settle_ticks(720)
	var t := 0.0
	while t < secs:
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(
				d.path_join("burst_%06.1f.png" % t))
		await get_tree().create_timer(0.1).timeout
		t += 0.1
	print("BURST done: ", t, " s")
	get_tree().quit()


func _screenshot_flow() -> void:
	var d := OS.get_environment("L2_SCREENSHOT")
	print("SCREENSHOT_FLOW ENTERED, dir=", d, " t=", Time.get_ticks_msec())
	for i in 10:
		await get_tree().process_frame
	# settle: the spawn falls ~1 m to the floor while the third-person camera
	# (rigidly attached to the character) follows — the state after N physics
	# TICKS is renderer-independent (DEVLOG-111). Default 720 ticks = 12 s of
	# game time = exactly what the llvmpipe-era 90-awaited-frame settle gave
	# (90 frames x the 8-tick catch-up cap), so the standing baselines keep
	# their state. L2_SETTLE_TICKS overrides (seconds of game time = /60).
	var settle_ticks := 720
	if OS.get_environment("L2_SETTLE_TICKS") != "":
		settle_ticks = int(OS.get_environment("L2_SETTLE_TICKS"))
	await _await_settle_ticks(settle_ticks)
	print("SCREENSHOT_FLOW settled (%d physics ticks) t=%d" % [settle_ticks, Time.get_ticks_msec()])
	await RenderingServer.frame_post_draw
	var cam = get_viewport().get_camera_3d()
	print("DEBUG camera global_pos: ", cam.global_position if cam else "no camera")
	print("DEBUG camera rotation: ", cam.global_rotation if cam else "no camera")
	get_viewport().get_texture().get_image().save_png(d + "/shot1.png")
	print("SCREENSHOT_FLOW shot1 SAVED t=", Time.get_ticks_msec())
	for i in 5:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(d + "/shot2.png")
	print("SCREENSHOT_FLOW shot2 SAVED t=", Time.get_ticks_msec())
	get_tree().quit()


func _load_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null: return {}
	var r = JSON.parse_string(f.get_as_text())
	return r if r is Dictionary else {}


func _load_data() -> void:
	tiles.clear()
	# L2_TILES="20_18,20_17" — the diagnostic subset (the cost attribution)
	var only := OS.get_environment("L2_TILES")
	for t in TILES:
		if only != "" and not ((t["dir"] as String).get_file() in only.split(",")):
			continue
		var dir: String = t["dir"]
		var td := _load_json(dir + "/terrain/terrain.json")
		var tile := {
			"dir": dir, "root": t["root"],
			# DEVLOG-136: the per-tile weather survives the rebuild
			"weather": str(t.get("weather", "overcast")),
			"map_data": _load_json(dir + "/map.json"),
			"materials": _load_json(dir + "/materials.json"),
			"asset_map": _load_json(dir + "/asset_map.json"),
			"bsp": _load_json(dir + "/bsp.json"),
			"width": int(td["source_height_size"][0]),
			"grid": int(td["source_height_size"][1]),
			"origin": Vector2(float(td["origin_game_xy"][0]), float(td["origin_game_xy"][1])),
			"cell": Vector2(float(td["cell_size_game_xy"][0]), float(td["cell_size_game_xy"][1])),
		}
		var stride: int = int(tile["width"]) + 1
		var f := FileAccess.open(dir + "/terrain/height_world_f32.raw", FileAccess.READ)
		if f: tile["heights"] = f.get_buffer(stride * stride * 4).to_float32_array()
		var pf := FileAccess.open(dir + "/terrain/surface_present_u8.raw", FileAccess.READ)
		if pf: tile["present"] = pf.get_buffer(int(tile["width"]) * int(tile["grid"]))
		tiles.append(tile)
	_activate(tiles[0])


## Point the builder globals at one tile (the per-tile builders read the
## globals; the debug flows and the spawn stay on the root tile).
func _activate(tile: Dictionary) -> void:
	map_data = tile["map_data"]
	materials_data = tile["materials"]
	asset_map_data = tile["asset_map"]
	bsp_data = tile["bsp"]
	terrain_width = int(tile["width"])
	terrain_grid_height = int(tile["grid"])
	terrain_origin = tile["origin"]
	terrain_cell = tile["cell"]
	terrain_heights = tile["heights"]
	terrain_present = tile["present"]
	active_dir = tile["dir"]
	active_root = bool(tile["root"])


func _height_at(tile: Dictionary, x: int, y: int) -> float:
	var th: PackedFloat32Array = tile["heights"]
	var w: int = int(tile["width"])
	return th[clampi(y, 0, int(tile["grid"])) * (w + 1) + clampi(x, 0, w)]


## The tile whose terrain cell grid covers the world point, or the root
## tile as the out-of-map fallback (the legacy clamp behavior).
func _tile_at(gx: float, gy: float) -> Dictionary:
	for tile in tiles:
		var o: Vector2 = tile["origin"]
		var ext: Vector2 = Vector2(int(tile["width"]), int(tile["grid"])) * (tile["cell"] as Vector2)
		if gx >= o.x and gy >= o.y and gx < o.x + ext.x and gy < o.y + ext.y:
			return tile
	return tiles[0]


## DEVLOG-139: the world cloudiness at a game point — the bilinear read of
## the world atlas (row 0 = the atlas south edge). Drives the sun light;
## the dome shader draws the SAME field, so the sky and the light agree
## and no region switch can ever disagree with what the player sees.
func _cloud_at(gx: float, gy: float) -> float:
	if _cloud_img == null:
		return 1.0
	var w := _cloud_img.get_width()
	var h := _cloud_img.get_height()
	var fx := (gx - CLOUD_ATLAS_RECT.position.x) / CLOUD_ATLAS_RECT.size.x \
			* float(w) - 0.5
	var fy := (gy - CLOUD_ATLAS_RECT.position.y) / CLOUD_ATLAS_RECT.size.y \
			* float(h) - 0.5
	var x0 := int(floor(fx))
	var y0 := int(floor(fy))
	var tx := fx - float(x0)
	var ty := fy - float(y0)
	var v00 := _cloud_img.get_pixel(clampi(x0, 0, w - 1), clampi(y0, 0, h - 1)).r
	var v10 := _cloud_img.get_pixel(clampi(x0 + 1, 0, w - 1), clampi(y0, 0, h - 1)).r
	var v01 := _cloud_img.get_pixel(clampi(x0, 0, w - 1), clampi(y0 + 1, 0, h - 1)).r
	var v11 := _cloud_img.get_pixel(clampi(x0 + 1, 0, w - 1), clampi(y0 + 1, 0, h - 1)).r
	return lerpf(lerpf(v00, v10, tx), lerpf(v01, v11, tx), ty)


func terrain_height(gx: float, gy: float) -> float:
	var tile := _tile_at(gx, gy)
	var o: Vector2 = tile["origin"]
	var cw: float = (tile["cell"] as Vector2).x
	var ch: float = (tile["cell"] as Vector2).y
	var lx := clampf((gx - o.x) / cw, 0.0, float(int(tile["width"])) - 1.0)
	var ly := clampf((gy - o.y) / ch, 0.0, float(int(tile["grid"])) - 1.0)
	var ix := int(lx)
	var iy := int(ly)
	var fx := lx - ix
	var fy := ly - iy
	var a := _height_at(tile, ix, iy)
	var b := _height_at(tile, ix + 1, iy)
	var c := _height_at(tile, ix, iy + 1)
	var d := _height_at(tile, ix + 1, iy + 1)
	return a + fx * (b - a) + fy * (c - a) + fx * fy * (a - b - c + d)


func has_terrain_surface(gx: float, gy: float) -> bool:
	var tile := _tile_at(gx, gy)
	var o: Vector2 = tile["origin"]
	var cw: float = (tile["cell"] as Vector2).x
	var ch: float = (tile["cell"] as Vector2).y
	var cx := int((gx - o.x) / cw)
	var cy := int((gy - o.y) / ch)
	var w: int = int(tile["width"])
	var g: int = int(tile["grid"])
	if cx < 0 or cy < 0 or cx >= w or cy >= g:
		return false
	var present: PackedByteArray = tile["present"]
	if present.size() == w * g:
		return present[cy * w + cx] == 1
	return true


## Find a staged texture PNG by package/object with the case fallbacks
## used by the staging pipeline (Linux file names are lowercase).
func _find_texture_path(pkg: String, obj: String) -> String:
	if pkg == "" or obj == "":
		return ""
	for cand in ([pkg, pkg.to_lower()]):
		var tp := "%s/textures/%s/Texture/%s.png" % [active_dir, cand, obj]
		if FileAccess.file_exists(tp):
			return tp
		tp = "%s/textures/%s/Texture/%s.png" % [active_dir, cand, obj.to_lower()]
		if FileAccess.file_exists(tp):
			return tp
	return ""


func _build_terrain() -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var stride := terrain_width + 1
	var ph := -8000.0
	var quads := 0
	# The actor locations in map.json are WORLD-frame for every tile (the
	# extractor normalizes them), and the terrain heights are absolute Z —
	# so NOTHING is parent-offset: the terrain mesh applies its own
	# terrain.json origin (world), the actors keep their raw positions.
	# (DEVLOG-107's tile parents double-offset the statics — the 19_18
	# "floating over the sea" bug, DEVLOG-110.)
	var ox: float = terrain_origin.x * UNIT_SCALE
	var oz: float = terrain_origin.y * UNIT_SCALE
	var cw: float = terrain_cell.x * UNIT_SCALE
	var ch: float = terrain_cell.y * UNIT_SCALE
	var inv_w := 1.0 / float(terrain_width)
	# DEVLOG-138: ONE terrain render path for every tile and every weather
	# region — the smooth ngrid normals (DEVLOG-130), the current terrain
	# shader, the POM heights. The DEVLOG-136 control split (the flat
	# normals + the HEAD shader on 20_19) is retired: the weather regions
	# differ ONLY in the sky/fog now, so the grass look cannot change at
	# the borders. L2_TERRAIN_FLATNORM=1 stays the A/B diagnostic.
	_terrain_flat_normals = OS.get_environment("L2_TERRAIN_FLATNORM") != ""
	# DEVLOG-130 (the user's "горы стали детализированнее, но днём плёнка
	# увеличилась"): SMOOTH analytic vertex normals. The client smooth-shades
	# its terrain (vertex lighting on the heightfield); generate_normals()
	# on the unindexed triangles produced per-face flat normals, and under
	# the moving day/night sun the adjacent facets diverge by up to 67%
	# brightness (the measured p95 on the northern mountain slopes at
	# 15:24) = the shimmering film in daylight. At the old static
	# south-east sun the north faces sat in ambient only, so the faceting
	# was invisible — the dynamic sun exposed it.
	# N = normalize(-dz/dx, 1, -dz/dy) per heightfield vertex; the heights
	# and the cells are both game units so the scale cancels.
	var ngrid := PackedVector3Array()
	ngrid.resize(stride * stride)
	for gy in range(stride):
		for gx in range(stride):
			var hl: float = terrain_heights[gy * stride + maxi(gx - 1, 0)]
			var hr: float = terrain_heights[gy * stride + mini(gx + 1, stride - 1)]
			var hu: float = terrain_heights[maxi(gy - 1, 0) * stride + gx]
			var hd: float = terrain_heights[mini(gy + 1, stride - 1) * stride + gx]
			# the cut cells hold placeholder heights (z < -8000); their
			# gradients poison the hole borders — clamp the slope (the
			# statics cover the cut)
			var dzdx: float = clampf((hr - hl) / (2.0 * terrain_cell.x), -4.0, 4.0)
			var dzdy: float = clampf((hd - hu) / (2.0 * terrain_cell.y), -4.0, 4.0)
			ngrid[gy * stride + gx] = Vector3(-dzdx, 1.0, -dzdy).normalized()
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
			# the smooth corner normals, indexed like cs/us: (x,y) (x+1,y)
			# (x+1,y+1) (x,y+1)
			var ns: Array[Vector3] = [
				ngrid[i00],
				ngrid[i00 + 1],
				ngrid[i00 + stride + 1],
				ngrid[i00 + stride],
			]
			# DEVLOG-137 (the border shot): the old order (0,2,1)/(0,3,2)
			# wound the triangles so their FRONT faces pointed DOWN (the
			# proof: generate_normals() on the 20_19 tile printed
			# first=(0.02, -0.997, 0.075) — down). With cull_disabled Godot
			# flips the normal for the back-face fragments, so the pre-130
			# generate_normals() DOWN normals were flipped UP and the terrain
			# was LIT; the DEVLOG-130 explicit UP normals on the same
			# down-wound triangles got flipped DOWN for every visible
			# fragment -> dot(NORMAL, LIGHT) <= 0 -> no sun, no moon, flat
			# ambient only (the exact black-ground picture since DEVLOG-130).
			# The winding now points the front faces UP so the smooth UP
			# normals are used as-is (no flip dependency; the POM's vt.z is
			# abs()-guarded so the facing flip changes nothing there).
			if real.size() == 4:
				_emit_tri(st, cs[0], cs[1], cs[2], us[0], us[1], us[2],
						ns[0], ns[1], ns[2])
				_emit_tri(st, cs[0], cs[2], cs[3], us[0], us[2], us[3],
						ns[0], ns[2], ns[3])
			else:
				_emit_tri(st, cs[real[0]], cs[real[1]], cs[real[2]],
						us[real[0]], us[real[1]], us[real[2]],
						ns[real[0]], ns[real[1]], ns[real[2]])
	var mat := ShaderMaterial.new()
	# DEVLOG-136: the per-tile weather picks the terrain shader — the
	# default-weather tiles run the HEAD default shader (no POM), the
	# overcast DE territory runs the current one. L2_TERRAIN_LIGHTDEBUG
	# (the diagnostic canvas) keeps the highest priority.
	if OS.get_environment("L2_TERRAIN_LIGHTDEBUG") != "":
		mat.shader = load("res://assets/shaders/terrain_lightdebug.gdshader") as Shader
		print("TERRAIN MATERIAL [%s]: LIGHTDEBUG canvas" % active_dir)
	else:
		mat.shader = load("res://scripts/terrain.gdshader") as Shader
	print("TERRAIN MATERIAL [%s]: shader=%s" % [active_dir,
			mat.shader.resource_path if mat.shader else "NULL"])
	# Original 8 terrain color layers with per-layer masks and UV scales
	# from terrain.json "layers" (verified mappings by the strict pipeline).
	var layers: Array = map_data.get("terrain_layers", [])
	var td2 := _load_json(active_dir + "/terrain/terrain.json")
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
	# DEVLOG-129: the terrain SPOM — the height ARRAY (8 layers, 512x512,
	# the height = the texgen albedo's A channel, low-frequency per the
	# DEVLOG-89 lesson) + the per-layer uv scales for the dominant-layer
	# march. A missing set falls back to the flat 0.5 gray.
	# DEVLOG-138: loaded for EVERY tile (the DEVLOG-136 control skip is
	# retired — one terrain path everywhere).
	var himgs: Array = []
	var ls: PackedVector2Array = PackedVector2Array()
	for li in range(8):
		var l: Dictionary = layers[li] if li < layers.size() else {}
		var tex: Dictionary = l.get("texture", {})
		var img := Image.create(512, 512, false, Image.FORMAT_RGBA8)
		img.fill(Color(0.5, 0.5, 0.5, 0.5))
		var hp := _find_texture_path(tex.get("package", ""), tex.get("object", ""))
		if hp != "":
			var ap := hp.get_basename() + ".pbr_albedo.png"
			var himg := Image.new()
			if FileAccess.file_exists(ap) and himg.load(ap) == OK:
				img = himg
		if img.get_width() != 512 or img.get_height() != 512:
			img.resize(512, 512, Image.INTERPOLATE_BILINEAR)
		if img.get_format() != Image.FORMAT_RGBA8:
			img.convert(Image.FORMAT_RGBA8)
		himgs.append(img)
		var sc: Array = l.get("scale", [128.0, 128.0, 76.0])
		ls.append(Vector2(16384.0 / float(sc[0]), 16384.0 / float(sc[1])))
	var harr := Texture2DArray.new()
	harr.create_from_images(himgs)
	mat.set_shader_parameter("layer_heights", harr)
	mat.set_shader_parameter("lscales", ls)
	mat.set_shader_parameter("do_debug",
			1.0 if OS.get_environment("L2_TERRAIN_DEBUG") == "uv" else 0.0)
	if OS.get_environment("L2_TERRAIN_DEBUG") != "":
		for li in range(8):
			var t = mat.get_shader_parameter("layer_%d_texture" % li)
			var s = mat.get_shader_parameter("layer_%d_uv_scale" % li)
			print("TERRAIN LAYER %d: tex=%s scale=%s" % [li, t.resource_path if t else "NONE", s])
	st.set_material(mat)
	# the normals come from the ngrid (set per corner in _emit_tri) —
	# generate_normals() here would overwrite them with per-face flat ones.
	# The L2_TERRAIN_FLATNORM A/B restores that old path explicitly.
	if _terrain_flat_normals:
		st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	# DEVLOG-135: the runtime proof of the terrain mesh's normal state (the
	# night shot shows the terrain receiving NO light at all — the classic
	# zero-normal signature: NdotL=0 kills the sun AND the moon, and the
	# normal-dependent ambient too).
	var _arr: Array = mi.mesh.surface_get_arrays(0)
	var _nrm: PackedVector3Array = _arr[Mesh.ARRAY_NORMAL]
	if _nrm != null and _nrm.size() > 0:
		var _bad := 0
		for _i in range(_nrm.size()):
			if _nrm[_i].length() < 0.5:
				_bad += 1
		print("TERRAIN NORMALS [%s]: %d normals, degenerate(<0.5)=%d, first=%s" % [
				active_dir, _nrm.size(), _bad, str(_nrm[0])])
	else:
		print("TERRAIN NORMALS [%s]: NO NORMAL ARRAY (fmt=%d)" % [
				active_dir, mi.mesh.surface_get_format(0)])
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


## Emit one terrain triangle. Normals come from the smooth heightfield
## ngrid (DEVLOG-130) and are set per corner here.
func _emit_tri(st: SurfaceTool, p1: Vector3, p2: Vector3, p3: Vector3,
		uv1: Vector2, uv2: Vector2, uv3: Vector2,
		n1: Vector3, n2: Vector3, n3: Vector3) -> void:
	# DEVLOG-130: the smooth heightfield normals are set per corner (the
	# generate_normals() call below was removed — on the unindexed triangles
	# it produced per-face flat normals = the facet mosaic under the moving
	# sun; see the ngrid block in _build_terrain). L2_TERRAIN_FLATNORM=1
	# (the DEVLOG-132 A/B) keeps the old flat-normal path instead.
	if not _terrain_flat_normals:
		st.set_normal(n1)
	st.set_uv(uv1); st.add_vertex(p1)
	if not _terrain_flat_normals:
		st.set_normal(n2)
	st.set_uv(uv2); st.add_vertex(p2)
	if not _terrain_flat_normals:
		st.set_normal(n3)
	st.set_uv(uv3); st.add_vertex(p3)


## The clean-room wide road over the bridge span (the user's request:
## the bridge = whole, wide, ONE layer, per the live screenshots). The
## profile = the Obj01 slab's own map-data profile widened to the full
## road width; the center band = the carpet (capet01), the side bands =
## the cobble (DE_V_floor02); the low rails at the edges; flush.
## The level BSP geometry (Brush -> Model -> Polys, engine RE 2026-11-12:
## the Polys reference is a compact object index inside the Model blob; see
## tools/l2strict/bsp2.py). Placed like static meshes: game (x, y, z) ->
## godot (x, z-up->y, y-width->z) * 0.01, no rotation (every 20_18 brush
## has Rotation 0). Collision = full trimesh with backface.
## Textures (RE 2026-11-12, fnd_13/fnd_14): the level Model's FBspSurf
## records carry the per-face material (surf +0x00 objref; the L2 compact
## decoder in Core.dll negates the FULL magnitude) and map to brush polys by
## (owner Brush, iBrushPoly = raw poly index). bsp2 writes per-face "tex"
## and the prim index into bsp.json; faces without a surf keep the neutral
## stone placeholder.
func _bsp_material(tex: Array, cache: Dictionary, texel_uvs: bool = true,
		two_sided: bool = true) -> Material:
	var key := "%s:%s|%s|%s" % [tex[0], tex[1], "t" if texel_uvs else "n",
			"2s" if two_sided else "1s"]
	if cache.has(key):
		return cache[key]
	# MODERN-PORT RULE: procedural clean-room shader first — no PNG in the
	# render path for the road materials. The VILLAGE BSP layers carry raw
	# texel UVs (uv_is_texels=true); the TEMPLE BSP carries the client's
	# baked section-stream UVs = final tile coordinates (DEVLOG-82) —
	# texel_uvs=false, no UV rescaling anywhere.
	# The client renders BSP faces one-sided unless the section is TwoSided
	# (UE2 backface culling; DEVLOG-82 rev2) — cull_back per surface. The
	# L2ProcTex cache is SHARED with the statics: duplicate before mutating.
	var pm := L2ProcTex.material_for(tex[0], tex[1], texel_uvs)
	if pm != null:
		var dup: Material = pm.duplicate()
		if dup is ShaderMaterial:
			(dup as ShaderMaterial).set_shader_parameter("cull_back", not two_sided)
			# DEVLOG-165/171: the derived floor mask is kept for future A/B,
			# but DISABLED by default — it opened holes at house edges and
			# let the central grate show through interiors. The real fix is
			# source-level BSP floor unification (MODERNIZATION_2026 Phase 1).
			if tex[1] == "DE_V_floor01" \
					and OS.get_environment("L2_USE_FLOOR_MASK") != "":
				if _native_floor_mask == null:
					_native_floor_mask = load("res://assets/maps/20_18/textures/oren_dev_t/native_floor_mask.png")
				if _native_floor_mask != null:
					(dup as ShaderMaterial).set_shader_parameter("native_floor_mask", _native_floor_mask)
					(dup as ShaderMaterial).set_shader_parameter("use_native_floor_mask", 1.0)
			# DEVLOG-147: the duplicate must be tracked too — it holds only
			# the parameters set before it was made, and the lantern push
			# happens at the end of _ready (rev2: the BSP floors — all the
			# village roads/plaza — missed the pools in rev1)
			L2ProcTex.track_pbr_material(dup as ShaderMaterial)
		cache[key] = dup
		return dup
	var m := StandardMaterial3D.new()
	var tp := _find_texture_path(tex[0], tex[1])
	if tp != "":
		var img := Image.new()
		if img.load(tp) == OK:
			m.albedo_texture = ImageTexture.create_from_image(img)
			if texel_uvs:
				# Texel UVs (1 texel per world unit): scale by 1/texture size.
				m.uv1_scale = Vector3(1.0 / img.get_width(), 1.0 / img.get_height(), 1.0)
			# else: the UVs are already the client's final tile coordinates —
			# pass through unchanged.
		else:
			print("bsp: texture failed to load ", tp)
	else:
		print("bsp: texture not staged ", key)
	m.roughness = 0.95
	m.cull_mode = StandardMaterial3D.CULL_DISABLED if two_sided else StandardMaterial3D.CULL_BACK
	cache[key] = m
	return m

func _bsp_grey() -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(1.0, 0.1, 0.9) if OS.get_environment("L2_GREY_DEBUG") != "" else Color(0.32, 0.31, 0.30)
	m.roughness = 0.95
	m.cull_mode = StandardMaterial3D.CULL_DISABLED
	return m

## Rebuild the surfaces of `mesh` whose BSP material belongs to `pkg` with
## per-face normals + tangents (SurfaceTool: flat normals — the BSP faces
## are planar polygons — then tangents). The BaseMaterial3D heightmap floor
## route (the built-in deep parallax) reads the mesh tangent frame; the
## jac-TBN shader materials never look at it, so shader-driven surfaces
## render pixel-identical. Returns a NEW mesh (the input stays untouched).
func _with_normals_for(mesh: Mesh, surfaces: Array, pkg: String) -> Mesh:
	var out := ArrayMesh.new()
	var added := 0
	for si in range(mesh.get_surface_count()):
		var arr: Array = mesh.surface_get_arrays(si)
		var tex: Variant = surfaces[si].get("tex") if si < surfaces.size() else null
		var is_temple: bool = tex != null and str(tex[0]).to_lower() == pkg
		if is_temple:
			var st := SurfaceTool.new()
			# DEVLOG-130: create_from_arrays' signature is (arrays,
			# primitive_type) — the old call passed the FORMAT bitmask as the
			# primitive, so the SurfaceTool sat on a garbage primitive and
			# BOTH generate_normals and generate_tangents failed on every
			# temple BSP surface (24 silent errors per boot). The BSP glTF
			# carries only POSITION+TEXCOORD_0 — without this fix the whole
			# temple BSP (the interior vault + the floors) rendered with no
			# normals: zero diffuse, ambient-only = the user's "статично
			# чёрный храм". The floors' built-in heightmap route also needs
			# the tangent frame this path never produced.
			st.create_from_arrays(arr, Mesh.PRIMITIVE_TRIANGLES)
			st.deindex()
			st.generate_normals(false)
			st.generate_tangents()
			out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,
					st.commit_to_arrays())
			added += 1
		else:
			out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	print("normals+tangents: %d/%d temple surfaces (%s)" % [added,
			mesh.get_surface_count(), pkg])
	return out

func _build_bsp() -> void:
	# The level BSP rendered DIRECTLY from the level Model's Surfs+Nodes
	# (tools/l2strict/levelbsp.py, RE 2026-11-12): the engine's own CSG
	# geometry — includes the CSG-split faces the brush reconstruction
	# cannot produce (the junction floors, the curb assemblies). One mesh,
	# one surface per material, UVs = texels (scaled per texture size).
	# Collision = the same mesh trimesh with backface (authentic: the level
	# BSP IS the engine's collision world).
	if OS.get_environment("L2_NO_LEVELBSP") != "":
		print("levelbsp: SKIPPED (L2_NO_LEVELBSP diagnostic)")
		_build_bsp_brushes()
		return
	var lb := _load_json(active_dir + "/levelbsp.json")
	var gp := "%s/meshes_bsp/LevelBSP.gltf" % active_dir
	if lb.is_empty() or not ResourceLoader.exists(gp):
		print("levelbsp: missing, falling back to brushes")
		_build_bsp_brushes()
		return
	var scene: PackedScene = load(gp)
	if scene == null:
		print("levelbsp: load failed")
		return
	var root := scene.instantiate()
	var mesh: Mesh = null
	for c in root.get_children():
		if c is MeshInstance3D:
			mesh = c.mesh
			break
	root.free()
	if mesh == null:
		return
	var surfaces: Array = lb.get("surfaces", [])
	# The temple court surfaces need mesh normals+tangents for Godot's
	# built-in heightmap floor material (BaseMaterial3D deep parallax reads
	# the mesh tangent frame); the jac-TBN shader path never looks at them,
	# so the village surfaces pass through pixel-identical.
	mesh = _with_normals_for(mesh, surfaces, "sylen_temple_t")
	var mat_cache := {}
	var textured := 0
	for si in range(mesh.get_surface_count()):
		if si < surfaces.size() and surfaces[si].get("tex") != null:
			# DEVLOG-116: the section-stream surfaces carry the client's
			# FINAL tile UVs (texel_uvs=false — no per-texture rescale);
			# the licensee-23 surf path keeps its texel UVs (the default).
			var texel: bool = surfaces[si].get("texel_uvs", true)
			mesh.surface_set_material(si, _bsp_material(surfaces[si]["tex"],
					mat_cache, texel))
			textured += 1
		else:
			mesh.surface_set_material(si, _bsp_grey())
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	world.add_child(mi)
	var body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var shape := mesh.create_trimesh_shape()
	shape.backface_collision = true
	col.shape = shape
	body.add_child(col)
	body.set_meta("mesh_key", "LevelBSP")
	world.add_child(body)
	print("levelbsp: surfaces ", mesh.get_surface_count(), ", textured ", textured,
		", unique materials ", mat_cache.size())
	# The level Model covers only the designer-built zone geometry (the
	# temple court, the valley); the streets/buildings live in the Brush
	# actors — render BOTH sources.
	_build_bsp_brushes()
	# The Shillien Temple interior comes from the level BSP node walk
	# (temple_bsp.py) — the client's own stone structure + the decoration
	# static meshes. Its UVs = the client's baked section-stream tile
	# coordinates (DEVLOG-82) — texel_uvs=false there.
	_build_temple_native()

func _build_bsp_brushes() -> void:
	var brushes: Array = bsp_data.get("brushes", [])
	var built := 0
	var skipped := 0
	var skip_brushes: Array = []
	var skip_env := OS.get_environment("L2_SKIP_BRUSH")
	if skip_env != "":
		skip_brushes = skip_env.split(",")
	var m := _bsp_grey()
	var mat_cache := {}
	var textured_surfaces := 0
	for br in brushes:
		if br.get("polys", "") in skip_brushes:
			skipped += 1
			continue
		var polys: String = br.get("polys", "")
		var loc: Array = br.get("location", [0, 0, 0])
		var faces: Array = br.get("faces", [])
		# NOTE: no brush-level portal skip anymore. The old 0x400000-majority
		# rule wrongly dropped ~77 real brushes (the road curbs + cobble
		# patches + valley walls) — 0x400000 is carried by ordinary faces
		# too. The zone/sky boxes drop out naturally: bsp2 emits prims only
		# for faces WITH a surf texture, and the zone boxes have none.
		var gp := "%s/meshes_bsp/BSP_%s.gltf" % [active_dir, polys]
		if not ResourceLoader.exists(gp):
			skipped += 1
			continue
		# The displaced variant (<name>_D.gltf, the 3D-geometry experiment):
		# RENDER the height-displaced mesh — its real polygons give the true
		# geometric sun response, continuous across the joints. Collision
		# stays on the FLAT mesh's trimesh (the relief is ±few cm).
		var gdp := "%s/meshes_bsp/BSP_%s_D.gltf" % [active_dir, polys]
		if ResourceLoader.exists(gdp):
			gp = gdp
		var scene: PackedScene = load(gp)
		if scene == null:
			skipped += 1
			continue
		var root := scene.instantiate()
		var mesh: Mesh = null
		for c in root.get_children():
			if c is MeshInstance3D:
				mesh = c.mesh
				break
		root.free()
		if mesh == null:
			skipped += 1
			continue
		var pos := Vector3(float(loc[0]) * UNIT_SCALE, float(loc[2]) * UNIT_SCALE, float(loc[1]) * UNIT_SCALE)
		# per-face materials: prim index -> texture (null prim = not rendered)
		var prim_tex := {}
		var prim_2s := {}
		var force2s := OS.get_environment("L2_BSP_2SIDED") != ""
		for f in faces:
			if f.get("prim") != null and f.get("tex") != null:
				prim_tex[int(f["prim"])] = f["tex"]
				# DEVLOG-153: the client culls BSP backfaces unless the surf
				# carries PF_TwoSided (0x100) — the lattice plate's floor01
				# underside must not plug the Iron_net holes from above.
				# L2_BSP_2SIDED = the A/B diagnostic (the old double-sided look).
				prim_2s[int(f["prim"])] = force2s or (int(f.get("flags", 0)) & 0x100) != 0
		# build the material list first, then SPLIT the alpha-cutout surfaces
		# (the lattice grates) into their OWN MeshInstance with shadow casting
		# OFF: the thin grate sits ~3 mm above the plate below, and its
		# hole-shaped shadow map produced full-surface shadow acne (the
		# "streaks" that broke the location in the reverted attempt)
		var mats: Array = []
		var brush_dbg := OS.get_environment("L2_BRUSH_DEBUG") != ""
		for si in range(mesh.get_surface_count()):
			if brush_dbg:
				var bm := StandardMaterial3D.new()
				var bhue := fmod(float(polys.length() * 131 + si * 37), 360.0)
				bm.albedo_color = Color.from_hsv(bhue / 360.0, 0.85, 0.95)
				mats.append(bm)
				print("BRUSH: ", polys, " surf ", si, " hue=", bhue)
				continue
			if prim_tex.has(si):
				mats.append(_bsp_material(prim_tex[si], mat_cache, true,
						prim_2s.get(si, true)))
			else:
				mats.append(m)
		var grate_idx: Array[int] = []
		var grey_idx: Array[int] = []
		for si in range(mats.size()):
			var mm: Material = mats[si]
			if mm is ShaderMaterial and mm.get_shader_parameter("use_alpha") == true:
				grate_idx.append(si)
			elif mm == m:
				grey_idx.append(si)
		var mi := MeshInstance3D.new()
		mi.position = pos
		var main_idx: Array[int] = []
		for si in range(mats.size()):
			if si in grate_idx or si in grey_idx:
				continue
			main_idx.append(si)
		if grey_idx.is_empty() and grate_idx.is_empty():
			for si in range(mesh.get_surface_count()):
				mesh.surface_set_material(si, mats[si])
			mi.mesh = mesh
			world.add_child(mi)
		else:
			# DEVLOG-147 rev4: three-way partition — the textured surfaces
			# (layer 1, the shader pools), the grate surfaces (shadow off),
			# the GREY placeholder surfaces (layer 2, the lantern omnis —
			# StandardMaterial3D cannot host the pool code).
			if not main_idx.is_empty():
				var am := ArrayMesh.new()
				for si in main_idx:
					am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,
							mesh.surface_get_arrays(si))
					am.surface_set_material(am.get_surface_count() - 1, mats[si])
				mi.mesh = am
				world.add_child(mi)
			if not grate_idx.is_empty():
				var gm := ArrayMesh.new()
				for si in grate_idx:
					gm.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,
							mesh.surface_get_arrays(si))
					gm.surface_set_material(gm.get_surface_count() - 1, mats[si])
				var gi := MeshInstance3D.new()
				gi.mesh = gm
				gi.position = pos
				gi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				world.add_child(gi)
			if not grey_idx.is_empty():
				var km := ArrayMesh.new()
				for si in grey_idx:
					km.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,
							mesh.surface_get_arrays(si))
					km.surface_set_material(km.get_surface_count() - 1, mats[si])
				var ki := MeshInstance3D.new()
				ki.mesh = km
				ki.position = pos
				ki.layers = 2  # omni-lit only (cull_mask = 2)
				world.add_child(ki)
		var body := StaticBody3D.new()
		var col := CollisionShape3D.new()
		var shape := mesh.create_trimesh_shape()
		shape.backface_collision = true
		if polys == "Polys377" and OS.get_environment("L2_PLAZA_DEBUG") != "":
			var pfs: PackedVector3Array = shape.get_faces()
			var pmn := Vector3(INF, INF, INF)
			var pmx := Vector3(-INF, -INF, -INF)
			for pf in pfs:
				pmn = pmn.min(pf)
				pmx = pmx.max(pf)
			print("PLAZA brush surfaces=", mesh.get_surface_count(),
					" faces=", pfs.size(), " local_aabb=", pmn, "..", pmx,
					" pos=", pos)
		col.shape = shape
		body.add_child(col)
		body.position = pos
		body.set_meta("mesh_key", "BSP:" + polys)
		world.add_child(body)
		built += 1
		textured_surfaces += prim_tex.size()
	print("bsp brushes built ", built, ", skipped ", skipped,
		", textured surfaces ", textured_surfaces, ", unique materials ", mat_cache.size())



## The Shillien Temple interior as a NATIVE mesh (temple_native.py): the
## client authors it as subtract volumes (the stair ramps Polys71/59 with
## the ai_004 step texture, the gallery slopes, the floors/walls) — the
## level BSP has none of it and no static meshes cover it. This loads the
## clean emitted mesh with the same texel-UV BSP materials + trimesh
## collision. Modern-port rule: coordinates from the client, no legacy
## brush-pipeline emulation.
func _build_temple_native() -> void:
	# DEVLOG-77: the temple interior IS the level BSP (336 nodes in the
	# temple region of Model500 — the old "zero temple BSP geometry" probe
	# read surf idx[4] = iBrushPoly as a node index and was invalid). The
	# client renders exactly: the level BSP (stone walls with the carved
	# panel recesses, floors, ceilings) + the decoration static meshes.
	# The Brush actors are the CSG sources — their Models are empty and the
	# runtime renders nothing from them (engine.dll has no runtime CSG).
	# TempleBsp.gltf = the node-walked temple part of the level BSP
	# (tools/l2strict/temple_bsp.py). The Brush faces are NOT rendered.
	if OS.get_environment("L2_NO_TEMPLEBSP") != "":
		print("temple_bsp: SKIPPED (L2_NO_TEMPLEBSP)")
		return
	var tn := _load_json(MAP_DIR + "/temple_bsp.json")
	var gp := "%s/meshes_bsp/TempleBsp.gltf" % MAP_DIR
	if tn.is_empty() or not ResourceLoader.exists(gp):
		print("temple_bsp: missing (build with tools/l2strict/temple_bsp.py)")
		return
	var scene: PackedScene = load(gp)
	if scene == null:
		print("temple_bsp: load failed")
		return
	var root := scene.instantiate()
	var mesh: Mesh = null
	for c in root.get_children():
		if c is MeshInstance3D:
			mesh = c.mesh
			break
	root.free()
	if mesh == null:
		return
	var surfaces: Array = tn.get("surfaces", [])
	# Every surface here is temple stone — normals+tangents for the built-in
	# heightmap floors (BaseMaterial3D); the jac-TBN shader walls ignore them.
	mesh = _with_normals_for(mesh, surfaces, "sylen_temple_t")
	var mat_cache := {}
	var textured := 0
	var dbg_cols := [Color(1.0, 0.1, 0.9), Color(0.1, 1.0, 0.2), Color(0.2, 0.4, 1.0),
		Color(1.0, 0.9, 0.1), Color(1.0, 0.4, 0.1), Color(0.1, 1.0, 0.9),
		Color(0.6, 0.1, 1.0), Color(0.9, 0.5, 0.1), Color(0.1, 0.6, 0.1),
		Color(0.9, 0.1, 0.4)]
	for si in range(mesh.get_surface_count()):
		if OS.get_environment("L2_BSP_DEBUG") != "":
			var dbg := StandardMaterial3D.new()
			dbg.albedo_color = dbg_cols[si % dbg_cols.size()]
			mesh.surface_set_material(si, dbg)
			textured += 1
			continue
		if si < surfaces.size() and surfaces[si].get("tex") != null:
			# the temple BSP = the client's baked section-stream UVs (final
			# tile coordinates) + per-section one-sidedness (DEVLOG-82 rev2)
			var ts: bool = surfaces[si].get("two_sided", true) or OS.get_environment("L2_BSP_2SIDED") != ""
			mesh.surface_set_material(si, _bsp_material(surfaces[si]["tex"], mat_cache, false, ts))
			textured += 1
		else:
			mesh.surface_set_material(si, _bsp_grey())
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	world.add_child(mi)
	var body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var shape := mesh.create_trimesh_shape()
	shape.backface_collision = true
	col.shape = shape
	body.add_child(col)
	body.set_meta("mesh_key", "TempleBsp")
	world.add_child(body)
	print("temple_bsp: build ", tn.get("build", "?"),
		", surfaces ", mesh.get_surface_count(),
		", textured ", textured, ", unique materials ", mat_cache.size())


func _road_pt(origin: Vector2, dir: Vector2, right: Vector2, lx: float, w: float, z: float) -> Vector3:
	var g := origin + dir * lx + right * w
	return Vector3(g.x * UNIT_SCALE, z * UNIT_SCALE, g.y * UNIT_SCALE)


## DEVLOG-163: all candle flames in one camera-facing MultiMesh. The five
## source images are the client's original FX_E_T flame_a01..a05 frames; no
## synthetic fire texture/actor is used. The shader billboards each quad and
## cycles the frame array with an individual position-derived phase.
func _build_candle_flames() -> void:
	if OS.get_environment("L2_CANDLE_FIRE_OFF") != "" \
			or _candle_flame_transforms.is_empty():
		return
	var imgs: Array[Image] = []
	for i in range(1, 6):
		var img := Image.new()
		var p := "res://assets/maps/20_18/textures/fx_e_t/Texture/flame_a%02d.png" % i
		if img.load(p) != OK:
			push_error("candle flame frame missing: " + p)
			return
		imgs.append(img)
	var frames := Texture2DArray.new()
	frames.create_from_images(imgs)
	var mat := ShaderMaterial.new()
	mat.shader = load("res://assets/shaders/l2_candle_flame.gdshader")
	mat.set_shader_parameter("flame_frames", frames)
	var verts := PackedVector3Array([
		Vector3(-0.5, -0.5, 0), Vector3(0.5, -0.5, 0),
		Vector3(0.5, 0.5, 0), Vector3(-0.5, 0.5, 0),
	])
	var uvs := PackedVector2Array([
		Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1),
	])
	var idx := PackedInt32Array([0, 1, 2, 0, 2, 3])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = idx
	var quad := ArrayMesh.new()
	quad.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = quad
	mm.instance_count = _candle_flame_transforms.size()
	for i in range(_candle_flame_transforms.size()):
		mm.set_instance_transform(i, _candle_flame_transforms[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	world.add_child(mmi)
	print("candle flames: ", _candle_flame_transforms.size(),
			" client-frame billboards (5 frames)")

func _build_meshes() -> void:
	var placed := 0
	var skipped: Array[String] = []
	for actor in map_data["actors"]:
		if actor.get("class") != "StaticMeshActor" or actor.get("deleted"): continue
		var mr = actor.get("mesh")
		if mr == null or not (mr is Dictionary): continue
		var key := "%s:%s" % [mr["package"], mr["object"]]
		# Nothing is skipped from the road family anymore (see the note on
		# _ROAD_STRIP_SKIP): the skips were merged-accessor-era artifacts.
		if key in _ROAD_STRIP_SKIP:
			continue
		var mesh := _get_mesh(key)
		if mesh == null:
			skipped.append(key)
			continue
		var loc: Array = actor["location"]
		var rot: Array = actor.get("rotation", [0, 0, 0])
		var pos_z: float = loc[2]
		# MODERN PORT (DEVLOG-86): foliage renders via one MultiMeshInstance3D
		# per mesh key (GPU instancing — one draw call for the whole actor
		# family) instead of 195 per-actor MeshInstance3D nodes.
		if _is_foliage_key(key):
			var f_ds := Vector3.ONE * float(actor.get("draw_scale", 1.0))
			var f_s3: Array = actor.get("draw_scale3d", [1.0, 1.0, 1.0])
			# DEVLOG-156: same mesh-axis permutation as the statics path.
			if f_s3 != null and f_s3.size() == 3:
				f_ds *= Vector3(f_s3[0], f_s3[2], f_s3[1])
			var vb := _ue_basis(int(rot[0]), int(rot[1]), int(rot[2])) \
					* Basis.from_scale(f_ds)
			if not _veg_batch.has(key):
				_veg_batch[key] = []
			(_veg_batch[key] as Array).append(Transform3D(vb,
					Vector3(loc[0] * UNIT_SCALE, pos_z * UNIT_SCALE, loc[1] * UNIT_SCALE)))
			continue
		var inst := MeshInstance3D.new()
		# DEVLOG-147 rev4: the render-layer routing for the lantern lighting.
		# All-placeholder keys (every surface = StandardMaterial3D) move to
		# LAYER 2 — lit exclusively by the lantern omnis (cull_mask = 2).
		# Mixed keys split per key: the ShaderMaterial surfaces stay on
		# layer 1 (the shader pools), the placeholder surfaces ride a twin
		# inst on layer 2 (omni-lit). Pool-capable keys unchanged.
		var is_placeholder: bool = _placeholder_keys.get(key, false)
		var sp: Variant = null
		if not is_placeholder:
			var std_cnt := 0
			for si in range(mesh.get_surface_count()):
				if mesh.surface_get_material(si) is StandardMaterial3D:
					std_cnt += 1
			if std_cnt > 0:
				if not _static_split.has(key):
					var main_am := ArrayMesh.new()
					var grey_am := ArrayMesh.new()
					var plaf_am := ArrayMesh.new()
					for si in range(mesh.get_surface_count()):
						var sm: Material = mesh.surface_get_material(si)
						var sarrs: Array = mesh.surface_get_arrays(si)
						if sm is StandardMaterial3D:
							grey_am.add_surface_from_arrays(
									Mesh.PRIMITIVE_TRIANGLES, sarrs)
							grey_am.surface_set_material(
									grey_am.get_surface_count() - 1, sm)
						elif sm is ShaderMaterial and sm.has_meta("l2_plafond"):
							# DEVLOG-149: the translucent glass does not cast
							# (its shadow would blob the ground under the
							# lamp); the metal cage/ledges around it DO cast —
							# the physical light clipping the user ordered.
							plaf_am.add_surface_from_arrays(
									Mesh.PRIMITIVE_TRIANGLES, sarrs)
							plaf_am.surface_set_material(
									plaf_am.get_surface_count() - 1, sm)
						else:
							main_am.add_surface_from_arrays(
									Mesh.PRIMITIVE_TRIANGLES, sarrs)
							main_am.surface_set_material(
									main_am.get_surface_count() - 1, sm)
					_static_split[key] = {"main": main_am,
							"grey": grey_am if grey_am.get_surface_count() > 0
							else null,
							"plaf": plaf_am
							if plaf_am.get_surface_count() > 0 else null}
				sp = _static_split[key]
		inst.mesh = sp["main"] if sp != null else mesh
		# Village floor slabs (O_De_01/02/03) read at Z -5541 but their top
		# surface then sits at -56 m — 11.6 m BELOW the village floor level
		# (-44.8, set by the bridge deck -44.05 and PlayerStart Zs -4478..-4493).
		# -5541 + 1161 = -4380 lands the slab top exactly on the floor level,
		# in the Z family of the other floor meshes (Bridge -4288, Btm_Obj01
		# -4508, O_DE_Btm -4952). Experimental shift pending engine-RE of the
		# discrepancy.
		inst.position = Vector3(loc[0] * UNIT_SCALE, pos_z * UNIT_SCALE, loc[1] * UNIT_SCALE)
		# DEVLOG-151: the per-axis DrawScale3D — UE2 mirrors the mesh in its
		# OWN axes, then rotates. 3 of the 8 village pylon actors carry
		# negative scale3d; the old uniform-only scale IGNORED the mirror,
		# so the 84 m pylon+chain composite (O_DE_Pir02) rendered its pylon
		# body on the VILLAGE side of the pivot instead of out in the cave
		# (the user's "опоры не на своих местах, цепи идут не туда") and the
		# mirrored houses/stairs (O_DE_H02/H03, O_DE_CH_sidestair...) were
		# unwrapped. The scale is baked INTO the basis (R*S — the mesh-space
		# scale): the Node3D.scale property is unreliable for negatives.
		# DEVLOG-156: DrawScale3D is authored in the MESH's own axes (UE
		# x,y,z), and the staged glTF maps them (x, z, y) — the vertical is
		# glTF Y = UE z. So the per-axis scale must be permuted the same
		# way: (sx, sz, sy). The old unswopped (sx, sy, sz) turned every
		# sy=-1 actor into a VERTICAL flip (7 village actors, 2 of the 4
		# Pir02 towers): the 84 m pylon's 51 m tail pointed UP through the
		# surface houses instead of down into the cavern.
		var ds := Vector3.ONE * float(actor.get("draw_scale", 1.0))
		var s3: Array = actor.get("draw_scale3d", [1.0, 1.0, 1.0])
		if s3 != null and s3.size() == 3:
			ds *= Vector3(s3[0], s3[2], s3[1])
		inst.transform.basis = _ue_basis(int(rot[0]), int(rot[1]), int(rot[2])) \
				* Basis.from_scale(ds)
		# DEVLOG-159: register the client-derived candle lights in world
		# space (the actor's exact R*S transform, same as the mesh).
		# L2_CANDLES_OFF=1 = the before-state A/B (both pool + emission).
		if OS.get_environment("L2_CANDLES_OFF") == "" \
				and _candle_local_positions.has(key):
			for cp in _candle_local_positions[key]:
				var wp: Vector3 = inst.transform * cp
				L2ProcTex.register_candle(wp)
				var fh := 0.28 if key.ends_with("store_17") \
						else (0.24 if key.ends_with("store_15") else 0.18)
				var fw := fh * 0.6
				_candle_flame_transforms.append(Transform3D(
						Basis.from_scale(Vector3(fw, fh, 1.0)),
						wp + Vector3(0, fh * 0.5 + 0.005, 0)))
		if key == "interior_B_delf_s:interior_B_delf_store_06" \
				and OS.get_environment("L2_GRATE_DEBUG") != "":
			var ga := mesh.get_aabb()
			var g0: Array = mesh.surface_get_arrays(0)
			var gv: PackedVector3Array = g0[Mesh.ARRAY_VERTEX]
			var gmin := Vector3(INF, INF, INF)
			var gmax := Vector3(-INF, -INF, -INF)
			for v in gv:
				var wv: Vector3 = inst.transform * v
				gmin = gmin.min(wv)
				gmax = gmax.max(wv)
			print("GRATE store06 mesh_aabb=", ga, " surf0_world=", gmin, "..", gmax,
					" center=", (gmin + gmax) * 0.5, " basis=", inst.basis)
		if is_placeholder:
			inst.layers = 2
		world.add_child(inst)
		var gi2: MeshInstance3D = null
		var pi2: MeshInstance3D = null
		if sp != null and sp["grey"] != null:
			gi2 = MeshInstance3D.new()
			gi2.mesh = sp["grey"]
			gi2.position = inst.position
			gi2.transform.basis = inst.transform.basis
			gi2.layers = 2
			world.add_child(gi2)
		if sp != null and sp.get("plaf") != null:
			pi2 = MeshInstance3D.new()
			pi2.mesh = sp["plaf"]
			pi2.position = inst.position
			pi2.transform.basis = inst.transform.basis
			pi2.layers = 1  # the pools/emission apply (the ShaderMaterial)
			pi2.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			world.add_child(pi2)
		# DEVLOG-151: a mirrored basis flips the triangle winding — a
		# backface-culled StandardMaterial3D surface would render its
		# INSIDES. Culling the FRONT restores the same visible side. The
		# shader materials (the PBR/analytic) are cull_disabled — nothing
		# to do for them.
		if ds.x * ds.y * ds.z < 0.0:
			_flip_cull_for_mirrored(inst)
			if gi2 != null:
				_flip_cull_for_mirrored(gi2)
			if pi2 != null:
				_flip_cull_for_mirrored(pi2)
		placed += 1
		# DEVLOG-144: the street lanterns = the light sources (the user's
		# order): a light at the blue plafond's center. The blue glass itself
		# is emissive (l2_proc_tex). The client's Light actors inside the
		# village are removed in _build_lights — the lanterns replace them.
		# DEVLOG-147 rev4 (the audit trail: the omni alone hit the compat
		# renderer's COMPILE-TIME 8-lights-per-object cap — the plaza floor
		# alone overlapped 32 lanterns, the per-object selection flipped with
		# the camera angle; the shader pools alone left the
		# StandardMaterial3D placeholders dark — they cannot host shader
		# code). THE FINAL SPLIT OF LABOR: the ShaderMaterial surfaces
		# (layer 1) are lit exclusively by the DETERMINISTIC shader pools
		# (l2_surface_pbr / l2_procedural, fed by the registered plafond
		# positions); the StandardMaterial3D placeholders (layer 2) are lit
		# exclusively by these omnis (cull_mask = 2 — they cannot double-
		# light anything on layer 1). The omnis are small-range, always on,
		# and their carriers are the small placeholder pieces — no lottery.
		if _plafond_center.has(key):
			var lpos: Vector3 = inst.transform * _plafond_center[key]
			L2ProcTex.register_lantern(lpos)
			var lantern := OmniLight3D.new()
			lantern.position = lpos
			lantern.light_color = Color(0.6, 0.75, 1.0)
			lantern.light_energy = 2.6
			# DEVLOG-148 rev5: the range 22 m — the CLIENT's plaza is lit
			# wall-to-wall by its lamps (the user's reference shot), while
			# our 7 m hand-set value left the plaza center beyond every
			# lantern ("фонари посередине нерабочие"). The range also brings
			# the omni shadow maps over the whole plaza grid (the two weak
			# character shadows).
			lantern.omni_range = 22.0
			# DEVLOG-150: the physical falloff — attenuation 2.0 makes the
			# omni use Godot's true inverse-square curve (the same function
			# the shader pools now use). The old 0.25 was nearly no decay —
			# the placeholder wash part of the "переосвещение".
			lantern.omni_attenuation = 2.0
			# DEVLOG-151: the omni shadows OFF. The carrier omnis own the
			# character shadows now; ~10-15 shadow cubes (the 25 m gate)
			# were filling the compat shadow atlas and could evict the
			# carriers' own slots — "теней так и нету". The placeholders
			# lose their cosmetic shadows; near the player the carriers
			# (cull mask 3) still shadow them correctly.
			lantern.shadow_enabled = false
			lantern.light_cull_mask = 2  # layer 2 = the placeholder surfaces
			lantern.visible = true       # always on, no gate, no camera dependence
			_lantern_omnis.append(lantern)
			world.add_child(lantern)
		# DEVLOG-160: the store_17 doordeco panel is a flat decorative
		# overlay (the ornate arch + the two candles), NOT a door leaf. Its
		# trimesh collider sat at chest height across the doorway: the ankle
		# ray passed under it, the knee ray over it, and the capsule could
		# enter but not leave (the user's report at 12204,15945). Visual only.
		var no_collision := key == "interior_B_delf_s:interior_B_delf_store_17"
		if not no_collision:
			if not _shape_cache.has(key):
				# DEVLOG-160: use the client's kDOP-covered triangle subset
				# when <mesh>.collision.json exists. The old direct render
				# trimesh made decorative arch/lattice panels solid — the
				# player could enter the shop but not leave through the
				# doorway (O_DE_SH_Set). Fallback stays the full trimesh.
				var mshape: Shape3D = _collision_shape(key, mesh)
				if mshape is ConcavePolygonShape3D:
					(mshape as ConcavePolygonShape3D).backface_collision = true
				_shape_cache[key] = mshape
			var body := StaticBody3D.new()
			var col := CollisionShape3D.new()
			col.shape = _shape_cache[key]
			body.add_child(col)
			body.position = inst.position
			body.transform.basis = inst.transform.basis
			body.set_meta("mesh_key", key)
			if key == "Oren_DEV_S:O_DE_inlet" \
					and OS.get_environment("L2_INLET_COL_DEBUG") != "" \
					and col.shape is ConcavePolygonShape3D:
				var fs: PackedVector3Array = (col.shape as ConcavePolygonShape3D).get_faces()
				var fmin := Vector3(INF, INF, INF)
				var fmax := Vector3(-INF, -INF, -INF)
				for fv in fs:
					fmin = fmin.min(fv)
					fmax = fmax.max(fv)
				print("INLETCOL body_pos=", body.position, " basis=", body.basis,
						" faces=", fs.size(), " local_aabb=", fmin, "..", fmax,
						" floor_local=", body.transform.affine_inverse() * Vector3(166.27, -41.124, 149.85))
			world.add_child(body)
	# DEVLOG-147 rev4: the layer-routing stats (per tile, cumulative keys)
	var ph_keys := 0
	for k in _placeholder_keys:
		if _placeholder_keys[k]:
			ph_keys += 1
	print("layer routing: ", ph_keys, " all-placeholder keys, ",
			_static_split.size(), " mixed keys split")
	# DEVLOG-158 rev2 (the GLM audit): L2_MAT_AUDIT=1 — the actual runtime
	# material routing for the plaza suspect keys + the light counts (the
	# floor-brightening investigation: same lights, same uniforms, yet the
	# slab rendered 2.4x brighter after the lamp frame rerouting).
	if OS.get_environment("L2_MAT_AUDIT") != "":
		print("MAT AUDIT lantern_omnis=", _lantern_omnis.size(),
				" carriers=", _carrier_lights.size())
		for key in ["Oren_DEV_S:O_DE_Btm_Obj01", "Oren_DEV_S:O_DE_Bank",
				"Oren_DEV_S:O_DE_Bank_Set", "Oren_DEV_S:O_DE_Btm",
				"Oren_DEV_S:O_DE_Center_obj",
				"Oren_DEV_S:O_DE_Lamp01", "Oren_DEV_S:O_DE_Lamp02"]:
			var mk: Mesh = _mesh_cache.get(key)
			if mk == null:
				continue
			var kinds := []
			for si in range(mk.get_surface_count()):
				var mm: Material = mk.surface_get_material(si)
				kinds.append(("SH" if mm is ShaderMaterial else "ST")
						+ str(si))
			print("MAT AUDIT ", key, " placeholder=",
					_placeholder_keys.get(key, false),
					" split=", _static_split.has(key),
					" surf_mats=", kinds)
	# DEVLOG-86: build the foliage MultiMeshes (one per mesh key) + physics.
	# Grass/bushes are NOT solid in the client (walk-through decoration —
	# the legacy full-trimesh bodies blocked the player with invisible
	# cards). Trees collide with a trunk cylinder per instance (the canopy
	# cards are not solid).
	var veg_trunk_shape := {}
	var veg_instances := 0
	for vkey in _veg_batch:
		var vmesh := _get_mesh(vkey)
		if vmesh == null:
			continue
		var vxs: Array = _veg_batch[vkey]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = vmesh
		mm.instance_count = vxs.size()
		for i in range(vxs.size()):
			mm.set_instance_transform(i, vxs[i])
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		# the grass cards alias into noise far away; the trees read at
		# distance (Godot 4 visibility ranges — the modern cull path); the
		# stones stay unlimited (rock at distance = landmark)
		if "grass" in vkey:
			mmi.visibility_range_end = 70.0
		elif "tree" in vkey:
			mmi.visibility_range_end = 260.0
		world.add_child(mmi)
		veg_instances += vxs.size()
		if "tree" in vkey and not _foliage_trunk.has(vkey):
			# DEVLOG-114: the permanent visibility of the pattern violations —
			# every tree key MUST have a trunk entry (the DEVLOG-112 rule);
			# a WARN here means a new tree family slipped through the gate
			print("WARN: tree key without trunk collider (pass-through): ", vkey)
		if "tree" in vkey and _foliage_trunk.has(vkey):
			var tb: AABB = _foliage_trunk[vkey]
			if not veg_trunk_shape.has(vkey):
				var cs := CylinderShape3D.new()
				cs.radius = clampf(maxf(tb.size.x, tb.size.z) * 0.5, 0.3, 1.2)
				cs.height = clampf(tb.size.y, 1.5, 6.0)
				veg_trunk_shape[vkey] = cs
			var cshape: CylinderShape3D = veg_trunk_shape[vkey]
			for vxf in vxs:
				var body := StaticBody3D.new()
				var col := CollisionShape3D.new()
				col.shape = cshape
				body.add_child(col)
				# the cylinder sits at the BARK AABB center in the mesh-local
				# frame, rotated/scaled by the instance basis — the mesh pivot
				# is NOT the trunk for off-center meshes (Darkelf_tree10's
				# geometry spans z -6.6..1.1 with the pivot at the edge), so
				# positioning at the origin left the cylinder in the middle
				# of the canopy spread (DEVLOG-112)
				body.position = vxf.origin + vxf.basis * Vector3(
						tb.position.x + tb.size.x * 0.5,
						tb.position.y + cshape.height * 0.5,
						tb.position.z + tb.size.z * 0.5)
				body.set_meta("mesh_key", "Veg:" + vkey)
				world.add_child(body)
		elif not ("grass" in vkey) and not ("tree" in vkey):
			# the field_deco stone boulders / artifact stones are SOLID —
			# keep the full trimesh per instance (the legacy behavior).
			# Trees are EXCLUDED: a tree key without its trunk entry must be
			# pass-through (the canopy cards are not solid), never the full
			# trimesh — the trimesh makes the alpha canopy cards solid and
			# the click ray stops on invisible foliage (DEVLOG-112).
			if not _shape_cache.has(vkey):
				var ms := vmesh.create_trimesh_shape()
				ms.backface_collision = true
				_shape_cache[vkey] = ms
			for vxf2 in vxs:
				var sbody := StaticBody3D.new()
				var scol := CollisionShape3D.new()
				scol.shape = _shape_cache[vkey]
				sbody.add_child(scol)
				sbody.position = vxf2.origin
				sbody.transform.basis = vxf2.basis
				sbody.set_meta("mesh_key", "Veg:" + vkey)
				world.add_child(sbody)
	print("foliage: %d instances in %d MultiMeshes, trunk colliders for %d tree meshes"
			% [veg_instances, _veg_batch.size(), veg_trunk_shape.size()])
	# DEVLOG-107: the batch is per TILE (the flush consumed it) — clearing
	# keeps the next tile's MultiMeshes from re-including this tile's
	# local-frame transforms.
	# DEVLOG-112: _foliage_trunk is NOT cleared — it is keyed by the MESH
	# key (tile-independent), but its entries are computed inside _get_mesh
	# ONLY on the cache miss (the cache lives for the whole session). A
	# clear here wiped every key computed by an earlier tile, and the later
	# tiles' trees fell into the full-trimesh fallback — solid canopy cards
	# (19_18: 5 of 6 tree keys; the click ray hit the invisible alpha cards
	# and the character stopped — the user's report).
	_veg_batch.clear()
	# GATE D (DEVLOG-79): tint side_ent surfaces with distinct colors
	if OS.get_environment("L2_SIDEENT_DEBUG") != "":
		var se_mesh: Mesh = _get_mesh("sylen_temple_s:sylentemple_side_ent")
		if se_mesh != null:
			var hide := StandardMaterial3D.new()
			hide.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			hide.albedo_color = Color(1.0, 1.0, 1.0, 0.0)
			hide.no_shadow_cast = true
			for dbg_si in [0, 1]:
				se_mesh.surface_set_material(dbg_si, hide)
			print("GATE D: side_ent surfaces 0,1 HIDDEN")
	print("placed ", placed, " static meshes, ", _shape_cache.size(), " collision shapes")
	if not skipped.is_empty():
		print("SKIPPED (mesh failed to load): ", skipped)


## UE2 FRotationMatrix closed form, matching AActor::LocalToWorld in engine.dll
## (see Docs/DEVLOG.md 2026-11-02). Angles are UE uint16 wraps; rows X/Y/Z are
## UE axes; Godot columns are C*row where C swaps y/z (UE->Godot mapping).
## Rotation is unit-scale: draw_scale is applied separately. Do NOT replace
## this with a Roll*Pitch*Yaw Euler product — it is not equivalent.
## DEVLOG-151: the mirrored-basis cull fix (see the placement comment) —
## duplicate every backface-culled StandardMaterial3D surface with CULL_FRONT.
func _flip_cull_for_mirrored(gi: GeometryInstance3D) -> void:
	var mesh: Mesh = gi.mesh
	if mesh == null:
		return
	for s in mesh.get_surface_count():
		var m: Material = gi.get_surface_override_material(s)
		if m == null:
			m = mesh.surface_get_material(s)
		var sm := m as StandardMaterial3D
		if sm != null and sm.cull_mode != BaseMaterial3D.CULL_FRONT:
			var d: StandardMaterial3D = sm.duplicate()
			d.cull_mode = BaseMaterial3D.CULL_FRONT
			gi.set_surface_override_material(s, d)

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


## The engine-authentic collision: the L2 client collides only the triangles
## covered by the mesh's kDOP leaf bboxes (the 29-B [01][XX][YY][81 81]+2
## corners records, engine.dll finding fnd_6). tools/l2strict/
## collision_extract.py writes <mesh>.collision.json (the covered triangles,
## staged glTF frame) next to each glTF; meshes without it keep the full
## trimesh. This is what removes the non-walkable Bridge lower deck.
func _collision_shape(key: String, mesh: Mesh) -> Shape3D:
	# DEVLOG-168: the inlet kDOP subset covers only the upper rock shell; both
	# the walkable floor and the lower tunnel walls are absent. A horizontal-
	# only merge fixed the floor but let the player run through the walls.
	# The inlet is a closed tunnel shell, so use its complete render trimesh
	# (winding-agnostic). L2_INLET_FULL_COLLISION=0 restores the old subset A/B.
	if key == "Oren_DEV_S:O_DE_inlet" \
			and OS.get_environment("L2_INLET_FULL_COLLISION") != "0":
		var full := mesh.create_trimesh_shape()
		full.backface_collision = true
		print("inlet collision: full render trimesh (kDOP subset incomplete)")
		return full
	var info = asset_map_data.get("meshes", {}).get(key)
	if info != null:
		var gp: String = info["gltf"]
		var cpath := "%s/%s.collision.json" % [gp.get_base_dir(), gp.get_file().get_basename()]
		if FileAccess.file_exists(cpath):
			var f := FileAccess.open(cpath, FileAccess.READ)
			var data = JSON.parse_string(f.get_as_text())
			var verts = data.get("verts", []) if data is Dictionary else []
			if verts is Array and verts.size() >= 9:
				var shape := ConcavePolygonShape3D.new()
				var pv := PackedVector3Array()
				pv.resize(verts.size() / 3)
				for i in range(verts.size() / 3):
					pv[i] = Vector3(verts[i * 3], verts[i * 3 + 1], verts[i * 3 + 2])
				shape.set_faces(pv)
				return shape
	return mesh.create_trimesh_shape()


## Foliage (vegetation) package keys: the tree packages and the field
## decoration grasses/bushes. CASE-INSENSITIVE: the old inline check
## (begins_with "Field_Deco") missed the lowercase "field_deco_S" package,
## so the grass card clusters rendered OPAQUE (no alpha scissor — the
## DEVLOG-86 flat poly piles). Cutout, not blending (the L2 alpha is a
## hard mask; blending needs sorting and breaks the depth pass).
func _is_foliage_key(key: String) -> bool:
	var parts := key.split(":")
	var pkg := parts[0].to_lower()
	var obj := (parts[1] if parts.size() > 1 else "").to_lower()
	# DEVLOG-112: "tree" in the OBJECT name too — the north tile's
	# Primitive_FieldOBJ_S trees (InDecotree/INtree/MDtree/PriPlain, 700+
	# instances) were missed by the package-name-only check and built as
	# old per-actor statics with FULL trimesh colliders (solid canopy
	# cards — the click ray stopped on invisible foliage)
	return "tree" in pkg or "tree" in obj or pkg.begins_with("field_deco")


func _get_mesh(key: String) -> Mesh:
	if _mesh_cache.has(key): return _mesh_cache[key]
	# DEVLOG-122 (the user's order: "надо аккуратно удалить её из мешей и
	# текстур"): the apse strip sylentemple_deco07 is REMOVED from the
	# render — above the statue's head it read as a "hat" (the vault that
	# encloses it in the client is missing from the TempleBsp build), and
	# the user judged the strip not needed at all. Both instances
	# (StaticMeshActor25/28) drop out with their colliders; the t004/in031
	# slot experiments die with it. The staged glTF stays on disk (the
	# asset_map reference is intact) — only the render path is cut.
	if key == "sylen_temple_s:sylentemple_deco07":
		_mesh_cache[key] = null
		return null
	var info = asset_map_data.get("meshes", {}).get(key)
	if info == null: _mesh_cache[key] = null; return null
	var gp: String = info["gltf"]
	# DEVLOG-90 baked-mesh route: the <Mesh>_baked.gltf variant (built by
	# tools/l2strict/baked_mesh.py in Blender) carries UV2 + the baked
	# normal/AO from the displaced high-poly — prefer it for the meshes
	# that have one. L2_NO_BAKED=1 = the A/B diagnostic (the plain import).
	var is_baked := false
	if OS.get_environment("L2_NO_BAKED") == "" \
			and not gp.contains("_baked"):
		var gb := gp.replace(".gltf", "_baked.gltf")
		if ResourceLoader.exists(gb):
			gp = gb
			is_baked = true
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
	# EVERY surface gets our material: the UModel export writes colored
	# baseColorFactor placeholders (red/green) for its materials — leaving
	# them on unmapped surfaces shows flat pink/green strips.
	var _static_grey := StandardMaterial3D.new()
	_static_grey.albedo_color = Color(1.0, 0.1, 0.9) if OS.get_environment("L2_GREY_DEBUG") != "" else Color(0.32, 0.31, 0.30)
	_static_grey.roughness = 0.95
	_static_grey.cull_mode = StandardMaterial3D.CULL_DISABLED
	# L2_FLAT_DEBUG: flat per-surface colors — identify visible geometry by
	# pixel color (decode: hue = (len(pkg)*131 + len(obj)*31 + si*37) % 360).
	var flat_dbg := OS.get_environment("L2_FLAT_DEBUG") != ""
	for si in range(mesh.get_surface_count()):
		if flat_dbg:
			var fm := StandardMaterial3D.new()
			var hue := fmod(float(parts[0].length() * 131 + parts[1].length() * 31 + si * 37), 360.0)
			fm.albedo_color = Color.from_hsv(hue / 360.0, 0.85, 0.95)
			fm.cull_mode = StandardMaterial3D.CULL_DISABLED
			mesh.surface_set_material(si, fm)
			print("FLAT: ", key, " surf ", si, " hue=", hue)
			continue
		if si >= pis.size():
			print("FALLBACK: ", key, " surf ", si, " (pis exhausted, pis=", pis.size(), ")")
			mesh.surface_set_material(si, _static_grey)
			continue
		var mi := int(pis[si])
		if mi < 0 or mi >= texs.size():
			print("FALLBACK: ", key, " surf ", si, " (mi ", mi, " out of ", texs.size(), ")")
			mesh.surface_set_material(si, _static_grey)
			continue
		var t = texs[mi]
		if t == null or not (t is Dictionary):
			mesh.surface_set_material(si, _static_grey)
			continue
		var tpkg: String = t.get("package", "")
		var tobj: String = t.get("object", "")
		# DEVLOG-144: the DE village lantern plafond — record the surface's
		# AABB center (the omni anchor; the client's own Light actors sat at
		# exactly this offset, the pivot +13..15 game units) and let
		# l2_proc_tex make the material emissive (the glass glows).
		if tobj == "DE_V_cube_deco3":
			var parrs: Array = mesh.surface_get_arrays(si)
			var pverts: PackedVector3Array = parrs[Mesh.ARRAY_VERTEX]
			if pverts.size() > 0:
				var paabb := AABB(pverts[0], Vector3.ZERO)
				for pv in pverts:
					paabb = paabb.expand(pv)
				_plafond_center[key] = paabb.get_center()
		# MODERN-PORT RULE: the client-derived PBR shader for every texture
		# with a generated set (generic lookup). Foliage is EXCLUDED — it
		# needs the alpha-scissor StandardMaterial3D path below (the PBR
		# shader has no alpha support).
		var is_foliage_pkg := _is_foliage_key(key)
		var pm: Material = null
		if not is_foliage_pkg:
			pm = L2ProcTex.material_for(tpkg, tobj, false)
		if pm != null:
			# DEVLOG-158 rev2 (GLM): the lamp frame/socket surfaces keep the
			# PBR pool path (layer 1, cast_shadow ON — the approved plaza
			# shadow look depends on it; the DEVLOG-158 rerouting to
			# layer-2 StandardMaterial twins wiped the carriers' lamp
			# shadows and brightened the whole plaza floor 2x). Instead the
			# head hardware textures (the collar/socket ring + the cage
			# arch over the crystal) get per-key CLONES of the same cached
			# material with a softened pool N*L and a raised pool gain:
			# the collar reads as lit metal, the hood/pole/houses untouched.
			var is_lamp_head := key in [
				"Oren_DEV_S:O_DE_Lamp01", "Oren_DEV_S:O_DE_Lamp02"
			] and tobj in ["DE_V_deco10", "DE_V_roof_deco"]
			if is_lamp_head and pm is ShaderMaterial:
				var frame_m: ShaderMaterial = (pm as ShaderMaterial).duplicate()
				frame_m.set_shader_parameter("lantern_ndl_soft", 0.5)
				frame_m.set_shader_parameter("lantern_pool_gain", _frame_pool_gain)
				# The frame's own lantern pool must never be skipped: at the
				# two player-nearest lanterns the pool skip + the carrier
				# trapped inside the hood left the collar black (the
				# user's "нет оправы" on the central eight).
				frame_m.set_meta("l2_frame_pool", true)
				L2ProcTex.track_pbr_material(frame_m)
				mesh.surface_set_material(si, frame_m)
				continue
			mesh.surface_set_material(si, pm)
			continue
		var tp: String = "%s/textures/%s/Texture/%s.png" % [active_dir, tpkg, tobj]
		if not FileAccess.file_exists(tp):
			tp = "%s/textures/%s/Texture/%s.png" % [active_dir, tpkg.to_lower(), tobj]
		if not FileAccess.file_exists(tp):
			mesh.surface_set_material(si, _static_grey)
			continue
		if true:
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
				# L2 statics render TWO-SIDED: the bridge side walls are
				# single-plane strips whose normals point away from the road;
				# the live client shows them from the road (no backface
				# culling for statics). Without this the bridge "боковины"
				# (the span side walls inside O_DE_Bridge) are invisible.
				# DEVLOG-79 rev2: the client renders L2 statics TWO-SIDED —
				# empirical: the bridge "боковины" (single-plane strips, normals
				# away from the road) are visible from the road in the live
				# client, and the temple facade gaps (the doorway spandrels,
				# DEVLOG-78/79) are filled by the skin's INNER faces only —
				# with backface culling they turn into sky holes. The
				# CULL_BACK experiment (rev2) was reverted.
				m.cull_mode = StandardMaterial3D.CULL_DISABLED
				# Real values (MECHANICS.md, decompiled/original packages):
				# Shader flags carried in materials.json.shader — apply TwoSided.
				# Opacity/OutputBlending are present as object refs/flags but not
				# mapped to floats here (honest limitation; see MECHANICS.md).
				var shader_flags = t.get("shader", null)
				var shader_two_sided: bool = shader_flags is Dictionary and bool(shader_flags.get("two_sided", false))
				# Alpha-scissor for the true foliage textures.
				# DEVLOG-86: the old inline predicate was CASE-SENSITIVE —
				# "field_deco_S" (lowercase) failed begins_with("Field_Deco")
				# and the grass card clusters rendered OPAQUE (the flat gray
				# poly piles).
				# DEVLOG-114 (the user's PERMANENT rule): the cutout is
				# decided BY CONTENT for every foliage key — the new tiles
				# name their leaf/moss textures without "leaf"/"grass"
				# (the 19_19 Darkelf_tree08 moss cards, the tomb banners,
				# the guard's flag rendered OPAQUE). The scissor on an
				# all-opaque alpha is a no-op; the stone meshes in the same
				# packages carry no alpha at all (verified by the scan).
				# The name check remains ONLY for the non-foliage keys (the
				# carpet alpha = a specular/blend mask — never cut).
				var is_foliage_tex := is_foliage_pkg \
						or "grass" in tobj.to_lower() \
						or "leaf" in tobj.to_lower()
				var skey := "%s:%s" % [tpkg.to_lower(), tobj]
				if is_foliage_tex and img.detect_alpha():
					m.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
					m.alpha_scissor_threshold = 0.35
					m.cull_mode = StandardMaterial3D.CULL_DISABLED
				elif skey in ["sylen_temple_t:silen_statue_1",
						"sylen_temple_t:silen_statue_chain",
						"sylen_temple_t:silen_statue_3",
						"sylen_temple_t:silen_statue_4"] \
						and img.detect_alpha():
					# The TRUE transparency-mask non-foliage atlases (the
					# user's 2026-11-21 report — the dark "hat" over the
					# Shillien statue's head): statue_1 carries the
					# head/crown parts with black=transparent surroundings
					# (content-verified: the texture's crown/face parts sit
					# on black; 27% real alpha-0), chain = the masked links
					# (67%). Opaque rendering turned the black texels into
					# the cap. The carpet alphas stay opaque — the
					# DEVLOG-114 rule holds: only the VERIFIED true masks
					# cut, and only by this explicit list.
					m.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
					m.alpha_scissor_threshold = 0.35
					m.cull_mode = StandardMaterial3D.CULL_DISABLED
				elif shader_two_sided or key in _down_floor_meshes:
					m.cull_mode = StandardMaterial3D.CULL_DISABLED
				mesh.surface_set_material(si, m)
				if key == "Oren_DEV_S:O_DE_Bridge" and si == 10:
					print("DIAG bridge floor surface %d: texture applied" % [si])
	# DEVLOG-147 rev4: the per-key placeholder flag — a key whose EVERY
	# surface landed on a StandardMaterial3D (the grey fallback or the
	# staged-PNG placeholder) has NO pool-capable surface; its instances
	# render on layer 2 (omni-lit). Mixed keys split per key instead.
	var tot_surfs := mesh.get_surface_count()
	var std_surfs := 0
	for si in range(tot_surfs):
		if mesh.surface_get_material(si) is StandardMaterial3D:
			std_surfs += 1
	_placeholder_keys[key] = tot_surfs > 0 and std_surfs == tot_surfs
	# DEVLOG-86: the trunk (bark surfaces) AABB for the tree cylinder
	# colliders. The whole-mesh AABB is canopy-wide (the leaf cards span
	# 8 m on tree12) — useless for collision.
	# DEVLOG-112: "tree" in the OBJECT name too — the package-only check
	# skipped the Primitive_FieldOBJ_S trees (the north tile), so their
	# flush fell into the full-trimesh fallback (solid canopy cards).
	if _is_foliage_key(key) \
			and "tree" in (str(parts[0]) + str(parts[1])).to_lower():
		var tb := AABB()
		var have_tb := false
		for si in range(mesh.get_surface_count()):
			if si >= pis.size():
				continue
			var tm := int(pis[si])
			if tm < 0 or tm >= texs.size():
				continue
			if not ("bark" in str(texs[tm].get("object", "")).to_lower()):
				continue
			var tarrs := mesh.surface_get_arrays(si)
			var tvv: PackedVector3Array = tarrs[Mesh.ARRAY_VERTEX]
			if tvv.size() == 0:
				continue
			var sb := AABB(tvv[0], Vector3.ZERO)
			for tv in tvv:
				sb = sb.expand(tv)
			if have_tb:
				tb = tb.merge(sb)
			else:
				tb = sb
				have_tb = true
		if have_tb:
			_foliage_trunk[key] = tb
	# DEVLOG-90: the baked-mesh variant switches its surfaces to the
	# Blender-baked maps (UV2). The collision trimesh is unaffected — the
	# baked variant carries the SAME low-poly geometry as the original.
	# RESTORED 2026-11-21 (the user's rollback order): the stable column
	# state = the top after Blender, the bottom with the 4x upscale
	# texture. The material is REBUILT from the PBR path directly — the
	# DEVLOG-117 SPOM routing hijacked the shared texture keys and the
	# old shader-path check silently stopped firing (the bake was lost).
	if is_baked:
		var base := gp.get_basename()
		var np := base.replace("_baked", "_baked_normal") + ".png"
		var ap := base.replace("_baked", "_baked_ao") + ".png"
		if FileAccess.file_exists(np) and FileAccess.file_exists(ap):
			var btex: Texture2D = load(np)
			var atex: Texture2D = load(ap)
			# the sidecar says which TEXCOORD holds the bake atlas (the
			# Blender exporter's layer order is not the list order)
			var atlas_in_uv2 := true
			var sidecar := base + ".json"
			if FileAccess.file_exists(sidecar):
				var f := FileAccess.open(sidecar, FileAccess.READ)
				var data = JSON.parse_string(f.get_as_text())
				if data is Dictionary:
					atlas_in_uv2 = bool(data.get("atlas_in_uv2", true))
			for bi in range(mesh.get_surface_count()):
				var bmis: int = int(pis[bi]) if bi < pis.size() else -1
				if bmis < 0 or bmis >= texs.size() \
						or not (texs[bmis] is Dictionary):
					continue
				var btex_info: Dictionary = texs[bmis]
				var bpm: Material = L2ProcTex.pbr_material_for(
						btex_info.get("package", ""),
						btex_info.get("object", ""), false)
				if bpm == null:
					continue
				var bdup: ShaderMaterial = bpm.duplicate()
				bdup.set_shader_parameter("use_baked", true)
				bdup.set_shader_parameter("atlas_in_uv2", atlas_in_uv2)
				bdup.set_shader_parameter("baked_normal_tex", btex)
				bdup.set_shader_parameter("baked_ao_tex", atex)
				bdup.set_shader_parameter("relief_gain", 1.2)
				# DEVLOG-101: the user's 4x upscale albedo override — the
				# upscale JPGs live in assets/textures/upscale (only the
				# ornate in001/in019); the surfaces without one keep the
				# client tile texture.
				var up := "res://assets/textures/upscale/%s_albedo_rgb_upscale.jpg" \
						% str(btex_info.get("object", ""))
				if ResourceLoader.exists(up):
					bdup.set_shader_parameter("albedo_tex", load(up))
				mesh.surface_set_material(bi, bdup)
	_mesh_cache[key] = mesh
	# DEVLOG-158 rev4: the surf5 (DE_V_new_deco3) hide REMOVED. The
	# 2026-11-10 (21) "face texture on the hand" fix cut the whole оправа
	# from the render because the band rendered as an OPAQUE sheet (the
	# stale texgen albedo had no alpha_mask — the band's own texture read
	# as a foreign plane across the statue's raised hand). The client
	# texture carries a real openwork mask (36.4% alpha-0 — the window
	# lattice); with the masked albedo + ALPHA_CUTOUT the band is an
	# openwork frame again — the central lanterns' оправа the user
	# reported missing, and the hand artifact dissolves into the rails.
	if key == "Oren_DEV_S:O_DE_Center_obj":
		pass
	return mesh

# Меши, у которых пол имеет нормали, смотрящие вниз (backface culling делает их невидимыми сверху).
# Предвычислено анализатором геометрии glTF.
# The road-strip skip list is EMPTY since 2026-11-13: the "2-m-thick wall"
# shapes and the "49-m terraced ring" were artifacts of the broken
# merged-accessor staging; the re-staged meshes carry the true per-prim
# geometry (O_DE_Btm = a ~0.6-m curb/step piece, not a ring). Nothing in the
# road family is skipped anymore.
var _ROAD_STRIP_SKIP := []
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
	# DEVLOG-110: the non-root lamps are created as before and hidden by
	# the proximity gate (the skip variant changed the rendered look —
	# 13172 px vs base14, the cause under investigation).
	# DEVLOG-129 (the user's order): ALL artificial lighting is REMOVED
	# from the Shillien Temple region — the temple is judged under the
	# natural light only (the sun/the moon). The temple bounds = the same
	# region as tools/l2strict/temple_bsp.py REGION.
	var temple_region := Rect2(25400.0, 8800.0, 6100.0, 8400.0)
	# DEVLOG-144 (the user's order): the artificial lighting INSIDE the
	# village is REMOVED — the street lanterns (O_DE_Lamp01/02, the blue
	# plafonds) become the light sources instead (the lantern pass in
	# _build_meshes). The region = the village terrain-hole bbox; the
	# tunnel corridor (x 15000+) keeps its client lights.
	var village_region := Rect2(5888.0, 11904.0, 9088.0, 9600.0)
	var placed := 0
	var skipped := 0
	var village_skipped := 0
	for actor in map_data["actors"]:
		if actor.get("class") != "Light" or actor.get("deleted"): continue
		var loc: Array = actor["location"]
		if temple_region.has_point(Vector2(loc[0], loc[1])):
			skipped += 1
			continue
		if village_region.has_point(Vector2(loc[0], loc[1])):
			village_skipped += 1
			continue
		var lamp := OmniLight3D.new()
		lamp.position = Vector3(loc[0] * UNIT_SCALE, loc[2] * UNIT_SCALE, loc[1] * UNIT_SCALE)
		lamp.light_color = Color(1.0, 0.9, 0.7)
		# Energy mapping is an adaptation (exact LightBrightness formula not recovered).
		lamp.light_energy = clampf(float(actor.get("light_brightness", 255.0)) / 64.0, 1.0, 8.0)
		lamp.omni_range = maxf(float(actor.get("light_radius", 128.0)) * UNIT_SCALE * 6.0, 3.0)
		lamp.omni_attenuation = 0.25
		lamp.shadow_enabled = false
		lamp.visible = false   # the proximity gate lights them up
		world.add_child(lamp)
		_lamps.append(lamp)
		placed += 1
	print("placed ", placed, " map lights (", _lamps.size(),
			" registered; ", skipped, " temple + ", village_skipped,
			" village skipped)")


func _build_environment() -> void:
	var bright := OS.get_environment("L2_BRIGHT") != ""
	_bright_mode = bright
	var sun := DirectionalLight3D.new()
	# The map's own sun (NSun0) held the static direction until the
	# LIGHTING STAGE opened (the user's order 2026-11-21): the sun now rides
	# the east->zenith->west path per the game clock (_update_daynight);
	# the look_at below is just the first-frame default.
	sun.position = Vector3.ZERO
	add_child(sun)
	sun.look_at(Vector3(-0.663, -0.539, -0.519), Vector3.UP)
	sun.light_energy = 5.0
	sun.shadow_enabled = true
	_sun = sun
	# DEVLOG-132 (the user's order: "сравнивай со старым кодом"): the shadow
	# setup is REVERTED TO THE OLD WORKING CODE — no bias/normal-bias/blur
	# overrides (the Godot defaults 0.1/2.0/1.0, PSSM4). The DEVLOG-120
	# overrides were the temple PWM band-aid; the PWM's root (the moon's
	# moving shadows) is gone since DEVLOG-125, so the defaults are safe
	# again. The 08:47 all-shadow-within-range defect remains undiagnosed
	# at the mechanism level; the A/B flag below localizes it.
	if OS.get_environment("L2_SUN_NOSHADOW") != "":
		sun.shadow_enabled = false  # the A/B diagnostic: the shadow map vs
			# the rest of the lighting path (the user runs and screenshots)
	# DEVLOG-110 NOTE: directional_shadow_max_distance=300 KILLED the sun's
	# direct light entirely in the compatibility renderer (the village
	# went night-dark) — the setting is unusable there; do not retry.
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	# The lighting stage is OPEN (the user's 2026-11-21 order): the overcast
	# weather + the day/night cycle drive the sky per frame in
	# _update_daynight. The colors below are the first-frame defaults.
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.2, 0.3, 0.5)
	sky_mat.sky_horizon_color = Color(0.45, 0.5, 0.55)
	sky.sky_material = sky_mat
	_sky_mat = sky_mat
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
	# ONLY for the normal scene: the L2_BRIGHT diagnostic needs the flat
	# white ambient to survive (the zone block used to overwrite it).
	if not bright:
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.395, 0.395, 0.395)
		env.ambient_light_energy = 60.0 / 255.0 * 2.0
		# DEVLOG-122 (the user's weather order): the ground fog is REMOVED —
		# "в пасмурную погоду затянутое небо, но земля без тумана". The
		# overcast is the SKY (the cloud dome below), not a ground haze.
		# The client's ZoneInfo DistanceFog stays recorded here for the
		# restore: FogColor RGB(24,29,35), Start 1 m / End 100 m (depth).
		# Re-enable env.fog_mode/fog_light_color/fog_depth_* + fog_enabled
		# to bring the client haze back.
	_env_ref = env
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	if not bright:
		# THE DAY/NIGHT CLOCK (the user's 2026-11-21): a game day = 4 real
		# hours, the night = 1 of them. L2_TIME pins the start hour (the
		# DEFAULT = RANDOM — the user compares the sun angle / shadows /
		# lighting across launches); L2_TIME_SCALE multiplies the clock
		# speed for tests. The full moon rides the anti-sun.
		var tod_env := OS.get_environment("L2_TIME")
		if tod_env != "":
			_tod_clock = clampf(float(tod_env), 0.0, 24.0)
		else:
			_tod_clock = randf_range(0.0, 24.0)
		var ts := OS.get_environment("L2_TIME_SCALE")
		_tod_rate = float(ts) if ts != "" else 1.0
		_moon = DirectionalLight3D.new()
		_moon.light_color = Color(0.72, 0.8, 1.0)
		# DEVLOG-125: the moon carries NO shadows — the user's "LED PWM on
		# the moonlit stairs" was the moving light direction re-rasterizing
		# the shadow map per frame; the client's night has no dynamic
		# shadows, the moon is a soft fill light.
		_moon.visible = false
		add_child(_moon)
		# the moon disc: an unshaded alpha quad with the fog DISABLED — the
		# depth fog at 700 m blackened the sprite into the "eclipse" (the
		# user's report) and the premultiplied blend leaked the outside-RGB
		# ring; the premultiplied-safe texture + the opaque-ish quad kill both.
		var moon_mesh := QuadMesh.new()
		moon_mesh.size = Vector2(46.0, 46.0)  # ~3.8 deg at 700 m
		var moon_mat := StandardMaterial3D.new()
		moon_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		moon_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		moon_mat.albedo_texture = load("res://assets/textures/sky/moon_full.png")
		moon_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
		if "disable_fog" in moon_mat:
			moon_mat.disable_fog = true
		moon_mesh.material = moon_mat
		_moon_quad = MeshInstance3D.new()
		_moon_quad.mesh = moon_mesh
		_moon_quad.visible = false
		add_child(_moon_quad)
		_update_daynight()
		print("day/night: game time %.2f h%s, sun elev %.1f deg" % [
				_tod_clock,
				" (L2_TIME)" if tod_env != "" else " (random)",
				rad_to_deg(asin(clampf(_tod_sun_dir().y, -1.0, 1.0)))])
	# the ONE world sky dome (DEVLOG-139): the procedural cloud cover on a
	# camera-following sphere for EVERY tile and region — the clouds are a
	# geographic field (world_clouds.png), the sun disc rides the dome and
	# is masked by the clouds. Created in BOTH modes (the L2_BRIGHT
	# diagnostic keeps the day-default dome — unshaded, ambient-independent)
	var dome_mesh := SphereMesh.new()
	dome_mesh.radius = 780.0
	dome_mesh.height = 1560.0
	dome_mesh.radial_segments = 48
	dome_mesh.rings = 24
	var dome_mat := ShaderMaterial.new()
	dome_mat.shader = load("res://assets/shaders/l2_sky_clouds.gdshader")
	# DEVLOG-141: the geographic cloudiness atlas — the dome reads it per
	# fragment (the clouds belong to the territories and are visible from
	# the neighboring maps), world.gd reads it above the camera for the sun
	var atlas_tex: Texture2D = load("res://assets/textures/sky/world_clouds.png")
	if atlas_tex == null:
		print("WARN: the cloud atlas failed to load — the dome reads the dense default")
	else:
		print("CLOUD ATLAS: %dx%d bound" % [atlas_tex.get_width(), atlas_tex.get_height()])
	dome_mat.set_shader_parameter("cloud_atlas", atlas_tex)
	dome_mat.set_shader_parameter("atlas_rect", Vector4(
			CLOUD_ATLAS_RECT.position.x * UNIT_SCALE,
			CLOUD_ATLAS_RECT.position.y * UNIT_SCALE,
			CLOUD_ATLAS_RECT.size.x * UNIT_SCALE,
			CLOUD_ATLAS_RECT.size.y * UNIT_SCALE))
	dome_mesh.material = dome_mat
	_sky_dome_mat = dome_mat
	_sky_dome = MeshInstance3D.new()
	_sky_dome.mesh = dome_mesh
	add_child(_sky_dome)
	# DEVLOG-139: the CPU copy of the same atlas drives the sun energy, so
	# the light always agrees with the sky the player sees.
	_cloud_img = Image.new()
	if _cloud_img.load("res://assets/textures/sky/world_clouds.png") != OK:
		_cloud_img = null
		print("WARN: world_clouds.png failed to load")


## The sun's sky direction at the current game clock: east (+X) horizon at
## 04:30, the ZENITH at 13:30, west (-X) horizon at 22:30; the rest of the
## night the circle continues below the horizon (sin(a) < 0).
func _tod_sun_dir() -> Vector3:
	var a := PI * (_tod_clock - 4.5) / 18.0
	return Vector3(cos(a), sin(a), 0.0)


## Point a directional light so it TRAVELS along dir (the light emits along
## -Z). Guards the near-zenith degenerate (dir anti-parallel to UP breaks
## look_at).
func _safe_look_at(node: Node3D, dir: Vector3) -> void:
	var t := dir
	if absf(t.y) > 0.999:
		t.z = 0.0001
		t = t.normalized()
	node.look_at(t * 100.0, Vector3.UP)


## The day/night driver (DEVLOG-120): the sky palette, the sun
## energy/color by elevation, the full moon on the anti-sun path, the
## zone-ambient day/night modulation.
## DEVLOG-138: the sun/moon/ambient made GLOBAL (no region branches).
## DEVLOG-139 (the user's order): ONE sky dome for the whole map — the
## clouds are a geographic field (the world atlas), the sun WORKS WITH
## THE CLOUDS (its energy is modulated by the cloudiness above the
## camera, the same field the dome draws) instead of any baked per-region
## light, and there is NO fog anywhere ("территории всегда светлые").
## No region switches remain to tune: the transitions live in the sky.
func _update_daynight() -> void:
	if _sun == null or _env_ref == null:
		return
	var to_sun := _tod_sun_dir()
	var e := to_sun.y
	_safe_look_at(_sun, -to_sun)
	# DEVLOG-129 (the user's clarification): the 30 Hz quantization is THE
	# MOON's — its direction updates at 30 Hz (the temple lamps are gone
	# entirely, the region skip above); the sun stays per-frame.
	if _moon != null:
		var tick := int(Time.get_ticks_msec() / 33)
		if tick != _last_light_tick:
			_last_light_tick = tick
			_safe_look_at(_moon, to_sun)  # the moon travels opposite the sun
	var day_f := smoothstep(0.05, 0.45, e)
	var dusk_f := smoothstep(-0.08, 0.15, e) * (1.0 - smoothstep(0.15, 0.45, e))
	var night_f := 1.0 - smoothstep(-0.08, 0.15, e)
	# the cloudiness above the camera (the world atlas, the bilinear read)
	var c_local := 1.0
	var wcam := get_viewport().get_camera_3d()
	if wcam != null:
		c_local = _cloud_at(wcam.global_position.x / UNIT_SCALE,
				wcam.global_position.z / UNIT_SCALE)
	# the sun works with the weather: the clear sky = the stronger direct
	# sun (3.4), the full overcast = the approved dimmer 2.8; warm at
	# sunrise/sunset, near-white at the zenith
	_sun.light_energy = lerpf(3.4, 2.8, c_local) * smoothstep(0.02, 0.5, e)
	_sun.light_color = Color(1.0, 0.75, 0.5).lerp(Color(1.0, 0.97, 0.93),
			smoothstep(0.05, 0.55, e))
	_sun.visible = _sun.light_energy > 0.02
	# the moon light: the full moon, bluish, night only (0.18 — the client's
	# night is near-black; the pale ornate albedos (ai_007 = 0.331 mean vs
	# the walls' 0.16) read FIRST at any brighter moon — the user's
	# "the horns stand out at night" reports)
	if _moon != null:
		_moon.light_energy = 0.18 * night_f
		_moon.visible = _moon.light_energy > 0.02
	# DEVLOG-149: the lantern day/night curve (the user's "пересветил" —
	# the omnis burned at full power at NOON, flooding the village; the
	# client's lamps are off at day). The lamps ramp on at dusk, off at
	# morning; the shader pools ride the same factor (lantern_night).
	var lamp_f := 1.0 - smoothstep(-0.05, 0.10, e)
	# DEVLOG-149: THE VILLAGE IS A CAVE (the user's order: "солнце не
	# должно влиять, локация в пещере") — the sun and the moon fade to
	# zero across a 15 m feathered boundary of the village bbox; the
	# lanterns own the cave lighting, and inside the cave they burn around
	# the clock (there is no day in a cave — this also fixes the "middle
	# lanterns do not work" daytime reports).
	if wcam != null:
		var ppos := wcam.global_position / UNIT_SCALE
		var ddx := maxf(maxf(5888.0 - ppos.x, ppos.x - 14976.0), 0.0)
		var ddz := maxf(maxf(11904.0 - ppos.z, ppos.z - 21504.0), 0.0)
		var outside := sqrt(ddx * ddx + ddz * ddz)
		var cave_f := 1.0 - smoothstep(0.0, 15.0, outside)
		_sun.light_energy *= (1.0 - cave_f)
		_sun.visible = _sun.light_energy > 0.02
		if _moon != null:
			_moon.light_energy *= (1.0 - cave_f)
			_moon.visible = _moon.light_energy > 0.02
		lamp_f = maxf(lamp_f, cave_f)
	if absf(lamp_f - _lamp_f_prev) > 0.004:
		_lamp_f_prev = lamp_f
		for l in _lantern_omnis:
			# DEVLOG-150: 10.0 = the pool's lantern_energy (the physical
			# inverse-square falloff dims ~25x faster than the old curve —
			# the energy is rebalanced so a lamp at 2-3 m matches the old
			# brightness and the far field dies).
			l.light_energy = 10.0 * lamp_f
		L2ProcTex.set_lantern_night(lamp_f)
	_lamp_f = lamp_f
	# the moon disc follows the camera (the sky object, depth-tested so the
	# terrain occludes it; the fog is disabled on its material)
	if _moon_quad != null:
		var cam := get_viewport().get_camera_3d()
		if cam != null:
			var to_moon := -to_sun
			_moon_quad.position = cam.global_position + to_moon * 700.0
			_moon_quad.visible = to_moon.y > 0.02 and night_f > 0.02
	# the zone ambient (the COLOR source): the night floors to 12% of the
	# tuned day value — one ambient for the whole world
	_env_ref.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	_env_ref.ambient_light_energy = 0.47 * (0.12 + 0.88 * maxf(day_f, dusk_f * 0.8))
	_env_ref.ambient_light_color = Color(0.395, 0.395, 0.395).lerp(
			Color(0.33, 0.35, 0.42), night_f)
	# the ONE dome: follows the camera; the cloud density = the geographic
	# atlas per fragment (the clouds belong to the territories, DEVLOG-141),
	# the sun disc glows through the semi-transparent veil
	if _sky_dome != null and _sky_dome_mat != null:
		var cam := get_viewport().get_camera_3d()
		if cam != null:
			_sky_dome.position = cam.global_position
			_sky_dome_mat.set_shader_parameter("cam_ws", cam.global_position)
		_sky_dome.visible = true
		_sky_dome_mat.set_shader_parameter("day_f", day_f)
		_sky_dome_mat.set_shader_parameter("dusk_f", dusk_f)
		_sky_dome_mat.set_shader_parameter("night_f", night_f)
		_sky_dome_mat.set_shader_parameter("drift", _tod_clock * 0.5)
		_sky_dome_mat.set_shader_parameter("sun_dir_ws", to_sun)
		_sky_dome_mat.set_shader_parameter("sun_disc_amount",
				smoothstep(-0.08, 0.06, e))
	# DEVLOG-139: NO fog anywhere (the client's ZoneInfo DistanceFog stays
	# recorded in _build_environment for the restore).
	_env_ref.fog_enabled = false


## The on-screen clock (the user's 2026-11-21 request): the game time
## HH:MM + the phase, for the day/night comparisons on the HUD.
func tod_label() -> String:
	var hh := int(_tod_clock)
	var mm := int(round(fmod(_tod_clock, 1.0) * 60.0))
	if mm >= 60:
		hh = (hh + 1) % 24
		mm = 0
	var e := _tod_sun_dir().y
	var phase := "ночь"
	if e > 0.45:
		phase = "день"
	elif e > 0.0:
		phase = "утро/вечер"
	elif e > -0.15:
		phase = "сумерки"
	return "%02d:%02d %s" % [hh, mm, phase]


func _spawn_player() -> void:
	# DEVLOG-144 (the user's order): the respawn = the OLD road point on the
	# path between the DE village and the Shillien Temple (21109,12819,
	# ground -36.66, the route floor-profile spot from the temple-stage
	# session), yaw -1.2313 faces the temple entrance. The village PlayerStart0
	# turned out to be inside a building.
	var start := Vector3(21109.0, 12819.0, -3666.0)
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
	_player = player
	# The diagnostic runs happen on the REAL display, in parallel with the
	# user's own work: their mouse (the right-drag orbit, the wheel zoom,
	# click-to-move) and keyboard (the arrows move the character) reached
	# the game window and contaminated the captures — entrance_road and
	# stairway_plaza baselines differed run-to-run (DEVLOG-111). Ignore ALL
	# input and never take focus while a diagnostic flow is active.
	if OS.get_environment("L2_SCREENSHOT") != "" or OS.get_environment("L2_BURST") != "":
		player.input_locked = true
		DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	player.position = Vector3(start.x * UNIT_SCALE, floor_y * UNIT_SCALE + 0.9, start.y * UNIT_SCALE)
	if OS.get_environment("L2_VIEW_YAW") == "":
		player.yaw = -1.2313  # face the Shillien Temple entrance (atan2(-dx,-dz))
	add_child(player)
	_spawn_physics_frame = Engine.get_physics_frames()
	print("player spawned at ", player.position, " terrain_height=", floor_y * UNIT_SCALE)


## DEVLOG-146 diagnostic: L2_LIGHT_CAP_AUDIT=1 — the compat renderer lights
## each object with at most 8 lights (a compile-time cap; the
## max_lights_per_object project setting does not raise it), chosen from the
## lights whose range sphere intersects the OBJECT's AABB. Objects
## overlapping MORE than 8 lights get an angle-dependent subset (the
## frustum-cull order decides) — "the pools disconnect at whole camera
## angles". The audit counts, for every visible MeshInstance3D, the visible
## omni lights intersecting its world AABB, and prints the objects past 8.
func _light_cap_audit() -> void:
	await get_tree().create_timer(1.2).timeout  # the lamp gate's first toggle
	var lights: Array[OmniLight3D] = []
	for c in world.get_children():
		if c is OmniLight3D and c.visible:
			lights.append(c)
	print("LIGHT CAP AUDIT: ", lights.size(), " visible omni lights")
	var rows := []
	for c in world.get_children():
		if c is MeshInstance3D and c.visible and c.mesh != null:
			var aabb: AABB = c.global_transform * c.get_aabb()
			var n := 0
			for l in lights:
				var cp: Vector3 = l.global_position.clamp(
						aabb.position, aabb.position + aabb.size)
				if cp.distance_to(l.global_position) <= l.omni_range:
					n += 1
			rows.append([n, aabb])
	rows.sort_custom(func(a, b): return a[0] > b[0])
	var over := 0
	for r in rows:
		if r[0] > 8:
			over += 1
	print("LIGHT CAP AUDIT: ", rows.size(), " mesh instances, ", over,
			" overlap more than 8 lights")
	for r in rows.slice(0, 40):
		var ab: AABB = r[1]
		print("  lights=%3d  aabb pos=(%.1f, %.1f, %.1f) size=(%.1f, %.1f, %.1f)"
				% [r[0], ab.position.x, ab.position.y, ab.position.z,
				ab.size.x, ab.size.y, ab.size.z])
