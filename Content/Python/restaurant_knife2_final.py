# -*- coding: utf-8 -*-
"""Knife2 final: Manager owns E scan + open gate + guests; Character calls Manager then TillSoil if miss."""
import unreal, json, traceback

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
REPORT = {"steps": [], "errors": [], "ok": {}}

def log(m):
    unreal.log("[REST_K2F2] " + str(m)); REPORT["steps"].append(str(m))

def pos(x,y): return unreal.IntPoint(int(x),int(y))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok = a.try_create_connection(b); log("conn[{}] {}".format(label, ok)); return ok

def setdef(pin, val):
    if not pin: return
    for fn in ("set_default_value", "set_pin_value"):
        try: getattr(pin, fn)(str(val)); return
        except Exception: pass

def make_print(ge,x,y,text,dur="2.5"):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x,y))
    setdef(find_pin(pr,"InString","Input"), text)
    setdef(find_pin(pr,"Duration","Input"), dur)
    return pr

def pin_type(category, sub=""):
    p = unreal.EdGraphPinType()
    if sub: p.import_text('(PinCategory="{}",PinSubCategory="{}")'.format(category, sub))
    else: p.import_text('(PinCategory="{}")'.format(category))
    return p

def add_var(bp, name, ptype):
    names = [str(n) for n in bel.list_member_variable_names(bp)]
    if name in names: return
    bel.add_member_variable(bp, name, ptype)
    try: bel.set_blueprint_variable_instance_editable(bp, name, True)
    except Exception: pass

# ===================== MANAGER =====================
bp_mgr = unreal.EditorAssetLibrary.load_asset(DIR + "/BP_RestaurantManager")
add_var(bp_mgr, "bIsOpenBusiness", pin_type("bool"))
add_var(bp_mgr, "GuestTimer", pin_type("real", "double"))
add_var(bp_mgr, "GuestInterval", pin_type("real", "double"))
add_var(bp_mgr, "bEHandled", pin_type("bool"))  # set true when HandlePlayerE finds a target

mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp_mgr))

# Purge old custom events bodies / knife nodes (keep BeginPlay)
kill = []
for n in list(mge.list_all_nodes()):
    t = bel.get_node_title(n)
    cn = n.get_class().get_name()
    if cn.startswith("K2Node_Event") and any(k in t for k in ("BeginPlay", "ActorBeginOverlap")):
        continue
    # keep Tick event node itself, clear its links later
    if cn.startswith("K2Node_Event") and ("Tick" in t):
        continue
    if cn == "K2Node_CustomEvent":
        kill.append(n); continue
    if any(k in t for k in (
        "HandlePlayerE", "SeatGuest", "ClearGuests", "ToggleOpen", "GetAllActorsWithTag",
        "GetAllActorsOfClass", "For Each Loop", "Cast To", "GuestTimer", "GuestInterval",
        "bIsOpenBusiness", "bOccupied", "CurrentDishId", "GetDisplayMinutes", "Distance2D",
        "GetPlayerPawn", "RestaurantInteract", "Sequence", "ClearGuests", "AUTO-CLOSE",
        "Guest seated", "OPEN!", "CLOSED", "too early", "too late", "Restaurant E",
        "seating", "FarmClock", "BP_Restaurant")):
        kill.append(n)
    if t == "PrintString":
        kill.append(n)
if kill:
    mge.remove_nodes(list({id(n): n for n in kill}.values()))
    log("mgr purged " + str(len(kill)))

# --- Custom event HandlePlayerE ---
he = mge.add_custom_event_node("HandlePlayerE")
bel.set_node_pos(he, pos(0, 200))
he_then = find_pin(he, "then", "Output") or find_pin(he, "execute", "Output")

# Set bEHandled = false
set_h0 = mge.add_set_member_variable_node("bEHandled")
bel.set_node_pos(set_h0, pos(250, 200))
connect(he_then, find_pin(set_h0, "execute", "Input"), "he->h0")
setdef(find_pin(set_h0, "bEHandled", "Input"), "false")

# GetPlayerPawn (pure) + loc
get_pawn = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(get_pawn, pos(250, 360))
setdef(find_pin(get_pawn, "PlayerIndex", "Input"), "0")
pawn_loc = mge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(pawn_loc, pos(500, 360))
connect(find_pin(get_pawn, "ReturnValue", "Output"), find_pin(pawn_loc, "self", "Input"), "pawn")

gat = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
bel.set_node_pos(gat, pos(500, 200))
connect(find_pin(set_h0, "then", "Output"), find_pin(gat, "execute", "Input"), "->gat")
setdef(find_pin(gat, "Tag", "Input"), "RestInteract")

