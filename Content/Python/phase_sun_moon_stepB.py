# -*- coding: utf-8 -*-
"""Step B: configure existing MoonLight actor only (no BP graph edits)."""
import unreal

OUT_LOG = []

def log(m):
    s = str(m)
    OUT_LOG.append(s)
    unreal.log("[SMB] " + s)
    print("[SMB] " + s)

def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    sun = moon = sky_atm = sky_light = None
    for a in eas.get_all_level_actors():
        cn = a.get_class().get_name()
        label = a.get_actor_label()
        if cn == "DirectionalLight" and label == "SunLight":
            sun = a
        elif cn == "DirectionalLight" and label == "MoonLight":
            moon = a
        elif cn == "SkyAtmosphere":
            sky_atm = a
        elif cn == "SkyLight":
            sky_light = a

    log("found sun={} moon={} skyAtm={} skyLight={}".format(
        bool(sun), bool(moon), bool(sky_atm), bool(sky_light)))

    if not moon:
        log("NO MoonLight — spawning")
        moon = eas.spawn_actor_from_class(
            unreal.DirectionalLight, unreal.Vector(0, 0, 400), unreal.Rotator(0, 0, 0))
        moon.set_actor_label("MoonLight")
        try:
            moon.tags = ["FarmMoon"]
        except Exception:
            pass

    # Ensure tags
    for actor, tag in ((sun, "FarmSun"), (moon, "FarmMoon")):
        if not actor:
            continue
        try:
            tags = list(actor.tags) if actor.tags else []
        except Exception:
            tags = []
        if tag not in [str(t) for t in tags]:
            tags.append(tag)
            try:
                actor.tags = tags
                log("added tag {} to {}".format(tag, actor.get_actor_label()))
            except Exception as e:
                log("tag fail {}: {}".format(tag, e))
        else:
            log("tag ok {} on {}".format(tag, actor.get_actor_label()))

    # Configure moon DL component
    for c in moon.get_components_by_class(unreal.DirectionalLightComponent):
        c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        c.set_editor_property("intensity", 2.0)
        # Cool blue Color 0-255: R140 G166 B242 ≈ Linear(0.55,0.65,0.95)
        cool = unreal.Color(140, 166, 242, 255)
        c.set_editor_property("light_color", cool)
        c.set_editor_property("atmosphere_sun_light", True)
        c.set_editor_property("atmosphere_sun_light_index", 1)
        try:
            c.set_editor_property("cast_shadows", True)
        except Exception:
            pass
        log("moon now inten={} color=({},{},{}) atm={} idx={} mob={}".format(
            c.get_editor_property("intensity"),
            c.light_color.r, c.light_color.g, c.light_color.b,
            c.atmosphere_sun_light, c.atmosphere_sun_light_index, c.mobility))

    if sun:
        for c in sun.get_components_by_class(unreal.DirectionalLightComponent):
            c.set_editor_property("atmosphere_sun_light", True)
            c.set_editor_property("atmosphere_sun_light_index", 0)
            c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
            log("sun idx={} atm={} mob={}".format(
                c.atmosphere_sun_light_index, c.atmosphere_sun_light, c.mobility))

    if sky_light:
        for c in sky_light.get_components_by_class(unreal.SkyLightComponent):
            try:
                c.set_editor_property("real_time_capture", True)
                log("sky RTC=True inten={}".format(c.intensity))
            except Exception as e:
                log("sky RTC " + str(e))

    if not sky_atm:
        log("spawning SkyAtmosphere")
        eas.spawn_actor_from_class(
            unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))

    # Save current level
    try:
        ok = unreal.EditorLevelLibrary.save_current_level()
        log("save_current_level={}".format(ok))
    except Exception as e:
        try:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
            log("save via LevelEditorSubsystem ok")
        except Exception as e2:
            log("save fail {} / {}".format(e, e2))

    log("Step B DONE")

if __name__ == "__main__":
    main()
