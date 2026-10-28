# -*- coding: utf-8 -*-
"""Stove.PlayerE: pickup ready / print cooking / start from pending tables."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
PATH = "/Game/Farm/Restaurant/BP_RestaurantStove"
R = {"steps": [], "errors": []}

def log(m):
    unreal.log("[K3SP] " + str(m)); R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Item", "bCooking", "bCookReady", "CookingDishId", "CookingTableId",
                 "CookTimeLeft", "CookingOrder", "bOrderPending", "CurrentDishId", "TableId", "bOccupied", "bEating"):
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

def add_foreach(ge, x, y):
    fe = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    bel.set_node_pos(fe, pos(x, y)); return fe

bp = unreal.EditorAssetLibrary.load_asset(PATH)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# remove existing PlayerE / OfferCookFromTable if re-run
kill = []
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if n.get_class().get_name() == "K2Node_CustomEvent" and t in ("PlayerE", "OfferCookFromTable", "StartCookFromClaim"):
        kill.append(n)
if kill:
    ge.remove_nodes(kill); log("rm " + str(len(kill)))

Y = 1400

# --- OfferCookFromTable: called by Table when pending; starts cook if stove idle ---
# Uses Active claim via Manager Ctx already? Simpler: Table calls StartCookSaladT1 etc.
# Stove events: StartSalad1, StartSalad2, StartStew1, StartStew2

def start_cook(name, dish, table, time_s, order, y):
    ev = ge.add_custom_event_node(name)
    bel.set_node_pos(ev, pos(0, y))
    get_c = ge.add_get_member_variable_node("bCooking"); bel.set_node_pos(get_c, pos(250, y + 80))
    get_r = ge.add_get_member_variable_node("bCookReady"); bel.set_node_pos(get_r, pos(250, y + 160))
    or_b = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    bel.set_node_pos(or_b, pos(500, y + 100))
    connect(out_data(get_c), find_pin(or_b, "A", "Input"), name + "orA")
    connect(out_data(get_r), find_pin(or_b, "B", "Input"), name + "orB")
    br = ge.add_branch_node(); bel.set_node_pos(br, pos(750, y))
    connect(find_pin(ev, "then", "Output"), find_pin(br, "execute", "Input"), name)
    connect(out_data(or_b), find_pin(br, "Condition", "Input"), name + "busy")
    # busy: do nothing
    # free: set cooking
    prev = find_pin(br, "else", "Output")
    x = 1000
    for vn, vv in [
        ("bCooking", "true"),
        ("bCookReady", "false"),
        ("CookingDishId", str(dish)),
        ("CookingTableId", str(table)),
        ("CookTimeLeft", str(time_s)),
        ("CookingOrder", order),
    ]:
        sn = ge.add_set_member_variable_node(vn)
        bel.set_node_pos(sn, pos(x, y))
        connect(prev, find_pin(sn, "execute", "Input"), name + vn)
        setdef(find_pin(sn, vn, "Input"), vv)
        prev = find_pin(sn, "then", "Output")
        x += 260
    pr = make_print(ge, x, y, "Restaurant COOK start {} for Table{} (~{}s)".format(order, table, time_s))
    connect(prev, find_pin(pr, "execute", "Input"), name + "pr")

start_cook("StartSalad1", 1, 1, 3.0, "TomatoSalad", Y)
start_cook("StartSalad2", 1, 2, 3.0, "TomatoSalad", Y + 350)
start_cook("StartStew1", 2, 1, 6.0, "Stew", Y + 700)
start_cook("StartStew2", 2, 2, 6.0, "Stew", Y + 1050)

# --- PlayerE ---
pe = ge.add_custom_event_node("PlayerE")
bel.set_node_pos(pe, pos(0, Y + 1500))

get_r = ge.add_get_member_variable_node("bCookReady"); bel.set_node_pos(get_r, pos(250, Y + 1580))
br_r = ge.add_branch_node(); bel.set_node_pos(br_r, pos(500, Y + 1500))
connect(find_pin(pe, "then", "Output"), find_pin(br_r, "execute", "Input"), "pe")
connect(out_data(get_r), find_pin(br_r, "Condition", "Input"), "ready?")

# READY: call Manager.ReceiveHeldFromStove via dish/table branches
# ReceiveSalad1 / ReceiveSalad2 / ReceiveStew1 / ReceiveStew2 on Manager
get_d = ge.add_get_member_variable_node("CookingDishId"); bel.set_node_pos(get_d, pos(750, Y + 1450))
eq1 = eq_int(ge, 1000, Y + 1450)
connect(out_data(get_d), find_pin(eq1, "A", "Input"), "d1")
setdef(find_pin(eq1, "B", "Input"), "1")
br_d = ge.add_branch_node(); bel.set_node_pos(br_d, pos(1250, Y + 1400))
connect(find_pin(br_r, "then", "Output"), find_pin(br_d, "execute", "Input"), "dish?")
connect(out_data(eq1), find_pin(br_d, "Condition", "Input"), "salad?")

get_t = ge.add_get_member_variable_node("CookingTableId"); bel.set_node_pos(get_t, pos(1500, Y + 1350))
eq_t1 = eq_int(ge, 1750, Y + 1350)
connect(out_data(get_t), find_pin(eq_t1, "A", "Input"), "t1")
setdef(find_pin(eq_t1, "B", "Input"), "1")
br_t = ge.add_branch_node(); bel.set_node_pos(br_t, pos(2000, Y + 1300))
connect(find_pin(br_d, "then", "Output"), find_pin(br_t, "execute", "Input"), "ts")
connect(out_data(eq_t1), find_pin(br_t, "Condition", "Input"), "t1?")

# GetAll Manager once helper at each leaf — call Receive*
def call_mgr_recv(ge, exec_pin, event_name, x, y):
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(x, y))
    connect(exec_pin, find_pin(gao, "execute", "Input"), event_name + "gao")
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
    get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(x + 300, y + 80))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), event_name + "arr")
    setdef(find_pin(get0, "Index", "Input"), "0")
    call = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:" + event_name)
    bel.set_node_pos(call, pos(x + 550, y))
    connect(find_pin(gao, "then", "Output"), find_pin(call, "execute", "Input"), event_name + "call")
    connect(find_pin(get0, "Item", "Output"), find_pin(call, "self", "Input"), event_name + "self")
    # clear stove after
    call_fc = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:ForceClear")
    bel.set_node_pos(call_fc, pos(x + 900, y))
    connect(find_pin(call, "then", "Output"), find_pin(call_fc, "execute", "Input"), event_name + "fc")
    return call_fc

call_mgr_recv(ge, find_pin(br_t, "then", "Output"), "ReceiveSalad1", 2300, Y + 1200)
call_mgr_recv(ge, find_pin(br_t, "else", "Output"), "ReceiveSalad2", 2300, Y + 1450)

get_t2 = ge.add_get_member_variable_node("CookingTableId"); bel.set_node_pos(get_t2, pos(1500, Y + 1650))
eq_t2 = eq_int(ge, 1750, Y + 1650)
connect(out_data(get_t2), find_pin(eq_t2, "A", "Input"), "t2")
setdef(find_pin(eq_t2, "B", "Input"), "1")
br_t2 = ge.add_branch_node(); bel.set_node_pos(br_t2, pos(2000, Y + 1600))
connect(find_pin(br_d, "else", "Output"), find_pin(br_t2, "execute", "Input"), "stew")
connect(out_data(eq_t2), find_pin(br_t2, "Condition", "Input"), "stewt1")
call_mgr_recv(ge, find_pin(br_t2, "then", "Output"), "ReceiveStew1", 2300, Y + 1550)
call_mgr_recv(ge, find_pin(br_t2, "else", "Output"), "ReceiveStew2", 2300, Y + 1800)

# not ready: cooking?
get_c = ge.add_get_member_variable_node("bCooking"); bel.set_node_pos(get_c, pos(750, Y + 1950))
br_c = ge.add_branch_node(); bel.set_node_pos(br_c, pos(1000, Y + 1900))
connect(find_pin(br_r, "else", "Output"), find_pin(br_c, "execute", "Input"), "cook?")
connect(out_data(get_c), find_pin(br_c, "Condition", "Input"), "cookC")
pr_c = make_print(ge, 1300, Y + 1850, "Restaurant STOVE: still cooking...")
connect(find_pin(br_c, "then", "Output"), find_pin(pr_c, "execute", "Input"), "prc")

# idle: ask tables to claim cook
gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao, pos(1300, Y + 2000))
connect(find_pin(br_c, "else", "Output"), find_pin(gao, "execute", "Input"), "idle")
setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
       "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
fe = add_foreach(ge, 1600, Y + 2000)
connect(find_pin(gao, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "fe")
connect(find_pin(gao, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "arr")
call_cl = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:TryClaimCook")
bel.set_node_pos(call_cl, pos(1950, Y + 2000))
connect(find_pin(fe, "LoopBody", "Output"), find_pin(call_cl, "execute", "Input"), "claim")
connect(find_pin(fe, "Array Element", "Output"), find_pin(call_cl, "self", "Input"), "claimself")
# if no claim happened stove stays idle — optional print after loop
pr_none = make_print(ge, 1950, Y + 2200, "Restaurant STOVE: no pending orders (or already claimed)")
connect(find_pin(fe, "Completed", "Output"), find_pin(pr_none, "execute", "Input"), "none")

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
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_stove_pe.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps({k: R[k] for k in ("status", "errors", "steps")}, indent=2, ensure_ascii=False)[:6000])