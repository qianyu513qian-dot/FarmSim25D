# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
created=[]
# list ge methods with spawn/add
for m in dir(ge):
    if any(k in m.lower() for k in ("spawn","add_","create_","node")) and not m.startswith("_"):
        unreal.log("ge."+m)
# Try create K2Node_SpawnActorFromClass directly
try:
    n = ge.create_node_from_name("K2Node_SpawnActorFromClass", unreal.Vector2D(0,0), [])
    unreal.log("K2Node_SpawnActorFromClass -> "+str(n))
    if n:
        unreal.log("pins="+str([str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
        created.append(n)
except Exception as e:
    unreal.log("fail "+str(e))
# Schema actions?
for name in ["SpawnActor from Class", "Spawn Actor From Class", "spawn actor from class"]:
    try:
        n = ge.create_node_from_name(name, unreal.Vector2D(0,0), [])
        unreal.log("{} -> {}".format(name, n))
        if n:
            unreal.log("pins="+str([str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
            created.append(n)
    except Exception as e:
        unreal.log("{} FAIL {}".format(name,e))
# Dynamic cast node class
for cls_name in ["K2Node_DynamicCast", "K2Node_ClassDynamicCast", "EdGraphSchema_K2"]:
    try:
        cls = getattr(unreal, cls_name, None)
        unreal.log("{} = {}".format(cls_name, cls))
    except Exception as e:
        unreal.log(str(e))
if hasattr(unreal, "K2Node_DynamicCast"):
    try:
        # maybe ge has add_node
        for m in ("add_node", "create_node", "add_graph_node"):
            if hasattr(ge, m):
                unreal.log("has "+m)
    except Exception:
        pass
if created: ge.remove_nodes(created)
