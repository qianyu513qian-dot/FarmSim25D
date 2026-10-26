# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Equal" in t.lower():
        for p in bel.list_all_pins(n):
            try:
                v = p.get_pin_value()
            except Exception:
                v = "?"
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            unreal.log("[EQ] {}.{} =[{}] conn={}".format(t, p.get_pin_name(), v, cps))
# Also check errors
unreal.log("[EQ] errors=" + str(len(ge.list_nodes_with_errors())))
