# -*- coding: utf-8 -*-
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()
def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None
# Find EnsureOrderUI custom and who calls it
for n in mge.list_all_nodes():
    t=title(n)
    if t in ("EnsureOrderUI","RefreshOrderUI") and n.get_class().get_name() in ("K2Node_CustomEvent","K2Node_CallFunction"):
        ep=find_pin(n,"execute","Input")
        preds=[title(c.get_owning_node()) for c in (ep.list_connected_pins() if ep else [])] if ep else []
        print(t, n.get_class().get_name(), "preds", preds)
# Any orphaned call that looked like BeginPlay chain (Create Widget etc)
for n in mge.list_all_nodes():
    t=title(n)
    if t in ("Create Widget","Add to Viewport","AddToViewport","EnsureOrderUI"):
        ep=find_pin(n,"execute","Input")
        preds=[title(c.get_owning_node()) for c in (ep.list_connected_pins() if ep else [])] if ep else []
        print("node", t, "preds", preds)
