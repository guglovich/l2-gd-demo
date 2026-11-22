// The ONE world sky (DEVLOG-141, the user's correction of the DEVLOG-140
// model: "небо одинаковое по цвету и синеве везде, но КОЛИЧЕСТВО ТУЧ на
// картах разное; тучи видны ГЛОБАЛЬНО, а не при переходе — чтобы не было
// эффекта, когда переходишь границу и видишь, что количество туч
// меняется; тучи именно сверху над картой, поэтому видны даже с соседней
// карты"). So the cloud density IS geographic again (the DEVLOG-139
// per-fragment atlas lookup on the cloud plane) — the clouds belong to
// the territories and are visible from the neighbors — but the DEVLOG-139
// wedge artifact is gone because the atlas field is now baked HEAVILY
// blurred (sigma 10 texels = ~51 m godot: the territory weather edges
// read as soft fronts in the sky instead of razor straight lines). The
// coverage + the opacity are the functions of the FRAGMENT's local
// density: the semi-transparent light veil over the DE territory (the
// whole sky covered, the blue showing through — "затянуто, но
// полупрозрачные, а не тёмные и толстые"), the sparse light clouds over
// the clear one. The sky PALETTE stays ONE for the whole world. The sun
// disc glows through the veil. The sun LIGHT (world.gd) samples the same
// atlas above the camera. No fog anywhere (fog_disabled).
shader_type spatial;
render_mode unshaded, cull_front, depth_draw_never, shadows_disabled, fog_disabled;

// the ONE sky palette for the whole world: the day pair = the approved
// DEVLOG-136 control blue; the dusk/night = the clean-room values
uniform vec3 day_top = vec3(0.20, 0.30, 0.50);
uniform vec3 day_hor = vec3(0.45, 0.50, 0.55);
uniform vec3 dusk_top = vec3(0.16, 0.20, 0.36);
uniform vec3 dusk_hor = vec3(0.70, 0.46, 0.30);
uniform vec3 night_top = vec3(0.012, 0.016, 0.038);
uniform vec3 night_hor = vec3(0.035, 0.045, 0.085);
// the cloud bodies: the LIGHT semi-transparent veil, not dark and thick
uniform vec3 cloud_day = vec3(0.84, 0.87, 0.92);
uniform vec3 cloud_dusk = vec3(0.84, 0.64, 0.50);
uniform vec3 cloud_night = vec3(0.10, 0.12, 0.18);

uniform float day_f = 1.0;
uniform float dusk_f = 0.0;
uniform float night_f = 0.0;
uniform float drift = 0.0;   // the cloud phase (the game clock driven)
// the world cloudiness field (0 = the clear map, 0.7 = the DE
// semi-transparent overcast, 1.0 = the densest reserve). atlas_rect =
// vec4(origin_x, origin_z, size_x, size_z) in GODOT METERS; row 0 =
// the atlas south edge (the same orientation as the tile masks). The
// atlas extends 1500 m godot beyond the built world in every direction
// and the cloud-plane distance SATURATES at 1500 m — the low sky (the
// neighbor territories' weather, DEVLOG-141) lands inside the atlas
// instead of clamping to a constant edge (the DEVLOG-141 miss: below
// ~42 deg elevation the old ±655 m atlas was exhausted and the whole
// low sky read one constant, so the clouds looked the same everywhere).
uniform sampler2D cloud_atlas : filter_linear, repeat_disable;
uniform vec4 atlas_rect = vec4(-2155.36, -1827.68, 4310.72, 3983.04);
uniform vec3 cam_ws = vec3(0.0);      // the godot camera position
uniform float cloud_plane_h = 600.0;  // the godot meters above the camera
uniform float cloud_scale = 0.005;    // the world meters -> the fbm input
uniform vec3 sun_dir_ws = vec3(0.0, 1.0, 0.0);  // normalized, TO the sun
uniform float sun_disc_amount = 1.0;  // world.gd: 0 at night, 1 by day
uniform vec3 sun_disc_color = vec3(1.0, 0.92, 0.78);

varying vec3 vdir;

