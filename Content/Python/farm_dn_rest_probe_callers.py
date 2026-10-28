# -*- coding: utf-8 -*-
import unreal, json
REPORT={}
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

# SeatGuest / ApplySignOpen / Set GuestTimer callers
for target in ("SeatGuest","ApplySignOpen","ApplySignClosed","Set GuestTimer","ResetDayCounters","PrintDayEndSummary"):
    callers=[]
    for n in mge.list_all_nodes():
        if title(n)!=target and not (target.startswith("Set ") and title(n)==target):
            if title(n)!=target: continue
        exe=find_pin(n,"execute","Input")
        if exe:
            froms=[title(c.get_owning_node()) for c in (exe.list_connected_pins() or [])]
            callers.append({"cls":n.get_class().get_name(),"from":froms})
        elif n.get_class().get_name()=="K2Node_CustomEvent":
            callers.append({"cls":"CustomEvent","from":[]})
    REPORT[target]=callers

# How open works: find Branch before Set bIsOpenBusiness true - walk parents more carefully via ALL exec pins including CustomEvent then reverse
# Find nodes that mention OpenSign tag
tags=[]
for n in mge.list_all_nodes():
    for p in bel.list_all_pins(n):
        try: d=str(p.get_default_as_string())
        except: d=""
        if d and ("OpenSign" in d or "RestMark" in d or "RestInteract" in d):
            tags.append({"node":title(n),"pin":str(p.get_pin_name()),"def":d})
REPORT["tags"]=tags

# Event BeginPlay chain
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in title(n):
        thenp=find_pin(n,"then","Output")
        chain=[]; cur_links=list(thenp.list_connected_pins() or []) if thenp else []
        seen=set()
        q=[c.get_owning_node() for c in cur_links]
        while q:
            cur=q.pop(0)
            if id(cur) in seen: continue
            seen.add(id(cur)); chain.append(title(cur))
            for pn in ("then","else","Completed","LoopBody"):
                tp=find_pin(cur,pn,"Output")
                if tp:
                    for c in tp.list_connected_pins() or []:
                        q.append(c.get_owning_node())
        REPORT["beginplay"]=chain[:40]

open(r"E:\UE\FarmSim25D\Saved\rest_probe_callers.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False)[:5000])
