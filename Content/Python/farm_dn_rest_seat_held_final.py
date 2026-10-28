# -*- coding: utf-8 -*-
"""Final verify chair offset defaults + HeldDishMesh component + clean orphans."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
REPORT={}

TBL="/Game/Farm/Restaurant/BP_RestaurantTable"
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
GUEST="/Game/Farm/Restaurant/BP_RestGuest"
tbp=unreal.load_asset(TBL); mbp=unreal.load_asset(MGR); gbp=unreal.load_asset(GUEST)
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp,"EventGraph"))
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp,"EventGraph"))

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
    for fn in ("get_default_as_string","get_default_value","get_pin_value","default_value"):
        if hasattr(p,fn):
            try:
                v=getattr(p,fn)
                v=v() if callable(v) else v
                if v is not None and str(v)!="":
                    return str(v)
            except Exception: pass
    try:
        return str(p.default_value)
    except Exception: pass
    # export text
    try:
        return p.get_editor_property("default_value")
    except Exception: pass
    return None

# Find MakeTransform used by spawn and its location offset
for n in tge.list_all_nodes():
    if title(n)!="MakeTransform": continue
    rv=find_pin(n,"ReturnValue","Output")
    links=[title(c.get_owning_node()) for c in (rv.list_connected_pins() or [])] if rv else []
    if not any("BeginDeferred" in L or "FinishSpawning" in L for L in links):
        continue
    loc=find_pin(n,"Location","Input")
    rot=find_pin(n,"Rotation","Input")
    REPORT["tf_links"]=links
    REPORT["tf_rot_def"]=pin_val(rot)
    REPORT["tf_rot_links"]=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in (rot.list_connected_pins() or [])] if rot else []
    # walk Location to MakeVector
    for c in (loc.list_connected_pins() or []) if loc else []:
        addn=c.get_owning_node()
        REPORT["loc_from"]=title(addn)
        bp=find_pin(addn,"B","Input")
        for c2 in (bp.list_connected_pins() or []) if bp else []:
            mv=c2.get_owning_node()
            REPORT["offset"]={"title":title(mv),"X":pin_val(find_pin(mv,"X","Input")),"Y":pin_val(find_pin(mv,"Y","Input")),"Z":pin_val(find_pin(mv,"Z","Input"))}
            # force-set again to be sure
            for pin,val in (("X","0.0"),("Y","-70.0"),("Z","-8.0")):
                p=find_pin(mv,pin,"Input")
                if p:
                    try: p.set_pin_value(val)
                    except:
                        try: p.set_default_value(val)
                        except: pass
            REPORT["offset_after"]={"X":pin_val(find_pin(mv,"X","Input")),"Y":pin_val(find_pin(mv,"Y","Input")),"Z":pin_val(find_pin(mv,"Z","Input"))}
    # force rotation yaw 90
    if rot:
        try: rot.set_pin_value("0.000000,90.000000,0.000000")
        except:
            try: rot.set_default_value("0.000000,90.000000,0.000000")
            except Exception as e: REPORT["rot_err"]=str(e)
        REPORT["tf_rot_after"]=pin_val(rot)

# Guest mesh
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary
for h in list(sub.k2_gather_subobject_data_for_blueprint(gbp) or []):
    data=sub.k2_find_subobject_data_from_handle(h)
    try:
        name=str(lib.get_variable_name(data) or "")
        obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
        if name=="GuestMesh" and obj:
            REPORT["guest_rel"]=str(obj.get_editor_property("relative_location"))
            REPORT["guest_scale"]=str(obj.get_editor_property("relative_scale3d"))
    except Exception as e:
        REPORT.setdefault("guest_err",[]).append(str(e))

# Manager HeldDishMesh
for h in list(sub.k2_gather_subobject_data_for_blueprint(mbp) or []):
    data=sub.k2_find_subobject_data_from_handle(h)
    try:
        name=str(lib.get_variable_name(data) or "")
        obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
        if "HeldDish" in name and obj:
            REPORT["held_comp"]={"name":name,"class":obj.get_class().get_name(),
                "mesh":str(obj.get_editor_property("static_mesh")),
                "scale":str(obj.get_editor_property("relative_scale3d")),
                "hidden":str(obj.get_editor_property("hidden_in_game") if False else "?")}
            try: REPORT["held_comp"]["hidden"]=str(obj.is_visible())
            except: pass
            try: REPORT["held_comp"]["hidden_in_game"]=str(obj.get_editor_property("component_tags"))
            except: pass
    except Exception as e:
        pass

# statuses
for path,key in ((TBL,"table"),(MGR,"mgr"),(GUEST,"guest")):
    bp=unreal.load_asset(path)
    bel.compile_blueprint(bp)
    REPORT[key]=str(bp.get_editor_property("status"))
    eas.save_asset(path)

# Try remove_node via EditorGraph
try:
    ge_inner=bel.find_graph(mbp,"EventGraph")
    REPORT["graph"]=str(ge_inner)
except Exception as e:
    REPORT["graph_err"]=str(e)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_seat_held_FINAL.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str))
print(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str))
