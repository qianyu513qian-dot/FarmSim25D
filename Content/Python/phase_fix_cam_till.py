# -*- coding: utf-8 -*-
"""Fix Lvl_TopDown: camera yaw90 so W=screen-up + empty SoilUntilled till zone near PlayerStart.

Re-run: python Content/Python/run_remote.py Content/Python/phase_fix_cam_till.py

A) SpringArm pitch=-40 yaw=90 ortho=2800 (was yaw135; W world +Y now matches screen top).
   Orient Rotation to Movement = False.
B) Clear blockers; place VMF_Hoe_* SoilUntilled on Grid union:
   - Till patch (23-26, 20-23) east of path, north of bridge (bridge rows 18-19 skipped)
   - Legacy HOE (25-27, 20-22)
PlayerStart stays Grid(22,16)=(2250,1650,100). Saves BP + level.
"""
import unreal

def log(m):
    unreal.log("[CAMTILL] " + str(m))
    print("[CAMTILL] " + str(m))

CELL = 100.0
ORIGIN = unreal.Vector(0.0, 0.0, 0.0)
PS_CX, PS_CY = 22, 16
TILL_X0, TILL_X1 = 23, 26
TILL_Y0, TILL_Y1 = 20, 23
HOE_X0, HOE_X1 = 25, 27
HOE_Y0, HOE_Y1 = 20, 22
BRIDGE_ROWS = (18, 19)
PATH_COLS = (21, 22)
CAM_PITCH = -40.0
CAM_YAW = 90.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0
BP_PATH = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
UNTILLED = "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Untilled"
Z_SOIL = 1.8


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def cell_center(cx, cy, z=0.0):
    return unreal.Vector(ORIGIN.x + (cx + 0.5) * CELL,
                         ORIGIN.y + (cy + 0.5) * CELL, z)


