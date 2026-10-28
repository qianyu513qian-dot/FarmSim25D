# -*- coding: utf-8 -*-
"""Manager Receive* + Table TryClaimCook / PushContext / BeginEatIfActive / WrongLeaveIfActive; rewire skips."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {"steps": [], "errors": [], "statuses": {}}

def log(m):
    unreal.log("[K3RT] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def out_data(node):
    if not node:
        return None
    for name in ("ReturnValue", "Item", "TableId", "CurrentDishId", "bOrderPending", "bOccupied", "bEating",
                 "bCooking", "bCookReady", "HeldDishId", "HeldTableId"):
        p = find_pin(node, name, "Output")
        if p:
            return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            if str(p.get_pin_name()).lower() not in ("outputdelegate", "then", "completed", "loopbody"):
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok)); return ok

def setdef(pin, val):
    if not pin:
        return
    try:
        pin.set_pin_value(str(val))
    except Exception:
        try:
            pin.set_default_value(str(val))
        except Exception:
            pass

def make_print(ge, x, y, text):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), "2.5")
    return pr

def eq_int(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(n, pos(x, y)); return n

def compile_save(bp, path, key):
    bel.compile_blueprint(bp)
    st = str(bp.get_editor_property("status"))
    R["statuses"][key] = st
    if "ERROR" in st:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
        for n in ge.list_all_nodes():
            try:
                em = n.get_editor_property("error_msg")
                if em and str(em).strip():
                    R["errors"].append(key + ":" + bel.get_node_title(n) + ": " + str(em)[:200])
            except Exception:
                pass
    else:
        unreal.EditorAssetLibrary.save_asset(path)
    return st

# ========== Manager Receive* ==========
MP = "/Game/Farm/Restaurant/BP_RestaurantManager"
mbp = unreal.EditorAssetLibrary.load_asset(MP)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# remove old Receive*
kill = [n for n in mge.list_all_nodes()
        if n.get_class().get_name() == "K2Node_CustomEvent"
        and bel.get_node_title(n) in ("ReceiveSalad1", "ReceiveSalad2", "ReceiveStew1", "ReceiveStew2")]
if kill:
    mge.remove_nodes(kill)

def recv(name, dish, table, order, y):
    ev = mge.add_custom_event_node(name)
    bel.set_node_pos(ev, pos(0, y))
    prev = find_pin(ev, "then", "Output")
    x = 300
    for vn, vv in [("HeldDishId", str(dish)), ("HeldTableId", str(table)), ("HeldOrder", order)]:
        sn = mge.add_set_member_variable_node(vn)
        bel.set_node_pos(sn, pos(x, y))
        connect(prev, find_pin(sn, "execute", "Input"), name + vn)
        setdef(find_pin(sn, vn, "Input"), vv)
        prev = find_pin(sn, "then", "Output")
        x += 280
    pr = make_print(mge, x, y, "Restaurant HOLD {} for Table{} — go serve".format(order, table))
    connect(prev, find_pin(pr, "execute", "Input"), name + "pr")

recv("ReceiveSalad1", 1, 1, "TomatoSalad", 4200)
recv("ReceiveSalad2", 1, 2, "TomatoSalad", 4450)
recv("ReceiveStew1", 2, 1, "Stew", 4700)
recv("ReceiveStew2", 2, 2, "Stew", 4950)
compile_save(mbp, MP, "manager_recv")

# ========== Table events ==========
TP = "/Game/Farm/Restaurant/BP_RestaurantTable"
tbp = unreal.EditorAssetLibrary.load_asset(TP)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))

kill = [n for n in tge.list_all_nodes()
        if n.get_class().get_name() == "K2Node_CustomEvent"
        and bel.get_node_title(n) in ("TryClaimCook", "PushContextAndEval", "BeginEatIfActive", "WrongLeaveIfActive")]
if kill:
    tge.remove_nodes(kill)

Y = 3200

# TryClaimCook: if pending & occupied & !eating → start matching stove cook (only if stove idle checked inside Start*)
tc = tge.add_custom_event_node("TryClaimCook")
bel.set_node_pos(tc, pos(0, Y))
get_p = tge.add_get_member_variable_node("bOrderPending"); bel.set_node_pos(get_p, pos(250, Y + 80))
get_o = tge.add_get_member_variable_node("bOccupied"); bel.set_node_pos(get_o, pos(250, Y + 160))
get_e = tge.add_get_member_variable_node("bEating"); bel.set_node_pos(get_e, pos(250, Y + 240))
and1 = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
bel.set_node_pos(and1, pos(500, Y + 100))
connect(out_data(get_p), find_pin(and1, "A", "Input"), "p")
connect(out_data(get_o), find_pin(and1, "B", "Input"), "o")
not_e = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
bel.set_node_pos(not_e, pos(500, Y + 240))
connect(out_data(get_e), find_pin(not_e, "A", "Input"), "ne")
and2 = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
bel.set_node_pos(and2, pos(750, Y + 140))
connect(out_data(and1), find_pin(and2, "A", "Input"), "a1")
connect(out_data(not_e), find_pin(and2, "B", "Input"), "a2")
br = tge.add_branch_node(); bel.set_node_pos(br, pos(1000, Y))
connect(find_pin(tc, "then", "Output"), find_pin(br, "execute", "Input"), "tc")
connect(out_data(and2), find_pin(br, "Condition", "Input"), "ok")

# branch dish + table
get_d = tge.add_get_member_variable_node("CurrentDishId"); bel.set_node_pos(get_d, pos(1250, Y + 50))
eqd = eq_int(tge, 1500, Y + 50)
connect(out_data(get_d), find_pin(eqd, "A", "Input"), "d")
setdef(find_pin(eqd, "B", "Input"), "1")
brd = tge.add_branch_node(); bel.set_node_pos(brd, pos(1750, Y))
connect(find_pin(br, "then", "Output"), find_pin(brd, "execute", "Input"), "dish")
connect(out_data(eqd), find_pin(brd, "Condition", "Input"), "salad")

get_tid = tge.add_get_member_variable_node("TableId"); bel.set_node_pos(get_tid, pos(2000, Y - 50))
eqt = eq_int(tge, 2250, Y - 50)
connect(out_data(get_tid), find_pin(eqt, "A", "Input"), "tid")
setdef(find_pin(eqt, "B", "Input"), "1")
brt = tge.add_branch_node(); bel.set_node_pos(brt, pos(2500, Y - 80))
connect(find_pin(brd, "then", "Output"), find_pin(brt, "execute", "Input"), "t")
connect(out_data(eqt), find_pin(brt, "Condition", "Input"), "t1")

def call_stove_start(ge, exec_pin, event_name, x, y):
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(x, y))
    connect(exec_pin, find_pin(gao, "execute", "Input"), event_name)
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C")
    get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(x + 280, y + 70))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), event_name + "a")
    setdef(find_pin(get0, "Index", "Input"), "0")
    call = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:" + event_name)
    bel.set_node_pos(call, pos(x + 520, y))
    connect(find_pin(gao, "then", "Output"), find_pin(call, "execute", "Input"), event_name + "c")
    connect(find_pin(get0, "Item", "Output"), find_pin(call, "self", "Input"), event_name + "s")

call_stove_start(tge, find_pin(brt, "then", "Output"), "StartSalad1", 2800, Y - 120)
call_stove_start(tge, find_pin(brt, "else", "Output"), "StartSalad2", 2800, Y + 80)

get_tid2 = tge.add_get_member_variable_node("TableId"); bel.set_node_pos(get_tid2, pos(2000, Y + 220))
eqt2 = eq_int(tge, 2250, Y + 220)
connect(out_data(get_tid2), find_pin(eqt2, "A", "Input"), "tid2")
setdef(find_pin(eqt2, "B", "Input"), "1")
brt2 = tge.add_branch_node(); bel.set_node_pos(brt2, pos(2500, Y + 200))
connect(find_pin(brd, "else", "Output"), find_pin(brt2, "execute", "Input"), "stew")
connect(out_data(eqt2), find_pin(brt2, "Condition", "Input"), "st1")
call_stove_start(tge, find_pin(brt2, "then", "Output"), "StartStew1", 2800, Y + 180)
call_stove_start(tge, find_pin(brt2, "else", "Output"), "StartStew2", 2800, Y + 380)

# PushContextAndEval
pc = tge.add_custom_event_node("PushContextAndEval")
bel.set_node_pos(pc, pos(0, Y + 600))
# Get manager
gaom = tge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gaom, pos(300, Y + 600))
connect(find_pin(pc, "then", "Output"), find_pin(gaom, "execute", "Input"), "pc")
setdef(find_pin(gaom, "ActorClass", "Input") or find_pin(gaom, "Class", "Input"),
       "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
getm = tge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(getm, pos(600, Y + 680))
connect(find_pin(gaom, "OutActors", "Output"), find_pin(getm, "TargetArray", "Input"), "marr")
setdef(find_pin(getm, "Index", "Input"), "0")

# table id branch -> CtxTable*
get_tid3 = tge.add_get_member_variable_node("TableId"); bel.set_node_pos(get_tid3, pos(600, Y + 560))
eqt3 = eq_int(tge, 850, Y + 560)
connect(out_data(get_tid3), find_pin(eqt3, "A", "Input"), "t3")
setdef(find_pin(eqt3, "B", "Input"), "1")
brt3 = tge.add_branch_node(); bel.set_node_pos(brt3, pos(1100, Y + 520))
connect(find_pin(gaom, "then", "Output"), find_pin(brt3, "execute", "Input"), "tidb")
connect(out_data(eqt3), find_pin(brt3, "Condition", "Input"), "t1b")
c1 = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:CtxTable1")
bel.set_node_pos(c1, pos(1400, Y + 480))
connect(find_pin(brt3, "then", "Output"), find_pin(c1, "execute", "Input"), "c1")
connect(find_pin(getm, "Item", "Output"), find_pin(c1, "self", "Input"), "c1s")
c2 = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:CtxTable2")
bel.set_node_pos(c2, pos(1400, Y + 600))
connect(find_pin(brt3, "else", "Output"), find_pin(c2, "execute", "Input"), "c2")
connect(find_pin(getm, "Item", "Output"), find_pin(c2, "self", "Input"), "c2s")

# dish
get_d2 = tge.add_get_member_variable_node("CurrentDishId"); bel.set_node_pos(get_d2, pos(1700, Y + 560))
eqd2 = eq_int(tge, 1950, Y + 560)
connect(out_data(get_d2), find_pin(eqd2, "A", "Input"), "d2")
setdef(find_pin(eqd2, "B", "Input"), "1")
brd2 = tge.add_branch_node(); bel.set_node_pos(brd2, pos(2200, Y + 520))
# chain from both c1/c2 then — use Sequence after both? Wire c1.then and c2.then both to brd2 via... can't dual.
# Use Sequence node from gaom.then path differently: set all ctx sequentially with branches that always continue.

# Rebuild PushContext more linearly: after CtxTable, always continue from a Sequence.
# Simpler: rewire — c1.then -> dish branch, c2.then -> same dish branch nodes duplicated.

def dish_pending_eval(ge, start_exec, mgr_item_getter, ybase, tag):
    get_d = ge.add_get_member_variable_node("CurrentDishId"); bel.set_node_pos(get_d, pos(1700, ybase))
    eq = eq_int(ge, 1950, ybase)
    connect(out_data(get_d), find_pin(eq, "A", "Input"), tag + "d")
    setdef(find_pin(eq, "B", "Input"), "1")
    br = ge.add_branch_node(); bel.set_node_pos(br, pos(2200, ybase - 40))
    connect(start_exec, find_pin(br, "execute", "Input"), tag + "br")
    connect(out_data(eq), find_pin(br, "Condition", "Input"), tag + "salad")
    cd1 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:CtxDish1")
    bel.set_node_pos(cd1, pos(2500, ybase - 80))
    connect(find_pin(br, "then", "Output"), find_pin(cd1, "execute", "Input"), tag + "cd1")
    connect(mgr_item_getter, find_pin(cd1, "self", "Input"), tag + "cd1s")
    cd2 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:CtxDish2")
    bel.set_node_pos(cd2, pos(2500, ybase + 40))
    connect(find_pin(br, "else", "Output"), find_pin(cd2, "execute", "Input"), tag + "cd2")
    connect(mgr_item_getter, find_pin(cd2, "self", "Input"), tag + "cd2s")
    # pending
    get_p = ge.add_get_member_variable_node("bOrderPending"); bel.set_node_pos(get_p, pos(2800, ybase))
    brp = ge.add_branch_node(); bel.set_node_pos(brp, pos(3050, ybase - 40))
    # both dish paths -> need Sequence. Duplicate pending+eval under each.
    def after_dish(exec_pin, yy, tg):
        getp = ge.add_get_member_variable_node("bOrderPending"); bel.set_node_pos(getp, pos(2800, yy))
        brp = ge.add_branch_node(); bel.set_node_pos(brp, pos(3050, yy - 40))
        connect(exec_pin, find_pin(brp, "execute", "Input"), tg + "p")
        connect(out_data(getp), find_pin(brp, "Condition", "Input"), tg + "pc")
        cy = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:CtxPendingYes")
        bel.set_node_pos(cy, pos(3350, yy - 80))
        connect(find_pin(brp, "then", "Output"), find_pin(cy, "execute", "Input"), tg + "y")
        connect(mgr_item_getter, find_pin(cy, "self", "Input"), tg + "ys")
        cn = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:CtxPendingNo")
        bel.set_node_pos(cn, pos(3350, yy + 40))
        connect(find_pin(brp, "else", "Output"), find_pin(cn, "execute", "Input"), tg + "n")
        connect(mgr_item_getter, find_pin(cn, "self", "Input"), tg + "ns")
        ev1 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EvalTableE")
        bel.set_node_pos(ev1, pos(3700, yy - 80))
        connect(find_pin(cy, "then", "Output"), find_pin(ev1, "execute", "Input"), tg + "e1")
        connect(mgr_item_getter, find_pin(ev1, "self", "Input"), tg + "e1s")
        ev2 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EvalTableE")
        bel.set_node_pos(ev2, pos(3700, yy + 40))
        connect(find_pin(cn, "then", "Output"), find_pin(ev2, "execute", "Input"), tg + "e2")
        connect(mgr_item_getter, find_pin(ev2, "self", "Input"), tg + "e2s")
    after_dish(find_pin(cd1, "then", "Output"), ybase - 80, tag + "A")
    after_dish(find_pin(cd2, "then", "Output"), ybase + 120, tag + "B")

mgr_item = find_pin(getm, "Item", "Output")
dish_pending_eval(tge, find_pin(c1, "then", "Output"), mgr_item, Y + 480, "T1")
dish_pending_eval(tge, find_pin(c2, "then", "Output"), mgr_item, Y + 780, "T2")

# BeginEatIfActive: if TableId == Manager.ActiveTableId -> BeginEat
bea = tge.add_custom_event_node("BeginEatIfActive")
bel.set_node_pos(bea, pos(0, Y + 1400))
gaom2 = tge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gaom2, pos(300, Y + 1400))
connect(find_pin(bea, "then", "Output"), find_pin(gaom2, "execute", "Input"), "bea")
setdef(find_pin(gaom2, "ActorClass", "Input") or find_pin(gaom2, "Class", "Input"),
       "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
getm2 = tge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(getm2, pos(600, Y + 1480))
connect(find_pin(gaom2, "OutActors", "Output"), find_pin(getm2, "TargetArray", "Input"), "m2")
setdef(find_pin(getm2, "Index", "Input"), "0")
# Get ActiveTableId from manager — use call Mgr that returns? Can't. Compare via Ctx already set — ActiveTableId is set.
# Get member ActiveTableId on manager actor — need Cast or Get. Try create Get with target.
gat = tge.add_get_member_variable_node("ActiveTableId")
# This get is on Table BP self — wrong. Need manager's ActiveTableId.
# Workaround: Manager.IsActiveTable1 / IsActiveTable2 events that Print and call back — 
# Simpler: BeginEatIfActive compares own TableId with... we set Active before Eval, then ForEach BeginEatIfActive —
# Table calls Manager.CheckActiveEqualsMe: Manager branches ActiveTableId==1 Call Table1.BeginEat — circular.

# Use: BeginEatIfActive gets Manager.ActiveTableId via GetAll + Call Manager.GetActiveTableIdInto — 
# Best: Table compares TableId to Active by calling Manager.MatchesActiveTable1 if TableId==1:
get_own = tge.add_get_member_variable_node("TableId"); bel.set_node_pos(get_own, pos(600, Y + 1360))
eq_own = eq_int(tge, 900, Y + 1360)
connect(out_data(get_own), find_pin(eq_own, "A", "Input"), "own")
setdef(find_pin(eq_own, "B", "Input"), "1")
br_own = tge.add_branch_node(); bel.set_node_pos(br_own, pos(1150, Y + 1400))
connect(find_pin(gaom2, "then", "Output"), find_pin(br_own, "execute", "Input"), "ownb")
connect(out_data(eq_own), find_pin(br_own, "Condition", "Input"), "is1")
# if table1: Call Manager.MatchesAndBeginEat1 — Manager: if ActiveTableId==1 Call this table BeginEat — still need table ref.

# Simplest reliable: BeginEatIfActive checks TableId == ActiveTableId by reading Manager var:
# Use CallFunction on manager: ConfirmActive1 — if Active==1, Call GetAll Tables ForEach BeginEatOn1 only table1.

# Even simpler for BeginEatIfActive on EACH table during ForEach:
# Call Manager.ShouldBeginEatFor1 / For2 — returns bool via... no return.
# Manager.Eval already knows ActiveTableId. Change Eval correct path to Call only:
#   if ActiveTableId==1: GetAll tables ForEach Call BeginEatOnlyIfId1
# Table.BeginEatOnlyIfId1: if TableId==1 BeginEat

# Replace BeginEatIfActive with BeginEatOnlyIfId1 and BeginEatOnlyIfId2 — Manager Eval will call both ForEach? 
# ForEach Call BeginEatOnlyIfId1 — only table1 responds. And Manager branches Active first.

be1 = tge.add_custom_event_node("BeginEatOnlyIfId1")
bel.set_node_pos(be1, pos(0, Y + 1700))
g1 = tge.add_get_member_variable_node("TableId"); bel.set_node_pos(g1, pos(300, Y + 1780))
e1 = eq_int(tge, 550, Y + 1780)
connect(out_data(g1), find_pin(e1, "A", "Input"), "be1")
setdef(find_pin(e1, "B", "Input"), "1")
b1 = tge.add_branch_node(); bel.set_node_pos(b1, pos(800, Y + 1700))
connect(find_pin(be1, "then", "Output"), find_pin(b1, "execute", "Input"), "be1e")
connect(out_data(e1), find_pin(b1, "Condition", "Input"), "be1c")
call_be = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:BeginEat")
bel.set_node_pos(call_be, pos(1100, Y + 1700))
connect(find_pin(b1, "then", "Output"), find_pin(call_be, "execute", "Input"), "be1call")

be2 = tge.add_custom_event_node("BeginEatOnlyIfId2")
bel.set_node_pos(be2, pos(0, Y + 1950))
g2 = tge.add_get_member_variable_node("TableId"); bel.set_node_pos(g2, pos(300, Y + 2030))
e2 = eq_int(tge, 550, Y + 2030)
connect(out_data(g2), find_pin(e2, "A", "Input"), "be2")
setdef(find_pin(e2, "B", "Input"), "2")
b2 = tge.add_branch_node(); bel.set_node_pos(b2, pos(800, Y + 1950))
connect(find_pin(be2, "then", "Output"), find_pin(b2, "execute", "Input"), "be2e")
connect(out_data(e2), find_pin(b2, "Condition", "Input"), "be2c")
call_be2 = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:BeginEat")
bel.set_node_pos(call_be2, pos(1100, Y + 1950))
connect(find_pin(b2, "then", "Output"), find_pin(call_be2, "execute", "Input"), "be2call")

wl1 = tge.add_custom_event_node("WrongLeaveOnlyIfId1")
bel.set_node_pos(wl1, pos(0, Y + 2200))
gw1 = tge.add_get_member_variable_node("TableId"); bel.set_node_pos(gw1, pos(300, Y + 2280))
ew1 = eq_int(tge, 550, Y + 2280)
connect(out_data(gw1), find_pin(ew1, "A", "Input"), "wl1")
setdef(find_pin(ew1, "B", "Input"), "1")
bw1 = tge.add_branch_node(); bel.set_node_pos(bw1, pos(800, Y + 2200))
connect(find_pin(wl1, "then", "Output"), find_pin(bw1, "execute", "Input"), "wl1e")
connect(out_data(ew1), find_pin(bw1, "Condition", "Input"), "wl1c")
call_wl = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:WrongLeave")
bel.set_node_pos(call_wl, pos(1100, Y + 2200))
connect(find_pin(bw1, "then", "Output"), find_pin(call_wl, "execute", "Input"), "wl1call")

wl2 = tge.add_custom_event_node("WrongLeaveOnlyIfId2")
bel.set_node_pos(wl2, pos(0, Y + 2450))
gw2 = tge.add_get_member_variable_node("TableId"); bel.set_node_pos(gw2, pos(300, Y + 2530))
ew2 = eq_int(tge, 550, Y + 2530)
connect(out_data(gw2), find_pin(ew2, "A", "Input"), "wl2")
setdef(find_pin(ew2, "B", "Input"), "2")
bw2 = tge.add_branch_node(); bel.set_node_pos(bw2, pos(800, Y + 2450))
connect(find_pin(wl2, "then", "Output"), find_pin(bw2, "execute", "Input"), "wl2e")
connect(out_data(ew2), find_pin(bw2, "Condition", "Input"), "wl2c")
call_wl2 = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:WrongLeave")
bel.set_node_pos(call_wl2, pos(1100, Y + 2450))
connect(find_pin(bw2, "then", "Output"), find_pin(call_wl2, "execute", "Input"), "wl2call")

# Remove incomplete BeginEatIfActive stub
# leave bea disconnected — remove it
tge.remove_nodes([bea, gaom2, getm2, get_own, eq_own, br_own])

compile_save(tbp, TP, "table")

# Fix Table Tick pay wiring if missing
# Re-open and find OnGuestPaid skips — add Call after eat complete
# Load table tick path: when eat done, Call OnGuestPaidSalad/Stew based on dish
# Probe existing BeginEat / Tick for pay calls
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_recv_table.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps({k: R[k] for k in ("statuses", "errors", "steps")}, indent=2, ensure_ascii=False)[:7000])