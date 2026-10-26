# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary

def log(m): unreal.log("[VMF_OK] " + str(m))

# PlotVisual comps
bp = unreal.load_asset("/Game/Farm/Grid/BP_PlotVisual")
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sub.k2_gather_subobject_data_for_blueprint(bp):
    data = sub.k2_find_subobject_data_from_handle(h)
    try:
        vname = str(lib.get_variable_name(data) or "")
        obj = lib.get_associated_object(data) if hasattr(lib, "get_associated_object") else lib.get_object(data)
        if obj and "StaticMesh" in obj.get_class().get_name():
            sm = obj.get_editor_property("static_mesh")
            rel = obj.get_editor_property("relative_location")
            log("SMC {} mesh={} rel=({},{},{})".format(vname, sm.get_name() if sm else None, rel.x, rel.y, rel.z))
    except Exception as e:
        log("sub "+str(e))

# ApplyState titles
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyState"))
try:
    log("ApplyState errors="+str(len(ge.list_nodes_with_errors())))
    log("ApplyState warns="+str(len(ge.list_nodes_with_warnings())))
except Exception as e:
    log(str(e))

# VisualizeCell spawn class pin
gbp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
vge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "VisualizeCell"))
for n in vge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Spawn" in t:
        for p in bel.list_all_pins(n):
            val=""
            try: val=str(p.get_pin_value())
            except: pass
            log("spawn.{} = {!r}".format(p.get_pin_name(), val))
    if "VisualizeCell" == t or n.get_class().get_name()=="K2Node_FunctionEntry":
        for p in bel.list_all_pins(n):
            log("entry.{} dir={}".format(p.get_pin_name(), p.get_pin_direction()))

# vars
names=[str(x).split(".")[-1] for x in bel.list_member_variable_names(gbp)]
log("has PlotVisuals="+str("PlotVisuals" in names))
log("funcs="+str([str(f.name) for f in bel.list_functions(gbp)]))
