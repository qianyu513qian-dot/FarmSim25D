# -*- coding: utf-8 -*-
"""Probe Manager/Table for open-hint + eating UI batch."""
import unreal, json
REPORT = {}
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
R["mgr_vars"] = [str(n) for n in bel.list_member_variable_names(mbp, False)]
R["customs"] = []
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_CustomEvent":
        chain = [title(x) for x in walk_then(n, 40)]
        R["customs"].append({"name": title(n), "chain": chain[:40]})

for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "Tick" in title(n):
        R["event_tick_chain"] = [title(x) for x in walk_then(n, 60)]

interest = []
for n in mge.list_all_nodes():
    t = title(n)
    if any(k in t for k in ("BeginEat","Pay","Open","Close","IsOpen","IsRestaurant","Seat","Timeout","PrintDay","ApplySign","Refresh","Eating","Hint","Minutes","FarmClock","RestaurantTick","Day")):
        interest.append({"t": t, "cls": n.get_class().get_name()})
R["interest"] = interest[:150]

tbp = eas.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
R["tbl_vars"] = [str(n) for n in bel.list_member_variable_names(tbp, False)]
R["tbl_customs"] = []
for n in tge.list_all_nodes():
    if n.get_class().get_name() in ("K2Node_CustomEvent", "K2Node_Event", "K2Node_FunctionEntry"):
        chain = [title(x) for x in walk_then(n, 35)]
        R["tbl_customs"].append({"name": title(n), "cls": n.get_class().get_name(), "chain": chain[:35]})

rb = find_custom(tge, "RefreshTableBubble")
if rb:
    R["bubble_chain"] = [title(x) for x in walk_then(rb, 50)]
    detail = []
    for x in walk_then(rb, 50):
        pins = []
        for p in bel.list_all_pins(x):
            try:
                dval = str(p.get_default_as_string())[:60]
            except Exception:
                dval = "?"
            pins.append("{}:{} def={}".format(p.get_pin_name(), p.get_pin_direction(), dval))
        detail.append({"t": title(x), "cls": x.get_class().get_name(), "pins": pins[:24]})
    R["bubble_detail"] = detail[:50]

# BeginEat on table or manager
for ge_name, ge in (("mgr", mge), ("tbl", tge)):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and "BeginEat" in title(n):
            R[ge_name + "_BeginEat"] = [title(x) for x in walk_then(n, 40)]

# Order strip / UpdateOrderList
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_CustomEvent" and any(k in title(n) for k in ("Order", "UI", "Strip", "List")):
        R.setdefault("ui_events", []).append({"name": title(n), "chain": [title(x) for x in walk_then(n, 30)]})

out = r"E:\UE\FarmSim25D\Saved\rest_probe_open_eat.json"
open(out, "w", encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
REPORT.update(R)
print("wrote", out, "customs", len(R["customs"]), "tbl", len(R["tbl_customs"]))
