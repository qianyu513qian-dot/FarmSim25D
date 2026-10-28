# -*- coding: utf-8 -*-
"""Deep probe: stove tick Set CookTimeLeft links; RestaurantTick; ReceiveSalad1; PrintString pins; ClearHeld."""
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

def walk(start, limit=30):
    chain=[]; seen=set(); q=[start]
    while q and len(chain)<limit:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); chain.append(title(cur))
        for pn in ("then","else","LoopBody","Completed"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
    return chain

def pin_names(path_fn):
    # create temp? just inspect an existing PrintString
    return None

R={}
# stove
bp=unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
tick=None
for n in ge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "Tick" in title(n):
        tick=n
R["stove_tick"]=walk(tick) if tick else []
# find Set CookTimeLeft that is in tick (linked from float-float / subtract)
sets=[]
for n in ge.list_all_nodes():
    if title(n)=="Set CookTimeLeft":
        thenp=find_pin(n,"then","Output")
        ex=find_pin(n,"execute","Input")
        sets.append({
            "then":[title(c.get_owning_node()) for c in (thenp.list_connected_pins() or [])] if thenp else [],
            "exec_from":[title(c.get_owning_node()) for c in (ex.list_connected_pins() or [])] if ex else [],
        })
R["stove_set_ctl"]=sets
# PrintString pin names
for n in ge.list_all_nodes():
    if title(n)=="PrintString":
        R["print_pins"]=[str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(n)]
        break

# mgr
mbp=unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
rt=None; ch=None; rs1=None
for n in mge.list_all_nodes():
    t=title(n); c=n.get_class().get_name()
    if c=="K2Node_CustomEvent" and t=="RestaurantTick": rt=n
    if c=="K2Node_CustomEvent" and t=="ClearHeld": ch=n
    if c=="K2Node_CustomEvent" and t=="ReceiveSalad1": rs1=n
R["RestaurantTick"]=walk(rt,40) if rt else []
R["ClearHeld"]=walk(ch,20) if ch else []
R["ReceiveSalad1"]=walk(rs1,25) if rs1 else []

# Event Tick then
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "Tick" in title(n):
        R["mgr_tick_then"]=[title(c.get_owning_node()) for c in (find_pin(n,"then","Output").list_connected_pins() or [])]
# DrawDebugString path exists?
try:
    n=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
    R["has_DrawDebugString"]=n is not None
    if n:
        R["dds_pins"]=[str(p.get_pin_name()) for p in bel.list_all_pins(n)]
        mge.remove_nodes([n])
except Exception as e:
    R["dds_err"]=str(e)
try:
    n=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugSphere")
    R["has_DrawDebugSphere"]=n is not None
    if n:
        R["dsp_pins"]=[str(p.get_pin_name()) for p in bel.list_all_pins(n)]
        mge.remove_nodes([n])
except Exception as e:
    R["dsp_err"]=str(e)
try:
    n=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugBox")
    R["has_DrawDebugBox"]=n is not None
    if n: mge.remove_nodes([n])
except Exception as e:
    R["ddb_err"]=str(e)

open(r"E:\UE\FarmSim25D\Saved\restaurant_probe_held_cook2.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False))
print(json.dumps(R,indent=2,ensure_ascii=False)[:9000])
