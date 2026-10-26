# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary

def log(m):
    print("[MV] " + str(m))
    unreal.log("[MV] " + str(m))

cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(cbp, "EventGraph"))
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if t != "MakeVector":
        continue
    # only those feeding AddMovementInput
    feeds_move = False
    for p in bel.list_all_pins(n):
        for c in p.list_connected_pins():
            if bel.get_node_title(c.get_owning_node()) == "AddMovementInput":
                feeds_move = True
    if not feeds_move:
        continue
    vals = {}
    for p in bel.list_all_pins(n):
        try:
            vals[str(p.get_pin_name())] = str(p.get_pin_value())
        except Exception:
            vals[str(p.get_pin_name())] = "?"
        cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
        if cps:
            vals["conn_"+str(p.get_pin_name())] = cps
    log("MakeVector " + str(vals))

# Also check Init PlotStates on GridManager event graph
gbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
names = [str(x) for x in bel.list_graph_names(gbp)]
log("GM graphs: " + str(names))
for gname in names:
    if "Event" in gname or "Begin" in gname or "Construct" in gname:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, gname))
        if not ge:
            continue
        for n in ge.list_all_nodes():
            log("GM[{}] {}".format(gname, bel.get_node_title(n)))

# ApplyState dry mesh
pv = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_PlotVisual")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(pv, "ApplyState"))
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Mesh" in t or "Soil" in t or "Switch" in t or "Apply" in t or "Set Static" in t:
        log("ApplyState " + t)
        for p in bel.list_all_pins(n):
            try:
                v = str(p.get_pin_value())
            except Exception:
                v = ""
            if v and v not in ("0", "False", "None", ""):
                log("  {}={}".format(p.get_pin_name(), v[:120]))
log("DONE")
