# -*- coding: utf-8 -*-
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
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
def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None
mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ev=find_custom(mge,"PrintDayEndSummary")
# BFS all nodes from ev
seen=set(); q=[ev]; nodes=[]
while q:
    cur=q.pop(0)
    if not cur or id(cur) in seen: continue
    seen.add(id(cur)); nodes.append(cur)
    for p in bel.list_all_pins(cur):
        for c in (p.list_connected_pins() or []):
            q.append(c.get_owning_node())
R=[]
for n in nodes:
    info={"t":title(n),"cls":n.get_class().get_name(),"pins":{}}
    for p in bel.list_all_pins(n):
        pn=str(p.get_pin_name())
        try: pv=str(p.get_pin_value()) if hasattr(p,"get_pin_value") else ""
        except: pv=""
        links=[title(c.get_owning_node()) for c in (p.list_connected_pins() or [])]
        if pv or links:
            info["pins"][pn]={"v":pv,"L":links}
    R.append(info)
print(json.dumps(R,indent=2,ensure_ascii=False,default=str)[:6000])
