# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
# list_available_nodes
try:
    nodes = ge.list_available_nodes()
    unreal.log("available type={} len={}".format(type(nodes), len(nodes) if nodes else 0))
    hits=[]
    for n in nodes:
        s=str(n)
        sl=s.lower()
        if any(k in sl for k in ("spawn","cast","plotvisual","destroy actor","get all actors")):
            hits.append(s)
    unreal.log("hits="+str(hits[:80]))
    unreal.log("nhits="+str(len(hits)))
except Exception as e:
    unreal.log("list_available FAIL "+str(e))
    import traceback; unreal.log(traceback.format_exc())
# try list_nodes_of_class with DynamicCast after creating somehow
# retarget_node_class?
unreal.log("retarget doc="+str(ge.retarget_node_class.__doc__))
