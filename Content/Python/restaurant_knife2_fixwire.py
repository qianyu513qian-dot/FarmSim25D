# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

def pins(n):
    return [(str(p.get_pin_name()), str(p.get_pin_direction()), str(p.get_pin_type_display_string())) for p in bel.list_all_pins(n)]

# Event Tick recreate
tries=[]
for cname in ["Event Tick", "ReceiveTick", "Tick"]:
    try:
        n=ge.create_node_from_name(cname, unreal.Vector2D(0,1500), [])
        tries.append({"n":cname,"ok":n is not None,"title":bel.get_node_title(n) if n else None,"cls":n.get_class().get_name() if n else None,"pins":pins(n) if n else []})
        if n: ge.remove_nodes([n])
    except Exception as e:
        tries.append({"n":cname,"err":str(e)[:150]})

# GetPlayerPawn
pawn=ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
tries.append({"pawn":pins(pawn),"title":bel.get_node_title(pawn)})
ploc=ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
tries.append({"k2loc":pins(ploc) if ploc else None,"title":bel.get_node_title(ploc) if ploc else None})
ploc2=ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
tries.append({"loc":pins(ploc2) if ploc2 else None,"title":bel.get_node_title(ploc2) if ploc2 else None})
# wire pawn to loc self
ok=False
if pawn and ploc2:
    rv=None; sf=None
    for p in bel.list_all_pins(pawn):
        if str(p.get_pin_name())=="ReturnValue": rv=p
    for p in bel.list_all_pins(ploc2):
        if str(p.get_pin_name()).lower()=="self": sf=p
    ok = rv.try_create_connection(sf) if rv and sf else False
    tries.append({"wire_pawn_loc":ok,"rv":str(rv),"sf":str(sf),"sf_type":str(sf.get_pin_type_display_string()) if sf else None})
if pawn and ploc:
    rv=None; sf=None
    for p in bel.list_all_pins(pawn):
        if str(p.get_pin_name())=="ReturnValue": rv=p
    for p in bel.list_all_pins(ploc):
        if str(p.get_pin_name()).lower()=="self": sf=p
    ok2 = rv.try_create_connection(sf) if rv and sf else False
    tries.append({"wire_pawn_k2loc":ok2})

# foreach element to loc
fe=ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
aloc=ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
el=None
for p in bel.list_all_pins(fe):
    if "element" in str(p.get_pin_name()).lower():
        el=p; break
sf=None
for p in bel.list_all_pins(aloc):
    if str(p.get_pin_name()).lower()=="self": sf=p
ok3=el.try_create_connection(sf) if el and sf else False
tries.append({"fe_el_pins":[str(p.get_pin_name()) for p in bel.list_all_pins(fe)],"wire_el":ok3,
              "el_type":str(el.get_pin_type_display_string()) if el else None,
              "sf_type":str(sf.get_pin_type_display_string()) if sf else None,
              "can": el.can_create_connection(sf) if el and sf else None})

# ClearGuests call
cg=ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearGuests")
tries.append({"cg":bel.get_node_title(cg) if cg else None,"pins":pins(cg) if cg else None})

# list current mgr nodes
nodes=[bel.get_node_title(n)+":"+n.get_class().get_name() for n in ge.list_all_nodes()]
ge.remove_nodes([x for x in (pawn,ploc,ploc2,fe,aloc,cg) if x])
print(json.dumps({"tries":tries,"nodes":nodes},indent=2,default=str)[:8000])