def grid_of(a):
    loc = a.get_actor_location()
    return int(loc.x // CELL), int(loc.y // CELL)


def wanted(gx, gy):
    if gy in BRIDGE_ROWS or gx in PATH_COLS:
        return False
    in_till = TILL_X0 <= gx <= TILL_X1 and TILL_Y0 <= gy <= TILL_Y1
    in_hoe = HOE_X0 <= gx <= HOE_X1 and HOE_Y0 <= gy <= HOE_Y1
    return in_till or in_hoe


def fix_camera_and_move():
    bp = unreal.EditorAssetLibrary.load_asset(BP_PATH)
    if not bp:
        return "no bp"
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
            rot.yaw = CAM_YAW
            rot.roll = 0.0
            try:
                obj.set_editor_property("relative_rotation", rot)
                now = obj.get_editor_property("relative_rotation")
                detail.append("SpringArm p={:.0f} y={:.0f}".format(now.pitch, now.yaw))
            except Exception as e:
                detail.append("SpringArm fail " + str(e))
        if cname == "CameraComponent" or name == "Camera":
            try:
                obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", CAM_ORTHO)
                detail.append("ortho={}".format(CAM_ORTHO))
            except Exception as e:
                detail.append("cam " + str(e))
        if "CharacterMovement" in cname or name in ("CharacterMovement", "CharMoveComp"):
            for prop in ("orient_rotation_to_movement", "b_orient_rotation_to_movement"):
                try:
                    obj.set_editor_property(prop, False)
                    detail.append("OrientRotToMove=False")
                    break
                except Exception:
                    pass
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(BP_PATH)
    return "; ".join(detail)


def mesh_xy_size(mesh):
    try:
        box = mesh.get_bounding_box()
        return abs(box.max.x - box.min.x), abs(box.max.y - box.min.y)
    except Exception:
        return CELL, CELL


def rebuild_hoe_tiles():
    removed = 0
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_Hoe_"):
            try:
                eas().destroy_actor(a)
                removed += 1
            except Exception:
                pass

    keep_sub = ("Grass", "Path", "Water", "Bridge", "House", "Fence", "Cliff", "Bank", "Yard", "FarmShed")
    kill_sub = ("Soil", "Crop", "Corn", "Tomato", "Pumpkin", "Tree", "Bush", "Rock", "Clump", "Flower", "Crate", "Chest", "Hoe")
    killed = []
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if not lab.startswith("VMF_"):
            continue
        if any(k in lab for k in keep_sub):
            continue
        if not any(k in lab for k in kill_sub):
            continue
        gx, gy = grid_of(a)
        if wanted(gx, gy):
            try:
                eas().destroy_actor(a)
                killed.append(lab)
            except Exception:
                pass

    mesh = unreal.EditorAssetLibrary.load_asset(UNTILLED)
    if not mesh:
        log("MISSING untilled")
        return removed, killed, 0, []
    sx, sy = mesh_xy_size(mesh)
    f = CELL / max(max(sx, sy), 1.0)
    scale = unreal.Vector(f, f, f)
    cells = sorted(set(
        (cx, cy)
        for cy in range(min(TILL_Y0, HOE_Y0), max(TILL_Y1, HOE_Y1) + 1)
        for cx in range(min(TILL_X0, HOE_X0), max(TILL_X1, HOE_X1) + 1)
        if wanted(cx, cy)
    ))
    for cx, cy in cells:
        lab = "VMF_Hoe_{}_{}".format(cx, cy)
        actor = eas().spawn_actor_from_class(
            unreal.StaticMeshActor, cell_center(cx, cy, Z_SOIL), unreal.Rotator())
        actor.set_actor_label(lab)
        actor.set_actor_scale3d(scale)
        smc = actor.static_mesh_component
        smc.set_static_mesh(mesh)
        try:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            actor.set_actor_enable_collision(False)
        except Exception:
            pass
    return removed, killed, len(cells), cells


def fix_player_start():
    spawn = cell_center(PS_CX, PS_CY, 100.0)
    kept = None
    for a in eas().get_all_level_actors():
        cn = a.get_class().get_name()
        lab = a.get_actor_label() or ""
        if cn == "PlayerStart" or lab == "PlayerStart" or "PlayerStart" in cn:
            if kept is None:
                kept = a
                a.set_actor_location(spawn, False, True)
                try:
                    a.set_actor_label("PlayerStart")
                except Exception:
                    pass
            else:
                try:
                    eas().destroy_actor(a)
                except Exception:
                    pass
    if kept is None:
        kept = eas().spawn_actor_from_class(unreal.PlayerStart, spawn, unreal.Rotator())
        kept.set_actor_label("PlayerStart")
    loc = kept.get_actor_location()
    return (round(loc.x), round(loc.y), round(loc.z))


def save_level():
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        return True
    except Exception:
        try:
            unreal.EditorLevelLibrary.save_current_level()
            return True
        except Exception as e:
            log("save fail " + str(e))
            return False


def main():
    log("=== START phase_fix_cam_till ===")
    cam = fix_camera_and_move()
    log("camera: " + cam)
    removed, killed, placed, cells = rebuild_hoe_tiles()
    log("hoe removed={} blockers_killed={} placed={} cells={}".format(
        removed, len(killed), placed, cells))
    ps = fix_player_start()
    log("PlayerStart Grid({},{}) world={}".format(PS_CX, PS_CY, ps))
    try:
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            unreal.Vector(2450.0, 1950.0 - 2800.0, 1800.0),
            unreal.Rotator(-40.0, 90.0, 0.0))
    except Exception:
        pass
    save_level()
    log("SUMMARY pitch={} yaw={} ortho={}".format(CAM_PITCH, CAM_YAW, CAM_ORTHO))
    log("SUMMARY WASD W=+Y S=-Y A=-X D=+X; yaw90 => W=screen-up")
    log("SUMMARY till Grid({}-{},{}-{}) U HOE({}-{},{}-{}) skip bridge{}".format(
        TILL_X0, TILL_X1, TILL_Y0, TILL_Y1, HOE_X0, HOE_X1, HOE_Y0, HOE_Y1, BRIDGE_ROWS))
    log("=== DONE ===")


if __name__ == "__main__":
    main()
