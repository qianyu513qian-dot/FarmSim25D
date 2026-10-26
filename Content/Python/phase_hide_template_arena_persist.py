# -*- coding: utf-8 -*-
"""PERMANENTLY delete TopDown template graybox from Lvl_TopDown + force-save ExternalActors.

Why reopen brought gray arena back:
  phase_hide_template_arena.py only set_is_temporarily_hidden_in_editor + parked actors.
  Temporary editor hide does NOT persist across project reopen; under Critical memory,
  ExternalActors packages often fail to flush, so hid/moved state never hit disk.

This script DESTROYS proto actors (DestroyActor), then force-saves the umap and dirty
ExternalActors packages so they cannot reappear.

Safe keep: VMF_*, Scene_*, FarmCollisionFloor, Farm_* gameplay, BP_* (not sky),
PlayerStart, lights/sky/fog/nav, BP_GridManager, cameras.

Re-run: python Content/Python/run_remote.py Content/Python/phase_hide_template_arena_persist.py
"""
import unreal
import time

TAG = "[HIDE_ARENA_PERSIST] "


def log(m):
    s = TAG + str(m)
    unreal.log(s)
    print(s)


CELL = 100.0
FARM = 40
CAM_PITCH = -40.0
CAM_YAW = -90.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0
BP_PATH = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
FLOOR_LABEL = "FarmCollisionFloor"
PS_X = 17.5 * CELL
PS_Y = 16.5 * CELL

KEEP_PREFIX = ("VMF_", "Scene_")
KEEP_EXACT = {
    "PlayerStart", "DirectionalLight", "SkyLight", "SkyAtmosphere",
    "ExponentialHeightFog", "VolumetricCloud", "SM_SkySphere", "BP_Sky_Sphere",
    "NavMeshBoundsVolume", "RecastNavMesh-Default", "WorldDataLayers",
    "WorldPartitionMiniMap0", "WorldSettings", "AbstractNavData",
    "DefaultPhysicsVolume", "PostProcessVolume", "BP_GridManager",
    FLOOR_LABEL,
}
KEEP_CLASS = {
    "PlayerStart", "DirectionalLight", "SkyLight", "SkyAtmosphere",
    "ExponentialHeightFog", "VolumetricCloud", "WorldSettings",
    "AbstractNavData", "DefaultPhysicsVolume", "NavMeshBoundsVolume",
    "Landscape", "PostProcessVolume",
}
# Old plane / borders that look like Farm_ but are graybox leftovers
FORCE_DESTROY_LABELS = {
    "FarmGround", "FarmGround_Grass", "GroundPlane", "Floor",
}
FORCE_DESTROY_PREFIX = ("FarmBorder",)


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def is_keep(a):
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    if lab in FORCE_DESTROY_LABELS or any(lab.startswith(p) for p in FORCE_DESTROY_PREFIX):
        return False
    if lab == FLOOR_LABEL:
        return True
    if lab.startswith(KEEP_PREFIX):
        return True
    # Keep Farm_* gameplay (collision floor already exact-kept); not FarmGround/Border
    if lab.startswith("Farm_") or lab.startswith("Farm"):
        if lab in FORCE_DESTROY_LABELS or any(lab.startswith(p) for p in FORCE_DESTROY_PREFIX):
            return False
        return True
    if lab.startswith("BP_") and lab not in ("BP_Sky_Sphere",):
        return True
    if lab in KEEP_EXACT or cn in KEEP_CLASS:
        return True
    if "Sky" in lab or "Sky" in cn or "Atmosphere" in cn or "Fog" in cn or "Cloud" in cn:
        return True
    if cn == "PlayerStart" or "PlayerStart" in cn:
        return True
    return False


def is_proto(a):
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

    if lab in FORCE_DESTROY_LABELS or any(lab.startswith(p) for p in FORCE_DESTROY_PREFIX):
        return True
    if lab == "Floor" or "Template_Map_Floor" in mesh_name or "Template_Map_Floor" in lab:
        return True
    if lab.startswith(("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_Quarter", "SM_Chamfer")):
        return True
    if mesh_name in (
        "SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_QuarterCylinder",
        "SM_Template_Map_Floor", "SM_ChamferCube",
    ):
        return True
    if "LevelPrototyping" in mesh_path or "Prototype" in mesh_path or "Prototype" in lab:
        return True
    if "Template" in lab or "Template" in mesh_name:
        return True
    if any(k in lab for k in ("Arena", "Blockout", "Cube_Floor", "Floor_400x400")):
        return True
    if cn == "StaticMeshActor":
        if "VoxelMicroFarm" in mesh_path or "/Farm/" in mesh_path or mesh_name.startswith("SM_VMF"):
            return False
        if "LevelPrototyping" in mesh_path:
            return True
        if mesh_name.startswith(("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_Quarter", "SM_Chamfer", "SM_Template")):
            return True
        # Gray Engine/BasicShapes cubes/cylinders used by template (not our invisible floor Plane)
        if lab.startswith("SM_") and "BasicShapes" in mesh_path and mesh_name != "Plane":
            return True
    return False


