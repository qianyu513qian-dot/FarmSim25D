# -*- coding: utf-8 -*-
"""Verify OpenEatUI_v1 wiring."""
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

def pin_def(p):
    if not p: return ""
    try: return str(p.get_default_as_string())
    except: return ""

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

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
tick=find_custom(mge,"RestaurantTick")
REPORT["tick_chain"]=[title(n) for n in walk_then(tick,100)]
REPORT["vars"]=[str(n) for n in bel.list_member_variable_names(mbp,False) if "Hint" in str(n) or "Open" in str(n)]
hints=[]
for n in mge.list_all_nodes():
    if title(n)=="PrintString" and pin_def(find_pin(n,"Key","Input"))=="RestOpenHint":
        hints.append({"text":pin_def(find_pin(n,"InString","Input")),"dur":pin_def(find_pin(n,"Duration","Input"))})
REPORT["open_hints"]=hints

aos=find_custom(mge,"ApplySignOpen")
REPORT["open_chain"]=[title(n) for n in walk_then(aos,15)]

tbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
rb=find_custom(tge,"RefreshTableBubble")
REPORT["bubble_chain"]=[title(n) for n in walk_then(rb,40)]
eat_bits=[]
for n in tge.list_all_nodes():
    if title(n)=="DrawDebugString":
        eat_bits.append({"dds_text":pin_def(find_pin(n,"Text","Input"))})
    if title(n) in ("Append","Concat_StrStr") or "Concat" in title(n):
        for p in bel.list_all_pins(n):
            d=pin_def(p)
            if "用餐" in d or "RestOrder" in d or d=="桌":
                eat_bits.append({"node":title(n),"pin":str(p.get_pin_name()),"def":d})
    if title(n)=="PrintString":
        d=pin_def(find_pin(n,"InString","Input"))
        if "用餐" in d:
            eat_bits.append({"print":d,"key":pin_def(find_pin(n,"Key","Input"))})
REPORT["eat_bits"]=eat_bits
try:
    REPORT["mgr_errs"]=[title(n) for n in (mge.list_nodes_with_errors() or [])]
    REPORT["tbl_errs"]=[title(n) for n in (tge.list_nodes_with_errors() or [])]
except Exception as e:
    REPORT["errlist"]=str(e)

# Confirm GetDisplayMinutes self linked
for n in walk_then(tick,100):
    if "GetDisplayMinutes" in title(n):
        sp=find_pin(n,"self","Input")
        REPORT["gdm_self"]=[title(c.get_owning_node()) for c in (sp.list_connected_pins() or [])] if sp else None
    if title(n)=="GetAllActorsOfClass":
        cp=find_pin(n,"ActorClass","Input")
        REPORT["gao_class"]=pin_def(cp)

open(r"E:\UE\FarmSim25D\Saved\rest_open_eat_verify.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False)[:5000])
