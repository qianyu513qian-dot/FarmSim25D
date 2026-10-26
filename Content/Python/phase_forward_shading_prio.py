# -*- coding: utf-8 -*-
"""Set ForwardShadingPriority on Sun/Moon to silence competing directional lights warning.
Sun=1 (preferred), Moon=0. No BP graph edits."""
import unreal

def log(m):
    unreal.log("[FWD_PRIO] " + str(m))
    print("[FWD_PRIO] " + str(m))

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

sun_n = moon_n = 0
for a in actors:
    if a.get_class().get_name() != "DirectionalLight":
        continue
    label = ""
    try:
        label = str(a.get_actor_label())
    except Exception:
        pass
    tags = [str(t) for t in (a.tags or [])]
    name = a.get_name()
    is_moon = ("Moon" in label) or ("FarmMoon" in tags) or ("Moon" in name)
    is_sun = ("Sun" in label) or ("FarmSun" in tags) or (not is_moon and "DirectionalLight_0" in name)
    # Prefer tag-based
    if "FarmMoon" in tags or label == "MoonLight":
        is_moon, is_sun = True, False
    if "FarmSun" in tags or label in ("SunLight", "DirectionalLight"):
        if not is_moon:
            is_sun = True

    for c in a.get_components_by_class(unreal.DirectionalLightComponent):
        prio = 0 if is_moon else 1
        # If ambiguous second light without tags, use atmosphere index
        try:
            idx = c.get_editor_property("atmosphere_sun_light_index")
            if idx == 1:
                prio = 0
                is_moon = True
            elif idx == 0:
                prio = 1
                is_sun = True
        except Exception:
            pass
        try:
            c.set_editor_property("forward_shading_priority", prio)
            # Also try PascalCase if needed
        except Exception:
            try:
                c.set_editor_property("ForwardShadingPriority", prio)
            except Exception as e:
                log("set fail {} {}".format(label or name, e))
                continue
        # verify
        try:
            got = c.get_editor_property("forward_shading_priority")
        except Exception:
            got = "?"
        log("set {} tags={} atm? prio={} got={}".format(label or name, tags, prio, got))
        if is_moon:
            moon_n += 1
        else:
            sun_n += 1

log("sun_touched={} moon_touched={}".format(sun_n, moon_n))

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        log("level saved2")
    except Exception as e:
        log("save fail " + str(e))

log("DONE")
