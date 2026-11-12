// The client-derived PBR surface shader (the user's directive 2026-11-13:
// textures 1:1 with the client — the client PNG is the PATTERN SOURCE, we add
// the modern volumetric layers: albedo 1:1 + height-driven parallax occlusion
// mapping + painted-luminance normals + roughness; see tools/l2strict/
// texgen.py which generates the sets).
//
// POM without mesh tangents: the BSP meshes carry none — the tangent basis is
// derived per-pixel from the screen-Jacobian of UV/position (dPdu/dPdv solve).
// UVs: BSP glTFs = raw TEXELS (uv_is_texels=true); UModel statics = 0..1 per
// tile (uv_is_texels=false, multiplied by tile_px).
shader_type spatial;
render_mode world_vertex_coords, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap, repeat_enable;
uniform bool uv_is_texels = true;
uniform vec2 tile_px = vec2(256.0, 256.0);
uniform float pom_scale = 0.05;  // visual depth, meters
uniform int pom_steps : hint_range(4, 32) = 16;
uniform float relief_gain = 1.0; // extra normal strength multiplier
uniform float rough_gain : hint_range(0.0, 1.0) = 0.9;
uniform float detail = 0.0;      // optional world-space grain (0 = pure client)
uniform bool use_alpha = false;  // TRUE cutout textures only (Iron_net, DE_V_fence
                                 // — the lattice grates). NOT set for the carpet
                                 // family: their alpha is a specular/blend mask.
uniform float alpha_scissor : hint_range(0.0, 1.0) = 0.4;

// ---- simplex noise (Ashima public-domain; only used when detail > 0) ----
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x * 34.0) + 10.0) * x); }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 10.0) * x); }

float snoise3(vec3 v) {
	const vec2 C = vec2(0.16666666666666666, 0.3333333333333333);
	const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
	vec3 i = floor(v + dot(v, C.yyy));
	vec3 x0 = v - i + dot(i, C.xxx);
	vec3 g = step(x0.yzx, x0.xyz);
	vec3 l = 1.0 - g;
	vec3 i1 = min(g.xyz, l.zxy);
	vec3 i2 = max(g.xyz, l.zxy);
	vec3 x1 = x0 - i1 + C.xxx;
	vec3 x2 = x0 - i2 + C.yyy;
	vec3 x3 = x0 - D.yyy;
	i = mod289(i);
	vec4 p = permute(permute(permute(i.z + vec4(0.0, i1.z, i2.z, 1.0))
		+ i.y + vec4(0.0, i1.y, i2.y, 1.0)) + i.x + vec4(0.0, i1.x, i2.x, 1.0));
	float n_ = 0.142857142857;
	vec3 ns = n_ * D.wyz - D.xzx;
	vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
	vec4 x_ = floor(j * ns.z);
	vec4 y_ = floor(j - 7.0 * x_);
	vec4 x = x_ * ns.x + ns.yyyy;
	vec4 y = y_ * ns.x + ns.yyyy;
	vec4 h = 1.0 - abs(x) - abs(y);
	vec4 b0 = vec4(x.xy, y.xy);
	vec4 b1 = vec4(x.zw, y.zw);
	vec4 s0 = floor(b0) * 2.0 + 1.0;
	vec4 s1 = floor(b1) * 2.0 + 1.0;
	vec4 sh = -step(h, vec4(0.0));
	vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
	vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
	vec3 p0 = vec3(a0.xy, h.x);
	vec3 p1 = vec3(a0.zw, h.y);
	vec3 p2 = vec3(a1.xy, h.z);
	vec3 p3 = vec3(a1.zw, h.w);
	vec4 norm = inversesqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
	p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
	vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
	m = m * m;
	return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

void fragment() {
	vec2 uv = uv_is_texels ? UV / tile_px : UV;   // 0..1 per tile
	// per-pixel tangent basis from the screen Jacobian (no mesh tangents)
	vec3 sigX = dFdx(VERTEX);
	vec3 sigY = dFdy(VERTEX);
	float ff = FRONT_FACING ? 1.0 : -1.0;
	vec3 ngeo = normalize(cross(sigX, sigY)) * ff;
	vec2 uvd_x = dFdx(uv);
	vec2 uvd_y = dFdy(uv);
	float mdet = uvd_x.x * uvd_y.y - uvd_x.y * uvd_y.x;
	vec3 dPdu = (sigX * uvd_y.y - sigY * uvd_x.y) / mdet;  // world step of +1 tile-u
	vec3 dPdv = (sigY * uvd_x.x - sigX * uvd_x.y) / mdet;
	vec3 T = normalize(dPdu);
	vec3 B = normalize(dPdv);
	// world -> uv-shifts Jacobian (texels per meter along T/B): |dPdu| meters per tile
	vec2 tile_m = vec2(length(dPdu), length(dPdv)); // meters per full tile

	vec3 view_w = normalize(INV_VIEW_MATRIX[3].xyz - VERTEX); // frag -> camera
	vec3 vt = vec3(dot(view_w, T), dot(view_w, B), dot(view_w, ngeo));

	float h0 = texture(albedo_tex, uv).a;
	vec2 uv_final = uv;
	// Offset mapping (single-sample parallax). The full POM loop caused
	// banding/smear artifacts: implicit-LOD sampling inside a dynamic loop is
	// undefined in GLSL, and grazing angles explode the offsets. The single
	// step + view-angle fade keeps the depth cue without artifacts.
	if (abs(mdet) > 1e-12 && pom_scale > 0.0005) {
		float angle_fade = smoothstep(0.12, 0.45, abs(vt.z));
		vec2 parallax = -vt.xy / max(0.25, abs(vt.z))
			* (pom_scale / max(tile_m, vec2(1e-5))) * (0.6 + 0.4 * h0)
			* angle_fade;
		uv_final = uv + parallax;
	}

	vec4 alb = texture(albedo_tex, uv_final);
	if (use_alpha && alb.a < alpha_scissor) {
		discard;   // the grate holes are see-through
	}
	vec3 nrm = texture(normal_tex, uv_final).rgb * 2.0 - 1.0;
	float rough = texture(normal_tex, uv_final).a;
	if (detail > 0.0) {
		float g = snoise3(VERTEX * 6.0) * 0.5 + snoise3(VERTEX * 21.0) * 0.3;
		alb.rgb *= 1.0 + 0.06 * detail * g;
	}
	ALBEDO = alb.rgb;
	NORMAL_MAP = nrm * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = relief_gain;
	ROUGHNESS = clamp(rough * rough_gain, 0.0, 1.0);
	// crevice shading from the height channel — scaled by the POM depth so
	// the flat weaves (pom ~0.012) keep the client's own painted shading
	// without double-darkening it. In alpha-cutout mode A is the transparency
	// mask, not height — no AO from it.
	if (use_alpha) {
		AO = 1.0;
	} else {
		AO = mix(1.0, clamp(0.55 + 0.45 * alb.a, 0.0, 1.0),
				clamp(pom_scale * 20.0, 0.0, 1.0));
	}
	AO_LIGHT_AFFECT = 0.6;
}
