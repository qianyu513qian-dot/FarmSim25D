# -*- coding: utf-8 -*-
"""Probe VisualizeCell Z offset, HideGrassAt, HarvestCell."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[PROBE_TILL] " + str(m))


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


bp = unreal.load_asset(MGR)
graphs = [g.get_name() for g in bel.get_all_graphs(bp)] if hasattr(bel, "get_all_graphs") else []
log("graphs_sample=" + str(graphs[:40] if graphs else "n/a"))

# List function graphs via find
for fname in ("VisualizeCell", "HideGrassAt", "ShowGrassAt", "HarvestCell", "TillCell", "VisualizeCellBody"):
    g = bel.find_graph(bp, fname)
    log("find_graph {} = {}".format(fname, bool(g)))

ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))
log("=== VisualizeCell nodes ===")
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    cls = n.get_class().get_name()
    log("  [{}] {}".format(cls, t))
    if "Make Vector" in t or t == "MakeVector" or "MakeVector" in cls:
        for axis in ("X", "Y", "Z"):
            p = find_pin(n, axis, "Input")
            if p:
                log("    {}={}".format(axis, p.get_pin_value()))
    if "HideGrass" in t or "ShowGrass" in t:
        for p in bel.list_all_pins(n):
            conns = []
            for cp in p.list_connected_pins():
                conns.append("{}@{}".format(cp.get_pin_name(), bel.get_node_title(cp.get_owning_node())))
            log("    pin {} dir={} -> {}".format(p.get_pin_name(), p.get_pin_direction(), conns))

# Entry then connections
entry = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
if entry:
    thenp = find_pin(entry, "then", "Output")
    if thenp:
        for cp in thenp.list_connected_pins():
            log("entry.then -> {} ({})".format(bel.get_node_title(cp.get_owning_node()), cp.get_pin_name()))

# HideGrassAt dump
hg = bel.find_graph(bp, "HideGrassAt")
if hg:
    hge = unreal.BlueprintGraphEditor.get_graph_editor(hg)
    log("=== HideGrassAt nodes ({}) errs={} ===".format(len(list(hge.list_all_nodes())), len(hge.list_nodes_with_errors())))
    for n in hge.list_all_nodes():
        log("  " + bel.get_node_title(n))
    for n in hge.list_nodes_with_errors():
        log("  ERR " + bel.get_node_title(n))

# HarvestCell viz call
hcg = bel.find_graph(bp, "HarvestCell")
if hcg:
    hcge = unreal.BlueprintGraphEditor.get_graph_editor(hcg)
    log("=== HarvestCell VisualizeCell calls ===")
    for n in hcge.list_all_nodes():
        t = bel.get_node_title(n)
        if "VisualizeCell" in t:
            log("  " + t)
            for p in bel.list_all_pins(n):
                if "state" in str(p.get_pin_name()).lower() or "grid" in str(p.get_pin_name()).lower():
                    conns = [bel.get_node_title(cp.get_owning_node()) for cp in p.list_connected_pins()]
                    log("    {} val={} conns={}".format(p.get_pin_name(), p.get_pin_value() if hasattr(p, "get_pin_value") else "?", conns))

# Sample grass Z
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
n = 0
for a in actors:
    try:
        lab = a.get_actor_label()
    except Exception:
        continue
    if "VMF_Grass_" in str(lab):
        loc = a.get_actor_location()
        log("grass {} loc=({},{},{})".format(lab, loc.x, loc.y, loc.z))
        n += 1
        if n >= 5:
            break

log("DONE probe")
