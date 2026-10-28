# -*- coding: utf-8 -*-
"""Batch: table dish during eat + close-of-business earnings summary.
Idempotent marker: DishDayEnd_v1
"""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
R = {"steps": [], "errors": [], "ok": []}

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
MESH_SALAD = "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Basket"
MESH_STEW = "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate"
MARKER = "DishDayEnd_v1"

def log(m):
    unreal.log("[DISHDAY] " + str(m)); print("[DISHDAY] " + str(m)); R["steps"].append(str(m))

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

def out_data(node):
    if not node: return None
    for name in ("ReturnValue", "Return Value", "TableDishMesh", "HeldDishMesh",
                 "CurrentDishId", "ServedCount", "DayEarned", "RestaurantMoney", "Item"):
        p = find_pin(node, name, "Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n = str(p.get_pin_name()).lower()
            if n not in ("outputdelegate", "then", "else", "completed", "loopbody"):
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); R["errors"].append("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    if not ok: R["errors"].append("fail " + label)
    return ok

def setdef(pin, val):
    if not pin: return False
    try:
        pin.set_pin_value(str(val)); return True
    except Exception:
        try:
            pin.set_default_value(str(val)); return True
        except Exception as e:
            log("setdef " + str(e)[:60]); return False

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def make_print(ge, x, y, text, dur="2.0", key="", color=None):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    if key: setdef(find_pin(pr, "Key", "Input"), key)
    if color:
        # TextColor as LinearColor string
        tp = find_pin(pr, "TextColor", "Input") or find_pin(pr, "Color", "Input")
        if tp: setdef(tp, color)
    return pr

def linear_last(ev, limit=30):
    cur = ev; last = ev
    for _ in range(limit):
        tp = find_pin(cur, "then", "Output")
        if not tp: return last, find_pin(last, "then", "Output")
        links = tp.list_connected_pins() or []
        if not links: return cur, tp
        last = links[0].get_owning_node(); cur = last
    return last, find_pin(last, "then", "Output")

def ensure_var(bp, name, type_name):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    if name in names:
        log("var exists " + name); return
    t = bel.get_basic_type_by_name(type_name)
    bel.add_member_variable(bp, name, t)
    log("var+ " + name)

def walk_kill_from(ge, start):
    kill = [start]; seen = set([id(start)])
    thenp = find_pin(start, "then", "Output")
    queue = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])] if thenp else []
    while queue:
        cur = queue.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); kill.append(cur)
        for pn in ("then", "else", "LoopBody", "Completed"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append(c.get_owning_node())
    return kill

# ========== TABLE ==========
tbp = eas.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary

# 0) TableDishMesh component
handles = list(sub.k2_gather_subobject_data_for_blueprint(tbp) or [])
root_h = None; mesh_obj = None
for h in handles:
    data = sub.k2_find_subobject_data_from_handle(h)
    try:
        if lib.is_root_component(data):
            root_h = h
        vname = str(lib.get_variable_name(data) or "")
        obj = lib.get_associated_object(data) if hasattr(lib, "get_associated_object") else lib.get_object(data)
        if vname == "TableDishMesh":
            mesh_obj = obj
    except Exception as e:
        log("scan " + str(e)[:60])

if mesh_obj is None:
    params = unreal.AddNewSubobjectParams()
    params.set_editor_property("parent_handle", root_h if root_h else handles[0])
    params.set_editor_property("new_class", unreal.StaticMeshComponent)
    params.set_editor_property("blueprint_context", tbp)
    res = sub.add_new_subobject(params)
    new_h = res[0] if isinstance(res, tuple) else res
    try: sub.rename_subobject(new_h, unreal.Text("TableDishMesh"))
    except Exception as e: log("rename " + str(e)[:60])
    data = sub.k2_find_subobject_data_from_handle(new_h)
    mesh_obj = lib.get_associated_object(data) if hasattr(lib, "get_associated_object") else lib.get_object(data)
    log("added TableDishMesh")
else:
    log("TableDishMesh exists")

if mesh_obj:
    try:
        basket = eas.load_asset(MESH_SALAD)
        mesh_obj.set_editor_property("static_mesh", basket)
    except Exception as e: log("mesh set " + str(e)[:60])
    try: mesh_obj.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 55.0))
    except Exception: pass
    try: mesh_obj.set_editor_property("relative_scale3d", unreal.Vector(0.004, 0.004, 0.004))
    except Exception: pass
    try: mesh_obj.set_editor_property("hidden_in_game", True)
    except Exception: pass
    try: mesh_obj.set_editor_property("visible", False)
    except Exception: pass
    R["ok"].append("TableDishMesh")

