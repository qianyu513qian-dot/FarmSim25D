# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
# add bEHandled on character temporarily? or get existing
names=list(bel.list_member_variable_names(cbp, False))
print("char vars sample", [n for n in names if "Rest" in n or "EHandle" in n or "Till" in n][:20])
# Try get bEHandled - may not exist on char
g=cge.add_get_member_variable_node("bEHandled")
print("get bEHandled", g, bel.get_node_title(g) if g else None)
if g:
    print("pins", [(str(p.get_pin_name()), str(p.get_pin_type_display_string()), str(p.get_pin_direction())) for p in bel.list_all_pins(g)])
    cge.remove_nodes([g])
# Try create Get bIsOpenBusiness from manager path
for cname in ["Get bEHandled", "Get bIsOpenBusiness"]:
    try:
        n=cge.create_node_from_name(cname, unreal.Vector2D(0,0), [])
        print(cname, n, bel.get_node_title(n) if n else None)
        if n:
            print(" pins", [(str(p.get_pin_name()), str(p.get_pin_type_display_string())) for p in bel.list_all_pins(n)])
            cge.remove_nodes([n])
    except Exception as e:
        print(cname, e)
# Call HandlePlayerE then try to read via Get - with Target from Array_Get
mgr = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
gao=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
# set class
for p in bel.list_all_pins(gao):
    if "ActorClass" in str(p.get_pin_name()) or str(p.get_pin_name())=="Class":
        p.set_pin_value("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
get0=cge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
he=cge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandlePlayerE")
item=None
for p in bel.list_all_pins(get0):
    if str(p.get_pin_name())=="Item": item=p
selfp=None
for p in bel.list_all_pins(he):
    if str(p.get_pin_name())=="self": selfp=p
ok_he = item.try_create_connection(selfp) if item and selfp else False
print("direct HandlePlayerE self", ok_he)
# After call, can we get variable from that object via create Set/Get with target?
# K2Node_VariableGet with self override - try wiring item to get node's self if any
g2=cge.add_get_member_variable_node("bEHandled")
if g2:
    pins=[(str(p.get_pin_name()), str(p.get_pin_type_display_string()), str(p.get_pin_direction())) for p in bel.list_all_pins(g2)]
    print("g2 pins", pins)
    # try connect item to any input object pin
    for p in bel.list_all_pins(g2):
        if "INPUT" in str(p.get_pin_direction()):
            ok=item.try_create_connection(p)
            print("wire item to", p.get_pin_name(), ok)
cge.remove_nodes([x for x in (gao,get0,he,g2) if x])
