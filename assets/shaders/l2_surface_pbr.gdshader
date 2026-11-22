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
// The client renders BSP faces one-sided (UE2 culls backfaces unless the
// section is TwoSided); statics render both sides. Gated per material.
uniform bool cull_back = false;
uniform vec2 tile_px = vec2(256.0, 256.0);
uniform float pom_scale = 0.05;  // visual depth, meters
uniform int pom_steps : hint_range(4, 32) = 16;
uniform float relief_gain = 1.0; // extra normal strength multiplier
uniform float rough_gain : hint_range(0.0, 1.0) = 0.9;
// The direct/indirect specular strength. The DEFAULT 0.5 = Godot's own —
// the approved village look is untouched. The Shillien Temple keys are set
// to 0.0 by l2_proc_tex.gd (the 2026-11-21 "the temple protrusions get the
// gloss in the sun" report — the stone is matte).
uniform float specular_strength : hint_range(0.0, 1.0) = 0.5;
uniform float detail = 0.0;      // optional world-space grain (0 = pure client)
uniform bool use_alpha = false;  // TRUE cutout textures only (Iron_net,
                                 // DE_V_fence — the lattice grates). NOT set
                                 // for the carpet family: their alpha is a
                                 // specular/blend mask.
uniform float alpha_scissor : hint_range(0.0, 1.0) = 0.4;
// DEVLOG-144: the emissive surfaces — the DE village lantern plafonds
// (DE_V_cube_deco3) glow as the lamp's own light; 0 = every other
// texture inert (the village look is untouched).
uniform float emission_energy : hint_range(0.0, 8.0) = 0.0;
// DEVLOG-147: the village lantern POOLS rendered IN THE SHADER. The audit
// (L2_LIGHT_CAP_AUDIT=1, world.gd) proved the mechanism: the compat
// renderer lights each object with at most 8 lights (a compile-time cap;
// the max_lights_per_object project setting does not raise it) chosen from
// the frustum-culled set — the plaza floor alone overlapped 32 lanterns,
// so WHICH pools survived flipped with the camera angle ("отрубаются все
// источники"). The omnis are gone; every PBR surface (the BSP floors, the
// statics, the character body — all share this shader) accumulates the
// pools from the fixed lantern-position array fed by world.gd. Zero
// renderer light lists involved => zero camera dependence, always on.
// lantern_count = 0 everywhere outside the village => inert there.
uniform vec3 lantern_pos[64];       // world-space plafond centers, meters
uniform int lantern_count = 0;
uniform vec3 lantern_color = vec3(0.6, 0.75, 1.0);
// DEVLOG-150: the physical falloff (inverse square, see the pool loop)
// dims ~25x faster than the old (1-d/r)^0.25 — the energy is rebalanced
// so a single lamp's pool at 2-3 m matches the old brightness and the
// far field finally dies (the roofs, the far plaza stay dark).
uniform float lantern_energy = 10.0;
uniform float lantern_range = 22.0;
// DEVLOG-148 rev3: the N*L softening for the BODY materials (the player
// sets 0.5 + energy 4.0): half-flat diffuse makes the black suit readable
// at night. 0 = the approved full-N*L ground pools everywhere else.
uniform float lantern_ndl_soft : hint_range(0.0, 1.0) = 0.0;
// DEVLOG-149: the day/night factor (world.gd, 0 at day — the lamps are
// off at noon; 1 at night) — the pools ride it like the omnis do.
uniform float lantern_night : hint_range(0.0, 1.0) = 1.0;
// DEVLOG-150: the lantern indices currently carried by REAL shadow-casting
// omnis (world.gd's shadow carriers = the two nearest registered lanterns
// to the player). The pool SKIPS them: their light arrives through the
// omnis instead, so the character's shadow finally falls on the ground
// (a shader pool cannot cast one — the user's "теней нету" was true by
// construction). The carrier omni sits at the same plafond position with
// the same range, the SAME curve (Godot's get_omni_attenuation, decay=2)
// and the same energy as the pool => the retarget swap is invisible.
uniform int lantern_shadow0 = -1;
uniform int lantern_shadow1 = -1;

