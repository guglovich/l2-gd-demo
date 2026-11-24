## Client-derived PBR material library (the user's directive 2026-11-13:
## textures 1:1 with the CLIENT, not analytic approximations). The pattern
## source = the client PNG; tools/l2strict/texgen.py generates the PBR sets
## from it (albedo 1:1 + height for POM + luminance normals + roughness), and
## assets/shaders/l2_surface_pbr.gdshader renders them with parallax occlusion
## mapping. Identity is exact by construction — the pattern IS the client's.
## The old analytic shader (l2_procedural.gdshader) stays as the FALLBACK for
## textures whose PBR set has not been generated yet.
class_name L2ProcTex

const PBR_SHADER_PATH := "res://assets/shaders/l2_surface_pbr.gdshader"
const ANALYTIC_SHADER_PATH := "res://assets/shaders/l2_procedural.gdshader"
const SPOM_SHADER_PATH := "res://assets/shaders/l2_spom.gdshader"
const TEX_ROOT := "res://assets/maps/20_18/textures"

## The Shillien Temple 3D-texture transition (the user's directive
## 2026-11-21): the temple WALL textures render through SPOM (self shading +
## the POM march with the min/max layer ladder, assets/shaders/
## l2_spom.gdshader — the CC0 godotshaders.com Amose05 shader ported onto
## this project's conventions); the temple FLOOR textures through Godot's
## BUILT-IN heightmap deep parallax (BaseMaterial3D, heightmap_min/max
## layers). Silhouette clipping / horizon erosion stay OFF (the temple UVs
## tile — a 0..1 clip would erase the walls; audited 2026-11-21). pom
## (meters) comes from the texgen sidecar json. All keys are sylen_temple_t:
## the village (oren_dev_t) stays pom=0 (the 2026-11-13 seams fix).
const SPOM_WALLS := [
	"oren_sylen_001", "oren_sylen_001_1", "oren_sylen_003", "oren_sylen_004",
	"oren_sylen_ai_005", "oren_sylen_ai_006", "oren_sylen_ai_007",
	"oren_sylen_ai_008", "oren_sylen_ai_009", "oren_sylen_in001",
	"oren_sylen_in002", "oren_sylen_in005", "oren_sylen_in007",
	"oren_sylen_in008", "oren_sylen_in010", "oren_sylen_in016",
	"oren_sylen_in017", "oren_sylen_in019", "oren_sylen_in020",
	"oren_sylen_in023", "oren_sylen_in024", "oren_sylen_in026",
	"oren_sylen_in031", "oren_sylen_in105", "oren_sylen_in107",
	"oren_sylen_in030",
	"oren_sylen_t004", "oren_sylen_t005", "oren_sylen_t010",
	"oren_sylen_t011", "oren_sylen_t012",
]
## The horizontal temple surfaces (the interior stone floor + the raised
## platform; the same textures also floor the temple court in the level
## BSP) — Godot's built-in heightmap route.
const HEIGHTMAP_FLOORS := ["oren_sylen_ai_004", "oren_sylen_in022"]

## tex key "pkg:obj" -> config. pkg = staged (lower-case) package dir.
##   tile: texture pixel size (texel-UV normalization + statics unit-UV)
##   pom: visual depth in meters for the UV-offset parallax. DISABLED (0.0)
##     everywhere 2026-11-13: at the surface joints the effective offsets
##     differ between neighbors (different pom and meters-per-tile), so the
##     textures visibly "walk" sideways at the seams while the camera moves
##     (the user's floating-seams bug, upper village entrance). The volumetric
##     look stays via normals/roughness/AO; re-enable per texture ONLY after
##     a verified seam-consistent scheme (uniform effective offsets).
##   mode: the analytic fallback mode (see l2_procedural.gdshader header)
const CONFIG := {
	"oren_dev_t:DE_V_floor01": {"tile": Vector2(256, 256), "pom": 0.0, "mode": 0},
	"oren_dev_t:DE_V_floor02": {"tile": Vector2(256, 256), "pom": 0.0, "mode": 1},
	"oren_dev_t:DE_V_m12": {"tile": Vector2(512, 512), "pom": 0.0, "mode": 2},
	"oren_dev_t:O_dark_01": {"tile": Vector2(512, 512), "pom": 0.0, "mode": 3},
	"sylen_temple_t:oren_sylen_001_1": {"tile": Vector2(256, 256), "pom": 0.0, "mode": 4},
	"oren_dev_t:DE_V_capet01": {"tile": Vector2(256, 256), "pom": 0.0, "mode": 5},
	"oren_dev_t:DE_V_capet02": {"tile": Vector2(256, 256), "pom": 0.0, "mode": 6},
	"oren_dev_t:DE_V_capet": {"tile": Vector2(128, 256), "pom": 0.0, "mode": 7},
}

