# -*- coding: utf-8 -*-
"""Step B2: fix MoonLight cool color via LinearColor (avoid BGRA swap)."""
import unreal

def log(m):
    unreal.log("[SMB2] " + str(m))
    print("[SMB2] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
moon = None
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "DirectionalLight" and a.get_actor_label() == "MoonLight":
        moon = a
        break
if not moon:
    log("NO moon")
else:
    for c in moon.get_components_by_class(unreal.DirectionalLightComponent):
        # Try LinearColor first (float RGB)
        try:
            lc = unreal.LinearColor(0.55, 0.65, 0.95, 1.0)
            c.set_light_color(lc)
            log("set_light_color LinearColor ok")
        except Exception as e:
            log("set_light_color fail " + str(e))
            # Color ctor appears BGRA in this build: Color(B,G,R,A)
            cool = unreal.Color(242, 166, 140, 255)  # B=242 G=166 R=140 -> RGB(140,166,242)
            c.set_editor_property("light_color", cool)
            log("fallback Color BGRA")
        col = c.get_editor_property("light_color")
        log("moon color now r={} g={} b={} inten={}".format(col.r, col.g, col.b, c.intensity))
    ok = unreal.EditorLevelLibrary.save_current_level()
    log("saved={}".format(ok))