# Rebuild Show/Hide if marker missing or force rebuild customs
old_show = find_custom(tge, "ShowTableDish")
old_hide = find_custom(tge, "HideTableDish")
if old_show:
    tge.remove_nodes(walk_kill_from(tge, old_show)); log("removed old ShowTableDish")
if old_hide:
    tge.remove_nodes(walk_kill_from(tge, old_hide)); log("removed old HideTableDish")

# ShowTableDish
X, Y = -2200, -2800
sev = tge.add_custom_event_node("ShowTableDish")
bel.set_node_pos(sev, pos(X, Y))
get_id = tge.add_get_member_variable_node("CurrentDishId")
bel.set_node_pos(get_id, pos(X + 250, Y + 120))
eq = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq, pos(X + 500, Y + 120))
connect(out_data(get_id), find_pin(eq, "A", "Input"), "show eqA")
setdef(find_pin(eq, "B", "Input"), "1")
br = tge.add_branch_node(); bel.set_node_pos(br, pos(X + 750, Y))
connect(find_pin(sev, "then", "Output"), find_pin(br, "execute", "Input"), "show->br")
connect(out_data(eq), find_pin(br, "Condition", "Input"), "show cond")

def set_dish_mesh(exec_pin, mesh_path, x, y, tag):
    getm = tge.add_get_member_variable_node("TableDishMesh")
    bel.set_node_pos(getm, pos(x, y + 100))
    sets = tge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
    bel.set_node_pos(sets, pos(x + 250, y))
    connect(exec_pin, find_pin(sets, "execute", "Input"), tag + "ex")
    connect(out_data(getm), find_pin(sets, "self", "Input"), tag + "self")
    setdef(find_pin(sets, "NewMesh", "Input") or find_pin(sets, "StaticMesh", "Input"), mesh_path)
    getm2 = tge.add_get_member_variable_node("TableDishMesh")
    bel.set_node_pos(getm2, pos(x + 500, y + 100))
    show = tge.add_call_function_node("/Script/Engine.SceneComponent:SetVisibility")
    bel.set_node_pos(show, pos(x + 750, y))
    connect(find_pin(sets, "then", "Output"), find_pin(show, "execute", "Input"), tag + "->vis")
    connect(out_data(getm2), find_pin(show, "self", "Input"), tag + "viself")
    setdef(find_pin(show, "bNewVisibility", "Input") or find_pin(show, "NewVisibility", "Input"), "true")
    setdef(find_pin(show, "bPropagateToChildren", "Input"), "false")
    pr = make_print(tge, x + 1050, y, "Table dish ON", dur="0.4", key="RestTableDish")
    connect(find_pin(show, "then", "Output"), find_pin(pr, "execute", "Input"), tag + "p")
    return pr

set_dish_mesh(find_pin(br, "then", "Output"), MESH_SALAD, X + 1000, Y - 40, "sal")
set_dish_mesh(find_pin(br, "else", "Output"), MESH_STEW, X + 1000, Y + 160, "stew")
R["ok"].append("ShowTableDish")

