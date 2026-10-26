# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_PlotVisual")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyState"))
created=[]
for path in [
    "/Script/Engine.SceneComponent:SetHiddenInGame",
    "/Script/Engine.Actor:SetActorHiddenInGame",
    "/Script/Engine.PrimitiveComponent:SetHiddenInGame",
    "/Script/Engine.SceneComponent:SetVisibility",
    "/Script/Engine.KismetSystemLibrary:IsValid",
]:
    try:
        n = ge.add_call_function_node(path)
        if n and len(bel.list_all_pins(n))>0:
            unreal.log("OK {} {}".format(path.split(":")[-1], [str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
            created.append(n)
        else:
            unreal.log("empty "+path)
            if n: created.append(n)
    except Exception as e:
        unreal.log("FAIL {} {}".format(path,e))
# Try set NewMesh pin default
n = ge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
created.append(n)
mp = None
for p in bel.list_all_pins(n):
    unreal.log("ssm {} dir={}".format(p.get_pin_name(), p.get_pin_direction()))
    if "NewMesh" in str(p.get_pin_name()) or "Mesh" in str(p.get_pin_name()):
        mp = p
mesh = "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry"
for v in [mesh, mesh+".SM_VMF_Soil_Dry", "SM_VMF_Soil_Dry"]:
    try:
        mp.set_pin_value(v)
        unreal.log("set_pin_value {!r} -> {!r}".format(v, mp.get_pin_value()))
    except Exception as e:
        unreal.log("set fail {}: {}".format(v,e))
if created:
    ge.remove_nodes(created)
# Don't compile/save ApplyState churn from probe
