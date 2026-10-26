# -*- coding: utf-8 -*-
"""Post-fix: fence scales + verify camera live + confirm standing."""
import unreal

def log(m):
    unreal.log("[BILL2] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def find(lab):
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == lab:
            return a
    return None

# Fix fences: long along ground axis, short height when standing
# Fence_N was (9,1) -> width 9 height 1 OK for facing camera
# Fence_W/E were (1,6) -> became thin tall; should be (6,1) width along Y, short height
for lab in ("Scene_Fence_W", "Scene_Fence_E"):
    a = find(lab)
    if not a:
        continue
    loc = a.get_actor_location()
    a.set_actor_scale3d(unreal.Vector(6.0, 1.2, 1.0))
    new_z = 1.2 * 100 * 0.5
    a.set_actor_location(unreal.Vector(loc.x, loc.y, new_z), False, True)
    a.set_actor_rotation(unreal.Rotator(0.0, -90.0, 90.0), False)
    log("fence fix {} scale=(6,1.2) z={}".format(lab, new_z))

# Fence_N: runs along X in layout — with camera-facing billboard it's OK as card;
# optionally orient along X: Roll=90 only so plane in XZ facing ±Y
# Keep camera-facing for consistency (Stardew-like cards)

# Verify camera after BP edit
bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
cls = unreal.EditorAssetLibrary.load_blueprint_class(bp_path)
actor = eas.spawn_actor_from_class(cls, unreal.Vector(-8000, -8000, 200), unreal.Rotator(0,0,0))
for c in actor.get_components_by_class(unreal.SceneComponent):
    cn = c.get_name()
    cc = c.get_class().get_name()
    if "Spring" in cc or cn == "Camera":
        rr = c.get_editor_property("relative_rotation")
        log("LIVE {} relRot=({},{},{})".format(cn, rr.pitch, rr.yaw, rr.roll))
        for prop in ("target_arm_length", "projection_mode", "ortho_width"):
            try:
                log("  {}={}".format(prop, c.get_editor_property(prop)))
            except Exception:
                pass
eas.destroy_actor(actor)

# Sample standing
for lab in ("Scene_House", "Scene_Tree_NE", "Scene_Lamp", "Scene_Fence_W",
            "Scene_Path_V", "Scene_Tilled", "FarmGround"):
    a = find(lab)
    if not a:
        log("MISSING " + lab)
        continue
    r = a.get_actor_rotation()
    loc = a.get_actor_location()
    sc = a.get_actor_scale3d()
    log("{} rot=({},{},{}) loc.z={} scale=({},{},{})".format(
        lab, round(r.pitch,1), round(r.yaw,1), round(r.roll,1),
        round(loc.z,1), round(sc.x,2), round(sc.y,2), round(sc.z,2)))

# Count visible proto
vis_proto = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("SM_") or lab == "Floor":
        try:
            hidden = a.is_temporarily_hidden_in_editor()
        except Exception:
            try:
                hidden = a.is_hidden_ed()
            except Exception:
                hidden = False
        sc = a.get_actor_scale3d()
        tiny = abs(sc.x) < 0.01
        if not (hidden or tiny):
            vis_proto += 1
            log("STILL VISIBLE PROTO? " + lab)
log("vis_proto_suspect=" + str(vis_proto))

# save
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("saved")
except Exception as e:
    log("save " + str(e))
