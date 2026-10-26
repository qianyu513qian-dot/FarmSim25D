# -*- coding: utf-8 -*-
"""Probe ApplyDayNightVisuals pins/values and SkyLight SetIntensity APIs."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[PROBE_DN] " + str(m)); print("[PROBE_DN] " + str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

log("=== ApplyDayNightVisuals nodes ===")
for n in ge.list_all_nodes():
    pins = []
    for p in bel.list_all_pins(n):
        try:
            v = p.get_pin_value()
        except Exception:
            v = "?"
        pins.append("{}={}({})".format(p.get_pin_name(), v, p.get_pin_direction()))
    log("{} | {}".format(title(n), " ; ".join(pins[:12])))

# Try SetIntensity paths for sky
ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
for path in [
    "/Script/Engine.SkyLightComponent:SetIntensity",
    "/Script/Engine.LightComponentBase:SetIntensity",
    "/Script/Engine.LightComponent:SetIntensity",
    "/Script/Engine.SkyLightComponent:SetLightColor",
]:
    try:
        n = ge2.add_call_function_node(path)
        if n:
            log("OK {} pins={}".format(path, [str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
            ge2.remove_nodes([n])
        else:
            log("NONE " + path)
    except Exception as e:
        log("ERR {} {}".format(path, e))

# Level light state
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
    cn = a.get_class().get_name()
    if cn in ("DirectionalLight", "SkyLight"):
        try:
            comps = a.get_components_by_class(unreal.LightComponentBase)
            for c in comps:
                log("LEVEL {} inten={} mob={} color={}".format(
                    a.get_name(),
                    c.get_editor_property("intensity"),
                    c.get_editor_property("mobility"),
                    c.get_editor_property("light_color") if hasattr(c, "get_editor_property") else "?"))
        except Exception as e:
            log("LEVEL {} err {}".format(a.get_name(), e))

log("DONE")
