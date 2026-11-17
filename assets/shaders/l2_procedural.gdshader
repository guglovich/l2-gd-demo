// The procedural clean-room surface shader (the MODERN-PORT RULE, AGENTS.md:
// no legacy PNG porting — surfaces are synthesized in-shader, 3D world-space
// noise for the volumetric grain, UV-aligned base pattern for the 1:1 layout
// identity with the original client; see Docs/DEVLOG.md 2026-11-12).
//
// One shader, 8 modes (set via "mode"):
//   0 cobble slate      (DE_V_floor01)      1 ornament tile (DE_V_floor02)
//   2 rock cliff        (DE_V_m12)          3 dark stone    (O_dark_01)
//   4 grey brick court  (oren_sylen_001_1)  5 carpet grey   (DE_V_capet01)
//   6 carpet ornate     (DE_V_capet02)      7 thorn braid   (DE_V_capet)
//
// UVs: BSP glTFs carry raw TEXELS (uv_is_texels = true); UModel statics carry
// normalized 0..1 (uv_is_texels = false, multiplied by tile_px in-shader).
// Relief: height field -> screen-space gradient normal (Mikkelsen surface
// gradient; no mesh tangents needed — the BSP meshes have none).
shader_type spatial;
render_mode world_vertex_coords, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform int mode = 0;
uniform bool uv_is_texels = true;
// The client renders BSP faces one-sided (UE2 culls backfaces unless the
// section is TwoSided); statics render both sides. Gated per material.
uniform bool cull_back = false;
uniform vec2 tile_px = vec2(256.0, 256.0);
uniform float relief = 1.0;      // normal bump strength
uniform float detail = 1.0;      // world-space grain amount
uniform float roughness_f : hint_range(0.0, 1.0) = 0.92;

// ---- noise (Ashima public-domain simplex; card-hashes ours) ----
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x * 34.0) + 10.0) * x); }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 10.0) * x); }

float snoise2(vec2 v) {
	const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
	vec2 i = floor(v + dot(v, C.yy));
	vec2 x0 = v - i + dot(i, C.xx);
	vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
	vec4 x12 = x0.xyxy + C.xxzz; x12.xy -= i1;
	i = mod289(i);
	vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
	vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
	m = m * m; m = m * m;
	vec3 x = 2.0 * fract(p * vec3(0.1031, 0.1030, 0.0973)) - 1.0;
	vec3 h = abs(x) - 0.5;
	vec3 ox = floor(x + 0.5);
	m *= 1.79284291400159 - 0.85373472095314 * (ox * x + h * h);
	vec3 g = vec3(m * x + h * ox * m);
	return 130.0 * dot(g, vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)));
}

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

float fbm3(vec3 p) {
	float f = 0.0;
	f += 0.5000 * snoise3(p); p *= 2.02;
	f += 0.2500 * snoise3(p); p *= 2.03;
	f += 0.1250 * snoise3(p);
	return f;
}

float fbm2(vec2 p) {
	float f = 0.0;
	f += 0.5000 * snoise2(p); p *= 2.02;
	f += 0.2500 * snoise2(p); p *= 2.03;
	f += 0.1250 * snoise2(p);
	return f;
}

float hash21(vec2 p) {
	p = fract(p * vec2(0.1031, 0.1030));
	p += dot(p, p.yx + 33.33);
	return fract((p.x + p.y) * p.x);
}

// Voronoi (F1, F2, cell hash) on a jittered grid.
vec3 voronoi(vec2 p) {
	vec2 n = floor(p);
	vec2 f = fract(p);
	float f1 = 8.0, f2 = 8.0, ch = 0.0;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 g = vec2(float(i), float(j));
			vec2 o = vec2(hash21(n + g), hash21(n + g + 7.7));
			o = 0.5 + 0.42 * sin(6.2831 * o) * 0.85; // jitter
			float d = length(g + o - f);
			if (d < f1) { f2 = f1; f1 = d; ch = hash21(n + g + 3.1); }
			else if (d < f2) { f2 = d; }
		}
	}
	return vec3(f1, f2, ch);
}

// ---------------- mode color/height ----------------
// Returns albedo; h in roughly [-1, 1] (negative = recessed mortar/gap).

