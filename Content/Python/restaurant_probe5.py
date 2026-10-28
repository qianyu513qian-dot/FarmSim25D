# -*- coding: utf-8 -*-
"""Probe RestoreClock pins, Cast create with [], Set Material, how print after pay is linked."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
R={"steps":[]}
def log(m):
    unreal.log("[P5] "+str(m)); print("[P5] "+str(m)); R["steps"].append(str(m))
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

mbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# RestoreClock pins
n=mge.add_call_function_node("/Script/FarmSim25D.FarmClock:RestoreClock")
pins=[]
for p in bel.list_all_pins(n):
    pins.append({"name":str(p.get_pin_name()),"dir":str(p.get_pin_direction()),"type":str(p.get_pin_type()),"def":p.get_pin_value()[:100] if p.get_pin_value() else ""})
R["RestoreClock_pins"]=pins
log("RestoreClock pins: "+str(pins))
# try set SavedState default
sp=find_pin(n,"SavedState","Input") or find_pin(n,"State","Input")
if sp:
    try:
        sp.set_pin_value("(AbsoluteDay=1,Minutes=1020.000000)")
        log("set_pin_value ok -> "+str(sp.get_pin_value()))
    except Exception as e:
        log("set_pin_value fail "+str(e))
    try:
        sp.import_text("(AbsoluteDay=1,Minutes=1020.000000)")
        log("import_text ok -> "+str(sp.get_pin_value()))
    except Exception as e:
        log("import_text fail "+str(e))
mge.remove_nodes([n])

# Cast with []
for cname in ["Cast To BP_TopDownCharacter","Cast To BP_TopDownCharacter_C","Cast To FarmClock"]:
    try:
        cn=mge.create_node_from_name(cname, unreal.Vector2D(0,0), [])
        log("CAST OK "+cname+" -> "+(title(cn) if cn else "None")+" class="+ (cn.get_class().get_name() if cn else ""))
        if cn:
            pp=[]
            for p in bel.list_all_pins(cn):
                pp.append(str(p.get_pin_name())+":"+str(p.get_pin_direction()))
            log("  pins "+str(pp))
            mge.remove_nodes([cn])
    except Exception as e:
        log("CAST FAIL "+cname+" "+str(e))

# Make FarmClockState with []
for cname in ["Make FarmClockState","Make FFarmClockState","MakeStruct FarmClockState"]:
    try:
        cn=mge.create_node_from_name(cname, unreal.Vector2D(0,0), [])
        log("MAKE OK "+cname+" -> "+(title(cn) if cn else "None"))
        if cn:
            pp=[str(p.get_pin_name()) for p in bel.list_all_pins(cn)]
            log("  pins "+str(pp))
            mge.remove_nodes([cn])
    except Exception as e:
        log("MAKE FAIL "+cname+" "+str(e))

# SetMaterial / CreateDynamicMaterialInstance
for path in [
 "/Script/Engine.PrimitiveComponent:SetMaterial",
 "/Script/Engine.PrimitiveComponent:CreateDynamicMaterialInstance",
 "/Script/Engine.PrimitiveComponent:SetVectorParameterValueOnMaterials",
 "/Script/Engine.MeshComponent:SetMaterial",
 "/Script/Engine.StaticMeshComponent:SetMaterial",
 "/Script/Engine.Actor:SetActorScale3D",
 "/Script/Engine.KismetMathLibrary:Add_IntInt",
 "/Script/Engine.KismetSystemLibrary:PrintString",
]:
    try:
        nn=mge.add_call_function_node(path)
        log("FN OK "+path+" -> "+(title(nn) if nn else "None"))
        if nn: mge.remove_nodes([nn])
    except Exception as e:
        log("FN FAIL "+path+" "+str(e))

# Inspect OnGuestPaidSalad chain pins carefully
def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

ev=find_custom(mge,"OnGuestPaidSalad")
then=find_pin(ev,"then","Output")
setn=then.list_connected_pins()[0].get_owning_node() if then and then.list_connected_pins() else None
log("pay salad first="+title(setn))
# follow to Print
then2=find_pin(setn,"then","Output")
prn=then2.list_connected_pins()[0].get_owning_node() if then2 and then2.list_connected_pins() else None
log("pay salad second="+title(prn))
then3=find_pin(prn,"then","Output")
log("print then links="+str(len(then3.list_connected_pins()) if then3 else 0))

# Open sets: find Print after open true and wire points
for n in mge.list_all_nodes():
    if title(n)!="Set bIsOpenBusiness": continue
    val=find_pin(n,"bIsOpenBusiness","Input")
    v=val.get_pin_value() if val else "?"
    thenp=find_pin(n,"then","Output")
    succ=title(thenp.list_connected_pins()[0].get_owning_node()) if thenp and thenp.list_connected_pins() else None
    # get node position
    try:
        pos=bel.get_node_position(n) if hasattr(bel,"get_node_position") else None
    except: pos=None
    log("SetOpen val=%s succ=%s"%(v,succ))

# Don't save dirty from probe removals - compile? skip
out=unreal.Paths.project_saved_dir()+"restaurant_probe5.json"
# stringify
with open(out,"w",encoding="utf-8") as f:
    json.dump({"steps":R["steps"],"RestoreClock_pins":[{k:str(v) for k,v in p.items()} for p in R.get("RestoreClock_pins",[])]}, f, indent=2, ensure_ascii=False)
log("WROTE "+out)