# HideTableDish
hev = tge.add_custom_event_node("HideTableDish")
bel.set_node_pos(hev, pos(X, Y + 500))
getm = tge.add_get_member_variable_node("TableDishMesh")
bel.set_node_pos(getm, pos(X + 300, Y + 600))
hide = tge.add_call_function_node("/Script/Engine.SceneComponent:SetVisibility")
bel.set_node_pos(hide, pos(X + 550, Y + 500))
connect(find_pin(hev, "then", "Output"), find_pin(hide, "execute", "Input"), "hide ex")
connect(out_data(getm), find_pin(hide, "self", "Input"), "hide self")
setdef(find_pin(hide, "bNewVisibility", "Input") or find_pin(hide, "NewVisibility", "Input"), "false")
setdef(find_pin(hide, "bPropagateToChildren", "Input"), "false")
prh = make_print(tge, X + 900, Y + 500, " ", dur="0.1", key="RestTableDish")
connect(find_pin(hide, "then", "Output"), find_pin(prh, "execute", "Input"), "hide p")
R["ok"].append("HideTableDish")

# Wire BeginEat -> ShowTableDish (append if not already)
def already_calls(ge, ev_name, target_title):
    ev = find_custom(ge, ev_name)
    if not ev: return False
    cur = ev; seen = set()
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        if target_title in title(cur) and cur.get_class().get_name() == "K2Node_CallFunction":
            return True
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
    return False

be = find_custom(tge, "BeginEat")
if be and not already_calls(tge, "BeginEat", "ShowTableDish"):
    last, term = linear_last(be)
    call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ShowTableDish")
    bel.set_node_pos(call, pos(2800, 400))
    connect(term, find_pin(call, "execute", "Input"), "BeginEat->Show")
    R["ok"].append("wire_BeginEat")
else:
    log("BeginEat already wired or missing")

cs = find_custom(tge, "ClearSeat")
if cs and not already_calls(tge, "ClearSeat", "HideTableDish"):
    last, term = linear_last(cs)
    call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:HideTableDish")
    bel.set_node_pos(call, pos(3200, 900))
    connect(term, find_pin(call, "execute", "Input"), "ClearSeat->Hide")
    R["ok"].append("wire_ClearSeat")
else:
    log("ClearSeat already wired or missing")

# Mid compile table so call nodes resolve
bel.compile_blueprint(tbp)
R["table_mid"] = str(tbp.get_editor_property("status"))
log("table mid " + R["table_mid"])

# ========== MANAGER ==========
mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ensure_var(mbp, "ServedCount", "int")
ensure_var(mbp, "DayEarned", "real")

# Rebuild bump + summary + reset customs
for nm in ("BumpServedSalad", "BumpServedStew", "PrintDayEndSummary", "ResetDayCounters", MARKER):
    old = find_custom(mge, nm)
    if old:
        mge.remove_nodes(walk_kill_from(mge, old)); log("removed " + nm)

def build_bump(name, amount, y):
    ev = mge.add_custom_event_node(name)
    bel.set_node_pos(ev, pos(-2000, y))
    # DayEarned += amount
    get_d = mge.add_get_member_variable_node("DayEarned")
    bel.set_node_pos(get_d, pos(-1700, y + 100))
    add_d = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
    if add_d is None:
        add_d = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
    bel.set_node_pos(add_d, pos(-1450, y + 100))
    connect(out_data(get_d), find_pin(add_d, "A", "Input"), name + " dA")
    setdef(find_pin(add_d, "B", "Input"), str(float(amount)))
    set_d = mge.add_set_member_variable_node("DayEarned")
    bel.set_node_pos(set_d, pos(-1200, y))
    connect(find_pin(ev, "then", "Output"), find_pin(set_d, "execute", "Input"), name + "->setD")
    connect(out_data(add_d), find_pin(set_d, "DayEarned", "Input"), name + " setD")
    # ServedCount += 1
    get_s = mge.add_get_member_variable_node("ServedCount")
    bel.set_node_pos(get_s, pos(-950, y + 100))
    add_s = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_IntInt")
    bel.set_node_pos(add_s, pos(-700, y + 100))
    connect(out_data(get_s), find_pin(add_s, "A", "Input"), name + " sA")
    setdef(find_pin(add_s, "B", "Input"), "1")
    set_s = mge.add_set_member_variable_node("ServedCount")
    bel.set_node_pos(set_s, pos(-450, y))
    connect(find_pin(set_d, "then", "Output"), find_pin(set_s, "execute", "Input"), name + "->setS")
    connect(out_data(add_s), find_pin(set_s, "ServedCount", "Input"), name + " setS")
    pr = make_print(mge, -150, y, "Served+1", dur="0.5", key="RestServed")
    connect(find_pin(set_s, "then", "Output"), find_pin(pr, "execute", "Input"), name + "p")
    R["ok"].append(name)
    return ev

