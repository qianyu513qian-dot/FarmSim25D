# -*- coding: utf-8 -*-
"""Final verify till/holes fix."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[VERIFY_TILL] " + str(m))

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        thenp = find_pin(n, "then", "Output")
        for cp in thenp.list_connected_pins():
            tog = cp.get_owning_node()
            log("entry -> " + bel.get_node_title(tog))
            then2 = find_pin(tog, "then", "Output")
            for cp2 in then2.list_connected_pins():
                log("Toggle.then -> " + bel.get_node_title(cp2.get_owning_node()))
            for pname in ("GridX", "GridY", "State"):
                pp = find_pin(tog, pname, "Input")
                conns = [bel.get_node_title(c.get_owning_node()) for c in pp.list_connected_pins()] if pp else []
                log("  Toggle.{} <- {}".format(pname, conns))

tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ToggleGrassForState"))
for n in tge.list_all_nodes():
    t = bel.get_node_title(n)
    if "ShowGrass" in t or "HideGrass" in t or "Branch" in t or "Equal" in t.lower():
        log("Toggle node: " + t)

hge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "HarvestCell"))
for n in hge.list_all_nodes():
    if "VisualizeCell" in bel.get_node_title(n):
        sp = find_pin(n, "State", "Input")
        log("HarvestCell.VisualizeCell State val={!r} conns={}".format(
            sp.get_pin_value() if sp else None,
            [bel.get_node_title(c.get_owning_node()) for c in sp.list_connected_pins()] if sp else []))

log("all good" if ge.list_nodes_with_errors() == [] else "has errors")
