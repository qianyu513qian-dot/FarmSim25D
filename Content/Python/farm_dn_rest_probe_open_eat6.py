# -*- coding: utf-8 -*-
"""How GetDisplayMinutes is obtained; FarmClock API; marker idempotency."""
import unreal, json
REPORT={}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"

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

def pin_def(p):
    if not p: return None
    for fn in ("get_default_as_string","get_default_value"):
        if hasattr(p,fn):
            try: return str(getattr(p,fn)())[:100]
            except: pass
    return None

def dump(n):
    pins={}
    for p in bel.list_all_pins(n):
        links=["{}.{}".format(title(c.get_owning_node()),c.get_pin_name()) for c in (p.list_connected_pins() or [])]
        d=pin_def(p)
        if d or links: pins[str(p.get_pin_name())]={"def":d,"links":links[:8],"type":str(p.get_pin_type_display_string())[:40]}
    return {"t":title(n),"cls":n.get_class().get_name(),"pins":pins}

mbp=eas.load_asset(MGR); mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
gm=[]
for n in mge.list_all_nodes():
    if "GetDisplayMinutes" in title(n) or "FarmClock" in title(n) or "GetActorOfClass" in title(n) or "Get All Actors of Class" in title(n) or "GetAllActorsOfClass" in title(n):
        if "FarmClock" in title(n) or "GetDisplayMinutes" in title(n) or "Clock" in title(n):
            gm.append(dump(n))
REPORT["clock_gets"]=gm

# Find FarmClock class path from C++
REPORT["farmclock_h"]=open(r"E:\UE\FarmSim25D\Source\FarmSim25D\FarmClock.h",encoding="utf-8",errors="replace").read()[:2500]

# Marker prints already
markers=[]
for n in mge.list_all_nodes():
    if title(n)=="PrintString":
        k=pin_def(find_pin(n,"Key","Input")) or ""
        s=pin_def(find_pin(n,"InString","Input")) or ""
        if "Marker" in k or "OpenHint" in k or "v1" in s or "Hint" in s:
            markers.append({"k":k,"s":s})
REPORT["markers"]=markers

# RestaurantTick terminal then pin
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="RestaurantTick":
        # walk to end
        cur=n; last=n
        for _ in range(40):
            tp=find_pin(cur,"then","Output")
            if not tp: break
            ls=list(tp.list_connected_pins() or [])
            # also else branches - just follow then of first path; find nodes with empty then
            if not ls:
                last=cur; break
            # prefer continuing SyncHeldMesh path - take first
            cur=ls[0].get_owning_node(); last=cur
        REPORT["tick_last"]=title(last)
        REPORT["tick_last_dump"]=dump(last)

# Table: how TableId used in Append for RestOrder key
tbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
app=[]
for n in tge.list_all_nodes():
    if title(n)=="Append":
        app.append(dump(n))
REPORT["appends"]=app[:20]

# String To Name for key
stn=[]
for n in tge.list_all_nodes():
    if "String To Name" in title(n) or "Conv_StringToName" in title(n) or title(n)=="To Name (String)":
        stn.append(dump(n))
REPORT["string_to_name"]=stn

open(r"E:\UE\FarmSim25D\Saved\rest_probe_open_eat6.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print("gm",len(gm),"markers",markers,"tick_last",REPORT.get("tick_last"))

