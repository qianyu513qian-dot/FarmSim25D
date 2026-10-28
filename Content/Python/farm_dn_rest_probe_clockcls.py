# -*- coding: utf-8 -*-
"""Probe how T-key gets FarmClock; test load_class for FarmClock."""
import unreal, json
REPORT={}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary

# load FarmClock class
paths=[
    "/Script/FarmSim25D.FarmClock",
    "/Script/FarmSim25D.FarmClock_C",
]
for p in paths:
    try:
        c=unreal.load_class(None, p)
        REPORT[p]=str(c)
    except Exception as e:
        REPORT[p]="err:"+str(e)[:80]
    try:
        o=unreal.load_object(None, p)
        REPORT[p+"_obj"]=str(o)
    except Exception as e:
        REPORT[p+"_obj"]="err:"+str(e)[:80]

# Character skip to 17 graph
cbp=eas.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()
def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None
hits=[]
for n in cge.list_all_nodes():
    t=title(n)
    if "FarmClock" in t or "GetDisplay" in t or "SkipTo17" in t or "1020" in t or "RestoreClock" in t or "Minutes" in t:
        pins={}
        for p in bel.list_all_pins(n):
            links=["{}.{}".format(title(c.get_owning_node()),c.get_pin_name()) for c in (p.list_connected_pins() or [])]
            try: d=str(p.get_default_as_string())[:60]
            except: d=""
            if links or d:
                pins[str(p.get_pin_name())]={"def":d,"links":links[:6]}
        hits.append({"t":t,"cls":n.get_class().get_name(),"pins":pins})
REPORT["char_hits"]=hits[:40]

# Does ge have add_cast_node
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")))
REPORT["has_add_cast"]=hasattr(mge,"add_cast_node")
cls=unreal.load_class(None,"/Script/FarmSim25D.FarmClock")
REPORT["cls"]=str(cls)
if hasattr(mge,"add_cast_node") and cls:
    # don't leave orphan - just test? skip create
    pass

# Check GetAllActorsOfClass ActorClass default for FarmClock in char
for n in cge.list_all_nodes():
    if "GetAllActorsOfClass" in title(n):
        cp=find_pin(n,"ActorClass","Input")
        try: d=str(cp.get_default_as_string()) if cp else ""
        except: d=""
        REPORT.setdefault("gao_classes",[]).append(d)

open(r"E:\UE\FarmSim25D\Saved\rest_probe_clockcls.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False)[:4500])
