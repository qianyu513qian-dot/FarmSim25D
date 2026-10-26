# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

bp = unreal.EditorAssetLibrary.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
# Dump Tick connections
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Tick" in t:
        unreal.log("TICK node " + t)
        for p in bel.list_all_pins(n):
            cps = list(p.list_connected_pins())
            unreal.log("  {} ({}) -> {}".format(p.get_pin_name(), p.get_pin_direction(), len(cps)))
            for cp in cps:
                unreal.log("    " + bel.get_node_title(cp.get_owning_node()) + "." + str(cp.get_pin_name()))

# list var names
unreal.log("vars: " + str([str(x) for x in bel.list_member_variable_names(bp)]))

# TillCell Equal how Tilled is set
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
for n in tge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Equal" in t.lower() or "Set Array" in t or t == "Get":
        unreal.log("till: " + t)
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = list(p.list_connected_pins())
            unreal.log("  {} val=[{}] conn={}".format(p.get_pin_name(), val, len(cps)))

# Probe Percent / Division for index->gx gy
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")))
for name in ["Utilities|Operators|Percent", "integer % integer", "%", "Utilities|Operators|Divide", "integer / integer"]:
    try:
        n = cge.create_node_from_name(name, unreal.Vector2D(0,0), [])
        unreal.log("create {} -> {}".format(name, bel.get_node_title(n) if n else None))
        if n:
            for p in bel.list_all_pins(n):
                unreal.log("  " + str(p.get_pin_name()))
            cge.remove_nodes([n])
    except Exception as ex:
        unreal.log_warning(str(ex))

# Make Literal Byte / enum
for name in ["Make Literal Byte", "Byte", "enum"]:
    try:
        n = cge.create_node_from_name(name, unreal.Vector2D(0,0), [])
        unreal.log("lit {} -> {}".format(name, n))
        if n:
            cge.remove_nodes([n])
    except Exception as ex:
        unreal.log_warning(str(ex))