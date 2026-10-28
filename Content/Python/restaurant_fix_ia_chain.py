# -*- coding: utf-8 -*-
"""Fix IA_Interact Started -> GetPlayerPawn -> GetAllActorsWithTag exec chain."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
out={}

def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower(); hits=[]
    for p in bel.list_all_pins(node):
        pn=str(p.get_pin_name())
        if substr in pn.lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                hits.append(p)
    return hits[0] if hits else None

def dump(n):
    if not n: return None
    return {"title":bel.get_node_title(n),"pins":[
        {"n":str(p.get_pin_name()),"d":str(p.get_pin_direction()),
         "c":[(bel.get_node_title(cp.get_owning_node()),str(cp.get_pin_name())) for cp in p.list_connected_pins()]}
        for p in bel.list_all_pins(n)]}

ia=gat=pawn=fe=till=None
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "IA_Interact" in t: ia=n
    if t=="GetAllActorsWithTag": gat=n
    if t in ("Get Player Pawn","GetPlayerPawn"): pawn=n
    if "ForEachLoop" in t or t=="For Each Loop": fe=n
    if t=="TillSoil": till=n

out["before"]={"ia":dump(ia),"pawn":dump(pawn),"gat":dump(gat),"fe":dump(fe)}

# Force reconnect
started=find_pin(ia,"Started","Output")
pawn_exec=find_pin(pawn,"execute","Input")
pawn_then=find_pin(pawn,"then","Output")
gat_exec=find_pin(gat,"execute","Input")

# If pawn missing recreate
if pawn is None:
    pawn=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(pawn, unreal.IntPoint(-2000,1050))
    pawn_exec=find_pin(pawn,"execute","Input")
    pawn_then=find_pin(pawn,"then","Output")
    try: find_pin(pawn,"PlayerIndex","Input").set_default_value("0")
    except Exception: pass

# Break and reconnect
for pin in (started, pawn_exec, gat_exec):
    if not pin: continue
    try: bel.break_pin_links(pin)
    except Exception:
        for cp in list(pin.list_connected_pins()):
            try: pin.break_link_to(cp)
            except Exception: pass

results={}
results["IA_pawn"]=bool(started and pawn_exec and started.try_create_connection(pawn_exec))
results["pawn_gat"]=bool(pawn_then and gat_exec and pawn_then.try_create_connection(gat_exec))
# ensure gat->fe
if gat and fe:
    gat_then=find_pin(gat,"then","Output")
    fe_exec=find_pin(fe,"Exec","Input") or find_pin(fe,"execute","Input")
    if gat_then and fe_exec:
        try: bel.break_pin_links(fe_exec)
        except Exception: pass
        results["gat_fe"]=bool(gat_then.try_create_connection(fe_exec))
    # array
    out_actors=find_pin(gat,"OutActors","Output")
    fe_arr=find_pin(fe,"Array","Input")
    if out_actors and fe_arr:
        results["arr"]=bool(out_actors.try_create_connection(fe_arr))
    # completed -> till
    if till:
        done=find_pin(fe,"Completed","Output")
        till_exec=find_pin(till,"execute","Input")
        if done and till_exec:
            # don't break till other links carefully
            results["fe_till"]=bool(done.try_create_connection(till_exec))

out["results"]=results
ok=bel.compile_blueprint(cbp)
out["compile"]=ok
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

# refresh dumps
ia=gat=pawn=fe=None
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "IA_Interact" in t: ia=n
    if t=="GetAllActorsWithTag": gat=n
    if t in ("Get Player Pawn","GetPlayerPawn"): pawn=n
    if "ForEachLoop" in t or t=="For Each Loop": fe=n
out["after"]={"ia":dump(ia),"pawn":dump(pawn),"gat":dump(gat),"fe_title":bel.get_node_title(fe) if fe else None}

# chain from started
chain=[]
if ia:
    started=find_pin(ia,"Started","Output")
    q=[cp.get_owning_node() for cp in started.list_connected_pins()] if started else []
    seen=set()
    while q and len(chain)<20:
        n=q.pop(0)
        if id(n) in seen: continue
        seen.add(id(n)); chain.append(bel.get_node_title(n))
        for p in bel.list_all_pins(n):
            if "output" not in str(p.get_pin_direction()).lower(): continue
            for cp in p.list_connected_pins():
                q.append(cp.get_owning_node())
out["chain"]=chain
els=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
els.save_current_level()
open(r"E:\UE\FarmSim25D\Saved\restaurant_ia_fix.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({"results":results,"compile":ok,"chain":chain},indent=2))
