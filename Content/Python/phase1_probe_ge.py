# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary

bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = bel.get_graph_editor(bp) if hasattr(bel, "get_graph_editor") else None
unreal.log("bel.get_graph_editor=" + str(ge))

# try on BlueprintGraphEditor static?
try:
    ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bp)
    unreal.log("BGE.get_graph_editor=" + str(ge2))
except Exception as ex:
    unreal.log_warning("BGE.get: " + str(ex))

# find methods that take blueprint
for m in ["get_graph_editor", "get_graph_editor_by_name", "get_graph"]:
    if hasattr(unreal.BlueprintGraphEditor, m):
        unreal.log("has " + m)

# Try open/edit
try:
    # list_graphs
    names = bel.list_graph_names(bp)
    unreal.log("graphs=" + str(names))
except Exception as ex:
    unreal.log_warning(str(ex))

# Instantiate editor via subsystem?
subs = [x for x in dir(unreal) if "Blueprint" in x and "Sub" in x]
unreal.log("subs=" + str(subs))

# Try: unreal.BlueprintEditorLibrary.find_event_graph then somehow get editor
eg = bel.find_event_graph(bp)
unreal.log("eg=" + str(eg))

# Check if Blueprint has get_graph_editor
for m in dir(bp):
    if "graph" in m.lower() or "editor" in m.lower():
        unreal.log("bp." + m)

# Try AssetEditorSubsystem open
try:
    aes = unreal.AssetEditorSubsystem()
    # might already be open
    unreal.log("aes ok")
except Exception as ex:
    unreal.log_warning(str(ex))

# Direct construct BlueprintGraphEditor?
try:
    help_doc = unreal.BlueprintGraphEditor.get_graph_editor.__doc__ if hasattr(unreal.BlueprintGraphEditor, "get_graph_editor") else None
    unreal.log("doc=" + str(help_doc))
except Exception as ex:
    unreal.log_warning(str(ex))

# Inspect static methods more carefully via call_method patterns - try get_default_object
try:
    bge_cdo = unreal.BlueprintGraphEditor.get_default_object()
    unreal.log("cdo=" + str(bge_cdo))
except Exception as ex:
    unreal.log_warning("cdo " + str(ex))

# list_available_nodes needs instance - search how to create
# Maybe: unreal.BlueprintEditorLibrary.create_and_edit? 
for m in dir(bel):
    if "edit" in m.lower() or "open" in m.lower() or "graph_editor" in m.lower():
        unreal.log("bel." + m)