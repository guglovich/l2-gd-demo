// SPOM — self-shadowed parallax occlusion mapping with silhouette clipping
// and horizon erosion, for the Shillien Temple walls (the user's directive
// 2026-11-21). Source technique: godotshaders.com "SPOM with horizon
// detection, self shading, silhouette clipping, parallax occlusion mapping,
// self shading, horizon trimming erosion" by Amose05 (CC0), ported onto
// this project's client-derived PBR conventions (l2_surface_pbr.gdshader):
//   - the screen-Jacobian tangent basis — the BSP/static meshes carry no
//     tangents, the basis is solved per pixel from the UV/position
//     screen-Jacobian (dPdu/dPdv);
//   - pom_scale is METERS, converted per surface through the Jacobian
//     (tile_m = meters per full tile) — not the published UV-unit scale;
//   - the angle/distance anti-swim fades (2026-11-13 seams / DEVLOG-88);
//   - ONE height source (the DEVLOG-94 rule): the albedo's A channel IS the
//     POM height — texgen.py sobel'd the normal from that same field, the
//     POM march, the self-shadow march and the crevice AO all read it, so
//     albedo shift and shading can never disagree (the DEVLOG-94 swimming).
//   - explicit textureLod(, 0) inside the dynamic loops (the DEVLOG-88
//     banding: implicit LOD in a loop is undefined in GLSL).
// Silhouette clipping (UV-bounds discard) and the curved-silhouette horizon
// erosion are per-material toggles, DEFAULT OFF: the temple UVs tile (the
// skin spans u -5.3..6.3 — a 0..1 clip would erase the walls; audited
// 2026-11-21). They stay for per-texture enablement once a surface with
// true 0..1 UVs needs the carved edge.
shader_type spatial;
render_mode world_vertex_coords, blend_mix, depth_draw_opaque, cull_disabled,
		diffuse_burley, specular_schlick_ggx;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap, repeat_enable;
uniform bool uv_is_texels = true;
// The client renders BSP faces one-sided (UE2 culls backfaces unless the
// section is TwoSided); statics render both sides. Gated per material.
uniform bool cull_back = false;
uniform vec2 tile_px = vec2(256.0, 256.0);
uniform float pom_scale = 0.04;  // visual depth, meters
// The SPOM layer ladder: fewer layers head-on, more at grazing angles —
// the deep-parallax quality knob (the user's "настраиваемые min/max layers").
uniform int pom_min_layers : hint_range(8, 64, 1) = 8;
uniform int pom_max_layers : hint_range(8, 64, 1) = 32;
uniform int shadow_min_layers : hint_range(8, 64, 1) = 8;
uniform int shadow_max_layers : hint_range(8, 64, 1) = 32;
uniform bool use_self_shadow = false;  // the 2026-11-21 verdict: the march's
	// blocked/lit patches on the sun-lit walls read as the matte gray film
	// vs the client (the client has no wall self-shadow); the POM relief
	// stays, the shadow march is off (the uniform remains for the re-enable)
// Silhouette clipping: discard everything the POM march pushed outside the
// UV bounds. ONLY valid on true 0..1-per-face UVs (no tiling).
uniform bool use_silhouette_clipping = false;
uniform vec2 clip_uv_min = vec2(0.0, 0.0);
uniform vec2 clip_uv_max = vec2(1.0, 1.0);
// Curved-silhouette horizon erosion (NdotV-based, UV-independent — safe on
// tiled UVs). Off by default: on a flat wall seen at grazing angles it eats
// the whole face; enable per texture for curved members (the pillars).
uniform bool use_curved_silhouette = false;
uniform float horizon_clip_strength : hint_range(0.0, 4.0, 0.01) = 1.0;
uniform float horizon_height_bias : hint_range(0.0, 1.0, 0.01) = 0.0;
uniform float horizon_safe_threshold : hint_range(0.0, 0.95, 0.01) = 0.3;
uniform float horizon_falloff_power : hint_range(0.5, 8.0, 0.1) = 2.0;
uniform float relief_gain = 1.0;  // normal strength multiplier
uniform float rough_gain : hint_range(0.0, 1.0) = 0.9;
// Specular ZERO (the 2026-11-21 verdict): the GGX fresnel at grazing camera
// angles whitened the walls into a camera-dependent B/W sheen under the
// moonlight — the temple stone is matte, F0 = 0 kills the term.
uniform float specular : hint_range(0.0, 1.0, 0.01) = 0.0;
uniform bool use_alpha = false;   // TRUE cutout textures only (the grates)
uniform float alpha_scissor : hint_range(0.0, 1.0) = 0.4;

