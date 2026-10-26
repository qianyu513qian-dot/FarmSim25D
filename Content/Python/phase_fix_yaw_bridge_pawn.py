# -*- coding: utf-8 -*-
"""Fix: SpringArm yaw=-90 (water L / trees R / house top), delete bad bridge rails/posts,
fix PlayerStart rot, save level. NO whole-scene rotate."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
CAM_PITCH = -40.0
CAM_YAW = -90.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0

def log(m):
    unreal.log("[FIX_YAW] " + str(m))
    print("[FIX_YAW] " + str(m))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# --- 1) Camera yaw flip ---
bp = unreal.EditorAssetLibrary.load_asset(CHAR)
if not bp:
    raise SystemExit("NO BP")
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
    if "SpringArm" in cname or name == "SpringArm":
        for prop, val in (
            ("do_collision_test", False),
            ("use_pawn_control_rotation", False),
            ("inherit_pitch", False),
            ("inherit_yaw", False),
            ("inherit_roll", False),
        ):
            try:
                obj.set_editor_property(prop, val)
            except Exception:
                pass
        try:
            obj.set_editor_property("target_arm_length", CAM_ARM)
        except Exception:
            pass
        rot = unreal.Rotator()
        rot.pitch = CAM_PITCH
        rot.yaw = CAM_YAW
        rot.roll = 0.0
        obj.set_editor_property("relative_rotation", rot)
        now = obj.get_editor_property("relative_rotation")
        log("SpringArm -> p={:.1f} y={:.1f} r={:.1f} arm={}".format(
            now.pitch, now.yaw, now.roll, obj.get_editor_property("target_arm_length")))
    if cname == "CameraComponent" or name == "Camera":
        try:
            obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            obj.set_editor_property("ortho_width", CAM_ORTHO)
            zero = unreal.Rotator()
            zero.pitch = 0.0
            zero.yaw = 0.0
            zero.roll = 0.0
            obj.set_editor_property("relative_rotation", zero)
            log("Camera ortho={}".format(CAM_ORTHO))
        except Exception as e:
            log("cam err " + str(e))

unreal.EditorAssetLibrary.save_asset(CHAR)
try:
    bel.compile_blueprint(bp)
    log("compiled BP")
except Exception as e:
    log("compile: " + str(e))

# --- 2) Bridges: delete FenceLow rails + FenceEnd posts (vertical sticks) ---
killed_rail = 0
killed_post = 0
deck_fixed = 0
for a in list(eas().get_all_level_actors()):
    lab = a.get_actor_label() or ""
    if not lab.startswith("VMF_Bridge"):
        continue
    if "Rail" in lab:
        try:
            eas().destroy_actor(a)
            killed_rail += 1
        except Exception as e:
            log("kill rail fail {}: {}".format(lab, e))
        continue
    if "Post" in lab:
        try:
            eas().destroy_actor(a)
            killed_post += 1
        except Exception as e:
            log("kill post fail {}: {}".format(lab, e))
        continue
    # Deck: PathStraight E-W should be yaw=0; ensure flat (pitch/roll 0) and z=5
    try:
        loc = a.get_actor_location()
        rot = unreal.Rotator()
        rot.pitch = 0.0
        rot.yaw = 0.0
        rot.roll = 0.0
        a.set_actor_rotation(rot, False)
        a.set_actor_location(unreal.Vector(loc.x, loc.y, 5.0), False, False)
        deck_fixed += 1
    except Exception as e:
        log("deck fix fail {}: {}".format(lab, e))
log("bridges killed_rail={} killed_post={} deck_fixed={}".format(killed_rail, killed_post, deck_fixed))

# --- 3) PlayerStart: fix crazy pitch=90 ---
for a in eas().get_all_level_actors():
    if a.get_class().get_name() != "PlayerStart":
        continue
    # Face along +Y (toward house / screen-up with yaw=-90 camera looking north)
    rot = unreal.Rotator()
    rot.pitch = 0.0
    rot.yaw = 0.0
    rot.roll = 0.0
    a.set_actor_rotation(rot, False)
    loc = a.get_actor_location()
    # keep XY, ensure feet above ground
    if loc.z < 50:
        a.set_actor_location(unreal.Vector(loc.x, loc.y, 100.0), False, False)
    log("PlayerStart rot fixed -> {}".format(a.get_actor_rotation()))

# --- 4) Confirm no duplicate placed pawn ---
pawnish = []
for a in eas().get_all_level_actors():
    lab = a.get_actor_label() or ""
    cls = a.get_class().get_name()
    if "Character" in cls or ("Pawn" in cls and "PlayerStart" not in cls):
        pawnish.append((lab, cls))
log("placed pawn-like actors: {}".format(pawnish if pawnish else "NONE (only GameMode spawn)"))
# Note scarecrow
for a in eas().get_all_level_actors():
    lab = a.get_actor_label() or ""
    if "Scarecrow" in lab:
        loc = a.get_actor_location()
        log("NOTE straw-hat figure is {} @ ({:.0f},{:.0f},{:.0f}) not a second pawn".format(
            lab, loc.x, loc.y, loc.z))

# --- 5) Save level ---
try:
    unreal.EditorLevelLibrary.save_current_level()
    log("level saved")
except Exception as e:
    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        els.save_current_level()
        log("level saved via LevelEditorSubsystem")
    except Exception as e2:
        log("save fail {} / {}".format(e, e2))

# Verify final springarm
bp2 = unreal.EditorAssetLibrary.load_asset(CHAR)
handles = sds.k2_gather_subobject_data_for_blueprint(bp2)
for h in handles:
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp2)
    if obj and ("SpringArm" in obj.get_class().get_name() or name == "SpringArm"):
        r = obj.get_editor_property("relative_rotation")
        log("VERIFY SpringArm p={:.1f} y={:.1f} r={:.1f}".format(r.pitch, r.yaw, r.roll))

log("DONE yaw={} pitch={} ortho={}".format(CAM_YAW, CAM_PITCH, CAM_ORTHO))
