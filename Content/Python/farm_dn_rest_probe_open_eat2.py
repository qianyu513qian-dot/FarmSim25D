# -*- coding: utf-8 -*-
"""Deep probe RestaurantTick + RefreshTableBubble + OrderList widget + open sign."""
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
            try: return str(getattr(p, fn)())[:80]
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

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def dump_chain(ge, name, limit=60):
    ev = find_custom(ge, name)
    if not ev: return None
    out = []
    for x in walk_then(ev, limit):
        pins = {}
        for p in bel.list_all_pins(x):
            d = pin_def(p)
            links = [title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in (p.list_connected_pins() or [])]
            if d or links:
                pins[str(p.get_pin_name())] = {"dir": str(p.get_pin_direction()), "def": d, "links": links[:6]}
        out.append({"t": title(x), "cls": x.get_class().get_name(), "pins": pins})
    return out

mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
REPORT["RestaurantTick"] = dump_chain(mge, "RestaurantTick", 80)
REPORT["RefreshOrderUI"] = dump_chain(mge, "RefreshOrderUI", 40)
REPORT["EnsureOrderUI"] = dump_chain(mge, "EnsureOrderUI", 30)

# Find open/close set bIsOpen
open_sets = []
for n in mge.list_all_nodes():
    t = title(n)
    if "bIsOpen" in t or "OpenBusiness" in t or "ApplySign" in t or "SetMinutes" in t or "FarmClock" in t or "GetMinutes" in t or "Minutes" in t:
        open_sets.append({"t": t, "cls": n.get_class().get_name()})
REPORT["open_related_nodes"] = open_sets

# HandlePlayerE / open sign branch for when open happens
REPORT["HandlePlayerE"] = dump_chain(mge, "HandlePlayerE", 50)

# ResetDayCounters callers
reset_callers = []
for n in mge.list_all_nodes():
    if title(n) == "ResetDayCounters":
        exe = find_pin(n, "execute", "Input")
        froms = [title(c.get_owning_node()) for c in (exe.list_connected_pins() or [])] if exe else []
        reset_callers.append({"cls": n.get_class().get_name(), "from": froms})
REPORT["ResetDayCounters_callers"] = reset_callers

tbp = eas.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
REPORT["RefreshTableBubble"] = dump_chain(tge, "RefreshTableBubble", 40)
REPORT["BeginEat"] = dump_chain(tge, "BeginEat", 30)

# WBP_RestOrderList graph
try:
    wbp = eas.load_asset(WBP)
    # widget blueprint
    graphs = []
    try:
        for gname in ("EventGraph", "UpdateOrders", "Refresh"):
            g = bel.find_graph(wbp, gname)
            if g:
                graphs.append(gname)
    except Exception as e:
        graphs.append("err:"+str(e)[:60])
    REPORT["wbp_graphs"] = graphs
    # list functions
    try:
        fns = [str(f) for f in bel.get_all_graphs(wbp)] if hasattr(bel, "get_all_graphs") else []
    except Exception:
        fns = []
    REPORT["wbp_fns"] = fns
    # member vars
    try:
        REPORT["wbp_vars"] = [str(n) for n in bel.list_member_variable_names(wbp, False)]
    except Exception as e:
        REPORT["wbp_vars_err"] = str(e)[:80]
    # dump event graph if any
    try:
        wge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(wbp))
        customs = []
        for n in wge.list_all_nodes():
            if n.get_class().get_name() in ("K2Node_CustomEvent", "K2Node_Event", "K2Node_FunctionEntry"):
                customs.append({"name": title(n), "chain": [title(x) for x in walk_then(n, 25)]})
        REPORT["wbp_customs"] = customs
    except Exception as e:
        REPORT["wbp_eg_err"] = str(e)[:120]
except Exception as e:
    REPORT["wbp_err"] = str(e)[:120]

# PrintString texts in RefreshTableBubble / RestaurantTick
texts = []
for section, data in (("tick", REPORT.get("RestaurantTick") or []), ("bubble", REPORT.get("RefreshTableBubble") or []), ("refresh", REPORT.get("RefreshOrderUI") or [])):
    for node in data:
        if node["t"] == "PrintString" or "DrawDebugString" in node["t"]:
            texts.append({"sec": section, "t": node["t"], "InString": (node["pins"].get("InString") or {}).get("def"), "Key": (node["pins"].get("Key") or {}).get("def"), "Text": (node["pins"].get("Text") or {}).get("def")})
REPORT["string_samples"] = texts

open(r"E:\UE\FarmSim25D\Saved\rest_probe_open_eat2.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print("ok deep probe")