def destroy_all_proto():
    destroyed = 0
    failed = 0
    names = []
    # Snapshot list first — mutating while iterating is unsafe
    actors = list(eas().get_all_level_actors())
    for a in actors:
        if not is_proto(a):
            continue
        lab = a.get_actor_label() or "?"
        try:
            # Soft-disable first so a partial flush still won't show them
            try:
                a.set_actor_hidden_in_game(True)
                a.set_is_temporarily_hidden_in_editor(True)
                a.set_actor_enable_collision(False)
            except Exception:
                pass
            ok = eas().destroy_actor(a)
            if ok is False:
                failed += 1
                log("destroy FAIL " + lab)
            else:
                destroyed += 1
                names.append(lab)
                log("destroyed " + lab)
        except Exception as e:
            failed += 1
            log("destroy EXC " + lab + " " + str(e))
    return destroyed, failed, names


def ensure_floor():
    mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    center = unreal.Vector(FARM * CELL * 0.5, FARM * CELL * 0.5, 0.0)
    scale = unreal.Vector(float(FARM), float(FARM), 1.0)
    actor = None
    for a in eas().get_all_level_actors():
        if (a.get_actor_label() or "") == FLOOR_LABEL:
            actor = a
            break
    created = False
    if actor is None:
        actor = eas().spawn_actor_from_class(unreal.StaticMeshActor, center, unreal.Rotator())
        actor.set_actor_label(FLOOR_LABEL)
        created = True
    flat = unreal.Rotator()
    flat.pitch = 0.0
    flat.yaw = 0.0
    flat.roll = 0.0
    actor.set_actor_location(center, False, True)
    actor.set_actor_rotation(flat, False)
    actor.set_actor_scale3d(scale)
    smc = actor.static_mesh_component
    if mesh:
        smc.set_static_mesh(mesh)
    try:
        smc.set_visibility(False, True)
        actor.set_actor_hidden_in_game(True)
        actor.set_is_temporarily_hidden_in_editor(True)
        actor.set_actor_enable_collision(True)
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        smc.set_editor_property("collision_profile_name", "BlockAll")
    except Exception as e:
        log("floor props " + str(e))
    log("FarmCollisionFloor created={} loc=({},{},{})".format(
        created, round(center.x), round(center.y), round(center.z)))
    return True


def ensure_playerstart():
    spawn = unreal.Vector(PS_X, PS_Y, 100.0)
    kept = None
    for a in list(eas().get_all_level_actors()):
        cn = a.get_class().get_name()
        lab = a.get_actor_label() or ""
        if cn == "PlayerStart" or lab == "PlayerStart" or "PlayerStart" in cn:
            if kept is None:
                kept = a
                a.set_actor_location(spawn, False, True)
                try:
                    a.set_actor_label("PlayerStart")
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
        kept = eas().spawn_actor_from_class(unreal.PlayerStart, spawn, unreal.Rotator())
        kept.set_actor_label("PlayerStart")
        log("spawned PlayerStart")
    loc = kept.get_actor_location()
    log("PlayerStart @ ({:.0f},{:.0f},{:.0f})".format(loc.x, loc.y, loc.z))
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
    try:
        unreal.EditorAssetLibrary.save_asset(BP_PATH)
    except Exception as e:
        log("save bp fail " + str(e))
    return "; ".join(detail) if detail else "no springarm"


def check_streaming_levels():
    info = []
    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
        # Persistent level path
        try:
            info.append("world=" + str(world.get_path_name()))
        except Exception:
            pass
        try:
            levels = world.get_levels()
            info.append("levels_count=" + str(len(levels) if levels else 0))
            for lv in (levels or [])[:20]:
                try:
                    info.append("level=" + str(lv.get_outer().get_path_name() if lv.get_outer() else lv.get_name()))
                except Exception:
                    try:
                        info.append("level=" + str(lv.get_path_name()))
                    except Exception:
                        info.append("level=?")
        except Exception as e:
            info.append("get_levels " + str(e))
        # Streaming
        try:
            streamings = world.get_streaming_levels()
            info.append("streaming_count=" + str(len(streamings) if streamings else 0))
            for s in (streamings or [])[:20]:
                try:
                    info.append("stream=" + str(s.get_world_asset_package_name()))
                except Exception:
                    info.append("stream=" + str(s))
        except Exception as e:
            info.append("streaming " + str(e))
    except Exception as e:
        info.append("world fail " + str(e))
    for line in info:
        log("LEVEL " + line)
    return info


def mark_all_actors_packages_dirty():
    """Nudge WP packages dirty so save flushes ExternalActors deletes."""
    n = 0
    for a in eas().get_all_level_actors():
        try:
            a.modify()
            n += 1
        except Exception:
            pass
    log("modify() touched actors=" + str(n))
    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
        world.modify()
    except Exception:
        pass


