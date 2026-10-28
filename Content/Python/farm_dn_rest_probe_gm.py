# -*- coding: utf-8 -*-
import unreal, json
REPORT={}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

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

for n in mge.list_all_nodes():
    if "GetDisplayMinutes" in title(n):
        pins=[]
        for p in bel.list_all_pins(n):
            links=["{}.{}".format(title(c.get_owning_node()),c.get_pin_name()) for c in (p.list_connected_pins() or [])]
            pins.append({"name":str(p.get_pin_name()),"dir":str(p.get_pin_direction()),"type":str(p.get_pin_type_display_string())[:50],"links":links,"def":str(p.get_default_as_string())[:40] if hasattr(p,'get_default_as_string') else None})
        REPORT.setdefault("gm",[]).append(pins)
        # member path
        try:
            REPORT.setdefault("gm_func",[]).append(str(n.get_editor_property("function_reference")) if hasattr(n,"get_editor_property") else "?")
        except Exception as e:
            REPORT.setdefault("gm_func",[]).append(str(e)[:80])

# Find GetActorOfClass FarmClock near those
for n in mge.list_all_nodes():
    t=title(n)
    if "FarmClock" in t or "Clock" in t:
        REPORT.setdefault("clock_nodes",[]).append(t+":"+n.get_class().get_name())

# How open sign E sets open - find Contains RestMark_OpenSign
for n in mge.list_all_nodes():
    if title(n)=="Contains":
        for p in bel.list_all_pins(n):
            d=""
            try: d=str(p.get_default_as_string())
            except: pass
            if "Open" in d or "Sign" in d or "Rest" in d:
                REPORT.setdefault("contains",[]).append(d)

open(r"E:\UE\FarmSim25D\Saved\rest_probe_gm.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False)[:4000])
