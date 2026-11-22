shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// Dark Elf Village terrain: eight L2 color layers, each with its own mask.
// Layers are blended in slot order over a neutral gray base, matching the
// public l2mapconv terrain renderer. Layer 0 (Obase_1) is the base terrain
// and covers most of the tile; other layers add detail on top.
//
// DEVLOG-129 (the user's order: "the mountains at night are especially
// bad — redo them with SPOM"): the raymarched POM on the DOMINANT layer's
// height field (layer_heights array, the height = the texgen albedo's A
// channel, low-frequency blur 4 — the DEVLOG-89 lesson). The masks stay
// UNSHIFTED (they are the coverage, not the relief); the detail textures
// sample at the displaced uv. The angle/distance fades and the explicit
// textureLod inside the loop = the project's anti-swim lessons
// (2026-11-13 / DEVLOG-88). The dynamic array layer index picks the
// dominant texture per fragment (the sampler arrays index legally).

uniform float do_debug = 0.0;
uniform sampler2D layer_0_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_1_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_2_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_3_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_4_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_5_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_6_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_7_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;

uniform sampler2D mask_0 : source_color;
uniform sampler2D mask_1 : source_color;
uniform sampler2D mask_2 : source_color;
uniform sampler2D mask_3 : source_color;
uniform sampler2D mask_4 : source_color;
uniform sampler2D mask_5 : source_color;
uniform sampler2D mask_6 : source_color;
uniform sampler2D mask_7 : source_color;

uniform vec2 layer_0_uv_scale = vec2(1.0);
uniform vec2 layer_1_uv_scale = vec2(1.0);
uniform vec2 layer_2_uv_scale = vec2(1.0);
uniform vec2 layer_3_uv_scale = vec2(1.0);
uniform vec2 layer_4_uv_scale = vec2(1.0);
uniform vec2 layer_5_uv_scale = vec2(1.0);
uniform vec2 layer_6_uv_scale = vec2(1.0);
uniform vec2 layer_7_uv_scale = vec2(1.0);

uniform vec2 layer_0_uv_offset = vec2(0.0);
uniform vec2 layer_1_uv_offset = vec2(0.0);
uniform vec2 layer_2_uv_offset = vec2(0.0);
uniform vec2 layer_3_uv_offset = vec2(0.0);
uniform vec2 layer_4_uv_offset = vec2(0.0);
uniform vec2 layer_5_uv_offset = vec2(0.0);
uniform vec2 layer_6_uv_offset = vec2(0.0);
uniform vec2 layer_7_uv_offset = vec2(0.0);

uniform sampler2DArray layer_heights : filter_linear_mipmap, repeat_enable;
uniform vec2 lscales[8];
uniform float pom_scale = 0.04;  // the terrain relief depth, meters
uniform int pom_min_layers : hint_range(8, 64, 1) = 8;
uniform int pom_max_layers : hint_range(8, 64, 1) = 32;

varying vec2 tile_uv;

void vertex() {
	tile_uv = UV;
}