// base_uv = the POM-displaced UV (the albedo/normal sample point)
varying vec2 base_uv;
// flat_uv = the UNDISPLACED surface UV — the self-shadow march and the
// crevice AO read it: a view-stable start (2026-11-21 the user's "matte
// gray film runs with the angle" — the march from the view-dependent
// displaced UV made the sun-lit occlusion pattern swim with the camera)
varying vec2 flat_uv;
// meters per full tile-u / tile-v (the Jacobian) — meters->UV conversion
varying vec2 tile_m;
// view-space tangent basis: LIGHT in light() is view-space, so the world
// jac TBN is transformed ONCE here and the shadow march uses it there
varying vec3 vT;
varying vec3 vB;
varying vec3 vN;

float pom_shadow(vec2 uv, vec3 travel, vec2 tm) {
	// The SPOM self-shadow (Amose05 GetParallaxShadow): march BACK up the
	// light beam (travel = light->fragment, tangent space) from the surface
	// point toward the height-field top. Returns TRANSMITTANCE: 0.0 when the
	// beam sank below the local terrain (occluded), 1.0 when it cleared the
	// field or the light grazes from below the tangent plane.
	if (travel.z >= 0.0) {
		return 0.0;
	}
	if (travel.z > -0.3) {
		// GRAZING light: travel.z -> 0 explodes the march steps (P ~
		// 1/travel.z) and the 64-step walk samples arbitrary texels —
		// the sun-facing walls flipped to a matte film depending on the
		// sun angle (the user's 2026-11-21 report). No shadow info here:
		// transmittance 1 = the native texture, stable.
		return 1.0;
	}
	float num_layers = mix(float(shadow_max_layers), float(shadow_min_layers),
			abs(travel.z));
	float layer_depth = 1.0 / num_layers;
	vec2 P = travel.xy / travel.z * (pom_scale / max(tm, vec2(1e-5)));
	P = clamp(P, vec2(-2.0), vec2(2.0));  // step-size insurance
	vec2 cur = uv;
	float terrain_d = 1.0 - textureLod(albedo_tex, cur, 0.0).a;
	float beam_d = terrain_d;
	int steps = int(num_layers);
	for (int i = 0; i < 64; i++) {
		if (i >= steps || beam_d <= 0.0 || beam_d > terrain_d) {
			break;
		}
		cur += P / float(steps);
		terrain_d = 1.0 - textureLod(albedo_tex, cur, 0.0).a;
		beam_d -= layer_depth;
	}
	return beam_d > terrain_d ? 0.0 : 1.0;
}