fe = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
if fe is None:
    fe = mge.create_node_from_name("ForEachLoop", unreal.Vector2D(800, 200), [])
bel.set_node_pos(fe, pos(800, 200))
connect(find_pin(gat, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "fe")
connect(find_pin(gat, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "arr")
el = find_pin(fe, "Array Element", "Output") or find_pin(fe, "Element", "Output")
body = find_pin(fe, "LoopBody", "Output") or find_pin(fe, "Then", "Output")

act_loc = mge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(act_loc, pos(1100, 80))
connect(el, find_pin(act_loc, "self", "Input"), "el")
dist = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
bel.set_node_pos(dist, pos(1350, 200))
connect(find_pin(pawn_loc, "ReturnValue", "Output"), find_pin(dist, "A", "Input") or find_pin(dist, "V1", "Input"), "A")
connect(find_pin(act_loc, "ReturnValue", "Output"), find_pin(dist, "B", "Input") or find_pin(dist, "V2", "Input"), "B")
lt = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
if lt is None: lt = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
bel.set_node_pos(lt, pos(1600, 200))
connect(find_pin(dist, "ReturnValue", "Output"), find_pin(lt, "A", "Input"), "d")
setdef(find_pin(lt, "B", "Input"), "200.0")
br = mge.add_branch_node(); bel.set_node_pos(br, pos(1850, 200))
connect(body, find_pin(br, "execute", "Input"), "body")
connect(find_pin(lt, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "near")

# Near: set handled + get label + branch OpenSign vs other
set_h1 = mge.add_set_member_variable_node("bEHandled")
bel.set_node_pos(set_h1, pos(2100, 120))
connect(find_pin(br, "then", "Output"), find_pin(set_h1, "execute", "Input"), "handled")
setdef(find_pin(set_h1, "bEHandled", "Input"), "true")

get_label = mge.add_call_function_node("/Script/Engine.Actor:GetActorLabel")
if get_label is None:
    get_label = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
bel.set_node_pos(get_label, pos(2100, 280))
connect(el, find_pin(get_label, "self", "Input") or find_pin(get_label, "Object", "Input"), "lab")

# Contains "OpenSign"?
contains = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains")
bel.set_node_pos(contains, pos(2400, 280))
connect(find_pin(get_label, "ReturnValue", "Output"), find_pin(contains, "SearchIn", "Input") or find_pin(contains, "Source", "Input"), "src")
setdef(find_pin(contains, "Substring", "Input") or find_pin(contains, "SearchFor", "Input"), "OpenSign")

br_sign = mge.add_branch_node(); bel.set_node_pos(br_sign, pos(2700, 120))
connect(find_pin(set_h1, "then", "Output"), find_pin(br_sign, "execute", "Input"), "->sign?")
connect(find_pin(contains, "ReturnValue", "Output"), find_pin(br_sign, "Condition", "Input"), "isSign")

# ---- OpenSign TRUE: ToggleOpen logic ----
# Get FarmClock
gao_fc = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao_fc, pos(3000, 0))
connect(find_pin(br_sign, "then", "Output"), find_pin(gao_fc, "execute", "Input"), "->clock")
setdef(find_pin(gao_fc, "ActorClass", "Input") or find_pin(gao_fc, "Class", "Input"), "/Script/FarmSim25D.FarmClock")
get0 = mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(get0, pos(3250, 60))
connect(find_pin(gao_fc, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input") or find_pin(get0, "Array", "Input"), "arr")
setdef(find_pin(get0, "Index", "Input"), "0")
cast_fc = None
try: cast_fc = mge.create_node_from_name("Cast To FarmClock", unreal.Vector2D(3500, 0), [])
except Exception as e: log("castfc " + str(e))
if cast_fc:
    bel.set_node_pos(cast_fc, pos(3500, 0))
    connect(find_pin(gao_fc, "then", "Output"), find_pin(cast_fc, "execute", "Input"), "castfc")
    item = find_pin(get0, "Item", "Output") or find_pin(get0, "ReturnValue", "Output") or find_pin(get0, "Output", "Output")
    if item is None:
        for p in bel.list_all_pins(get0):
            if "output" in str(p.get_pin_direction()).lower():
                item = p; break
    connect(item, find_pin(cast_fc, "Object", "Input"), "obj")
    gdm = mge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
    bel.set_node_pos(gdm, pos(3800, 80))
    as_fc = None
    for p in bel.list_all_pins(cast_fc):
        if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
            as_fc = p; break
    connect(as_fc, find_pin(gdm, "self", "Input"), "gdm")

    get_open = mge.add_get_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(get_open, pos(3800, 200))
    br_o = mge.add_branch_node(); bel.set_node_pos(br_o, pos(4100, 0))
    connect(find_pin(cast_fc, "then", "Output"), find_pin(br_o, "execute", "Input"), "brO")
    connect(find_pin(get_open, "bIsOpenBusiness", "Output"), find_pin(br_o, "Condition", "Input"), "open?")

    # close
    set_c = mge.add_set_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(set_c, pos(4400, -120))
    connect(find_pin(br_o, "then", "Output"), find_pin(set_c, "execute", "Input"), "close")
    setdef(find_pin(set_c, "bIsOpenBusiness", "Input"), "false")
    pr_c = make_print(mge, 4700, -120, "Restaurant: CLOSED early — seating stopped")
    connect(find_pin(set_c, "then", "Output"), find_pin(pr_c, "execute", "Input"), "prc")
    # call ClearGuests
    call_clear = mge.create_node_from_name("ClearGuests", unreal.Vector2D(5000, -120), []) if False else None
    # We'll add ClearGuests event below and create call after

    # late
    geq = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
    bel.set_node_pos(geq, pos(4400, 80))
    connect(find_pin(gdm, "ReturnValue", "Output"), find_pin(geq, "A", "Input"), "m")
    setdef(find_pin(geq, "B", "Input"), "1380")
    br_l = mge.add_branch_node(); bel.set_node_pos(br_l, pos(4650, 80))
    connect(find_pin(br_o, "else", "Output"), find_pin(br_l, "execute", "Input"), "late?")
    connect(find_pin(geq, "ReturnValue", "Output"), find_pin(br_l, "Condition", "Input"), "condL")
    pr_l = make_print(mge, 4950, 40, "Restaurant: too late (>=23:00), cannot open")
    connect(find_pin(br_l, "then", "Output"), find_pin(pr_l, "execute", "Input"), "late")

    # early
    lti = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_IntInt")
    bel.set_node_pos(lti, pos(4950, 200))
    connect(find_pin(gdm, "ReturnValue", "Output"), find_pin(lti, "A", "Input"), "m")
    setdef(find_pin(lti, "B", "Input"), "1020")
    br_e = mge.add_branch_node(); bel.set_node_pos(br_e, pos(5200, 200))
    connect(find_pin(br_l, "else", "Output"), find_pin(br_e, "execute", "Input"), "early?")
    connect(find_pin(lti, "ReturnValue", "Output"), find_pin(br_e, "Condition", "Input"), "condE")
    pr_e = make_print(mge, 5500, 160, "Restaurant: too early (<17:00), cannot open")
    connect(find_pin(br_e, "then", "Output"), find_pin(pr_e, "execute", "Input"), "early")

    # open ok
    set_o = mge.add_set_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(set_o, pos(5500, 320))
    connect(find_pin(br_e, "else", "Output"), find_pin(set_o, "execute", "Input"), "open")
    setdef(find_pin(set_o, "bIsOpenBusiness", "Input"), "true")
    pr_o = make_print(mge, 5800, 320, "Restaurant: OPEN! Guests every ~4s when a table is free.")
    connect(find_pin(set_o, "then", "Output"), find_pin(pr_o, "execute", "Input"), "pro")
else:
    pr_fb = make_print(mge, 3000, 0, "Restaurant SIGN: FarmClock cast failed")
    connect(find_pin(br_sign, "then", "Output"), find_pin(pr_fb, "execute", "Input"), "fb")

# ---- Not OpenSign: Print Restaurant E -> label ----
append = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
bel.set_node_pos(append, pos(3000, 400))
setdef(find_pin(append, "A", "Input"), "Restaurant E -> ")
connect(find_pin(get_label, "ReturnValue", "Output"), find_pin(append, "B", "Input"), "name")
pr_other = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
bel.set_node_pos(pr_other, pos(3300, 400))
connect(find_pin(br_sign, "else", "Output"), find_pin(pr_other, "execute", "Input"), "other")
connect(find_pin(append, "ReturnValue", "Output"), find_pin(pr_other, "InString", "Input"), "str")
setdef(find_pin(pr_other, "Duration", "Input"), "2.5")

# --- ClearGuests custom event ---
cg = mge.add_custom_event_node("ClearGuests")
bel.set_node_pos(cg, pos(0, 900))
pr_cg = make_print(mge, 250, 900, "Restaurant: clearing guests / freeing tables")
connect(find_pin(cg, "then", "Output") or find_pin(cg, "execute", "Output"), find_pin(pr_cg, "execute", "Input"), "cg")
gao_t = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao_t, pos(550, 900))
connect(find_pin(pr_cg, "then", "Output"), find_pin(gao_t, "execute", "Input"), "tables")
setdef(find_pin(gao_t, "ActorClass", "Input") or find_pin(gao_t, "Class", "Input"),
       DIR + "/BP_RestaurantTable.BP_RestaurantTable_C")
fe_c = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
if fe_c is None: fe_c = mge.create_node_from_name("ForEachLoop", unreal.Vector2D(850, 900), [])
bel.set_node_pos(fe_c, pos(850, 900))
connect(find_pin(gao_t, "then", "Output"), find_pin(fe_c, "Exec", "Input") or find_pin(fe_c, "execute", "Input"), "fe")
connect(find_pin(gao_t, "OutActors", "Output"), find_pin(fe_c, "Array", "Input"), "arr")
cast_t = None
try: cast_t = mge.create_node_from_name("Cast To BP_RestaurantTable", unreal.Vector2D(1150, 850), [])
except Exception as e: log(str(e))
if cast_t:
    bel.set_node_pos(cast_t, pos(1150, 850))
    connect(find_pin(fe_c, "LoopBody", "Output") or find_pin(fe_c, "Then", "Output"), find_pin(cast_t, "execute", "Input"), "body")
    connect(find_pin(fe_c, "Array Element", "Output") or find_pin(fe_c, "Element", "Output"), find_pin(cast_t, "Object", "Input"), "el")
    set_free = None
    try: set_free = mge.create_node_from_name("Set bOccupied", unreal.Vector2D(1450, 850), [])
    except Exception: pass
    if set_free:
        bel.set_node_pos(set_free, pos(1450, 850))
        connect(find_pin(cast_t, "then", "Output"), find_pin(set_free, "execute", "Input"), "free")
        as_t = None
        for p in bel.list_all_pins(cast_t):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_t = p; break
        connect(as_t, find_pin(set_free, "self", "Input") or find_pin(set_free, "Target", "Input"), "as")
        setdef(find_pin(set_free, "bOccupied", "Input"), "false")

# Wire close path -> ClearGuests call
if cast_fc:
    try:
        call_cg = mge.create_node_from_name("ClearGuests", unreal.Vector2D(5000, -120), [])
        if call_cg:
            bel.set_node_pos(call_cg, pos(5000, -120))
            connect(find_pin(pr_c, "then", "Output"), find_pin(call_cg, "execute", "Input"), "->clear")
    except Exception as e:
        log("call clear " + str(e))

# --- SeatGuest ---
sg = mge.add_custom_event_node("SeatGuest")
bel.set_node_pos(sg, pos(0, 1300))
gao_s = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao_s, pos(250, 1300))
connect(find_pin(sg, "then", "Output") or find_pin(sg, "execute", "Output"), find_pin(gao_s, "execute", "Input"), "seat")
setdef(find_pin(gao_s, "ActorClass", "Input") or find_pin(gao_s, "Class", "Input"),
       DIR + "/BP_RestaurantTable.BP_RestaurantTable_C")
fe_s = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
if fe_s is None: fe_s = mge.create_node_from_name("ForEachLoop", unreal.Vector2D(550, 1300), [])
bel.set_node_pos(fe_s, pos(550, 1300))
connect(find_pin(gao_s, "then", "Output"), find_pin(fe_s, "Exec", "Input") or find_pin(fe_s, "execute", "Input"), "fe")
connect(find_pin(gao_s, "OutActors", "Output"), find_pin(fe_s, "Array", "Input"), "arr")
cast_s = None
try: cast_s = mge.create_node_from_name("Cast To BP_RestaurantTable", unreal.Vector2D(850, 1250), [])
except Exception: pass
if cast_s:
    bel.set_node_pos(cast_s, pos(850, 1250))
    connect(find_pin(fe_s, "LoopBody", "Output") or find_pin(fe_s, "Then", "Output"), find_pin(cast_s, "execute", "Input"), "body")
    connect(find_pin(fe_s, "Array Element", "Output") or find_pin(fe_s, "Element", "Output"), find_pin(cast_s, "Object", "Input"), "el")
    as_s = None
    for p in bel.list_all_pins(cast_s):
        if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
            as_s = p; break
    get_occ = None
    try: get_occ = mge.create_node_from_name("Get bOccupied", unreal.Vector2D(1150, 1400), [])
    except Exception: pass
    br_free = mge.add_branch_node(); bel.set_node_pos(br_free, pos(1400, 1250))
    connect(find_pin(cast_s, "then", "Output"), find_pin(br_free, "execute", "Input"), "free?")
    if get_occ:
        bel.set_node_pos(get_occ, pos(1150, 1400))
        connect(as_s, find_pin(get_occ, "self", "Input") or find_pin(get_occ, "Target", "Input"), "as")
        notb = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
        bel.set_node_pos(notb, pos(1350, 1400))
        connect(find_pin(get_occ, "bOccupied", "Output") or find_pin(get_occ, "ReturnValue", "Output"),
                find_pin(notb, "A", "Input"), "occ")
        connect(find_pin(notb, "ReturnValue", "Output"), find_pin(br_free, "Condition", "Input"), "!")
    set_occ = None
    try: set_occ = mge.create_node_from_name("Set bOccupied", unreal.Vector2D(1700, 1200), [])
    except Exception: pass
    if set_occ:
        bel.set_node_pos(set_occ, pos(1700, 1200))
        connect(find_pin(br_free, "then", "Output"), find_pin(set_occ, "execute", "Input"), "seat!")
        connect(as_s, find_pin(set_occ, "self", "Input") or find_pin(set_occ, "Target", "Input"), "as")
        setdef(find_pin(set_occ, "bOccupied", "Input"), "true")
        rand = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:RandomIntegerInRange")
        bel.set_node_pos(rand, pos(1700, 1400))
        setdef(find_pin(rand, "Min", "Input"), "1")
        setdef(find_pin(rand, "Max", "Input"), "2")
        set_dish = None
        try: set_dish = mge.create_node_from_name("Set CurrentDishId", unreal.Vector2D(2000, 1200), [])
        except Exception: pass
        if set_dish:
            bel.set_node_pos(set_dish, pos(2000, 1200))
            connect(find_pin(set_occ, "then", "Output"), find_pin(set_dish, "execute", "Input"), "dish")
            connect(as_s, find_pin(set_dish, "self", "Input") or find_pin(set_dish, "Target", "Input"), "as")
            connect(find_pin(rand, "ReturnValue", "Output"), find_pin(set_dish, "CurrentDishId", "Input"), "id")
            pr_s = make_print(mge, 2300, 1200, "Restaurant: Guest seated + ordered (CurrentDishId 1=salad 2=stew). Full tables stop new guests.")
            connect(find_pin(set_dish, "then", "Output"), find_pin(pr_s, "execute", "Input"), "prs")
        # WARNING: ForEach seats ALL free tables same pulse. Mitigate with bSeatLock:
        # After first seat set a gate — add Set GuestTimer already 0; accept both tables fill in one pulse if both free
        # Better: only seat ONE by using DoOnce macro inside SeatGuest
        do_once = None
        try:
            do_once = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:DoOnce")
        except Exception:
            try: do_once = mge.create_node_from_name("DoOnce", unreal.Vector2D(1550, 1200), [])
            except Exception: pass
        if do_once and set_occ:
            # Rewire: br_free then -> DoOnce -> set_occ
            bel.set_node_pos(do_once, pos(1550, 1180))
            # break br_free -> set_occ and insert DoOnce
            br_then = find_pin(br_free, "then", "Output")
            set_exec = find_pin(set_occ, "execute", "Input")
            if br_then and set_exec:
                for cp in list(br_then.list_connected_pins()):
                    try: br_then.break_link_to(cp)
                    except Exception: pass
                connect(br_then, find_pin(do_once, "execute", "Input") or find_pin(do_once, "Exec", "Input"), "->once")
                connect(find_pin(do_once, "Completed", "Output") or find_pin(do_once, "then", "Output"), set_exec, "once->set")

# --- Event Tick: auto-close + guest timer ---
tick_n = None
for n in mge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Event Tick" in t or t == "ReceiveTick":
        tick_n = n; break
if tick_n is None:
    try: tick_n = mge.add_event_node("ReceiveTick")
    except Exception:
        tick_n = mge.create_node_from_name("Event Tick", unreal.Vector2D(0, 1700), [])
bel.set_node_pos(tick_n, pos(0, 1700))
tick_then = find_pin(tick_n, "then", "Output") or find_pin(tick_n, "execute", "Output")
delta = find_pin(tick_n, "Delta", "Output") or find_pin(tick_n, "DeltaSeconds", "Output")
# break non-parent links
if tick_then:
    for cp in list(tick_then.list_connected_pins()):
        if "Parent" in bel.get_node_title(cp.get_owning_node()): continue
        try: tick_then.break_link_to(cp)
        except Exception: pass

seq = None
try: seq = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:Sequence")
except Exception:
    try: seq = mge.create_node_from_name("Sequence", unreal.Vector2D(250, 1700), [])
    except Exception: pass
if seq:
    bel.set_node_pos(seq, pos(250, 1700))
    connect(tick_then, find_pin(seq, "execute", "Input") or find_pin(seq, "Exec", "Input"), "tick->seq")
    t0 = find_pin(seq, "Then 0", "Output") or find_pin(seq, "then_0", "Output")
    t1 = find_pin(seq, "Then 1", "Output") or find_pin(seq, "then_1", "Output")
else:
    t0, t1 = tick_then, None

# Then0 auto-close at 1380
gao2 = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao2, pos(500, 1600))
connect(t0, find_pin(gao2, "execute", "Input"), "clock")
setdef(find_pin(gao2, "ActorClass", "Input") or find_pin(gao2, "Class", "Input"), "/Script/FarmSim25D.FarmClock")
get02 = mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(get02, pos(750, 1660))
connect(find_pin(gao2, "OutActors", "Output"), find_pin(get02, "TargetArray", "Input") or find_pin(get02, "Array", "Input"), "a")
setdef(find_pin(get02, "Index", "Input"), "0")
cast2 = None
try: cast2 = mge.create_node_from_name("Cast To FarmClock", unreal.Vector2D(1000, 1600), [])
except Exception: pass
if cast2:
    bel.set_node_pos(cast2, pos(1000, 1600))
    connect(find_pin(gao2, "then", "Output"), find_pin(cast2, "execute", "Input"), "c")
    item2 = find_pin(get02, "Item", "Output") or find_pin(get02, "ReturnValue", "Output") or find_pin(get02, "Output", "Output")
    connect(item2, find_pin(cast2, "Object", "Input"), "o")
    gdm2 = mge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
    bel.set_node_pos(gdm2, pos(1250, 1660))
    as2 = None
    for p in bel.list_all_pins(cast2):
        if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
            as2 = p; break
    connect(as2, find_pin(gdm2, "self", "Input"), "g")
    geq2 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
    bel.set_node_pos(geq2, pos(1500, 1660))
    connect(find_pin(gdm2, "ReturnValue", "Output"), find_pin(geq2, "A", "Input"), "m")
    setdef(find_pin(geq2, "B", "Input"), "1380")
    get_o2 = mge.add_get_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(get_o2, pos(1500, 1780))
    and2 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND"); bel.set_node_pos(and2, pos(1750, 1700))
    connect(find_pin(geq2, "ReturnValue", "Output"), find_pin(and2, "A", "Input"), "a")
    connect(find_pin(get_o2, "bIsOpenBusiness", "Output"), find_pin(and2, "B", "Input"), "b")
    br_ac = mge.add_branch_node(); bel.set_node_pos(br_ac, pos(2000, 1600))
    connect(find_pin(cast2, "then", "Output"), find_pin(br_ac, "execute", "Input"), "br")
    connect(find_pin(and2, "ReturnValue", "Output"), find_pin(br_ac, "Condition", "Input"), "c")
    set_ac = mge.add_set_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(set_ac, pos(2300, 1550))
    connect(find_pin(br_ac, "then", "Output"), find_pin(set_ac, "execute", "Input"), "close")
    setdef(find_pin(set_ac, "bIsOpenBusiness", "Input"), "false")
    pr_ac = make_print(mge, 2600, 1550, "Restaurant AUTO-CLOSE 23:00")
    connect(find_pin(set_ac, "then", "Output"), find_pin(pr_ac, "execute", "Input"), "pr")
    try:
        call_cg2 = mge.create_node_from_name("ClearGuests", unreal.Vector2D(2900, 1550), [])
        if call_cg2:
            bel.set_node_pos(call_cg2, pos(2900, 1550))
            connect(find_pin(pr_ac, "then", "Output"), find_pin(call_cg2, "execute", "Input"), "cg")
    except Exception: pass

# Then1 guest timer
if t1:
    get_o3 = mge.add_get_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(get_o3, pos(500, 1950))
    br_g = mge.add_branch_node(); bel.set_node_pos(br_g, pos(750, 1900))
    connect(t1, find_pin(br_g, "execute", "Input"), "g?")
    connect(find_pin(get_o3, "bIsOpenBusiness", "Output"), find_pin(br_g, "Condition", "Input"), "open")
    get_t = mge.add_get_member_variable_node("GuestTimer"); bel.set_node_pos(get_t, pos(1000, 2050))
    addf = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
    if addf is None: addf = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
    bel.set_node_pos(addf, pos(1250, 2000))
    connect(find_pin(get_t, "GuestTimer", "Output"), find_pin(addf, "A", "Input"), "t")
    connect(delta, find_pin(addf, "B", "Input"), "dt")
    set_t = mge.add_set_member_variable_node("GuestTimer"); bel.set_node_pos(set_t, pos(1550, 1900))
    connect(find_pin(br_g, "then", "Output"), find_pin(set_t, "execute", "Input"), "setT")
    connect(find_pin(addf, "ReturnValue", "Output"), find_pin(set_t, "GuestTimer", "Input"), "v")
    get_iv = mge.add_get_member_variable_node("GuestInterval"); bel.set_node_pos(get_iv, pos(1550, 2050))
    geqf = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble")
    if geqf is None: geqf = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat")
    bel.set_node_pos(geqf, pos(1850, 1900))
    connect(find_pin(addf, "ReturnValue", "Output"), find_pin(geqf, "A", "Input"), "a")
    connect(find_pin(get_iv, "GuestInterval", "Output"), find_pin(geqf, "B", "Input"), "b")
    br_r = mge.add_branch_node(); bel.set_node_pos(br_r, pos(2150, 1900))
    connect(find_pin(set_t, "then", "Output"), find_pin(br_r, "execute", "Input"), "ready?")
    connect(find_pin(geqf, "ReturnValue", "Output"), find_pin(br_r, "Condition", "Input"), "c")
    set_t0 = mge.add_set_member_variable_node("GuestTimer"); bel.set_node_pos(set_t0, pos(2450, 1860))
    connect(find_pin(br_r, "then", "Output"), find_pin(set_t0, "execute", "Input"), "reset")
    setdef(find_pin(set_t0, "GuestTimer", "Input"), "0.0")
    try:
        call_sg = mge.create_node_from_name("SeatGuest", unreal.Vector2D(2750, 1860), [])
        if call_sg:
            bel.set_node_pos(call_sg, pos(2750, 1860))
            connect(find_pin(set_t0, "then", "Output"), find_pin(call_sg, "execute", "Input"), "seat")
    except Exception as e: log("seat call " + str(e))

bel.compile_blueprint(bp_mgr)
unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantManager")
REPORT["ok"]["manager"] = True
log("manager done")

# ===================== CHARACTER =====================
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
add_var(cbp, "bRestEHandled", pin_type("bool"))
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia = till = None
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IA_Interact" in t: ia = n
    if t == "TillSoil": till = n
started = find_pin(ia, "Started", "Output")

# clean restaurant helpers
kill = []
if started:
    stack = list(started.list_connected_pins()); seen = set()
    while stack:
        p = stack.pop(0); n = p.get_owning_node()
        if id(n) in seen: continue
        seen.add(id(n)); t = bel.get_node_title(n)
        if t == "TillSoil" or "IA_Interact" in t: continue
        kill.append(n)
        for pp in bel.list_all_pins(n):
            for cp in pp.list_connected_pins(): stack.append(cp)
for n in list(cge.list_all_nodes()):
    t = bel.get_node_title(n)
    if any(k in t for k in ("GetAllActorsWithTag", "For Each Loop", "bRestEHandled", "Distance2D",
                              "GetPlayerPawn", "HandlePlayerE", "Cast To BP_Restaurant", "RestaurantInteract",
                              "GetAllActorsOfClass", "Not_PreBool", "Less_", "GetDisplayName", "Concat_StrStr")):
        if t != "TillSoil" and "IA_Interact" not in t:
            kill.append(n)
kill = [n for n in kill if bel.get_node_title(n) != "TillSoil" and "IA_Interact" not in bel.get_node_title(n)]
kill = list({id(n): n for n in kill}.values())
if kill:
    cge.remove_nodes(kill); log("char cleaned " + str(len(kill)))
if started:
    for cp in list(started.list_connected_pins()):
        try: started.break_link_to(cp)
        except Exception: pass

# Started -> GetAllActorsOfClass Manager -> Array_Get0 -> Cast -> HandlePlayerE
# -> read Manager.bEHandled -> Branch !handled -> TillSoil
gao = cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao, pos(-2000, 1000))
connect(started, find_pin(gao, "execute", "Input"), "IA->mgrs")
setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"),
       DIR + "/BP_RestaurantManager.BP_RestaurantManager_C")
