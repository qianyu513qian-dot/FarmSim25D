# -*- coding: utf-8 -*-
"""Deep-check pin defaults for OpenHint print, GAO class, eating concatenations."""
import unreal, json
REPORT={}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary

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

def dump_pins(n):
    out=[]
    for p in bel.list_all_pins(n):
        info={"name":str(p.get_pin_name()),"dir":str(p.get_pin_direction()),"type":str(p.get_pin_type_display_string())[:50]}
        for fn in ("get_default_as_string","get_default_value","get_pin_value","default_value"):
            if hasattr(p, fn):
                try:
                    v=getattr(p, fn)
                    info[fn]=str(v() if callable(v) else v)[:120]
                except Exception as e:
                    info[fn]="err:"+str(e)[:40]
        links=["{}.{}".format(title(c.get_owning_node()),c.get_pin_name()) for c in (p.list_connected_pins() or [])]
        if links: info["links"]=links[:6]
        out.append(info)
    return out

def walk_then(start, max_d=80):
    thenp=find_pin(start,"then","Output")
    q=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=[]; ids=set()
    while q:
        cur,d=q.pop(0)
        if id(cur) in ids or d>max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append((c.get_owning_node(),d+1))
    return seen

def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
tick=find_custom(mge,"RestaurantTick")
chain=walk_then(tick,100)
# Find the NEW GetAllActorsOfClass (last one in chain) and following PrintStrings
gaos=[n for n in chain if title(n)=="GetAllActorsOfClass"]
prints=[n for n in chain if title(n)=="PrintString"]
REPORT["gao_count"]=len(gaos)
if gaos:
    REPORT["last_gao"]=dump_pins(gaos[-1])
REPORT["tick_prints"]=[dump_pins(p) for p in prints[-3:]]

# GetDisplayMinutes in chain
for n in chain:
    if "GetDisplayMinutes" in title(n):
        REPORT["gdm"]=dump_pins(n)

tbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
rb=find_custom(tge,"RefreshTableBubble")
bchain=walk_then(rb,40)
REPORT["bubble_titles"]=[title(n) for n in bchain]
# All new-ish nodes: DrawDebugString, Concat, Print after eating branch
for n in bchain:
    if title(n) in ("DrawDebugString","PrintString") or "Concat" in title(n) or title(n)=="Append":
        REPORT.setdefault("bubble_nodes",[]).append({"t":title(n),"pins":dump_pins(n)})

# Also scan ALL Concat/Append for 用餐
for n in tge.list_all_nodes():
    if "Concat" in title(n) or title(n)=="Append":
        for p in bel.list_all_pins(n):
            for fn in ("get_default_as_string","get_default_value"):
                if hasattr(p,fn):
                    try:
                        v=str(getattr(p,fn)())
                        if v and v not in ("",):
                            REPORT.setdefault("all_concat_defs",[]).append({"t":title(n),"pin":str(p.get_pin_name()),"fn":fn,"v":v[:80]})
                    except Exception:
                        pass

open(r"E:\UE\FarmSim25D\Saved\rest_open_eat_pins.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False)[:7000])
