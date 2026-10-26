# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
created=[]
for name in [
    "Game|SpawnActorfromClass",
    "Utilities|Casting|CastToBP_PlotVisual",
    "Utilities|Casting|CastToStaticMeshActor",
]:
    try:
        n = ge.create_node_from_name(name, unreal.Vector2D(30,30), [])
        if n and len(bel.list_all_pins(n))>0:
            unreal.log("OK {} class={} pins={}".format(name, n.get_class().get_name(), [str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
            created.append(n)
        else:
            unreal.log("NONE "+name)
            if n: created.append(n)
    except Exception as e:
        unreal.log("FAIL {}: {}".format(name,e))
if created: ge.remove_nodes(created)