get0 = cge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(get0, pos(-1700, 1080))
connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input") or find_pin(get0, "Array", "Input"), "arr")
setdef(find_pin(get0, "Index", "Input"), "0")
cast_m = None
try: cast_m = cge.create_node_from_name("Cast To BP_RestaurantManager", unreal.Vector2D(-1400, 1000), [])
except Exception as e: log(str(e))
if not cast_m:
    # fallback TillSoil only
    connect(started, find_pin(till, "execute", "Input"), "ROLLBACK no cast")
    REPORT["errors"].append("no manager cast")
    REPORT["ok"]["character"] = False
else:
    bel.set_node_pos(cast_m, pos(-1400, 1000))
    connect(find_pin(gao, "then", "Output"), find_pin(cast_m, "execute", "Input"), "cast")
    item = find_pin(get0, "Item", "Output") or find_pin(get0, "ReturnValue", "Output") or find_pin(get0, "Output", "Output")
    if item is None:
        for p in bel.list_all_pins(get0):
            if "output" in str(p.get_pin_direction()).lower():
                item = p; break
    connect(item, find_pin(cast_m, "Object", "Input"), "obj")
    as_m = None
    for p in bel.list_all_pins(cast_m):
        if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
            as_m = p; break
    # Call HandlePlayerE
    call_he = None
    try: call_he = cge.create_node_from_name("HandlePlayerE", unreal.Vector2D(-1000, 1000), [])
    except Exception as e: log("he " + str(e))
    if call_he is None:
        # add_call_function custom event?
        try:
            call_he = cge.add_call_function_node(DIR + "/BP_RestaurantManager.BP_RestaurantManager_C:HandlePlayerE")
        except Exception as e:
            log("he2 " + str(e))
    if call_he:
        bel.set_node_pos(call_he, pos(-1000, 1000))
        connect(find_pin(cast_m, "then", "Output"), find_pin(call_he, "execute", "Input") or find_pin(call_he, "self", "Input") and find_pin(call_he, "execute", "Input"), "->he")
        # self target
        connect(as_m, find_pin(call_he, "self", "Input") or find_pin(call_he, "Target", "Input"), "as->he")
        # After HE: get bEHandled from manager
        get_h = None
        try: get_h = cge.create_node_from_name("Get bEHandled", unreal.Vector2D(-700, 1150), [])
        except Exception: pass
        br_t = cge.add_branch_node(); bel.set_node_pos(br_t, pos(-400, 1000))
        connect(find_pin(call_he, "then", "Output"), find_pin(br_t, "execute", "Input"), "->br")
        if get_h:
            bel.set_node_pos(get_h, pos(-700, 1150))
            connect(as_m, find_pin(get_h, "self", "Input") or find_pin(get_h, "Target", "Input"), "as")
            notb = cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
            bel.set_node_pos(notb, pos(-500, 1150))
            connect(find_pin(get_h, "bEHandled", "Output") or find_pin(get_h, "ReturnValue", "Output"),
                    find_pin(notb, "A", "Input"), "h")
            connect(find_pin(notb, "ReturnValue", "Output"), find_pin(br_t, "Condition", "Input"), "!h")
        else:
            # if can't read, always TillSoil after (safe for farming) — restaurant still got HandlePlayerE
            setdef(find_pin(br_t, "Condition", "Input"), "true")
            log("WARN: always TillSoil after HE (no bEHandled get)")
        connect(find_pin(br_t, "then", "Output"), find_pin(till, "execute", "Input"), "TillSoil")
        REPORT["ok"]["character"] = True
    else:
        connect(find_pin(cast_m, "then", "Output"), find_pin(till, "execute", "Input"), "no HE fallback till")
        REPORT["ok"]["character"] = False
        REPORT["errors"].append("HandlePlayerE call missing")

