# -*- coding: utf-8 -*-
"""Probe OpenSign components, Manager open/close nodes, SellCrops money add, IMC key strings."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
R={"steps":[]}
def log(m):
    unreal.log("[P3] "+str(m)); print("[P3] "+str(m)); R["steps"].append(str(m))
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
def walk_then(start, max_d=50):
    thenp=find_pin(start,"then","Output")
    queue=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=[]; ids=set()
    while queue:
        cur,d=queue.pop(0)
        if id(cur) in ids or d>max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(),d+1))
    return seen

# OpenSign instance components in level
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if a.get_actor_label()!="Restaurant_OpenSign":
        continue
    comps=[]
    for c in a.get_components_by_class(unreal.ActorComponent.static_class()):
        comps.append(c.get_name()+":"+c.get_class().get_name())
    R["opensign_live_comps"]=comps
    tags=list(a.tags) if hasattr(a,"tags") else []
    R["opensign_tags"]=[str(t) for t in tags]
    log("OpenSign comps="+str(comps)+" tags="+str(R["opensign_tags"]))

# RestMark_OpenSign
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor.static_class()):
    if "RestMark_OpenSign" in a.get_actor_label():
        tags=list(a.tags) if hasattr(a,"tags") else []
        mesh=a.static_mesh_component
        mat=None
        try:
            mat=str(mesh.get_material(0))
        except: pass
        R["restmark"]={"tags":[str(t) for t in tags],"mat":mat,"scale":str(a.get_actor_scale3d())}
        log("RestMark: "+str(R["restmark"]))

# Manager HandlePlayerE full chain
mbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="HandlePlayerE":
        chain=[title(x)+"|"+x.get_class().get_name() for x in walk_then(n,60)]
        R["HandlePlayerE"]=chain
        log("HandlePlayerE len="+str(len(chain)))
    if n.get_class().get_name()=="K2Node_Event" and "Tick" in title(n):
        chain=[title(x) for x in walk_then(n,80)]
        R["Tick"]=chain[:80]
        log("Tick len="+str(len(chain)))

# SellCrops function body
cbp=unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sg=bel.find_graph(cbp,"SellCrops")
if sg:
    sge=unreal.BlueprintGraphEditor.get_graph_editor(sg)
    R["SellCrops_nodes"]=[title(n) for n in sge.list_all_nodes()]
    log("SellCrops: "+str(R["SellCrops_nodes"]))

# How to create InputAction - look at existing asset properties
ia=unreal.load_asset("/Game/TopDown/Input/Actions/IA_Interact")
R["IA_Interact_class"]=ia.get_class().get_name() if ia else None
try:
    R["IA_value_type"]=str(ia.get_editor_property("value_type"))
except Exception as e:
    R["IA_vt_err"]=str(e)

# IMC DefaultKeyMappings
imc=unreal.load_asset("/Game/TopDown/Input/IMC_Default")
try:
    dkm=imc.get_editor_property("default_key_mappings")
    mapped=[]
    for m in dkm:
        action=m.get_editor_property("action")
        key=m.get_editor_property("key")
        # key has key_name
        kn=None
        try: kn=key.get_editor_property("key_name")
        except:
            try: kn=str(key)
            except: kn="?"
        mapped.append({"action": action.get_name() if action else None, "key": str(kn)})
    R["imc_keys"]=mapped
    log("keys: "+str(mapped))
except Exception as e:
    R["imc_dkm_err"]=str(e)

# Factory for InputAction
try:
    factory_names=[c for c in dir(unreal) if "InputAction" in c or "InputMapping" in c]
    R["input_factories"]=factory_names
except Exception as e:
    R["fact_err"]=str(e)

# phase_fix_grow_imc content peek via reading isn't available; check IA_Grow binding
# Can we call restore_clock from BP?
try:
    n=mge.add_call_function_node("/Script/FarmSim25D.FarmClock:RestoreClock")
    log("RestoreClock node: "+(title(n) if n else "None"))
    if n: mge.remove_nodes([n])
except Exception as e:
    log("RestoreClock fail "+str(e))
try:
    n=mge.add_call_function_node("/Script/FarmSim25D.FarmClock:restore_clock")
    log("restore_clock node: "+(title(n) if n else "None"))
    if n: mge.remove_nodes([n])
except Exception as e:
    log("restore_clock fail "+str(e))
for path in [
 "/Script/FarmSim25D.FarmClock:GetDisplayMinutes",
 "/Script/FarmSim25D.FarmClock:AdvanceClock",
 "/Script/FarmSim25D.FarmClock:CaptureClock",
]:
    try:
        n=mge.add_call_function_node(path)
        log("OK "+path+" -> "+(title(n) if n else "None"))
        if n: mge.remove_nodes([n])
    except Exception as e:
        log("FAIL "+path+" "+str(e))

out=unreal.Paths.project_saved_dir()+"restaurant_probe3.json"
with open(out,"w",encoding="utf-8") as f: json.dump(R,f,indent=2,ensure_ascii=False)
log("WROTE "+out)