def force_save():
    results = {}
    # 1) LevelEditorSubsystem.save_current_level
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = les.save_current_level()
        results["save_current_level"] = bool(ok)
        log("save_current_level -> " + str(ok))
    except Exception as e:
        results["save_current_level"] = "exc:" + str(e)
        log("save_current_level exc " + str(e))
        try:
            unreal.EditorLevelLibrary.save_current_level()
            results["save_current_level_ell"] = True
            log("save via EditorLevelLibrary OK")
        except Exception as e2:
            results["save_current_level_ell"] = "exc:" + str(e2)
            log("ELL save fail " + str(e2))

    # 2) Save all dirty packages (critical for ExternalActors)
    try:
        ok2 = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        results["save_dirty_packages"] = bool(ok2) if ok2 is not None else True
        log("save_dirty_packages -> " + str(ok2))
    except Exception as e:
        results["save_dirty_packages"] = "exc:" + str(e)
        log("save_dirty_packages exc " + str(e))

    # 3) save_loaded_assets / save directory of ExternalActors
    try:
        ok3 = unreal.EditorAssetLibrary.save_directory("/Game/__ExternalActors__/TopDown/Lvl_TopDown", True, True)
        results["save_ext_dir"] = bool(ok3)
        log("save_ext_dir -> " + str(ok3))
    except Exception as e:
        results["save_ext_dir"] = "exc:" + str(e)
        log("save_ext_dir exc " + str(e))

    try:
        ok4 = unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Lvl_TopDown")
        results["save_umap_asset"] = bool(ok4)
        log("save_umap_asset -> " + str(ok4))
    except Exception as e:
        results["save_umap_asset"] = "exc:" + str(e)
        log("save_umap_asset exc " + str(e))

    return results


def verify():
    leftover = []
    vmf = 0
    floor_ok = False
    ps = None
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_"):
            vmf += 1
        if lab == FLOOR_LABEL:
            floor_ok = True
        cn = a.get_class().get_name()
        if cn == "PlayerStart" or lab == "PlayerStart":
            loc = a.get_actor_location()
            ps = (round(loc.x), round(loc.y), round(loc.z))
        if is_proto(a):
            leftover.append(lab)
            log("LEFTOVER_PROTO " + lab)
    log("verify vmf={} leftover_visible_proto={} floor={} PlayerStart={}".format(
        vmf, len(leftover), floor_ok, ps))
    return {
        "vmf": vmf,
        "leftover_visible_proto": len(leftover),
        "leftover_names": leftover[:40],
        "floor": floor_ok,
        "playerstart": ps,
    }


def focus_viewport():
    center = unreal.Vector(FARM * CELL * 0.5, FARM * CELL * 0.5, 0.0)
    try:
        look_from = unreal.Vector(center.x + 0.0, center.y - 2800.0, 2200.0)
        # Match play cam yaw=-90 (looking toward +Y / house)
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            look_from, unreal.Rotator(-40.0, -90.0, 0.0))
        log("viewport cam set yaw=-90 toward farm")
        return True
    except Exception as e:
        log("viewport cam fail " + str(e))
        return False


def main():
    log("=== START permanent destroy template arena ===")
    try:
        path = unreal.EditorLevelLibrary.get_editor_world().get_path_name()
        log("world=" + str(path))
    except Exception as e:
        log("world path fail " + str(e))

    check_streaming_levels()

    # Pre-count
    pre = sum(1 for a in eas().get_all_level_actors() if is_proto(a))
    log("pre_proto_count=" + str(pre))

    destroyed, failed, names = destroy_all_proto()
    log("destroyed_count={} failed={} sample={}".format(
        destroyed, failed, sorted(names)[:20]))

    ensure_floor()
    ps = ensure_playerstart()
    cam = fix_camera()
    log("cam: " + str(cam))
    focus_viewport()

    mark_all_actors_packages_dirty()
    # Brief yield so WP can register destroys
    try:
        time.sleep(0.2)
    except Exception:
        pass
    save_results = force_save()
    # Second save pass — WP ExternalActors sometimes need two flushes
    try:
        time.sleep(0.3)
    except Exception:
        pass
    save_results2 = force_save()

    v = verify()
    log("SUMMARY destroyed={} failed={} leftover_visible_proto={} vmf={} floor={} "
        "PlayerStart={} cam=[{}] save1={} save2={}".format(
            destroyed, failed, v["leftover_visible_proto"], v["vmf"], v["floor"],
            v["playerstart"] or ps, cam, save_results, save_results2))
    log("NOTE: under Critical memory UE may fail to flush ExternalActors — "
        "user should File→Save All after this fix.")
    log("=== END ===")


if __name__ == "__main__":
    main()
else:
    main()
