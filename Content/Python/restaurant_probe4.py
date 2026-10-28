# -*- coding: utf-8 -*-
"""Probe Set bIsOpenBusiness sites, RestaurantTick, FarmClockState make, Cast Character path."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
R={"steps":[]}
def log(m):
    unreal.log("[P4] "+str(m)); print("[P4] "+str(m)); R["steps"].append(str(m))
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

mbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# All Set bIsOpenBusiness and their predecessors via execute input
sets=[]
for n in mge.list_all_nodes():
    t=title(n)
    if t=="Set bIsOpenBusiness" or (t.startswith("Set ") and "bIsOpenBusiness" in t):
        val=find_pin(n,"bIsOpenBusiness","Input")
        v=val.get_pin_value() if val else "?"
        # who calls this
        ep=find_pin(n,"execute","Input")
        preds=[]
        if ep:
            for c in ep.list_connected_pins() or []:
                preds.append(title(c.get_owning_node()))
        thenp=find_pin(n,"then","Output")
        succs=[]
        if thenp:
            for c in thenp.list_connected_pins() or []:
                succs.append(title(c.get_owning_node()))
        sets.append({"val":v,"preds":preds,"succs":succs,"y":int(bel.get_node_pos(n).y) if hasattr(bel,"get_node_pos") else 0})
R["set_open"]=sets
log("Set bIsOpenBusiness count="+str(len(sets))+" "+str(sets))

# RestaurantTick custom
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="RestaurantTick":
        # BFS all exec
        thenp=find_pin(n,"then","Output")
        queue=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
        seen=[]; ids=set()
        while queue:
            cur,d=queue.pop(0)
            if id(cur) in ids or d>80: continue
            ids.add(id(cur)); seen.append(title(cur))
            for pn in ("then","else","Completed","LoopBody"):
                tp=find_pin(cur,pn,"Output")
                if tp:
                    for c in tp.list_connected_pins() or []:
                        queue.append((c.get_owning_node(),d+1))
        R["RestaurantTick"]=seen
        log("RestaurantTick: "+str(seen[:50]))

# Try MakeFarmClockState / struct
for path in [
 "/Script/FarmSim25D.FarmClockState",
]:
    pass
# try add make struct node
try:
    # K2Node_MakeStruct
    n=mge.create_node_from_name("Make FarmClockState", unreal.Vector2D(0,0))
    log("create Make FarmClockState: "+str(n)+" "+(title(n) if n else ""))
    if n: mge.remove_nodes([n])
except Exception as e:
    log("MakeStruct fail "+str(e))

# Cast to character
cbp=unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
gen=cbp.generated_class()
log("char generated="+str(gen))
for path in [
 "/Script/Engine.GameplayStatics:GetPlayerPawn",
 "/Script/Engine.GameplayStatics:GetPlayerCharacter",
 "/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:UpdateFarmHUD",
]:
    try:
        n=mge.add_call_function_node(path)
        log("OK "+path+" -> "+(title(n) if n else "None"))
        if n: mge.remove_nodes([n])
    except Exception as e:
        log("FAIL "+path+" "+str(e))

# Cast node
try:
    n=mge.add_cast_node(gen) if hasattr(mge,"add_cast_node") else None
    log("add_cast_node "+str(n))
    if n: mge.remove_nodes([n])
except Exception as e:
    log("cast_node err "+str(e))
# try create_node_from_name Cast
for cname in ["Cast To BP_TopDownCharacter_C","Cast To BP_TopDownCharacter"]:
    try:
        n=mge.create_node_from_name(cname, unreal.Vector2D(100,100))
        log("create "+cname+" -> "+str(n)+" "+(title(n) if n else ""))
        if n: mge.remove_nodes([n])
    except Exception as e:
        log("create fail "+cname+" "+str(e))

# Material create API quick
try:
    mat_factory=unreal.MaterialFactoryNew()
    log("MaterialFactoryNew ok")
except Exception as e:
    log(str(e))

# Existing rest mark materials
mats=unreal.EditorAssetLibrary.list_assets("/Game/Farm/Restaurant/Labels", True, False)
R["label_assets"]=mats
log("labels: "+str(mats))

# OpenSign Handle path: dump ALL nodes with OpenSign/1020/1380/Print in manager
interesting=[]
for n in mge.list_all_nodes():
    t=title(n)
    if any(k in t for k in ("OpenSign","1020","1380","OPEN","CLOSE","Sign","GetDisplayMinutes","RestaurantTick","Apply")):
        interesting.append(t)
    # PrintString defaults
    if t=="PrintString":
        inp=find_pin(n,"InString","Input") or find_pin(n,"String","Input")
        if inp:
            v=inp.get_pin_value() or ""
            if "SIGN" in v.upper() or "OPEN" in v.upper() or "CLOSE" in v.upper() or "17" in v or "Restaurant" in v:
                interesting.append("Print:"+v[:80])
R["interesting"]=interesting
log("interesting="+str(interesting[:60]))

out=unreal.Paths.project_saved_dir()+"restaurant_probe4.json"
with open(out,"w",encoding="utf-8") as f: json.dump(R,f,indent=2,ensure_ascii=False)
log("WROTE "+out)
