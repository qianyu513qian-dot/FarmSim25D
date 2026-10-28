# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
# probe basic types
types = {}
for name in ["bool","boolean","float","real","double","int","int32","integer","string","name","text","String","Float"]:
    try:
        t = bel.get_basic_type_by_name(name)
        types[name] = str(t) if t else None
    except Exception as e:
        types[name] = "ERR:"+str(e)[:80]

# change GuestTimer to float
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ft = bel.get_basic_type_by_name("real") or bel.get_basic_type_by_name("float")
st = bel.get_basic_type_by_name("string") or bel.get_basic_type_by_name("name")
print("ft",ft,"st",st)
print("vars before", list(bel.list_member_variable_names(bp, False)))
if ft:
    try:
        bel.change_member_variable_type(bp, "GuestTimer", ft)
        bel.change_member_variable_type(bp, "GuestInterval", ft)
        print("changed float ok")
    except Exception as e:
        print("chg float", e)
tbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
if st:
    try:
        bel.change_member_variable_type(tbp, "CurrentOrder", st)
        print("changed string ok")
    except Exception as e:
        print("chg str", e)
print("types", types)
print("mgr vars", list(bel.list_member_variable_names(bp, False)))
print("tbl vars", list(bel.list_member_variable_names(tbp, False)))

# probe int compare + random + self node
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
probes=[]
for path in [
    "/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt",
    "/Script/Engine.KismetMathLibrary:RandomIntegerInRange",
    "/Script/Engine.KismetMathLibrary:RandomBool",
    "/Script/Engine.KismetMathLibrary:Add_DoubleDouble",
    "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble",
    "/Script/Engine.KismetSystemLibrary:GetDisplayName",
]:
    try:
        n=mge.add_call_function_node(path)
        probes.append({"p":path,"ok":n is not None,"title":bel.get_node_title(n) if n else None,
                       "pins":[str(p.get_pin_name()) for p in bel.list_all_pins(n)] if n else []})
        if n: mge.remove_nodes([n])
    except Exception as e:
        probes.append({"p":path,"err":str(e)[:100]})
# Get Self
for cname in ["Get Reference to Self", "Self", "Get Self"]:
    try:
        n=mge.create_node_from_name(cname, unreal.Vector2D(0,0), [])
        probes.append({"p":cname,"ok":n is not None,"title":bel.get_node_title(n) if n else None})
        if n: mge.remove_nodes([n])
    except Exception as e:
        probes.append({"p":cname,"err":str(e)[:80]})
# Select string
try:
    n=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:SelectString")
    probes.append({"p":"SelectString","ok":n is not None,"pins":[str(p.get_pin_name()) for p in bel.list_all_pins(n)] if n else []})
    if n: mge.remove_nodes([n])
except Exception as e:
    probes.append({"p":"SelectString","err":str(e)[:80]})

# Character orphan TillSoil links
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
till=None
for n in cge.list_all_nodes():
    if bel.get_node_title(n)=="TillSoil":
        till=n
till_exec=None
for p in bel.list_all_pins(till):
    if str(p.get_pin_name())=="execute":
        till_exec=p
        print("TillSoil execute from", [bel.get_node_title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()])

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_probe3.json","w",encoding="utf-8").write(json.dumps({"types":types,"probes":probes},indent=2))
print(json.dumps(probes,indent=2)[:3000])
