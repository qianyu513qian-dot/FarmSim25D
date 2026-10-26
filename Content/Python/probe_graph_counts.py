# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
for fname in ("ApplyDayNightVisuals", "AdvanceDayGrowth", "GrowCell"):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    nodes = list(ge.list_all_nodes())
    titles = [str(bel.get_node_title(n)) for n in nodes]
    unreal.log("[CHK] {} count={} titles={}".format(fname, len(nodes), titles[:25]))
    print("[CHK] {} count={} titles={}".format(fname, len(nodes), titles[:25]))
