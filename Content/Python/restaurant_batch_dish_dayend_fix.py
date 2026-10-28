# -*- coding: utf-8 -*-
"""Fix: wire BeginEat->ShowTableDish and ClearSeat->HideTableDish after compile."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
R = {"steps": [], "errors": [], "ok": []}

def log(m):
    unreal.log("[DISHFIX] " + str(m)); print("[DISHFIX] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

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

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); R["errors"].append("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    if not ok: R["errors"].append("fail " + label)
    return ok

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def linear_last(ev, limit=30):
    cur = ev
    for _ in range(limit):
        tp = find_pin(cur, "then", "Output")
        if not tp: return cur, None
        links = tp.list_connected_pins() or []
        if not links: return cur, tp
        cur = links[0].get_owning_node()
    return cur, find_pin(cur, "then", "Output")

def already_calls(ge, ev_name, target_title):
    ev = find_custom(ge, ev_name)
    if not ev: return False
    cur = ev; seen = set()
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        if target_title == title(cur) or target_title in title(cur):
            if "Call" in cur.get_class().get_name() or cur.get_class().get_name() == "K2Node_CallFunction":
                return True
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
    return False

def walk_titles(ge, name, limit=25):
    ev = find_custom(ge, name)
    if not ev: return None
    out = []; cur = ev
    for _ in range(limit):
        out.append(title(cur))
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
    return out

TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
tbp = eas.load_asset(TBL)
mbp = eas.load_asset(MGR)
# ensure table compiled so Show/Hide are callable
bel.compile_blueprint(tbp)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

log("has Show " + str(find_custom(tge, "ShowTableDish") is not None))
log("has Hide " + str(find_custom(tge, "HideTableDish") is not None))

# Remove orphaned failed call nodes if any (CallFunction with no exec in)
orphans = []
for n in list(tge.list_all_nodes()):
    t = title(n)
    if t in ("ShowTableDish", "HideTableDish") and n.get_class().get_name() == "K2Node_CallFunction":
        # check if execute has incoming
        ex = find_pin(n, "execute", "Input")
        preds = (ex.list_connected_pins() or []) if ex else []
        if not preds:
            orphans.append(n)
            log("orphan call " + t)
if orphans:
    tge.remove_nodes(orphans)

# Wire BeginEat
if not already_calls(tge, "BeginEat", "ShowTableDish"):
    be = find_custom(tge, "BeginEat")
    last, term = linear_last(be)
    log("BeginEat last=" + title(last) + " term=" + str(term is not None))
    call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ShowTableDish")
    log("call Show type=" + (call.get_class().get_name() if call else "NONE"))
    if call:
        bel.set_node_pos(call, pos(bel.get_node_pos(last).x + 400, bel.get_node_pos(last).y + 80))
        ok = connect(term, find_pin(call, "execute", "Input"), "BeginEat->Show")
        if ok: R["ok"].append("BeginEat->Show")
else:
    log("BeginEat already wired"); R["ok"].append("BeginEat_already")

# Wire ClearSeat
if not already_calls(tge, "ClearSeat", "HideTableDish"):
    cs = find_custom(tge, "ClearSeat")
    last, term = linear_last(cs)
    log("ClearSeat last=" + title(last) + " term=" + str(term is not None))
    call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:HideTableDish")
    log("call Hide type=" + (call.get_class().get_name() if call else "NONE"))
    if call:
        bel.set_node_pos(call, pos(bel.get_node_pos(last).x + 400, bel.get_node_pos(last).y + 80))
        ok = connect(term, find_pin(call, "execute", "Input"), "ClearSeat->Hide")
        if ok: R["ok"].append("ClearSeat->Hide")
else:
    log("ClearSeat already wired"); R["ok"].append("ClearSeat_already")

bel.compile_blueprint(tbp)
bel.compile_blueprint(mbp)
R["table"] = str(tbp.get_editor_property("status"))
R["mgr"] = str(mbp.get_editor_property("status"))
log("table " + R["table"])
log("mgr " + R["mgr"])

R["v_BeginEat"] = walk_titles(tge, "BeginEat")
R["v_ClearSeat"] = walk_titles(tge, "ClearSeat")
R["v_pay_salad"] = walk_titles(mge, "OnGuestPaidSalad")
R["v_pay_stew"] = walk_titles(mge, "OnGuestPaidStew")

# Verify close chains: find Set bIsOpenBusiness false paths
close_chains = []
for n in mge.list_all_nodes():
    if title(n) != "ApplySignClosed" or n.get_class().get_name() != "K2Node_CallFunction":
        continue
    # walk then
    chain = [title(n)]; cur = n
    for _ in range(8):
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
        chain.append(title(cur))
    close_chains.append(chain)
R["close_chains"] = close_chains

open_chains = []
for n in mge.list_all_nodes():
    if title(n) != "ApplySignOpen" or n.get_class().get_name() != "K2Node_CallFunction":
        continue
    chain = [title(n)]; cur = n
    for _ in range(8):
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
        chain.append(title(cur))
    open_chains.append(chain)
R["open_chains"] = open_chains

errs = []
for n in tge.list_all_nodes():
    try:
        em = n.get_editor_property("error_msg")
        if em and str(em).strip():
            errs.append("tbl:" + title(n) + ":" + str(em)[:100])
    except: pass
R["tbl_errs"] = errs

if "ERROR" not in R["table"]:
    eas.save_asset(TBL)
if "ERROR" not in R["mgr"]:
    eas.save_asset(MGR)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

open(r"E:\UE\FarmSim25D\Saved\rest_dish_dayend_fix.json", "w", encoding="utf-8").write(
    json.dumps(R, indent=2, ensure_ascii=False, default=str))
print(json.dumps(R, indent=2, ensure_ascii=False, default=str)[:8000])
