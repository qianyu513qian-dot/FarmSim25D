# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.EditorAssetLibrary.load_asset(MGR), "TillCell"))
for m in dir(ge):
    if not m.startswith("_"):
        unreal.log("ge." + m)
# try create_node with class path
for name in [
    "Enum Literal",
    "enum literal",
    "Make Enum",
    "Utilities|Enum|Enum Literal",
    "Class|/Script/BlueprintGraph.K2Node_EnumLiteral",
]:
    try:
        n = ge.create_node_from_name(name, unreal.Vector2D(50, 50), [])
        unreal.log("TRY {} -> {}".format(name, n))
        if n:
            unreal.log(" title=" + bel.get_node_title(n))
            for p in bel.list_all_pins(n):
                unreal.log("  " + str(p.get_pin_name()))
            ge.remove_nodes([n])
    except Exception as ex:
        unreal.log_warning("{}: {}".format(name, ex))