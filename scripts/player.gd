extends CharacterBody3D
## Third-person player: mouse click-to-move (run to the destination in a
## straight line), WASD kept as the fallback, mouse orbit, terrain-following.
## The gait = a procedural bob until the skeletal animations are converted
## from the L2 .psa/.ukx data.

const WALK_SPEED := 2.6
const RUN_SPEED := 6.4
const GRAVITY := 14.0
const ARRIVE_DIST := 0.6

var terrain: Node3D
var yaw := 0.0
var _last_title_ms := 0
var _coord_label: Label
var move_target: Vector3
var has_target := false
var _target_time := 0.0  # seconds since the current click-to-move target was set
var rig: Node3D
var dest_marker: MeshInstance3D

func _init() -> void:
	if OS.get_environment("L2_VIEW_YAW") != "":
		yaw = float(OS.get_environment("L2_VIEW_YAW"))
	if OS.get_environment("L2_ZOOM") != "":
		cam_zoom = clampf(float(OS.get_environment("L2_ZOOM")), 0.02, 2.6)
	if OS.get_environment("L2_VIEW_PITCH") != "":
		pitch = float(OS.get_environment("L2_VIEW_PITCH"))
var pitch := -0.35
# Mouse-wheel camera zoom (the classic L2 camera distance): 1.0 = default,
# the wheel scales the whole pivot->camera offset so the pitch angle holds.
# L2_ZOOM=<float> overrides it at spawn (the screenshot-verification hook).
var cam_zoom := 1.0
var cam_pivot: Node3D
var cam: Camera3D

func _ready() -> void:
	cam_pivot = Node3D.new()
	add_child(cam_pivot)
	cam = Camera3D.new()
	if OS.get_environment("L2_DEBUG_CAM") != "":
		if OS.get_environment("L2_DEBUG_CAM") == "down":
			cam.position = Vector3(0, 6, 0.001)
			cam.rotation = Vector3(-1.55, 0, 0)
		elif OS.get_environment("L2_DEBUG_CAM") == "side":
			# side view for character-animation diagnostics
			cam.position = Vector3(-6, 1.0, 0.001)
			cam.rotation = Vector3(-0.05, -PI / 2, 0)
		elif OS.get_environment("L2_DEBUG_CAM") == "close":
			# head/upper-body close-up for character diagnostics
			cam.position = Vector3(-2.4, 1.5, 0.001)
			cam.rotation = Vector3(-0.05, -PI / 2, 0)
		elif OS.get_environment("L2_DEBUG_CAM") == "close2":
			# the opposite side (character front when facing east)
			cam.position = Vector3(2.4, 1.5, 0.001)
			cam.rotation = Vector3(-0.05, PI / 2, 0)
		elif OS.get_environment("L2_DEBUG_CAM") == "macro":
			# head close-up at the calibrated scale (the character ~0.44 m)
			cam.position = Vector3(-0.75, 0.42, 0.001)
			cam.rotation = Vector3(-0.05, -PI / 2, 0)
			cam.fov = 40
		else:
			cam.position = Vector3(0, 30, 0.001)
			cam.rotation = Vector3(-1.55, 0, 0)
	else:
		cam.position = Vector3(0, 2.4, 4.4)
	cam_pivot.add_child(cam)
	cam.current = true
	cam.far = 10000.0
	# Set initial camera rotation to avoid first-frame wrong orientation
	cam_pivot.rotation = Vector3(pitch, yaw, 0)
	var body := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.7
	body.shape = cap
	body.position = Vector3(0, 0.85, 0)
	add_child(body)
	_load_character()
	# on-screen coordinates (visible in screenshots)
	_coord_label = Label.new()
	_coord_label.position = Vector2(12, 8)
	_coord_label.add_theme_font_size_override("font_size", 22)
	_coord_label.add_theme_color_override("font_color", Color(1, 1, 0.2))
	_coord_label.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	_coord_label.add_theme_constant_override("outline_size", 6)
	var hud := CanvasLayer.new()
	hud.name = "HUD"
	add_child(hud)
	hud.add_child(_coord_label)
	_make_crosshair()
	# the destination marker: a glowing disc placed on the ground by the click
	dest_marker = MeshInstance3D.new()
	var disc := CylinderMesh.new()
	disc.top_radius = 0.35
	disc.bottom_radius = 0.35
	disc.height = 0.02
	var dm := StandardMaterial3D.new()
	dm.albedo_color = Color(0.4, 0.8, 1.0)
	dm.emission_enabled = true
	dm.emission = Color(0.3, 0.7, 1.0)
	dm.emission_energy_multiplier = 2.0
	dm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	disc.material = dm
	dest_marker.mesh = disc
	dest_marker.visible = false
	add_child(dest_marker)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	# diagnostic hook: start running immediately so screenshots capture the
	# run animation mid-stride (L2_AUTORUN=1)
	if OS.get_environment("L2_AUTORUN") == "1":
		has_target = true
		_target_time = 0.0
		move_target = position + Vector3(12.0, 0.0, 0.0)
		dest_marker.visible = true

