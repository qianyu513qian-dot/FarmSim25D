# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# probe compare nodes
probes=[]
for cname in [
    "integer >= integer", "Int >= Int", "int >= int",
    "float >= float", "double >= double",
    "Greater Equal (Integer)", "GreaterEqual_IntInt",
    "int + int", "float + float", "double + double",
]:
    try:
        n = mge.create_node_from_name(cname, unreal.Vector2D(0,0), [])
        probes.append({"n":cname,"ok":n is not None,"title":bel.get_node_title(n) if n else None,
                       "cls":n.get_class().get_name() if n else None,
                       "pins":[str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(n)] if n else []})
        if n: mge.remove_nodes([n])
    except Exception as e:
        probes.append({"n":cname,"err":str(e)[:100]})

# GetDisplayMinutes return type via pin
gdm = mge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
gdm_pins = []
for p in bel.list_all_pins(gdm):
    gdm_pins.append({"name":str(p.get_pin_name()),"type":p.get_pin_type_display_string(),"dir":str(p.get_pin_direction())})
mge.remove_nodes([gdm])

# FarmClock State.Minutes - get member?
# try Get Minutes from FarmClock
for path in [
    "/Script/FarmSim25D.FarmClock:GetMinutes",
    "/Script/FarmSim25D.FarmClock:GetState",
]:
    try:
        n=mge.add_call_function_node(path)
        probes.append({"n":path,"ok":n is not None,"title":bel.get_node_title(n) if n else None,
                       "pins":[str(p.get_pin_name()) for p in bel.list_all_pins(n)] if n else []})
        if n: mge.remove_nodes([n])
    except Exception as e:
        probes.append({"n":path,"err":str(e)[:80]})

# Character: list ALL nodes titles to see orphans
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
char_nodes=[{"t":bel.get_node_title(n),"c":n.get_class().get_name()} for n in cge.list_all_nodes()]

# Table existing bOccupied - use that not bOccupied_0
tbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
print("tbl", list(bel.list_member_variable_names(tbp, False)))
# types of key vars
for vn in ["bOccupied","bOccupied_0","CurrentOrder","CurrentDishId","bHasOrder"]:
    t=bel.get_member_variable_type(tbp, vn)
    print("tbl", vn, bel.pin_type_to_json_schema(t, None) if t else None)
for vn in ["bIsOpen","bIsOpenBusiness","GuestTimer","GuestTimer_0","GuestInterval","InteractRange","bEHandled","bSeatedOnce"]:
    t=bel.get_member_variable_type(bp, vn)
    print("mgr", vn, bel.pin_type_to_json_schema(t, None) if t else None)

# README
readme=""
try:
    readme=open(r"E:\UE\FarmSim25D\Content\Farm\Restaurant\README.md",encoding="utf-8").read()[:2000]
except: pass

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_probe4.json","w",encoding="utf-8").write(json.dumps({
    "probes":probes,"gdm_pins":gdm_pins,"char_nodes":char_nodes,"readme":readme
},indent=2,ensure_ascii=False))
print(json.dumps(probes,indent=2))
print("gdm", gdm_pins)
print("char count", len(char_nodes))
for c in char_nodes:
    if any(k in c["t"] for k in ["IA_","Till","Print","Branch","GetAll","Restaurant","Handle","Rest","For Each","Distance","Sphere"]):
        print(c)
