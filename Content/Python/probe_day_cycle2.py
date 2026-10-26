# -*- coding: utf-8 -*-
"""Probe2: DirectionalLight details, BeginPlay/Tick chains, UpdateFarmHUD, how to add vars."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[PROBE_DAY2] " + str(m))
    print("[PROBE_DAY2] " + str(m))

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def conn(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

# Lights
try:
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = subsystem.get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

for a in actors:
    cls = a.get_class().get_name()
    name = a.get_name()
    if "Directional" in cls or "Directional" in name:
        log("DIRLIGHT {} {}".format(cls, name))
        log("  loc={} rot={}".format(a.get_actor_location(), a.get_actor_rotation()))
        try:
            for c in a.get_components_by_class(unreal.LightComponent):
                log("  lightcomp {} {}".format(c.get_class().get_name(), c.get_name()))
                for prop in ("intensity", "light_color", "indirect_lighting_intensity", "intensity_units",
                             "atmosphere_sun_light", "cast_shadows", "mobility"):
                    try:
                        log("    {}={}".format(prop, c.get_editor_property(prop)))
                    except Exception as e:
                        log("    {} err {}".format(prop, e))
        except Exception as e:
            log("  comps " + str(e))
        # also try DirectionalLightComponent specifically
        try:
            for c in a.get_components_by_class(unreal.DirectionalLightComponent):
                for prop in ("intensity", "light_color", "forward_shading_priority"):
                    try:
                        log("    dl.{}={}".format(prop, c.get_editor_property(prop)))
                    except Exception:
                        pass
        except Exception:
            pass

# GridManager BeginPlay/Tick chain
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
for n in ge.list_all_nodes():
    cls = n.get_class().get_name()
    if cls != "K2Node_Event":
        continue
    t = title(n)
    thenp = find_pin(n, "then", "Output")
    log("EVENT {} then->{}".format(t, [title(c.get_owning_node()) for c in conn(thenp)]))
    # BFS
    queue = [(c.get_owning_node(), 1) for c in conn(thenp)]
    seen = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in seen or d > 12:
            continue
        seen.add(id(cur))
        log("  " * d + title(cur))
        for pn in ("then", "else", "LoopBody", "Completed"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in conn(tp):
                    queue.append((c.get_owning_node(), d + 1))

# How add variable?
log("=== add_member_variable APIs ===")
for name in dir(bel):
    if "var" in name.lower() or "member" in name.lower():
        log("bel." + name)
for name in dir(unreal):
    if "Blueprint" in name and ("Var" in name or "Member" in name or "Editor" in name):
        if not name.startswith("_"):
            log("unreal." + name)

# Check existing var names via get nodes already present
var_names = set()
for n in ge.list_all_nodes():
    t = title(n)
    if t.startswith("Get ") or t.startswith("Set "):
        var_names.add(t)
log("EG get/set: " + str(sorted(var_names)))

# Try listing from generated class
try:
    gen = bp.generated_class()
    log("gen=" + str(gen))
    # CDO defaults
    cdo = unreal.get_default_object(gen)
    for prop in ("CellSize", "GridWidth", "GridHeight", "GridOrigin", "PlotStates", "BlockedIndices",
                 "CurrentDay", "TimeOfDay", "DayLengthSeconds"):
        try:
            log("CDO.{}={}".format(prop, cdo.get_editor_property(prop)))
        except Exception as e:
            log("CDO.{} missing ({})".format(prop, type(e).__name__))
except Exception as e:
    log("gen err " + str(e))

# UpdateFarmHUD on character
char = unreal.load_asset(CHAR)
try:
    uge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(char, "UpdateFarmHUD"))
    log("=== UpdateFarmHUD nodes ===")
    for n in uge.list_all_nodes():
        log("  {} | {}".format(n.get_class().get_name(), title(n)))
        if title(n) == "PrintString":
            for pn in ("InString", "Key", "Duration", "TextColor"):
                p = find_pin(n, pn, "Input")
                if p:
                    try:
                        log("    {}={!r} links={}".format(pn, p.get_pin_value(), len(conn(p))))
                    except Exception as e:
                        log("    {} {}".format(pn, e))
except Exception as e:
    log("UpdateFarmHUD dump: " + str(e))

# How SetLightIntensity / SetIntensity looked up
log("=== light setter search ===")
# Just list a few known paths
for path in [
    "/Script/Engine.LightComponent:SetIntensity",
    "/Script/Engine.LightComponentBase:SetIntensity",
    "/Script/Engine.DirectionalLightComponent:SetIntensity",
    "/Script/Engine.Actor:K2_SetActorRotation",
    "/Script/Engine.KismetSystemLibrary:PrintString",
    "/Script/Engine.KismetMathLibrary:FMod",
    "/Script/Engine.KismetMathLibrary:Percent_FloatFloat",
    "/Script/Engine.KismetMathLibrary:FClamp",
    "/Script/Engine.KismetMathLibrary:Lerp",
    "/Script/Engine.KismetMathLibrary:Sin",
    "/Script/Engine.KismetMathLibrary:Cos",
    "/Script/Engine.KismetMathLibrary:MakeRotator",
    "/Script/Engine.KismetMathLibrary:Conv_IntToString",
    "/Script/Engine.KismetStringLibrary:Concat_StrStr",
    "/Script/Engine.GameplayStatics:GetAllActorsOfClass",
    "/Script/Engine.KismetSystemLibrary:GetActorListFromComponentList",
]:
    try:
        # try creating temporary? just log path existence via load
        log("path ok? " + path)
    except Exception as e:
        log("path " + path + " " + str(e))

# Check add_member_variable signature
try:
    import inspect
    if hasattr(bel, "add_member_variable"):
        log("add_member_variable exists")
except Exception:
    pass

# Look at recent scripts that add variables
log("DONE")
