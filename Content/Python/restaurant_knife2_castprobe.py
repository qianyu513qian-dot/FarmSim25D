# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
tried = []
for cname in [
    "Cast To FarmClock", "Cast To AFarmClock",
    "Cast To BP_RestaurantManager", "Cast To BP_RestaurantManager_C",
    "Cast To BP_RestaurantTable", "Cast To BP_RestaurantInteractable",
]:
    try:
        n = cge.create_node_from_name(cname, unreal.Vector2D(0, 0), [])
        tried.append({"name": cname, "ok": n is not None, "title": bel.get_node_title(n) if n else None})
        if n: cge.remove_nodes([n])
    except Exception as e:
        tried.append({"name": cname, "ok": False, "err": str(e)[:120]})

gao = cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
get0 = cge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
gdm = cge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
pins_gdm = [str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(gdm)]
pins_get0 = [str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(get0)]
item = None
for p in bel.list_all_pins(get0):
    if "output" in str(p.get_pin_direction()).lower() and str(p.get_pin_name()).lower() != "self":
        item = p; break
self_pin = find if False else None
for p in bel.list_all_pins(gdm):
    if str(p.get_pin_name()).lower()=="self":
        self_pin = p; break
ok_direct = bool(item and self_pin and item.try_create_connection(self_pin))
cge.remove_nodes([x for x in (gao,get0,gdm) if x])

bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
customs = [bel.get_node_title(n) for n in mge.list_all_nodes() if n.get_class().get_name()=="K2Node_CustomEvent"]
he_try = []
for cname in ["HandlePlayerE"]:
    try:
        n = cge.create_node_from_name(cname, unreal.Vector2D(0,0), [])
        he_try.append({"n":cname,"ok":n is not None,"title":bel.get_node_title(n) if n else None,
                       "pins":[str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(n)] if n else []})
        if n: cge.remove_nodes([n])
    except Exception as e:
        he_try.append({"n":cname,"err":str(e)[:120]})
try:
    n = cge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandlePlayerE")
    he_try.append({"n":"add_call","ok":n is not None,"title":bel.get_node_title(n) if n else None,
                   "pins":[str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(n)] if n else []})
    if n: cge.remove_nodes([n])
except Exception as e:
    he_try.append({"n":"add_call","err":str(e)[:120]})

# Does BlueprintGraphEditor have spawn_cast or similar?
apis = [x for x in dir(cge) if "cast" in x.lower() or "create" in x.lower() or "add_" in x.lower()]
rep = {"casts": tried, "gdm_pins": pins_gdm, "get0_pins": pins_get0, "direct_gdm_self": ok_direct,
       "customs": customs, "he_try": he_try, "ge_apis": apis}
print(json.dumps(rep, ensure_ascii=False, indent=2))
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_castprobe.json","w",encoding="utf-8").write(json.dumps(rep,indent=2))
