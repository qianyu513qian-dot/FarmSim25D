# -*- coding: utf-8 -*-
"""Force isometric SpringArm on BP_TopDownCharacter (pitch -40, yaw -45, ortho 2800)."""
import unreal

def log(m):
    unreal.log("[VMF_CAM] " + str(m))

CAM_PITCH = -40.0
CAM_YAW = 135.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0
bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

bp = unreal.EditorAssetLibrary.load_asset(bp_path)
if not bp:
    log("NO BP")
    raise SystemExit(1)

sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)

for h in handles:
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cname = obj.get_class().get_name()
    log("sub name={} class={}".format(name, cname))

    if "SpringArm" in cname or name == "SpringArm":
        # arm length
        try:
            obj.set_editor_property("target_arm_length", CAM_ARM)
            log("target_arm_length={}".format(CAM_ARM))
        except Exception as e:
            log("arm len fail " + str(e))

        # collision test 鈥?try several names
        for prop, val in (
            ("do_collision_test", False),
            ("b_do_collision_test", False),
            ("DoCollisionTest", False),
        ):
            try:
                obj.set_editor_property(prop, val)
                log("set {}={}".format(prop, val))
                break
            except Exception as e:
                log("skip {}: {}".format(prop, e))

        for prop, val in (
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
                log("set {}={}".format(prop, val))
            except Exception:
                pass

        rot = unreal.Rotator()
        rot.pitch = CAM_PITCH
        rot.yaw = CAM_YAW
        rot.roll = 0.0
        try:
            obj.set_editor_property("relative_rotation", rot)
            now = obj.get_editor_property("relative_rotation")
            log("SpringArm relative_rotation p={} y={} r={}".format(now.pitch, now.yaw, now.roll))
        except Exception as e:
            log("relrot fail " + str(e))
            try:
                mr = unreal.MathLibrary.make_rotator(CAM_PITCH, CAM_YAW, 0.0)
                obj.set_editor_property("relative_rotation", mr)
                now = obj.get_editor_property("relative_rotation")
                log("make_rotator path p={} y={} r={}".format(now.pitch, now.yaw, now.roll))
            except Exception as e2:
                log("make_rotator fail " + str(e2))

    if cname == "CameraComponent" or name == "Camera":
        try:
            obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            obj.set_editor_property("ortho_width", CAM_ORTHO)
            log("Camera ORTHO ortho_width={}".format(CAM_ORTHO))
        except Exception as e:
            log("cam fail " + str(e))
        try:
            zero = unreal.Rotator()
            zero.pitch = 0.0
            zero.yaw = 0.0
            zero.roll = 0.0
            obj.set_editor_property("relative_rotation", zero)
        except Exception:
            pass

try:
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    log("compiled")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(bp_path)
log("saved")

# live verify via spawned actor
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cls = unreal.EditorAssetLibrary.load_blueprint_class(bp_path)
actor = eas.spawn_actor_from_class(cls, unreal.Vector(-9200, -9200, 200), unreal.Rotator())
for c in actor.get_components_by_class(unreal.SceneComponent):
    cn = c.get_class().get_name()
    if "SpringArm" in cn:
        rr = c.get_editor_property("relative_rotation")
        try:
            arm = c.get_editor_property("target_arm_length")
        except Exception:
            arm = "?"
        log("LIVE SpringArm arm={} p={} y={} r={}".format(arm, rr.pitch, rr.yaw, rr.roll))
    if cn == "CameraComponent":
        try:
            ow = c.get_editor_property("ortho_width")
            pm = c.get_editor_property("projection_mode")
            log("LIVE Camera ortho={} proj={}".format(ow, pm))
        except Exception as e:
            log("LIVE cam " + str(e))
eas.destroy_actor(actor)
log("=== DONE CAM ISO ===")