void fragment() {
	if (cull_back && !FRONT_FACING) {
		discard;
	}
	vec2 uv = uv_is_texels ? UV / tile_px : UV;  // 0..1 per tile
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
	tile_m = vec2(length(dPdu), length(dPdv));  // meters per full tile
	vT = (VIEW_MATRIX * vec4(T, 0.0)).xyz;
	vB = (VIEW_MATRIX * vec4(B, 0.0)).xyz;
	vN = (VIEW_MATRIX * vec4(ngeo, 0.0)).xyz;

	vec3 view_w = normalize(INV_VIEW_MATRIX[3].xyz - VERTEX);  // frag -> camera
	vec3 vt = vec3(dot(view_w, T), dot(view_w, B), dot(view_w, ngeo));

	flat_uv = uv;
	base_uv = uv;
	// Raymarched parallax occlusion mapping with the SPOM layer ladder —
	// fewer layers head-on, more at grazing angles. The view ray is marched
	// through the height field (albedo A) in tangent-space steps and stops
	// at the first height intersection, refined between the straddling
	// samples. The angle/distance fades keep the shift readable (at 15+ m
	// or on grazing faces the view-dependent shift reads as swimming).
	if (abs(mdet) > 1e-12 && pom_scale > 0.0005) {
		float angle_fade = smoothstep(0.12, 0.45, abs(vt.z));
		float num_layers = mix(float(pom_max_layers), float(pom_min_layers),
				abs(vt.z));
		float layer_depth = 1.0 / num_layers;
		vec2 ray_uv = vt.xy / max(0.25, abs(vt.z))
				* (pom_scale / max(tile_m, vec2(1e-5)));
		// DEVLOG-123 (the user's "the temple protrusions get the film in
		// the sun" report): the SMALL ornate faces carry a tiny tile_m
		// (meters per tile) — pom_scale/tile_m explodes and the march
		// samples fly across the whole texture = the wash. The parallax
		// physically cannot exceed a fraction of the tile: cap it. The
		// big wall faces sit far below the cap (their ratio ~0.01-0.08).
		ray_uv = clamp(ray_uv, vec2(-0.35), vec2(0.35));
		vec2 duv = ray_uv * layer_depth;
		float cd = 0.0;                       // ray depth below the surface
		float ch = 1.0 - textureLod(albedo_tex, uv, 0.0).a;
		vec2 uvc = uv;
		int steps = int(num_layers);
		for (int i = 0; i < 64; i++) {
			if (i >= steps || ch <= cd) {
				break;
			}
			uvc -= duv;
			cd += layer_depth;
			ch = 1.0 - textureLod(albedo_tex, uvc, 0.0).a;
		}
		if (ch > cd) {
			// never pierced the height field (flat texel / grazing) — no shift
			uvc = uv;
		} else {
			// refine between the straddling samples
			vec2 uvp = uvc + duv;
			float ph = 1.0 - textureLod(albedo_tex, uvp, 0.0).a;
			float pd = cd - layer_depth;
			float tw = clamp((ph - pd)
					/ ((cd - pd) + (ph - ch) + 1e-6), 0.0, 1.0);
			uvc = mix(uvp, uvc, tw);
		}
		float dist_fade = 1.0 - smoothstep(15.0, 35.0, length(VERTEX));
		base_uv = mix(uv, uvc, angle_fade * dist_fade);
	}

	// Silhouette clipping (SPOM): the march must not push the UV outside
	// the face's own bounds — those pixels are the carved silhouette.
	if (use_silhouette_clipping) {
		if (base_uv.x < clip_uv_min.x || base_uv.x > clip_uv_max.x ||
				base_uv.y < clip_uv_min.y || base_uv.y > clip_uv_max.y) {
			discard;
		}
	}
	// Curved-silhouette horizon erosion (SPOM): near the mesh horizon
	// (NdotV -> 0) clip fragments whose height sits below the erosion
	// curve — simulates displacement on curved members without
	// tessellation. Toggled per material (flat walls: OFF).
	if (use_curved_silhouette) {
		float NdotV = abs(dot(NORMAL, VIEW));
		float t = clamp(1.0 - NdotV / max(horizon_safe_threshold, 0.001),
				0.0, 1.0);
		float horizon_factor = pow(t, horizon_falloff_power);
		float height_threshold = clamp(horizon_factor * horizon_clip_strength,
				0.0, 1.0);
		float surface_height = textureLod(albedo_tex, base_uv, 0.0).a
				- horizon_height_bias;
		if (surface_height < height_threshold) {
			discard;
		}
	}

	vec4 alb = texture(albedo_tex, base_uv);
	if (use_alpha && alb.a < alpha_scissor) {
		discard;  // the grate holes are see-through
	}
	vec3 nrm = texture(normal_tex, base_uv).rgb * 2.0 - 1.0;
	float rough = texture(normal_tex, base_uv).a;
	ALBEDO = alb.rgb;
	// the matte floor 0.82 (the 2026-11-21 "the protrusions get the gloss"
	// report): the roughness 0.59-0.86 + the bright overcast dome = the
	// environment specular sheen on the sun-facing ornate faces; the stone
	// is matte, the floor kills the sheen.
	ROUGHNESS = clamp(max(rough * rough_gain, 0.82), 0.0, 1.0);
	SPECULAR = 0.0;
	NORMAL_MAP = nrm * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = relief_gain;
	// The crevice AO is REMOVED (the 2026-11-21 verdict): at weight 0.8 it
	// darkened the dark painted texels ~36% — a static matte film vs the
	// client's flat albedo, visible at every angle and distance. The client
	// carries no wall AO — AO stays 1.0 (the alpha-cutout mode never had it).
	AO = 1.0;
}

