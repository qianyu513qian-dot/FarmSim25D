# -*- coding: utf-8 -*-
"""Knife2 wire: E surgical + open/close clock + guest spawn. No cast; direct self wires."""
import unreal, json, shutil, os

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
REPORT = {"steps": [], "errors": [], "ok": {}, "actors_before": 0, "actors_after": 0}

def log(m):
    unreal.log("[K2W] " + str(m))
    REPORT["steps"].append(str(m))

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

def out_pin(node, substr=""):
    if not node:
        return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if "OUTPUT" not in str(p.get_pin_direction()):
            continue
        if not substr or substr in str(p.get_pin_name()).lower():
            if str(p.get_pin_name()).lower() in ("outputdelegate",):
                continue
            return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    return ok

def setdef(pin, val):
    if not pin:
        return
    for fn in ("set_pin_value", "set_default_value"):
        try:
            getattr(pin, fn)(str(val))
            return
        except Exception:
            pass

def make_print(ge, x, y, text, dur="2.5"):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    setdef(find_pin(pr, "TextColor", "Input"), "(R=0.000000,G=0.800000,B=1.000000,A=1.000000)")
    return pr

def ensure_var(bp, name, type_name="bool"):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    t = bel.get_basic_type_by_name(type_name)
    if name not in names:
        if t:
            bel.add_member_variable(bp, name, t)
        else:
            # graph editor fallback
            ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
            ge.add_member_variable(name)
            if t:
                bel.change_member_variable_type(bp, name, t)
        log("added var " + name)
    elif t:
        try:
            bel.change_member_variable_type(bp, name, t)
        except Exception:
            pass
    return True

def find_custom(ge, title):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and bel.get_node_title(n) == title:
            return n
    return None

def find_event(ge, title_substr):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_Event" and title_substr in bel.get_node_title(n):
            return n
    return None

def purge_except(ge, keep_titles, keep_classes=("K2Node_Event", "K2Node_CustomEvent")):
    kill = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        c = n.get_class().get_name()
        if c in keep_classes and any(k in t for k in keep_titles):
            # break outgoing exec so we can rewire
            then = find_pin(n, "then", "Output")
            if then:
                then.break_pin_links()
            continue
        if c == "K2Node_Event" and ("BeginPlay" in t or "ActorBeginOverlap" in t):
            continue
        kill.append(n)
    if kill:
        ge.remove_nodes(kill)
        log("purged {} nodes".format(len(kill)))

def add_foreach(ge, x, y):
    fe = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    if fe is None:
        fe = ge.create_node_from_name("ForEachLoop", unreal.Vector2D(x, y), [])
    bel.set_node_pos(fe, pos(x, y))
    return fe

