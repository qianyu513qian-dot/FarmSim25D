# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[AS] " + str(m)); print("[AS] " + str(m))

def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

pv = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_PlotVisual")
age = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(pv, "ApplyState"))
for n in age.list_all_nodes():
    t = bel.get_node_title(n)
    if "equal" in t.lower() or t in ("Branch", "SetHiddenInGame", "Set Visibility"):
        for p in bel.list_all_pins(n):
            val=""
            try: val=str(p.get_pin_value())
            except: pass
            cps=[(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            log("{}.{} =[{}] <-{}".format(t, p.get_pin_name(), val, cps[:4]))

# Also dump which AMI gets which MakeVector by matching pin object links
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
log("=== MOVE PAIRING ===")
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "AddMovementInput":
        continue
    wd = find_pin(n, "WorldDirection", "Input")
    sc = find_pin(n, "ScaleValue", "Input")
    wd_src = []
    sc_src = []
    if wd:
        for c in wd.list_connected_pins():
            own = c.get_owning_node()
            vals={}
            for p in bel.list_all_pins(own):
                try: vals[str(p.get_pin_name())]=str(p.get_pin_value())
                except: pass
            wd_src.append((bel.get_node_title(own), vals))
    if sc:
        for c in sc.list_connected_pins():
            sc_src.append((bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())))
    log("AMI WorldDir from {} Scale from {}".format(wd_src, sc_src))

# Camera component variable name
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sub.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp)
    if obj:
        log("sub {} class={}".format(name, obj.get_class().get_name()))
