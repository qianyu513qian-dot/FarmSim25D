# -*- coding: utf-8 -*-
"""Probe lights, GridManager graphs/vars, GrowCell, HUD for day cycle."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[PROBE_DAY] " + str(m))
    print("[PROBE_DAY] " + str(m))

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

# --- GridManager ---
bp = unreal.load_asset(MGR)
log("=== BP_GridManager graphs ===")
try:
    log("graphs=" + str([str(n) for n in bel.list_graph_names(bp)]))
except Exception as e:
    log("list_graph_names: " + str(e))
try:
    log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
except Exception as e:
    log("list_functions: " + str(e))
try:
    # variables
    vars_out = []
    for v in bel.get_blueprint_variable_list(bp) if hasattr(bel, "get_blueprint_variable_list") else []:
        vars_out.append(str(v))
    if not vars_out:
        # try alternate
        try:
            for v in bp.get_editor_property("new_variables"):
                name = v.get_editor_property("var_name") if hasattr(v, "get_editor_property") else str(v)
                vars_out.append(str(name))
        except Exception as e2:
            log("vars alt: " + str(e2))
    log("vars=" + str(vars_out))
except Exception as e:
    log("vars: " + str(e))

# Dump EventGraph nodes briefly
eg = bel.find_graph(bp, "EventGraph")
if eg:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    log("=== EventGraph nodes ({}) ===".format(len(list(ge.list_all_nodes()))))
    for n in ge.list_all_nodes():
        cls = n.get_class().get_name()
        log("  {} | {}".format(cls, title(n)))

# GrowCell summary
if "GrowCell" in [str(n) for n in bel.list_graph_names(bp)]:
    gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
    log("=== GrowCell nodes ===")
    for n in gge.list_all_nodes():
        log("  {} | {}".format(n.get_class().get_name(), title(n)))

# --- Level lights ---
log("=== Level actors (lights / sky) ===")
try:
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = subsystem.get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

light_count = 0
for a in actors:
    cls = a.get_class().get_name()
    name = a.get_name()
    if any(k in cls.lower() or k in name.lower() for k in ("light", "sky", "sun", "atmosphere", "fog")):
        light_count += 1
        loc = a.get_actor_location()
        log("  {} | {} | loc=({},{},{})".format(cls, name, loc.x, loc.y, loc.z))
        # try intensity
        for prop in ("intensity", "light_color", "mobility", "source_type"):
            try:
                val = a.get_editor_property(prop)
                log("    {}.{}={}".format(name, prop, val))
            except Exception:
                pass
        # components
        try:
            for c in a.get_components_by_class(unreal.ActorComponent):
                cn = c.get_class().get_name()
                if "light" in cn.lower() or "sky" in cn.lower():
                    log("    comp {} {}".format(cn, c.get_name()))
                    for prop in ("intensity", "light_color", "indirect_lighting_intensity"):
                        try:
                            log("      {}.{}={}".format(c.get_name(), prop, c.get_editor_property(prop)))
                        except Exception:
                            pass
        except Exception as e:
            log("    comps err " + str(e))

log("light-ish actors=" + str(light_count))

# GridManager actor in level?
for a in actors:
    if "GridManager" in a.get_name() or "GridManager" in a.get_class().get_name():
        log("GridManager actor: {} {}".format(a.get_class().get_name(), a.get_name()))

# Character UpdateFarmHUD / PrintString Key pattern
char = unreal.load_asset(CHAR)
ceg = bel.find_graph(char, "EventGraph")
cge = unreal.BlueprintGraphEditor.get_graph_editor(ceg)
log("=== Char graphs with HUD/Print ===")
try:
    log("char graphs=" + str([str(n) for n in bel.list_graph_names(char)]))
except Exception:
    pass
for n in cge.list_all_nodes():
    t = title(n)
    if t in ("UpdateFarmHUD", "PrintString") or "HUD" in t or "Day" in t:
        log("  {} | {}".format(n.get_class().get_name(), t))
        if t == "PrintString":
            for pn in ("InString", "Key", "Duration", "TextColor"):
                p = None
                for pp in bel.list_all_pins(n):
                    if pn.lower() in str(pp.get_pin_name()).lower():
                        p = pp
                        break
                if p:
                    try:
                        log("    {}={!r} connected={}".format(pn, p.get_pin_value(), len(list(p.list_connected_pins() or []))))
                    except Exception as e:
                        log("    {} err {}".format(pn, e))

# Check if UpdateFarmHUD function exists
try:
    for gname in bel.list_graph_names(char):
        if "HUD" in str(gname) or "Farm" in str(gname) or "Update" in str(gname):
            log("char graph interest: " + str(gname))
except Exception:
    pass

log("=== DONE ===")
