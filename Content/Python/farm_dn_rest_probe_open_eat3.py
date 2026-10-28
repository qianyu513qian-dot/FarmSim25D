# -*- coding: utf-8 -*-
"""Probe WBP tick, open-business setters, GetDisplayMinutes usages, bubble string build."""
import unreal, json
REPORT = {}
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
WBP = "/Game/Farm/UI/WBP_RestOrderList"

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def pin_def(p):
    if not p: return None
    for fn in ("get_default_as_string", "get_default_value", "get_pin_value"):
        if hasattr(p, fn):
            try: return str(getattr(p, fn)())[:100]
            except Exception: pass
    return None

def walk_then(start, max_d=80):
    thenp = find_pin(start, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen = []; ids = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in ids or d > max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then", "else", "Completed", "LoopBody"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d + 1))
    return seen

def dump_node(x):
    pins = {}
    for p in bel.list_all_pins(x):
        links = ["{}.{}".format(title(c.get_owning_node()), c.get_pin_name()) for c in (p.list_connected_pins() or [])]
        d = pin_def(p)
        if d or links:
            pins[str(p.get_pin_name())] = {"dir": str(p.get_pin_direction()), "def": d, "links": links[:8]}
    return {"t": title(x), "cls": x.get_class().get_name(), "pins": pins}

# WBP Event Tick full dump
wbp = eas.load_asset(WBP)
wge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(wbp))
tick = None
for n in wge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "Tick" in title(n):
        tick = n
REPORT["wbp_tick"] = [dump_node(x) for x in walk_then(tick, 80)] if tick else None
# Also dump ALL nodes around SetText for data links (not just exec walk)
settexts = []
for n in wge.list_all_nodes():
    if "SetText" in title(n) or "SetPercent" in title(n) or "Append" in title(n) or "Format" in title(n) or "bEating" in title(n) or "Patience" in title(n) or "CurrentOrder" in title(n) or "GetAllActors" in title(n) or "Table" in title(n):
        settexts.append(dump_node(n))
REPORT["wbp_interesting"] = settexts[:80]
REPORT["wbp_all_titles"] = [title(n) for n in wge.list_all_nodes()][:200]

# Manager: every Set bIsOpenBusiness and GetDisplayMinutes neighborhood
mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
sets = []
for n in mge.list_all_nodes():
    if title(n) == "Set bIsOpenBusiness":
        exe = find_pin(n, "execute", "Input")
        froms = [title(c.get_owning_node()) for c in (exe.list_connected_pins() or [])] if exe else []
        then = find_pin(n, "then", "Output")
        tos = [title(c.get_owning_node()) for c in (then.list_connected_pins() or [])] if then else []
        val = find_pin(n, "bIsOpenBusiness", "Input")
        sets.append({"from": froms, "to": tos, "val_def": pin_def(val), "val_links": ["{}.{}".format(title(c.get_owning_node()), c.get_pin_name()) for c in (val.list_connected_pins() or [])] if val else []})
REPORT["Set_bIsOpenBusiness"] = sets

mins = []
for n in mge.list_all_nodes():
    if "GetDisplayMinutes" in title(n) or (title(n) == "integer >= integer" or title(n) == "int >= int"):
        mins.append(dump_node(n))
    if title(n) in ("integer >= integer", "Int >= Int", "integer > integer", ">="):
        mins.append(dump_node(n))
REPORT["minutes_nodes"] = mins[:40]

# Also find comparisons involving 1020 / 1380
comps = []
for n in mge.list_all_nodes():
    for p in bel.list_all_pins(n):
        d = pin_def(p) or ""
        if d in ("1020", "1380", "17", "23", "1020.0", "1380.0") or "1020" in d or "1380" in d:
            comps.append({"node": title(n), "pin": str(p.get_pin_name()), "def": d, "cls": n.get_class().get_name()})
REPORT["literal_times"] = comps

# Table bubble: dump Append / Select / Branch / Get bEating around RefreshTableBubble
tbp = eas.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
bubble_nodes = []
for n in tge.list_all_nodes():
    t = title(n)
    if any(k in t for k in ("Append", "DrawDebugString", "Get bEating", "Get CurrentOrder", "Get Patience", "Select", "Format", "Conv_", "Get bOccupied", "Get bHasOrder", "Get bOrderPending")):
        bubble_nodes.append(dump_node(n))
REPORT["tbl_string_nodes"] = bubble_nodes[:60]

# Event Tick table eating branch
for n in tge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "Tick" in title(n):
        REPORT["tbl_tick_chain"] = [dump_node(x) for x in walk_then(n, 40)]

open(r"E:\UE\FarmSim25D\Saved\rest_probe_open_eat3.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print("ok probe3 wbp_tick", len(REPORT.get("wbp_tick") or []), "sets", len(sets), "times", comps)
