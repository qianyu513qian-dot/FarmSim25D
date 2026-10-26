# -*- coding: utf-8 -*-
"""Hide TopDown template graybox in Lvl_TopDown; restore PlayerStart + iso cam; save.
Re-run: python Content/Python/run_remote.py Content/Python/phase_hide_template_arena.py
Does NOT touch VMF_*/Scene_*/Farm_* props (except FarmGround/FarmBorder), BP_GridManager, lights, sky.
"""
import unreal

def log(m):
    unreal.log("[HIDE_ARENA] " + str(m))

CELL = 100.0
WIDTH = 40
HEIGHT = 40
ORIGIN = unreal.Vector(0.0, 0.0, 0.0)
# Authored PS_CX,PS_CY = 17,16 then mirrored X for yaw=135 -> grid ~ (22,16)
PS_CX_MIRRORED = WIDTH - 1 - 17  # 22
PS_CY = 16
CAM_PITCH = -40.0
CAM_YAW = 135.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0
BP_PATH = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

KEEP_PREFIX = ("VMF_", "Scene_")
KEEP_EXACT = {
    "PlayerStart", "DirectionalLight", "SkyLight", "SkyAtmosphere",
    "ExponentialHeightFog", "VolumetricCloud", "SM_SkySphere", "BP_Sky_Sphere",
    "NavMeshBoundsVolume", "RecastNavMesh-Default", "WorldDataLayers",
    "WorldPartitionMiniMap0", "WorldSettings", "AbstractNavData",
    "DefaultPhysicsVolume", "PostProcessVolume", "BP_GridManager",
}
KEEP_CLASS = {
    "PlayerStart", "DirectionalLight", "SkyLight", "SkyAtmosphere",
    "ExponentialHeightFog", "VolumetricCloud", "WorldSettings",
    "AbstractNavData", "DefaultPhysicsVolume", "NavMeshBoundsVolume",
    "Landscape", "PostProcessVolume",
}


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def cell_center(cx, cy, z=100.0):
    return unreal.Vector(ORIGIN.x + (cx + 0.5) * CELL,
                         ORIGIN.y + (cy + 0.5) * CELL, z)


def is_keep(a):
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    if lab.startswith(KEEP_PREFIX):
        return True
    if lab.startswith("BP_") and lab not in ("BP_Sky_Sphere",):
        # Keep gameplay BPs (GridManager, characters placed as BP_*)
        # but NOT template sky sphere already in KEEP_EXACT
        return True
    if lab in KEEP_EXACT or cn in KEEP_CLASS:
        return True
    if "Sky" in lab or "Sky" in cn or "Atmosphere" in cn or "Fog" in cn or "Cloud" in cn:
        return True
    if cn == "PlayerStart" or "PlayerStart" in cn:
        return True
    return False


def is_proto(a):
    """True if this is TopDown template / old farm graybox to hide."""
    if is_keep(a):
        return False
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    mesh_name = mesh_path = ""
    try:
        smc = a.static_mesh_component
        if smc and smc.static_mesh:
            mesh_name = smc.static_mesh.get_name()
            mesh_path = smc.static_mesh.get_path_name()
    except Exception:
        pass

    # Explicit old farm plane / borders
    if lab in ("FarmGround", "FarmGround_Grass", "GroundPlane") or lab.startswith("FarmBorder"):
        return True
    if lab == "Floor" or "Template_Map_Floor" in mesh_name or "Template_Map_Floor" in lab:
        return True
    if lab.startswith(("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_Quarter", "SM_Chamfer")):
        return True
    if mesh_name in ("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_QuarterCylinder",
                     "SM_Template_Map_Floor", "SM_ChamferCube"):
        return True
    if "LevelPrototyping" in mesh_path or "Prototype" in mesh_path or "Prototype" in lab:
        return True
    if "Template" in lab or "Template" in mesh_name:
        return True
    if any(k in lab for k in ("Arena", "Blockout", "Cube_Floor", "Floor_400x400")):
        return True
    # StaticMeshActor with prototyping mesh path
    if cn == "StaticMeshActor" and ("LevelPrototyping" in mesh_path or mesh_name.startswith("SM_")):
        # Only if not already keep (VMF meshes are SM_VMF_* under Farm path)
        if "VoxelMicroFarm" in mesh_path or "/Farm/" in mesh_path or mesh_name.startswith("SM_VMF"):
            return False
        if mesh_name.startswith("SM_") and "LevelPrototyping" in mesh_path:
            return True
        if mesh_name.startswith(("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_Quarter", "SM_Chamfer", "SM_Template")):
            return True
    return False


def hide_actor(a):
    lab = a.get_actor_label() or ""
    try:
        a.set_actor_hidden_in_game(True)
    except Exception:
        pass
    try:
        a.set_is_temporarily_hidden_in_editor(True)
    except Exception:
        pass
    try:
        a.set_actor_enable_collision(False)
    except Exception:
        pass
    try:
        smc = a.static_mesh_component
        if smc:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            try:
                smc.set_visibility(False, True)
            except Exception:
                pass
    except Exception:
        pass
    # Park far away so editor framing / clipping won't show them
    try:
        loc = a.get_actor_location()
        if abs(loc.x) < 40000 and abs(loc.y) < 40000:
            a.set_actor_location(unreal.Vector(-55000.0, -55000.0, -2000.0), False, True)
    except Exception:
        pass
    log("hid " + lab)


