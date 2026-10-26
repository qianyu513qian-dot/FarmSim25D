# -*- coding: utf-8 -*-
import unreal

def log(m):
    unreal.log("[CAMP4] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cls = unreal.EditorAssetLibrary.load_blueprint_class("/Game/TopDown/Blueprints/BP_TopDownCharacter")
actor = eas.spawn_actor_from_class(cls, unreal.Vector(-5000, -5000, 200), unreal.Rotator(0,0,0))
for c in actor.get_components_by_class(unreal.SceneComponent):
    cn = c.get_name()
    cc = c.get_class().get_name()
    if "Spring" in cc or ("Camera" in cc and "Proxy" not in cc and "Frustum" not in cc) or cn in ("SpringArm", "Camera"):
        rr = c.get_editor_property("relative_rotation")
        rl = c.get_editor_property("relative_location")
        log("{} ({}) relRot=({},{},{}) relLoc=({},{},{})".format(
            cn, cc, rr.pitch, rr.yaw, rr.roll, rl.x, rl.y, rl.z))
        for prop in ["target_arm_length", "b_use_pawn_control_rotation", "b_inherit_pitch",
                     "b_inherit_yaw", "b_inherit_roll", "b_do_collision_test",
                     "projection_mode", "ortho_width", "field_of_view"]:
            try:
                log("  {}={}".format(prop, c.get_editor_property(prop)))
            except Exception:
                pass
eas.destroy_actor(actor)

bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)
log("handles=" + str(len(handles)))
for h in handles:
    try:
        name = lib.get_variable_name(h)
        obj = lib.get_object_for_blueprint(h, bp)
        log("SUB name={} obj={}".format(name, obj.get_class().get_name() if obj else None))
        if obj and ("Spring" in obj.get_class().get_name() or obj.get_class().get_name() == "CameraComponent"):
            rr = obj.get_editor_property("relative_rotation")
            log("  TEMPLATE rot=({},{},{})".format(rr.pitch, rr.yaw, rr.roll))
            for prop in ["target_arm_length", "projection_mode", "ortho_width"]:
                try:
                    log("  {}={}".format(prop, obj.get_editor_property(prop)))
                except Exception:
                    pass
    except Exception as e:
        log("sub fail " + str(e))