// DEVLOG-147 rev3/rev4 probe trail (kept for the record): the WORLD
// position for the pools = the VERTEX-STAGE VERTEX (world with
// world_vertex_coords — probe 3: the buildings fired with these positions;
// probe 4: the fract decode consistent with the world meters). The
// FRAGMENT VERTEX is VIEW-space (probe 5: switching the pool to it
// extinguished every pool — the docs' fragment line is right; the Gate E
// rule stands). The varying below carries the world position; the normal
// sign is handled by abs(N*L) (see the pool comment).
varying vec3 wpos;

void vertex() {
	wpos = VERTEX;
}
// DEVLOG-90 baked-mesh route: the *_baked.glTF variants carry UV2 + the
// Blender-baked tangent-space normal and AO (from the displaced high-poly).
// Sampled at UV2 — zero UV shift (no swimming), correct from any angle.
// DEVLOG-92: the full baked material per the user's work order — baked
// diffuse albedo at UV2, matte roughness 0.8, metallic 0, specular 0.35,
// the AO map back with a softening weight (the dense displaced low body
// bakes a much cleaner AO than the spiky high-poly did).
uniform bool use_baked = false;
// the Blender glTF exporter's TEXCOORD order does not follow the layer
// list (it swapped once, DEVLOG-92): the sidecar json records which
// channel holds the bake atlas (0..1) vs the client tile UVs.
uniform bool atlas_in_uv2 = true;
uniform sampler2D baked_albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D baked_normal_tex : hint_normal, filter_linear_mipmap;
uniform sampler2D baked_ao_tex : filter_linear_mipmap;

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
	if (cull_back && !FRONT_FACING) {
		discard;
	}
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
	// Raymarched parallax occlusion mapping (DEVLOG-88; replaces the
	// single-step offset whose UVs swam with the camera while giving no
	// real occlusion). The view ray is marched through the height field in
	// tangent-space steps and stops at the first height intersection,
	// refined by one lerp between the straddling samples — raised features
	// occlude what is behind them, which is what reads as actual 3D.
	// textureLod(., 0) = EXPLICIT LOD: implicit-LOD sampling inside a
	// dynamic loop is undefined in GLSL (the 2026-11-13 banding).
	if (abs(mdet) > 1e-12 && pom_scale > 0.0005) {
		float angle_fade = smoothstep(0.12, 0.45, abs(vt.z));
		vec2 ray_uv = vt.xy / max(0.25, abs(vt.z))
			* (pom_scale / max(tile_m, vec2(1e-5)));
		float layer = 1.0 / float(pom_steps);
		vec2 duv = ray_uv * layer;
		float cd = 0.0;                       // ray depth below the surface
		float ch = 1.0 - h0;                  // height depth (alpha = raised)
		vec2 uvc = uv;
		for (int i = 0; i < pom_steps; i++) {
			if (ch <= cd) {
				break;
			}
			uvc -= duv;
			cd += layer;
			ch = 1.0 - textureLod(albedo_tex, uvc, 0.0).a;
		}
		if (ch > cd) {
			// never pierced the height field (flat texel / grazing) — no shift
			uvc = uv;
		} else {
			// refine between the straddling samples: the ray (pd -> cd)
			// crosses the height curve (ph -> ch) at t* from the previous
			// sample, where pd<ph and cd>=ch
			vec2 uvp = uvc + duv;
			float ph = 1.0 - textureLod(albedo_tex, uvp, 0.0).a;
			float pd = cd - layer;
			float tw = clamp((ph - pd)
					/ ((cd - pd) + (ph - ch) + 1e-6), 0.0, 1.0);
			uvc = mix(uvp, uvc, tw);
		}
		// distance fade: the parallax shift is view-dependent — at 15+ m it
		// reads as swimming/shimmer, not depth (VERTEX in fragment = view
		// space, its length = the camera distance)
		float dist_fade = 1.0 - smoothstep(15.0, 35.0, length(VERTEX));
		uv_final = mix(uv, uvc, angle_fade * dist_fade);
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
	if (use_baked) {
		// the baked material (DEVLOG-92): the dense displaced low body
		// carries the REAL pilaster/panel geometry; the Blender-baked
		// tangent normal + AO on the ATLAS channel, the client albedo on
		// the TILE channel (which is which comes from the sidecar json).
		// The baked DIFFUSE was black in Blender 5.3 headless (both the
		// Principled color pass and the EMIT rewiring — mean 18/255) and
		// is DROPPED: the client albedo is the same pattern 1:1.
		vec2 auv = atlas_in_uv2 ? UV2 : UV;
		vec2 tuv = atlas_in_uv2 ? UV : UV2;
		ALBEDO = texture(albedo_tex, tuv).rgb;
		NORMAL_MAP = texture(baked_normal_tex, auv).rgb;
		NORMAL_MAP_DEPTH = relief_gain;
		ROUGHNESS = 0.8;        // matte stone, not plastic
		METALLIC = 0.0;
		SPECULAR = 0.35;        // fewer highlights
		AO = mix(1.0, texture(baked_ao_tex, auv).r, 0.85);
		AO_LIGHT_AFFECT = 0.7;
	} else {
		ROUGHNESS = clamp(rough * rough_gain, 0.0, 1.0);
		SPECULAR = specular_strength;
		NORMAL_MAP = nrm * 0.5 + 0.5;
		NORMAL_MAP_DEPTH = relief_gain;
		// crevice shading from the height channel — scaled by the POM depth
		// so the flat weaves (pom ~0.012) keep the client's own painted
		// shading without double-darkening it. In alpha-cutout mode A is
		// the transparency mask, not height — no AO from it.
		if (use_alpha) {
			AO = 1.0;
		} else {
			AO = mix(1.0, clamp(0.55 + 0.45 * alb.a, 0.0, 1.0),
					clamp(pom_scale * 20.0, 0.0, 1.0));
		}
		AO_LIGHT_AFFECT = 0.6;
	}
	// DEVLOG-147 rev4: the lantern pools — shader-side, deterministic, on
	// the world position varying wpos (the vertex-stage VERTEX = world
	// with world_vertex_coords — Gate D probe 4 verified) and the screen-
	// Jacobian world normal. abs(N*L): the GLES3 dFdy convention + the
	// BSP's front-DOWN winding (DEVLOG-137) make the naive max(dot) sign
	// INVERTED on the floor back faces (the walls lit, the ground never
	// did — the probe-4 decode: wn.y = -1 on the floors). abs() is the
	// sign-proof two-sided form; the pool is a local glow, and the
	// undersides it would reach are void in the village.
	float lant_sum = 0.0;
	vec3 wn = normalize(cross(dFdx(wpos), dFdy(wpos))) * ff;
	for (int li = 0; li < lantern_count; li++) {
		// DEVLOG-150: the shadow-carrier lanterns are skipped — their
		// light comes through the real omnis (with the shadow maps).
		if (li == lantern_shadow0 || li == lantern_shadow1) {
			continue;
		}
		vec3 tol = lantern_pos[li] - wpos;
		float ld = length(tol);
		if (ld >= lantern_range) {
			continue;
		}
		// DEVLOG-150: the PHYSICAL falloff — exactly Godot's own omni
		// curve (scene_forward_lights_inc.glsl get_omni_attenuation,
		// decay = 2.0): the range window (1-(d/range)^4)^2 times the true
		// inverse square 1/d^2. The old (1-d/r)^0.25 was nearly flat
		// (75% strength at 15 m!) — that WAS the "переосвещение" and the
		// lit roofs. Godot's omni_attenuation is set to 2.0 on every
		// lantern/carrier light, so pool and omni are the same function.
		float nd = ld / lantern_range;
		nd *= nd; nd *= nd;            // (d/range)^4
		nd = max(1.0 - nd, 0.0);
		nd *= nd;                      // window^2
		float latt = nd * pow(max(ld, 0.05), -2.0);
		float lndl = mix(abs(dot(wn, tol / max(ld, 1e-4))), 1.0,
				lantern_ndl_soft);
		lant_sum += latt * lndl;
	}
	// DEVLOG-150: the overlap guard stays (2-3 lamps within a few meters
	// still sum up); with the physical falloff it only bites close-in.
	lant_sum = min(lant_sum, 1.3);
	// DEVLOG-144: the lamp glass glows with its own blue (the albedo
	// pattern carries the plafond's glass/frame detail)
	EMISSION = alb.rgb * emission_energy
			+ alb.rgb * lantern_color
			* (lantern_energy * lantern_night * lant_sum);
}