static var _pbr_shader: Shader = null
static var _an_shader: Shader = null
static var _spom_shader: Shader = null
static var _cache := {}

## DEVLOG-147: the village lantern plafond centers (godot meters, world
## space) collected by world.gd during the mesh build. The pools render in
## l2_surface_pbr.gdshader itself (the compat renderer's per-object 8-light
## compile-time cap made the omni-driven pools an angle-dependent lottery on
## the big village meshes). The uniform array is FIXED-SIZE (64) in the
## shader — padded with zeros; lantern_count carries the real length.
const LANTERN_ARRAY_MAX := 64
static var _lanterns := PackedVector3Array()
## DEVLOG-159: the village candles (47 client-derived sources: 16 door
## sconces + 31 table candles). Separate warm shader pool — always on,
## short range, deterministic, no real-omni light-cap involvement.
const CANDLE_ARRAY_MAX := 64
static var _candles := PackedVector3Array()
## DEVLOG-147 rev2: EVERY live PBR ShaderMaterial — the _cache originals AND
## the per-BSP-surface duplicates. `_bsp_material` duplicates the cached
## material and a duplicate holds only the parameters set before it was
## made; the lantern push happens at the end of _ready, AFTER all the
## duplicates exist. The first rev walked only _cache — the BSP floors (all
## the village roads/plaza) never received lantern_count and the pools were
## dead everywhere the user looks ("освещение вообще не работает").
static var _tracked: Array[ShaderMaterial] = []

static func register_lantern(p: Vector3) -> void:
	if _lanterns.size() < LANTERN_ARRAY_MAX:
		_lanterns.append(p)

static func register_candle(p: Vector3) -> void:
	if _candles.size() < CANDLE_ARRAY_MAX:
		_candles.append(p)

static func candles_size() -> int:
	return _candles.size()

static func candle_positions() -> PackedVector3Array:
	return _candles

static func candle_uniform() -> PackedVector3Array:
	var arr := PackedVector3Array(_candles)
	while arr.size() < CANDLE_ARRAY_MAX:
		arr.append(Vector3.ZERO)
	return arr

static func track_pbr_material(m: ShaderMaterial) -> void:
	_tracked.append(m)

static func lanterns_size() -> int:
	return _lanterns.size()

## The padded array for a shader uniform vec3[64].
static func lantern_uniform() -> PackedVector3Array:
	var arr := PackedVector3Array(_lanterns)
	while arr.size() < LANTERN_ARRAY_MAX:
		arr.append(Vector3.ZERO)
	return arr

## The tracked list for world.gd (the crystal-pulse pass).
static func tracked_materials() -> Array[ShaderMaterial]:
	return _tracked

## DEVLOG-149: the lantern day/night factor (0 at day, 1 at night) — the
## pools ride it so the village is not flooded with lamp light at noon.
static func set_lantern_night(f: float) -> void:
	for m in _tracked:
		if is_instance_valid(m):
			m.set_shader_parameter("lantern_night", f)

## DEVLOG-150: the registered plafond positions for world.gd's shadow
## carriers (it picks the two nearest to the player each frame).
static func lantern_positions() -> PackedVector3Array:
	return _lanterns

