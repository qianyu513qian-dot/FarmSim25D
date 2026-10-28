# -*- coding: utf-8 -*-
"""Probe: BeginEat / ClearSeat / close / vars for table-dish + day-end batch."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
R = {"mgr_vars": [], "table_vars": [], "customs": [], "begin_eat": [], "clear_seat": [],
     "pay_salad": [], "pay_stew": [], "set_open_false": [], "errors": []}

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def walk(start, limit=40):
    chain=[]; seen=set(); q=[start]
    while q and len(chain)<limit:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); chain.append(title(cur))
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
    return chain

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

def list_vars(bp):
    out=[]
    try:
        for v in bel.get_new_variables(bp) or []:
            try:
                out.append(str(v.var_name) if hasattr(v,"var_name") else str(v))
            except Exception:
                out.append(str(v))
    except Exception as e:
        # fallback: scan get nodes
        pass
    return out

MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
TBL="/Game/Farm/Restaurant/BP_RestaurantTable"
mbp=eas.load_asset(MGR); tbp=eas.load_asset(TBL)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))

# vars via get nodes
seen_v=set()
for n in mge.list_all_nodes():
    t=title(n)
    if t.startswith("Get ") or t.startswith("Set "):
        seen_v.add(t)
R["mgr_getset"]=sorted(seen_v)[:80]
seen_tv=set()
for n in tge.list_all_nodes():
    t=title(n)
    if t.startswith("Get ") or t.startswith("Set "):
        seen_tv.add(t)
R["table_getset"]=sorted(seen_tv)[:80]

for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent":
        R["customs"].append(title(n))
R["customs"]=sorted(set(R["customs"]))

for name,key in (("BeginEat","begin_eat"),("BeginEatOnly","begin_eat_only"),
                 ("OnGuestPaidSalad","pay_salad"),("OnGuestPaidStew","pay_stew"),
                 ("ClearHeld","clear_held"),("TryServe","try_serve"),
                 ("HandleServe","handle_serve"),("NotifyServe","notify_serve"),
                 ("CloseBusiness","close_biz"),("OpenBusiness","open_biz"),
                 ("RestaurantTick","rest_tick"),("ApplySignOpen","sign_open"),
                 ("ApplySignClosed","sign_closed")):
    ev=find_custom(mge,name)
    R[key]=walk(ev) if ev else None

for name,key in (("ClearSeat","clear_seat"),("TrySeat","try_seat"),
                 ("PayAndClear","pay_and_clear"),("BeginEat","tbl_begin_eat"),
                 ("BeginEatOnly","tbl_begin_eat_only"),("TimeoutLeave","timeout")):
    ev=find_custom(tge,name)
    R[key]=walk(ev) if ev else None

# Find Set bIsOpenBusiness false chains
for n in mge.list_all_nodes():
    if title(n)!="Set bIsOpenBusiness": continue
    val=find_pin(n,"bIsOpenBusiness","Input")
    dv=""
    if val:
        try: dv=str(val.get_default_as_string()) if hasattr(val,"get_default_as_string") else str(getattr(val,"default_value",""))
        except: 
            try: dv=str(val.default_value)
            except: dv="?"
        links=val.list_connected_pins() or []
        if links: dv="LINKED:"+title(links[0].get_owning_node())
    # predecessors
    preds=[]
    for p in bel.list_all_pins(n):
        if "INPUT" in str(p.get_pin_direction()) and "exec" in str(p.get_pin_type_display_string()).lower():
            for c in p.list_connected_pins() or []:
                preds.append(title(c.get_owning_node()))
    then_next=[]
    tp=find_pin(n,"then","Output")
    if tp:
        for c in tp.list_connected_pins() or []:
            then_next.append(title(c.get_owning_node()))
    R["set_open_false"].append({"dv":dv,"preds":preds,"then":then_next,"chain":walk(n,12)})

# components on table
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary
comps=[]
for h in list(sub.k2_gather_subobject_data_for_blueprint(tbp) or []):
    data=sub.k2_find_subobject_data_from_handle(h)
    try:
        name=str(lib.get_variable_name(data) or "")
        obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
        comps.append({"name":name,"class":obj.get_class().get_name() if obj else "?"})
    except: pass
R["table_comps"]=comps
comps_m=[]
for h in list(sub.k2_gather_subobject_data_for_blueprint(mbp) or []):
    data=sub.k2_find_subobject_data_from_handle(h)
    try:
        name=str(lib.get_variable_name(data) or "")
        obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
        comps_m.append({"name":name,"class":obj.get_class().get_name() if obj else "?"})
    except: pass
R["mgr_comps"]=comps_m

# Call BeginEat / ClearSeat sites
calls=[]
for label,ge in (("mgr",mge),("tbl",tge)):
    for n in ge.list_all_nodes():
        t=title(n)
        if any(k in t for k in ("BeginEat","ClearSeat","PayAndClear","SERVE","OnGuestPaid")):
            calls.append({"where":label,"title":t,"cls":n.get_class().get_name()})
R["calls"]=calls[:60]

# mesh paths exist?
for p in ("/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Basket",
          "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate",
          "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Storage/SM_VMF_Prop_VegetableBasket"):
    R.setdefault("meshes",{})[p]=eas.does_asset_exist(p)

open(r"E:\UE\FarmSim25D\Saved\rest_dish_dayend_probe.json","w",encoding="utf-8").write(
    json.dumps(R,indent=2,ensure_ascii=False,default=str))
print(json.dumps(R,indent=2,ensure_ascii=False,default=str)[:12000])