build_bump("BumpServedSalad", 15.0, -3600)
build_bump("BumpServedStew", 28.0, -3200)

# ResetDayCounters
rev = mge.add_custom_event_node("ResetDayCounters")
bel.set_node_pos(rev, pos(-2000, -2800))
set_s0 = mge.add_set_member_variable_node("ServedCount")
bel.set_node_pos(set_s0, pos(-1600, -2800))
connect(find_pin(rev, "then", "Output"), find_pin(set_s0, "execute", "Input"), "rst->S")
setdef(find_pin(set_s0, "ServedCount", "Input"), "0")
set_d0 = mge.add_set_member_variable_node("DayEarned")
bel.set_node_pos(set_d0, pos(-1250, -2800))
connect(find_pin(set_s0, "then", "Output"), find_pin(set_d0, "execute", "Input"), "rst->D")
setdef(find_pin(set_d0, "DayEarned", "Input"), "0.0")
pr0 = make_print(mge, -900, -2800, "Day counters reset", dur="1.0", key="RestDayEnd")
connect(find_pin(set_d0, "then", "Output"), find_pin(pr0, "execute", "Input"), "rst p")
R["ok"].append("ResetDayCounters")

# PrintDayEndSummary: build string
pev = mge.add_custom_event_node("PrintDayEndSummary")
bel.set_node_pos(pev, pos(-2000, -2400))
# Conv DayEarned
get_de = mge.add_get_member_variable_node("DayEarned")
bel.set_node_pos(get_de, pos(-1700, -2200))
cde = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
if cde is None:
    cde = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
bel.set_node_pos(cde, pos(-1450, -2200))
connect(out_data(get_de), find_pin(cde, "InDouble", "Input") or find_pin(cde, "InFloat", "Input") or find_pin(cde, "Double", "Input") or find_pin(cde, "In", "Input"), "de conv")
get_sc = mge.add_get_member_variable_node("ServedCount")
bel.set_node_pos(get_sc, pos(-1700, -2050))
csc = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
bel.set_node_pos(csc, pos(-1450, -2050))
connect(out_data(get_sc), find_pin(csc, "InInt", "Input") or find_pin(csc, "Int", "Input") or find_pin(csc, "In", "Input"), "sc conv")

# Concat chain: prefix + earned + mid + count + suffix
def concat(ge, a_pin, b_pin_or_lit, x, y, tag, lit=None):
    n = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(n, pos(x, y))
    if a_pin: connect(a_pin, find_pin(n, "A", "Input"), tag + "A")
    if b_pin_or_lit is not None and lit is None:
        connect(b_pin_or_lit, find_pin(n, "B", "Input"), tag + "B")
    if lit is not None:
        setdef(find_pin(n, "B" if a_pin else "A", "Input") if a_pin else find_pin(n, "A", "Input"), lit)
        if a_pin is None:
            setdef(find_pin(n, "A", "Input"), lit)
    return n

# 「打烊 | 今日餐厅营收 $」 + earned + 「 | 服务 」 + count + 「 桌」
c1 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
bel.set_node_pos(c1, pos(-1150, -2300))
setdef(find_pin(c1, "A", "Input"), u"打烊 | 今日餐厅营收 $")
connect(out_data(cde), find_pin(c1, "B", "Input"), "c1B")

c2 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
bel.set_node_pos(c2, pos(-850, -2300))
connect(out_data(c1), find_pin(c2, "A", "Input"), "c2A")
setdef(find_pin(c2, "B", "Input"), u" | 服务 ")

c3 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
bel.set_node_pos(c3, pos(-550, -2300))
connect(out_data(c2), find_pin(c3, "A", "Input"), "c3A")
connect(out_data(csc), find_pin(c3, "B", "Input"), "c3B")

