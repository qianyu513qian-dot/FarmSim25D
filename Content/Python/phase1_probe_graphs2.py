# -*- coding: utf-8 -*-
import unreal

def list_methods(cls, needle=""):
    ms = [m for m in dir(cls) if not m.startswith("_") and (needle.lower() in m.lower() if needle else True)]
    unreal.log(str(cls) + (" ["+needle+"]" if needle else "") + ": " + ", ".join(ms[:80]))

list_methods(unreal.BlueprintEditorLibrary, "graph")
list_methods(unreal.BlueprintEditorLibrary, "node")
list_methods(unreal.BlueprintEditorLibrary, "pin")
list_methods(unreal.BlueprintEditorLibrary, "event")
list_methods(unreal.BlueprintEditorLibrary, "variable")
list_methods(unreal.BlueprintGraphEditor)
list_methods(unreal.BlueprintGraphPinLibrary)
list_methods(unreal.BlueprintGraphPin)

# try find event graph
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
try:
    eg = unreal.BlueprintEditorLibrary.find_event_graph(bp)
    unreal.log("event_graph=" + str(eg) + " name=" + (eg.get_name() if eg else "None"))
    if eg:
        nodes = eg.nodes if hasattr(eg, "nodes") else eg.get_editor_property("nodes")
        unreal.log("nodes=" + str(len(list(nodes))))
        for n in list(nodes)[:20]:
            unreal.log(" node " + n.get_class().get_name() + " " + n.get_name())
except Exception as ex:
    unreal.log_warning("find_event_graph: " + str(ex))

# try ubergraph via reflection
try:
    pages = bp.get_editor_property("ubergraph_pages")
    unreal.log("ubergraph_pages=" + str(pages))
except Exception as ex:
    unreal.log_warning("uber: " + str(ex))