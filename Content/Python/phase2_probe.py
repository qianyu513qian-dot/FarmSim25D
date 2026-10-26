import unreal
bel = unreal.BlueprintEditorLibrary
unreal.log("has add_function_graph " + str(hasattr(bel, "add_function_graph")))
attrs = [a for a in dir(bel) if ("func" in a.lower() or "graph" in a.lower() or "member" in a.lower() or "event" in a.lower() or "node" in a.lower())]
unreal.log("bel: " + str(attrs))
ge_cls = unreal.BlueprintGraphEditor
gattrs = [a for a in dir(ge_cls) if not a.startswith("_")]
unreal.log("ge: " + str(gattrs))
unreal.log("Input factories: " + str([a for a in dir(unreal) if "Factory" in a and "Input" in a]))
unreal.log("AssetTools create: check AssetToolsHelpers")
# Try open mgr and list methods on graph editor instance
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
unreal.log("ge instance methods sample: " + str([a for a in dir(ge) if "add" in a.lower() or "create" in a.lower() or "func" in a.lower()][:60]))
# list function graphs
try:
    unreal.log("function_graphs: " + str([str(g.get_name()) for g in bp.function_graphs]))
except Exception as ex:
    unreal.log_warning(str(ex))