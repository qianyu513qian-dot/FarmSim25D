# -*- coding: utf-8 -*-
"""Manager: pay events, stove/trash/table E handlers, dispatch from HandlePlayerE."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
PATH = "/Game/Farm/Restaurant/BP_RestaurantManager"
R = {"steps": [], "errors": []}

def log(m):
    unreal.log("[K3M] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    cands = []
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                cands.append(p)
    return cands[0] if cands else None

def out_data(node):
    if not node:
        return None
    for name in ("ReturnValue", "Item", "bIsOpenBusiness", "HeldDishId", "HeldTableId", "RestaurantMoney",
                 "ActiveTableId", "ActiveDishId", "bActivePending", "bCooking", "bCookReady"):
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

def make_print(ge, x, y, text, dur="2.8"):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    return pr

def ensure_var(bp, name, type_name):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    t = bel.get_basic_type_by_name(type_name)
    if name not in names:
        bel.add_member_variable(bp, name, t)
        log("var " + name)

def eq_int(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(n, pos(x, y)); return n

def ne_int(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:NotEqual_IntInt")
    bel.set_node_pos(n, pos(x, y)); return n

def add_d(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
    if n is None:
        n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
    bel.set_node_pos(n, pos(x, y)); return n

def add_foreach(ge, x, y):
    fe = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    bel.set_node_pos(fe, pos(x, y)); return fe

bp = unreal.EditorAssetLibrary.load_asset(PATH)
ensure_var(bp, "ActiveTableId", "int")
ensure_var(bp, "ActiveDishId", "int")
ensure_var(bp, "bActivePending", "bool")
ensure_var(bp, "HeldDishId", "int")
ensure_var(bp, "HeldTableId", "int")
ensure_var(bp, "RestaurantMoney", "real")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# Remove old knife3 customs if re-run; keep HandlePlayerE/ClearGuests/SeatGuest/RestaurantTick/Tick/BeginPlay
KILL_NAMES = {
    "OnGuestPaidSalad", "OnGuestPaidStew", "HandleStoveE", "HandleTrashE", "HandleTableE",
    "DispatchNonSignE", "CtxTable1", "CtxTable2", "CtxDish1", "CtxDish2", "CtxPendingYes", "CtxPendingNo",
    "EvalTableE", "ClearHeld", "ReceiveHeld",
}
kill = []
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    c = n.get_class().get_name()
    if c == "K2Node_CustomEvent" and t in KILL_NAMES:
        kill.append(n)
        # also will purge dangling by compiling — remove nodes only customs first
if kill:
    # remove nodes that are ONLY in those event chains is hard; remove customs and orphan calls later
    for n in kill:
        then = find_pin(n, "then", "Output")
        if then:
            then.break_pin_links()
    ge.remove_nodes(kill)
    log("removed old customs " + str(len(kill)))

Y = 2200  # place new logic below existing

def pay_event(name, amount, y):
    ev = ge.add_custom_event_node(name)
    bel.set_node_pos(ev, pos(0, y))
    get_m = ge.add_get_member_variable_node("RestaurantMoney"); bel.set_node_pos(get_m, pos(250, y + 80))
    addn = add_d(ge, 500, y + 80)
    connect(out_data(get_m), find_pin(addn, "A", "Input"), name + "A")
    setdef(find_pin(addn, "B", "Input"), str(amount))
    set_m = ge.add_set_member_variable_node("RestaurantMoney"); bel.set_node_pos(set_m, pos(800, y))
    connect(find_pin(ev, "then", "Output"), find_pin(set_m, "execute", "Input"), name + "set")
    connect(out_data(addn), find_pin(set_m, "RestaurantMoney", "Input"), name + "v")
    pr = make_print(ge, 1100, y, "Restaurant PAY +${}  (money updated)".format(int(amount)))
    connect(find_pin(set_m, "then", "Output"), find_pin(pr, "execute", "Input"), name + "pr")
    # append total via second print fixed — enough
    return ev

pay_event("OnGuestPaidSalad", 15.0, Y)
pay_event("OnGuestPaidStew", 28.0, Y + 250)

# ClearHeld
ch = ge.add_custom_event_node("ClearHeld")
bel.set_node_pos(ch, pos(0, Y + 550))
s1 = ge.add_set_member_variable_node("HeldDishId"); bel.set_node_pos(s1, pos(300, Y + 550))
connect(find_pin(ch, "then", "Output"), find_pin(s1, "execute", "Input"), "ch1")
setdef(find_pin(s1, "HeldDishId", "Input"), "0")
s2 = ge.add_set_member_variable_node("HeldTableId"); bel.set_node_pos(s2, pos(600, Y + 550))
connect(find_pin(s1, "then", "Output"), find_pin(s2, "execute", "Input"), "ch2")
setdef(find_pin(s2, "HeldTableId", "Input"), "0")
s3 = ge.add_set_member_variable_node("HeldOrder"); bel.set_node_pos(s3, pos(900, Y + 550))
connect(find_pin(s2, "then", "Output"), find_pin(s3, "execute", "Input"), "ch3")
setdef(find_pin(s3, "HeldOrder", "Input"), "")

# Context setters
def ctx_set(name, var, val, y):
    ev = ge.add_custom_event_node(name)
    bel.set_node_pos(ev, pos(0, y))
    sn = ge.add_set_member_variable_node(var); bel.set_node_pos(sn, pos(350, y))
    connect(find_pin(ev, "then", "Output"), find_pin(sn, "execute", "Input"), name)
    setdef(find_pin(sn, var, "Input"), str(val))
    return ev

ctx_set("CtxTable1", "ActiveTableId", 1, Y + 750)
ctx_set("CtxTable2", "ActiveTableId", 2, Y + 850)
ctx_set("CtxDish1", "ActiveDishId", 1, Y + 950)
ctx_set("CtxDish2", "ActiveDishId", 2, Y + 1050)
ctx_set("CtxPendingYes", "bActivePending", True, Y + 1150)
ctx_set("CtxPendingNo", "bActivePending", False, Y + 1250)

# ========== HandleTrashE ==========
ht = ge.add_custom_event_node("HandleTrashE")
bel.set_node_pos(ht, pos(0, Y + 1400))
get_h = ge.add_get_member_variable_node("HeldDishId"); bel.set_node_pos(get_h, pos(250, Y + 1480))
ne = ne_int(ge, 500, Y + 1480)
connect(out_data(get_h), find_pin(ne, "A", "Input"), "hA")
setdef(find_pin(ne, "B", "Input"), "0")
br = ge.add_branch_node(); bel.set_node_pos(br, pos(750, Y + 1400))
connect(find_pin(ht, "then", "Output"), find_pin(br, "execute", "Input"), "trash")
connect(out_data(ne), find_pin(br, "Condition", "Input"), "holding?")
pr_yes = make_print(ge, 1050, Y + 1320, "Restaurant TRASH: discarded dish (no money loss)")
connect(find_pin(br, "then", "Output"), find_pin(pr_yes, "execute", "Input"), "ty")
call_ch = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
bel.set_node_pos(call_ch, pos(1450, Y + 1320))
connect(find_pin(pr_yes, "then", "Output"), find_pin(call_ch, "execute", "Input"), "tclr")
pr_no = make_print(ge, 1050, Y + 1500, "Restaurant TRASH: hands empty")
connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "tn")

# ========== HandleStoveE ==========
hs = ge.add_custom_event_node("HandleStoveE")
bel.set_node_pos(hs, pos(0, Y + 1700))
# if holding -> warn
get_h2 = ge.add_get_member_variable_node("HeldDishId"); bel.set_node_pos(get_h2, pos(250, Y + 1780))
ne2 = ne_int(ge, 500, Y + 1780)
connect(out_data(get_h2), find_pin(ne2, "A", "Input"), "h2")
setdef(find_pin(ne2, "B", "Input"), "0")
br_h = ge.add_branch_node(); bel.set_node_pos(br_h, pos(750, Y + 1700))
connect(find_pin(hs, "then", "Output"), find_pin(br_h, "execute", "Input"), "stove")
connect(out_data(ne2), find_pin(br_h, "Condition", "Input"), "hold?")
pr_hold = make_print(ge, 1050, Y + 1620, "Restaurant STOVE: holding dish — serve or trash first")
connect(find_pin(br_h, "then", "Output"), find_pin(pr_hold, "execute", "Input"), "sh")

# else get stove
gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao, pos(1050, Y + 1750))
connect(find_pin(br_h, "else", "Output"), find_pin(gao, "execute", "Input"), "->stoveA")
setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
       "/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C")
get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(get0, pos(1350, Y + 1830))
connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), "sarr")
setdef(find_pin(get0, "Index", "Input"), "0")

# Call Stove.OnPlayerE from Manager — add that event on stove that handles ready/cooking/start via callbacks
# For now inline: Call custom Stove.TryInteract which we add below after compile... 
# Use Manager logic with Get member on stove via create_node Get bCookReady targeting stove — needs cast.
# Instead Call Stove.PlayerE (we'll add)

call_sp = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:PlayerE")
bel.set_node_pos(call_sp, pos(1650, Y + 1750))
connect(find_pin(gao, "then", "Output"), find_pin(call_sp, "execute", "Input"), "sp")
connect(find_pin(get0, "Item", "Output"), find_pin(call_sp, "self", "Input"), "spself")

# ========== EvalTableE ==========
# Assumes ActiveTableId/DishId/Pending set; uses Held*
et = ge.add_custom_event_node("EvalTableE")
bel.set_node_pos(et, pos(0, Y + 2100))
get_hd = ge.add_get_member_variable_node("HeldDishId"); bel.set_node_pos(get_hd, pos(250, Y + 2180))
eq0 = eq_int(ge, 500, Y + 2180)
connect(out_data(get_hd), find_pin(eq0, "A", "Input"), "eq0A")
setdef(find_pin(eq0, "B", "Input"), "0")
br0 = ge.add_branch_node(); bel.set_node_pos(br0, pos(750, Y + 2100))
connect(find_pin(et, "then", "Output"), find_pin(br0, "execute", "Input"), "eval")
connect(out_data(eq0), find_pin(br0, "Condition", "Input"), "empty?")
# empty hands -> print status
pr_st = make_print(ge, 1050, Y + 2020, "Restaurant TABLE status: see order/patience (hands empty)")
connect(find_pin(br0, "then", "Output"), find_pin(pr_st, "execute", "Input"), "stat")
# also call Table.PrintStatus on matching — skip detail print via ActivePending
get_ap = ge.add_get_member_variable_node("bActivePending"); bel.set_node_pos(get_ap, pos(1050, Y + 2140))
br_ap = ge.add_branch_node(); bel.set_node_pos(br_ap, pos(1350, Y + 2100))
connect(find_pin(pr_st, "then", "Output"), find_pin(br_ap, "execute", "Input"), "ap")
connect(out_data(get_ap), find_pin(br_ap, "Condition", "Input"), "pend?")
pr_p = make_print(ge, 1650, Y + 2020, "Restaurant TABLE: order pending (cook at stove)")
connect(find_pin(br_ap, "then", "Output"), find_pin(pr_p, "execute", "Input"), "pp")
pr_np = make_print(ge, 1650, Y + 2180, "Restaurant TABLE: occupied / eating / no pending")
connect(find_pin(br_ap, "else", "Output"), find_pin(pr_np, "execute", "Input"), "pnp")

# holding: match ActiveTableId==HeldTableId and ActiveDishId==HeldDishId
get_ht = ge.add_get_member_variable_node("HeldTableId"); bel.set_node_pos(get_ht, pos(1050, Y + 2350))
get_at = ge.add_get_member_variable_node("ActiveTableId"); bel.set_node_pos(get_at, pos(1050, Y + 2430))
eq_t = eq_int(ge, 1350, Y + 2380)
connect(out_data(get_ht), find_pin(eq_t, "A", "Input"), "ht")
connect(out_data(get_at), find_pin(eq_t, "B", "Input"), "at")
get_ad = ge.add_get_member_variable_node("ActiveDishId"); bel.set_node_pos(get_ad, pos(1050, Y + 2510))
eq_d = eq_int(ge, 1350, Y + 2500)
connect(out_data(get_hd), find_pin(eq_d, "A", "Input"), "hd")
connect(out_data(get_ad), find_pin(eq_d, "B", "Input"), "ad")
and_b = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
bel.set_node_pos(and_b, pos(1600, Y + 2420))
connect(out_data(eq_t), find_pin(and_b, "A", "Input"), "andA")
connect(out_data(eq_d), find_pin(and_b, "B", "Input"), "andB")
br_m = ge.add_branch_node(); bel.set_node_pos(br_m, pos(1900, Y + 2300))
connect(find_pin(br0, "else", "Output"), find_pin(br_m, "execute", "Input"), "match?")
connect(out_data(and_b), find_pin(br_m, "Condition", "Input"), "matchC")

# correct: ClearHeld + BeginEat on that table
call_ch2 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
bel.set_node_pos(call_ch2, pos(2200, Y + 2200))
connect(find_pin(br_m, "then", "Output"), find_pin(call_ch2, "execute", "Input"), "okclr")
# GetAll tables ForEach Call BeginEatIfActive — Table.BeginEatIfActive checks TableId==Active... 
# Simpler: Call both tables' BeginEatIfMe — each checks own TableId vs need
# Use: GetAll tables, ForEach Call TryBeginEatFromServe
gao_t = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao_t, pos(2500, Y + 2200))
connect(find_pin(call_ch2, "then", "Output"), find_pin(gao_t, "execute", "Input"), "->tbl")
setdef(find_pin(gao_t, "ActorClass", "Input") or find_pin(gao_t, "Class", "Input"),
       "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
fe = add_foreach(ge, 2800, Y + 2200)
connect(find_pin(gao_t, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "fe")
connect(find_pin(gao_t, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "tarr")
call_be = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:BeginEatIfActive")
bel.set_node_pos(call_be, pos(3150, Y + 2200))
connect(find_pin(fe, "LoopBody", "Output"), find_pin(call_be, "execute", "Input"), "be")
connect(find_pin(fe, "Array Element", "Output"), find_pin(call_be, "self", "Input"), "beself")

# wrong: ClearHeld + WrongLeave on active table (all tables WrongLeaveIfActive)
call_ch3 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
bel.set_node_pos(call_ch3, pos(2200, Y + 2500))
connect(find_pin(br_m, "else", "Output"), find_pin(call_ch3, "execute", "Input"), "badclr")
pr_bad = make_print(ge, 2500, Y + 2500, "Restaurant WRONG serve — dish gone, guest leaves $0")
connect(find_pin(call_ch3, "then", "Output"), find_pin(pr_bad, "execute", "Input"), "badpr")
gao_t2 = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao_t2, pos(2850, Y + 2500))
connect(find_pin(pr_bad, "then", "Output"), find_pin(gao_t2, "execute", "Input"), "->tbl2")
setdef(find_pin(gao_t2, "ActorClass", "Input") or find_pin(gao_t2, "Class", "Input"),
       "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
fe2 = add_foreach(ge, 3150, Y + 2500)
connect(find_pin(gao_t2, "then", "Output"), find_pin(fe2, "Exec", "Input") or find_pin(fe2, "execute", "Input"), "fe2")
connect(find_pin(gao_t2, "OutActors", "Output"), find_pin(fe2, "Array", "Input"), "tarr2")
call_wl = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:WrongLeaveIfActive")
bel.set_node_pos(call_wl, pos(3500, Y + 2500))
connect(find_pin(fe2, "LoopBody", "Output"), find_pin(call_wl, "execute", "Input"), "wl")
connect(find_pin(fe2, "Array Element", "Output"), find_pin(call_wl, "self", "Input"), "wlself")

# ========== HandleTableE: nearest table pushes context then Eval ==========
hte = ge.add_custom_event_node("HandleTableE")
bel.set_node_pos(hte, pos(0, Y + 2800))
# GetAll tables ForEach distance — Call PushContextAndEval on each near
gao3 = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao3, pos(300, Y + 2800))
connect(find_pin(hte, "then", "Output"), find_pin(gao3, "execute", "Input"), "hte")
setdef(find_pin(gao3, "ActorClass", "Input") or find_pin(gao3, "Class", "Input"),
       "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
fe3 = add_foreach(ge, 600, Y + 2800)
connect(find_pin(gao3, "then", "Output"), find_pin(fe3, "Exec", "Input") or find_pin(fe3, "execute", "Input"), "fe3")
connect(find_pin(gao3, "OutActors", "Output"), find_pin(fe3, "Array", "Input"), "arr3")
# distance check
pawn = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(pawn, pos(600, Y + 3000))
setdef(find_pin(pawn, "PlayerIndex", "Input") or find_pin(pawn, "Index", "Input"), "0")
ploc = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(ploc, pos(900, Y + 3000))
connect(out_data(pawn), find_pin(ploc, "self", "Input"), "pl")
aloc = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(aloc, pos(900, Y + 2880))
connect(find_pin(fe3, "Array Element", "Output"), find_pin(aloc, "self", "Input"), "al")
dist = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
bel.set_node_pos(dist, pos(1200, Y + 2920))
connect(out_data(ploc), find_pin(dist, "V1", "Input") or find_pin(dist, "A", "Input"), "v1")
connect(out_data(aloc), find_pin(dist, "V2", "Input") or find_pin(dist, "B", "Input"), "v2")
lt = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
if lt is None:
    lt = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
bel.set_node_pos(lt, pos(1500, Y + 2920))
connect(out_data(dist), find_pin(lt, "A", "Input"), "d")
setdef(find_pin(lt, "B", "Input"), "280.0")
brn = ge.add_branch_node(); bel.set_node_pos(brn, pos(1750, Y + 2800))
connect(find_pin(fe3, "LoopBody", "Output"), find_pin(brn, "execute", "Input"), "near")
connect(out_data(lt), find_pin(brn, "Condition", "Input"), "nearC")
call_pe = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:PushContextAndEval")
bel.set_node_pos(call_pe, pos(2100, Y + 2800))
connect(find_pin(brn, "then", "Output"), find_pin(call_pe, "execute", "Input"), "pe")
connect(find_pin(fe3, "Array Element", "Output"), find_pin(call_pe, "self", "Input"), "peself")

# ========== DispatchNonSignE ==========
disp = ge.add_custom_event_node("DispatchNonSignE")
bel.set_node_pos(disp, pos(0, Y + 3300))
# scan RestInteract nearest of stove/trash/table by name Contains
gaw = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
bel.set_node_pos(gaw, pos(300, Y + 3300))
connect(find_pin(disp, "then", "Output"), find_pin(gaw, "execute", "Input"), "disp")
setdef(find_pin(gaw, "Tag", "Input"), "RestInteract")
fe4 = add_foreach(ge, 600, Y + 3300)
connect(find_pin(gaw, "then", "Output"), find_pin(fe4, "Exec", "Input") or find_pin(fe4, "execute", "Input"), "fe4")
connect(find_pin(gaw, "OutActors", "Output"), find_pin(fe4, "Array", "Input"), "arr4")
pawn2 = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(pawn2, pos(600, Y + 3500))
setdef(find_pin(pawn2, "PlayerIndex", "Input") or find_pin(pawn2, "Index", "Input"), "0")
pl2 = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(pl2, pos(900, Y + 3500))
connect(out_data(pawn2), find_pin(pl2, "self", "Input"), "pl2")
al2 = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(al2, pos(900, Y + 3380))
connect(find_pin(fe4, "Array Element", "Output"), find_pin(al2, "self", "Input"), "al2")
dist2 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
bel.set_node_pos(dist2, pos(1200, Y + 3420))
connect(out_data(pl2), find_pin(dist2, "V1", "Input") or find_pin(dist2, "A", "Input"), "v1b")
connect(out_data(al2), find_pin(dist2, "V2", "Input") or find_pin(dist2, "B", "Input"), "v2b")
lt2 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
if lt2 is None:
    lt2 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
bel.set_node_pos(lt2, pos(1500, Y + 3420))
connect(out_data(dist2), find_pin(lt2, "A", "Input"), "db")
setdef(find_pin(lt2, "B", "Input"), "280.0")
br5 = ge.add_branch_node(); bel.set_node_pos(br5, pos(1750, Y + 3300))
connect(find_pin(fe4, "LoopBody", "Output"), find_pin(br5, "execute", "Input"), "n5")
connect(out_data(lt2), find_pin(br5, "Condition", "Input"), "n5c")
gdn = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
bel.set_node_pos(gdn, pos(2000, Y + 3420))
connect(find_pin(fe4, "Array Element", "Output"), find_pin(gdn, "Object", "Input"), "gdn")
# Contains Stove
cs = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains")
bel.set_node_pos(cs, pos(2300, Y + 3300))
connect(out_data(gdn), find_pin(cs, "SearchIn", "Input"), "csIn")
setdef(find_pin(cs, "Substring", "Input"), "Stove")
brs = ge.add_branch_node(); bel.set_node_pos(brs, pos(2600, Y + 3300))
connect(find_pin(br5, "then", "Output"), find_pin(brs, "execute", "Input"), "bs")
connect(out_data(cs), find_pin(brs, "Condition", "Input"), "bsc")
call_hs = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandleStoveE")
bel.set_node_pos(call_hs, pos(2950, Y + 3200))
connect(find_pin(brs, "then", "Output"), find_pin(call_hs, "execute", "Input"), "hs")
# Trash
ct = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains")
bel.set_node_pos(ct, pos(2950, Y + 3400))
connect(out_data(gdn), find_pin(ct, "SearchIn", "Input"), "ctIn")
setdef(find_pin(ct, "Substring", "Input"), "Trash")
brt = ge.add_branch_node(); bel.set_node_pos(brt, pos(3300, Y + 3400))
connect(find_pin(brs, "else", "Output"), find_pin(brt, "execute", "Input"), "bt")
connect(out_data(ct), find_pin(brt, "Condition", "Input"), "btc")
call_ht = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandleTrashE")
bel.set_node_pos(call_ht, pos(3650, Y + 3320))
connect(find_pin(brt, "then", "Output"), find_pin(call_ht, "execute", "Input"), "ht")
# Table
cta = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains")
bel.set_node_pos(cta, pos(3650, Y + 3550))
connect(out_data(gdn), find_pin(cta, "SearchIn", "Input"), "ctaIn")
setdef(find_pin(cta, "Substring", "Input"), "Table")
brta = ge.add_branch_node(); bel.set_node_pos(brta, pos(4000, Y + 3500))
connect(find_pin(brt, "else", "Output"), find_pin(brta, "execute", "Input"), "bta")
connect(out_data(cta), find_pin(brta, "Condition", "Input"), "btac")
call_hte = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandleTableE")
bel.set_node_pos(call_hte, pos(4350, Y + 3420))
connect(find_pin(brta, "then", "Output"), find_pin(call_hte, "execute", "Input"), "hte2")
pr_o = make_print(ge, 4350, Y + 3600, "Restaurant E (other)")
connect(find_pin(brta, "else", "Output"), find_pin(pr_o, "execute", "Input"), "other")

# Patch HandlePlayerE: OpenSign else currently Print — redirect to DispatchNonSignE
# Find Contains OpenSign branch else -> PrintString; break and wire Dispatch
patched = False
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "Contains":
        continue
    sub = find_pin(n, "Substring", "Input")
    if not sub or "OpenSign" not in str(sub.get_pin_value()):
        continue
    # find branch that uses this Contains as condition
    ret = find_pin(n, "ReturnValue", "Output")
    if not ret:
        continue
    for c in ret.list_connected_pins():
        brn = c.get_owning_node()
        if brn.get_class().get_name() != "K2Node_IfThenElse":
            continue
        else_p = find_pin(brn, "else", "Output")
        if else_p:
            else_p.break_pin_links()
            call_d = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:DispatchNonSignE")
            bel.set_node_pos(call_d, pos(3200, 200))
            connect(else_p, find_pin(call_d, "execute", "Input"), "else->dispatch")
            patched = True
            log("patched OpenSign else -> DispatchNonSignE")
R["patched"] = patched

bel.compile_blueprint(bp)
R["status"] = str(bp.get_editor_property("status"))
if "ERROR" in R["status"]:
    for n in ge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                R["errors"].append(bel.get_node_title(n) + ": " + str(em)[:220])
        except Exception:
            pass
else:
    unreal.EditorAssetLibrary.save_asset(PATH)
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_manager.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps({k: R[k] for k in ("status", "patched", "errors", "steps")}, indent=2, ensure_ascii=False)[:8000])