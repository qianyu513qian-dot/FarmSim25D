# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
# list available with empty context
try:
    avail = ge.list_available_nodes([])
    hits = [a for a in avail if "ultip" in str(a).lower() or "*" in str(a) or "Integer" in str(a)]
    unreal.log("hits=" + str(len(hits)))
    for h in hits[:40]:
        unreal.log(str(h))
except Exception as ex:
    unreal.log_warning(str(ex))

# try create with different names
names = [
    "Utilities|Operators|Multiply",
    "Math|Integer|*",
    "Math|Integer|Multiply",
    "Utilities|Operators|*",
    "integer * integer",
    "Utilities|Int|Multiply",
]
for n in names:
    node = ge.create_node_from_name(n, unreal.Vector2D(0, 0), [])
    unreal.log("try {} -> {}".format(n, node))

unreal.log("add_event_override doc=" + str(bel.add_event_override.__doc__))

# character events
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
unreal.log("char events sample:")
for e in bel.list_events(cbp):
    if "Begin" in str(e) or "Tick" in str(e):
        unreal.log(str(e))
# existing nodes
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Begin" in t or "Tick" in t or "Get Actor" in t:
        unreal.log("char node: " + t + " " + n.get_name())