## DEVLOG-150: the shadow-carrier swap — the lantern indices whose pools
## are skipped (their light arrives via the real shadowed omnis instead).
## Only pushed when the pair actually changes.
static var _shadow_pair := Vector2i(-1, -1)
static func set_lantern_shadow(i0: int, i1: int) -> void:
	var pair := Vector2i(i0, i1)
	if pair == _shadow_pair:
		return
	_shadow_pair = pair
	for m in _tracked:
		if is_instance_valid(m):
			# DEVLOG-158 rev2: the lamp frame clones (l2_frame_pool meta)
			# never skip their own lantern — at the two player-nearest
			# lanterns the skip + the carrier trapped inside the hood is
			# exactly what blackened the collar ("нет оправы").
			if m.has_meta("l2_frame_pool"):
				m.set_shader_parameter("lantern_shadow0", -1)
				m.set_shader_parameter("lantern_shadow1", -1)
				continue
			m.set_shader_parameter("lantern_shadow0", i0)
			m.set_shader_parameter("lantern_shadow1", i1)

## Push the lantern uniforms into every tracked PBR material. Called once at
## the end of _ready (after every tile's meshes and BSP surfaces exist);
## materials created later (the character) get the uniforms at creation.
static func apply_lanterns() -> void:
	if _pbr_shader == null:
		return
	var arr := lantern_uniform()
	var live := 0
	var n_pbr := 0
	var n_an := 0
	for m in _tracked:
		if is_instance_valid(m):
			m.set_shader_parameter("lantern_pos", arr)
			m.set_shader_parameter("lantern_count", _lanterns.size())
			live += 1
			if m.shader == _pbr_shader:
				n_pbr += 1
			elif _an_shader != null and m.shader == _an_shader:
				n_an += 1
	print("lantern pools: ", _lanterns.size(), " positions -> ", live,
			" tracked materials (pbr ", n_pbr, ", analytic ", n_an, ")")

## DEVLOG-159: push the fixed candle positions into every live PBR material.
## The flicker lives in the shader (TIME + a position-derived phase), so this
## is a one-time push, exactly like the lantern pool bootstrap.
static func apply_candles() -> void:
	if _pbr_shader == null:
		return
	var arr := candle_uniform()
	var live := 0
	for m in _tracked:
		if is_instance_valid(m):
			m.set_shader_parameter("candle_pos", arr)
			m.set_shader_parameter("candle_count", _candles.size())
			live += 1
	print("candle pools: ", _candles.size(), " positions -> ", live,
			" tracked materials")

## DEVLOG-162: the two player-nearest candles are carried by real shadowed
## omnis; skip their shader-pool indices so the light cannot leak through walls.
static var _candle_shadow_pair := Vector2i(-1, -1)
static func set_candle_shadow(i0: int, i1: int) -> void:
	var pair := Vector2i(i0, i1)
	if pair == _candle_shadow_pair:
		return
	_candle_shadow_pair = pair
	for m in _tracked:
		if is_instance_valid(m):
			m.set_shader_parameter("candle_shadow0", i0)
			m.set_shader_parameter("candle_shadow1", i1)

