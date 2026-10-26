# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def dump_api(obj, substr):
    for n in dir(obj):
        if substr.lower() in n.lower():
            unreal.log(type(obj).__name__ + "." + n)

unreal.log("=== probe ===")
dump_api(bel, "rename")
dump_api(bel, "function")
dump_api(bel, "graph")
bp = unreal.EditorAssetLibrary.load_asset(MGR)
unreal.log("graphs " + str([str(n) for n in bel.list_graph_names(bp)]))
unreal.log("funcs " + str([str(f) for f in bel.list_functions(bp)]))
# try rename_graph with 2 args
try:
    g = bel.find_graph(bp, "TillCell")
    unreal.log("find TillCell: " + str(g))
    if g:
        unreal.log("graph name " + str(g.get_name()))
        dump_api(g, "name")
        dump_api(g, "rename")
except Exception as ex:
    unreal.log_warning(str(ex))
# TillCell_0 still in funcs?
try:
    g0 = bel.find_graph(bp, "TillCell_0")
    unreal.log("find TillCell_0: " + str(g0))
except Exception as ex:
    unreal.log_warning(str(ex))

# Try creating call node with TillCell_0 path
cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
for path in [
    "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:TillCell",
    "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:TillCell_0",
]:
    n = cge.add_call_function_node(path)
    unreal.log("add_call " + path + " -> " + str(n) + (" title=" + bel.get_node_title(n) if n else ""))
    if n:
        for p in bel.list_all_pins(n):
            unreal.log("  pin " + str(p.get_pin_name()) + " " + str(p.get_pin_direction()))
        cge.remove_nodes([n])

# create_node_from_name variants
for name in ["TillCell", "Till Cell", "TillCell_0", "Call Function TillCell"]:
    try:
        n = cge.create_node_from_name(name, unreal.Vector2D(0,0), [])
        unreal.log("create " + name + " -> " + str(n) + (" " + bel.get_node_title(n) if n else ""))
        if n:
            for p in bel.list_all_pins(n):
                unreal.log("  pin " + str(p.get_pin_name()))
            cge.remove_nodes([n])
    except Exception as ex:
        unreal.log_warning(name + ": " + str(ex))

# IMC key dump
imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
mappings = imc.get_editor_property("mappings")
unreal.log("mappings count " + str(len(mappings)))
for m in mappings:
    try:
        a = m.get_editor_property("action")
        k = m.get_editor_property("key")
        unreal.log("map action=" + str(a) + " key=" + str(k))
    except Exception as ex:
        unreal.log_warning(str(ex))

# Key construction
for method in ["E", "Keyboard_E"]:
    try:
        k = unreal.Key()
        k.set_editor_property("key_name", method)
        unreal.log("Key " + method + " -> " + str(k) + " name=" + str(k.get_editor_property("key_name")))
    except Exception as ex:
        unreal.log_warning(str(ex))

# How does Move map look - find IA_Move key style