float hash13(vec3 p) {
	p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3));
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float vnoise(vec3 x) {
	vec3 i = floor(x);
	vec3 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(
		mix(mix(hash13(i), hash13(i + vec3(1.0, 0.0, 0.0)), f.x),
			mix(hash13(i + vec3(0.0, 1.0, 0.0)), hash13(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
		mix(mix(hash13(i + vec3(0.0, 0.0, 1.0)), hash13(i + vec3(1.0, 0.0, 1.0)), f.x),
			mix(hash13(i + vec3(0.0, 1.0, 1.0)), hash13(i + vec3(1.0, 1.0, 1.0)), f.x), f.y),
		f.z);
}

float fbm(vec3 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 5; i++) {
		v += a * vnoise(p);
		p = p * 2.17 + vec3(11.3, 7.1, 5.7);
		a *= 0.5;
	}
	return v;
}

void vertex() {
	vdir = VERTEX;  // the dome's local space = camera-centered
}

void fragment() {
	vec3 dir = normalize(vdir);
	// the ONE sky gradient for the whole world
	vec3 top_c = day_top * day_f + dusk_top * dusk_f + night_top * night_f;
	vec3 hor_c = day_hor * day_f + dusk_hor * dusk_f + night_hor * night_f;
	float up = max(dir.y, 0.0);
	vec3 base = mix(hor_c, top_c, smoothstep(0.0, 0.55, up));
	if (dir.y < 0.0) {
		base = mix(hor_c, hor_c * 0.55, smoothstep(0.0, 0.3, -dir.y));
	}
	// the cloud field anchored to the WORLD: the direction projected onto
	// the cloud plane gives the world point the cloud belongs to — the
	// projection SATURATES at 1500 m so the low sky stays inside the atlas
	// (the DEVLOG-141 miss: the pure H/dir.y perspective exhausted the
	// atlas below 42 deg and the low sky read one clamped constant)
	float dist = min(cloud_plane_h / max(dir.y, 0.02), 1500.0);
	vec2 plane_ws = cam_ws.xz + dir.xz * dist;
	vec2 cuv = plane_ws * cloud_scale + vec2(drift * 0.9, drift * 0.55);
	float n = fbm(vec3(cuv, drift * 0.03));
	// the GEOGRAPHIC density at the cloud's world point: the clouds belong
	// to the territories (the DE overcast, the clear neighbor) and are
	// visible from the neighboring maps; the baked field is heavily
	// blurred, so the edges read as soft fronts, not the DEVLOG-139 wedges
	vec2 auv = (plane_ws - atlas_rect.xy) / atlas_rect.zw;
	float c = texture(cloud_atlas, clamp(auv, vec2(0.0), vec2(1.0))).r;
	// the coverage + the opacity from the LOCAL density — the WIDE mapping
	// (the DEVLOG-141 miss: 0.78..0.55 was too flat, the eye saw the same
	// amount everywhere): the clear map = the near-cloudless sky; the DE
	// overcast = the whole sky covered by the SEMI-TRANSPARENT veil;
	// 1.0 = the densest reserve
	float cov = mix(0.85, 0.30, c);
	float op = mix(0.45, 0.85, c);
	// DEVLOG-143: the clouds live ONLY on the ceiling (the user: they must
	// not "roll down the map edges like walls"). The old fade started at
	// 1 deg of elevation where the saturated projection stretches the
	// patches into vertical curtains along the horizon; now the clouds
	// fade in from 12.7 deg and are full above 26.6 deg — the low sky is
	// the clean gradient.
	float mask = smoothstep(cov - 0.14, cov + 0.14, n)
			* smoothstep(0.22, 0.45, dir.y);
	// the cloud bodies: the light veil, slightly grayer when denser
	vec3 cloud_c = cloud_day * day_f + cloud_dusk * dusk_f
			+ cloud_night * night_f;
	cloud_c *= 1.0 - 0.18 * c;
	vec3 cloud_shaded = mix(base, cloud_c, 0.55);
	vec3 cloud_body = mix(cloud_shaded, cloud_c, smoothstep(0.05, 0.6, dir.y));
	vec3 out_c = mix(base, cloud_body, mask * op);
	// the sun disc glows through the semi-transparent veil
	float sd = dot(dir, normalize(sun_dir_ws));
	float disc = smoothstep(0.9997, 0.9999, sd);
	float halo = pow(clamp(sd, 0.0, 1.0), 160.0) * 0.4;
	out_c += (disc * 1.5 + halo) * sun_disc_color * sun_disc_amount
			* (1.0 - mask * op);
	ALBEDO = out_c;
	ROUGHNESS = 1.0;
}
