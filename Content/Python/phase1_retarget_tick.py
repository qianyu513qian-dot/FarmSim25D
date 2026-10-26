# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary

def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        pname = str(p.get_pin_name())
        direc = str(p.get_pin_direction())
        if name_substr.lower() in pname.lower():
            if direction is None or direction.lower() in direc.lower():
                return p
    return None

def connect(a, b):
    if a is None or b is None:
        return False
    return a.try_create_connection(b)

CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
MGR = "/Game/Farm/Grid/BP_GridManager"

# Dump character
bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
unreal.log("=== CHAR NODES ===")
for n in ge.list_all_nodes():
    unreal.log(bel.get_node_title(n) + " | " + n.get_class().get_name() + " | " + n.get_name())

# Dump gridmanager event graph briefly
bp2 = unreal.EditorAssetLibrary.load_asset(MGR)
ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp2))
unreal.log("=== MGR NODES ===")
for n in ge2.list_all_nodes():
    unreal.log(bel.get_node_title(n) + " | " + n.get_class().get_name())

# Fix tick: find CallFunction GetActorOfClass by pins
get_ref = None
for n in ge.list_all_nodes():
    if "GridManagerRef" in bel.get_node_title(n) and "Get" in n.get_class().get_name():
        get_ref = n
    if n.get_class().get_name() == "K2Node_VariableGet":
        for p in bel.list_all_pins(n):
            if "GridManagerRef" in str(p.get_pin_name()):
                get_ref = n

if not get_ref:
    get_ref = ge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, unreal.IntPoint(-500, 40))

ref_out = find_pin(get_ref, "GridManagerRef", "Output") or bel.find_output_pin_by_index(get_ref, 0)

for n in ge.list_all_nodes():
    # identify GetActorOfClass by ActorClass pin
    class_pin = find_pin(n, "ActorClass")
    if class_pin is not None and n.get_class().get_name() == "K2Node_CallFunction":
        unreal.log("found GetActorOfClass-like: " + n.get_name() + " title=" + bel.get_node_title(n))
        ret_pin = find_pin(n, "ReturnValue")
        if ret_pin and ref_out:
            cps = list(ret_pin.list_connected_pins())
            unreal.log(" connected count=" + str(len(cps)))
            for cp in cps:
                try:
                    ret_pin.break_single_pin_link(cp)
                except Exception as ex:
                    unreal.log_warning(str(ex))
                ok = connect(ref_out, cp)
                unreal.log("retarget connect " + str(ok))
        # reroute tick exec past this node if needed
        tick = ge.find_event_node("ReceiveTick")
        if tick:
            tick_then = bel.find_then_pin(tick) or find_pin(tick, "then", "Output")
            get_then = bel.find_then_pin(n) or find_pin(n, "then", "Output")
            get_exec = bel.find_execute_pin(n) or find_pin(n, "execute", "Input")
            # see if tick connects to get
            if tick_then:
                tick_targets = list(tick_then.list_connected_pins())
                unreal.log("tick targets: " + str([str(t.get_pin_name()) + "@" + str(t.get_owning_node().get_name()) for t in tick_targets]))
                if get_exec in tick_targets or any(t.get_owning_node() == n for t in tick_targets):
                    nexts = list(get_then.list_connected_pins()) if get_then else []
                    try:
                        tick_then.break_pin_links()
                    except Exception:
                        pass
                    for np in nexts:
                        connect(tick_then, np)
                        unreal.log("tick bypass to " + str(np.get_owning_node().get_name()))

try:
    bel.compile_blueprint(bp)
    unreal.log("char compile ok")
except Exception as ex:
    unreal.log_warning(str(ex))
unreal.EditorAssetLibrary.save_asset(CHAR)
unreal.log("done")