# -*- coding: utf-8 -*-
"""Deep probe: exec chain + tags + moon color. READ ONLY."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
OUT = r"E:\UE\FarmSim25D\Content\Python\_probe_sun_moon_stepA2.txt"
lines = []

def log(m):
    s = str(m)
    lines.append(s)
    unreal.log("[SMA2] " + s)
    print("[SMA2] " + s)

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    want = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connected(pin):
    if not pin:
        return []
    try:
        return list(pin.list_connected_pins() or [])
    except Exception as e:
        log("list_connected_pins err: " + str(e))
        return []

def walk_exec(start_pin, limit=40):
    chain = []
    pin = start_pin
    seen = set()
    for _ in range(limit):
        if not pin:
            break
        links = connected(pin)
        if not links:
            chain.append("(end)")
            break
        nxt_pin = links[0]
        nxt = nxt_pin.get_owning_node()
        nid = id(nxt)
        if nid in seen:
            chain.append("CYCLE " + title(nxt))
            break
        seen.add(nid)
        chain.append(title(nxt) + " [" + nxt.get_class().get_name() + "]")
        # continue via then / execute output
        thenp = find_pin(nxt, "then", "Output")
        if thenp is None:
            # Branch: note both then/else but follow then
            thenp = find_pin(nxt, "then", "Output")
        pin = thenp
    return chain

def main():
    log("=== Step A2 deep ===")
    # Level tags + moon color as LinearColor if possible
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        cn = a.get_class().get_name()
        if cn not in ("DirectionalLight", "SkyLight", "SkyAtmosphere"):
            continue
        label = a.get_actor_label()
        try:
            tags = [str(t) for t in a.tags]
        except Exception:
            try:
                tags = [str(t) for t in a.get_editor_property("tags")]
            except Exception:
                tags = ["?"]
        log("ACTOR {} label={!r} tags={}".format(cn, label, tags))
        if cn == "DirectionalLight":
            for c in a.get_components_by_class(unreal.DirectionalLightComponent):
                try:
                    lc = c.get_editor_property("light_color")
                    log("  color struct={!r} type={}".format(lc, type(lc)))
                    # try r,g,b attrs
                    for attr in ("r", "g", "b", "R", "G", "B"):
                        if hasattr(lc, attr):
                            log("  color.{}={}".format(attr, getattr(lc, attr)))
                except Exception as e:
                    log("  color err " + str(e))
                try:
                    log("  inten={} atm={} idx={} mob={}".format(
                        c.intensity, c.atmosphere_sun_light,
                        c.atmosphere_sun_light_index, c.mobility))
                except Exception as e:
                    log("  props " + str(e))

    bp = unreal.load_asset(MGR)
    names = [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]
    for want in ("SunActor", "MoonActor", "SkyLightActor", "TimeOfDay", "CurrentDay", "DayLengthSeconds"):
        log("VAR {} present={}".format(want, want in names))

    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    entry = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
            break
    then = find_pin(entry, "then", "Output")
    log("Apply exec chain from entry:")
    for step in walk_exec(then):
        log("  -> " + step)

    # Dump data links for key nodes
    log("--- key data links ---")
    for n in ge.list_all_nodes():
        t = title(n)
        interesting = any(k in t for k in (
            "MapRange", "MakeRotator", "SetIntensity", "SetLightColor",
            "Set Actor Rotation", "Get SunActor", "Get MoonActor", "Get Sky",
            "float * float", "float + float", "Sin", "IsValid", "Branch",
            "Get TimeOfDay", "MakeColor", "GetComponent"
        ))
        if not interesting and n.get_class().get_name() not in ("K2Node_IfThenElse",):
            continue
        log("NODE " + t)
        for p in bel.list_all_pins(n):
            links = connected(p)
            if not links:
                continue
            for lp in links:
                log("  {} ({}) <-> {} @ {}".format(
                    p.get_pin_name(), p.get_pin_direction(),
                    lp.get_pin_name(), title(lp.get_owning_node())))

    # EventGraph moon assign chain
    log("--- EventGraph light assign ---")
    eg = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    for n in eg.list_all_nodes():
        t = title(n)
        if any(k in t for k in ("SunActor", "MoonActor", "SkyLight", "GetAllActors", "Get All Actors", "FarmSun", "FarmMoon")):
            log("EG " + t)
            for p in bel.list_all_pins(n):
                try:
                    v = p.get_pin_value()
                except Exception:
                    v = None
                links = connected(p)
                if (v is not None and str(v) not in ("", "None", "0", "0.0", "false", "true")) or links:
                    log("  pin {} val={!r} links={}".format(
                        p.get_pin_name(), v,
                        ["{}@{}".format(lp.get_pin_name(), title(lp.get_owning_node())) for lp in links]))

    # Position of nodes (to distinguish sun vs moon SetIntensity)
    log("--- node positions (x,y) ---")
    for n in ge.list_all_nodes():
        t = title(n)
        if any(k in t for k in ("SetIntensity", "SetLightColor", "Set Actor Rotation", "Get Sun", "Get Moon", "Get Sky", "MapRange", "MakeRotator", "Branch", "IsValid")):
            try:
                p = bel.get_node_pos(n)
                log("  pos=({},{}) {}".format(p.x, p.y, t))
            except Exception as e:
                log("  pos? {} {}".format(t, e))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log("WROTE " + OUT)

if __name__ == "__main__":
    main()
