# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
gbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestGuest")
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
apis = [x for x in dir(gge) if not x.startswith("_")]
for a in apis:
    if any(k in a.lower() for k in ("cast","spawn","call","add_","class","dynamic","material")):
        print(a)
print("---bel---")
for a in dir(bel):
    if "cast" in a.lower() or "material" in a.lower():
        print("bel."+a)
# Try DynamicCast path as CallFunction
n = gge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
print("GetActorOfClass", n)
# Pure cast might be K2Node_DynamicCast via add_node_by_class
for a in apis:
    if "node" in a.lower() and "add" in a.lower():
        print("addapi", a)