// The SPOM BRDF (Amose05, CC0) — the diffuse term carries the parallax
// self-shadow transmittance; the specular term is the standard GGX pair.
float D_GGX(float cos_theta_m, float alpha) {
	float a = cos_theta_m * alpha;
	float k = alpha / (1.0 - cos_theta_m * cos_theta_m + a * a);
	return k * k * (1.0 / PI);
}

float V_GGX(float NdotL, float NdotV, float alpha) {
	return 0.5 / mix(2.0 * NdotL * NdotV, NdotL + NdotV, alpha);
}

float SchlickFresnel(float u) {
	float m = 1.0 - u;
	float m2 = m * m;
	return m2 * m2 * m;
}

vec3 F0(float mt, float spc, vec3 cl) {
	float dielectric = 0.16 * spc * spc;
	return mix(vec3(dielectric), cl.rgb, vec3(mt));
}

void light() {
	vec3 L = normalize(LIGHT);
	vec3 V = normalize(VIEW);
	// DEVLOG-128 (the user's finding: "the temple works without light and
	// shadows, always statically black"): the skin shell is wound INWARD —
	// the client renders it two-sided and never cares, but the built-in
	// NORMAL points away from the sun on the outside view, killing NdotL
	// (the walls never received direct light; the outward-wound deco10
	// horns DID — the whole "the horns work, the temple doesn't" story).
	// The Jacobian geometric normal (the varying vN, view-space) is correct
	// on BOTH faces — use it for the lighting.
	vec3 N = normalize(vN);
	// the light's travel direction (light -> fragment) in tangent space;
	// LIGHT is view-space, the varying jac basis is view-space too
	vec3 travel = -vec3(dot(L, vT), dot(L, vB), dot(L, vN));
	float NdotL = min(dot(N, L), 1.0);
	float cNdotL = max(NdotL, 0.0);
	float NdotV = dot(N, V);
	float cNdotV = max(NdotV, 1e-4);
	vec3 H = normalize(V + L);
	float cLdotH = clamp(dot(L, H), 0.0, 1.0);
	float cNdotH = clamp(dot(N, H), 0.0, 1.0);
	float cLdotH5 = SchlickFresnel(cLdotH);
	float shadow = use_self_shadow ? pom_shadow(base_uv, travel, tile_m) : 1.0;
	float diffuse_brdf_NL = cNdotL * (1.0 / PI);
	float D = D_GGX(cNdotH, ROUGHNESS);
	float G = V_GGX(cNdotL, cNdotV, ROUGHNESS);
	vec3 f0 = F0(METALLIC, specular, ALBEDO);
	float f90 = clamp(dot(f0, vec3(50.0 * 0.33)), METALLIC, 1.0);
	vec3 F = f0 + (f90 - f0) * cLdotH5;
	vec3 specular_brdf_NL = cNdotL * D * F * G;
	DIFFUSE_LIGHT += diffuse_brdf_NL * shadow * LIGHT_COLOR * ATTENUATION;
	SPECULAR_LIGHT += specular_brdf_NL * LIGHT_COLOR * SPECULAR_AMOUNT * ATTENUATION;
}
