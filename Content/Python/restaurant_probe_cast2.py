# -*- coding: utf-8 -*-
import unreal, json, inspect
bel=unreal.BlueprintEditorLibrary
mbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
print("cast doc", mge.cast.__doc__)
print("cast", mge.cast)
try:
    print("sig", inspect.signature(mge.cast))
except Exception as e:
    print("sig err", e)
# try call patterns
CHAR="/Game/TopDown/Blueprints/BP_TopDownCharacter"
gen=unreal.load_asset(CHAR).generated_class()
results=[]
for args in [
    (gen,),
    (gen, unreal.Vector2D(0,0)),
    ("BP_TopDownCharacter",),
]:
    try:
        n=mge.cast(*args)
        results.append({"args":str(args),"ok":n is not None,"t":bel.get_node_title(n) if n else None,"c":n.get_class().get_name() if n else None})
        if n:
            pins=[str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(n)]
            results[-1]["pins"]=pins
            mge.remove_nodes([n])
    except Exception as e:
        results.append({"args":str(args),"err":str(e)[:200]})
print(json.dumps(results,indent=2))
# Also try unreal.BlueprintGraphEditor.cast as static?
