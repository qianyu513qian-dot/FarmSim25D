# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestDebugLabels")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
nodes=[]
for n in ge.list_all_nodes():
    t=bel.get_node_title(n)
    try: np=bel.get_node_pos(n); y=np.y; x=np.x
    except Exception: x=y=None
    pins=[]
    if t in ("DrawDebugString","DrawDebugSphere","Event Tick","Event BeginPlay","PrintString","MakeVector"):
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) in ("Text","InString","then","execute","Center","TextLocation"):
                val=None
                try: val=p.get_pin_value()
                except Exception: pass
                links=[bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]
                pins.append({"n":str(p.get_pin_name()),"v":val,"links":links})
    nodes.append({"t":t,"cls":n.get_class().get_name(),"x":x,"y":y,"pins":pins})
# tick chain
chain=[]
for n in ge.list_all_nodes():
    if bel.get_node_title(n)=="Event Tick":
        cur=n; seen=set()
        while cur and id(cur) not in seen:
            seen.add(id(cur))
            then=None
            for p in bel.list_all_pins(cur):
                if str(p.get_pin_name()).lower() in ("then","completed") and "OUTPUT" in str(p.get_pin_direction()):
                    then=p; break
            nxt=[bel.get_node_title(c.get_owning_node()) for c in (then.list_connected_pins() if then else [])]
            chain.append({"t":bel.get_node_title(cur),"to":nxt})
            if then and then.list_connected_pins():
                cur=then.list_connected_pins()[0].get_owning_node()
            else: break
R={"chain":chain,"interesting":[n for n in nodes if n["pins"] or n["t"] in ("Event Tick","Event BeginPlay")],"count":len(nodes)}
open(r"E:\UE\FarmSim25D\Saved\restaurant_restdebug_probe.json","w",encoding="utf-8").write(json.dumps(R,ensure_ascii=False,indent=2))
print(json.dumps(R,ensure_ascii=False,indent=2))