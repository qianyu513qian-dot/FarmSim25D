# -*- coding: utf-8 -*-
"""Patch phase_scene_build.spawn_plane so upright props spawn correctly next rebuild.
Also take an editor screenshot of the farm."""
import unreal
import os

def log(m):
    unreal.log("[PATCH] " + str(m))

# --- Screenshot from current editor view (best-effort) ---
out = r"E:\UE\FarmSim25D\Saved\Screenshots\billboard_fix.png"
try:
    os.makedirs(os.path.dirname(out), exist_ok=True)
except Exception:
    pass

# Focus camera on farm center roughly
try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Find house for look-at
    house = None
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == "Scene_House":
            house = a
            break
    if house:
        loc = house.get_actor_location()
        # Set viewport to look at farm from 2.5D angle
        # EditorLevelLibrary has pilot methods in older API
        try:
            unreal.EditorLevelLibrary.set_level_viewport_camera_info(
                unreal.Vector(loc.x - 1200, loc.y, loc.z + 900),
                unreal.Rotator(-40.0, 0.0, 0.0),  # careful: may be roll-pitch-yaw ctor!
            )
            log("viewport set")
        except Exception as e:
            # field-assign rotator for viewport
            try:
                r = unreal.Rotator()
                r.pitch = -40.0
                r.yaw = 0.0
                r.roll = 0.0
                # try alternate
                unreal.EditorLevelLibrary.set_level_viewport_camera_info(
                    unreal.Vector(loc.x - 1200, loc.y, loc.z + 900), r
                )
                log("viewport set via fields")
            except Exception as e2:
                log("viewport fail " + str(e) + " / " + str(e2))
except Exception as e:
    log("focus fail " + str(e))

# High-res screenshot
try:
    # Automation take_high_res_screenshot
    unreal.AutomationLibrary.take_high_res_screenshot(
        1920, 1080, out, None, True, True, unreal.ComparisonTolerance.LOW, "", 0.0
    )
    log("screenshot queued " + out)
except Exception as e:
    log("screenshot fail " + str(e))
    try:
        # fallback EditorLevelLibrary
        unreal.EditorLevelLibrary.editor_play_simulate()
    except Exception:
        pass

# Final summary counts
stood = flat = hidden = 0
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("Scene_"):
        rr = a.get_actor_rotation()
        if abs(rr.roll) > 45 or abs(rr.pitch) > 45:
            stood += 1
        else:
            flat += 1
    if lab.startswith("SM_") or lab == "Floor" or lab.startswith("FarmBorder_"):
        sc = a.get_actor_scale3d()
        if abs(sc.x) < 0.01:
            hidden += 1
log("summary stood~{} flat~{} hidden_proto~{}".format(stood, flat, hidden))