c4 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
bel.set_node_pos(c4, pos(-250, -2300))
connect(out_data(c3), find_pin(c4, "A", "Input"), "c4A")
setdef(find_pin(c4, "B", "Input"), u" 桌")

pr_sum = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
bel.set_node_pos(pr_sum, pos(50, -2400))
connect(find_pin(pev, "then", "Output"), find_pin(pr_sum, "execute", "Input"), "sum ex")
connect(out_data(c4), find_pin(pr_sum, "InString", "Input"), "sum str")
setdef(find_pin(pr_sum, "Duration", "Input"), "8.0")
setdef(find_pin(pr_sum, "Key", "Input"), "RestDayEnd")
# yellow
tc = find_pin(pr_sum, "TextColor", "Input")
if tc: setdef(tc, "(R=1.000000,G=0.920000,B=0.200000,A=1.000000)")
R["ok"].append("PrintDayEndSummary")

# Marker event (empty) for idempotency detection
mk = mge.add_custom_event_node(MARKER)
bel.set_node_pos(mk, pos(-2000, -4000))
prmk = make_print(mge, -1600, -4000, "DishDayEnd_v1", dur="0.01", key="RestMarker")
connect(find_pin(mk, "then", "Output"), find_pin(prmk, "execute", "Input"), "mk")

# Mid compile manager so customs exist as callables
bel.compile_blueprint(mbp)
R["mgr_mid"] = str(mbp.get_editor_property("status"))
log("mgr mid " + R["mgr_mid"])

# --- Wire bumps into pay chains (after Set RestaurantMoney, before Print if possible) ---
def wire_after_set_money(ev_name, bump_name, y):
    ev = find_custom(mge, ev_name)
    if not ev:
        R["errors"].append("missing " + ev_name); return
    # if already has bump, skip
    cur = ev; seen = set()
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        if bump_name in title(cur):
            log(ev_name + " already has " + bump_name); return
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
    # Find Set RestaurantMoney in chain; insert bump after it
    cur = ev; prev = None
    while cur:
        if title(cur) == "Set RestaurantMoney":
            tp = find_pin(cur, "then", "Output")
            old_targets = [c for c in (tp.list_connected_pins() or [])] if tp else []
            try:
                if tp: tp.break_pin_links()
            except Exception: pass
            call = mge.add_call_function_node(
                "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:" + bump_name)
            bel.set_node_pos(call, pos(900, y))
            connect(tp, find_pin(call, "execute", "Input"), ev_name + "->bump")
            # reattach old (Print / GrantMoney)
            for ot in old_targets:
                connect(find_pin(call, "then", "Output"), ot, ev_name + "bump->old")
            R["ok"].append(ev_name + "->" + bump_name)
            return
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
    R["errors"].append("no Set RestaurantMoney in " + ev_name)

wire_after_set_money("OnGuestPaidSalad", "BumpServedSalad", 2100)
wire_after_set_money("OnGuestPaidStew", "BumpServedStew", 2400)

# --- Wire PrintDayEndSummary into close paths (Set bIsOpenBusiness -> ApplySignClosed) ---
# Insert between ApplySignClosed and its then targets, OR call summary first then ApplySignClosed.
# Safer: after ApplySignClosed call, before ClearGuests — append PrintDayEndSummary right after ApplySignClosed returns.
# Actually ApplySignClosed is a custom event CALL. Find CallFunction ApplySignClosed whose then goes to PrintString/ClearGuests.

