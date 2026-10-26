# -*- coding: utf-8 -*-
"""Follow-up: fix SpringArm rot, cam-relative Move, fill holes with live grass mesh."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
CELL = 100.0
FARM = 40
CAM_PITCH = -40.0
CAM_YAW = -45.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0
FLOOR_LABEL = "FarmCollisionFloor"

def log(m):
    unreal.log("[FIX2] " + str(m)); print("[FIX2] " + str(m))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] : {}".format(label, ok)); return ok

def find_pin(node, name_substr, direction=None):
    if not node: return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def set_val(pin, value, label=""):
    if not pin: return
    try: pin.set_pin_value(str(value))
    except Exception as e: log("set {} {}".format(label, e))

def break_links(pin):
    if pin:
        try: pin.break_pin_links()
        except Exception as e: log("break "+str(e))

def cell_center(cx, cy, z=0.0):
    return unreal.Vector((cx + 0.5) * CELL, (cy + 0.5) * CELL, z)

def grid_of_loc(loc):
    return int(loc.x // CELL), int(loc.y // CELL)

def fix_springarm():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    detail = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(h)
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj: continue
        cname = obj.get_class().get_name()
        name = str(lib.get_variable_name(data))
        if "SpringArm" in cname or name == "SpringArm":
            try: obj.set_editor_property("target_arm_length", CAM_ARM)
            except Exception: pass
            for prop, val in (
                ("do_collision_test", False), ("b_do_collision_test", False),
                ("use_pawn_control_rotation", False), ("b_use_pawn_control_rotation", False),
                ("inherit_pitch", False), ("b_inherit_pitch", False),
                ("inherit_yaw", False), ("b_inherit_yaw", False),
                ("inherit_roll", False), ("b_inherit_roll", False),
            ):
                try: obj.set_editor_property(prop, val)
                except Exception: pass
            rot = unreal.Rotator()
            rot.pitch = CAM_PITCH
            rot.yaw = CAM_YAW
            rot.roll = 0.0
            obj.set_editor_property("relative_rotation", rot)
            now = obj.get_editor_property("relative_rotation")
            detail.append("SpringArm p={:.0f} y={:.0f}".format(now.pitch, now.yaw))
        if cname == "CameraComponent" or name == "Camera":
            try:
                obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", CAM_ORTHO)
                detail.append("ortho={}".format(CAM_ORTHO))
            except Exception as e:
                detail.append(str(e))
        if "CharacterMovement" in cname:
            for prop in ("orient_rotation_to_movement", "b_orient_rotation_to_movement"):
                try:
                    obj.set_editor_property(prop, False); detail.append("Orient=False"); break
                except Exception: pass
    try: bel.compile_blueprint(bp)
    except Exception: pass
    unreal.EditorAssetLibrary.save_asset(CHAR)
    return "; ".join(detail)

def try_create(ge, names, xy):
    for name in names:
        try:
            n = ge.create_node_from_name(name, unreal.Vector2D(xy[0], xy[1]), [])
            if n:
                try: bel.set_node_pos(n, pos(xy[0], xy[1]))
                except Exception: pass
                log("created "+name); return n
        except Exception as e:
            log("create {} : {}".format(name, e))
    return None

def try_call(ge, paths, xy):
    for path in paths:
        try:
            n = ge.add_call_function_node(path)
            if n:
                try: bel.set_node_pos(n, pos(xy[0], xy[1]))
                except Exception: pass
                log("call "+path); return n
        except Exception as e:
            log("call {} : {}".format(path, e))
    return None

def fix_move_cam_relative():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

    ami_x = ami_y = None
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) != "AddMovementInput": continue
        sc = find_pin(n, "ScaleValue", "Input")
        if not sc: continue
        for c in sc.list_connected_pins():
            if str(c.get_pin_name()) == "X": ami_x = n
            if str(c.get_pin_name()) == "Y": ami_y = n
    if not ami_x or not ami_y:
        return "FAIL AMI"

    # Already done?
    wd = find_pin(ami_y, "WorldDirection", "Input")
    if wd:
        for c in wd.list_connected_pins():
            t = bel.get_node_title(c.get_owning_node())
            if any(k in t for k in ("Normal", "Forward", "Right", "Get World Rotation")):
                return "already cam-rel: "+t

    for ami in (ami_x, ami_y):
        break_links(find_pin(ami, "WorldDirection", "Input"))

    bx, by = -1600, -300

    # Variable get for Camera component — try several APIs
    get_cam = None
    for name in ("Get Camera", "Camera", "Get CameraComponent"):
        get_cam = try_create(ge, [name], (bx, by))
        if get_cam: break
    if not get_cam:
        # add_node VariableGet
        try:
            get_cam = ge.add_node(unreal.K2Node_VariableGet.static_class(), unreal.Vector2D(bx, by))
            # set variable name
            for prop in ("variable_name", "VariableName"):
                try:
                    get_cam.set_editor_property(prop, "Camera")
                    log("VariableGet Camera via "+prop); break
                except Exception as e:
                    log("set var "+str(e))
            try: bel.set_node_pos(get_cam, pos(bx, by))
            except Exception: pass
        except Exception as e:
            log("add VariableGet "+str(e))
    if not get_cam:
        # Self → Get Component by Class CameraComponent
        get_cam = try_call(ge, [
            "/Script/Engine.Actor:GetComponentByClass",
        ], (bx, by))
        if get_cam:
            # set component class pin
            cp = find_pin(get_cam, "ComponentClass", "Input") or find_pin(get_cam, "Class", "Input")
            set_val(cp, "/Script/Engine.CameraComponent", "camclass")
            log("using GetComponentByClass CameraComponent")

    if not get_cam:
        return "FAIL still no camera ref"

    get_rot = try_call(ge, [
        "/Script/Engine.SceneComponent:K2_GetComponentRotation",
    ], (bx+280, by))
    if not get_rot:
        get_rot = try_create(ge, ["Get World Rotation", "K2_GetComponentRotation", "GetWorldRotation"], (bx+280, by))
    if not get_rot:
        return "FAIL no get_rot"

    cam_out = (find_pin(get_cam, "Camera", "Output")
               or find_pin(get_cam, "ReturnValue", "Output")
               or find_pin(get_cam, "CameraComponent", "Output"))
    # VariableGet often exposes pin named after var
    if not cam_out:
        for p in bel.list_all_pins(get_cam):
            if "OUTPUT" in str(p.get_pin_direction()).upper() or "output" in str(p.get_pin_direction()).lower():
                if "exec" not in str(p.get_pin_name()).lower():
                    cam_out = p; break
    rot_self = find_pin(get_rot, "self", "Input") or find_pin(get_rot, "Target", "Input")
    connect(cam_out, rot_self, "cam->rot")
    log("get_cam pins="+str([(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(get_cam)]))
    log("get_rot pins="+str([(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(get_rot)]))

    rot_out = find_pin(get_rot, "ReturnValue", "Output")

    # Flatten yaw-only rotator
    br = try_call(ge, ["/Script/Engine.KismetMathLibrary:BreakRotator"], (bx+560, by))
    if not br: br = try_create(ge, ["Break Rotator", "BreakRotator"], (bx+560, by))
    mr = try_call(ge, ["/Script/Engine.KismetMathLibrary:MakeRotator"], (bx+820, by))
    if not mr: mr = try_create(ge, ["Make Rotator", "MakeRotator"], (bx+820, by))
    flat = rot_out
    if br and mr and rot_out:
        connect(rot_out, find_pin(br, "Rotation", "Input") or find_pin(br, "InRot", "Input") or find_pin(br, "A", "Input"), "rot->br")
        connect(find_pin(br, "Yaw", "Output"), find_pin(mr, "Yaw", "Input"), "yaw")
        set_val(find_pin(mr, "Pitch", "Input"), "0.0", "p0")
        set_val(find_pin(mr, "Roll", "Input"), "0.0", "r0")
        flat = find_pin(mr, "ReturnValue", "Output")

    fwd = try_call(ge, ["/Script/Engine.KismetMathLibrary:GetForwardVector"], (bx+1100, by-80))
    if not fwd: fwd = try_create(ge, ["Get Forward Vector", "GetForwardVector"], (bx+1100, by-80))
    right = try_call(ge, ["/Script/Engine.KismetMathLibrary:GetRightVector"], (bx+1100, by+80))
    if not right: right = try_create(ge, ["Get Right Vector", "GetRightVector"], (bx+1100, by+80))
    if not fwd or not right:
        return "FAIL fwd/right"

    connect(flat, find_pin(fwd, "InRot", "Input") or find_pin(fwd, "A", "Input") or find_pin(fwd, "Rotation", "Input"), "flat->fwd")
    connect(flat, find_pin(right, "InRot", "Input") or find_pin(right, "A", "Input") or find_pin(right, "Rotation", "Input"), "flat->right")

    n2d_f = try_call(ge, ["/Script/Engine.KismetMathLibrary:Vector_Normal2D"], (bx+1400, by-80))
    if not n2d_f: n2d_f = try_create(ge, ["Normalize 2D", "Normal2D", "Vector_Normal2D"], (bx+1400, by-80))
    n2d_r = try_call(ge, ["/Script/Engine.KismetMathLibrary:Vector_Normal2D"], (bx+1400, by+80))
    if not n2d_r: n2d_r = try_create(ge, ["Normalize 2D", "Normal2D", "Vector_Normal2D"], (bx+1400, by+80))

    if n2d_f and n2d_r:
        connect(find_pin(fwd, "ReturnValue", "Output"), find_pin(n2d_f, "A", "Input") or find_pin(n2d_f, "InVec", "Input"), "f->n")
        connect(find_pin(right, "ReturnValue", "Output"), find_pin(n2d_r, "A", "Input") or find_pin(n2d_r, "InVec", "Input"), "r->n")
        connect(find_pin(n2d_f, "ReturnValue", "Output"), find_pin(ami_y, "WorldDirection", "Input"), "W=fwd")
        connect(find_pin(n2d_r, "ReturnValue", "Output"), find_pin(ami_x, "WorldDirection", "Input"), "AD=right")
    else:
        # Break/Make Z=0 fallback
        for vec_node, ami, tag, dy in ((fwd, ami_y, "W", -80), (right, ami_x, "AD", 80)):
            b2 = try_call(ge, ["/Script/Engine.KismetMathLibrary:BreakVector"], (bx+1400, by+dy))
            if not b2: b2 = try_create(ge, ["Break Vector"], (bx+1400, by+dy))
            m2 = try_call(ge, ["/Script/Engine.KismetMathLibrary:MakeVector"], (bx+1650, by+dy))
            if not m2: m2 = try_create(ge, ["Make Vector"], (bx+1650, by+dy))
            connect(find_pin(vec_node, "ReturnValue", "Output"), find_pin(b2, "InVec", "Input") or find_pin(b2, "In", "Input"), tag+"br")
            connect(find_pin(b2, "X", "Output"), find_pin(m2, "X", "Input"), tag+"x")
            connect(find_pin(b2, "Y", "Output"), find_pin(m2, "Y", "Input"), tag+"y")
            set_val(find_pin(m2, "Z", "Input"), "0.0", tag+"z")
            connect(find_pin(m2, "ReturnValue", "Output"), find_pin(ami, "WorldDirection", "Input"), tag+"ami")

    try:
        bel.compile_blueprint(bp); log("compile ok")
    except Exception as e:
        log("compile "+str(e))
    unreal.EditorAssetLibrary.save_asset(CHAR)
    return "cam-relative ok"

def fill_holes():
    # Grab mesh+scale from any existing grass actor
    grass_mesh = None
    scale = unreal.Vector(0.01, 0.01, 0.01)
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_Grass_"):
            try:
                grass_mesh = a.static_mesh_component.static_mesh
                scale = a.get_actor_scale3d()
                log("donor {} mesh={} scale=({},{},{})".format(
                    lab, grass_mesh.get_path_name() if grass_mesh else None, scale.x, scale.y, scale.z))
                break
            except Exception as e:
                log("donor err "+str(e))
    if not grass_mesh:
        # try load known paths
        for p in (
            "/Game/Farm/VoxelMicroFarm/Models/Expansion02/GroundStudy/SM_VMF_GroundStudy_Grass_B",
            "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass",
        ):
            if unreal.EditorAssetLibrary.does_asset_exist(p):
                grass_mesh = unreal.EditorAssetLibrary.load_asset(p)
                log("loaded "+p)
                break
    if not grass_mesh:
        return 0, "NO_MESH"

    kinds = ("Grass", "Path", "Water", "Bridge", "Cliff", "Bank", "Soil", "Hoe", "Yard")
    covered = set()
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_") and any(k in lab for k in kinds):
            covered.add(grid_of_loc(a.get_actor_location()))
    log("covered n="+str(len(covered)))

    holes = []
    for gy in range(1, FARM - 1):
        for gx in range(1, FARM - 1):
            if (gx, gy) not in covered:
                holes.append((gx, gy))
    log("holes n={} sample={}".format(len(holes), holes[:30]))

    placed = []
    for gx, gy in holes:
        lab = "VMF_Grass_{}_{}".format(gx, gy)
        actor = eas().spawn_actor_from_class(
            unreal.StaticMeshActor, cell_center(gx, gy, 0.0), unreal.Rotator())
        actor.set_actor_label(lab)
        actor.set_actor_scale3d(scale)
        smc = actor.static_mesh_component
        smc.set_static_mesh(grass_mesh)
        try:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            actor.set_actor_enable_collision(False)
        except Exception:
            pass
        placed.append((gx, gy))
    return len(placed), placed[:30]

def ensure_floor():
    mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    center = unreal.Vector(FARM * CELL * 0.5, FARM * CELL * 0.5, 0.0)
    scale = unreal.Vector(float(FARM), float(FARM), 1.0)
    actor = None
    for a in eas().get_all_level_actors():
        if (a.get_actor_label() or "") == FLOOR_LABEL:
            actor = a; break
    if actor is None:
        actor = eas().spawn_actor_from_class(unreal.StaticMeshActor, center, unreal.Rotator())
        actor.set_actor_label(FLOOR_LABEL)
    actor.set_actor_location(center, False, True)
    actor.set_actor_scale3d(scale)
    smc = actor.static_mesh_component
    smc.set_static_mesh(mesh)
    try:
        smc.set_visibility(False, True)
        actor.set_actor_hidden_in_game(True)
        actor.set_is_temporarily_hidden_in_editor(True)
        actor.set_actor_enable_collision(True)
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        smc.set_editor_property("collision_profile_name", "BlockAll")
    except Exception as e:
        log("floor "+str(e))
    return True

def save_level():
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level(); return True
    except Exception:
        try: unreal.EditorLevelLibrary.save_current_level(); return True
        except Exception as e:
            log("save "+str(e)); return False

def verify():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    # springarm
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    arm = "?"
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(h)
        obj = lib.get_object_for_blueprint(data, bp)
        if obj and "SpringArm" in obj.get_class().get_name():
            r = obj.get_editor_property("relative_rotation")
            arm = "p={:.0f} y={:.0f}".format(r.pitch, r.yaw)
    # move dirs
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    move_info = []
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) != "AddMovementInput": continue
        wd = find_pin(n, "WorldDirection", "Input")
        sc = find_pin(n, "ScaleValue", "Input")
        wds = [bel.get_node_title(c.get_owning_node()) for c in wd.list_connected_pins()] if wd else []
        scs = [str(c.get_pin_name()) for c in sc.list_connected_pins()] if sc else []
        move_info.append((scs, wds))
    # holes
    kinds = ("Grass", "Path", "Water", "Bridge", "Cliff", "Bank", "Soil", "Hoe", "Yard")
    covered = set()
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_") and any(k in lab for k in kinds):
            covered.add(grid_of_loc(a.get_actor_location()))
    hoe = [(x, y) for y in range(20, 24) for x in range(25, 28) if (x, y) not in covered]
    near = [(x, y) for y in range(14, 19) for x in range(20, 27) if (x, y) not in covered]
    imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
    txt = imc.get_editor_property("default_key_mappings").export_text()
    return {"arm": arm, "move": move_info, "hoe_holes": hoe, "near_holes": near,
            "imc_E": "Key=E" in txt and "IA_Interact" in txt}

def main():
    log("=== START fix2 ===")
    log("springarm: " + fix_springarm())
    log("move: " + fix_move_cam_relative())
    ensure_floor()
    n, sample = fill_holes()
    log("filled n={} sample={}".format(n, sample))
    save_level()
    log("VERIFY " + str(verify()))
    log("=== DONE ===")

if __name__ == "__main__":
    main()