## TRUE transparency-mask textures (the lattice grates — the center-plaza
## floor and the fences). NOT a blanket rule: most L2 alphas are
## specular/blend masks (the carpet family must stay opaque).
const ALPHA_CUTOUT := [
	"oren_dev_t:Iron_net",
	"oren_dev_t:DE_V_fence",
	# the central platform lantern frames (DEVLOG-158 rev4, the user's
	# "оправа" on the CENTER village lanterns — NOT the street lamps):
	# the client DE_V_new_deco3 is RGBA with a real openwork mask (36.4%
	# alpha-0, the window lattice band wrapping the O_DE_Center_obj
	# crystals); the staged pbr_albedo A was a stale height field until
	# the 2026-11-24 texgen re-run (A == source alpha, verified 1.0).
	# rev4a: this entry was LOST between the A/B checkouts and never
	# reached the c3c5110 commit — the band rendered opaque ("булыжники
	# без кристаллов", the user's report). Restored + committed now.
	"oren_dev_t:DE_V_new_deco3",
	# the house doorway arch/grate (DEVLOG-164): the client doordeco is
	# RGBA with a real openwork mask (61.1% alpha-0). The staged PBR A was
	# a stale height field, so the grate rendered as a solid black panel.
	# Texgen re-run: A == source alpha (1.0), sidecar alpha_mask=true.
	"interior_b_delf_t:interior_B_delf_doordeco",
	# the Shirai statue spike surface (De_Statue004): the client texture is
	# RGBA with the real spike mask (62.5% transparent); the staged
	# pbr_albedo A now carries it (texgen: source-alpha, 2026-11-23,
	# DEVLOG-154)
	"oren_dev_t:De_Statue004",
	# DEVLOG-130 (the user's "шапка над статуей не пропала"): the Shillien
	# statue's PF_Masked atlases — the palette-0 texels are transparent in
	# the client. The statics scissor branch in world.gd NEVER fired for
	# them: material_for() returns the PBR material first and continues, so
	# the black margins rendered opaque as the "hat". Cut here, by content:
	# the staged PNGs carry the real UModel-exported palette masks
	# (statue_1 27%, 3 17%, 4 28%, chain 66% — chain's transparent
	# background is NON-black RGB, a legit masked layout). statue_2 stays
	# opaque: its staged PNG is RGB (an alpha-less client format — the
	# black texels are genuine paint, not palette 0). The pbr_albedo alphas
	# were stale (built before the staged mask regeneration) — texgen
	# re-run 2026-11-21, the pbr A == the staged A verified 1.000.
	"sylen_temple_t:silen_statue_1",
	"sylen_temple_t:silen_statue_3",
	"sylen_temple_t:silen_statue_4",
	"sylen_temple_t:silen_statue_chain",
]

static func _find_pbr(pkg: String, obj: String, suffix: String) -> Texture2D:
	var p := "%s/%s/Texture/%s.%s" % [TEX_ROOT, pkg.to_lower(), obj, suffix]
	if ResourceLoader.exists(p):
		return load(p)
	return null

## Returns a material for a texture. GENERIC (2026-11-13): any texture with a
## generated PBR set gets the client-derived PBR shader — tile_px is taken
## from the generated texture itself; CONFIG only carries per-texture pom
## overrides (0.0 everywhere since the seams fix) and the analytic fallback
## mode. null = no PBR set (the caller keeps its own placeholder).
## uv_is_texels: BSP glTFs carry raw texel UVs, UModel statics 0..1 per tile.
static func material_for(pkg: String, obj: String, uv_is_texels: bool) -> Material:
	var key := "%s:%s" % [pkg.to_lower(), obj]
	var ck := "%s|%s" % [key, "t" if uv_is_texels else "u"]
	if _cache.has(ck):
		return _cache[ck]
	var pkg_l := pkg.to_lower()
	var m: Material = null
	# The Shillien Temple transition (2026-11-21): walls -> SPOM shader,
	# floors -> Godot's built-in heightmap deep parallax. Everything keyed
	# to sylen_temple_t; the other packages keep the PBR/analytic paths.
	if pkg_l.begins_with("sylen_temple"):
		if HEIGHTMAP_FLOORS.has(obj):
			m = _floor_heightmap_material(pkg_l, obj, key, uv_is_texels)
		elif SPOM_WALLS.has(obj):
			m = _spom_material(pkg_l, obj, key, uv_is_texels)
	if m == null:
		m = _pbr_material(pkg_l, obj, key, uv_is_texels)
	var cfg: Variant = CONFIG.get(key)
	if m == null and cfg != null:
		print("analytic route: ", key)
		m = _analytic_material(cfg, uv_is_texels)
	_cache[ck] = m
	return m


static func _load_sidecar(pkg_l: String, obj: String) -> Dictionary:
	var p := "%s/%s/Texture/%s.pbr.json" % [TEX_ROOT, pkg_l, obj]
	if FileAccess.file_exists(p):
		var f := FileAccess.open(p, FileAccess.READ)
		var d: Variant = JSON.parse_string(f.get_as_text())
		if d is Dictionary:
			return d
	return {}