vec3 mode_cobble(vec2 px, vec3 wp, out float h) {
	vec2 t = px / 256.0;
	vec3 v = voronoi(t * 4.0 + vec2(0.13, 0.7));
	float edge = v.y - v.x;              // 0 in the mortar, big mid-cell
	float mortar = 1.0 - smoothstep(0.015, 0.09, edge);
	float ch = v.z;
	// slate grain + per-cell tone
	float grain = fbm2(t * 18.0) * 0.5 + fbm3(wp * 7.0) * 0.5;
	vec3 dark = vec3(0.130, 0.108, 0.079);
	vec3 bright = vec3(0.368, 0.342, 0.299);
	vec3 cell = mix(dark, bright, 0.35 + 0.45 * ch + 0.25 * grain);
	vec3 albedo = mix(cell, vec3(0.085, 0.072, 0.055), mortar);
	// crevice AO
	albedo *= mix(0.75, 1.0, smoothstep(0.0, 0.25, edge));
	h = mix(-0.7, 0.35 + 0.5 * ch, smoothstep(0.0, 0.12, edge));
	h += 0.2 * grain;
	return albedo;
}

float sdHex(vec2 p, float r) {
	const vec3 k = vec3(-0.866025404, 0.5, 0.577350269);
	p = abs(p);
	p -= 2.0 * min(dot(k.xy, p), 0.0) * k.xy;
	p -= vec2(clamp(p.x, -k.z * r, k.z * r), r);
	return length(p) * sign(p.y);
}

vec3 mode_ornament(vec2 px, vec3 wp, out float h) {
	vec2 t = px / 256.0;
	vec2 c = t - 0.5;
	float a = max(abs(c.x), abs(c.y));        // square metric
	float dh = sdHex(c, 0.30);
	float r1 = smoothstep(0.015, 0.0, abs(a - 0.38));  // outer square ring
	float r2 = smoothstep(0.015, 0.0, abs(a - 0.34));
	float hexd = smoothstep(0.02, 0.0, abs(dh));       // hexagon outline
	float weave = fbm2(t * 26.0) * 0.4 + fbm3(wp * 9.0) * 0.4;
	// diagonal ticks inside the outer ring
	float ticks = smoothstep(0.02, 0.0, abs(fract(a * 14.0) - 0.5) * step(0.33, a) * step(a, 0.43));
	vec3 field = vec3(0.198, 0.170, 0.148);
	vec3 band = vec3(0.590, 0.501, 0.459);
	vec3 mid = vec3(0.330, 0.282, 0.252);
	vec3 albedo = field + 0.05 * weave;
	albedo = mix(albedo, band * (0.85 + 0.15 * ticks), max(r1, r2));
	albedo = mix(albedo, mid * (0.9 + 0.2 * weave), hexd * 0.6);
	h = -0.25 + 0.5 * max(max(r1, r2), hexd) + 0.2 * weave;
	return albedo;
}

vec3 mode_rock(vec2 px, vec3 wp, out float h) {
	vec3 p = wp * 0.55;
	float n = fbm3(p);
	float ridge = 1.0 - abs(snoise3(p * 1.7));
	ridge = ridge * ridge;
	float g = fbm3(wp * 6.0) * 0.4;
	float v = 0.5 * n + 0.35 * ridge + 0.3 * g;
	vec3 dark = vec3(0.143, 0.104, 0.066);
	vec3 bright = vec3(0.455, 0.393, 0.309);
	vec3 albedo = mix(dark, bright, clamp(0.45 + 0.75 * v, 0.0, 1.0));
	h = clamp(v * 1.2, -1.0, 1.0);
	return albedo;
}

vec3 mode_dark_stone(vec2 px, vec3 wp, out float h) {
	float v = fbm3(wp * 0.9) * 0.6 + fbm3(wp * 3.5) * 0.35;
	vec3 dark = vec3(0.176, 0.143, 0.105);
	vec3 bright = vec3(0.376, 0.325, 0.263);
	vec3 albedo = mix(dark, bright, clamp(0.5 + 0.7 * v, 0.0, 1.0));
	h = v;
	return albedo;
}

