# -*- coding: utf-8 -*-
"""Probe Manager/Table for open-hint + eating UI batch."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"

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

def walk_then(start, max_d=50):
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

R = {}

mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
vars = [str(n) for n in bel.list_member_variable_names(mbp, False)]
R["mgr_vars"] = vars
R["customs"] = []
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_CustomEvent":
        chain = [title(x) for x in walk_then(n, 40)]
        R["customs"].append({"name": title(n), "chain": chain[:40]})

# Event Tick chain
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "Tick" in title(n):
        R["event_tick_chain"] = [title(x) for x in walk_then(n, 60)]

# Look for BeginEat, Pay, Open, Close, IsOpen
interest = []
for n in mge.list_all_nodes():
    t = title(n)
    if any(k in t for k in ("BeginEat","Pay","Open","Close","IsOpen","IsRestaurant","Seat","Timeout","PrintDay","ApplySign","Refresh","Eating","Hint","Minutes","FarmClock")):
        interest.append({"t": t, "cls": n.get_class().get_name()})
R["interest"] = interest[:120]

# Table customs
tbp = eas.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
R["tbl_vars"] = [str(n) for n in bel.list_member_variable_names(tbp, False)]
R["tbl_customs"] = []
for n in tge.list_all_nodes():
    if n.get_class().get_name() in ("K2Node_CustomEvent", "K2Node_Event", "K2Node_FunctionEntry"):
        chain = [title(x) for x in walk_then(n, 35)]
        R["tbl_customs"].append({"name": title(n), "cls": n.get_class().get_name(), "chain": chain[:35]})

# RefreshTableBubble detail
rb = find_custom(tge, "RefreshTableBubble")
if rb:
    R["bubble_chain"] = [title(x) for x in walk_then(rb, 50)]
    # Also dump SetText / DrawDebug / Branch conditions roughly
    detail = []
    for x in walk_then(rb, 50):
        pins = []
        for p in bel.list_all_pins(x):
            pins.append("{}:{} def={}".format(p.get_pin_name(), p.get_pin_direction(), str(p.get_default_as_string())[:40] if hasattr(p,'get_default_as_string') else "?"))
        detail.append({"t": title(x), "cls": x.get_class().get_name(), "pins": pins[:20]})
    R["bubble_detail"] = detail[:40]

open(r"E:\UE\FarmSim25D\Saved\rest_probe_open_eat.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False))
print("wrote probe; customs=", len(R["customs"]), "tbl=", len(R["tbl_customs"]))
