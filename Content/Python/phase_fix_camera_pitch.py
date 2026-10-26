# -*- coding: utf-8 -*-
"""Fix SpringArm: restore Pitch=-55 (not Roll)."""
import unreal

def log(m):
    unreal.log("[CAMFIX] " + str(m))

bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(bp_path)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)

for h in handles:
    try:
        data = lib.get_data(h)
        name = str(lib.get_variable_name(data))
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj:
            continue
        cname = obj.get_class().get_name()
        log("sub {} class={}".format(name, cname))
        if "SpringArm" in cname or name == "SpringArm":
            old = obj.get_editor_property("relative_rotation")
            log("BEFORE template rot p={} y={} r={}".format(old.pitch, old.yaw, old.roll))
            # Force pitch=-55, yaw=0, roll=0 (TopDown 2.5D)
            target = unreal.Rotator(-55.0, 0.0, 0.0)
            obj.set_editor_property("relative_rotation", target)
            # also try component methods
            try:
                obj.set_editor_property("RelativeRotation", target)
            except Exception:
                pass
            # verify readback
            now = obj.get_editor_property("relative_rotation")
            log("AFTER template rot p={} y={} r={}".format(now.pitch, now.yaw, now.roll))
            try:
                obj.set_editor_property("target_arm_length", 5000.0)
                obj.set_editor_property("b_do_collision_test", False)
            except Exception as e:
                log("arm props " + str(e))
        if cname == "CameraComponent" or name == "Camera":
            try:
                obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", 1600.0)
                cr = obj.get_editor_property("relative_rotation")
                log("Camera rot p={} y={} r={} ortho=1600".format(cr.pitch, cr.yaw, cr.roll))
            except Exception as e:
                log("cam " + str(e))
    except Exception as e:
        log("iter " + str(e))

# Compile + save
try:
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    log("compiled")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(bp_path)
log("saved bp")

# Live verify (need fresh class)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cls = unreal.EditorAssetLibrary.load_blueprint_class(bp_path)
actor = eas.spawn_actor_from_class(cls, unreal.Vector(-9000, -9000, 200), unreal.Rotator(0,0,0))
for c in actor.get_components_by_class(unreal.SceneComponent):
    if "SpringArm" in c.get_class().get_name() or c.get_name() == "Camera":
        rr = c.get_editor_property("relative_rotation")
        log("LIVE {} p={} y={} r={}".format(c.get_name(), rr.pitch, rr.yaw, rr.roll))
        for prop in ("target_arm_length", "ortho_width", "projection_mode"):
            try:
                log("  {}={}".format(prop, c.get_editor_property(prop)))
            except Exception:
                pass
eas.destroy_actor(actor)
