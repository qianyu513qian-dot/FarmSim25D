# -*- coding: utf-8 -*-
"""Probe level lights + BP_GridManager day/night vars/BeginPlay for dual sun/moon."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[PROBE_SM] " + str(m))
    print("[PROBE_SM] " + str(m))


def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()


def main():
    log("START")
    bp = unreal.load_asset(MGR)
    names = [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]
    want = ("SunActor", "MoonActor", "SkyLightActor", "TimeOfDay", "CurrentDay", "DayLengthSeconds")
    log("vars=" + str([v for v in want if v in names]))
    log("MoonActor present=" + str("MoonActor" in names))

    # Level actors
    try:
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    except Exception:
        actors = unreal.EditorLevelLibrary.get_all_level_actors()

    sky_atmo = 0
    for a in actors:
        cn = a.get_class().get_name()
        an = a.get_actor_label() if hasattr(a, "get_actor_label") else a.get_name()
        if cn in ("DirectionalLight", "SkyLight", "SkyAtmosphere", "ExponentialHeightFog", "VolumetricCloud"):
            log("ACTOR class={} label={} name={}".format(cn, an, a.get_name()))
            try:
                tags = list(a.tags) if hasattr(a, "tags") else []
                log("  tags={}".format([str(t) for t in tags]))
            except Exception as e:
                log("  tags err " + str(e))
            if cn == "SkyAtmosphere":
                sky_atmo += 1
            try:
                if cn == "DirectionalLight":
                    comps = a.get_components_by_class(unreal.DirectionalLightComponent)
                    for c in comps:
                        log("  inten={} mob={} color={} atmSun={} idx={} castShadow={}".format(
                            c.get_editor_property("intensity"),
                            c.get_editor_property("mobility"),
                            c.get_editor_property("light_color"),
                            c.get_editor_property("atmosphere_sun_light"),
                            c.get_editor_property("atmosphere_sun_light_index"),
                            c.get_editor_property("cast_shadows"),
                        ))
                elif cn == "SkyLight":
                    comps = a.get_components_by_class(unreal.SkyLightComponent)
                    for c in comps:
                        props = {}
                        for p in ("intensity", "mobility", "real_time_capture", "light_color"):
                            try:
                                props[p] = c.get_editor_property(p)
                            except Exception:
                                props[p] = "?"
                        log("  sky props={}".format(props))
            except Exception as e:
                log("  comp err " + str(e))
    log("SkyAtmosphere count={}".format(sky_atmo))

    # BeginPlay Set SunActor chain
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    for n in ge.list_all_nodes():
        t = title(n)
        if "SunActor" in t or "SkyLightActor" in t or "MoonActor" in t:
            log("EG node: " + t)
        if "Get All Actors Of Class" in t or "GetAllActorsOfClass" in t.replace(" ", ""):
            pins = []
            for p in bel.list_all_pins(n):
                try:
                    v = p.get_pin_value()
                except Exception:
                    v = "?"
                pins.append("{}={!r}".format(p.get_pin_name(), v))
            log("GetAllActors: {} | {}".format(t, " ; ".join(pins[:8])))

    # ApplyDayNightVisuals summary
    ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    nodes = list(ge2.list_all_nodes())
    log("ApplyDayNightVisuals nodes={}".format(len(nodes)))
    set_i_count = 0
    for n in nodes:
        t = title(n)
        if "SetIntensity" in t or "Set Intensity" in t:
            set_i_count += 1
            log("  " + t)
        if "SetActorRotation" in t or "Set Actor Rotation" in t:
            log("  " + t)
        if "360" in t or "Map Range" in t or "MapRange" in t:
            for p in bel.list_all_pins(n):
                try:
                    v = p.get_pin_value()
                except Exception:
                    v = "?"
                if str(v) not in ("", "0", "0.0", "None", "None?"):
                    log("  {} pin {}={!r}".format(t, p.get_pin_name(), v))
    log("SetIntensity count={}".format(set_i_count))
    log("DONE")


if __name__ == "__main__":
    main()
