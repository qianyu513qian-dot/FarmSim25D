# -*- coding: utf-8 -*-
"""Rewrite Table TrySeat init + ClearSeat + Event Tick (patience/eat) + helper events."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
PATH = "/Game/Farm/Restaurant/BP_RestaurantTable"
R = {"steps": [], "errors": []}

def log(m):
    unreal.log("[K3T] " + str(m)); R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Item", "bOccupied", "CurrentOrder", "CurrentDishId", "bHasOrder",
                 "bOrderPending", "bEating", "PatienceLeft", "EatLeft", "OrderPrice", "TableId"):
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

def make_print(ge, x, y, text, dur="2.5"):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    return pr

def cmp_le(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble")
    if n is None:
        n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_FloatFloat")
    bel.set_node_pos(n, pos(x, y)); return n

def sub_d(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble")
    if n is None:
        n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_FloatFloat")
    bel.set_node_pos(n, pos(x, y)); return n

def eq_int(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(n, pos(x, y)); return n

def eq_str(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:EqualEqual_StrStr")
    bel.set_node_pos(n, pos(x, y)); return n

bp = unreal.EditorAssetLibrary.load_asset(PATH)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# Purge only our custom event bodies and rewire Tick — keep BeginPlay/Overlap parent calls
kill = []
keep_titles = set()
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    c = n.get_class().get_name()
    if c == "K2Node_Event" and ("BeginPlay" in t or "ActorBeginOverlap" in t):
        continue
    if c == "K2Node_CallParentFunction":
        continue
    # remove Tick body but keep Event Tick node
    if c == "K2Node_Event" and t == "Event Tick":
        then = find_pin(n, "then", "Output")
        if then:
            then.break_pin_links()
        keep_titles.add(id(n))
        continue
    if c == "K2Node_CustomEvent" and t in ("TrySeat", "ClearSeat", "BeginEat", "WrongLeave", "VoidIfCookingTable"):
        then = find_pin(n, "then", "Output")
        if then:
            then.break_pin_links()
        # delete custom to recreate clean
        kill.append(n)
        continue
    kill.append(n)
if kill:
    ge.remove_nodes(kill)
    log("purged " + str(len(kill)))

# Ensure Event Tick exists
tick = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and bel.get_node_title(n) == "Event Tick":
        tick = n
if tick is None:
    try:
        tick = bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(0, 0))
        log("added Event Tick")
    except Exception as e:
        R["errors"].append("tick " + str(e))

# ========== ClearSeat ==========
clr = ge.add_custom_event_node("ClearSeat")
bel.set_node_pos(clr, pos(0, 200))
chain = find_pin(clr, "then", "Output")
sets = [
    ("bOccupied", "false"),
    ("bHasOrder", "false"),
    ("bOrderPending", "false"),
    ("bEating", "false"),
    ("CurrentOrder", ""),
    ("CurrentDishId", "0"),
    ("PatienceLeft", "0.0"),
    ("EatLeft", "0.0"),
    ("OrderPrice", "0.0"),
]
x = 300
prev = chain
for name, val in sets:
    sn = ge.add_set_member_variable_node(name)
    bel.set_node_pos(sn, pos(x, 200))
    connect(prev, find_pin(sn, "execute", "Input"), "clr->" + name)
    setdef(find_pin(sn, name, "Input"), val)
    prev = find_pin(sn, "then", "Output")
    x += 280
log("ClearSeat done")

# ========== TrySeat ==========
# if occupied skip; else occupy + random order + patience 22
try_ev = ge.add_custom_event_node("TrySeat")
bel.set_node_pos(try_ev, pos(0, 600))
get_occ = ge.add_get_member_variable_node("bOccupied")
bel.set_node_pos(get_occ, pos(200, 680))
br = ge.add_branch_node(); bel.set_node_pos(br, pos(450, 600))
connect(find_pin(try_ev, "then", "Output"), find_pin(br, "execute", "Input"), "try")
connect(out_data(get_occ), find_pin(br, "Condition", "Input"), "occ?")

# free path
set_occ = ge.add_set_member_variable_node("bOccupied"); bel.set_node_pos(set_occ, pos(750, 700))
connect(find_pin(br, "else", "Output"), find_pin(set_occ, "execute", "Input"), "free")
setdef(find_pin(set_occ, "bOccupied", "Input"), "true")

rb = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:RandomBool")
bel.set_node_pos(rb, pos(750, 850))
# dish id: pick A=salad(1) if RandomBool else stew(2) via Select
# use Branch on RandomBool instead of SelectInt for reliability
br_d = ge.add_branch_node(); bel.set_node_pos(br_d, pos(1050, 700))
connect(find_pin(set_occ, "then", "Output"), find_pin(br_d, "execute", "Input"), "->dish")
connect(out_data(rb), find_pin(br_d, "Condition", "Input"), "rb?")

def order_chain(start_exec, y, order, dish, price, label):
    s1 = ge.add_set_member_variable_node("CurrentOrder"); bel.set_node_pos(s1, pos(1350, y))
    connect(start_exec, find_pin(s1, "execute", "Input"), label + "ord")
    setdef(find_pin(s1, "CurrentOrder", "Input"), order)
    s2 = ge.add_set_member_variable_node("CurrentDishId"); bel.set_node_pos(s2, pos(1650, y))
    connect(find_pin(s1, "then", "Output"), find_pin(s2, "execute", "Input"), label + "id")
    setdef(find_pin(s2, "CurrentDishId", "Input"), str(dish))
    s3 = ge.add_set_member_variable_node("OrderPrice"); bel.set_node_pos(s3, pos(1950, y))
    connect(find_pin(s2, "then", "Output"), find_pin(s3, "execute", "Input"), label + "pr")
    setdef(find_pin(s3, "OrderPrice", "Input"), str(price))
    s4 = ge.add_set_member_variable_node("bHasOrder"); bel.set_node_pos(s4, pos(2250, y))
    connect(find_pin(s3, "then", "Output"), find_pin(s4, "execute", "Input"), label + "ho")
    setdef(find_pin(s4, "bHasOrder", "Input"), "true")
    s5 = ge.add_set_member_variable_node("bOrderPending"); bel.set_node_pos(s5, pos(2550, y))
    connect(find_pin(s4, "then", "Output"), find_pin(s5, "execute", "Input"), label + "pend")
    setdef(find_pin(s5, "bOrderPending", "Input"), "true")
    s6 = ge.add_set_member_variable_node("bEating"); bel.set_node_pos(s6, pos(2850, y))
    connect(find_pin(s5, "then", "Output"), find_pin(s6, "execute", "Input"), label + "eatf")
    setdef(find_pin(s6, "bEating", "Input"), "false")
    s7 = ge.add_set_member_variable_node("PatienceLeft"); bel.set_node_pos(s7, pos(3150, y))
    connect(find_pin(s6, "then", "Output"), find_pin(s7, "execute", "Input"), label + "pat")
    setdef(find_pin(s7, "PatienceLeft", "Input"), "22.0")
    pr = make_print(ge, 3450, y, "Restaurant GUEST order=" + order + " $" + str(int(price)) + " patience=22s")
    connect(find_pin(s7, "then", "Output"), find_pin(pr, "execute", "Input"), label + "prnt")
    return pr

order_chain(find_pin(br_d, "then", "Output"), 650, "TomatoSalad", 1, 15.0, "sal_")
order_chain(find_pin(br_d, "else", "Output"), 950, "Stew", 2, 28.0, "stew_")
log("TrySeat done")

# ========== BeginEat ==========
be = ge.add_custom_event_node("BeginEat")
bel.set_node_pos(be, pos(0, 1300))
s1 = ge.add_set_member_variable_node("bEating"); bel.set_node_pos(s1, pos(300, 1300))
connect(find_pin(be, "then", "Output"), find_pin(s1, "execute", "Input"), "be")
setdef(find_pin(s1, "bEating", "Input"), "true")
s2 = ge.add_set_member_variable_node("bOrderPending"); bel.set_node_pos(s2, pos(600, 1300))
connect(find_pin(s1, "then", "Output"), find_pin(s2, "execute", "Input"), "be2")
setdef(find_pin(s2, "bOrderPending", "Input"), "false")
s3 = ge.add_set_member_variable_node("EatLeft"); bel.set_node_pos(s3, pos(900, 1300))
connect(find_pin(s2, "then", "Output"), find_pin(s3, "execute", "Input"), "be3")
setdef(find_pin(s3, "EatLeft", "Input"), "3.5")
s4 = ge.add_set_member_variable_node("PatienceLeft"); bel.set_node_pos(s4, pos(1200, 1300))
connect(find_pin(s3, "then", "Output"), find_pin(s4, "execute", "Input"), "be4")
setdef(find_pin(s4, "PatienceLeft", "Input"), "999.0")
pr = make_print(ge, 1500, 1300, "Restaurant SERVE OK — guest eating ~3.5s")
connect(find_pin(s4, "then", "Output"), find_pin(pr, "execute", "Input"), "bepr")

# ========== WrongLeave ==========
wl = ge.add_custom_event_node("WrongLeave")
bel.set_node_pos(wl, pos(0, 1600))
prw = make_print(ge, 300, 1600, "Restaurant WRONG dish/table — leave $0, dish gone")
connect(find_pin(wl, "then", "Output"), find_pin(prw, "execute", "Input"), "wl")
call_clr = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ClearSeat")
bel.set_node_pos(call_clr, pos(700, 1600))
connect(find_pin(prw, "then", "Output"), find_pin(call_clr, "execute", "Input"), "wl->clr")

# ========== Event Tick: patience + eat ==========
if tick:
    bel.set_node_pos(tick, pos(0, 2000))
    then_t = find_pin(tick, "then", "Output")
    get_occ2 = ge.add_get_member_variable_node("bOccupied"); bel.set_node_pos(get_occ2, pos(200, 2080))
    br_o = ge.add_branch_node(); bel.set_node_pos(br_o, pos(450, 2000))
    connect(then_t, find_pin(br_o, "execute", "Input"), "tick")
    connect(out_data(get_occ2), find_pin(br_o, "Condition", "Input"), "occ")

    # eating branch
    get_eat = ge.add_get_member_variable_node("bEating"); bel.set_node_pos(get_eat, pos(700, 2080))
    br_e = ge.add_branch_node(); bel.set_node_pos(br_e, pos(950, 2000))
    connect(find_pin(br_o, "then", "Output"), find_pin(br_e, "execute", "Input"), "->eat?")
    connect(out_data(get_eat), find_pin(br_e, "Condition", "Input"), "eating?")

    # --- eating path: EatLeft -= dt; if <=0 pay+clear ---
    get_el = ge.add_get_member_variable_node("EatLeft"); bel.set_node_pos(get_el, pos(1200, 1920))
    sub1 = sub_d(ge, 1450, 1920)
    connect(out_data(get_el), find_pin(sub1, "A", "Input"), "elA")
    connect(find_pin(tick, "DeltaSeconds", "Output"), find_pin(sub1, "B", "Input"), "dt1")
    set_el = ge.add_set_member_variable_node("EatLeft"); bel.set_node_pos(set_el, pos(1750, 1850))
    connect(find_pin(br_e, "then", "Output"), find_pin(set_el, "execute", "Input"), "setel")
    connect(out_data(sub1), find_pin(set_el, "EatLeft", "Input"), "elv")
    le1 = cmp_le(ge, 2050, 1920)
    connect(out_data(sub1), find_pin(le1, "A", "Input"), "leA")
    setdef(find_pin(le1, "B", "Input"), "0.0")
    br_done = ge.add_branch_node(); bel.set_node_pos(br_done, pos(2300, 1850))
    connect(find_pin(set_el, "then", "Output"), find_pin(br_done, "execute", "Input"), "done?")
    connect(out_data(le1), find_pin(br_done, "Condition", "Input"), "doneC")
    # pay: call Manager.OnGuestPaid via GetAll
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(2600, 1800))
    connect(find_pin(br_done, "then", "Output"), find_pin(gao, "execute", "Input"), "->mgr")
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
    get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(2900, 1880))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), "arr")
    setdef(find_pin(get0, "Index", "Input"), "0")
    # set pending pay amount on manager by calling OnGuestPaid — Manager reads from... 
    # We'll call OnGuestPaid and also pass price by setting Manager temp via separate events.
    # Use: Call OnGuestPaidSalad if dish==1 else OnGuestPaidStew
    get_dish = ge.add_get_member_variable_node("CurrentDishId"); bel.set_node_pos(get_dish, pos(2900, 2000))
    eq1 = eq_int(ge, 3200, 2000)
    connect(out_data(get_dish), find_pin(eq1, "A", "Input"), "dA")
    setdef(find_pin(eq1, "B", "Input"), "1")
    br_pay = ge.add_branch_node(); bel.set_node_pos(br_pay, pos(3450, 1800))
    connect(find_pin(gao, "then", "Output"), find_pin(br_pay, "execute", "Input"), "paybr")
    connect(out_data(eq1), find_pin(br_pay, "Condition", "Input"), "salad?")
    pay1 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:OnGuestPaidSalad")
    bel.set_node_pos(pay1, pos(3750, 1700))
    connect(find_pin(br_pay, "then", "Output"), find_pin(pay1, "execute", "Input"), "payS")
    connect(find_pin(get0, "Item", "Output"), find_pin(pay1, "self", "Input"), "paySself")
    pay2 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:OnGuestPaidStew")
    bel.set_node_pos(pay2, pos(3750, 1900))
    connect(find_pin(br_pay, "else", "Output"), find_pin(pay2, "execute", "Input"), "payW")
    connect(find_pin(get0, "Item", "Output"), find_pin(pay2, "self", "Input"), "payWself")
    # after pay either path — need sequence; use both then → ClearSeat via separate clears
    call_clr2 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ClearSeat")
    bel.set_node_pos(call_clr2, pos(4100, 1700))
    connect(find_pin(pay1, "then", "Output"), find_pin(call_clr2, "execute", "Input"), "clrS")
    call_clr3 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ClearSeat")
    bel.set_node_pos(call_clr3, pos(4100, 1900))
    connect(find_pin(pay2, "then", "Output"), find_pin(call_clr3, "execute", "Input"), "clrW")

    # --- patience path (not eating) ---
    get_pend = ge.add_get_member_variable_node("bHasOrder"); bel.set_node_pos(get_pend, pos(1200, 2200))
    br_p = ge.add_branch_node(); bel.set_node_pos(br_p, pos(1450, 2150))
    connect(find_pin(br_e, "else", "Output"), find_pin(br_p, "execute", "Input"), "pat?")
    connect(out_data(get_pend), find_pin(br_p, "Condition", "Input"), "hasord")
    get_pl = ge.add_get_member_variable_node("PatienceLeft"); bel.set_node_pos(get_pl, pos(1750, 2220))
    sub2 = sub_d(ge, 2000, 2220)
    connect(out_data(get_pl), find_pin(sub2, "A", "Input"), "plA")
    connect(find_pin(tick, "DeltaSeconds", "Output"), find_pin(sub2, "B", "Input"), "dt2")
    set_pl = ge.add_set_member_variable_node("PatienceLeft"); bel.set_node_pos(set_pl, pos(2300, 2150))
    connect(find_pin(br_p, "then", "Output"), find_pin(set_pl, "execute", "Input"), "setpl")
    connect(out_data(sub2), find_pin(set_pl, "PatienceLeft", "Input"), "plv")
    le2 = cmp_le(ge, 2600, 2220)
    connect(out_data(sub2), find_pin(le2, "A", "Input"), "le2A")
    setdef(find_pin(le2, "B", "Input"), "0.0")
    br_to = ge.add_branch_node(); bel.set_node_pos(br_to, pos(2850, 2150))
    connect(find_pin(set_pl, "then", "Output"), find_pin(br_to, "execute", "Input"), "to?")
    connect(out_data(le2), find_pin(br_to, "Condition", "Input"), "toC")
    pr_to = make_print(ge, 3150, 2150, "Restaurant TIMEOUT — guest left $0")
    connect(find_pin(br_to, "then", "Output"), find_pin(pr_to, "execute", "Input"), "topr")
    # void stove if cooking this table
    gao_s = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao_s, pos(3450, 2150))
    connect(find_pin(pr_to, "then", "Output"), find_pin(gao_s, "execute", "Input"), "->stove")
    setdef(find_pin(gao_s, "ActorClass", "Input") or find_pin(gao_s, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C")
    get_s = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get_s, pos(3750, 2220))
    connect(find_pin(gao_s, "OutActors", "Output"), find_pin(get_s, "TargetArray", "Input"), "sarr")
    setdef(find_pin(get_s, "Index", "Input"), "0")
    void = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:VoidIfTable")
    bel.set_node_pos(void, pos(4050, 2150))
    connect(find_pin(gao_s, "then", "Output"), find_pin(void, "execute", "Input"), "void")
    connect(find_pin(get_s, "Item", "Output"), find_pin(void, "self", "Input"), "voidself")
    # need to pass TableId — VoidIfTable will read from... stove compares CookingTableId to something.
    # Simpler VoidIfTable voids always if cooking OR we add VoidCook on stove that clears always on any timeout from any table if CookingTableId matches.
    # For VoidIfTable: stove event reads GetAll tables? Better: Manager or Table sets stove.
    # Change: call stove.VoidCook always on timeout (if cooking that table id). 
    # Stove.VoidIfTable needs TableId param — without params, Table sets a static approach:
    # Call stove.VoidCookMatching — stove checks CookingTableId == nearest? 
    # Simplest: on timeout always call Stove.VoidCook which clears if CookingTableId == this TableId.
    # Stove needs to read caller TableId — use Manager PendingVoidTableId.
    # Even simpler for v1: on timeout Call Stove.ForceVoidCook (clears any cook) — might void other table's dish unfairly rare with 1 stove 1 cook.
    # Use ForceVoidCook only if this table's TableId == stove.CookingTableId — implemented inside VoidIfTable by GetAll and compare... 
    # VoidIfTable on stove: get all tables, find occupied timeout... too heavy.
    # **VoidIfTable**: custom event on stove that clears cooking if CookingTableId equals... we need input.
    # Workaround: Table before void sets Manager.HeldTableId temp? Messy.
    # **Stove.VoidIfTableId1** and **VoidIfTableId2** — Table branches on TableId.
    get_tid = ge.add_get_member_variable_node("TableId"); bel.set_node_pos(get_tid, pos(3750, 2350))
    eqt = eq_int(ge, 4000, 2350)
    connect(out_data(get_tid), find_pin(eqt, "A", "Input"), "tid")
    setdef(find_pin(eqt, "B", "Input"), "1")
    # Actually replace void call with ForceVoidCook always (1 stove 1 dish)
    # Remove void typed call; use ForceVoidCook
    # Reconnect: already wired void — we'll define VoidIfTable as ForceVoidCook equivalent that clears if CookingTableId matches by reading... 
    # Define stove VoidIfTable as: if CookingTableId!=0 clear (ForceVoid) — OK for timeout from any table when that table times out during its cook; if other table times out while stove cooks first table, wrongly voids — edge case accept OR check.
    # For check without cast: Stove.VoidIfTable compares CookingTableId to Get — can't get caller id.
    # Use ForceVoidCook on timeout always:
    pass  # keep VoidIfTable name; implement as clear-if-cooking on stove

    call_clr4 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ClearSeat")
    bel.set_node_pos(call_clr4, pos(4400, 2150))
    connect(find_pin(void, "then", "Output"), find_pin(call_clr4, "execute", "Input"), "clrTO")

bel.compile_blueprint(bp)
st = str(bp.get_editor_property("status"))
R["status"] = st
if "ERROR" in st:
    # dump errors
    for n in ge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                R["errors"].append(bel.get_node_title(n) + ": " + str(em)[:200])
        except Exception:
            pass
else:
    unreal.EditorAssetLibrary.save_asset(PATH)
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_table.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False)[:5000])