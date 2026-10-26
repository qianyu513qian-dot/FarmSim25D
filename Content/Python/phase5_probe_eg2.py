# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.load_asset(MGR)
graph = bel.find_graph(bp, "EventGraph")
unreal.log("graph=" + str(graph))
ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
unreal.log("ge=" + str(ge))
nodes = list(ge.list_all_nodes()) if ge else []
unreal.log("count=" + str(len(nodes)))
for n in nodes:
    unreal.log("N " + n.get_class().get_name() + " :: " + str(n))
