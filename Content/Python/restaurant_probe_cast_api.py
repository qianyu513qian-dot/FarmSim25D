# -*- coding: utf-8 -*-
import unreal, json
bel=unreal.BlueprintEditorLibrary
mbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
cbp=unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
apis=[x for x in dir(mge) if "cast" in x.lower() or "create" in x.lower() or "add_" in x.lower()]
print("APIS", apis)
# try various cast creates
results=[]
for cname in [
 "Cast To BP_TopDownCharacter",
 "Utilities|Casting|Cast To BP_TopDownCharacter",
 "Cast To BP_TopDownCharacter_C",
 "Class Cast|Cast To BP_TopDownCharacter",
]:
    try:
        n=mge.create_node_from_name(cname, unreal.Vector2D(0,0), [])
        results.append({"n":cname,"ok":n is not None,"t":bel.get_node_title(n) if n else None,"c":n.get_class().get_name() if n else None})
        if n: mge.remove_nodes([n])
    except Exception as e:
        results.append({"n":cname,"err":str(e)[:100]})
# DynamicCast class spawn?
try:
    cls=unreal.K2Node_DynamicCast.static_class()
    results.append({"dyn_cls":str(cls)})
except Exception as e:
    results.append({"dyn_err":str(e)})
# Does add_cast exist on cge?
results.append({"mge_has":hasattr(mge,"add_cast_node"),"cge_has":hasattr(cge,"add_cast_node")})
# Try calling GrantMoney with GetPlayerPawn self directly (will it connect?)
pawn=mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
call=mge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:GrantMoney_Salad")
ok=False
try:
    a=None
    for p in bel.list_all_pins(pawn):
        if "OUTPUT" in str(p.get_pin_direction()) and "return" in str(p.get_pin_name()).lower():
            a=p
    b=None
    for p in bel.list_all_pins(call):
        if str(p.get_pin_name()).lower()=="self":
            b=p
    ok=a.try_create_connection(b) if a and b else False
    results.append({"pawn_to_grant_self":ok,"pawn_pins":[str(p.get_pin_name()) for p in bel.list_all_pins(pawn)],
                    "call_pins":[str(p.get_pin_name()) for p in bel.list_all_pins(call)]})
except Exception as e:
    results.append({"conn_err":str(e)})
mge.remove_nodes([x for x in (pawn,call) if x])
# GetPlayerCharacter
pawn=mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerCharacter")
call=mge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:GrantMoney_Salad")
a=None
for p in bel.list_all_pins(pawn):
    if "OUTPUT" in str(p.get_pin_direction()) and "return" in str(p.get_pin_name()).lower():
        a=p
b=find if False else None
for p in bel.list_all_pins(call):
    if str(p.get_pin_name()).lower()=="self": b=p
ok=a.try_create_connection(b) if a and b else False
results.append({"char_to_grant_self":ok})
mge.remove_nodes([x for x in (pawn,call) if x])
# Pure cast via schema
try:
    schema = unreal.EdGraphSchema_K2.get_default_object() if False else None
except: pass
open(r"E:\UE\FarmSim25D\Saved\cast_api.json","w",encoding="utf-8").write(json.dumps(results,indent=2,default=str))
print(json.dumps(results,indent=2,default=str))
