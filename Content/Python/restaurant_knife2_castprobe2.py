# -*- coding: utf-8 -*-
import unreal, json, inspect
bel = unreal.BlueprintEditorLibrary
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
cast_doc = str(cge.cast.__doc__) if cge.cast.__doc__ else ""
try:
    cast_sig = str(inspect.signature(cge.cast))
except Exception as e:
    cast_sig = str(e)

fc = unreal.load_object(None, "/Script/FarmSim25D.FarmClock")
mgr_cls = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager").generated_class()
tbl_cls = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable").generated_class()
pin_apis = [x for x in dir(bel.list_all_pins(cge.list_all_nodes()[0])[0]) if not x.startswith("_")]
tries = []
for label, cls in [("FarmClock", fc), ("Manager", mgr_cls), ("Table", tbl_cls)]:
    for mode in ["pos_cls", "cls_pos", "cls_only"]:
        try:
            if mode=="pos_cls":
                n = cge.cast(unreal.Vector2D(100,100), cls)
            elif mode=="cls_pos":
                n = cge.cast(cls, unreal.Vector2D(100,100))
            else:
                n = cge.cast(cls)
            tries.append({"label":label,"mode":mode,"ok":n is not None,"title":bel.get_node_title(n) if n else None,
                          "pins":[str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(n)] if n else [],
                          "cls":n.get_class().get_name() if n else None})
            if n: cge.remove_nodes([n])
            break
        except Exception as e:
            tries.append({"label":label,"mode":mode,"err":str(e)[:220]})

# IA chain via pin links
ia = None
for n in cge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_EnhancedInputAction" and "IA_Interact" in bel.get_node_title(n):
        ia = n
ia_info = {"title": bel.get_node_title(ia) if ia else None, "pin_link_api": [x for x in pin_apis if "link" in x.lower() or "connect" in x.lower() or "dest" in x.lower()]}
if ia:
    for p in bel.list_all_pins(ia):
        if str(p.get_pin_name())=="Started":
            # try various link getters
            for meth in ["get_linked_pins","linked_to","get_destination_pins","get_connections"]:
                if hasattr(p, meth):
                    try:
                        linked = getattr(p, meth)()
                        ia_info["Started_"+meth] = [bel.get_node_title(l.get_owning_node()) if hasattr(l,"get_owning_node") else str(l) for l in linked]
                    except Exception as e:
                        ia_info["Started_"+meth] = str(e)[:80]
            # also try bel helpers
            for meth in ["get_pin_linked_to","list_pin_links","get_linked_to"]:
                if hasattr(bel, meth):
                    try:
                        linked = getattr(bel, meth)(p)
                        ia_info["Started_bel_"+meth] = str(linked)[:200]
                    except Exception as e:
                        ia_info["Started_bel_"+meth] = str(e)[:80]

bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
mgr_nodes = [{"t":bel.get_node_title(n),"c":n.get_class().get_name()} for n in mge.list_all_nodes()]

# member vars via add_get
get_beh = mge.add_get_member_variable_node("bEHandled")
get_open = mge.add_get_member_variable_node("bIsOpen")
var_ok = {"bEHandled": get_beh is not None, "bIsOpen": get_open is not None}
if get_beh: mge.remove_nodes([get_beh])
if get_open: mge.remove_nodes([get_open])

# OpenSign
osp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantOpenSign")
oge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(osp)) if osp else None
os_nodes = [{"t":bel.get_node_title(n),"c":n.get_class().get_name()} for n in oge.list_all_nodes()] if oge else []

# tables/actors in level
eas = unreal.EditorActorSubsystem()
acts = eas.get_all_level_actors()
rest = [a.get_actor_label() for a in acts if a.get_actor_label().startswith("Restaurant_") or a.get_actor_label().startswith("RestChair_")]
farm_ok = any("Grass" in a.get_actor_label() or "Bridge" in a.get_actor_label() for a in acts)

rep = {"cast_doc":cast_doc[:800],"cast_sig":cast_sig,"tries":tries,"ia":ia_info,
       "mgr_node_count":len(mgr_nodes),"mgr_nodes":mgr_nodes,"var_ok":var_ok,
       "os_nodes":os_nodes,"rest_count":len(rest),"rest":rest,"actors":len(acts),"farm_ok":farm_ok,
       "pin_apis":pin_apis}
print(json.dumps(rep, ensure_ascii=False, indent=2)[:12000])
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_castprobe2.json","w",encoding="utf-8").write(json.dumps(rep,indent=2,ensure_ascii=False))
