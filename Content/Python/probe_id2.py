# -*- coding: utf-8 -*-
"""Deeper identification of call targets and IA assets via export/pins."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[ID2] " + str(m))
    print("[ID2] " + str(m))

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())

for i, n in enumerate(nodes):
    cn = n.get_class().get_name()
    # try export_text on node
    et = ""
    try:
        et = n.export_text()
    except Exception:
        try:
            et = unreal.SystemLibrary.get_display_name(n)
        except Exception:
            et = ""
    # also try get_editor_property with various names
    props = {}
    for prop in ("input_action", "InputAction", "function_reference", "FunctionReference",
                 "event_reference", "EventReference", "variable_name", "VariableName",
                 "member_name", "MemberName"):
        try:
            props[prop] = str(n.get_editor_property(prop))
        except Exception:
            pass
    # pins with default values of interest
    pin_info = []
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        pv = ""
        try:
            pv = p.get_pin_value()
        except Exception:
            pass
        if pn in ("InString", "InputAction", "self", "Success") or (pv and len(str(pv)) < 80 and pv not in ("", "0", "0.0", "None")):
            pin_info.append("{}={!r}".format(pn, pv))
    interesting = cn in ("K2Node_EnhancedInputAction", "K2Node_Event", "K2Node_CallFunction",
                         "K2Node_IfThenElse", "K2Node_VariableGet", "K2Node_VariableSet",
                         "K2Node_FormatText")
    # Filter: only dump if looks farm-related or has InString
    snippet = (et or "")[:200]
    if interesting and (i >= 27 or "Print" in snippet or "Plant" in snippet or "Harvest" in snippet
                        or "Till" in snippet or "Grid" in snippet or "IA_" in snippet
                        or any("InString" in x for x in pin_info) or cn == "K2Node_EnhancedInputAction"
                        or cn == "K2Node_Event"):
        log("N[{}] {} props={} pins={} et={!r}".format(i, cn, props, pin_info, snippet))

# Also inspect add_member_variable signature via help
import inspect
try:
    log("add_member_variable sig=" + str(inspect.signature(bel.add_member_variable)))
except Exception as e:
    log("sig err " + str(e))
    try:
        log("add_member_variable doc=" + str(bel.add_member_variable.__doc__))
    except Exception as e2:
        log(str(e2))