bel.compile_blueprint(cbp)
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

# Level instance defaults
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab == "Restaurant_Manager":
        for k, v in (("GuestInterval", 4.0), ("guest_interval", 4.0), ("GuestTimer", 0.0),
                     ("bIsOpenBusiness", False), ("b_is_open_business", False),
                     ("bEHandled", False), ("b_e_handled", False)):
            try: a.set_editor_property(k, v)
            except Exception: pass
        try: a.set_actor_tick_enabled(True)
        except Exception: pass
    if lab.startswith("Restaurant_Table"):
        for k, v in (("bOccupied", False), ("b_occupied", False), ("CurrentDishId", 0), ("current_dish_id", 0)):
            try: a.set_editor_property(k, v)
            except Exception: pass

REPORT["actors"] = len(eas.get_all_level_actors())
from collections import Counter
c = Counter()
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("VMF_Grass"): c["grass"] += 1
    elif "Bridge" in lab: c["bridge"] += 1
    elif "Tree" in lab: c["tree"] += 1
REPORT["farm"] = dict(c)

# verify IA
chain = []
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "Started":
                for cp in p.list_connected_pins():
                    chain.append(bel.get_node_title(cp.get_owning_node()))
REPORT["ia"] = chain

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    REPORT["saved"] = True
except Exception:
    unreal.EditorLevelLibrary.save_current_level(); REPORT["saved"] = True

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_final.json", "w", encoding="utf-8").write(
    json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
