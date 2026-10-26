# -*- coding: utf-8 -*-
"""Map Plant/Harvest exec chains + probe UMG APIs + default var value APIs."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[P] " + str(m))
    print("[P] " + str(m))

def linked(p):
    try:
        return list(p.get_linked_to() or [])
    except Exception:
        return []

def node_label(n):
    cn = n.get_class().get_name()
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        try:
            pv = p.get_pin_value()
        except Exception:
            pv = ""
        if pn == "InString" and pv:
            return "Print({!r})".format(pv)
        if pn == "InputAction" and pv:
            return "IA({})".format(pv.split("/")[-1].split(".")[0] if pv else "?")
        if pn == "Success":
            return "Call(SuccessOut)"
    # GridX input means WorldToGrid or cell op
    pins = [str(p.get_pin_name()) for p in bel.list_all_pins(n)]
    if "GridX" in pins and "WorldLocation" in pins:
        return "WorldToGrid"
    if "GridX" in pins and "Success" in pins:
        return "CellOp"
    if "GridX" in pins and "World Location" in pins:
        return "GridToWorld"
    if "GridManagerRef" in pins:
        return "Get GridManagerRef"
    if cn == "K2Node_IfThenElse":
        return "Branch"
    if "ReturnValue" in pins and "self" in pins and len(pins) <= 3:
        return "GetActorLocation?"
    return cn

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())

# Find Plant and Harvest IA nodes and walk Started chain
for i, n in enumerate(nodes):
    if n.get_class().get_name() != "K2Node_EnhancedInputAction":
        continue
    ia = ""
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) == "InputAction":
            try:
                ia = p.get_pin_value()
            except Exception:
                pass
    if "Plant" not in ia and "Harvest" not in ia:
        continue
    log("==== " + ia)
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) != "Started":
            continue
        # BFS exec from Started
        queue = [(lp.get_owning_node(), 0) for lp in linked(p)]
        seen = set()
        while queue:
            cur, depth = queue.pop(0)
            if id(cur) in seen or depth > 12:
                continue
            seen.add(id(cur))
            log("  " + ("  "*depth) + node_label(cur))
            for cp in bel.list_all_pins(cur):
                cpn = str(cp.get_pin_name())
                if cpn in ("then", "then", "else") or "then" in cpn.lower():
                    for lp in linked(cp):
                        queue.append((lp.get_owning_node(), depth + 1))

# BeginPlay walk
for i, n in enumerate(nodes):
    if n.get_class().get_name() != "K2Node_Event":
        continue
    # check if ReceiveBeginPlay by looking at linked chain / pins
    has_delta = any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n))
    kind = "Tick" if has_delta else "BeginPlay?"
    log("EVENT[{}] kind={}".format(i, kind))
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) == "then":
            for lp in linked(p):
                log("  -> " + node_label(lp.get_owning_node()))

# UMG / defaults
log("UMG classes: " + str([x for x in dir(unreal) if "Widget" in x and ("Factory" in x or "Blueprint" in x or "Tree" in x)][:30]))
log("has set_blueprint_variable_default? " + str(hasattr(bel, "set_blueprint_variable_default_value") or hasattr(unreal, "BlueprintEditorLibrary")))
# check default value methods
log("default methods: " + str([x for x in dir(bel) if "default" in x.lower() or "Default" in x]))
# CDO default
try:
    gen = unreal.load_object(None, CHAR + "_C")
    log("gen=" + str(gen))
except Exception as e:
    log("gen err " + str(e))
# Generated class
try:
    bp2 = unreal.load_asset(CHAR)
    gc = bp2.generated_class()
    cdo = unreal.get_default_object(gc)
    log("CDO=" + str(cdo))
except Exception as e:
    log("CDO err " + str(e))
