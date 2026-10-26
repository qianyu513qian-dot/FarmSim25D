# -*- coding: utf-8 -*-
"""Fix flat-painting look: stand Scene_* props, hide prototyping, camera pitch -55.
Re-run: python Content/Python/run_remote.py Content/Python/phase_scene_fix_billboards.py
NOTE: UE5.8 unreal.Rotator(a,b,c) is (roll,pitch,yaw) — always use field assign.
"""
import unreal

SCENE_PREFIX = "Scene_"
CELL = 100.0
FLAT = {
    "Water_Left", "Water_Bottom", "Pond_NE", "Path_V", "Path_H",
    "Tilled", "Terrace", "Bridge", "Stairs", "Cliff_S",
}

def log(m):
    unreal.log("[BILLBOARD] " + str(m))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def billboard_rot():
    r = unreal.Rotator()
    r.pitch = 0.0
    r.yaw = -90.0
    r.roll = 90.0
    return r

def zero_rot():
    return unreal.Rotator()

def is_flat(lab):
    rest = lab[len(SCENE_PREFIX):]
    if rest in FLAT:
        return True
    return rest.startswith("Water_") or rest.startswith("Path_") or rest.startswith("Pond_")

def hide_proto(a):
    lab = a.get_actor_label()
    keep = {
        "FarmGround", "BP_GridManager", "PlayerStart", "DirectionalLight",
        "SkyLight", "SkyAtmosphere", "ExponentialHeightFog", "VolumetricCloud",
        "SM_SkySphere", "NavMeshBoundsVolume", "RecastNavMesh-Default",
        "WorldDataLayers", "WorldPartitionMiniMap0",
    }
    if lab.startswith(SCENE_PREFIX) or lab in keep:
        return False
    if lab.startswith("FarmBorder_"):
        return True
    mesh_name = mesh_path = ""
    try:
        smc = a.static_mesh_component
        if smc and smc.static_mesh:
            mesh_name = smc.static_mesh.get_name()
            mesh_path = smc.static_mesh.get_path_name()
    except Exception:
        pass
    if lab == "Floor" or "Template_Map_Floor" in mesh_name:
        return True
    if lab.startswith("SM_Cube") or lab.startswith("SM_Ramp") or lab.startswith("SM_Cylinder") or lab.startswith("SM_QuarterCylinder"):
        return True
    if "LevelPrototyping" in mesh_path or mesh_name in ("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_QuarterCylinder", "SM_Template_Map_Floor"):
        return True
    return False

def fix_scene():
    stood, flat_n = 0, 0
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if not lab.startswith(SCENE_PREFIX):
            continue
        loc = a.get_actor_location()
        sc = a.get_actor_scale3d()
        if is_flat(lab):
            a.set_actor_rotation(zero_rot(), False)
            flat_n += 1
            continue
        height = max(abs(sc.y) * CELL, CELL)
        new_z = max(height * 0.5, 40.0)
        a.set_actor_rotation(billboard_rot(), False)
        a.set_actor_location(unreal.Vector(loc.x, loc.y, new_z), False, True)
        try:
            a.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            pass
        stood += 1
    return stood, flat_n

def hide_all_proto():
    n = 0
    for a in eas().get_all_level_actors():
        if not hide_proto(a):
            continue
        try:
            a.set_actor_hidden_in_game(True)
            a.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass
        try:
            if a.static_mesh_component:
                a.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            pass
        try:
            a.set_actor_scale3d(unreal.Vector(0.001, 0.001, 0.001))
        except Exception:
            pass
        n += 1
    return n

def fix_camera():
    bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    detail = "no springarm"
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(h)
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj:
            continue
        if "SpringArm" in obj.get_class().get_name():
            r = unreal.Rotator()
            r.pitch = -55.0
            r.yaw = 0.0
            r.roll = 0.0
            obj.set_editor_property("relative_rotation", r)
            try:
                obj.set_editor_property("target_arm_length", 5000.0)
            except Exception:
                pass
            now = obj.get_editor_property("relative_rotation")
            detail = "SpringArm pitch={} yaw={} roll={}".format(now.pitch, now.yaw, now.roll)
        if obj.get_class().get_name() == "CameraComponent":
            try:
                obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", 1600.0)
            except Exception:
                pass
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(bp_path)
    return detail

def main():
    log("=== START ===")
    stood, flat_n = fix_scene()
    hidden = hide_all_proto()
    cam = fix_camera()
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    except Exception:
        pass
    log("stood={} flat={} hidden_proto={}".format(stood, flat_n, hidden))
    log("cam: " + cam)
    log("prop rot = pitch=0 yaw=-90 roll=90; ground stays identity")
    log("=== END — Play Lvl_TopDown ===")

main()