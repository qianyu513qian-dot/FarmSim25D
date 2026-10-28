# -*- coding: utf-8 -*-
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def pin_val(p):
    if not p: return None
    if hasattr(p,"get_pin_value"):
        try: return str(p.get_pin_value())
        except: pass
    return None

mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
tbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
R={"concats":[], "table_comps":[]}

# Find PrintDayEndSummary region concats
ev=None
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="PrintDayEndSummary":
        ev=n; break
# All Concat near summary
for n in mge.list_all_nodes():
    if "Concat" in title(n):
        a=pin_val(find_pin(n,"A","Input"))
        b=pin_val(find_pin(n,"B","Input"))
        if a or b:
            R["concats"].append({"A":a,"B":b})

# TableDishMesh exists
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary
for h in list(sub.k2_gather_subobject_data_for_blueprint(tbp) or []):
    data=sub.k2_find_subobject_data_from_handle(h)
    try:
        name=str(lib.get_variable_name(data) or "")
        if "Dish" in name or "Table" in name:
            obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
            info={"name":name}
            if obj:
                try: info["mesh"]=str(obj.get_editor_property("static_mesh"))
                except: pass
                try: info["hidden"]=str(obj.get_editor_property("hidden_in_game"))
                except: pass
                try: info["rel"]=str(obj.get_editor_property("relative_location"))
                except: pass
                try: info["scale"]=str(obj.get_editor_property("relative_scale3d"))
                except: pass
            R["table_comps"].append(info)
    except: pass

R["table_status"]=str(tbp.get_editor_property("status"))
R["mgr_status"]=str(mbp.get_editor_property("status"))
print(json.dumps(R,indent=2,ensure_ascii=False,default=str))