void fragment() {
	// the masks first — the dominant layer for the POM march comes from
	// them (the layer boundaries are the COVERAGE: the masks never shift)
	vec2 mask_uv = tile_uv;
	float mw0 = texture(mask_1, mask_uv).r;
	float mw1 = texture(mask_2, mask_uv).r;
	float mw2 = texture(mask_3, mask_uv).r;
	float mw3 = texture(mask_4, mask_uv).r;
	float mw4 = texture(mask_5, mask_uv).r;
	float mw5 = texture(mask_6, mask_uv).r;
	float mw6 = texture(mask_7, mask_uv).r;
	int dom = 0;
	float wmax = 0.15;
	if (mw0 > wmax) { wmax = mw0; dom = 1; }
	if (mw1 > wmax) { wmax = mw1; dom = 2; }
	if (mw2 > wmax) { wmax = mw2; dom = 3; }
	if (mw3 > wmax) { wmax = mw3; dom = 4; }
	if (mw4 > wmax) { wmax = mw4; dom = 5; }
	if (mw5 > wmax) { wmax = mw5; dom = 6; }
	if (mw6 > wmax) { wmax = mw6; dom = 7; }
	// DEVLOG-131 (the user's "the film remains at night on the NEAR
	// mountains"): at the layer boundaries the argmax flips between
	// neighbors, and the march (computed from ONE layer's height field)
	// jumps with it = the shimmering texture slide. The runner-up weight
	// measures the ambiguity; the shift damps where it is not decisive.
	float w2 = 0.0;
	if (dom != 0 && 0.15 > w2) { w2 = 0.15; }
	if (dom != 1 && mw0 > w2) { w2 = mw0; }
	if (dom != 2 && mw1 > w2) { w2 = mw1; }
	if (dom != 3 && mw2 > w2) { w2 = mw2; }
	if (dom != 4 && mw3 > w2) { w2 = mw3; }
	if (dom != 5 && mw4 > w2) { w2 = mw4; }
	if (dom != 6 && mw5 > w2) { w2 = mw5; }
	if (dom != 7 && mw6 > w2) { w2 = mw6; }
	float dom_margin = smoothstep(0.05, 0.3, wmax - w2);

	// the POM march on the dominant layer's height field
	vec2 pom_shift = vec2(0.0);
	// the jac tangent frame (the view space; the lengths = the world)
	vec3 sigX = dFdx(VERTEX);
	vec3 sigY = dFdy(VERTEX);
	vec2 uvd_x = dFdx(tile_uv);
	vec2 uvd_y = dFdy(tile_uv);
	float mdet = uvd_x.x * uvd_y.y - uvd_x.y * uvd_y.x;
	vec3 dPdu = (sigX * uvd_y.y - sigY * uvd_x.y) / mdet;
	vec3 dPdv = (sigY * uvd_x.x - sigX * uvd_x.y) / mdet;
	vec3 T = normalize(dPdu);
	vec3 B = normalize(dPdv);
	float ff = FRONT_FACING ? 1.0 : -1.0;
	vec3 ngeo = normalize(cross(sigX, sigY)) * ff;
	float tile_m = length(dPdu);  // the meters per tile-u (~327.68)
	vec3 view_v = normalize(-VERTEX);  // the frag -> camera (the view space)
	vec3 vt = vec3(dot(view_v, T), dot(view_v, B), dot(view_v, ngeo));

	if (abs(mdet) > 1e-12 && pom_scale > 0.0005) {
		// DEVLOG-131: the fades tightened (the angle 0.25..0.55, the
		// distance 25..70 m, the scale 0.04) — at night the weak flat
		// light made the view-dependent texture slide read as a film on
		// the near slopes; the march now dies earlier at the grazing
		// angles and closer in.
		float angle_fade = smoothstep(0.25, 0.55, abs(vt.z));
		float dist_fade = 1.0 - smoothstep(25.0, 70.0, length(VERTEX));
		float num_layers = mix(float(pom_max_layers), float(pom_min_layers),
				abs(vt.z));
		float layer_depth = 1.0 / num_layers;
		vec2 ray_tile = vt.xy / max(0.25, abs(vt.z))
				* (pom_scale / max(tile_m, 1e-5));
		vec2 ray_l = clamp(ray_tile * lscales[dom],
				vec2(-0.35), vec2(0.35));
		vec2 luv0 = tile_uv * lscales[dom];
		float cd = 0.0;
		float ch = 1.0 - texture(layer_heights, vec3(luv0, float(dom))).a;
		vec2 uvc = luv0;
		int steps = int(num_layers);
		for (int i = 0; i < 64; i++) {
			if (i >= steps || ch <= cd) {
				break;
			}
			uvc -= ray_l * layer_depth;
			cd += layer_depth;
			ch = 1.0 - texture(layer_heights, vec3(uvc, float(dom))).a;
		}
		if (ch > cd) {
			uvc = luv0;  // never pierced (the flat texel / grazing) — no shift
		} else {
			vec2 uvp = uvc + ray_l * layer_depth;
			float ph = 1.0 - texture(layer_heights, vec3(uvp, float(dom))).a;
			float pd = cd - layer_depth;
			float tw = clamp((ph - pd)
					/ ((cd - pd) + (ph - ch) + 1e-6), 0.0, 1.0);
			uvc = mix(uvp, uvc, tw);
		}
		// the march shift back into the tile_uv units, faded
		vec2 shift_tile = (luv0 - uvc) / max(lscales[dom], vec2(1e-5));
		pom_shift = shift_tile * angle_fade * dist_fade * dom_margin;
	}

	// the detail textures sample at the DISPLACED tile_uv; the masks at the
	// unshifted one. The blend order and the base layer are unchanged.
	vec2 duv = tile_uv - pom_shift;
	vec3 color = vec3(0.35);
	color = texture(layer_0_texture, duv * layer_0_uv_scale + layer_0_uv_offset).rgb;
	color = mix(color, texture(layer_1_texture, duv * layer_1_uv_scale + layer_1_uv_offset).rgb, mw0);
	color = mix(color, texture(layer_2_texture, duv * layer_2_uv_scale + layer_2_uv_offset).rgb, mw1);
	color = mix(color, texture(layer_3_texture, duv * layer_3_uv_scale + layer_3_uv_offset).rgb, mw2);
	color = mix(color, texture(layer_4_texture, duv * layer_4_uv_scale + layer_4_uv_offset).rgb, mw3);
	color = mix(color, texture(layer_5_texture, duv * layer_5_uv_scale + layer_5_uv_offset).rgb, mw4);
	color = mix(color, texture(layer_6_texture, duv * layer_6_uv_scale + layer_6_uv_offset).rgb, mw5);
	color = mix(color, texture(layer_7_texture, duv * layer_7_uv_scale + layer_7_uv_offset).rgb, mw6);

	// L2_TERRAIN_DEBUG=uv -> paint tile_uv; =masks -> paint mask weights
	if (do_debug > 0.5) {
		ALBEDO = vec3(tile_uv.x, tile_uv.y, 0.0);
	} else {
		ALBEDO = color;
	}
	ROUGHNESS = 0.95;
	// DEVLOG-125: the rock slopes under the moonlight sheened (the user's
	// "the rocks get the film at night" — the terrain textures are the
	// direct client transfer, no PBR); the rock is fully matte.
	SPECULAR = 0.0;
}

// DEVLOG-135 (the user's night shot: the ground is PURE BLACK while the
// trees/temple are moonlit — the terrain receives NO sun, NO moon, NO
// ambient). The mesh and its normals are verified healthy (the runtime
// print: 368-393k normals, zero degenerate). The pattern: every material
// with an explicit light() override lights up (the SPOM walls, the PBR
// statics, the foliage StandardMaterial), the ONLY default-light() shader
// in the project — this one — is light-blind in the compatibility
// renderer. The fix = the explicit Lambert path, exactly the proven SPOM
// diffuse term (Godot multiplies ALBEDO outside light(), as the approved
// SPOM shader shows): cNdotL/PI x LIGHT_COLOR (the energy folded in) x
// ATTENUATION (the shadow factor). The env ambient still applies on top
// (it is stage-level, outside light()).
void light() {
	float cNdotL = clamp(dot(NORMAL, normalize(LIGHT)), 0.0, 1.0);
	DIFFUSE_LIGHT += cNdotL * LIGHT_COLOR * ATTENUATION / PI;
}
