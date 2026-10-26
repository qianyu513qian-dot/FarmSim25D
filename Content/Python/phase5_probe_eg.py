# -*- coding: utf-8 -*-
"""Probe EventGraph BeginPlay nodes only — read-only."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.load_asset(MGR)
graph = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
for n in ge.list_all_nodes():
    t = n.get_class().get_name()
    title = ""
    try:
        title = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
    except Exception:
        title = str(n)
    if any(k in (t + title).lower() for k in ("begin", "tick", "timer", "plot", "forloop", "custom")):
        unreal.log("NODE {} | {} | pos={}".format(t, title, bel.get_node_pos(n) if hasattr(bel, "get_node_pos") else "?"))
        for p in bel.list_all_pins(n):
            if "exec" in str(p.get_pin_name()).lower() or "then" in str(p.get_pin_name()).lower():
                unreal.log("  pin {} {}".format(p.get_pin_name(), p.get_pin_direction()))
