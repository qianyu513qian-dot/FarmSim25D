# -*- coding: utf-8 -*-
"""Probe how GuestActor / OrderListWidget types are defined; fix HeldDishActor."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
REPORT={}

def log(m):
    unreal.log("[TYPE] "+str(m)); print("[TYPE] "+str(m))

TBL="/Game/Farm/Restaurant/BP_RestaurantTable"
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
tbp=unreal.load_asset(TBL)
mbp=unreal.load_asset(MGR)

# List variable APIs
apis=[a for a in dir(bel) if "variable" in a.lower() or "member" in a.lower() or "pin_type" in a.lower()]
REPORT["apis"]=apis

# Try get variable type info
for bp, name in ((tbp,"GuestActor"),(mbp,"OrderListWidget"),(mbp,"HeldDishActor"),(mbp,"TableActorClass")):
    info={"bp":str(bp.get_name()),"var":name}
    for fn in ("get_member_variable_type","get_variable_type","find_member_variable","get_introduced_variables"):
        if hasattr(bel, fn):
            try:
                info[fn]=str(getattr(bel,fn)(bp, name) if fn!="get_introduced_variables" else getattr(bel,fn)(bp))
            except Exception as e:
                try:
                    info[fn]=str(getattr(bel,fn)(bp))
                except Exception as e2:
                    info[fn]="err "+str(e)[:80]
    REPORT[name]=info

# Try NewObject EdGraphPinType properties
pt=unreal.EdGraphPinType()
props=[]
try:
    for p in dir(pt):
        if p.startswith("_"): continue
        try:
            props.append(p+"="+str(getattr(pt,p))[:60])
        except: props.append(p)
except Exception as e:
    props.append(str(e))
REPORT["pin_type_dir"]=props[:80]

# unreal.PinCategory?
cats=[]
for n in dir(unreal):
    if "Pin" in n or "pin_category" in n.lower():
        cats.append(n)
REPORT["pin_names"]=[c for c in cats if "Pin" in c][:40]

# How restaurant scripts added GuestActor
# Try: bel.add_member_variable with class
help_add=""
try:
    help_add=str(bel.add_member_variable.__doc__)
except: pass
REPORT["add_doc"]=help_add

# Try remove HeldDishActor and re-add as object with subcategory
try:
    if hasattr(bel,"remove_member_variable"):
        bel.remove_member_variable(mbp,"HeldDishActor")
        log("removed HeldDishActor")
        REPORT["removed"]=True
except Exception as e:
    REPORT["remove_err"]=str(e)

# Recreate using pattern from GuestActor on table - inspect generated class property
try:
    cls=tbp.generated_class()
    cdo=unreal.get_default_object(cls)
    ga=cdo.get_editor_property("GuestActor")
    REPORT["guest_cdo"]=str(type(ga))+" "+str(ga)
except Exception as e:
    REPORT["guest_cdo_err"]=str(e)

# Try add with SoftObject / object
# Looking at UE Python: BlueprintEditorLibrary.add_member_variable(Blueprint, VariableName, VariableType: EdGraphPinType)
# get_basic_type_by_name returns EdGraphPinType for int/bool/string/float/name/byte/object?
for name in ("object","soft_object","class","soft_class","actor","interface","struct","int","bool"):
    try:
        t=bel.get_basic_type_by_name(name)
        # inspect fields via get_editor_property alternatives
        info={"name":name,"str":str(t)}
        for prop in ("PinCategory","PinSubCategory","PinSubCategoryObject","ContainerType","bIsReference","pin_category","pin_sub_category_object"):
            try:
                info[prop]=str(t.get_editor_property(prop))
            except Exception as e:
                info[prop]="x"
        # try struct fields
        try:
            info["pc"]=str(t.pin_category)
        except Exception as e:
            info["pc"]=str(e)[:40]
        REPORT.setdefault("types",[]).append(info)
    except Exception as e:
        REPORT.setdefault("types",[]).append({"name":name,"err":str(e)[:60]})

open(r"E:\UE\FarmSim25D\Saved\rest_held_type_probe.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str))
print(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str)[:8000])