def wire_close_summary():
    count = 0
    for n in list(mge.list_all_nodes()):
        if title(n) != "ApplySignClosed" or n.get_class().get_name() != "K2Node_CallFunction":
            continue
        # Check predecessor is Set bIsOpenBusiness
        preds = []
        for p in bel.list_all_pins(n):
            if "INPUT" in str(p.get_pin_direction()) and "exec" in str(p.get_pin_type_display_string()).lower():
                for c in p.list_connected_pins() or []:
                    preds.append(title(c.get_owning_node()))
        if not any("bIsOpenBusiness" in p for p in preds) and "Set bIsOpenBusiness" not in preds:
            # still allow if then chain has ClearGuests
            pass
        tp = find_pin(n, "then", "Output")
        if not tp: continue
        # if already PrintDayEndSummary downstream, skip
        nxts = [c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if any("PrintDayEndSummary" in title(x) for x in nxts):
            log("close already has summary"); continue
        # Also skip if this ApplySignClosed is not on a close path (preds empty weird)
        # Insert: break then, summary, then old
        old = list(tp.list_connected_pins() or [])
        try: tp.break_pin_links()
        except Exception: pass
        call = mge.add_call_function_node(
            "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:PrintDayEndSummary")
        bel.set_node_pos(call, pos(bel.get_node_pos(n).x + 350, bel.get_node_pos(n).y + 80 + count * 40))
        connect(tp, find_pin(call, "execute", "Input"), "close->sum" + str(count))
        for ot in old:
            connect(find_pin(call, "then", "Output"), ot, "sum->old" + str(count))
        count += 1
        R["ok"].append("close_summary_" + str(count))
    if count == 0:
        R["errors"].append("no ApplySignClosed call to wire")
    log("wired close summaries: " + str(count))

wire_close_summary()

# --- Wire ResetDayCounters into open path (after ApplySignOpen) ---
def wire_open_reset():
    count = 0
    for n in list(mge.list_all_nodes()):
        if title(n) != "ApplySignOpen" or n.get_class().get_name() != "K2Node_CallFunction":
            continue
        tp = find_pin(n, "then", "Output")
        if not tp: continue
        nxts = [c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if any("ResetDayCounters" in title(x) for x in nxts):
            log("open already reset"); continue
        old = list(tp.list_connected_pins() or [])
        try: tp.break_pin_links()
        except Exception: pass
        call = mge.add_call_function_node(
            "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ResetDayCounters")
        bel.set_node_pos(call, pos(bel.get_node_pos(n).x + 350, bel.get_node_pos(n).y - 60))
        connect(tp, find_pin(call, "execute", "Input"), "open->rst")
        for ot in old:
            connect(find_pin(call, "then", "Output"), ot, "rst->old")
        count += 1
        R["ok"].append("open_reset")
    log("wired open resets: " + str(count))

wire_open_reset()

# Final compile + save
bel.compile_blueprint(tbp)
bel.compile_blueprint(mbp)
R["table_final"] = str(tbp.get_editor_property("status"))
R["mgr_final"] = str(mbp.get_editor_property("status"))
log("table " + R["table_final"])
log("mgr " + R["mgr_final"])

errs = []
for label, ge in (("tbl", tge), ("mgr", mge)):
    for n in ge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                errs.append(label + ":" + title(n) + ":" + str(em)[:120])
        except Exception:
            pass
R["compile_errs"] = errs
for e in errs[:20]:
    log("ERR " + e)

if "ERROR" not in R["table_final"]:
    eas.save_asset(TBL)
if "ERROR" not in R["mgr_final"]:
    eas.save_asset(MGR)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# verify chains
def walk_titles(ge, name, limit=20):
    ev = find_custom(ge, name)
    if not ev: return None
    out = []; cur = ev
    for _ in range(limit):
        out.append(title(cur))
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
    return out

R["v_BeginEat"] = walk_titles(tge, "BeginEat")
R["v_ClearSeat"] = walk_titles(tge, "ClearSeat")
R["v_pay_salad"] = walk_titles(mge, "OnGuestPaidSalad")
R["v_pay_stew"] = walk_titles(mge, "OnGuestPaidStew")
R["v_show"] = walk_titles(tge, "ShowTableDish")
R["v_hide"] = walk_titles(tge, "HideTableDish")
R["v_sum"] = walk_titles(mge, "PrintDayEndSummary")
R["has_marker"] = find_custom(mge, MARKER) is not None

open(r"E:\UE\FarmSim25D\Saved\rest_dish_dayend.json", "w", encoding="utf-8").write(
    json.dumps(R, indent=2, ensure_ascii=False, default=str))
print(json.dumps(R, indent=2, ensure_ascii=False, default=str)[:12000])