def hide_all_proto():
    n = 0
    names = []
    for a in eas().get_all_level_actors():
        if not is_proto(a):
            continue
        hide_actor(a)
        names.append(a.get_actor_label() or "?")
        n += 1
    return n, names


def fix_player_start():
    spawn = cell_center(PS_CX_MIRRORED, PS_CY, 100.0)
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
                try:
                    a.set_actor_hidden_in_game(False)
                    a.set_is_temporarily_hidden_in_editor(False)
                except Exception:
                    pass
            else:
                try:
                    eas().destroy_actor(a)
                except Exception:
                    pass
    if kept is None:
        try:
            kept = eas().spawn_actor_from_class(unreal.PlayerStart, spawn, unreal.Rotator())
            kept.set_actor_label("PlayerStart")
            log("spawned PlayerStart")
        except Exception as e:
            log("PlayerStart spawn fail: " + str(e))
            return None
    loc = kept.get_actor_location()
    log("PlayerStart @ ({:.0f},{:.0f},{:.0f}) grid~({},{})".format(
        loc.x, loc.y, loc.z, PS_CX_MIRRORED, PS_CY))
    return (round(loc.x), round(loc.y), round(loc.z))


def fix_camera():
    bp = unreal.EditorAssetLibrary.load_asset(BP_PATH)
    if not bp:
        log("NO BP_TopDownCharacter")
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
                ("do_collision_test", False),
                ("b_do_collision_test", False),
                ("use_pawn_control_rotation", False),
                ("b_use_pawn_control_rotation", False),
                ("inherit_pitch", False),
                ("b_inherit_pitch", False),
                ("inherit_yaw", False),
                ("b_inherit_yaw", False),
                ("inherit_roll", False),
                ("b_inherit_roll", False),
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
                detail.append("SpringArm p={:.0f} y={:.0f} arm={}".format(
                    now.pitch, now.yaw, CAM_ARM))
            except Exception as e:
                detail.append("SpringArm fail " + str(e))
        if cname == "CameraComponent" or name == "Camera":
            try:
                obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", CAM_ORTHO)
                detail.append("ortho={}".format(CAM_ORTHO))
            except Exception as e:
                detail.append("cam fail " + str(e))
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(BP_PATH)
    return "; ".join(detail) if detail else "no springarm"


def focus_editor_on_farm():
    """Point level editor camera toward farm center so user sees VMF not void."""
    center = unreal.Vector(WIDTH * CELL * 0.5, HEIGHT * CELL * 0.5, 0.0)
    try:
        # Look from iso-ish position
        look_from = unreal.Vector(center.x - 2200.0, center.y - 2200.0, 1800.0)
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(look_from, unreal.Rotator(-40.0, 135.0, 0.0))
        log("viewport cam set toward farm center")
        return True
    except Exception as e:
        log("viewport cam fail: " + str(e))
        try:
            els = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            # some builds use different API; ignore
        except Exception:
            pass
        return False


def save_level():
    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = els.save_current_level()
        log("save_current_level -> " + str(ok))
        return bool(ok)
    except Exception as e:
        log("save fail: " + str(e))
        try:
            unreal.EditorLevelLibrary.save_current_level()
            log("save via EditorLevelLibrary")
            return True
        except Exception as e2:
            log("save2 fail: " + str(e2))
            return False


def verify():
    vis_proto = 0
    vmf = 0
    ps = None
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_"):
            vmf += 1
        if is_proto(a):
            # after hide, still "proto" by identity; check hidden flags
            hid = False
            try:
                hid = a.is_temporarily_hidden_in_editor()
            except Exception:
                pass
            if not hid:
                vis_proto += 1
                log("STILL_VISIBLE " + lab)
        cn = a.get_class().get_name()
        if cn == "PlayerStart" or lab == "PlayerStart":
            loc = a.get_actor_location()
            ps = (round(loc.x), round(loc.y), round(loc.z))
    log("verify vmf={} still_visible_proto={} PlayerStart={}".format(vmf, vis_proto, ps))
    return vis_proto, vmf, ps


def main():
    log("=== START hide template arena ===")
    # Ensure Lvl_TopDown is current if possible
    try:
        path = unreal.EditorLevelLibrary.get_editor_world().get_path_name()
        log("world=" + str(path))
    except Exception as e:
        log("world path fail " + str(e))

    n, names = hide_all_proto()
    log("hidden_count={}".format(n))
    for nm in sorted(names):
        pass  # already logged per-actor

    ps = fix_player_start()
    cam = fix_camera()
    log("cam: " + str(cam))
    focus_editor_on_farm()
    saved = save_level()
    vis, vmf, ps2 = verify()
    log("SUMMARY hidden={} saved={} PlayerStart={} cam=[{}] vmf={} leftover_visible_proto={}".format(
        n, saved, ps2 or ps, cam, vmf, vis))
    log("=== END ===")


main()
