# -*- coding: utf-8 -*-
"""Targeted gap fill: wire dangling Eval/Stove/Table tick by coordinates and titles."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {"steps": [], "errors": [], "statuses": {}, "probe": {}}

def log(m):
    unreal.log("[K3F2] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def out_data(node):
    if not node: return None
    for name in ("ReturnValue", "Item", "ActiveTableId", "OutActors", "Array Element"):
        p = find_pin(node, name, "Output")
        if p: return p
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
    if not pin: return
    try: pin.set_pin_value(str(val))
    except Exception:
        try: pin.set_default_value(str(val))
        except Exception: pass

def pin_links(p):
    if not p: return -1
    try: return len(list(p.list_connected_pins()))
    except: return -1

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
            except Exception: pass
    else:
        unreal.EditorAssetLibrary.save_asset(path)

def foreach_call(ge, exec_pin, actor_path, event_path, event_name, x, y):
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(x, y))
    connect(exec_pin, find_pin(gao, "execute", "Input"), event_name + "gao")
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"), actor_path)
    fe = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    bel.set_node_pos(fe, pos(x + 320, y))
    connect(find_pin(gao, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), event_name + "fe")
    connect(find_pin(gao, "OutActors", "Output"), find_pin(fe, "Array", "Input"), event_name + "arr")
    call = ge.add_call_function_node(event_path)
    if call is None:
        log("NULL " + event_path); return
    bel.set_node_pos(call, pos(x + 680, y))
    connect(find_pin(fe, "LoopBody", "Output"), find_pin(call, "execute", "Input"), event_name + "call")
    connect(find_pin(fe, "Array Element", "Output"), find_pin(call, "self", "Input"), event_name + "self")

def call_on_first(ge, exec_pin, actor_path, event_path, label, x, y, then_chain=None):
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(x, y))
    connect(exec_pin, find_pin(gao, "execute", "Input"), label + "gao")
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"), actor_path)
    get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(x + 300, y + 70))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), label + "arr")
    setdef(find_pin(get0, "Index", "Input"), "0")
    call = ge.add_call_function_node(event_path)
    if call is None:
        log("NULL " + event_path); return None
    bel.set_node_pos(call, pos(x + 560, y))
    connect(find_pin(gao, "then", "Output"), find_pin(call, "execute", "Input"), label + "call")
    connect(find_pin(get0, "Item", "Output"), find_pin(call, "self", "Input"), label + "self")
    if then_chain:
        then_chain(find_pin(call, "then", "Output"), x + 900, y)
    return call

# ========== Probe call titles ==========
MP = "/Game/Farm/Restaurant/BP_RestaurantManager"
mbp = unreal.EditorAssetLibrary.load_asset(MP)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
call_titles = []
for n in mge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Get" in t and "Actor" in t:
        call_titles.append(t)
    if "AND" in t.upper() or "And" in t:
        call_titles.append("ANDNODE:" + t)
R["probe"]["mgr_titles"] = sorted(set(call_titles))[:30]

# Find branch at ~1900,4500
match_br = None
for n in mge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_IfThenElse":
        continue
    p = bel.get_node_pos(n)
    if abs(int(p.x) - 1900) < 50 and abs(int(p.y) - 4500) < 50:
        match_br = n
        break
R["probe"]["match_br"] = match_br is not None

if match_br and pin_links(find_pin(match_br, "then", "Output")) == 0:
    thenp = find_pin(match_br, "then", "Output")
    elsep = find_pin(match_br, "else", "Output")
    bx, by = int(bel.get_node_pos(match_br).x), int(bel.get_node_pos(match_br).y)

    call_ch = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
    bel.set_node_pos(call_ch, pos(bx + 350, by - 80))
    connect(thenp, find_pin(call_ch, "execute", "Input"), "okClear")
    pr = make_print(mge, bx + 700, by - 80, "Restaurant SERVE OK — guest eating")
    connect(find_pin(call_ch, "then", "Output"), find_pin(pr, "execute", "Input"), "okPr")
    get_at = mge.add_get_member_variable_node("ActiveTableId")
    bel.set_node_pos(get_at, pos(bx + 700, by + 20))
    eq = eq_int(mge, bx + 950, by + 20)
    connect(out_data(get_at), find_pin(eq, "A", "Input"), "at")
    setdef(find_pin(eq, "B", "Input"), "1")
    brt = mge.add_branch_node(); bel.set_node_pos(brt, pos(bx + 1200, by - 80))
    connect(find_pin(pr, "then", "Output"), find_pin(brt, "execute", "Input"), "which")
    connect(out_data(eq), find_pin(brt, "Condition", "Input"), "t1")
    foreach_call(mge, find_pin(brt, "then", "Output"),
                 "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C",
                 "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:BeginEatOnlyIfId1",
                 "BE1", bx + 1500, by - 120)
    foreach_call(mge, find_pin(brt, "else", "Output"),
                 "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C",
                 "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:BeginEatOnlyIfId2",
                 "BE2", bx + 1500, by + 80)

    call_ch2 = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
    bel.set_node_pos(call_ch2, pos(bx + 350, by + 220))
    connect(elsep, find_pin(call_ch2, "execute", "Input"), "badClear")
    pr2 = make_print(mge, bx + 700, by + 220, "Restaurant WRONG serve — dish gone, guest $0 leave")
    connect(find_pin(call_ch2, "then", "Output"), find_pin(pr2, "execute", "Input"), "badPr")
    get_at2 = mge.add_get_member_variable_node("ActiveTableId")
    bel.set_node_pos(get_at2, pos(bx + 700, by + 320))
    eq2 = eq_int(mge, bx + 950, by + 320)
    connect(out_data(get_at2), find_pin(eq2, "A", "Input"), "at2")
    setdef(find_pin(eq2, "B", "Input"), "1")
    brt2 = mge.add_branch_node(); bel.set_node_pos(brt2, pos(bx + 1200, by + 220))
    connect(find_pin(pr2, "then", "Output"), find_pin(brt2, "execute", "Input"), "which2")
    connect(out_data(eq2), find_pin(brt2, "Condition", "Input"), "t1b")
    foreach_call(mge, find_pin(brt2, "then", "Output"),
                 "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C",
                 "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:WrongLeaveOnlyIfId1",
                 "WL1", bx + 1500, by + 180)
    foreach_call(mge, find_pin(brt2, "else", "Output"),
                 "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C",
                 "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:WrongLeaveOnlyIfId2",
                 "WL2", bx + 1500, by + 380)
    log("Eval serve paths wired")

# HandleStoveE: find custom event, follow to GetAll Stove with dangling then
for n in mge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_CustomEvent" or bel.get_node_title(n) != "HandleStoveE":
        continue
    # BFS exec from then looking for GetAll with dangling then
    # Simpler: any GetAll with Stove class and dangling then
    break

for n in mge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Actor" not in t:
        continue
    cls = find_pin(n, "ActorClass", "Input") or find_pin(n, "Class", "Input")
    try:
        cv = str(cls.get_pin_value()) if cls else ""
    except Exception:
        cv = ""
    if "Stove" not in cv:
        continue
    then = find_pin(n, "then", "Output")
    if pin_links(then) == 0:
        call = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:PlayerE")
        if call:
            bel.set_node_pos(call, pos(int(bel.get_node_pos(n).x) + 550, int(bel.get_node_pos(n).y)))
            connect(then, find_pin(call, "execute", "Input"), "PlayerE")
            # Array_Get for self
            outa = find_pin(n, "OutActors", "Output")
            get0 = None
            if outa:
                for c in outa.list_connected_pins():
                    get0 = c.get_owning_node(); break
            if get0 is None and outa:
                get0 = mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
                bel.set_node_pos(get0, pos(int(bel.get_node_pos(n).x) + 300, int(bel.get_node_pos(n).y) + 80))
                connect(outa, find_pin(get0, "TargetArray", "Input"), "sarr")
                setdef(find_pin(get0, "Index", "Input"), "0")
            if get0:
                connect(find_pin(get0, "Item", "Output"), find_pin(call, "self", "Input"), "PEself")
            log("wired Stove PlayerE")

# HandleTrashE ClearHeld
for n in mge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_CustomEvent" or bel.get_node_title(n) != "HandleTrashE":
        continue
    # find branch then -> print -> need ClearHeld
    # Walk: event then -> branch; branch then dangling or print then dangling
    then = find_pin(n, "then", "Output")
    # find all PrintString with unlinked then near trash Y (~3600)
    break

for n in mge.list_all_nodes():
    if bel.get_node_title(n) != "Print String":
        continue
    p = bel.get_node_pos(n)
    # trash discarded print around Y+1320 = 3520
    if abs(int(p.y) - 3520) < 100 or abs(int(p.y) - 3600) < 200:
        th = find_pin(n, "then", "Output")
        if pin_links(th) == 0:
            call = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
            if call:
                bel.set_node_pos(call, pos(int(p.x) + 400, int(p.y)))
                connect(th, find_pin(call, "execute", "Input"), "trashClr")

# HandleTableE branch then at 5000,1750 dangling -> PushContextAndEval
for n in mge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_IfThenElse":
        continue
    p = bel.get_node_pos(n)
    if abs(int(p.x) - 1750) < 40 and abs(int(p.y) - 5000) < 40:
        thenp = find_pin(n, "then", "Output")
        if pin_links(thenp) == 0:
            # find owning ForEach for Array Element - search nearby ForEach
            fe = None
            for m in mge.list_all_nodes():
                if "ForEach" in bel.get_node_title(m) or m.get_class().get_name() == "K2Node_MacroInstance":
                    mp = bel.get_node_pos(m)
                    if abs(int(mp.y) - 5000) < 100 and int(mp.x) < int(p.x):
                        fe = m
            call = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:PushContextAndEval")
            if call:
                bel.set_node_pos(call, pos(int(p.x) + 400, int(p.y)))
                connect(thenp, find_pin(call, "execute", "Input"), "Push")
                if fe:
                    connect(find_pin(fe, "Array Element", "Output"), find_pin(call, "self", "Input"), "PushSelf")
                log("wired PushContext")

compile_save(mbp, MP, "manager")

# ========== STOVE: wire Receive* on dangling Manager GetAll ==========
SP = "/Game/Farm/Restaurant/BP_RestaurantStove"
sbp = unreal.EditorAssetLibrary.load_asset(SP)
sge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(sbp))

# List all GetAll-like
stove_gaos = []
for n in sge.list_all_nodes():
    t = bel.get_node_title(n)
    cls = find_pin(n, "ActorClass", "Input") or find_pin(n, "Class", "Input")
    try:
        cv = str(cls.get_pin_value()) if cls else ""
    except Exception:
        cv = ""
    if cls or "Actor" in t:
        stove_gaos.append({"title": t, "cls": cv[-50:], "then": pin_links(find_pin(n, "then", "Output")),
                           "x": int(bel.get_node_pos(n).x), "y": int(bel.get_node_pos(n).y)})
R["probe"]["stove_gaos"] = stove_gaos

recv = ["ReceiveSalad1", "ReceiveSalad2", "ReceiveStew1", "ReceiveStew2"]
idx = 0
for n in sorted(sge.list_all_nodes(), key=lambda n: bel.get_node_pos(n).y):
    cls = find_pin(n, "ActorClass", "Input") or find_pin(n, "Class", "Input")
    try:
        cv = str(cls.get_pin_value()) if cls else ""
    except Exception:
        cv = ""
    if "Manager" not in cv:
        continue
    then = find_pin(n, "then", "Output")
    if pin_links(then) != 0:
        continue
    if idx >= 4:
        break
    name = recv[idx]; idx += 1
    call = sge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:" + name)
    if call is None:
        log("still NULL " + name); continue
    bel.set_node_pos(call, pos(int(bel.get_node_pos(n).x) + 550, int(bel.get_node_pos(n).y)))
    connect(then, find_pin(call, "execute", "Input"), name)
    outa = find_pin(n, "OutActors", "Output")
    get0 = None
    if outa:
        for c in outa.list_connected_pins():
            get0 = c.get_owning_node(); break
    if get0 is None and outa:
        get0 = sge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
        bel.set_node_pos(get0, pos(int(bel.get_node_pos(n).x) + 300, int(bel.get_node_pos(n).y) + 70))
        connect(outa, find_pin(get0, "TargetArray", "Input"), name + "a")
        setdef(find_pin(get0, "Index", "Input"), "0")
    if get0:
        connect(find_pin(get0, "Item", "Output"), find_pin(call, "self", "Input"), name + "s")
    fc = sge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantStove.BP_RestaurantStove_C:ForceClear")
    bel.set_node_pos(fc, pos(int(bel.get_node_pos(n).x) + 900, int(bel.get_node_pos(n).y)))
    connect(find_pin(call, "then", "Output"), find_pin(fc, "execute", "Input"), name + "fc")

# TryClaimCook
for n in sge.list_all_nodes():
    if "ForEach" not in bel.get_node_title(n) and n.get_class().get_name() != "K2Node_MacroInstance":
        continue
    body = find_pin(n, "LoopBody", "Output")
    if body and pin_links(body) == 0:
        # only the idle PlayerE foreach near Y+2000 from base 2900+
        y = int(bel.get_node_pos(n).y)
        if y > 3000:
            call = sge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:TryClaimCook")
            if call:
                bel.set_node_pos(call, pos(int(bel.get_node_pos(n).x) + 400, y))
                connect(body, find_pin(call, "execute", "Input"), "claim")
                connect(find_pin(n, "Array Element", "Output"), find_pin(call, "self", "Input"), "claims")
                log("wired TryClaimCook")

compile_save(sbp, SP, "stove")

# ========== TABLE: patch Tick eat done / patience to PayAndClear / TimeoutLeave ==========
TP = "/Game/Farm/Restaurant/BP_RestaurantTable"
tbp = unreal.EditorAssetLibrary.load_asset(TP)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))

# Dump tick chain: Event Tick -> ...
tick_info = []
for n in tge.list_all_nodes():
    c = n.get_class().get_name()
    t = bel.get_node_title(n)
    if c == "K2Node_Event" and "Tick" in t:
        then = find_pin(n, "then", "Output")
        # follow one step
        nxt = []
        if then:
            for p in then.list_connected_pins():
                nxt.append(bel.get_node_title(p.get_owning_node()))
        tick_info.append({"next": nxt})
    if "ClearSeat" in t or "PayAndClear" in t or "Timeout" in t or "BeginEat" in t:
        tick_info.append({"node": t, "x": int(bel.get_node_pos(n).x), "y": int(bel.get_node_pos(n).y),
                          "cls": c})
R["probe"]["table_tick"] = tick_info[:40]

# Find branches that set EatLeft or call ClearSeat after eating
# Look for Call ClearSeat nodes - if exec comes from eat-done, redirect
clear_calls = []
for n in tge.list_all_nodes():
    if "ClearSeat" in bel.get_node_title(n) and n.get_class().get_name() == "K2Node_CallFunction":
        clear_calls.append(n)

# Find LessEqual on EatLeft -> Branch then -> should PayAndClear
# Find Get EatLeft
for n in tge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_IfThenElse":
        continue
    # if Condition comes from LessEqual involving EatLeft
    cond = find_pin(n, "Condition", "Input")
    if not cond or pin_links(cond) == 0:
        continue
    src = list(cond.list_connected_pins())[0].get_owning_node()
    st = bel.get_node_title(src)
    if "Less" not in st and "nearly" not in st.lower():
        continue
    # Check if A pin connected to EatLeft get or Cook - look at Get nodes near
    # Heuristic by Y from knife3_table: eating branch vs patience
    y = int(bel.get_node_pos(n).y)
    thenp = find_pin(n, "then", "Output")
    if pin_links(thenp) == 0:
        continue
    # See what's connected
    targets = [bel.get_node_title(p.get_owning_node()) for p in thenp.list_connected_pins()]
    R["probe"].setdefault("le_branches", []).append({"y": y, "targets": targets, "src": st})

# Aggressive: find ClearSeat calls that are NOT under PayAndClear/TimeoutLeave/WrongLeave/TrySeat
# and see predecessors
for n in clear_calls:
    # get execute pin incoming
    exe = find_pin(n, "execute", "Input")
    if not exe:
        continue
    preds = []
    for p in exe.list_connected_pins():
        preds.append(bel.get_node_title(p.get_owning_node()))
    y = int(bel.get_node_pos(n).y)
    R["probe"].setdefault("clear_preds", []).append({"y": y, "preds": preds})
    # If pred is Print or Set bEating / Set EatLeft chain from tick eat done (~y 2000 area from knife3)
    # Replace: break incoming, insert PayAndClear for eat; TimeoutLeave for patience
    if y < 2800:  # likely tick region from original table script
        # If any pred suggests eat done (Set member, Print, Branch)
        for p in list(exe.list_connected_pins()):
            pred = p.get_owning_node()
            # redirect pred's output from ClearSeat to PayAndClear or TimeoutLeave
            # Determine: if nearby Get PatienceLeft vs EatLeft
            pass

# Rebuild Tick eat/patience completion cleanly:
# Find Event Tick, find eating branch and patience branch ends that call ClearSeat — patch those ClearSeat to PayAndClear/TimeoutLeave

for n in clear_calls:
    exe = find_pin(n, "execute", "Input")
    y = int(bel.get_node_pos(n).y)
    x = int(bel.get_node_pos(n).x)
    if not exe or pin_links(exe) == 0:
        continue
    # Only patch ClearSeat in Tick graph region (y between 0 and 2800 roughly from knife3_table)
    if y > 3000:
        continue  # PayAndClear's own ClearSeat etc.
    # Check if this ClearSeat is already after PayAndClear - skip if pred is OnGuestPaid or PayAndClear
    preds = [bel.get_node_title(p.get_owning_node()) for p in exe.list_connected_pins()]
    if any("Paid" in p or "PayAnd" in p or "Timeout" in p or "Wrong" in p or "TrySeat" not in p and "Clear" in str(preds) for p in preds):
        # still patch tick ones
        pass
    # Heuristic: eating done ClearSeat is usually after setting bEating false around y~2000-2500
    # Patience timeout ClearSeat similar
    # Look at Get member nodes feeding the Branch that leads here — walk back one Branch

    # Replace this ClearSeat call with PayAndClear if we find EatLeft in the branch condition chain
    # Replace with TimeoutLeave if PatienceLeft
    # Walk back from execute links to a Branch, check its condition source variables
    branch = None
    for p in exe.list_connected_pins():
        node = p.get_owning_node()
        # may be Print or Set then ClearSeat — go back further via execute
        # For simplicity: use Y — knife3_table put patience around one Y and eat around another
        pass

    # Read knife3_table.py from disk for exact strings
    break

# Read table script for print texts
import os
table_py = r"E:\UE\FarmSim25D\Content\Python\restaurant_knife3_table.py"
texts = []
if os.path.exists(table_py):
    txt = open(table_py, encoding="utf-8").read()
    import re
    texts = re.findall(r'PrintString.*?["\']([^"\']+)["\']', txt)
    texts += re.findall(r'make_print\([^)]*["\']([^"\']+)["\']', txt)
    texts += re.findall(r'setdef\(find_pin\(pr.*?["\']([^"\']{5,})["\']', txt)
R["probe"]["table_py_prints"] = texts[:20]

# Direct approach: find ALL CallFunction ClearSeat in tick area; for each, check graph:
# If incoming node title contains Print with empty string, inspect linked Set nodes for variable names

# Simpler nuclear option for tick completion:
# Add at end of Tick: after existing logic, we can't easily.
# Find Branch then that connects to ClearSeat where Branch y < 2800:
for n in list(tge.list_all_nodes()):
    if n.get_class().get_name() != "K2Node_IfThenElse":
        continue
    y = int(bel.get_node_pos(n).y)
    if y > 3000:
        continue
    thenp = find_pin(n, "then", "Output")
    if not thenp or pin_links(thenp) == 0:
        continue
    targets = list(thenp.list_connected_pins())
    for tp in targets:
        tgt = tp.get_owning_node()
        if "ClearSeat" not in bel.get_node_title(tgt):
            # follow one more hop if Print/Set
            t2 = find_pin(tgt, "then", "Output")
            if t2:
                for tp2 in t2.list_connected_pins():
                    tgt2 = tp2.get_owning_node()
                    if "ClearSeat" in bel.get_node_title(tgt2):
                        tgt = tgt2
                        thenp = t2  # will break wrong
                        break
        if "ClearSeat" not in bel.get_node_title(tgt):
            continue
        # Determine Eat vs Patience: look at Condition's LessEqual A source Get variable
        cond = find_pin(n, "Condition", "Input")
        kind = "unknown"
        if cond and pin_links(cond) > 0:
            le = list(cond.list_connected_pins())[0].get_owning_node()
            # LessEqual A pin
            a = find_pin(le, "A", "Input")
            if a and pin_links(a) > 0:
                src = list(a.list_connected_pins())[0].get_owning_node()
                st = bel.get_node_title(src)
                if "Eat" in st:
                    kind = "eat"
                elif "Patience" in st:
                    kind = "patience"
                else:
                    # Get member variable node title is the var name
                    kind = "eat" if "Eat" in st else ("patience" if "Patience" in st else st)
        R["probe"].setdefault("clear_kinds", []).append({"y": y, "kind": kind})
        if kind == "unknown":
            continue
        # Break link to ClearSeat and call PayAndClear / TimeoutLeave instead
        # Find the pin that connects to ClearSeat execute
        exe = find_pin(tgt, "execute", "Input")
        for inp in list(exe.list_connected_pins()):
            inp.break_link_to(exe) if hasattr(inp, "break_link_to") else None
        # break all links on execute
        try:
            exe.break_pin_links()
        except Exception:
            pass
        # Also need to reconnect the predecessor then to new call
        # Find predecessor: the node that was feeding ClearSeat — re-get from Branch chain
        # Re-link branch then (or print then) carefully:
        # Walk from Branch thenp to final ClearSeat, replace ClearSeat node

# Alternative: don't break; add Call PayAndClear on Branch then IN PARALLEL by breaking ClearSeat
# and wiring PayAndClear which itself calls ClearSeat

# Find eat-done and patience-done more carefully by Get member names
for n in list(tge.list_all_nodes()):
    if n.get_class().get_name() != "K2Node_VariableGet":
        continue
    t = bel.get_node_title(n)
    if t not in ("EatLeft", "PatienceLeft"):
        continue
    # Find LessEqual using this
    outp = out_data(n)
    if not outp:
        continue
    for cp in outp.list_connected_pins():
        le = cp.get_owning_node()
        if "Less" not in bel.get_node_title(le):
            continue
        ret = find_pin(le, "ReturnValue", "Output")
        if not ret:
            continue
        for bp in ret.list_connected_pins():
            br = bp.get_owning_node()
            if br.get_class().get_name() != "K2Node_IfThenElse":
                continue
            thenp = find_pin(br, "then", "Output")
            if not thenp:
                continue
            # Break everything on then and wire to PayAndClear / TimeoutLeave
            # But keep print if any — append after
            thenp.break_pin_links()
            if t == "EatLeft":
                call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:PayAndClear")
                bel.set_node_pos(call, pos(int(bel.get_node_pos(br).x) + 400, int(bel.get_node_pos(br).y)))
                connect(thenp, find_pin(call, "execute", "Input"), "->Pay")
                log("EatLeft done -> PayAndClear")
            else:
                call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:TimeoutLeave")
                bel.set_node_pos(call, pos(int(bel.get_node_pos(br).x) + 400, int(bel.get_node_pos(br).y)))
                connect(thenp, find_pin(call, "execute", "Input"), "->Timeout")
                log("PatienceLeft done -> TimeoutLeave")

compile_save(tbp, TP, "table")

# final compile all
for path, key in [(SP, "stoveF"), (MP, "managerF"), (TP, "tableF")]:
    compile_save(unreal.EditorAssetLibrary.load_asset(path), path, key)

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_fix2.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps({k: R[k] for k in ("statuses", "errors", "steps", "probe")}, indent=2, ensure_ascii=False)[:12000])