vec3 mode_grey_brick(vec2 px, vec3 wp, out float h) {
	vec2 t = px / 256.0;
	float rows = 8.0;
	float row = floor(t.y * rows);
	float off = mod(row, 2.0) * 0.5;
	vec2 b = vec2(fract(t.x * 2.0 + off), fract(t.y * rows));
	float bh = hash21(vec2(floor(t.x * 2.0 + off), row));
	float mort = 1.0 - smoothstep(0.0, 0.06, min(b.x, b.y) * smoothstep(1.0, 0.94, max(b.x, b.y)));
	float grain = fbm2(t * 30.0) * 0.5 + fbm3(wp * 8.0) * 0.5;
	vec3 dark = vec3(0.134, 0.125, 0.097);
	vec3 bright = vec3(0.412, 0.402, 0.377);
	vec3 brick = mix(dark, bright, 0.4 + 0.3 * bh + 0.35 * grain);
	vec3 albedo = mix(brick, dark * 0.8, mort);
	h = mix(0.3 + 0.4 * bh, -0.6, mort) + 0.2 * grain;
	return albedo;
}

// carpet weave helper: fine stitched grain
float weave2(vec2 t, float fx, float fy) {
	float w = sin(t.x * 3.14159 * fx) * sin(t.y * 3.14159 * fy);
	return 0.6 + 0.4 * w;
}

vec3 mode_carpet_grey(vec2 px, vec3 wp, out float h) {
	vec2 t = px / vec2(128.0, 256.0);
	float dx = abs(t.x - 0.5);
	float wv = weave2(t, 24.0, 24.0) * 0.5 + fbm2(t * 40.0) * 0.35 + fbm3(wp * 6.0) * 0.35;
	vec3 dark = vec3(0.163, 0.127, 0.103);
	vec3 bright = vec3(0.461, 0.417, 0.359);
	vec3 field = mix(dark, bright, clamp(0.5 + 0.5 * wv, 0.0, 1.0));
	// side border bands with X-stitch diamonds
	float band = smoothstep(0.30, 0.34, dx);
	vec2 q = t * vec2(10.0, 8.0);
	vec2 fq = abs(fract(q) - 0.5);
	float xst = smoothstep(0.10, 0.0, abs(fq.x + fq.y - 0.28) - 0.07);
	vec3 border = mix(dark * 0.9, bright * 0.9, xst);
	vec3 albedo = mix(field, border, band);
	h = 0.2 * wv - 0.3 * band + 0.4 * xst * band;
	return albedo;
}

vec3 mode_carpet_ornate(vec2 px, vec3 wp, out float h) {
	vec2 t = px / 256.0;
	float dx = abs(t.x - 0.5);
	float wv = weave2(t, 20.0, 20.0) * 0.4 + fbm2(t * 36.0) * 0.3 + fbm3(wp * 6.0) * 0.3;
	vec3 dark = vec3(0.091, 0.070, 0.061);
	vec3 bright = vec3(0.473, 0.432, 0.385);
	vec3 field = mix(dark, dark * 1.7, clamp(0.4 + 0.4 * wv, 0.0, 1.0));
	// two diamond medallions along the length
	float best = 8.0;
	for (int k = 0; k < 2; k++) {
		vec2 c = vec2(0.5, 0.28 + 0.44 * float(k));
		vec2 d = abs(t - c);
		float dd = d.x + d.y;           // diamond metric
		best = min(best, abs(dd - 0.16));
	}
	float gold = smoothstep(0.02, 0.0, best);
	// woven gold side bands
	float band = smoothstep(0.38, 0.42, dx);
	float weave_b = weave2(t * vec2(3.0, 1.0), 16.0, 8.0);
	vec3 albedo = field;
	albedo = mix(albedo, bright * 0.8, gold);
	albedo = mix(albedo, bright * (0.55 + 0.35 * weave_b), band);
	h = 0.3 * wv + 0.5 * gold - 0.2 * band + 0.3 * weave_b * band;
	return albedo;
}

