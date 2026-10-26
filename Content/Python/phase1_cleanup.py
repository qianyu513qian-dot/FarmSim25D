# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

bp = unreal.EditorAssetLibrary.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
to_remove = []
for n in ge.list_all_nodes():
    title = bel.get_node_title(n)
    # remove junk "Seconds * FrameRate" promotable if present
    if "Seconds" in title and "FrameRate" in title:
        to_remove.append(n)
        unreal.log("remove " + title)
if to_remove:
    ge.remove_nodes(to_remove)
    unreal.log("removed " + str(len(to_remove)))

# verify ForLoop LastIndex connections
for n in ge.list_all_nodes():
    if "For Loop" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if "LastIndex" in str(p.get_pin_name()):
                cps = list(p.list_connected_pins())
                unreal.log("LastIndex links=" + str(len(cps)) + " " + str([c.get_owning_node().get_name() for c in cps]))

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)

# remove orphan GetActorOfClass on character
cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
begin = cge.find_event_node("ReceiveBeginPlay")
orphans = []
for n in cge.list_all_nodes():
    if bel.get_node_title(n) == "GetActorOfClass":
        exe = bel.find_execute_pin(n)
        linked = list(exe.list_connected_pins()) if exe else []
        from_begin = any(x.get_owning_node() == begin for x in linked)
        if not from_begin:
            orphans.append(n)
            unreal.log("orphan remove " + n.get_name())
if orphans:
    cge.remove_nodes(orphans)
bel.compile_blueprint(cbp)
unreal.EditorAssetLibrary.save_asset(CHAR)
unreal.log("cleanup done")