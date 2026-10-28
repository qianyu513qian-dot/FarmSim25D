# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary

def pin_map(n):
    out = {}
    for p in bel.list_all_pins(n):
        name = str(p.get_pin_name())
        connected = []
        for c in p.list_connected_pins():
            on = c.get_owning_node()
            connected.append(bel.get_node_title(on)+"."+str(c.get_pin_name()))
        out[name] = {"dir":str(p.get_pin_direction()), "val":p.get_pin_value(), "to":connected}
    return out

# Character IA
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia = None
for n in cge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_EnhancedInputAction" and "IA_Interact" in bel.get_node_title(n):
        ia = n
ia_map = pin_map(ia) if ia else {}

# Manager detailed pins for key nodes
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
detail = []
for n in mge.list_all_nodes():
    t = bel.get_node_title(n)
    c = n.get_class().get_name()
    if c in ("K2Node_CustomEvent","K2Node_Event","K2Node_IfThenElse","K2Node_VariableSet","K2Node_VariableGet") or "Print" in t or "Contains" in t or "GetAll" in t or "Get Display" in t or "Handle" in t or "Seat" in t or "Clear" in t or "For Each" in t or "Append" in t or "GetDisplay" in t or t.startswith("Get "):
        detail.append({"t":t,"c":c,"pins":pin_map(n)})

# Framework relevant
fw = open(r"E:\UE\FarmSim25D\Docs\Restaurant_Framework.md",encoding="utf-8").read()
# dump full for knife2 sections
lines = fw.splitlines()
idx = [i for i,l in enumerate(lines) if any(k in l for k in ["开业","刷客","交互","Manager","HandlePlayer","SeatGuest","17:00","23:00","RestInteract","bIsOpen"])]
snippets = []
for i in idx[:40]:
    snippets.append(f"{i}: {lines[i]}")

# list previous scripts
import os
scripts = [f for f in os.listdir(r"E:\UE\FarmSim25D\Content\Python") if "knife2" in f.lower() or "restaurant" in f.lower()]

# table BP vars
tbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
# try common vars
for vn in ["bOccupied","SeatState","CurrentOrder","bHasGuest","OrderName"]:
    g = tge.add_get_member_variable_node(vn)
    print("table var", vn, g is not None)
    if g: tge.remove_nodes([g])

# Interactable parent
ibp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantInteractable")
ige = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(ibp)) if ibp else None
i_nodes = [{"t":bel.get_node_title(n),"c":n.get_class().get_name()} for n in ige.list_all_nodes()] if ige else []
for vn in ["InteractLabel","RestaurantInteract"]:
    if ige:
        g = ige.add_get_member_variable_node(vn)
        print("interact var", vn, g is not None)
        if g: ige.remove_nodes([g])

rep = {"ia_map":ia_map,"mgr_detail":detail,"fw_lines":snippets,"scripts":scripts,"i_nodes":i_nodes}
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_state.json","w",encoding="utf-8").write(json.dumps(rep,indent=2,ensure_ascii=False))
print("IA Started ->", ia_map.get("Started"))
print("mgr nodes", len(detail))
print("scripts", scripts)
print("---FW---")
print("\n".join(snippets[:50]))
