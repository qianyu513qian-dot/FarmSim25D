# -*- coding: utf-8 -*-
"""Post-rebuild SAFE: IMC E/F/R/G/H, cam-relative Move (if missing), FarmCollisionFloor,
SpringArm yaw=90 pitch=-40, verify water horizontal. NO rotate, NO hole-fill, NO mirror.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
CELL = 100.0
FARM = 40
CAM_PITCH = -40.0
CAM_YAW = -90.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0
FLOOR_LABEL = "FarmCollisionFloor"

IA_MAP = {
    "E": "/Game/TopDown/Input/Actions/IA_Interact",
    "F": "/Game/TopDown/Input/Actions/IA_Plant",
    "R": "/Game/TopDown/Input/Actions/IA_Water",
    "G": "/Game/TopDown/Input/Actions/IA_Grow",
    "H": "/Game/TopDown/Input/Actions/IA_Harvest",
}


def log(m):
    unreal.log("[REBUILD_SAFE] " + str(m))
    print("[REBUILD_SAFE] " + str(m))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] : {}".format(label, ok))
    return ok


def set_val(pin, value, label=""):
    if not pin:
        return
    try:
        pin.set_pin_value(str(value))
    except Exception as e:
        log("set {} {}".format(label, e))


def break_links(pin):
    if pin:
        try:
            pin.break_pin_links()
        except Exception as e:
            log("break " + str(e))


def try_create(ge, names, xy):
    for name in names:
        try:
            n = ge.create_node_from_name(name, unreal.Vector2D(xy[0], xy[1]), [])
            if n:
                try:
                    bel.set_node_pos(n, unreal.IntPoint(int(xy[0]), int(xy[1])))
                except Exception:
                    pass
                log("created " + name)
                return n
        except Exception as e:
            log("create {} : {}".format(name, e))
    return None


def try_call(ge, paths, xy):
    for path in paths:
        try:
            n = ge.add_call_function_node(path)
            if n:
                try:
                    bel.set_node_pos(n, unreal.IntPoint(int(xy[0]), int(xy[1])))
                except Exception:
                    pass
                log("call " + path)
                return n
        except Exception as e:
            log("call {} : {}".format(path, e))
    return None


def destroy_bad_leftovers():
    """Kill GrassFill / vertical water leftovers / stray Scene_ if any survive rebuild."""
    killed = 0
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if "GrassFill" in lab:
            try:
                eas().destroy_actor(a)
                killed += 1
            except Exception:
                pass
            continue
        if lab.startswith("VMF_Water") or "Water" in lab and lab.startswith("VMF_"):
            try:
                r = a.get_actor_rotation()
                if abs(r.pitch) > 5.0 or abs(r.roll) > 5.0:
                    log("BAD water rot p={:.1f} y={:.1f} r={:.1f} -> destroy {}".format(
                        r.pitch, r.yaw, r.roll, lab))
                    eas().destroy_actor(a)
                    killed += 1
                    continue
                # force flat
                flat = unreal.Rotator()
                flat.pitch = 0.0
                flat.yaw = 0.0
                flat.roll = 0.0
                a.set_actor_rotation(flat, False)
            except Exception as e:
                log("water check " + str(e))
    log("destroyed leftovers={}".format(killed))


def fix_springarm(yaw=CAM_YAW):
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    detail = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(h)
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj:
            continue
        cname = obj.get_class().get_name()
        name = str(lib.get_variable_name(data))
        if "SpringArm" in cname or name == "SpringArm":
            try:
                obj.set_editor_property("target_arm_length", CAM_ARM)
            except Exception:
                pass
            for prop, val in (
                ("do_collision_test", False), ("b_do_collision_test", False),
                ("use_pawn_control_rotation", False), ("b_use_pawn_control_rotation", False),
                ("inherit_pitch", False), ("b_inherit_pitch", False),
                ("inherit_yaw", False), ("b_inherit_yaw", False),
                ("inherit_roll", False), ("b_inherit_roll", False),
            ):
                try:
                    obj.set_editor_property(prop, val)
                except Exception:
                    pass
            rot = unreal.Rotator()
            rot.pitch = CAM_PITCH
            rot.yaw = float(yaw)
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
                    obj.set_editor_property(prop, False)
                    detail.append("Orient=False")
                    break
                except Exception:
                    pass
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(CHAR)
    return "; ".join(detail)


def ensure_imc():
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    if not imc:
        return "NO IMC"
    results = []
    for key_name, ia_path in IA_MAP.items():
        if not unreal.EditorAssetLibrary.does_asset_exist(ia_path):
            results.append("{}:MISSING".format(key_name))
            continue
        ia = unreal.EditorAssetLibrary.load_asset(ia_path)
        k = unreal.Key()
        k.import_text(key_name)
        try:
            imc.unmap_all_keys_from_action(ia)
        except Exception:
            pass
        try:
            m = imc.map_key(ia, k)
            results.append("{}:ok".format(key_name))
        except Exception as e:
            results.append("{}:{}".format(key_name, e))
    unreal.EditorAssetLibrary.save_asset(IMC)
    txt = imc.get_editor_property("default_key_mappings").export_text()
    results.append("hasE={} F={} R={} G={} H={}".format(
        "Key=E" in txt, "Key=F" in txt, "Key=R" in txt, "Key=G" in txt, "Key=H" in txt))
    return "; ".join(results)


def ensure_cam_relative_move():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

    ami_x = ami_y = None
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) != "AddMovementInput":
            continue
        sc = find_pin(n, "ScaleValue", "Input")
        if not sc:
            continue
        for c in sc.list_connected_pins():
            if str(c.get_pin_name()) == "X":
                ami_x = n
            if str(c.get_pin_name()) == "Y":
                ami_y = n
    if not ami_x or not ami_y:
        return "FAIL AMI"

    wd = find_pin(ami_y, "WorldDirection", "Input")
    if wd:
        for c in wd.list_connected_pins():
            t = bel.get_node_title(c.get_owning_node())
            if any(k in t for k in ("Normal", "Forward", "Right", "Get World Rotation", "GetComponentRotation")):
                return "already cam-rel: " + t

    for ami in (ami_x, ami_y):
        break_links(find_pin(ami, "WorldDirection", "Input"))

    bx, by = -1600, -300
    get_cam = try_call(ge, ["/Script/Engine.Actor:GetComponentByClass"], (bx, by))
    if get_cam:
        cp = find_pin(get_cam, "ComponentClass", "Input") or find_pin(get_cam, "Class", "Input")
        set_val(cp, "/Script/Engine.CameraComponent", "camclass")
    if not get_cam:
        return "FAIL no camera ref"

    get_rot = try_call(ge, ["/Script/Engine.SceneComponent:K2_GetComponentRotation"], (bx + 280, by))
    if not get_rot:
        get_rot = try_create(ge, ["Get World Rotation", "K2_GetComponentRotation"], (bx + 280, by))
    if not get_rot:
        return "FAIL no get_rot"

    cam_out = (find_pin(get_cam, "ReturnValue", "Output")
               or find_pin(get_cam, "Camera", "Output"))
    rot_self = find_pin(get_rot, "self", "Input") or find_pin(get_rot, "Target", "Input")
    connect(cam_out, rot_self, "cam->rot")

    rot_out = find_pin(get_rot, "ReturnValue", "Output")
    br = try_call(ge, ["/Script/Engine.KismetMathLibrary:BreakRotator"], (bx + 560, by))
    mr = try_call(ge, ["/Script/Engine.KismetMathLibrary:MakeRotator"], (bx + 820, by))
    flat = rot_out
    if br and mr and rot_out:
        connect(rot_out, find_pin(br, "Rotation", "Input") or find_pin(br, "InRot", "Input") or find_pin(br, "A", "Input"), "rot->br")
        connect(find_pin(br, "Yaw", "Output"), find_pin(mr, "Yaw", "Input"), "yaw")
        set_val(find_pin(mr, "Pitch", "Input"), "0.0", "p0")
        set_val(find_pin(mr, "Roll", "Input"), "0.0", "r0")
        flat = find_pin(mr, "ReturnValue", "Output")

    fwd = try_call(ge, ["/Script/Engine.KismetMathLibrary:GetForwardVector"], (bx + 1100, by - 80))
    right = try_call(ge, ["/Script/Engine.KismetMathLibrary:GetRightVector"], (bx + 1100, by + 80))
    if not fwd or not right:
        return "FAIL fwd/right"
    connect(flat, find_pin(fwd, "InRot", "Input") or find_pin(fwd, "A", "Input") or find_pin(fwd, "Rotation", "Input"), "flat->fwd")
    connect(flat, find_pin(right, "InRot", "Input") or find_pin(right, "A", "Input") or find_pin(right, "Rotation", "Input"), "flat->right")

    n2d_f = try_call(ge, ["/Script/Engine.KismetMathLibrary:Vector_Normal2D"], (bx + 1400, by - 80))
    n2d_r = try_call(ge, ["/Script/Engine.KismetMathLibrary:Vector_Normal2D"], (bx + 1400, by + 80))
    if n2d_f and n2d_r:
        connect(find_pin(fwd, "ReturnValue", "Output"), find_pin(n2d_f, "A", "Input") or find_pin(n2d_f, "InVec", "Input"), "f->n")
        connect(find_pin(right, "ReturnValue", "Output"), find_pin(n2d_r, "A", "Input") or find_pin(n2d_r, "InVec", "Input"), "r->n")
        connect(find_pin(n2d_f, "ReturnValue", "Output"), find_pin(ami_y, "WorldDirection", "Input"), "W=fwd")
        connect(find_pin(n2d_r, "ReturnValue", "Output"), find_pin(ami_x, "WorldDirection", "Input"), "AD=right")
    else:
        return "FAIL Normal2D"

    try:
        bel.compile_blueprint(bp)
        log("compile ok")
    except Exception as e:
        log("compile " + str(e))
    unreal.EditorAssetLibrary.save_asset(CHAR)
    return "cam-relative ok"


def ensure_floor():
    mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    center = unreal.Vector(FARM * CELL * 0.5, FARM * CELL * 0.5, 0.0)
    scale = unreal.Vector(float(FARM), float(FARM), 1.0)
    actor = None
    for a in eas().get_all_level_actors():
        if (a.get_actor_label() or "") == FLOOR_LABEL:
            actor = a
            break
    if actor is None:
        actor = eas().spawn_actor_from_class(unreal.StaticMeshActor, center, unreal.Rotator())
        actor.set_actor_label(FLOOR_LABEL)
    flat = unreal.Rotator()
    flat.pitch = 0.0
    flat.yaw = 0.0
    flat.roll = 0.0
    actor.set_actor_location(center, False, True)
    actor.set_actor_rotation(flat, False)
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
        log("floor " + str(e))
    return True


def ensure_playerstart():
    spawn = unreal.Vector(17.5 * CELL, 16.5 * CELL, 100.0)
    ps = None
    for a in eas().get_all_level_actors():
        cn = a.get_class().get_name()
        lab = a.get_actor_label() or ""
        if cn == "PlayerStart" or lab == "PlayerStart":
            ps = a
            break
    if ps is None:
        ps = eas().spawn_actor_from_class(unreal.PlayerStart, spawn, unreal.Rotator())
        ps.set_actor_label("PlayerStart")
    else:
        ps.set_actor_location(spawn, False, True)
    loc = ps.get_actor_location()
    return "({:.0f},{:.0f},{:.0f})".format(loc.x, loc.y, loc.z)


def verify():
    counts = {"Grass": 0, "Soil": 0, "Fence": 0, "Path": 0, "Tree": 0, "Cliff": 0,
              "Water": 0, "Crop": 0, "Bridge": 0}
    water_rots = []
    bad_pitch = []
    zs = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if not lab.startswith("VMF_"):
            continue
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        if abs(rot.pitch) > 5.0 or abs(rot.roll) > 5.0:
            bad_pitch.append((lab, round(rot.pitch, 1), round(rot.roll, 1)))
        if lab.startswith("VMF_Grass_"):
            counts["Grass"] += 1
            zs.append(loc.z)
        if "Soil" in lab:
            counts["Soil"] += 1
        if "Fence" in lab:
            counts["Fence"] += 1
        if lab.startswith("VMF_Path") or "Bridge" in lab:
            counts["Path" if "Path" in lab else "Bridge"] += 1
        if "Tree" in lab:
            counts["Tree"] += 1
        if lab.startswith("VMF_Cliff"):
            counts["Cliff"] += 1
        if "Water" in lab:
            counts["Water"] += 1
            water_rots.append((lab, round(rot.pitch, 2), round(rot.yaw, 2), round(rot.roll, 2),
                               round(loc.x), round(loc.y), round(loc.z)))
        if "Crop" in lab:
            counts["Crop"] += 1

    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    arm = "?"
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        obj = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if obj and "SpringArm" in obj.get_class().get_name():
            r = obj.get_editor_property("relative_rotation")
            arm = "p={:.0f} y={:.0f} arm={}".format(
                r.pitch, r.yaw, obj.get_editor_property("target_arm_length"))
    ps_s = "?"
    for a in eas().get_all_level_actors():
        if a.get_actor_label() == "PlayerStart":
            loc = a.get_actor_location()
            ps_s = "({:.0f},{:.0f},{:.0f})".format(loc.x, loc.y, loc.z)
            break
    vmf = sum(1 for a in eas().get_all_level_actors() if (a.get_actor_label() or "").startswith("VMF_"))
    zmin = min(zs) if zs else None
    zmax = max(zs) if zs else None
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    txt = imc.get_editor_property("default_key_mappings").export_text()
    return {
        "counts": counts,
        "VMF_total": vmf,
        "SpringArm": arm,
        "PlayerStart": ps_s,
        "water_rots": water_rots,
        "bad_pitch_n": len(bad_pitch),
        "bad_pitch_sample": bad_pitch[:8],
        "grass_z_range": (zmin, zmax),
        "IMC": "E={} F={} R={} G={} H={}".format(
            "Key=E" in txt, "Key=F" in txt, "Key=R" in txt, "Key=G" in txt, "Key=H" in txt),
    }


def save_level():
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        return True
    except Exception:
        try:
            unreal.EditorLevelLibrary.save_current_level()
            return True
        except Exception as e:
            log("save " + str(e))
            return False


def main():
    log("=== START rebuild_safe post ===")
    destroy_bad_leftovers()
    log("springarm: " + fix_springarm(CAM_YAW))
    log("imc: " + ensure_imc())
    log("move: " + ensure_cam_relative_move())
    ensure_floor()
    log("PlayerStart: " + ensure_playerstart())
    save_level()
    v = verify()
    log("VERIFY " + str(v))
    log("=== DONE yaw={} (no rotate) ===".format(CAM_YAW))


if __name__ == "__main__":
    main()

