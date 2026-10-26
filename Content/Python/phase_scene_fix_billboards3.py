# -*- coding: utf-8 -*-
"""Re-orient standing props with correct rotator (field-assign).
UE5.8 Python: Rotator(a,b,c) == (roll, pitch, yaw) — avoid ctor.
Desired billboard: pitch=0, yaw=-90, roll=90 (plane YZ, normal -X, V up).
"""
import unreal

SCENE_PREFIX = "Scene_"
CELL = 100.0
FLAT_SUFFIXES = {
    "Water_Left", "Water_Bottom", "Pond_NE",
    "Path_V", "Path_H", "Tilled", "Terrace",
    "Bridge", "Stairs", "Cliff_S",
}

def log(m):
    unreal.log("[BILL3] " + str(m))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def make_billboard_rot():
    r = unreal.Rotator()
    r.pitch = 0.0
    r.yaw = -90.0
    r.roll = 90.0
    return r

def is_flat(lab):
    rest = lab[len(SCENE_PREFIX):]
    if rest in FLAT_SUFFIXES:
        return True
    if rest.startswith("Water_") or rest.startswith("Path_") or rest.startswith("Pond_"):
        return True
    return False

stood = 0
for a in eas().get_all_level_actors():
    lab = a.get_actor_label()
    if not lab.startswith(SCENE_PREFIX):
        continue
    if is_flat(lab):
        a.set_actor_rotation(unreal.Rotator(), False)  # zero
        continue
    sc = a.get_actor_scale3d()
    loc = a.get_actor_location()
    height = abs(sc.y) * CELL
    if height < 50:
        height = CELL
    new_z = max(height * 0.5, 40.0)
    a.set_actor_rotation(make_billboard_rot(), False)
    a.set_actor_location(unreal.Vector(loc.x, loc.y, new_z), False, True)
    stood += 1
    rr = a.get_actor_rotation()
    log("STAND {} p={} y={} r={} z={}".format(
        lab, round(rr.pitch,1), round(rr.yaw,1), round(rr.roll,1), round(new_z,1)))

# Ensure camera still pitch=-55 via field assign
bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(bp_path)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
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
        now = obj.get_editor_property("relative_rotation")
        log("SpringArm template p={} y={} r={}".format(now.pitch, now.yaw, now.roll))
    if obj.get_class().get_name() == "CameraComponent":
        try:
            obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            obj.set_editor_property("ortho_width", 1600.0)
        except Exception:
            pass

try:
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(bp_path)

# Live cam check
cls = unreal.EditorAssetLibrary.load_blueprint_class(bp_path)
actor = eas().spawn_actor_from_class(cls, unreal.Vector(-9200, -9200, 200), unreal.Rotator())
for c in actor.get_components_by_class(unreal.SceneComponent):
    if "SpringArm" in c.get_class().get_name():
        rr = c.get_editor_property("relative_rotation")
        log("LIVE SpringArm p={} y={} r={}".format(rr.pitch, rr.yaw, rr.roll))
eas().destroy_actor(actor)

# Verify samples
for lab in ("Scene_House", "Scene_Tree_NE", "Scene_Lamp", "Scene_Fence_N",
            "Scene_Fence_W", "Scene_Path_V", "Scene_Water_Left", "FarmGround"):
    for a in eas().get_all_level_actors():
        if a.get_actor_label() != lab:
            continue
        rr = a.get_actor_rotation()
        loc = a.get_actor_location()
        sc = a.get_actor_scale3d()
        log("VERIFY {} rot=({},{},{}) z={} sc=({},{})".format(
            lab, round(rr.pitch,1), round(rr.yaw,1), round(rr.roll,1),
            round(loc.z,1), round(sc.x,2), round(sc.y,2)))

try:
    ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("save level " + str(ok))
except Exception as e:
    log("save " + str(e))

log("stood_count={}".format(stood))
log("DONE — Play Lvl_TopDown")
