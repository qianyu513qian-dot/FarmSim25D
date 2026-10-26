# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
unreal.log("ge.cast doc="+str(ge.cast.__doc__))
unreal.log("ge.cast="+str(ge.cast))
# try calling
pv = unreal.load_asset("/Game/Farm/Grid/BP_PlotVisual")
cls = pv.generated_class()
created=[]
for args in [
    (cls,),
    (cls, unreal.Vector2D(0,0)),
    ("/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C",),
]:
    try:
        n = ge.cast(*args)
        unreal.log("cast{} -> {} pins={}".format(args, n, [str(p.get_pin_name()) for p in bel.list_all_pins(n)] if n else None))
        if n: created.append(n)
    except Exception as e:
        unreal.log("cast{} FAIL {}".format(args, e))
# try inspect signature via unreal reflection
try:
    import inspect
    unreal.log("sig="+str(inspect.signature(ge.cast)))
except Exception as e:
    unreal.log("inspect "+str(e))
if created: ge.remove_nodes(created)
