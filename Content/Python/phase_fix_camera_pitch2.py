# -*- coding: utf-8 -*-
"""Diagnose Rotator ctor + force SpringArm pitch via field assign."""
import unreal

def log(m):
    unreal.log("[CAMFIX2] " + str(m))

# Rotator constructor order test
r1 = unreal.Rotator(-55.0, 0.0, 0.0)
log("Rotator(-55,0,0) -> p={} y={} r={}".format(r1.pitch, r1.yaw, r1.roll))
r2 = unreal.Rotator(0.0, 0.0, -55.0)
log("Rotator(0,0,-55) -> p={} y={} r={}".format(r2.pitch, r2.yaw, r2.roll))
r3 = unreal.Rotator()
r3.pitch = -55.0
r3.yaw = 0.0
r3.roll = 0.0
log("field assign pitch=-55 -> p={} y={} r={}".format(r3.pitch, r3.yaw, r3.roll))

bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(bp_path)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)

for h in handles:
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj or "SpringArm" not in obj.get_class().get_name():
        continue
    # Try field-assigned rotator
    target = unreal.Rotator()
    target.pitch = -55.0
    target.yaw = 0.0
    target.roll = 0.0
    obj.set_editor_property("relative_rotation", target)
    now = obj.get_editor_property("relative_rotation")
    log("after field-set template p={} y={} r={}".format(now.pitch, now.yaw, now.roll))

    # Try unreal.Rotator.make or from_quaternion
    try:
        q = unreal.MathLibrary.make_rotator(-55.0, 0.0, 0.0)  # may be pitch yaw roll
        log("make_rotator(-55,0,0) p={} y={} r={}".format(q.pitch, q.yaw, q.roll))
        obj.set_editor_property("relative_rotation", q)
        now2 = obj.get_editor_property("relative_rotation")
        log("after make_rotator template p={} y={} r={}".format(now2.pitch, now2.yaw, now2.roll))
    except Exception as e:
        log("make_rotator " + str(e))

    # Try setting pitch property alone if exists
    try:
        # RelativeRotation is a struct; set via editor
        pass
    except Exception:
        pass

try:
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(bp_path)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cls = unreal.EditorAssetLibrary.load_blueprint_class(bp_path)
actor = eas.spawn_actor_from_class(cls, unreal.Vector(-9100, -9100, 200), unreal.Rotator(0,0,0))
for c in actor.get_components_by_class(unreal.SceneComponent):
    if "SpringArm" in c.get_class().get_name():
        rr = c.get_editor_property("relative_rotation")
        log("LIVE SpringArm p={} y={} r={}".format(rr.pitch, rr.yaw, rr.roll))
        # Try RUNTIME fix on a note - also try set_relative_rotation
        try:
            fix = unreal.Rotator()
            fix.pitch = -55.0
            fix.yaw = 0.0
            fix.roll = 0.0
            c.set_editor_property("relative_rotation", fix)
            rr2 = c.get_editor_property("relative_rotation")
            log("LIVE after set p={} y={} r={}".format(rr2.pitch, rr2.yaw, rr2.roll))
        except Exception as e:
            log("live set " + str(e))
        # world rotation of camera
        try:
            cam = None
            for c2 in actor.get_components_by_class(unreal.CameraComponent):
                if "Proxy" not in c2.get_class().get_name():
                    cam = c2
                    break
            if cam:
                # get world rotation via editor prop
                wr = cam.get_editor_property("relative_rotation")
                log("cam rel p={} y={} r={}".format(wr.pitch, wr.yaw, wr.roll))
        except Exception as e:
            log("camwr " + str(e))
eas.destroy_actor(actor)

# Also check: does MathLibrary.rotator_from_axis_and_angle help?
# Inspect original template defaults from parent CDO of engine TopDown if any
