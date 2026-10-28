# -*- coding: utf-8 -*-
import unreal, json, inspect
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
apis=[x for x in dir(ge) if "event" in x.lower() or "tick" in x.lower() or "override" in x.lower() or "add_" in x.lower()]
print("apis", apis)
# try add_component_bound / dispatcher
docs={}
for name in ["add_custom_event_node","add_dispatcher_event_node","add_component_bound_event_node","create_node_from_name"]:
    f=getattr(ge,name)
    docs[name]=str(f.__doc__)[:300] if f.__doc__ else ""
# Bel helpers for events
bapis=[x for x in dir(bel) if "event" in x.lower() or "tick" in x.lower() or "override" in x.lower()]
print("bel", bapis)
for name in bapis:
    f=getattr(bel,name)
    if f.__doc__:
        print("---",name,"---")
        print(f.__doc__[:250])

# Timer approach probe
for path in [
    "/Script/Engine.KismetSystemLibrary:K2_SetTimer",
    "/Script/Engine.KismetSystemLibrary:K2_SetTimerDelegate",
    "/Script/Engine.System:SetTimer",
]:
    try:
        n=ge.add_call_function_node(path)
        print("timer", path, bel.get_node_title(n) if n else None, [str(p.get_pin_name()) for p in bel.list_all_pins(n)] if n else None)
        if n: ge.remove_nodes([n])
    except Exception as e:
        print("timer err", path, e)

# BeginPlay exists - wire SetTimer calling custom RestaurantTick
# Also test: connect Array first then element to loc
gaw=ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
for p in bel.list_all_pins(gaw):
    if str(p.get_pin_name())=="Tag":
        p.set_pin_value("RestInteract")
fe=ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
# connect array first
for p in bel.list_all_pins(gaw):
    if str(p.get_pin_name())=="OutActors":
        for q in bel.list_all_pins(fe):
            if str(q.get_pin_name())=="Array":
                print("arr wire", p.try_create_connection(q))
aloc=ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
el=sf=None
for p in bel.list_all_pins(fe):
    if str(p.get_pin_name())=="Array Element": el=p
for p in bel.list_all_pins(aloc):
    if str(p.get_pin_name()).lower()=="self": sf=p
print("el type after arr", el.get_pin_type_display_string() if el else None)
print("wire el after arr", el.try_create_connection(sf) if el and sf else None, "can", el.can_create_connection(sf) if el and sf else None)
ge.remove_nodes([x for x in (gaw,fe,aloc) if x])
print("docs", json.dumps(docs,indent=2))
