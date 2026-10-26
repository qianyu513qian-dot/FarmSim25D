# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
created=[]
for path in [
    "/Script/Engine.Actor:GetComponentByClass",
    "/Script/Engine.Actor:K2_GetComponentsByClass",
    "/Script/Engine.StaticMeshActor:GetStaticMeshComponent",
    "/Script/Engine.Actor:SetActorScale3D",
    "/Script/Engine.Actor:K2_SetActorLocation",
    "/Script/Engine.Actor:SetActorEnableCollision",
]:
    try:
        n=ge.add_call_function_node(path)
        if n and len(bel.list_all_pins(n))>0:
            unreal.log("OK {} {}".format(path.split(":")[-1],[str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
            created.append(n)
        else:
            unreal.log("empty "+path)
            if n: created.append(n)
    except Exception as e:
        unreal.log("FAIL {} {}".format(path,e))
# BeginDeferred ActorClass pin set to StaticMeshActor
n=ge.add_call_function_node("/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass")
created.append(n)
for p in bel.list_all_pins(n):
    if "Class" in str(p.get_pin_name()):
        for v in ["/Script/Engine.StaticMeshActor", "StaticMeshActor", "/Script/Engine.StaticMeshActor.StaticMeshActor_C"]:
            try:
                p.set_pin_value(v)
                unreal.log("ActorClass set {!r} -> {!r}".format(v, p.get_pin_value()))
            except Exception as e:
                unreal.log("ActorClass fail {}: {}".format(v,e))
# DynamicCast create via list_available with actor return pin context
ret = find=None
for p in bel.list_all_pins(n):
    if str(p.get_pin_name())=="ReturnValue":
        find=p
try:
    avail = ge.list_available_nodes([find] if find else [])
    unreal.log("avail len="+str(len(avail)))
    for a in avail:
        s=str(a).lower()
        if "cast" in s or "spawn" in s:
            unreal.log("avail: "+str(a))
except Exception as e:
    unreal.log("avail err "+str(e))
# Try create DynamicCast then retarget
try:
    # spawn a cast from Actor to Actor then retarget?
    dc = unreal.K2Node_DynamicCast()
    unreal.log("dc instance "+str(dc))
except Exception as e:
    unreal.log("dc inst "+str(e))
if created: ge.remove_nodes(created)
