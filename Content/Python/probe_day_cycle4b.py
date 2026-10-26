# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.load_asset(MGR)
def log(m):
    unreal.log("[P4b] " + str(m)); print("[P4b] " + str(m))
log("alive")
names = [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]
log("has DayLengthSeconds=" + str("DayLengthSeconds" in names))
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
# list ge methods briefly
interesting = [n for n in dir(ge) if any(k in n.lower() for k in ("set_member","get_member","macro","cast","branch","add_call","create_node")) and not n.startswith("_")]
log("ge methods=" + str(interesting))
# For Loop existing
for n in ge.list_all_nodes():
    t = str(bel.get_node_title(n))
    if "For" in t or "Loop" in t:
        log("node {} {}".format(n.get_class().get_name(), t))
        for p in bel.list_all_pins(n):
            log("  {} {}".format(p.get_pin_name(), p.get_pin_direction()))
# try add_macro
if hasattr(ge, "add_macro_node"):
    log("add_macro_node doc=" + str(ge.add_macro_node.__doc__))
if hasattr(ge, "add_macro_instance_node"):
    log("add_macro_instance_node doc=" + str(ge.add_macro_instance_node.__doc__))
# try create_node_from_name ForLoop
try:
    n = ge.create_node_from_name("Flow Control|ForLoop", unreal.Vector2D(100,100), [])
    log("ForLoop create=" + str(n))
    if n:
        log("title=" + str(bel.get_node_title(n)))
        ge.remove_nodes([n])
except Exception as e:
    log("ForLoop create fail " + str(e))
try:
    n = ge.create_node_from_name("Utilities|FlowControl|For Loop", unreal.Vector2D(100,100), [])
    log("For Loop create=" + str(n))
    if n:
        log("title=" + str(bel.get_node_title(n)))
        ge.remove_nodes([n])
except Exception as e:
    log("For Loop fail " + str(e))
# set/get DayLengthSeconds
try:
    g = ge.add_get_member_variable_node("DayLengthSeconds")
    s = ge.add_set_member_variable_node("DayLengthSeconds")
    log("get/set ok {} / {}".format(bel.get_node_title(g), bel.get_node_title(s)))
    ge.remove_nodes([g,s])
except Exception as e:
    log("get/set " + str(e))
# CDO
try:
    cdo = bel.get_default_object(bp)
    cdo.set_editor_property("DayLengthSeconds", 75.0)
    log("CDO DayLengthSeconds=" + str(cdo.get_editor_property("DayLengthSeconds")))
except Exception as e:
    log("CDO " + str(e))
log("DONE")