## The plain client-derived PBR material, BYPASSING the SPOM/floor routing.
## The baked-mesh route (world.gd) calls this for its surfaces: the Blender
## bake lives on l2_surface_pbr.gdshader (the DEVLOG-90/101/102 approved
## look) and must not be hijacked by the temple SPOM routing even when the
## baked mesh shares its textures with the SPOM walls (the DEVLOG-117
## regression: the baked switch keyed on the shader path and silently
## stopped firing). Separate cache suffix — the SPOM and PBR materials for
## the same texture key coexist.
static func pbr_material_for(pkg: String, obj: String, uv_is_texels: bool) -> Material:
	var key := "%s:%s" % [pkg.to_lower(), obj]
	var ck := "%s|%s|pbr" % [key, "t" if uv_is_texels else "u"]
	if _cache.has(ck):
		return _cache[ck]
	var m := _pbr_material(pkg.to_lower(), obj, key, uv_is_texels)
	_cache[ck] = m
	return m


## The temple WALL material: the SPOM shader (the POM march + self shading).
## Height = the albedo's A channel (the same field the normal was sobel'd
## from — the DEVLOG-94 one-height rule). pom meters from the texgen
## sidecar; missing sidecar = no parallax (the flat PBR look).
static func _spom_material(pkg_l: String, obj: String, key: String,
		uv_is_texels: bool) -> Material:
	var alb := _find_pbr(pkg_l, obj, "pbr_albedo.png")
	var nrm := _find_pbr(pkg_l, obj, "pbr_normal.png")
	if alb == null or nrm == null:
		return null
	if _spom_shader == null:
		_spom_shader = load(SPOM_SHADER_PATH)
	if _spom_shader == null:
		return null
	var m := ShaderMaterial.new()
	m.shader = _spom_shader
	m.set_shader_parameter("albedo_tex", alb)
	m.set_shader_parameter("normal_tex", nrm)
	m.set_shader_parameter("uv_is_texels", uv_is_texels)
	m.set_shader_parameter("tile_px", Vector2(alb.get_width(), alb.get_height()))
	m.set_shader_parameter("use_alpha", key in ALPHA_CUTOUT)
	var pom := 0.0
	var side := _load_sidecar(pkg_l, obj)
	if side.has("pom"):
		pom = float(side["pom"])
	if OS.get_environment("L2_SPOM_OFF") != "":
		pom = 0.0
	m.set_shader_parameter("pom_scale", pom)
	# Silhouette carving only on true 0..1-per-face UVs; the temple UVs tile
	# (skin u -5.3..6.3 — audited 2026-11-21), so the carve stays off.
	m.set_shader_parameter("use_silhouette_clipping", false)
	m.set_shader_parameter("use_curved_silhouette", false)
	return m


## The temple FLOOR material: Godot's BUILT-IN heightmap deep parallax
## (BaseMaterial3D, ray-marched, configurable min/max layers — the user's
## directive 2026-11-21). Height = the standalone texgen pbr_height.png,
## the SAME field the albedo's A channel and the normal carry. REQUIRES the
## mesh to carry normals+tangents (world.gd adds them for the temple BSP
## surfaces; the jac-TBN shader path ignores them, so nothing else changes).
static func _floor_heightmap_material(pkg_l: String, obj: String, key: String,
		uv_is_texels: bool) -> Material:
	var alb := _find_pbr(pkg_l, obj, "pbr_albedo.png")
	var nrm := _find_pbr(pkg_l, obj, "pbr_normal.png")
	var hgt := _find_pbr(pkg_l, obj, "pbr_height.png")
	if alb == null or nrm == null or hgt == null:
		return null
	if OS.get_environment("L2_SPOM_OFF") != "":
		return null  # the A/B toggle: fall through to the flat PBR path
	var m := StandardMaterial3D.new()
	m.albedo_texture = alb
	m.normal_enabled = true
	m.normal_texture = nrm
	m.normal_scale = 1.0
	# roughness rides the normal's alpha (painted-bright = smoother), the
	# same channel texgen wrote
	m.roughness_texture = nrm
	m.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_ALPHA
	m.roughness = 1.0
	m.metallic = 0.0
	m.heightmap_enabled = true
	m.heightmap_deep_parallax = true
	m.heightmap_min_layers = 8
	m.heightmap_max_layers = 32
	m.heightmap_texture = hgt
	m.heightmap_scale = 5.0
	if uv_is_texels:
		# raw texel UVs -> 0..1 per tile
		m.uv1_scale = Vector3(1.0 / alb.get_width(), 1.0 / alb.get_height(), 1.0)
	return m

