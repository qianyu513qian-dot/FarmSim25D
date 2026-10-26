# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    unreal.log("[N] " + t)
    if "Byte" in t or "Equal" in t or "==" in t or "Set Array" in t or "Visualize" in t or "IsValid" in t:
        for p in bel.list_all_pins(n):
            try:
                v = str(p.get_pin_value())
            except Exception:
                v = "?"
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            if cps or v not in ("", "?", "0", "false", "False"):
                unreal.log("   {}.{} =[{}] <-{}".format(t, p.get_pin_name(), v, cps[:3]))