def cmp_ge(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
    bel.set_node_pos(n, pos(x, y))
    return n

def cmp_lt_num(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
    if n is None:
        n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    bel.set_node_pos(n, pos(x, y))
    return n

def add_d(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
    if n is None:
        n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
    bel.set_node_pos(n, pos(x, y))
    return n

# ---------------- TABLE: TrySeat / ClearSeat ----------------
def wire_table():
    bp = unreal.EditorAssetLibrary.load_asset(DIR + "/BP_RestaurantTable")
    ensure_var(bp, "bOccupied", "bool")
    ensure_var(bp, "bHasOrder", "bool")
    ensure_var(bp, "CurrentOrder", "string")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    # remove old TrySeat/ClearSeat bodies if exist
    for title in ("TrySeat", "ClearSeat"):
        ev = find_custom(ge, title)
        if ev:
            # remove nodes solely in its chain is hard; remove custom and recreate
            pass
    # purge custom events TrySeat/ClearSeat and dangling by removing all non-BeginPlay/Overlap
    keep = []
    kill = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        c = n.get_class().get_name()
        if c == "K2Node_Event" and ("BeginPlay" in t or "ActorBeginOverlap" in t or "Tick" in t):
            then = find_pin(n, "then", "Output")
            if then:
                then.break_pin_links()
            keep.append(t)
            continue
        if c == "K2Node_CustomEvent" and t in ("TrySeat", "ClearSeat"):
            then = find_pin(n, "then", "Output")
            if then:
                then.break_pin_links()
            # delete and recreate clean
            kill.append(n)
            continue
        if c == "K2Node_CallParentFunction":
            continue
        kill.append(n)
    if kill:
        ge.remove_nodes(kill)
        log("table purged {}".format(len(kill)))

    # TrySeat
    try_ev = ge.add_custom_event_node("TrySeat")
    bel.set_node_pos(try_ev, pos(0, 400))
    get_occ = ge.add_get_member_variable_node("bOccupied")
    bel.set_node_pos(get_occ, pos(200, 480))
    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(450, 400))
    connect(find_pin(try_ev, "then", "Output"), find_pin(br, "execute", "Input"), "try->br")
    connect(find_pin(get_occ, "bOccupied", "Output") or out_pin(get_occ), find_pin(br, "Condition", "Input"), "occ?")
    # else free: set occupied
    set_occ = ge.add_set_member_variable_node("bOccupied")
    bel.set_node_pos(set_occ, pos(750, 500))
    connect(find_pin(br, "else", "Output"), find_pin(set_occ, "execute", "Input"), "free")
    setdef(find_pin(set_occ, "bOccupied", "Input"), "true")
    # random order
    rb = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:RandomBool")
    bel.set_node_pos(rb, pos(750, 650))
    sel = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:SelectString")
    bel.set_node_pos(sel, pos(1000, 650))
    setdef(find_pin(sel, "A", "Input"), "TomatoSalad")
    setdef(find_pin(sel, "B", "Input"), "Stew")
    connect(out_pin(rb, "return"), find_pin(sel, "bPickA", "Input") or find_pin(sel, "PickA", "Input"), "pick")
    set_ord = ge.add_set_member_variable_node("CurrentOrder")
    bel.set_node_pos(set_ord, pos(1300, 500))
    connect(find_pin(set_occ, "then", "Output"), find_pin(set_ord, "execute", "Input"), "->ord")
    connect(out_pin(sel, "return"), find_pin(set_ord, "CurrentOrder", "Input"), "ordval")
    set_ho = ge.add_set_member_variable_node("bHasOrder")
    bel.set_node_pos(set_ho, pos(1600, 500))
    connect(find_pin(set_ord, "then", "Output"), find_pin(set_ho, "execute", "Input"), "->ho")
    setdef(find_pin(set_ho, "bHasOrder", "Input"), "true")
    # print label + order
    glab = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
    # better GetActorLabel
    glab = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetObjectName")
    try:
        glab2 = ge.add_call_function_node("/Script/Engine.Actor:GetActorLabel")
    except Exception:
        glab2 = None
    if glab2:
        glab = glab2
    bel.set_node_pos(glab, pos(1600, 650))
    app = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    if app is None:
        app = ge.create_node_from_name("Append", unreal.Vector2D(1900, 650), [])
    bel.set_node_pos(app, pos(1900, 650))
    # Append may be commutative with A/B pins
    setdef(find_pin(app, "A", "Input"), "Restaurant GUEST seated @ ")
    # need two appends for order
    app2 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    if app2 is None:
        app2 = ge.create_node_from_name("Append", unreal.Vector2D(2200, 650), [])
    bel.set_node_pos(app2, pos(2200, 650))
    connect(out_pin(glab, "return") or find_pin(glab, "ReturnValue", "Output"), find_pin(app, "B", "Input"), "lab")
    connect(out_pin(app, "return") or find_pin(app, "ReturnValue", "Output"), find_pin(app2, "A", "Input"), "a2")
    # mid: " order="
    # Use Append with order: simpler fixed print via two prints or one Append with Select already known
    # Wire CurrentOrder get into B of app2 with prefix via another append
    app3 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    if app3 is None:
        app3 = ge.create_node_from_name("Append", unreal.Vector2D(2100, 720), [])
    bel.set_node_pos(app3, pos(2050, 720))
    setdef(find_pin(app3, "A", "Input"), " order=")
    get_ord = ge.add_get_member_variable_node("CurrentOrder")
    bel.set_node_pos(get_ord, pos(1800, 780))
    connect(find_pin(get_ord, "CurrentOrder", "Output") or out_pin(get_ord), find_pin(app3, "B", "Input"), "ov")
    connect(out_pin(app3, "return") or find_pin(app3, "ReturnValue", "Output"), find_pin(app2, "B", "Input"), "b2")
    pr = make_print(ge, 2500, 500, "Restaurant GUEST")
    connect(find_pin(set_ho, "then", "Output"), find_pin(pr, "execute", "Input"), "->pr")
    connect(out_pin(app2, "return") or find_pin(app2, "ReturnValue", "Output"), find_pin(pr, "InString", "Input"), "msg")

    # ClearSeat
    clr = ge.add_custom_event_node("ClearSeat")
    bel.set_node_pos(clr, pos(0, 900))
    set_f = ge.add_set_member_variable_node("bOccupied")
    bel.set_node_pos(set_f, pos(300, 900))
    connect(find_pin(clr, "then", "Output"), find_pin(set_f, "execute", "Input"), "clr")
    setdef(find_pin(set_f, "bOccupied", "Input"), "false")
    set_o2 = ge.add_set_member_variable_node("CurrentOrder")
    bel.set_node_pos(set_o2, pos(600, 900))
    connect(find_pin(set_f, "then", "Output"), find_pin(set_o2, "execute", "Input"), "->o")
    setdef(find_pin(set_o2, "CurrentOrder", "Input"), "")
    set_h2 = ge.add_set_member_variable_node("bHasOrder")
    bel.set_node_pos(set_h2, pos(900, 900))
    connect(find_pin(set_o2, "then", "Output"), find_pin(set_h2, "execute", "Input"), "->h")
    setdef(find_pin(set_h2, "bHasOrder", "Input"), "false")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantTable")
    REPORT["ok"]["table"] = True
    log("table TrySeat/ClearSeat done")

# ---------------- MANAGER ----------------
def wire_manager():
    bp = unreal.EditorAssetLibrary.load_asset(DIR + "/BP_RestaurantManager")
    ensure_var(bp, "bIsOpenBusiness", "bool")
    ensure_var(bp, "bEHandled", "bool")
    ensure_var(bp, "GuestTimer", "real")
    ensure_var(bp, "GuestInterval", "real")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    # Purge everything except BeginPlay/Overlap; recreate customs + Tick
    kill = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        c = n.get_class().get_name()
        if c == "K2Node_Event" and ("BeginPlay" in t or "ActorBeginOverlap" in t):
            then = find_pin(n, "then", "Output")
            if then:
                then.break_pin_links()
            continue
        kill.append(n)
    if kill:
        ge.remove_nodes(kill)
        log("manager purged {}".format(len(kill)))

    # --- HandlePlayerE ---
    he = ge.add_custom_event_node("HandlePlayerE")
    bel.set_node_pos(he, pos(0, 0))
    set_f = ge.add_set_member_variable_node("bEHandled")
    bel.set_node_pos(set_f, pos(250, 0))
    connect(find_pin(he, "then", "Output"), find_pin(set_f, "execute", "Input"), "he->f")
    setdef(find_pin(set_f, "bEHandled", "Input"), "false")

    pawn = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(pawn, pos(250, 120))
    setdef(find_pin(pawn, "PlayerIndex", "Input") or find_pin(pawn, "Index", "Input"), "0")
    ploc = ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
    bel.set_node_pos(ploc, pos(500, 120))
    connect(out_pin(pawn, "return"), find_pin(ploc, "self", "Input"), "pawn->loc")

    gaw = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
    bel.set_node_pos(gaw, pos(500, 0))
    connect(find_pin(set_f, "then", "Output"), find_pin(gaw, "execute", "Input"), "->gaw")
    setdef(find_pin(gaw, "Tag", "Input"), "RestInteract")

    fe = add_foreach(ge, 800, 0)
    connect(find_pin(gaw, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "->fe")
    connect(find_pin(gaw, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "arr")

    aloc = ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
    bel.set_node_pos(aloc, pos(1100, 80))
    connect(find_pin(fe, "Array Element", "Output") or find_pin(fe, "Element", "Output"), find_pin(aloc, "self", "Input"), "el->loc")
    dist = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
    bel.set_node_pos(dist, pos(1350, 80))
    connect(out_pin(ploc, "return"), find_pin(dist, "V1", "Input") or find_pin(dist, "A", "Input"), "v1")
    connect(out_pin(aloc, "return"), find_pin(dist, "V2", "Input") or find_pin(dist, "B", "Input"), "v2")
    lt = cmp_lt_num(ge, 1600, 80)
    connect(out_pin(dist, "return"), find_pin(lt, "A", "Input"), "d")
    setdef(find_pin(lt, "B", "Input"), "280.0")
    brd = ge.add_branch_node()
    bel.set_node_pos(brd, pos(1850, 0))
    connect(find_pin(fe, "LoopBody", "Output") or find_pin(fe, "Loop Body", "Output"), find_pin(brd, "execute", "Input"), "body")
    connect(out_pin(lt, "return"), find_pin(brd, "Condition", "Input"), "near?")

    set_t = ge.add_set_member_variable_node("bEHandled")
    bel.set_node_pos(set_t, pos(2100, 0))
    connect(find_pin(brd, "then", "Output"), find_pin(set_t, "execute", "Input"), "hit")
    setdef(find_pin(set_t, "bEHandled", "Input"), "true")

    glab = ge.add_call_function_node("/Script/Engine.Actor:GetActorLabel")
    bel.set_node_pos(glab, pos(2100, 120))
    connect(find_pin(fe, "Array Element", "Output") or find_pin(fe, "Element", "Output"), find_pin(glab, "self", "Input"), "el->lab")
    contains = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains")
    bel.set_node_pos(contains, pos(2350, 120))
    connect(out_pin(glab, "return"), find_pin(contains, "SearchIn", "Input"), "sin")
    setdef(find_pin(contains, "Substring", "Input"), "OpenSign")
    brs = ge.add_branch_node()
    bel.set_node_pos(brs, pos(2600, 0))
    connect(find_pin(set_t, "then", "Output"), find_pin(brs, "execute", "Input"), "->sign?")
    connect(out_pin(contains, "return"), find_pin(brs, "Condition", "Input"), "sign?")

    # non-sign print
    app = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    if app is None:
        app = ge.create_node_from_name("Append", unreal.Vector2D(2900, 200), [])
    bel.set_node_pos(app, pos(2900, 200))
    setdef(find_pin(app, "A", "Input"), "Restaurant E -> ")
    connect(out_pin(glab, "return"), find_pin(app, "B", "Input"), "lab")
    pr_o = make_print(ge, 3200, 200, "Restaurant E")
    connect(find_pin(brs, "else", "Output"), find_pin(pr_o, "execute", "Input"), "other")
    connect(out_pin(app, "return") or find_pin(app, "ReturnValue", "Output"), find_pin(pr_o, "InString", "Input"), "omsg")

    # OpenSign path with clock (NO cast)
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(2900, -50))
    connect(find_pin(brs, "then", "Output"), find_pin(gao, "execute", "Input"), "sign->clock")
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"), "/Script/FarmSim25D.FarmClock")
    get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(3200, 40))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), "carr")
    setdef(find_pin(get0, "Index", "Input"), "0")
    gdm = ge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
    bel.set_node_pos(gdm, pos(3450, 40))
    item = find_pin(get0, "Item", "Output")
    connect(item, find_pin(gdm, "self", "Input"), "fc->gdm")

    # minutes >= 1020?
    geq = cmp_ge(ge, 3700, 40)
    connect(out_pin(gdm, "return"), find_pin(geq, "A", "Input"), "m")
    setdef(find_pin(geq, "B", "Input"), "1020")
    br_t = ge.add_branch_node()
    bel.set_node_pos(br_t, pos(3950, -50))
    connect(find_pin(gao, "then", "Output"), find_pin(br_t, "execute", "Input"), "->time")
    connect(out_pin(geq, "return"), find_pin(br_t, "Condition", "Input"), ">=17?")
    pr_early = make_print(ge, 4250, 80, "Restaurant: too early (<17:00), cannot open")
    connect(find_pin(br_t, "else", "Output"), find_pin(pr_early, "execute", "Input"), "early")

    # already open?
    get_open = ge.add_get_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(get_open, pos(4250, -20))
    br_o = ge.add_branch_node()
    bel.set_node_pos(br_o, pos(4500, -50))
    connect(find_pin(br_t, "then", "Output"), find_pin(br_o, "execute", "Input"), "->open?")
    connect(find_pin(get_open, "bIsOpenBusiness", "Output") or out_pin(get_open), find_pin(br_o, "Condition", "Input"), "open?")

    # close early
    set_c = ge.add_set_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(set_c, pos(4800, -150))
    connect(find_pin(br_o, "then", "Output"), find_pin(set_c, "execute", "Input"), "close")
    setdef(find_pin(set_c, "bIsOpenBusiness", "Input"), "false")
    pr_c = make_print(ge, 5100, -150, "Restaurant: CLOSED (early). Seating stopped.")
    connect(find_pin(set_c, "then", "Output"), find_pin(pr_c, "execute", "Input"), "prc")
    call_cg = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearGuests")
    bel.set_node_pos(call_cg, pos(5400, -150))
    connect(find_pin(pr_c, "then", "Output"), find_pin(call_cg, "execute", "Input"), "->clear")

    # open: check not past 23
    geq23 = cmp_ge(ge, 4800, 40)
    connect(out_pin(gdm, "return"), find_pin(geq23, "A", "Input"), "m23")
    setdef(find_pin(geq23, "B", "Input"), "1380")
    br_late = ge.add_branch_node()
    bel.set_node_pos(br_late, pos(5100, 40))
    connect(find_pin(br_o, "else", "Output"), find_pin(br_late, "execute", "Input"), "->late?")
    connect(out_pin(geq23, "return"), find_pin(br_late, "Condition", "Input"), ">=23?")
    pr_late = make_print(ge, 5400, 0, "Restaurant: too late (>=23:00), cannot open")
    connect(find_pin(br_late, "then", "Output"), find_pin(pr_late, "execute", "Input"), "late")
    set_op = ge.add_set_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(set_op, pos(5400, 120))
    connect(find_pin(br_late, "else", "Output"), find_pin(set_op, "execute", "Input"), "open!")
    setdef(find_pin(set_op, "bIsOpenBusiness", "Input"), "true")
    set_tm = ge.add_set_member_variable_node("GuestTimer")
    bel.set_node_pos(set_tm, pos(5700, 120))
    connect(find_pin(set_op, "then", "Output"), find_pin(set_tm, "execute", "Input"), "rst")
    setdef(find_pin(set_tm, "GuestTimer", "Input"), "0.0")
    pr_op = make_print(ge, 6000, 120, "Restaurant: OPEN for business. Guests incoming.")
    connect(find_pin(set_tm, "then", "Output"), find_pin(pr_op, "execute", "Input"), "pro")

    # --- ClearGuests ---
    cg = ge.add_custom_event_node("ClearGuests")
    bel.set_node_pos(cg, pos(0, 700))
    pr_cg = make_print(ge, 250, 700, "Restaurant: clearing guests / freeing tables")
    connect(find_pin(cg, "then", "Output"), find_pin(pr_cg, "execute", "Input"), "cg")
    gao_t = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao_t, pos(550, 700))
    connect(find_pin(pr_cg, "then", "Output"), find_pin(gao_t, "execute", "Input"), "->tbl")
    setdef(find_pin(gao_t, "ActorClass", "Input") or find_pin(gao_t, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
    fe_c = add_foreach(ge, 850, 700)
    connect(find_pin(gao_t, "then", "Output"), find_pin(fe_c, "Exec", "Input") or find_pin(fe_c, "execute", "Input"), "fec")
    connect(find_pin(gao_t, "OutActors", "Output"), find_pin(fe_c, "Array", "Input"), "tarr")
    call_cs = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:ClearSeat")
    bel.set_node_pos(call_cs, pos(1150, 700))
    connect(find_pin(fe_c, "LoopBody", "Output") or find_pin(fe_c, "Loop Body", "Output"), find_pin(call_cs, "execute", "Input"), "->cs")
    connect(find_pin(fe_c, "Array Element", "Output") or find_pin(fe_c, "Element", "Output"), find_pin(call_cs, "self", "Input"), "selfcs")

    # --- SeatGuest ---
    sg = ge.add_custom_event_node("SeatGuest")
    bel.set_node_pos(sg, pos(0, 1100))
    get_open2 = ge.add_get_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(get_open2, pos(200, 1180))
    br_sg = ge.add_branch_node()
    bel.set_node_pos(br_sg, pos(450, 1100))
    connect(find_pin(sg, "then", "Output"), find_pin(br_sg, "execute", "Input"), "sg")
    connect(find_pin(get_open2, "bIsOpenBusiness", "Output") or out_pin(get_open2), find_pin(br_sg, "Condition", "Input"), "open?")
    gao_s = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao_s, pos(750, 1100))
    connect(find_pin(br_sg, "then", "Output"), find_pin(gao_s, "execute", "Input"), "->s")
    setdef(find_pin(gao_s, "ActorClass", "Input") or find_pin(gao_s, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
    rnd = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:RandomIntegerInRange")
    bel.set_node_pos(rnd, pos(1000, 1220))
    setdef(find_pin(rnd, "Min", "Input"), "0")
    setdef(find_pin(rnd, "Max", "Input"), "1")
    geti = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(geti, pos(1250, 1180))
    connect(find_pin(gao_s, "OutActors", "Output"), find_pin(geti, "TargetArray", "Input"), "sarr")
    connect(out_pin(rnd, "return"), find_pin(geti, "Index", "Input"), "idx")
    call_ts = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:TrySeat")
    bel.set_node_pos(call_ts, pos(1550, 1100))
    connect(find_pin(gao_s, "then", "Output"), find_pin(call_ts, "execute", "Input"), "->ts")
    connect(find_pin(geti, "Item", "Output"), find_pin(call_ts, "self", "Input"), "selfts")

    # --- Tick: force close + guest timer ---
    tick = ge.add_custom_event_node("Tick")  # wrong - need Event Tick
    # remove mistaken custom
    ge.remove_nodes([tick])
    tick = find_event(ge, "Tick")
    if tick is None:
        # try create
        try:
            tick = ge.create_node_from_name("Event Tick", unreal.Vector2D(0, 1500), [])
        except Exception as e:
            log("no tick " + str(e))
    if tick is None:
        REPORT["errors"].append("no Event Tick")
    else:
        bel.set_node_pos(tick, pos(0, 1500))
        then_t = find_pin(tick, "then", "Output")
        if then_t:
            then_t.break_pin_links()
        gao_fc = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
        bel.set_node_pos(gao_fc, pos(300, 1500))
        connect(then_t, find_pin(gao_fc, "execute", "Input"), "tick->fc")
        setdef(find_pin(gao_fc, "ActorClass", "Input") or find_pin(gao_fc, "Class", "Input"), "/Script/FarmSim25D.FarmClock")
        getfc = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
        bel.set_node_pos(getfc, pos(600, 1580))
        connect(find_pin(gao_fc, "OutActors", "Output"), find_pin(getfc, "TargetArray", "Input"), "farr")
        setdef(find_pin(getfc, "Index", "Input"), "0")
        gdm2 = ge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
        bel.set_node_pos(gdm2, pos(850, 1580))
        connect(find_pin(getfc, "Item", "Output"), find_pin(gdm2, "self", "Input"), "gdm2")
        geq_t = cmp_ge(ge, 1100, 1580)
        connect(out_pin(gdm2, "return"), find_pin(geq_t, "A", "Input"), "m")
        setdef(find_pin(geq_t, "B", "Input"), "1380")
        br_23 = ge.add_branch_node()
        bel.set_node_pos(br_23, pos(1350, 1500))
        connect(find_pin(gao_fc, "then", "Output"), find_pin(br_23, "execute", "Input"), "->23")
        connect(out_pin(geq_t, "return"), find_pin(br_23, "Condition", "Input"), "23?")
        get_ob = ge.add_get_member_variable_node("bIsOpenBusiness")
        bel.set_node_pos(get_ob, pos(1350, 1620))
        br_ob = ge.add_branch_node()
        bel.set_node_pos(br_ob, pos(1650, 1500))
        connect(find_pin(br_23, "then", "Output"), find_pin(br_ob, "execute", "Input"), "->ob")
        connect(find_pin(get_ob, "bIsOpenBusiness", "Output") or out_pin(get_ob), find_pin(br_ob, "Condition", "Input"), "ob?")
        set_cl = ge.add_set_member_variable_node("bIsOpenBusiness")
        bel.set_node_pos(set_cl, pos(1950, 1450))
        connect(find_pin(br_ob, "then", "Output"), find_pin(set_cl, "execute", "Input"), "forceclose")
        setdef(find_pin(set_cl, "bIsOpenBusiness", "Input"), "false")
        pr_fc = make_print(ge, 2250, 1450, "Restaurant: AUTO CLOSE at 23:00")
        connect(find_pin(set_cl, "then", "Output"), find_pin(pr_fc, "execute", "Input"), "prfc")
        call_cg2 = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearGuests")
        bel.set_node_pos(call_cg2, pos(2550, 1450))
        connect(find_pin(pr_fc, "then", "Output"), find_pin(call_cg2, "execute", "Input"), "cg2")

        # guest timer path from both else of 23 and else of ob, and also when <23
        # Use Sequence from tick after clock fetch: always run timer check
        # Simpler: from br_23.else and br_ob.else both go to timer; also from br_23.else
        get_ob3 = ge.add_get_member_variable_node("bIsOpenBusiness")
        bel.set_node_pos(get_ob3, pos(1350, 1750))
        br_tm = ge.add_branch_node()
        bel.set_node_pos(br_tm, pos(1650, 1750))
        # run timer check when NOT forcing close path end — wire from br_23.else
        connect(find_pin(br_23, "else", "Output"), find_pin(br_tm, "execute", "Input"), "tm")
        connect(find_pin(get_ob3, "bIsOpenBusiness", "Output") or out_pin(get_ob3), find_pin(br_tm, "Condition", "Input"), "open tm?")
        # also when 23 but already closed: br_ob.else -> timer skip is fine (closed)
        # GuestTimer += DeltaSeconds
        get_tm = ge.add_get_member_variable_node("GuestTimer")
        bel.set_node_pos(get_tm, pos(1900, 1820))
        addn = add_d(ge, 2150, 1820)
        connect(find_pin(get_tm, "GuestTimer", "Output") or out_pin(get_tm), find_pin(addn, "A", "Input"), "tmA")
        connect(find_pin(tick, "DeltaSeconds", "Output") or find_pin(tick, "Delta Time", "Output"), find_pin(addn, "B", "Input"), "dt")
        set_tm2 = ge.add_set_member_variable_node("GuestTimer")
        bel.set_node_pos(set_tm2, pos(2450, 1750))
        connect(find_pin(br_tm, "then", "Output"), find_pin(set_tm2, "execute", "Input"), "addtm")
        connect(out_pin(addn, "return"), find_pin(set_tm2, "GuestTimer", "Input"), "tmv")
        get_iv = ge.add_get_member_variable_node("GuestInterval")
        bel.set_node_pos(get_iv, pos(2450, 1880))
        # if interval is 0, treat as 4
        geq_iv = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble")
        if geq_iv is None:
            geq_iv = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat")
        bel.set_node_pos(geq_iv, pos(2750, 1820))
        connect(out_pin(addn, "return"), find_pin(geq_iv, "A", "Input"), "tmcmp")
        # Compare to max(GuestInterval, 4) — just use literal 4.0 for reliability
        setdef(find_pin(geq_iv, "B", "Input"), "4.0")
        br_iv = ge.add_branch_node()
        bel.set_node_pos(br_iv, pos(3000, 1750))
        connect(find_pin(set_tm2, "then", "Output"), find_pin(br_iv, "execute", "Input"), "->iv")
        connect(out_pin(geq_iv, "return"), find_pin(br_iv, "Condition", "Input"), "iv?")
        set_rst = ge.add_set_member_variable_node("GuestTimer")
        bel.set_node_pos(set_rst, pos(3300, 1750))
        connect(find_pin(br_iv, "then", "Output"), find_pin(set_rst, "execute", "Input"), "rst")
        setdef(find_pin(set_rst, "GuestTimer", "Input"), "0.0")
        call_sg = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SeatGuest")
        bel.set_node_pos(call_sg, pos(3600, 1750))
        connect(find_pin(set_rst, "then", "Output"), find_pin(call_sg, "execute", "Input"), "seat")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantManager")
    REPORT["ok"]["manager"] = True
    log("manager done")

# ---------------- CHARACTER ----------------
def wire_character():
    src = r"E:\UE\FarmSim25D\Content\TopDown\Blueprints\BP_TopDownCharacter.uasset"
    bak = r"E:\UE\FarmSim25D\Saved\BP_TopDownCharacter_pre_knife2b.uasset"
    try:
        shutil.copy2(src, bak)
        log("backup " + bak)
    except Exception as e:
        REPORT["errors"].append("backup " + str(e))

    bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    ensure_var(bp, "bRestEHandled", "bool")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    # find IA and TillSoil
    ia = None
    till = None
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if n.get_class().get_name() == "K2Node_EnhancedInputAction" and "IA_Interact" in t:
            ia = n
        if t == "TillSoil":
            till = n
    if not ia or not till:
        REPORT["errors"].append("missing IA or TillSoil")
        REPORT["ok"]["character"] = False
        return

    # Break TillSoil execute links and IA Started
    till_ex = find_pin(till, "execute", "Input")
    if till_ex:
        till_ex.break_pin_links()
    started = find_pin(ia, "Started", "Output")
    if started:
        started.break_pin_links()

    # Remove leftover knife2 probe nodes that are clearly restaurant (heuristic)
    kill = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        c = n.get_class().get_name()
        if n in (ia, till):
            continue
        if any(k in t for k in ("bRestEHandled", "GetAllActorsWithTag", "RestInteract", "HandlePlayerE",
                                  "BP_RestaurantManager", "Vector_Distance2D", "Distance2D",
                                  "Restaurant E", "GetAllActorsOfClass")):
            kill.append(n)
        # orphan PrintString with Restaurant in default?
        if t == "PrintString":
            pin = find_pin(n, "InString", "Input")
            val = pin.get_pin_value() if pin else ""
            if "Restaurant" in str(val) or val == "Hello":
                kill.append(n)
    # Also remove orphan Branch/ForEach that only connected to till — safer: remove nodes titled For Each near restaurant work from prior
    # Don't remove random Branch
    if kill:
        # unique
        uniq = []
        seen = set()
        for n in kill:
            i = id(n)
            if i not in seen:
                seen.add(i)
                uniq.append(n)
        ge.remove_nodes(uniq)
        log("char purged restaurant leftovers {}".format(len(uniq)))

    # Re-find after purge
    ia = till = None
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if n.get_class().get_name() == "K2Node_EnhancedInputAction" and "IA_Interact" in t:
            ia = n
        if t == "TillSoil":
            till = n
    started = find_pin(ia, "Started", "Output")
    till_ex = find_pin(till, "execute", "Input")

    y = 900
    set_f = ge.add_set_member_variable_node("bRestEHandled")
    bel.set_node_pos(set_f, pos(-1600, y))
    connect(started, find_pin(set_f, "execute", "Input"), "Started->setF")
    setdef(find_pin(set_f, "bRestEHandled", "Input"), "false")

    # Call Manager.HandlePlayerE
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(-1300, y))
    connect(find_pin(set_f, "then", "Output"), find_pin(gao, "execute", "Input"), "->mgr")
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
    get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(-1000, y + 80))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), "marr")
    setdef(find_pin(get0, "Index", "Input"), "0")
    he = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:HandlePlayerE")
    bel.set_node_pos(he, pos(-700, y))
    connect(find_pin(gao, "then", "Output"), find_pin(he, "execute", "Input"), "->he")
    connect(find_pin(get0, "Item", "Output"), find_pin(he, "self", "Input"), "heself")

    # Local RestInteract scan for TillSoil gate
    gaw = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
    bel.set_node_pos(gaw, pos(-400, y))
    connect(find_pin(he, "then", "Output"), find_pin(gaw, "execute", "Input"), "->tag")
    setdef(find_pin(gaw, "Tag", "Input"), "RestInteract")
    pawn = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(pawn, pos(-400, y + 150))
    setdef(find_pin(pawn, "PlayerIndex", "Input") or find_pin(pawn, "Index", "Input"), "0")
    ploc = ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
    bel.set_node_pos(ploc, pos(-100, y + 150))
    connect(out_pin(pawn, "return"), find_pin(ploc, "self", "Input"), "pl")
    fe = add_foreach(ge, -100, y)
    connect(find_pin(gaw, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "fe")
    connect(find_pin(gaw, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "arr")
    aloc = ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
    bel.set_node_pos(aloc, pos(200, y + 80))
    connect(find_pin(fe, "Array Element", "Output") or find_pin(fe, "Element", "Output"), find_pin(aloc, "self", "Input"), "el")
    dist = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
    bel.set_node_pos(dist, pos(450, y + 80))
    connect(out_pin(ploc, "return"), find_pin(dist, "V1", "Input") or find_pin(dist, "A", "Input"), "v1")
    connect(out_pin(aloc, "return"), find_pin(dist, "V2", "Input") or find_pin(dist, "B", "Input"), "v2")
    lt = cmp_lt_num(ge, 700, y + 80)
    connect(out_pin(dist, "return"), find_pin(lt, "A", "Input"), "d")
    setdef(find_pin(lt, "B", "Input"), "280.0")
    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(950, y))
    connect(find_pin(fe, "LoopBody", "Output") or find_pin(fe, "Loop Body", "Output"), find_pin(br, "execute", "Input"), "body")
    connect(out_pin(lt, "return"), find_pin(br, "Condition", "Input"), "near")
    set_t = ge.add_set_member_variable_node("bRestEHandled")
    bel.set_node_pos(set_t, pos(1200, y))
    connect(find_pin(br, "then", "Output"), find_pin(set_t, "execute", "Input"), "hit")
    setdef(find_pin(set_t, "bRestEHandled", "Input"), "true")

    # Completed -> branch
    get_h = ge.add_get_member_variable_node("bRestEHandled")
    bel.set_node_pos(get_h, pos(1200, y + 160))
    br2 = ge.add_branch_node()
    bel.set_node_pos(br2, pos(1500, y))
    connect(find_pin(fe, "Completed", "Output"), find_pin(br2, "execute", "Input"), "done")
    connect(find_pin(get_h, "bRestEHandled", "Output") or out_pin(get_h), find_pin(br2, "Condition", "Input"), "handled?")
    # else -> TillSoil
    connect(find_pin(br2, "else", "Output"), till_ex, "else->TillSoil")
    # then: restaurant handled — optional confirm print
    pr = make_print(ge, 1800, y - 40, "Restaurant E handled (no TillSoil)")
    connect(find_pin(br2, "then", "Output"), find_pin(pr, "execute", "Input"), "handled print")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    REPORT["ok"]["character"] = True
    log("character done")

def verify():
    acts = eas.get_all_level_actors()
    REPORT["actors_after"] = len(acts)
    rest = [a.get_actor_label() for a in acts if a.get_actor_label().startswith("Restaurant_") or a.get_actor_label().startswith("RestChair_")]
    farm = any(("Grass" in a.get_actor_label() or "Bridge" in a.get_actor_label() or "Tree" in a.get_actor_label()) for a in acts)
    REPORT["rest"] = rest
    REPORT["farm_ok"] = farm
    # IA chain
    bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    chain = {}
    for n in ge.list_all_nodes():
        if "IA_Interact" in bel.get_node_title(n):
            p = find_pin(n, "Started", "Output")
            chain["Started"] = [bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()] if p else []
        if bel.get_node_title(n) == "TillSoil":
            p = find_pin(n, "execute", "Input")
            chain["TillSoil"] = [bel.get_node_title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in p.list_connected_pins()] if p else []
    REPORT["ia_chain"] = chain
    mbp = unreal.EditorAssetLibrary.load_asset(DIR + "/BP_RestaurantManager")
    mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
    REPORT["mgr_nodes"] = [bel.get_node_title(n) for n in mge.list_all_nodes()]
    log("verify actors {} farm {} rest {}".format(REPORT["actors_after"], farm, len(rest)))

def main():
    REPORT["actors_before"] = len(eas.get_all_level_actors())
    try:
        wire_table()
    except Exception as e:
        REPORT["errors"].append("table " + str(e))
        unreal.log_error(str(e))
    try:
        wire_manager()
    except Exception as e:
        REPORT["errors"].append("manager " + str(e))
        unreal.log_error(str(e))
    try:
        wire_character()
    except Exception as e:
        REPORT["errors"].append("character " + str(e))
        unreal.log_error(str(e))
        # rollback character IA to TillSoil
        try:
            bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
            ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
            ia = till = None
            for n in ge.list_all_nodes():
                t = bel.get_node_title(n)
                if "IA_Interact" in t and n.get_class().get_name() == "K2Node_EnhancedInputAction":
                    ia = n
                if t == "TillSoil":
                    till = n
            if ia and till:
                sp = find_pin(ia, "Started", "Output")
                if sp:
                    sp.break_pin_links()
                connect(sp, find_pin(till, "execute", "Input"), "ROLLBACK")
                bel.compile_blueprint(bp)
                unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
                REPORT["ok"]["character_rollback"] = True
        except Exception as e2:
            REPORT["errors"].append("rollback " + str(e2))
    verify()
    # save level
    try:
        unreal.EditorLevelLibrary.save_current_level()
    except Exception:
        pass
    path = r"E:\UE\FarmSim25D\Saved\restaurant_knife2_wire.json"
    open(path, "w", encoding="utf-8").write(json.dumps(REPORT, indent=2, ensure_ascii=False))
    log("wrote " + path)
    print(json.dumps({k: REPORT[k] for k in ("ok", "errors", "actors_before", "actors_after", "farm_ok", "ia_chain", "rest")}, ensure_ascii=False, indent=2))

main()