static func _pbr_material(pkg_l: String, obj: String, key: String,
		uv_is_texels: bool) -> Material:
	var alb := _find_pbr(pkg_l, obj, "pbr_albedo.png")
	var nrm := _find_pbr(pkg_l, obj, "pbr_normal.png")
	if alb == null or nrm == null:
		return null
	if _pbr_shader == null:
		_pbr_shader = load(PBR_SHADER_PATH)
	var pom := 0.0
	var cfg: Variant = CONFIG.get(key)
	if cfg != null:
		pom = float(cfg["pom"])
	var m := ShaderMaterial.new()
	m.shader = _pbr_shader
	m.set_shader_parameter("albedo_tex", alb)
	m.set_shader_parameter("normal_tex", nrm)
	m.set_shader_parameter("uv_is_texels", uv_is_texels)
	m.set_shader_parameter("tile_px", Vector2(alb.get_width(), alb.get_height()))
	m.set_shader_parameter("pom_scale", pom)
	m.set_shader_parameter("use_alpha", key in ALPHA_CUTOUT)
	# DEVLOG-159: the two client candle textures glow on their bright warm
	# texels only (the shader derives the mask from albedo color). The door
	# panel's dark rails and the candle holders stay inert.
	# L2_CANDLES_OFF=1 = the before-state A/B.
	if OS.get_environment("L2_CANDLES_OFF") == "" \
			and obj in ["interior_B_delf_candle01", "interior_B_delf_doordeco"]:
		m.set_shader_parameter("candle_glow", 0.35)
	# DEVLOG-144: the DE village lantern plafonds glow (the lamp's own
	# glass emission); every other texture stays inert (the energy 0)
	if obj == "DE_V_cube_deco3":
		m.set_shader_parameter("emission_energy", 1.6)
		# DEVLOG-151 rev2: the FLAT lantern-colored term — the glass
		# albedo is dark (~0.1) and the albedo-scaled pulse read as "the
		# crystals unchanged" (the user's verdict); the flat term makes
		# the crystal itself burn with the lantern blue.
		m.set_shader_parameter("emission_flat", 1.0)
		# DEVLOG-149: the glass meta — world.gd splits the lamp statics so
		# the translucent glass renders without cast_shadow (its shadow
		# would blob the ground under the lamp), and _process breathes the
		# crystal's emission (the user: "кристаллы должны светиться")
		m.set_meta("l2_plafond", true)
	# DEVLOG-147: track every PBR material — the lantern push happens at
	# the end of _ready and must reach it
	track_pbr_material(m)
	return m

static func _analytic_material(cfg: Dictionary, uv_is_texels: bool) -> Material:
	if _an_shader == null:
		_an_shader = load(ANALYTIC_SHADER_PATH)
		if _an_shader == null:
			return null
	var m := ShaderMaterial.new()
	m.shader = _an_shader
	m.set_shader_parameter("mode", int(cfg["mode"]))
	m.set_shader_parameter("tile_px", cfg["tile"])
	m.set_shader_parameter("uv_is_texels", uv_is_texels)
	m.set_shader_parameter("relief", 1.0)
	m.set_shader_parameter("roughness_f", 0.92 if int(cfg["mode"]) < 5 else 0.98)
	# DEVLOG-147 rev4: the analytic materials carry the village lantern
	# pools too (the BSP floors DE_V_floor/DE_V_m12/O_dark_01 route HERE —
	# no staged PBR sets). Tracked like the PBR ones; apply_lanterns pushes
	# the same uniform names into both shaders.
	track_pbr_material(m)
	return m
