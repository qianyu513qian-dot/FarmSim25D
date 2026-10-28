# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
out=[]
for cname in ["integer >= integer","int >= int","float >= float","double >= double","integer < integer","float + float","double + double"]:
    try:
        n=mge.create_node_from_name(cname, unreal.Vector2D(0,0), [])
        out.append({"n":cname,"ok":n is not None,"title":bel.get_node_title(n) if n else None,"cls":n.get_class().get_name() if n else None})
        if n: mge.remove_nodes([n])
    except Exception as e:
        out.append({"n":cname,"err":str(e)[:100]})
# Less_IntInt / GreaterEqual via exact
for path in ["/Script/Engine.KismetMathLibrary:Less_IntInt","/Script/Engine.KismetMathLibrary:Greater_IntInt","/Script/Engine.KismetMathLibrary:EqualEqual_IntInt"]:
    try:
        n=mge.add_call_function_node(path)
        out.append({"n":path,"title":bel.get_node_title(n) if n else None,"pins":[str(p.get_pin_name()) for p in bel.list_all_pins(n)] if n else []})
        if n: mge.remove_nodes([n])
    except Exception as e:
        out.append({"n":path,"err":str(e)[:80]})
# gdm type
gdm=mge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
for p in bel.list_all_pins(gdm):
    out.append({"gdm":str(p.get_pin_name()),"disp":str(p.get_pin_type_display_string())})
mge.remove_nodes([gdm])
# Does OpenSign have RestaurantInteract function graph?
osp=unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantOpenSign")
graphs=[]
# list graphs
for meth in ["get_all_graphs","list_graphs"]:
    if hasattr(bel,meth):
        try:
            graphs=[str(x) for x in getattr(bel,meth)(osp)]
        except Exception as e:
            graphs.append(str(e))
# find_graph
for gname in ["RestaurantInteract","EventGraph","UserConstructionScript"]:
    g=bel.find_graph(osp,gname)
    graphs.append({"name":gname,"found":g is not None})
print(json.dumps(out+[{"graphs":graphs}],indent=2))
