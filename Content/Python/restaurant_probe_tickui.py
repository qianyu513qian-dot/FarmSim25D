# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

mbp=unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
R={"calls":[], "tick_detail":[], "refresh":None, "ensure":None}
for n in mge.list_all_nodes():
    t=title(n)
    if "RefreshOrderUI" in t or "EnsureOrderUI" in t or "RestaurantTick" in t:
        R["calls"].append({"title":t, "class":n.get_class().get_name(),
            "then":[title(c.get_owning_node()) for c in ((find_pin(n,"then","Output").list_connected_pins() or []) if find_pin(n,"then","Output") else [])],
            "exec_from":[title(c.get_owning_node()) for c in ((find_pin(n,"execute","Input").list_connected_pins() or []) if find_pin(n,"execute","Input") else [])],
        })
# Event tick node fully
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "Tick" in title(n):
        thenp=find_pin(n,"then","Output")
        linked=thenp.list_connected_pins() if thenp else []
        for c in linked or []:
            cn=c.get_owning_node()
            R["tick_detail"].append({"to":title(cn),"class":cn.get_class().get_name(),"pins":[str(p.get_pin_name()) for p in bel.list_all_pins(cn)]})

# CustomEvent RestaurantTick pins
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="RestaurantTick":
        R["rt_pins"]=[str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(n)]
        thenp=find_pin(n,"then","Output")
        R["rt_then_links"]=[title(c.get_owning_node()) for c in (thenp.list_connected_pins() or [])] if thenp else None

open(r"E:\UE\FarmSim25D\Saved\restaurant_probe_tickui.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False))
print(json.dumps(R,indent=2,ensure_ascii=False)[:7000])
