# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
def log(m):
    unreal.log("[P6] "+str(m)); print("[P6] "+str(m))

paths = [
    "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble",
    "/Script/Engine.KismetMathLibrary:Divide_DoubleDouble",
    "/Script/Engine.KismetMathLibrary:Add_DoubleDouble",
    "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble",
    "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble",
    "/Script/Engine.KismetMathLibrary:Multiply_IntInt",
    "/Script/Engine.KismetMathLibrary:Divide_IntInt",
    "/Script/Engine.KismetMathLibrary:Percent_IntInt",
    "/Script/Engine.KismetMathLibrary:Add_IntInt",
    "/Script/Engine.KismetMathLibrary:Subtract_IntInt",
    "/Script/Engine.KismetMathLibrary:Multiply_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Divide_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Add_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Subtract_FloatFloat",
    "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat",
    "/Script/Engine.KismetMathLibrary:Percent_FloatFloat",
    "/Script/Engine.KismetMathLibrary:FMod",
    "/Script/Engine.KismetMathLibrary:Conv_IntToString",
    "/Script/Engine.KismetStringLibrary:Conv_IntToString",
    "/Script/Engine.KismetStringLibrary:Concat_StrStr",
    "/Script/Engine.KismetSystemLibrary:IsValid",
    "/Script/Engine.KismetMathLibrary:MakeColor",
    "/Script/Engine.KismetMathLibrary:LinearColorLerp",
    "/Script/Engine.KismetMathLibrary:MapRangeClamped",
    "/Script/Engine.KismetMathLibrary:Sin",
    "/Script/Engine.KismetMathLibrary:MakeRotator",
]
for path in paths:
    try:
        n = ge.add_call_function_node(path)
        if n:
            pins = [(str(p.get_pin_name()), str(p.get_pin_direction()).split(".")[-1]) for p in bel.list_all_pins(n)]
            log("OK {} title={} pins={}".format(path.split(":")[-1], bel.get_node_title(n), pins[:8]))
            ge.remove_nodes([n])
        else:
            log("None " + path)
    except Exception as e:
        log("FAIL {} {}".format(path, e))

# create_node_from_name variants for int ops that worked historically
for name in [
    "Utilities|Operators|Multiply",
    "Utilities|Operators|integer * integer",
    "Math|Integer|integer * integer",
    "int * int",
    "Utilities|Operators|int * int",
]:
    try:
        n = ge.create_node_from_name(name, unreal.Vector2D(0,0), [])
        log("create_name {} -> {}".format(name, bel.get_node_title(n) if n else None))
        if n:
            ge.remove_nodes([n])
    except Exception as e:
        log("create_name {} FAIL {}".format(name, e))

# GetComponentByClass ComponentClass pin type
n = ge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
if n:
    for p in bel.list_all_pins(n):
        log("GetComp {} {} type={}".format(p.get_pin_name(), p.get_pin_direction(), p.get_pin_type_display_string() if hasattr(p,'get_pin_type_display_string') else '?'))
        try:
            log("  val={!r}".format(p.get_pin_value()))
        except Exception as e:
            log("  valerr "+str(e))
    ge.remove_nodes([n])

# GetAllActorsOfClass
n = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
if n:
    for p in bel.list_all_pins(n):
        log("GetAll {} {} type={}".format(p.get_pin_name(), p.get_pin_direction(), getattr(p, 'get_pin_type_display_string', lambda: '?')()))
        try:
            log("  val={!r}".format(p.get_pin_value()))
        except Exception as e:
            log("  valerr "+str(e))
    ge.remove_nodes([n])

log("DONE")
