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
const TEX_ROOT := "res://assets/maps/20_18/textures"

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
static var _cache := {}

## TRUE transparency-mask textures (the lattice grates — the center-plaza
## floor and the fences). NOT a blanket rule: most L2 alphas are
## specular/blend masks (the carpet family must stay opaque).
const ALPHA_CUTOUT := [
	"oren_dev_t:Iron_net",
	"oren_dev_t:DE_V_fence",
]

## The road texture mechanisms (world-uv, the road samplers, the texture
## substitutions) are ROLLED BACK (the user's verdict 2026-11-14: the
## texture variety at the entrance was lost — "нехватка текстур"). The road
## pieces render their AUTHORED textures and UVs again. Any future seam work
## must not substitute the authored textures.
const WORLD_UV := {}
const ROAD_STONES := []
const TEXTURE_SUBSTITUTE := {}

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
## road = the mesh belongs to the road A->B family: its horizontal road-stone
## faces sample the ONE road texture (floor01) via the shader's road
## samplers, at the single road scale (0.78125 tiles/m).
static func material_for(pkg: String, obj: String, uv_is_texels: bool,
		road: bool = false) -> Material:
	var key := "%s:%s" % [pkg.to_lower(), obj]
	if TEXTURE_SUBSTITUTE.has(key):
		key = TEXTURE_SUBSTITUTE[key]
		var parts := key.split(":")
		pkg = parts[0]
		obj = parts[1]
	var ck := "%s|%s|%s" % [key, "t" if uv_is_texels else "u",
			"r" if road else "s"]
	if _cache.has(ck):
		return _cache[ck]
	var m := _pbr_material(pkg.to_lower(), obj, key, uv_is_texels, road)
	var cfg: Variant = CONFIG.get(key)
	if m == null and cfg != null:
		m = _analytic_material(cfg, uv_is_texels)
	_cache[ck] = m
	return m

static func _pbr_material(pkg_l: String, obj: String, key: String,
		uv_is_texels: bool, road: bool) -> Material:
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
	# M2 (the user's mandate v2): ONE road scale everywhere — 0.78125 tiles/m
	# (200 texels/m of DE_V_floor01) on every road face of both layers.
	# M1: whenever the world-uv override can fire, the road samplers MUST be
	# bound (they carry the ONE road cobble = floor01) — an unbound sampler
	# samples WHITE (the white-plaza regression 2026-11-14: the BSP floor01
	# plates had world_uv but no road samplers).
	if WORLD_UV.has(key) or (road and ROAD_STONES.has(key)):
		m.set_shader_parameter("world_uv_scale", 0.78125)
		var r_alb := _find_pbr("oren_dev_t", "DE_V_floor01", "pbr_albedo.png")
		var r_nrm := _find_pbr("oren_dev_t", "DE_V_floor01", "pbr_normal.png")
		if r_alb != null:
			m.set_shader_parameter("road_albedo_tex", r_alb)
		if r_nrm != null:
			m.set_shader_parameter("road_normal_tex", r_nrm)
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
	return m
