# -*- coding: utf-8 -*-
"""Step A: read-only probe for sun/moon day-night. NO graph edits."""
import unreal
import os

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
OUT = r"E:\UE\FarmSim25D\Content\Python\_probe_sun_moon_stepA.txt"
lines = []

def log(m):
    s = str(m)
    lines.append(s)
    unreal.log("[SMA] " + s)
    print("[SMA] " + s)

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        try:
            return n.get_class().get_name()
        except Exception:
            return "?"

def pin_info(p):
    try:
        name = str(p.get_pin_name())
    except Exception:
        name = "?"
    try:
        direction = str(p.get_pin_direction())
    except Exception:
        direction = "?"
    try:
        val = p.get_pin_value()
    except Exception:
        val = None
    linked = []
    try:
        for lp in p.get_linked_to():
            try:
                linked.append(str(lp.get_pin_name()) + "@" + title(lp.get_owning_node()))
            except Exception:
                linked.append("?")
    except Exception:
        pass
    return name, direction, val, linked

def main():
    log("=== Step A probe START ===")
    # Level actors
    eas = unreal.EditorActorSubsystem()
    actors = eas.get_all_level_actors()
    log("--- Level lights/sky ---")
    for a in actors:
        try:
            cls = a.get_class().get_name()
            label = a.get_actor_label()
            name = a.get_name()
        except Exception:
            continue
        if any(k in cls for k in ("DirectionalLight", "SkyLight", "SkyAtmosphere", "ExponentialHeightFog", "VolumetricCloud")):
            log("ACTOR cls={} label={!r} name={!r}".format(cls, label, name))
            # try light props
            try:
                comps = a.get_components_by_class(unreal.DirectionalLightComponent)
                for c in comps:
                    try:
                        log("  DL intensity={} color={} atmSun={} atmIdx={}".format(
                            c.get_editor_property("intensity"),
                            c.get_editor_property("light_color"),
                            c.get_editor_property("atmosphere_sun_light"),
                            c.get_editor_property("atmosphere_sun_light_index"),
                        ))
                    except Exception as e:
                        log("  DL props err: " + str(e))
            except Exception:
                pass
            try:
                comps = a.get_components_by_class(unreal.SkyLightComponent)
                for c in comps:
                    try:
                        log("  Sky intensity={}".format(c.get_editor_property("intensity")))
                    except Exception as e:
                        log("  Sky props err: " + str(e))
            except Exception:
                pass

    # BP vars
    log("--- BP_GridManager variables ---")
    bp = unreal.load_asset(MGR)
    if not bp:
        log("NO BP")
        return
    try:
        for v in bel.get_introduced_variables(bp):
            vn = str(v.var_name) if hasattr(v, "var_name") else str(v)
            if any(k in vn for k in ("Sun", "Sky", "Moon", "TimeOfDay", "CurrentDay", "DayLength", "Day")):
                log("VAR " + vn)
    except Exception as e:
        log("vars via introduced: " + str(e))
        try:
            for v in bp.new_variables:
                log("VAR " + str(v.var_name) + " type=" + str(v.var_type))
        except Exception as e2:
            log("vars fail: " + str(e2))

    # ApplyDayNightVisuals node titles only
    log("--- ApplyDayNightVisuals nodes ---")
    g = bel.find_graph(bp, "ApplyDayNightVisuals")
    if not g:
        log("NO ApplyDayNightVisuals graph")
    else:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        nodes = list(ge.list_all_nodes())
        log("node_count={}".format(len(nodes)))
        for n in nodes:
            t = title(n)
            log("NODE [{}] {}".format(n.get_class().get_name(), t))
            # dump interesting pins for MapRange / SetIntensity / SetActorRotation / Get vars
            tl = t.lower()
            interesting = (
                "maprange" in tl or "setintensity" in tl or "setlightcolor" in tl
                or "setactorrotation" in tl or "makerotator" in tl
                or "sunactor" in tl or "skylight" in tl or "moon" in tl
                or "timeofday" in tl or "multiply" in tl or "sin" in tl
                or "branch" in tl or "isvalid" in tl or "getcomponent" in tl
                or n.get_class().get_name() in ("K2Node_FunctionEntry", "K2Node_VariableGet", "K2Node_IfThenElse")
            )
            if interesting:
                for p in bel.list_all_pins(n):
                    name, direction, val, linked = pin_info(p)
                    if val is not None and str(val) not in ("", "None"):
                        log("  pin {} {} val={!r} links={}".format(name, direction, val, linked))
                    elif linked:
                        log("  pin {} {} links={}".format(name, direction, linked))

        try:
            errs = ge.list_nodes_with_errors()
            log("errors={}".format(len(errs)))
            for e in errs:
                log("  ERR " + title(e))
        except Exception as e:
            log("err list: " + str(e))

    # AdvanceDayGrowth quick check (Watered-only)
    log("--- AdvanceDayGrowth quick ---")
    g2 = bel.find_graph(bp, "AdvanceDayGrowth")
    if g2:
        ge2 = unreal.BlueprintGraphEditor.get_graph_editor(g2)
        for n in ge2.list_all_nodes():
            t = title(n)
            if "growcell" in t.lower() or "equal" in t.lower() or "visualize" in t.lower():
                log("ADG NODE " + t)
                if "equal" in t.lower():
                    for p in bel.list_all_pins(n):
                        if str(p.get_pin_name()) == "B":
                            try:
                                log("  Equal.B={!r}".format(p.get_pin_value()))
                            except Exception:
                                pass

    # BeginPlay light finder snippets
    log("--- EventGraph / BeginPlay light-related ---")
    eg = bel.find_graph(bp, "EventGraph")
    if eg:
        ge3 = unreal.BlueprintGraphEditor.get_graph_editor(eg)
        for n in ge3.list_all_nodes():
            t = title(n)
            tl = t.lower()
            if any(k in tl for k in ("sun", "sky", "moon", "directional", "get actor", "getallactors")):
                log("EG NODE [{}] {}".format(n.get_class().get_name(), t))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log("WROTE " + OUT)
    log("=== Step A DONE ===")

if __name__ == "__main__":
    main()
