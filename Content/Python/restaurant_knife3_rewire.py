# -*- coding: utf-8 -*-
"""Rewire skipped CallFunction nodes now that events exist; fix Eval serve + Table pay/void."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {"steps": [], "errors": [], "statuses": {}}

def log(m):
    unreal.log("[K3RW] " + str(m)); R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Item", "ActiveTableId", "HeldDishId", "CurrentDishId", "OutActors"):
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

def pin_has_links(p):
    if not p:
        return True
    try:
        return len(list(p.list_connected_pins())) > 0
    except Exception:
        return True

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

def class_pin_is(gao, substr):
    p = find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input")
    if not p:
        return False
    try:
        return substr.lower() in str(p.get_pin_value()).lower()
    except Exception:
        return False

def wire_call_after_gao(ge, gao, call_path, label, y_off=0):
    """If gao.then unlinked, add Call and Array_Get Item -> self."""
    then = find_pin(gao, "then", "Output")
    if pin_has_links(then):
        log("already " + label)
        return None
    get0 = None
    # find existing Array_Get connected to OutActors
    outa = find_pin(gao, "OutActors", "Output")
    if outa:
        for c in outa.list_connected_pins():
            n = c.get_owning_node()
            if "Array_Get" in n.get_class().get_name() or "Get" in bel.get_node_title(n):
                get0 = n
                break
    if get0 is None:
        get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
        bel.set_node_pos(get0, pos(int(bel.get_node_pos(gao).x) + 300, int(bel.get_node_pos(gao).y) + 80 + y_off))
        connect(outa, find_pin(get0, "TargetArray", "Input"), label + "arr")
        setdef(find_pin(get0, "Index", "Input"), "0")
    call = ge.add_call_function_node(call_path)
    if call is None:
        log("NULL call " + call_path)
        return None
    bel.set_node_pos(call, pos(int(bel.get_node_pos(gao).x) + 550, int(bel.get_node_pos(gao).y) + y_off))
    connect(then, find_pin(call, "execute", "Input"), label + "exec")
    connect(find_pin(get0, "Item", "Output"), find_pin(call, "self", "Input"), label + "self")
    return call

def wire_self_call(ge, exec_pin, call_path, label, x, y):
    if pin_has_links(exec_pin):
        log("already exec " + label)
        return None
    call = ge.add_call_function_node(call_path)
    if call is None:
        log("NULL " + call_path); return None
    bel.set_node_pos(call, pos(x, y))
    connect(exec_pin, find_pin(call, "execute", "Input"), label)
    return call

# ===================== STOVE rewire =====================
SP = "/Game/Farm/Restaurant/BP_RestaurantStove"
sbp = unreal.EditorAssetLibrary.load_asset(SP)
sge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(sbp))

# Find GetAllActors targeting Manager near PlayerE ready branches with unlinked then
for n in list(sge.list_all_nodes()):
    if "GetAllActorsOfClass" not in bel.get_node_title(n) and n.get_class().get_name() != "K2Node_CallFunction":
        continue
    title = bel.get_node_title(n)
    if "Get All Actors Of Class" not in title and "GetAllActorsOfClass" not in title:
        # also check function name
        pass
    if not class_pin_is(n, "Manager"):
        continue
    then = find_pin(n, "then", "Output")
    if pin_has_links(then):
        continue
    # Determine which Receive by nearby CookingDishId context — use Y position heuristic from our layout
    y = int(bel.get_node_pos(n).y)
    # Y+1200 Salad1, +1450 Salad2, +1550 Stew1, +1800 Stew2 (approx from script Y+1500 base)
    if y < 2800:
        ev = "ReceiveSalad1"
    elif y < 3050:
        ev = "ReceiveSalad2"
    elif y < 3300:
        ev = "ReceiveStew1"
    else:
        ev = "ReceiveStew2"
    # Better: look at connected exec source branch
    # For now use order of unlinked Manager GAOs
    pass

# Collect unlinked Manager GAOs in Y order
mgr_gaos = []
for n in sge.list_all_nodes():
    if "Get All Actors Of Class" in bel.get_node_title(n) and class_pin_is(n, "Manager"):
        then = find_pin(n, "then", "Output")
        if not pin_has_links(then):
            mgr_gaos.append((int(bel.get_node_pos(n).y), n))
mgr_gaos.sort(key=lambda t: t[0])
recv_names = ["ReceiveSalad1", "ReceiveSalad2", "ReceiveStew1", "ReceiveStew2"]
for i, (y, gao) in enumerate(mgr_gaos[:4]):
    name = recv_names[i]
    call = wire_call_after_gao(sge, gao, "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:" + name, name)
    if call:
        # ForceClear after
        then2 = find_pin(call, "then", "Output")
        if then2 and not pin_has_links(then2):
            fc = sge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:ForceClear")
            bel.set_node_pos(fc, pos(int(bel.get_node_pos(call).x) + 350, int(bel.get_node_pos(call).y)))
            connect(then2, find_pin(fc, "execute", "Input"), name + "fc")

# TryClaimCook on Table GAO from PlayerE idle
for n in sge.list_all_nodes():
    if "Get All Actors Of Class" in bel.get_node_title(n) and class_pin_is(n, "Table"):
        # find ForEach with unlinked LoopBody call
        outa = find_pin(n, "OutActors", "Output")
        if not outa:
            continue
        for c in outa.list_connected_pins():
            fe = c.get_owning_node()
            if "ForEach" not in bel.get_node_title(fe) and fe.get_class().get_name() != "K2Node_MacroInstance":
                continue
            body = find_pin(fe, "LoopBody", "Output")
            if body and not pin_has_links(body):
                call = sge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:TryClaimCook")
                bel.set_node_pos(call, pos(int(bel.get_node_pos(fe).x) + 350, int(bel.get_node_pos(fe).y)))
                connect(body, find_pin(call, "execute", "Input"), "claim")
                connect(find_pin(fe, "Array Element", "Output"), find_pin(call, "self", "Input"), "claimself")

compile_save(sbp, SP, "stove")

# ===================== MANAGER rewire =====================
MP = "/Game/Farm/Restaurant/BP_RestaurantManager"
mbp = unreal.EditorAssetLibrary.load_asset(MP)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# HandleTrashE: Print then -> ClearHeld
for n in mge.list_all_nodes():
    if bel.get_node_title(n) != "Print String":
        continue
    # check string
    insp = find_pin(n, "InString", "Input")
    if not insp:
        continue
    try:
        s = str(insp.get_pin_value())
    except Exception:
        continue
    if "TRASH: discarded" in s:
        th = find_pin(n, "then", "Output")
        if th and not pin_has_links(th):
            wire_self_call(mge, th, "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld",
                           "trashClear", int(bel.get_node_pos(n).x) + 400, int(bel.get_node_pos(n).y))

# HandleStoveE: GetAll Stove then -> PlayerE
for n in mge.list_all_nodes():
    if "Get All Actors Of Class" in bel.get_node_title(n) and class_pin_is(n, "Stove"):
        wire_call_after_gao(mge, n, "/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:PlayerE", "PlayerE")

# Dispatch: Stove/Trash/Table Contains branches
for n in mge.list_all_nodes():
    if bel.get_node_title(n) != "Contains":
        continue
    sub = find_pin(n, "Substring", "Input")
    if not sub:
        continue
    try:
        ss = str(sub.get_pin_value())
    except Exception:
        continue
    ret = find_pin(n, "ReturnValue", "Output")
    if not ret:
        continue
    for c in ret.list_connected_pins():
        br = c.get_owning_node()
        if br.get_class().get_name() != "K2Node_IfThenElse":
            continue
        thenp = find_pin(br, "then", "Output")
        if not thenp or pin_has_links(thenp):
            continue
        path = None
        if ss == "Stove":
            path = "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandleStoveE"
        elif ss == "Trash":
            path = "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandleTrashE"
        elif ss == "Table":
            path = "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandleTableE"
        if path:
            wire_self_call(mge, thenp, path, "disp" + ss, int(bel.get_node_pos(br).x) + 350, int(bel.get_node_pos(br).y))

# OpenSign else -> DispatchNonSignE
for n in mge.list_all_nodes():
    if bel.get_node_title(n) != "Contains":
        continue
    sub = find_pin(n, "Substring", "Input")
    if not sub:
        continue
    try:
        if "OpenSign" not in str(sub.get_pin_value()):
            continue
    except Exception:
        continue
    ret = find_pin(n, "ReturnValue", "Output")
    for c in ret.list_connected_pins():
        br = c.get_owning_node()
        if br.get_class().get_name() != "K2Node_IfThenElse":
            continue
        elsep = find_pin(br, "else", "Output")
        if elsep and not pin_has_links(elsep):
            wire_self_call(mge, elsep, "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:DispatchNonSignE",
                           "dispatch", int(bel.get_node_pos(br).x) + 400, int(bel.get_node_pos(br).y) + 80)

# HandleTableE: near then -> PushContextAndEval
for n in mge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_MacroInstance":
        continue
    if "ForEach" not in bel.get_node_title(n):
        continue
    body = find_pin(n, "LoopBody", "Output")
    if not body:
        continue
    # find branch after body
    for c in body.list_connected_pins():
        br = c.get_owning_node()
        if br.get_class().get_name() != "K2Node_IfThenElse":
            continue
        thenp = find_pin(br, "then", "Output")
        if thenp and not pin_has_links(thenp):
            # likely distance branch for tables
            call = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:PushContextAndEval")
            if call:
                bel.set_node_pos(call, pos(int(bel.get_node_pos(br).x) + 350, int(bel.get_node_pos(br).y)))
                connect(thenp, find_pin(call, "execute", "Input"), "PushEval")
                # self from ForEach Array Element
                connect(find_pin(n, "Array Element", "Output"), find_pin(call, "self", "Input"), "PushEvalSelf")

# EvalTableE correct/wrong paths: replace BeginEatIfActive / WrongLeaveIfActive
# Find ClearHeld calls with unlinked then, or GAO Table with ForEach calling missing events
# Rebuild serve completion: find EvalTableE custom event and patch match branches

# Remove broken ForEach BeginEatIfActive / WrongLeaveIfActive call nodes if any exist as error
# Add after ClearHeld on correct path: branch ActiveTableId -> ForEach BeginEatOnlyIfId1/2

# Find EvalTableE
eval_ev = None
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_CustomEvent" and bel.get_node_title(n) == "EvalTableE":
        eval_ev = n
        break

# Find BooleanAND used for match in Eval — then branch then/else
# Look for print WRONG serve
for n in list(mge.list_all_nodes()):
    if bel.get_node_title(n) != "Print String":
        continue
    insp = find_pin(n, "InString", "Input")
    try:
        s = str(insp.get_pin_value()) if insp else ""
    except Exception:
        s = ""
    if "WRONG serve" in s:
        # ensure ClearHeld before it
        # find incoming — if none, wire from match else
        pass

# Find match Branch (BooleanAND -> Condition) near Eval
match_br = None
for n in mge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_CallFunction":
        continue
    if "BooleanAND" not in bel.get_node_title(n) and "AND" not in bel.get_node_title(n):
        continue
    ret = find_pin(n, "ReturnValue", "Output")
    if not ret:
        continue
    for c in ret.list_connected_pins():
        br = c.get_owning_node()
        if br.get_class().get_name() == "K2Node_IfThenElse":
            # check if in Eval region by Y
            if int(bel.get_node_pos(br).y) > 4000:  # Y+2100 base from manager script ~4300
                match_br = br
                break

if match_br is None:
    # fallback: any AND->Branch with then unlinked or calling missing
    for n in mge.list_all_nodes():
        if "BooleanAND" in bel.get_node_title(n) or bel.get_node_title(n) == "AND":
            ret = find_pin(n, "ReturnValue", "Output")
            if not ret:
                continue
            for c in ret.list_connected_pins():
                br = c.get_owning_node()
                if br.get_class().get_name() == "K2Node_IfThenElse":
                    match_br = br

if match_br:
    thenp = find_pin(match_br, "then", "Output")
    elsep = find_pin(match_br, "else", "Output")
    # Break existing broken links on then/else and rebuild
    if thenp:
        thenp.break_pin_links()
    if elsep:
        elsep.break_pin_links()

    # CORRECT path
    call_ch = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
    bel.set_node_pos(call_ch, pos(int(bel.get_node_pos(match_br).x) + 300, int(bel.get_node_pos(match_br).y) - 100))
    connect(thenp, find_pin(call_ch, "execute", "Input"), "okClear")
    pr_ok = make_print(mge, int(bel.get_node_pos(match_br).x) + 650, int(bel.get_node_pos(match_br).y) - 100,
                       "Restaurant SERVE OK — guest eating")
    connect(find_pin(call_ch, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "okPr")
    get_at = mge.add_get_member_variable_node("ActiveTableId")
    bel.set_node_pos(get_at, pos(int(bel.get_node_pos(match_br).x) + 650, int(bel.get_node_pos(match_br).y)))
    eq = eq_int(mge, int(bel.get_node_pos(match_br).x) + 900, int(bel.get_node_pos(match_br).y))
    connect(out_data(get_at), find_pin(eq, "A", "Input"), "at")
    setdef(find_pin(eq, "B", "Input"), "1")
    br_t = mge.add_branch_node()
    bel.set_node_pos(br_t, pos(int(bel.get_node_pos(match_br).x) + 1150, int(bel.get_node_pos(match_br).y) - 100))
    connect(find_pin(pr_ok, "then", "Output"), find_pin(br_t, "execute", "Input"), "whichT")
    connect(out_data(eq), find_pin(br_t, "Condition", "Input"), "isT1")

    def foreach_table_call(ge, exec_pin, event_name, x, y):
        gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
        bel.set_node_pos(gao, pos(x, y))
        connect(exec_pin, find_pin(gao, "execute", "Input"), event_name + "gao")
        setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
               "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
        fe = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
        bel.set_node_pos(fe, pos(x + 300, y))
        connect(find_pin(gao, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), event_name + "fe")
        connect(find_pin(gao, "OutActors", "Output"), find_pin(fe, "Array", "Input"), event_name + "arr")
        call = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:" + event_name)
        bel.set_node_pos(call, pos(x + 650, y))
        connect(find_pin(fe, "LoopBody", "Output"), find_pin(call, "execute", "Input"), event_name + "call")
        connect(find_pin(fe, "Array Element", "Output"), find_pin(call, "self", "Input"), event_name + "self")

    bx = int(bel.get_node_pos(match_br).x) + 1450
    by = int(bel.get_node_pos(match_br).y) - 100
    foreach_table_call(mge, find_pin(br_t, "then", "Output"), "BeginEatOnlyIfId1", bx, by - 50)
    foreach_table_call(mge, find_pin(br_t, "else", "Output"), "BeginEatOnlyIfId2", bx, by + 150)

    # WRONG path
    call_ch2 = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
    bel.set_node_pos(call_ch2, pos(int(bel.get_node_pos(match_br).x) + 300, int(bel.get_node_pos(match_br).y) + 250))
    connect(elsep, find_pin(call_ch2, "execute", "Input"), "badClear")
    pr_bad = make_print(mge, int(bel.get_node_pos(match_br).x) + 650, int(bel.get_node_pos(match_br).y) + 250,
                        "Restaurant WRONG serve — dish gone, guest leaves $0")
    connect(find_pin(call_ch2, "then", "Output"), find_pin(pr_bad, "execute", "Input"), "badPr")
    get_at2 = mge.add_get_member_variable_node("ActiveTableId")
    bel.set_node_pos(get_at2, pos(int(bel.get_node_pos(match_br).x) + 650, int(bel.get_node_pos(match_br).y) + 350))
    eq2 = eq_int(mge, int(bel.get_node_pos(match_br).x) + 900, int(bel.get_node_pos(match_br).y) + 350)
    connect(out_data(get_at2), find_pin(eq2, "A", "Input"), "at2")
    setdef(find_pin(eq2, "B", "Input"), "1")
    br_t2 = mge.add_branch_node()
    bel.set_node_pos(br_t2, pos(int(bel.get_node_pos(match_br).x) + 1150, int(bel.get_node_pos(match_br).y) + 250))
    connect(find_pin(pr_bad, "then", "Output"), find_pin(br_t2, "execute", "Input"), "whichTw")
    connect(out_data(eq2), find_pin(br_t2, "Condition", "Input"), "isT1w")
    foreach_table_call(mge, find_pin(br_t2, "then", "Output"), "WrongLeaveOnlyIfId1", bx, by + 250)
    foreach_table_call(mge, find_pin(br_t2, "else", "Output"), "WrongLeaveOnlyIfId2", bx, by + 450)
    log("rebuilt Eval match paths")
else:
    log("WARN no match_br found")

compile_save(mbp, MP, "manager")

# ===================== TABLE pay + void on tick =====================
TP = "/Game/Farm/Restaurant/BP_RestaurantTable"
tbp = unreal.EditorAssetLibrary.load_asset(TP)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))

# Find eat-done path: when EatLeft <= 0 clears — look for Print about pay or ClearSeat after eating
# Probe: list custom events and find Tick branch for eating done
# Add PayAndClear custom event that calls Manager OnGuestPaid* then ClearSeat
kill = [n for n in tge.list_all_nodes()
        if n.get_class().get_name() == "K2Node_CustomEvent"
        and bel.get_node_title(n) in ("PayAndClear", "TimeoutLeave")]
if kill:
    tge.remove_nodes(kill)

pac = tge.add_custom_event_node("PayAndClear")
bel.set_node_pos(pac, pos(0, 5600))
get_d = tge.add_get_member_variable_node("CurrentDishId"); bel.set_node_pos(get_d, pos(250, 5680))
eq = eq_int(tge, 500, 5680)
connect(out_data(get_d), find_pin(eq, "A", "Input"), "pd")
setdef(find_pin(eq, "B", "Input"), "1")
br = tge.add_branch_node(); bel.set_node_pos(br, pos(750, 5600))
connect(find_pin(pac, "then", "Output"), find_pin(br, "execute", "Input"), "pac")
connect(out_data(eq), find_pin(br, "Condition", "Input"), "salad?")

def call_mgr_pay(ge, exec_pin, event_name, x, y):
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(x, y))
    connect(exec_pin, find_pin(gao, "execute", "Input"), event_name)
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
    get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(x + 280, y + 70))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), event_name + "a")
    setdef(find_pin(get0, "Index", "Input"), "0")
    call = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:" + event_name)
    bel.set_node_pos(call, pos(x + 520, y))
    connect(find_pin(gao, "then", "Output"), find_pin(call, "execute", "Input"), event_name + "c")
    connect(find_pin(get0, "Item", "Output"), find_pin(call, "self", "Input"), event_name + "s")
    clr = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ClearSeat")
    bel.set_node_pos(clr, pos(x + 850, y))
    connect(find_pin(call, "then", "Output"), find_pin(clr, "execute", "Input"), event_name + "clr")
    return clr

call_mgr_pay(tge, find_pin(br, "then", "Output"), "OnGuestPaidSalad", 1000, 5550)
call_mgr_pay(tge, find_pin(br, "else", "Output"), "OnGuestPaidStew", 1000, 5750)

# TimeoutLeave: void stove + ClearSeat $0
tl = tge.add_custom_event_node("TimeoutLeave")
bel.set_node_pos(tl, pos(0, 6000))
pr = make_print(tge, 300, 6000, "Restaurant TIMEOUT leave $0")
connect(find_pin(tl, "then", "Output"), find_pin(pr, "execute", "Input"), "tl")
gaos = tge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gaos, pos(600, 6000))
connect(find_pin(pr, "then", "Output"), find_pin(gaos, "execute", "Input"), "void")
setdef(find_pin(gaos, "ActorClass", "Input") or find_pin(gaos, "Class", "Input"),
       "/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C")
get0 = tge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(get0, pos(900, 6080))
connect(find_pin(gaos, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), "sa")
setdef(find_pin(get0, "Index", "Input"), "0")
voidc = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:VoidIfTable")
bel.set_node_pos(voidc, pos(1150, 6000))
connect(find_pin(gaos, "then", "Output"), find_pin(voidc, "execute", "Input"), "vc")
connect(find_pin(get0, "Item", "Output"), find_pin(voidc, "self", "Input"), "vs")
clr = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ClearSeat")
bel.set_node_pos(clr, pos(1500, 6000))
connect(find_pin(voidc, "then", "Output"), find_pin(clr, "execute", "Input"), "tlclr")

# Patch Tick: find eating done / patience timeout branches that only ClearSeat — redirect to PayAndClear / TimeoutLeave
# Look for ClearSeat call nodes — if from eat done, insert PayAndClear instead
# Safer: find Print strings from knife3_table about paid/timeout
for n in tge.list_all_nodes():
    if bel.get_node_title(n) != "Print String":
        continue
    insp = find_pin(n, "InString", "Input")
    try:
        s = str(insp.get_pin_value()) if insp else ""
    except Exception:
        s = ""
    th = find_pin(n, "then", "Output")
    if not th:
        continue
    # After eat finish print, call PayAndClear instead of/in addition to ClearSeat
    if "EAT done" in s or "finished eating" in s.lower() or "paid" in s.lower() or "客人用餐结束" in s:
        th.break_pin_links()
        call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:PayAndClear")
        bel.set_node_pos(call, pos(int(bel.get_node_pos(n).x) + 400, int(bel.get_node_pos(n).y)))
        connect(th, find_pin(call, "execute", "Input"), "->pay")
        log("patched eat done -> PayAndClear")
    if "TIMEOUT" in s or "patience" in s.lower() or "超时" in s:
        # if then goes to ClearSeat, also Void
        if not pin_has_links(th):
            call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:TimeoutLeave")
            bel.set_node_pos(call, pos(int(bel.get_node_pos(n).x) + 400, int(bel.get_node_pos(n).y)))
            connect(th, find_pin(call, "execute", "Input"), "->timeout")
            log("patched timeout print -> TimeoutLeave")
        else:
            # replace ClearSeat with TimeoutLeave
            th.break_pin_links()
            call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:TimeoutLeave")
            bel.set_node_pos(call, pos(int(bel.get_node_pos(n).x) + 400, int(bel.get_node_pos(n).y)))
            connect(th, find_pin(call, "execute", "Input"), "->timeout2")
            log("replaced timeout chain -> TimeoutLeave")

# If Tick eat-done branch calls ClearSeat directly without print match, find Set bEating false then ClearSeat
# Probe Tick for LessEqual EatLeft
compile_save(tbp, TP, "table")

# Recompile all three once more
for path, key in [(SP, "stove2"), (MP, "manager2"), (TP, "table2")]:
    bp = unreal.EditorAssetLibrary.load_asset(path)
    compile_save(bp, path, key)

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_rewire.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps({k: R[k] for k in ("statuses", "errors", "steps")}, indent=2, ensure_ascii=False)[:9000])