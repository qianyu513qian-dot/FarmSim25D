# -*- coding: utf-8 -*-
"""Find player mesh path; RestaurantTick chain; AddNewSubobject for WidgetComponent."""
import unreal

def log(m):
    unreal.log("[UI_C3] " + str(m))
    print("[UI_C3] " + str(m))

bel = unreal.BlueprintEditorLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

# Char CDO mesh via generated components
char = unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
handles = list(sub.k2_gather_subobject_data_for_blueprint(char) or [])
for i,h in enumerate(handles):
    data = sub.k2_find_subobject_data_from_handle(h)
    ex = data.export_text()
    if "Skeletal" in ex or "Mesh" in ex:
        log("H{} {}".format(i, ex[:350].replace("\n"," ")))

# Search all skeletal meshes
ar = unreal.AssetRegistryHelpers.get_asset_registry()
filter = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine","SkeletalMesh")], recursive_paths=True)
assets = ar.get_assets(filter)
log("skel count=" + str(len(list(assets or []))))
for a in list(assets or []):
    log("  SKEL " + str(a.package_name) + "/" + str(a.asset_name))

# Manager RestaurantTick - follow from custom event
mbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))

def title(n):
    return str(bel.get_node_title(n))

def find_pin(n, name, direction=None):
    for p in bel.list_all_pins(n):
        if name.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

tick_ev = None
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="RestaurantTick":
        tick_ev = n
        break
log("RestaurantTick=" + str(tick_ev))
if tick_ev:
    thenp = find_pin(tick_ev, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=set()
    while queue:
        cur,d = queue.pop(0)
        if id(cur) in seen or d>20: continue
        seen.add(id(cur))
        log("  "*d + title(cur) + " |" + cur.get_class().get_name())
        for pn in ("then","else","LoopBody","Completed"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d+1))

# BeginPlay manager
bp_ev = None
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in title(n):
        bp_ev = n
        break
log("Mgr BeginPlay=" + str(title(bp_ev) if bp_ev else None))
if bp_ev:
    thenp = find_pin(bp_ev, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=set(); 
    while queue:
        cur,d=queue.pop(0)
        if id(cur) in seen or d>12: continue
        seen.add(id(cur))
        log("  "*d + title(cur))
        for pn in ("then","else"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d+1))

# Try add WidgetComponent to Table
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
th = list(sub.k2_gather_subobject_data_for_blueprint(tbp) or [])
log("table handles=" + str(len(th)))
# parent = DefaultSceneRoot handle index 1 typically
parent = th[1] if len(th)>1 else th[0]
params = unreal.AddNewSubobjectParams()
params.blueprint_context = tbp
params.new_class = unreal.WidgetComponent
params.parent_handle = parent
params.conform_transform_to_parent = True
try:
    result = sub.add_new_subobject(params)
    log("add WidgetComponent result=" + str(result) + " type=" + str(type(result)))
except Exception as e:
    log("add WC " + str(e))

# Re-gather
th2 = list(sub.k2_gather_subobject_data_for_blueprint(tbp) or [])
log("table handles after=" + str(len(th2)))
for i,h in enumerate(th2):
    ex = sub.k2_find_subobject_data_from_handle(h).export_text()
    if "Widget" in ex:
        log("  WC [{}] {}".format(i, ex[:300].replace("\n"," ")))

log("DONE_C3")