func _make_crosshair() -> void:
	# the visible cursor: the L2-style crosshair (the mouse is never
	# captured in this game — the clicks are aimed precisely)
	var img := Image.create(32, 32, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for i in range(32):
		if i < 11 or i > 21:
			img.set_pixel(i, 16, Color(1, 1, 1, 0.95))
			img.set_pixel(16, i, Color(1, 1, 1, 0.95))
	for i in range(10, 23):
		img.set_pixel(i, 16, Color(0.1, 0.1, 0.1, 0.6))
		img.set_pixel(16, i, Color(0.1, 0.1, 0.1, 0.6))
	img.set_pixel(16, 16, Color(1.0, 0.75, 0.2))
	var tex := ImageTexture.create_from_image(img)
	Input.set_custom_mouse_cursor(tex, Input.CURSOR_ARROW, Vector2(16, 16))

## The character = the original L2 Dark Elf female FIGHTER base (2026-11-15):
## the m000 body parts (no armor set, no weapon) + the face variant t00 + the
## hair, the client-derived PBR sets (texgen.py from the client PNGs), the run
## animation Run_Hand_FDarkElf injected by tools/psa_to_gltf.py into every
## part's glTF (rotation+translation channels).
const CHAR_TEX_ROOT := "res://assets/character/fdarkelf/Texture"
## The unified single-skeleton character (tools/build_character.py): one
## skin, one animation player, the six client meshes as skinned meshes.
const CHAR_SCENE := "res://assets/character/FDarkElf_base.gltf"
## The mesh name -> [texture object, alpha-cutout] for the material pass.
## The armor = the chargrp.dat starting outfit (2026-11-15): the DE female
## FIGHTER starts in FDarkElf_m001_{u,l,b,g} with the t02 texture set — the
## dark leather bodice with straps (the user's original-client screenshots).
## The m000 body parts are replaced by the armor meshes (build_character
## --skip); the face + the ah tuft stay m000.
const CHAR_MAT_MAP := {
	# the u/g t02 textures carry BINARY alpha (0 or 255, measured: u 5%,
	# g 14% transparent, no mid values) — the client cuts the strap/plate
	# quads out with it; without the scissor they render as black
	# rectangles over the arms/shoulders (the user's screenshot)
	"FDarkElf_m001_u": ["FDarkElf_m001_t02_u", true],
	"FDarkElf_m001_l": ["FDarkElf_m001_t02_l", false],
	"FDarkElf_m001_b": ["FDarkElf_m001_t02_b", false],
	"FDarkElf_m001_g": ["FDarkElf_m001_t02_g", true],
	"FDarkElf_m000_f": ["FDarkElf_m000_t00_f", false],
	"FDarkElf_m000_m00_ah": ["FDarkElf_m000_t00_m00_ah_ori", true],
}
## The full hair = FDarkElf_m000_m00_bh: its own 13-bone skeleton (Hair01-13,
## the client's hair physics) whose bind is in body space — it cannot play the
## Bip01 run clip, so it is attached to the Bip01_head bone via BoneAttachment3D
## (the client attaches the hair bones to the head too). Without the bh the
## head shows only the dark backside of the face texture and the small ah tuft
## reads as a "displaced face" (the user's bug report, 2026-11-15).
const CHAR_HAIR := ["FDarkElf_m000_m00_bh", "FDarkElf_m000_t00_m00_bh_ori"]
## The user's live calibration with the +/- keys (2026-11-15): the mesh
## renders at its stored scale — the character height ≈ 0.44 m as exported
## (scale 1.0). The dat collision_height 37.5 does NOT translate to cm the
## way the earlier estimates assumed.
const CHAR_SCALE := 1.0
const RUN_ANIM := "Run_Hand_FDarkElf"
## The two standing animations from the client: the calm Wait (barely moves)
## and the weapon-ready AtkWait (the livelier stance played right after the
## movement/activity, then it settles into the calm Wait). Both injected
## without the Bip01_head channels (see DEVLOG-62).
const IDLE_ANIM := "Wait_Hand_FDarkElf"
const ATKWAIT_ANIM := "AtkWait_Hand_FDarkElf"

var _anim_players: Array = []
var _char_skels: Array = []
var _idle_since_ms := -100000  # far in the past = the calm Wait at spawn
var _face_mat: ShaderMaterial
var _face_open: Texture2D
var _face_closed: Texture2D
var _blink_t := 2.0
var _blink_closed := false
var _scale_hold_ms := 0  # the HUD shows the calibration value for 2.5 s
var _pbr_shader: Shader

func _load_character() -> void:
	# THE CLEAN-ROOM CHARACTER (the modern-port rule): the L2 client's
	# six-separately-animated-parts hack (six skeletons, six animation
	# players — the face "sliding off the head" at every animation) is
	# replaced by ONE unified glTF: one skeleton, one skin, one animation
	# player, the six client meshes as plain skinned meshes (tools/
	# build_character.py merges the UModel exports). A part desync is
	# structurally impossible now.
	var char_scale := CHAR_SCALE
	if OS.get_environment("L2_CHAR_SCALE") != "":
		char_scale = float(OS.get_environment("L2_CHAR_SCALE"))
	rig = Node3D.new()
	rig.name = "Rig"
	rig.rotation_degrees.y = 180.0
	rig.scale = Vector3.ONE * char_scale
	add_child(rig)
	if _pbr_shader == null:
		_pbr_shader = load("res://assets/shaders/l2_surface_pbr.gdshader")
	var inst: Node = (load(CHAR_SCENE) as PackedScene).instantiate()
	inst.name = "Character"
	rig.add_child(inst)
	# one skeleton, one animation player
	for sk in inst.find_children("*", "Skeleton3D", true, false):
		_char_skels.append(sk)
	for ap in inst.find_children("*", "AnimationPlayer", true, false):
		var lib = ap.get_animation_library("")  # untyped: Variant return
		for a in lib.get_animation_list():
			lib.get_animation(a).loop_mode = Animation.LOOP_LINEAR
		_anim_players.append(ap)
	# the client-derived PBR materials per mesh (the glTF carries only dummy
	# materials — UModel does not bind L2 character textures); the mesh names
	# identify the parts
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		# the imported MeshInstance node names are the clean part names
		# (the mesh resource name carries the "FDarkElf_base_" file prefix)
		var mesh_name: String = str(mi.name)
		var cfg: Array = CHAR_MAT_MAP.get(mesh_name, ["FDarkElf_m000_t1000_u", false])
		var tex_obj: String = cfg[0]
		var mat := ShaderMaterial.new()
		mat.shader = _pbr_shader
		mat.set_shader_parameter("albedo_tex",
				load("%s/%s.pbr_albedo.png" % [CHAR_TEX_ROOT, tex_obj]))
		mat.set_shader_parameter("normal_tex",
				load("%s/%s.pbr_normal.png" % [CHAR_TEX_ROOT, tex_obj]))
		mat.set_shader_parameter("uv_is_texels", false)
		mat.set_shader_parameter("pom_scale", 0.0)
		mat.set_shader_parameter("use_alpha", cfg[1])
		if cfg[1]:
			# the hair: alpha-SCISSOR, not alpha blend — the hair textures'
			# alpha is binary (bh: 80% of pixels > 0.6, 19% < 0.1) and the
			# alpha blend made the strands 40% see-through from behind
			# (the user's transparency bug, 2026-11-15)
			var hm := StandardMaterial3D.new()
			hm.albedo_texture = load("%s/%s.pbr_albedo.png" % [CHAR_TEX_ROOT, tex_obj])
			hm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
			hm.alpha_scissor_threshold = 0.5
			hm.roughness = 0.55
			hm.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
			hm.cull_mode = BaseMaterial3D.CULL_BACK
			for s in mi.mesh.get_surface_count():
				mi.set_surface_override_material(s, hm)
		else:
			for s in mi.mesh.get_surface_count():
				mi.set_surface_override_material(s, mat)
		if mesh_name == "FDarkElf_m000_f":
			_face_mat = mat
			_face_open = load("%s/FDarkElf_m000_t00_f.pbr_albedo.png" % CHAR_TEX_ROOT)
			_face_closed = load("%s/FDarkElf_m000_t00_f1.pbr_albedo.png" % CHAR_TEX_ROOT)
	_attach_full_hair()

func _attach_full_hair() -> void:
	# the bh hair (its own 13-bone physics skeleton, bind in body space)
	# rides the Bip01_head bone of the single character skeleton via
	# BoneAttachment3D with the inv-bind correction — the same way the
	# client attaches its hair bones to the head
	var hair_scene: PackedScene = load("res://assets/character/%s.gltf" % CHAR_HAIR[0])
	if hair_scene == null:
		return
	var skel: Skeleton3D = _char_skels[0] if _char_skels.size() > 0 else null
	if skel == null:
		return
	var head_bind := skel.get_bone_global_pose(skel.find_bone("Bip01_head"))
	var attach := BoneAttachment3D.new()
	attach.name = "HairAttach"
	attach.bone_idx = skel.find_bone("Bip01_head")
	attach.bone_name = "Bip01_head"
	skel.add_child(attach)
	var inst: Node = hair_scene.instantiate()
	# correction: the bh bind (identity in body space) expressed in the head
	# bone's bind space; Hair01 then rides every head pose
	attach.add_child(inst)
	inst.transform = head_bind.affine_inverse() * Transform3D.IDENTITY
	var hm := StandardMaterial3D.new()
	hm.albedo_texture = load("%s/%s.pbr_albedo.png" % [CHAR_TEX_ROOT, CHAR_HAIR[1]])
	hm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	hm.alpha_scissor_threshold = 0.5
	hm.roughness = 0.55
	hm.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		for s in mi.mesh.get_surface_count():
			mi.set_surface_override_material(s, hm)
	# diagnostic hook: freeze the run clip at one frame (L2_ANIM_FRAME=<0..15>)
	if OS.get_environment("L2_ANIM_FRAME") != "":
		var fr := int(OS.get_environment("L2_ANIM_FRAME"))
		for ap in _anim_players:
			ap.play(RUN_ANIM)
			ap.seek(fr / 24.0, true)
			ap.pause()
	# diagnostic: per-part skeleton/bone state (L2_CHAR_DEBUG=1)
	if OS.get_environment("L2_CHAR_DEBUG") == "1":
		var dbg_t := 0.0
		var dbg_timer := Timer.new()
		dbg_timer.wait_time = 0.5
		dbg_timer.timeout.connect(func():
			dbg_t += 0.5
			var line := "t=%.2f " % dbg_t
			for c in rig.get_children():
				var sk: Skeleton3D = c.find_children("*", "Skeleton3D", true, false)[0]
				var bi: int = sk.find_bone("Bip01_head")
				var gp: Vector3 = (sk.global_transform * sk.get_bone_global_pose(bi)).origin
				var ap: AnimationPlayer = c.find_children("*", "AnimationPlayer", true, false)[0]
				var nm: String = c.name.get_slice("_", 3) if c.name.begins_with("FDarkElf_m000_") else str(c.name)
				line += " %s[anim=%s pos=%.3f head=%.2f %.2f %.2f]" % [nm, ap.current_animation, ap.current_animation_position, gp.x, gp.y, gp.z]
			print(line))
		add_child(dbg_timer)
		dbg_timer.start()

func _char_run(active: bool) -> void:
	if OS.get_environment("L2_ANIM_FRAME") != "":
		return  # the frozen-frame diagnostic overrides the state machine
	if active:
		_idle_since_ms = -1  # the idle timer restarts on the next idle frame
		for ap in _anim_players:
			if ap.current_animation != RUN_ANIM:
				ap.play(RUN_ANIM)
	else:
		# the two-stage standing (the client behavior): the livelier AtkWait
		# stance right after the movement, then the calm Wait
		if _idle_since_ms == -1:
			_idle_since_ms = Time.get_ticks_msec()
		var want: String = ATKWAIT_ANIM if Time.get_ticks_msec() - _idle_since_ms < 3000 else IDLE_ANIM
		for ap in _anim_players:
			if ap.current_animation != want:
				ap.play(want)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		# the camera orbit on the held right button (the classic L2 camera);
		# the mouse stays visible and free for aiming
		yaw -= event.relative.x * 0.003
		pitch = clampf(pitch - event.relative.y * 0.003, -1.2, 0.4)
	elif event is InputEventMouseButton and event.pressed \
			and event.button_index == MOUSE_BUTTON_WHEEL_UP:
		# wheel zoom: up = closer, down = farther (clamped)
		cam_zoom = clampf(cam_zoom * 0.88, 0.02, 2.6)  # no lower limit: the user zooms in close to the character
	elif event is InputEventMouseButton and event.pressed \
			and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
		cam_zoom = clampf(cam_zoom * 1.14, 0.02, 2.6)
	elif event is InputEventMouseButton and event.pressed \
			and event.button_index == MOUSE_BUTTON_LEFT:
		# click-to-move: cast through the click position onto the world,
		# set the destination, the character runs there in a straight line
		var from := cam.project_ray_origin(event.position)
		var dir := cam.project_ray_normal(event.position)
		var q := PhysicsRayQueryParameters3D.create(from, from + dir * 2000.0)
		q.exclude = [get_rid()]
		var hit := get_world_3d().direct_space_state.intersect_ray(q)
		if hit:
			move_target = hit.position
			has_target = true
			_target_time = 0.0
			dest_marker.global_position = move_target + Vector3(0, 0.05, 0)
			dest_marker.visible = true
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventKey and event.pressed and not event.echo:
		# live character-scale calibration: + grows, - shrinks (5% a step);
		# the current multiplier prints to the console for the DEVLOG
		if event.keycode == KEY_EQUAL:
			rig.scale = rig.scale * 1.05
			_scale_hold_ms = Time.get_ticks_msec() + 2500
			print("CHAR_SCALE %.2f (height ~%.2f m)" % [rig.scale.x, 0.444 * rig.scale.x])
		elif event.keycode == KEY_MINUS:
			rig.scale = rig.scale * 0.95
			_scale_hold_ms = Time.get_ticks_msec() + 2500
			print("CHAR_SCALE %.2f (height ~%.2f m)" % [rig.scale.x, 0.444 * rig.scale.x])

func _physics_process(delta: float) -> void:
	if OS.get_environment("L2_DEBUG_CAM") == "":
		cam_pivot.rotation = Vector3(pitch, yaw, 0)
		cam.position = Vector3(0, 2.4, 4.4) * cam_zoom
		# camera collision (the classic L2 behavior): zooming out must not
		# push the camera into rocks/walls — pull it to the first hit
		var desired := cam.global_position
		var cq := PhysicsRayQueryParameters3D.create(
				cam_pivot.global_position + Vector3(0, 1.2, 0), desired)
		cq.exclude = [get_rid()]
		var chit := get_world_3d().direct_space_state.intersect_ray(cq)
		if chit:
			var hp: Vector3 = chit.get("position")
			cam.global_position = hp + (cam_pivot.global_position + Vector3(0, 1.2, 0) \
					- hp).normalized() * 0.25
	var input := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	var dir := Vector3.ZERO
	var moving := false
	var speed := 0.0
	if input.length_squared() > 0.01:
		var basis_yaw := Basis(Vector3.UP, yaw)
		var fwd := -basis_yaw.z
		var right := basis_yaw.x
		dir = (fwd * -input.y + right * input.x).normalized()
		speed = RUN_SPEED if Input.is_key_pressed(KEY_SHIFT) else WALK_SPEED
		velocity.x = dir.x * speed
		velocity.z = dir.z * speed
		# face movement direction
		rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), 10.0 * delta)
		moving = true
	elif has_target:
		_target_time += delta
		# click-to-move: run straight to the destination until close
		var to_t := move_target - position
		to_t.y = 0.0
		if to_t.length() > ARRIVE_DIST:
			dir = to_t.normalized()
			velocity.x = dir.x * RUN_SPEED
			velocity.z = dir.z * RUN_SPEED
			rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), 10.0 * delta)
			moving = true
			speed = RUN_SPEED
		else:
			has_target = false
			dest_marker.visible = false
		# blocked (a wall/house between): the real displacement is ~zero while
		# the run animation plays — drop the target and stand. The 0.5 s grace
		# period is REQUIRED: on the first frames get_real_velocity() still
		# returns the previous frame's zero and the check would kill every
		# fresh target instantly (the "character does not move" bug, 2026-11-15)
		if moving and _target_time > 0.5 and get_real_velocity().length() < 0.5:
			has_target = false
			_target_time = 0.0
			dest_marker.visible = false
			velocity.x = 0
			velocity.z = 0
			moving = false
	if not moving:
		velocity.x = move_toward(velocity.x, 0, 20 * delta)
		velocity.z = move_toward(velocity.z, 0, 20 * delta)
	if is_on_floor():
		velocity.y = 0
	else:
		velocity.y -= GRAVITY * delta
	move_and_slide()
	# the real L2 run animation (Run_Hand_FDarkElf, rotation-only from the
	# PSA); the procedural bob/lean is retired — the clip carries the gait
	# the eye blink: swap the face albedo between the open (t00_f) and the
	# closed (t00_f1) client frames every few seconds
	if _face_mat != null:
		_blink_t -= delta
		if _blink_t <= 0.0:
			if _blink_closed:
				_face_mat.set_shader_parameter("albedo_tex", _face_open)
				_blink_closed = false
				_blink_t = randf_range(2.5, 4.5)
			else:
				_face_mat.set_shader_parameter("albedo_tex", _face_closed)
				_blink_closed = true
				_blink_t = 0.12
	_char_run(moving)
	# live game coordinates: window title + on-screen HUD (debug aid)
	var now := Time.get_ticks_msec()
	if now - _last_title_ms > 250:
		_last_title_ms = now
		var g := Vector3(position.x / 0.01, position.y / 0.01, position.z / 0.01)
		DisplayServer.window_set_title(
			"L2 20_18  X=%.0f Y=%.0f Z=%.1f" % [g.x, g.z, g.y])
		if _coord_label:
			if Time.get_ticks_msec() < _scale_hold_ms:
				_coord_label.text = "CHAR SCALE %.2f = %.2f m  (+/-)" % [rig.scale.x, 0.444 * rig.scale.x]
			else:
				_coord_label.text = "X=%.0f  Y=%.0f  Z=%.1f" % [g.x, g.z, g.y]
	if terrain:
		var game_x: float = position.x / 0.01
		var game_y: float = position.z / 0.01
		if terrain.has_terrain_surface(game_x, game_y):
			var t: float = terrain.terrain_height(game_x, game_y)
			# Ground snap ONLY when the heightfield is close above the player.
			# The canyon tunnel passes UNDER solid terrain: without the
			# distance window the clamp teleported the camera up into the
			# rock (the buried-in-tunnel bug, DEVLOG 2026-11-12).
			if position.y < t and t - position.y < 0.8:
				position.y = t
				velocity.y = 0
