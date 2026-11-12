## Clean-room procedural material library (MODERN-PORT RULE, AGENTS.md):
## road/ground surfaces are synthesized by assets/shaders/l2_procedural.gdshader
## — no PNG textures in the render path. The shader params (palettes, tile
## sizes, pattern metrics) were derived by observation from the original
## client textures (clean-room reference study, DEVLOG 2026-11-12).
## 1:1 identity is verified per the project rule: spawn screenshots compared
## against Docs/DE_village.png and the user's live captures.
class_name L2ProcTex

const SHADER_PATH := "res://assets/shaders/l2_procedural.gdshader"

## tex key "pkg:obj" -> shader config. pkg is the STAGED package name
## (lower-case directories in assets/maps/20_18/textures/).
const CONFIG := {
	"oren_dev_t:DE_V_floor01": {"mode": 0, "tile": Vector2(256, 256), "relief": 1.0},
	"oren_dev_t:DE_V_floor02": {"mode": 1, "tile": Vector2(256, 256), "relief": 0.7},
	"oren_dev_t:DE_V_m12": {"mode": 2, "tile": Vector2(512, 512), "relief": 0.8},
	"oren_dev_t:O_dark_01": {"mode": 3, "tile": Vector2(512, 512), "relief": 0.6},
	"sylen_temple_t:oren_sylen_001_1": {"mode": 4, "tile": Vector2(256, 256), "relief": 0.8},
	"oren_dev_t:DE_V_capet01": {"mode": 5, "tile": Vector2(128, 256), "relief": 0.35},
	"oren_dev_t:DE_V_capet02": {"mode": 6, "tile": Vector2(256, 256), "relief": 0.35},
	"oren_dev_t:DE_V_capet": {"mode": 7, "tile": Vector2(128, 256), "relief": 0.35},
}

static var _shader: Shader = null
static var _cache := {}

## Returns a ShaderMaterial for a procedural texture, or null when the
## texture has no procedural mode. `uv_is_texels`: BSP glTFs carry raw
## texel UVs, UModel statics carry normalized 0..1 UVs.
static func material_for(pkg: String, obj: String, uv_is_texels: bool) -> Material:
	# package casing varies between import names and staged dirs
	var key := "%s:%s" % [pkg.to_lower(), obj]
	var cfg: Variant = CONFIG.get(key)
	if cfg == null:
		return null
	# same texture may be consumed by both uv conventions — cache per key+flag
	var ck := "%s|%s" % [key, "t" if uv_is_texels else "u"]
	if _cache.has(ck):
		return _cache[ck]
	if _shader == null:
		_shader = load(SHADER_PATH)
		if _shader == null:
			push_error("l2_proc_tex: shader missing " + SHADER_PATH)
			return null
	var m := ShaderMaterial.new()
	m.shader = _shader
	m.set_shader_parameter("mode", int(cfg["mode"]))
	m.set_shader_parameter("tile_px", cfg["tile"])
	m.set_shader_parameter("uv_is_texels", uv_is_texels)
	m.set_shader_parameter("relief", float(cfg["relief"]))
	m.set_shader_parameter("roughness_f", 0.92 if int(cfg["mode"]) < 5 else 0.98)
	_cache[ck] = m
	return m
