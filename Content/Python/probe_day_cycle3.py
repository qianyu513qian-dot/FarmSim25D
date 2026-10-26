# -*- coding: utf-8 -*-
"""Probe GrowCell VisualizeCell pins and add_member_variable signature / defaults."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[P3] " + str(m))
    print("[P3] " + str(m))

fn = bel.add_member_variable
log("doc=" + str(getattr(fn, "__doc__", None)))
try:
    log("annotations=" + str(getattr(fn, "__annotations__", None)))
except Exception:
    pass
log("dir sample=" + str([x for x in dir(fn) if not x.startswith("_")][:20]))

# list member vars
bp = unreal.load_asset(MGR)
try:
    names = bel.list_member_variable_names(bp)
    log("member vars=" + str([str(n) for n in names]))
except Exception as e:
    log("list_member_variable_names: " + str(e))

# GrowCell VisualizeCell call pins
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
for n in ge.list_all_nodes():
    t = str(bel.get_node_title(n))
    if "VisualizeCell" in t:
        log("VisualizeCell call pins:")
        for p in bel.list_all_pins(n):
            links = []
            try:
                links = [(str(bel.get_node_title(c.get_owning_node())), str(c.get_pin_name())) for c in (p.list_connected_pins() or [])]
            except Exception:
                pass
            try:
                val = p.get_pin_value()
            except Exception:
                val = "?"
            log("  {} | {} | val={!r} | links={}".format(p.get_pin_name(), p.get_pin_direction(), val, links))

# Can we create SetIntensity node?
test_ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
for path in [
    "/Script/Engine.LightComponent:SetIntensity",
    "/Script/Engine.LightComponentBase:SetIntensity",
    "/Script/Engine.DirectionalLightComponent:SetIntensity",
    "/Script/Engine.LightComponent:SetLightColor",
    "/Script/Engine.Actor:K2_SetActorRotation",
    "/Script/Engine.Actor:GetComponentByClass",
    "/Script/Engine.GameplayStatics:GetAllActorsOfClass",
    "/Script/Engine.KismetArrayLibrary:Array_Length",
    "/Script/Engine.KismetMathLibrary:Multiply_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Divide_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Add_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Subtract_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Greater_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Less_FloatFloat",
    "/Script/Engine.KismetMathLibrary:MapRangeClamped",
    "/Script/Engine.KismetMathLibrary:DegSin",
    "/Script/Engine.KismetMathLibrary:Sin",
    "/Script/Engine.KismetMathLibrary:MakeColor",
    "/Script/Engine.KismetMathLibrary:LinearColorLerp",
    "/Script/Engine.KismetMathLibrary:Conv_FloatToLinearColor",
]:
    try:
        n = test_ge.add_call_function_node(path)
        if n:
            log("CREATE OK " + path + " -> " + str(bel.get_node_title(n)))
            # remove immediately
            test_ge.remove_nodes([n])
        else:
            log("CREATE None " + path)
    except Exception as e:
        log("CREATE FAIL " + path + " : " + str(e))

# How to set default value on member var?
for name in dir(bel):
    if "default" in name.lower() or "variable_default" in name.lower():
        log("bel." + name)

log("DONE")
