# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
created=[]
for name in [
    "Cast to BP_PlotVisual",
    "Cast To BP_PlotVisual",
    "Utilities|Cast to BP_PlotVisual",
    "Class|Cast to BP_PlotVisual",
    "Actor|Cast to BP_PlotVisual",
]:
    try:
        n = ge.create_node_from_name(name, unreal.Vector2D(10,10), [])
        if n and len(bel.list_all_pins(n))>0:
            unreal.log("OK {} pins={}".format(name, [str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
            created.append(n)
        else:
            unreal.log("NONE "+name)
            if n: created.append(n)
    except Exception as e:
        unreal.log("FAIL {}: {}".format(name,e))
# ge methods for cast
for m in dir(ge):
    if "cast" in m.lower() and not m.startswith("_"):
        unreal.log("ge."+m)
for m in dir(bel):
    if "cast" in m.lower() and not m.startswith("_"):
        unreal.log("bel."+m)
# Try add Actor Tag
for path in [
    "/Script/Engine.KismetArrayLibrary:Array_Add",
    "/Script/Engine.KismetArrayLibrary:Array_Clear",
    "/Script/Engine.KismetArrayLibrary:Array_Length",
    "/Script/Engine.GameplayStatics:GetActorOfClass",
]:
    try:
        n=ge.add_call_function_node(path)
        if n and len(bel.list_all_pins(n))>0:
            unreal.log("CALL {} {}".format(path.split(":")[-1],[str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
            created.append(n)
        else:
            unreal.log("empty "+path)
            if n: created.append(n)
    except Exception as e:
        unreal.log("FAIL "+str(e))
if created: ge.remove_nodes(created)
