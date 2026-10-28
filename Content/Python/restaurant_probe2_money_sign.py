# -*- coding: utf-8 -*-
"""Deeper probe: OpenSign RestaurantInteract graph, sell money pattern, IMC mappings."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {"steps":[]}
def log(m):
    unreal.log("[PROBE2] "+str(m)); print("[PROBE2] "+str(m)); R["steps"].append(str(m))
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
def walk_then(start, max_d=40):
    thenp = find_pin(start, "then", "Output")
    queue = [(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=[]; ids=set()
    while queue:
        cur,d=queue.pop(0)
        if id(cur) in ids or d>max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d+1))
    return seen

# List ALL graphs on OpenSign and Interactable
for path in ["/Game/Farm/Restaurant/BP_RestaurantOpenSign","/Game/Farm/Restaurant/BP_RestaurantInteractable"]:
    bp=unreal.load_asset(path)
    glist=[]
    # Ubergraph + function graphs via asset registry of Blueprint
    try:
        # Blueprint.UbergraphPages / FunctionGraphs
        for attr in ("ubergraph_pages","function_graphs","macro_graphs","event_graphs"):
            if hasattr(bp, attr):
                pages=getattr(bp, attr)
                glist.append(attr+":"+str([str(p.get_name()) if hasattr(p,"get_name") else str(p) for p in (pages or [])]))
    except Exception as e:
        glist.append("attr_err:"+str(e))
    # try EditorAssetLibrary / BlueprintEditorLibrary helpers
    for gname in ("EventGraph","RestaurantInteract","UserConstructionScript","ApplySignVisual","SetOpenVisual"):
        try:
            g=bel.find_graph(bp, gname)
            glist.append(("FOUND" if g else "MISS")+":"+gname)
            if g:
                ge=unreal.BlueprintGraphEditor.get_graph_editor(g)
                nodes=[title(n) for n in ge.list_all_nodes()]
                R[path.split("/")[-1]+"_"+gname]=nodes[:80]
        except Exception as e:
            glist.append("ERR:"+gname+":"+str(e))
    R[path.split("/")[-1]+"_graphs"]=glist
    log(path.split("/")[-1]+" "+str(glist))

# Sell crops money add pattern on character
cbp=unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
sell_nodes=[]
for n in cge.list_all_nodes():
    t=title(n)
    if "Sell" in t or "Money" in t or "UpdateFarmHUD" in t:
        sell_nodes.append(t+"|"+n.get_class().get_name())
R["char_moneyish"]=sell_nodes[:60]

# Find EnhancedInputAction IA_SellCrops and walk
for n in cge.list_all_nodes():
    if "IA_SellCrops" in title(n) and "EnhancedInput" in n.get_class().get_name():
        chain=[title(x) for x in walk_then(n)]
        # also check Started pin
        started=find_pin(n,"Started","Output") or find_pin(n,"Triggered","Output")
        if started:
            outs=[c.get_owning_node() for c in (started.list_connected_pins() or [])]
            chains=[]
            for o in outs:
                chains.append([title(o)]+[title(x) for x in walk_then(o)])
            R["IA_SellCrops_chains"]=chains
        R["IA_SellCrops_then"]=chain
        log("SellCrops chain: "+str(R.get("IA_SellCrops_chains") or chain))

# IMC_Default: list mappings
imc=unreal.load_asset("/Game/TopDown/Input/IMC_Default")
try:
    mappings=imc.get_editor_property("mappings")
    mapped=[]
    for m in mappings:
        try:
            action=m.get_editor_property("action")
            key=m.get_editor_property("key")
            mapped.append({"action": str(action.get_name() if action else None), "key": str(key)})
        except Exception as e:
            mapped.append({"err":str(e), "raw":str(m)})
    R["imc_mappings"]=mapped
    log("IMC mappings: "+str(mapped))
except Exception as e:
    R["imc_err"]=str(e)

# OpenSign SCS - use SubobjectDataSubsystem or SimpleConstructionScript
osbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantOpenSign")
try:
    scs=osbp.simple_construction_script
    nodes=[]
    if scs:
        for n in scs.get_all_nodes():
            nodes.append(n.get_variable_name()+"|"+str(n.get_component_class().get_name() if n.get_component_class() else None))
    R["opensign_scs"]=nodes
    log("opensign scs: "+str(nodes))
except Exception as e:
    R["opensign_scs_err"]=str(e)

# Parent interactable SCS
ibp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantInteractable")
try:
    scs=ibp.simple_construction_script
    nodes=[]
    if scs:
        for n in scs.get_all_nodes():
            nodes.append(n.get_variable_name()+"|"+str(n.get_component_class().get_name() if n.get_component_class() else None))
    R["interactable_scs"]=nodes
except Exception as e:
    R["interactable_scs_err"]=str(e)

# Look for RestDebug / label cubes on OpenSign in level
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
sign_info=[]
for a in actors:
    lab=a.get_actor_label()
    if "OpenSign" in lab or "RestLabel" in lab or "Restaurant_" in lab:
        sign_info.append({"label":lab, "class":a.get_class().get_name(), "loc":str(a.get_actor_location())})
R["level_restaurant_actors"]=sign_info
log("level actors: "+str(len(sign_info)))

out=unreal.Paths.project_saved_dir()+"restaurant_probe2.json"
with open(out,"w",encoding="utf-8") as f: json.dump(R,f,indent=2,ensure_ascii=False)
log("WROTE "+out)
