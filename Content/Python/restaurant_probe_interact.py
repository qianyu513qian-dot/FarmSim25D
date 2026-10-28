# -*- coding: utf-8 -*-
"""Dump IA_Interact downstream on BP_TopDownCharacter (titles only)."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
# find event graph
graphs = []
try:
    graphs = list(bp.get_editor_property("ubergraph_pages"))
except Exception as e:
    unreal.log(str(e))
# BlueprintEditorLibrary find_graph
eg = None
for name in ("EventGraph", "Event Graph"):
    try:
        eg = bel.find_graph(bp, name)
        if eg: break
    except Exception:
        pass
unreal.log("eg="+str(eg))
nodes_info=[]
if eg:
    # try BlueprintGraphEditor
    try:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
        nodes = list(ge.list_all_nodes())
    except Exception as e:
        unreal.log("ge fail "+str(e))
        nodes=[]
        try:
            # alternate
            for n in unreal.EdGraphLibrary.get_all_nodes(eg):
                nodes.append(n)
        except Exception as e2:
            unreal.log("alt "+str(e2))
    ia=None
    for n in nodes:
        try:
            t=bel.get_node_title(n)
        except Exception:
            t=str(n)
        nodes_info.append(t)
        if "IA_Interact" in str(t):
            ia=n
    # BFS from IA_Interact started
    chain=[]
    if ia:
        from collections import deque
        q=deque([ia]); seen=set(); seen.add(id(ia))
        while q and len(chain)<40:
            n=q.popleft()
            try: t=bel.get_node_title(n)
            except: t="?"
            chain.append(t)
            for p in bel.list_all_pins(n):
                if "output" not in str(p.get_pin_direction()).lower(): continue
                for c in p.list_connected_pins():
                    on=c.get_owning_node()
                    if id(on) not in seen:
                        seen.add(id(on)); q.append(on)
    out={"node_count":len(nodes_info),"ia_chain":chain,"sample_titles":[t for t in nodes_info if any(k in str(t) for k in ("Interact","Till","Print","Branch","Sleep","Money","Restaurant"))][:40]}
else:
    out={"error":"no event graph"}
open(r"E:\UE\FarmSim25D\Saved\interact_dump.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
