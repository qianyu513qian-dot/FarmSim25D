# -*- coding: utf-8 -*-
"""Probe BlueprintGraphEditor set/get var APIs and ForLoop / Percent / Cast."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

def log(m):
    unreal.log("[P4] " + str(m))
    print("[P4] " + str(m))

for name in sorted(dir(ge)):
    if any(k in name.lower() for k in ("set", "get", "member", "var", "macro", "cast", "branch", "event", "create", "add_")):
        if not name.startswith("_"):
            log("ge." + name)

# Test create set/get for a new temp var after adding
pin = unreal.EdGraphPinType()
pin.import_text('(PinCategory="real",PinSubCategory="")')
if "DayLengthSeconds" not in [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]:
    ok = bel.add_member_variable(bp, "DayLengthSeconds", pin)
    log("add DayLengthSeconds -> " + str(ok))
else:
    log("DayLengthSeconds already")

# Try set default via CDO
try:
    cdo = bel.get_default_object(bp)
    log("cdo=" + str(cdo))
    cdo.set_editor_property("DayLengthSeconds", 75.0)
    log("set CDO DayLengthSeconds=" + str(cdo.get_editor_property("DayLengthSeconds")))
except Exception as e:
    log("CDO set: " + str(e))

# Create get/set nodes
try:
    g = ge.add_get_member_variable_node("DayLengthSeconds")
    log("get node=" + str(bel.get_node_title(g)))
    s = ge.add_set_member_variable_node("DayLengthSeconds")
    log("set node=" + str(bel.get_node_title(s)))
    for p in bel.list_all_pins(s):
        log("  setpin {} {}".format(p.get_pin_name(), p.get_pin_direction()))
    ge.remove_nodes([g, s])
except Exception as e:
    log("get/set: " + str(e))

# For Loop macro
try:
    # How was For Loop added in BeginPlay?
    for n in ge.list_all_nodes():
        if "For" in str(bel.get_node_title(n)):
            log("existing For: {} class={}".format(bel.get_node_title(n), n.get_class().get_name()))
            for p in bel.list_all_pins(n):
                log("  {} {}".format(p.get_pin_name(), p.get_pin_direction()))
except Exception as e:
    log("for: " + str(e))

# create_node_from_name for ForLoop
for path in [
    "Flow Control|ForLoop",
    "Utilities|FlowControl|ForLoop",
    "Macro Libraries|Standard Macros|For Loop",
]:
    try:
        n = ge.create_node_from_name(path, unreal.Vector2D(0, 0), [])
        log("create_node_from_name {} -> {}".format(path, n))
        if n:
            ge.remove_nodes([n])
    except Exception as e:
        log("create_node_from_name {} : {}".format(path, e))

# add_macro?
if hasattr(ge, "add_macro_instance_node"):
    log("has add_macro_instance_node")
    try:
        log("doc=" + str(ge.add_macro_instance_node.__doc__))
    except Exception:
        pass

# Cast node
for path in [
    "/Script/Engine.DirectionalLight",
    "DirectionalLight",
]:
    pass
if hasattr(ge, "add_dynamic_cast_node"):
    log("has add_dynamic_cast_node doc=" + str(ge.add_dynamic_cast_node.__doc__))

# Percent float
for path in [
    "/Script/Engine.KismetMathLibrary:Percent_FloatFloat",
    "/Script/Engine.KismetMathLibrary:GenericPercent_FloatFloat",
    "/Script/Engine.KismetMathLibrary:FMod",
]:
    try:
        n = ge.add_call_function_node(path)
        log("OK {} -> {}".format(path, bel.get_node_title(n) if n else None))
        if n:
            for p in bel.list_all_pins(n):
                log("  {} {}".format(p.get_pin_name(), p.get_pin_direction()))
            ge.remove_nodes([n])
    except Exception as e:
        log("FAIL {} {}".format(path, e))

# MakeRotator pins
n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeRotator")
if n:
    for p in bel.list_all_pins(n):
        log("MakeRotator {} {}".format(p.get_pin_name(), p.get_pin_direction()))
    ge.remove_nodes([n])

# GetAllActorsOfClass pins + Array_Get
n = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
if n:
    for p in bel.list_all_pins(n):
        try:
            v = p.get_pin_value()
        except Exception:
            v = ""
        log("GetAll {} {} val={!r}".format(p.get_pin_name(), p.get_pin_direction(), v))
    ge.remove_nodes([n])

# Class pin for DirectionalLight - how to set?
# Often PinSubCategoryObject

# Max float
for path in [
    "/Script/Engine.KismetMathLibrary:FMax",
    "/Script/Engine.KismetMathLibrary:Max",
    "/Script/Engine.KismetMathLibrary:Max_FloatFloat",
]:
    try:
        n = ge.add_call_function_node(path)
        log("max {} -> {}".format(path, bel.get_node_title(n) if n else None))
        if n:
            ge.remove_nodes([n])
    except Exception as e:
        log("max fail {} {}".format(path, e))

# Select float / Select
for path in [
    "/Script/Engine.KismetMathLibrary:SelectFloat",
    "/Script/Engine.KismetSystemLibrary:SelectString",
]:
    try:
        n = ge.add_call_function_node(path)
        log("sel {} -> {}".format(path, bel.get_node_title(n) if n else None))
        if n:
            ge.remove_nodes([n])
    except Exception as e:
        log("sel fail {} {}".format(path, e))

# Don't leave DayLengthSeconds broken - keep it, we'll use it
bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)
log("compiled after DayLengthSeconds add")
log("DONE")