vec3 mode_thorn_braid(vec2 px, vec3 wp, out float h) {
	vec2 t = px / vec2(128.0, 256.0);
	float wv = fbm2(t * 30.0) * 0.4 + fbm3(wp * 6.0) * 0.4;
	vec3 dark = vec3(0.112, 0.090, 0.069);
	vec3 bright = vec3(0.521, 0.485, 0.447);
	vec3 albedo = dark + 0.03 * wv;
	// three meandering braids running along the length
	float best = 8.0;
	for (int k = 0; k < 3; k++) {
		float ph = 2.1 * float(k);
		float cx = 0.5 + 0.30 * sin(t.y * 9.42 + ph) + 0.12 * sin(t.y * 25.1 + ph * 2.0);
		best = min(best, abs(t.x - cx));
	}
	float strand = smoothstep(0.030, 0.010, best + 0.02 * wv);
	albedo = mix(albedo, bright, strand);
	// thorn spikes off the strands
	float th = hash21(floor(t * vec2(24.0, 24.0)));
	float thorn = smoothstep(0.93, 0.99, th) * smoothstep(0.06, 0.0, best);
	albedo = mix(albedo, bright * 1.1, thorn);
	h = 0.2 * wv + 0.6 * strand + 0.5 * thorn;
	return albedo;
}

// dispatch: returns albedo, writes height h
vec3 surface_p(int m, vec2 px, vec3 wp, out float h) {
	if (m == 0) return mode_cobble(px, wp, h);
	if (m == 1) return mode_ornament(px, wp, h);
	if (m == 2) return mode_rock(px, wp, h);
	if (m == 3) return mode_dark_stone(px, wp, h);
	if (m == 4) return mode_grey_brick(px, wp, h);
	if (m == 5) return mode_carpet_grey(px, wp, h);
	if (m == 6) return mode_carpet_ornate(px, wp, h);
	return mode_thorn_braid(px, wp, h);
}

void fragment() {
	if (cull_back && !FRONT_FACING) {
		discard;
	}
	vec2 px = uv_is_texels ? UV : UV * tile_px;
	float h0, hu, hv, hx, hy, hz;
	vec3 alb = surface_p(mode, px, VERTEX, h0);
	// UV-space height steps: FIXED 1-texel epsilon (the BSP faces are huge
	// polys where fwidth(UV) is far below one texel per pixel — the
	// screen-space epsilon exploded the normals, the white-crack artifact).
	// The pattern features are 8-64 texels wide, so 1-texel steps resolve them.
	vec2 duv = fwidth(UV);
	float eps = clamp(max(duv.x, duv.y), 1e-4, 1.0);
	surface_p(mode, px + vec2(eps, 0.0), VERTEX, hu);
	surface_p(mode, px + vec2(0.0, eps), VERTEX, hv);
	float dbx = (hu - h0) / eps;
	float dby = (hv - h0) / eps;
	// world-space height steps (modes 2/3 derive h from world position;
	// the UV steps never see that variation)
	float ew = 0.04;
	surface_p(mode, px, VERTEX + vec3(ew, 0.0, 0.0), hx);
	surface_p(mode, px, VERTEX + vec3(0.0, ew, 0.0), hy);
	surface_p(mode, px, VERTEX + vec3(0.0, 0.0, ew), hz);
	vec3 gw = vec3(hx - h0, hy - h0, hz - h0) / ew;

	// geometric normal from screen-space derivatives (no mesh tangents)
	vec3 sigX = dFdx(VERTEX);
	vec3 sigY = dFdy(VERTEX);
	float ff = FRONT_FACING ? 1.0 : -1.0;
	vec3 nrm = normalize(cross(sigX, sigY)) * ff;

	// world direction of +1 texel in u / v: solve the 2x2 screen-Jacobian
	vec2 uvd = vec2(dFdx(UV).x, dFdy(UV).x);
	vec2 vvd = vec2(dFdx(UV).y, dFdy(UV).y);
	float mdet = uvd.x * vvd.y - uvd.y * vvd.x;
	vec3 g = gw - dot(gw, nrm) * nrm;   // tangential world gradient
	if (abs(mdet) > 1e-10) {
		vec3 dPdu = (sigX * vvd.y - sigY * vvd.x) / mdet;
		vec3 dPdv = (sigY * uvd.x - sigX * uvd.y) / mdet;
		g += normalize(dPdu) * dbx + normalize(dPdv) * dby;
	}
	vec3 wn = normalize(nrm - relief * 0.15 * g);
	NORMAL = normalize((VIEW_MATRIX * vec4(wn, 0.0)).xyz);
	ALBEDO = alb;
	ROUGHNESS = roughness_f;
	AO = clamp(1.0 - 0.35 * max(0.0, -h0), 0.0, 1.0);
}
