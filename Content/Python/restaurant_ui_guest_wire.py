# -*- coding: utf-8 -*-
"""
Wire restaurant order UI + guest visuals.
- Side strip: WBP_RestOrderList Create/AddToViewport + RefreshOrderUI (Print Key backup)
- Bubble: OrderBubble WidgetComponent show/hide + DrawDebug patience
- Guest: spawn BP_RestGuest on TrySeat, destroy on ClearSeat; Paint Tint MI by TableId
Surgical: add custom events + splice terminals; do not wipe cook/serve graphs.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"
WBP_LIST = "/Game/Farm/UI/WBP_RestOrderList"
MI_RED = "/Game/Farm/Restaurant/Guests/MI_GuestRed"
MI_BLUE = "/Game/Farm/Restaurant/Guests/MI_GuestBlue"
MI_GREEN = "/Game/Farm/Restaurant/Guests/MI_GuestGreen"

R = {"steps": [], "errors": []}

def log(m):
    unreal.log("[UI_WIRE] " + str(m))
    print("[UI_WIRE] " + str(m))
    R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Return Value", "Item", "GuestMesh", "OrderListWidget", "GuestActor",
                 "bOccupied", "CurrentOrder", "CurrentDishId", "bHasOrder", "bOrderPending", "bEating",
                 "PatienceLeft", "EatLeft", "OrderPrice", "TableId", "TintIndex", "bIsOpenBusiness"):
        p = find_pin(node, name, "Output")
        if p:
            return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            if str(p.get_pin_name()).lower() not in ("outputdelegate", "then", "else", "completed", "loopbody"):
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
        return False
    try:
        pin.set_pin_value(str(val))
        return True
    except Exception:
        try:
            pin.set_default_value(str(val))
            return True
        except Exception as e:
            log("setdef fail " + str(e)[:80])
            return False

def make_print(ge, x, y, text, dur="1.5", key=""):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    if key:
        setdef(find_pin(pr, "Key", "Input"), key)
    return pr

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

def ensure_var(bp, name, type_name):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    t = bel.get_basic_type_by_name(type_name)
    if name not in names:
        bel.add_member_variable(bp, name, t)
        log("add {}.{}".format(bp.get_name(), name))
    return True

def ensure_object_var(bp, name, class_path):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    if name in names:
        return
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="object",PinSubCategory="",PinSubCategoryObject="{}")'.format(class_path))
    bel.add_member_variable(bp, name, p)
    log("add obj {}.{}".format(bp.get_name(), name))

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def find_event(ge, name_substr):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_Event" and name_substr in title(n):
            return n
    return None

def walk_then(start_node, max_d=30):
    thenp = find_pin(start_node, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen = []
    seen_ids = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in seen_ids or d > max_d:
            continue
        seen_ids.add(id(cur))
        seen.append(cur)
        for pn in ("then", "else", "Completed", "LoopBody"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d + 1))
    return seen

def terminal_thens(start_node):
    """Return list of (node, then_pin) that have then output with no connections (exec terminals)."""
    nodes = walk_then(start_node)
    # also include start if its then goes nowhere? usually not
    terms = []
    for n in nodes:
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            terms.append((n, thenp))
    return terms

def splice_after_terminals(ge, start_node, new_exec_node, label=""):
    """Connect all terminal then pins to new_exec_node execute."""
    terms = terminal_thens(start_node)
    if not terms:
        # connect directly from start then if empty
        thenp = find_pin(start_node, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            terms = [(start_node, thenp)]
    for n, thenp in terms:
        connect(thenp, find_pin(new_exec_node, "execute", "Input"), label + "<-" + title(n))
    return len(terms)

def purge_disconnected_calls(ge, titles_or_funcs):
    """Break links on orphan probe nodes matching titles (best-effort)."""
    for n in list(ge.list_all_nodes()):
        t = title(n)
        if any(k in t for k in titles_or_funcs):
            # if no exec in connected, leave; only remove fully disconnected
            exe_in = find_pin(n, "execute", "Input")
            has_in = bool(exec_in and list(exec_in.list_connected_pins() or []))
            if not has_in and n.get_class().get_name() == "K2Node_CallFunction":
                for p in bel.list_all_pins(n):
                    try:
                        p.break_pin_links()
                    except Exception:
                        pass
                log("orphaned break " + t)

# ===================== VARS =====================
mbp = unreal.load_asset(MGR)
tbp = unreal.load_asset(TBL)
gbp = unreal.load_asset(GUEST)

ensure_object_var(mbp, "OrderListWidget", "/Script/UMG.UserWidget")
ensure_var(mbp, "bOrderUIReady", "bool")
ensure_object_var(tbp, "GuestActor", "/Script/Engine.Actor")
ensure_var(tbp, "bBubbleVisible", "bool")

# ===================== TABLE: SpawnGuest / DestroyGuest =====================
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))

# Remove prior UI/guest custom events if re-run
for old in ("SpawnGuestVisual", "DestroyGuestVisual", "RefreshTableBubble", "UI_SpawnGuest", "UI_DestroyGuest"):
    ev = find_custom(tge, old)
    if ev:
        for p in bel.list_all_pins(ev):
            try:
                p.break_pin_links()
            except Exception:
                pass

# --- DestroyGuestVisual: if GuestActor valid -> Destroy -> set null; hide bubble ---
des = tge.add_custom_event_node("DestroyGuestVisual")
bel.set_node_pos(des, pos(-2800, 4200))
get_g = tge.add_get_member_variable_node("GuestActor")
bel.set_node_pos(get_g, pos(-2500, 4300))
is_valid = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
bel.set_node_pos(is_valid, pos(-2200, 4300))
connect(out_data(get_g), find_pin(is_valid, "Object", "Input") or find_pin(is_valid, "WorldContextObject", "Input") or find_pin(is_valid, "", "Input"), "g->valid")
# IsValid pin names vary
obj_pin = find_pin(is_valid, "Object", "Input")
if obj_pin is None:
    for p in bel.list_all_pins(is_valid):
        if "INPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            obj_pin = p
            break
connect(out_data(get_g), obj_pin, "g->isvalid")
brv = tge.add_branch_node()
bel.set_node_pos(brv, pos(-1900, 4200))
connect(find_pin(des, "then", "Output"), find_pin(brv, "execute", "Input"), "des->br")
connect(out_data(is_valid), find_pin(brv, "Condition", "Input"), "valid->cond")
destroy = tge.add_call_function_node("/Script/Engine.Actor:K2_DestroyActor")
bel.set_node_pos(destroy, pos(-1550, 4150))
connect(find_pin(brv, "then", "Output"), find_pin(destroy, "execute", "Input"), "br->destroy")
connect(out_data(get_g), find_pin(destroy, "self", "Input"), "g->destroySelf")
set_null = tge.add_set_member_variable_node("GuestActor")
bel.set_node_pos(set_null, pos(-1200, 4150))
connect(find_pin(destroy, "then", "Output"), find_pin(set_null, "execute", "Input"), "dest->null")
# also from else of branch -> still null
connect(find_pin(brv, "else", "Output"), find_pin(set_null, "execute", "Input"), "else->null")
# Hide OrderBubble
get_bub = tge.add_get_member_variable_node("OrderBubble")
bel.set_node_pos(get_bub, pos(-1200, 4400))
hide = tge.add_call_function_node("/Script/Engine.SceneComponent:SetHiddenInGame")
bel.set_node_pos(hide, pos(-900, 4350))
setdef(find_pin(hide, "NewHidden", "Input"), "true")
connect(find_pin(set_null, "then", "Output"), find_pin(hide, "execute", "Input"), "null->hide")
connect(out_data(get_bub), find_pin(hide, "self", "Input"), "bub->hide")
pr_d = make_print(tge, -600, 4350, "Restaurant UI guest despawn", "1.2")
connect(find_pin(hide, "then", "Output"), find_pin(pr_d, "execute", "Input"), "hide->pr")

# --- SpawnGuestVisual ---
sp = tge.add_custom_event_node("SpawnGuestVisual")
bel.set_node_pos(sp, pos(-2800, 4700))
# Destroy existing first
call_des = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:DestroyGuestVisual")
bel.set_node_pos(call_des, pos(-2500, 4700))
# may fail before compile — compile mid-way later
# Get actor location + offset
get_loc = tge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(get_loc, pos(-2200, 4900))
make_off = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
bel.set_node_pos(make_off, pos(-2200, 5050))
setdef(find_pin(make_off, "X", "Input"), "40.0")
setdef(find_pin(make_off, "Y", "Input"), "40.0")
setdef(find_pin(make_off, "Z", "Input"), "0.0")
add_v = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
bel.set_node_pos(add_v, pos(-1900, 4950))
connect(out_data(get_loc), find_pin(add_v, "A", "Input"), "locA")
connect(out_data(make_off), find_pin(add_v, "B", "Input"), "offB")
make_tf = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeTransform")
bel.set_node_pos(make_tf, pos(-1600, 4950))
connect(out_data(add_v), find_pin(make_tf, "Location", "Input") or find_pin(make_tf, "Translation", "Input"), "loc->tf")

# BeginDeferred spawn
spawn = tge.add_call_function_node("/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass")
bel.set_node_pos(spawn, pos(-1300, 4700))
# Class pin
class_pin = find_pin(spawn, "ActorClass", "Input") or find_pin(spawn, "Class", "Input")
guest_gen = unreal.load_asset(GUEST).generated_class()
if class_pin and guest_gen:
    try:
        class_pin.set_default_object(guest_gen)
        log("spawn class default_object ok")
    except Exception:
        setdef(class_pin, guest_gen.get_path_name())
        log("spawn class path set")
connect(out_data(make_tf), find_pin(spawn, "SpawnTransform", "Input") or find_pin(spawn, "Transform", "Input"), "tf->spawn")

finish = tge.add_call_function_node("/Script/Engine.GameplayStatics:FinishSpawningActor")
bel.set_node_pos(finish, pos(-900, 4700))
connect(out_data(spawn), find_pin(finish, "Actor", "Input"), "spawn->finishActor")
connect(out_data(make_tf), find_pin(finish, "SpawnTransform", "Input") or find_pin(finish, "Transform", "Input"), "tf->finish")

set_g = tge.add_set_member_variable_node("GuestActor")
bel.set_node_pos(set_g, pos(-550, 4700))
connect(out_data(finish), find_pin(set_g, "GuestActor", "Input"), "fin->setG")

# Tint: cast to BP_RestGuest, set TintIndex = TableId-1, SetMaterial on mesh
# Show bubble
get_bub2 = tge.add_get_member_variable_node("OrderBubble")
bel.set_node_pos(get_bub2, pos(-550, 4950))
show = tge.add_call_function_node("/Script/Engine.SceneComponent:SetHiddenInGame")
bel.set_node_pos(show, pos(-250, 4900))
setdef(find_pin(show, "NewHidden", "Input"), "false")
connect(out_data(get_bub2), find_pin(show, "self", "Input"), "bub->show")

pr_s = make_print(tge, 50, 4700, "Restaurant UI guest spawn", "1.2")

# Wire spawn chain exec (Destroy call deferred until compile)
# For now: Sp -> spawn -> finish -> set_g -> show -> print
connect(find_pin(sp, "then", "Output"), find_pin(spawn, "execute", "Input"), "sp->spawn")
connect(find_pin(spawn, "then", "Output"), find_pin(finish, "execute", "Input"), "spawn->finish")
connect(find_pin(finish, "then", "Output"), find_pin(set_g, "execute", "Input"), "finish->set")
connect(find_pin(set_g, "then", "Output"), find_pin(show, "execute", "Input"), "set->show")
connect(find_pin(show, "then", "Output"), find_pin(pr_s, "execute", "Input"), "show->pr")

# After set guest: apply material by TableId
get_tid = tge.add_get_member_variable_node("TableId")
bel.set_node_pos(get_tid, pos(-550, 5200))
eq1 = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq1, pos(-250, 5200))
setdef(find_pin(eq1, "B", "Input"), "1")
connect(out_data(get_tid), find_pin(eq1, "A", "Input"), "tid->eq1")
# We'll apply tint in a follow-up after compile via Cast + SetMaterial — keep spawn robust first

bel.compile_blueprint(tbp)
log("table mid-compile")

# Re-get graph after compile
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))

# Splice SpawnGuestVisual after TrySeat terminals
tryseat = find_custom(tge, "TrySeat")
call_sp = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:SpawnGuestVisual")
bel.set_node_pos(call_sp, pos(3800, 900))
n_sp = splice_after_terminals(tge, tryseat, call_sp, "TrySeat->Spawn")
log("TrySeat splice count=" + str(n_sp))

# Splice DestroyGuestVisual at START of ClearSeat (before clearing flags)
clear = find_custom(tge, "ClearSeat")
call_des2 = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:DestroyGuestVisual")
bel.set_node_pos(call_des2, pos(-200, 1100))
if clear:
    thenp = find_pin(clear, "then", "Output")
    old = list(thenp.list_connected_pins() or []) if thenp else []
    if thenp:
        try:
            thenp.break_pin_links()
        except Exception:
            pass
    connect(thenp, find_pin(call_des2, "execute", "Input"), "Clear->Destroy")
    if old:
        connect(find_pin(call_des2, "then", "Output"), old[0], "Destroy->oldClear")
    log("ClearSeat prepend Destroy")

# ===================== TABLE TICK: bubble patience DrawDebug =====================
# Append RefreshTableBubble at end of Tick chain
tick = find_event(tge, "Tick")
refb = tge.add_custom_event_node("RefreshTableBubble")
bel.set_node_pos(refb, pos(-2800, 5600))
# if not occupied: return (hide already). if occupied: DrawDebugBox color by patience
get_occ = tge.add_get_member_variable_node("bOccupied")
bel.set_node_pos(get_occ, pos(-2500, 5700))
br_occ = tge.add_branch_node()
bel.set_node_pos(br_occ, pos(-2200, 5600))
connect(find_pin(refb, "then", "Output"), find_pin(br_occ, "execute", "Input"), "ref->brocc")
connect(out_data(get_occ), find_pin(br_occ, "Condition", "Input"), "occ->c")
get_pl = tge.add_get_member_variable_node("PatienceLeft")
bel.set_node_pos(get_pl, pos(-1900, 5750))
# ratio approx PatienceLeft/22
div = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:Divide_DoubleDouble")
if div is None:
    div = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:Divide_FloatFloat")
bel.set_node_pos(div, pos(-1600, 5750))
setdef(find_pin(div, "B", "Input"), "22.0")
connect(out_data(get_pl), find_pin(div, "A", "Input"), "pl/22")
# DrawDebugBox at actor+Z
get_loc2 = tge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(get_loc2, pos(-1900, 5600))
make_z = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
bel.set_node_pos(make_z, pos(-1900, 5450))
setdef(find_pin(make_z, "X", "Input"), "0.0")
setdef(find_pin(make_z, "Y", "Input"), "0.0")
setdef(find_pin(make_z, "Z", "Input"), "140.0")
add_z = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
bel.set_node_pos(add_z, pos(-1600, 5550))
connect(out_data(get_loc2), find_pin(add_z, "A", "Input"), "loc")
connect(out_data(make_z), find_pin(add_z, "B", "Input"), "z")
# extent based on patience: MakeVector(30*ratio+5, 8, 8) — simplify fixed extent, color by ratio
# Color: Lerp green->red
make_green = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeColor")
bel.set_node_pos(make_green, pos(-1300, 5900))
setdef(find_pin(make_green, "R", "Input") or find_pin(make_green, "X", "Input"), "0.1")
setdef(find_pin(make_green, "G", "Input") or find_pin(make_green, "Y", "Input"), "0.95")
setdef(find_pin(make_green, "B", "Input") or find_pin(make_green, "Z", "Input"), "0.2")
setdef(find_pin(make_green, "A", "Input") or find_pin(make_green, "W", "Input"), "1.0")
make_red = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeColor")
bel.set_node_pos(make_red, pos(-1300, 6050))
setdef(find_pin(make_red, "R", "Input") or find_pin(make_red, "X", "Input"), "0.95")
setdef(find_pin(make_red, "G", "Input") or find_pin(make_red, "Y", "Input"), "0.1")
setdef(find_pin(make_red, "B", "Input") or find_pin(make_red, "Z", "Input"), "0.1")
setdef(find_pin(make_red, "A", "Input") or find_pin(make_red, "W", "Input"), "1.0")
lerp = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:LinearColorLerp")
if lerp is None:
    lerp = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:VLerp")  # fallback wrong
bel.set_node_pos(lerp, pos(-1000, 5950))
# Alpha = 1 - ratio (low patience -> red). Use 1-ratio
one_m = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble")
if one_m is None:
    one_m = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_FloatFloat")
bel.set_node_pos(one_m, pos(-1300, 5750))
setdef(find_pin(one_m, "A", "Input"), "1.0")
connect(out_data(div), find_pin(one_m, "B", "Input"), "1-ratio")
if lerp:
    connect(out_data(make_green), find_pin(lerp, "A", "Input"), "g")
    connect(out_data(make_red), find_pin(lerp, "B", "Input"), "r")
    connect(out_data(one_m), find_pin(lerp, "Alpha", "Input"), "a")

dbg = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugBox")
bel.set_node_pos(dbg, pos(-700, 5600))
setdef(find_pin(dbg, "Duration", "Input"), "0.0")
setdef(find_pin(dbg, "Thickness", "Input"), "3.0")
extent = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
bel.set_node_pos(extent, pos(-1000, 5550))
setdef(find_pin(extent, "X", "Input"), "35.0")
setdef(find_pin(extent, "Y", "Input"), "10.0")
setdef(find_pin(extent, "Z", "Input"), "8.0")
connect(find_pin(br_occ, "then", "Output"), find_pin(dbg, "execute", "Input"), "occ->dbg")
connect(out_data(add_z), find_pin(dbg, "Center", "Input"), "center")
connect(out_data(extent), find_pin(dbg, "Extent", "Input"), "ext")
if lerp:
    connect(out_data(lerp), find_pin(dbg, "LineColor", "Input") or find_pin(dbg, "Color", "Input"), "col")

# Also DrawDebugString with dish short EN (CJK unreliable on debug)
get_ord = tge.add_get_member_variable_node("CurrentOrder")
bel.set_node_pos(get_ord, pos(-1000, 5400))
dbg_s = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
bel.set_node_pos(dbg_s, pos(-400, 5450))
setdef(find_pin(dbg_s, "Duration", "Input"), "0.0")
connect(find_pin(dbg, "then", "Output"), find_pin(dbg_s, "execute", "Input"), "dbg->str")
connect(out_data(add_z), find_pin(dbg_s, "TextLocation", "Input") or find_pin(dbg_s, "Location", "Input"), "locS")
connect(out_data(get_ord), find_pin(dbg_s, "Text", "Input"), "ord")

# Call RefreshTableBubble from Tick terminal
call_refb = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:RefreshTableBubble")
bel.set_node_pos(call_refb, pos(4200, 2400))
if tick:
    n_tb = splice_after_terminals(tge, tick, call_refb, "Tick->Bubble")
    log("Tick splice bubble=" + str(n_tb))

bel.compile_blueprint(tbp)
eas.save_asset(TBL)
log("TABLE DONE")

# ===================== MANAGER: Order UI =====================
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
purge_disconnected_calls(mge, ("BeginDeferred", "FinishSpawning", "Create", "AddToViewport", "SetText", "SetPercent", "DrawDebug", "SetMaterial", "K2_DestroyActor", "SetActorHidden", "SetHiddenInGame"))

# EnsureSetupOrderUI custom
for old in ("EnsureOrderUI", "RefreshOrderUI"):
    ev = find_custom(mge, old)
    if ev:
        for p in bel.list_all_pins(ev):
            try:
                p.break_pin_links()
            except Exception:
                pass

ens = mge.add_custom_event_node("EnsureOrderUI")
bel.set_node_pos(ens, pos(-3200, 5200))
get_w = mge.add_get_member_variable_node("OrderListWidget")
bel.set_node_pos(get_w, pos(-2900, 5300))
is_v = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
bel.set_node_pos(is_v, pos(-2600, 5300))
opin = find_pin(is_v, "Object", "Input")
if opin is None:
    for p in bel.list_all_pins(is_v):
        if "INPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            opin = p; break
connect(out_data(get_w), opin, "w->valid")
br = mge.add_branch_node()
bel.set_node_pos(br, pos(-2300, 5200))
connect(find_pin(ens, "then", "Output"), find_pin(br, "execute", "Input"), "ens->br")
connect(out_data(is_v), find_pin(br, "Condition", "Input"), "v->c")
# else create
create = mge.add_call_function_node("/Script/UMG.WidgetBlueprintLibrary:Create")
bel.set_node_pos(create, pos(-1950, 5350))
wbp_cls = unreal.load_asset(WBP_LIST).generated_class()
cp = find_pin(create, "Class", "Input") or find_pin(create, "WidgetType", "Input")
if cp and wbp_cls:
    try:
        cp.set_default_object(wbp_cls)
        log("Create class ok")
    except Exception:
        setdef(cp, wbp_cls.get_path_name())
addv = mge.add_call_function_node("/Script/UMG.UserWidget:AddToViewport")
bel.set_node_pos(addv, pos(-1550, 5350))
set_w = mge.add_set_member_variable_node("OrderListWidget")
bel.set_node_pos(set_w, pos(-1200, 5350))
connect(find_pin(br, "else", "Output"), find_pin(create, "execute", "Input"), "else->create")
connect(find_pin(create, "then", "Output"), find_pin(addv, "execute", "Input"), "create->add")
connect(out_data(create), find_pin(addv, "self", "Input"), "w->addself")
connect(find_pin(addv, "then", "Output"), find_pin(set_w, "execute", "Input"), "add->set")
connect(out_data(create), find_pin(set_w, "OrderListWidget", "Input"), "w->var")
pr_ui = make_print(mge, -900, 5350, "Restaurant OrderUI ready", "2.0")
connect(find_pin(set_w, "then", "Output"), find_pin(pr_ui, "execute", "Input"), "set->pr")

# RefreshOrderUI: Ensure + gather tables + Print persistent strip (Chinese)
ref = mge.add_custom_event_node("RefreshOrderUI")
bel.set_node_pos(ref, pos(-3200, 5700))
call_ens = None  # filled after compile

# Build strip via GetAllActorsOfClass Table, ForEach, append strings — complex.
# MVP reliable: always Print two lines from Active* vars is insufficient (2 tables).
# Use GetAllActorsOfClass + two indexed Gets for Table1/Table2 by TableId match — heavy.
# Simpler MVP: PrintString Key=RestOrderStrip with text built from both tables via two GetAll + loops is hard.
# Practical: ForEachLoop macro on tables building via temp vars — still hard in pure remote.
# FALLBACK that works: on each Table Tick when occupied, that table prints its own line with Key=RestOrder_{TableId}
# And Manager Refresh just EnsureOrderUI.

# Table-side order strip line (persistent Print)
# Add to RefreshTableBubble: PrintString Key=RestOrderN

tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
refb = find_custom(tge, "RefreshTableBubble")
# Find dbg_s terminal and append Print strip
# Rebuild a small append on RefreshTableBubble: after occupied branch then, also PrintChinese strip
# Find the DrawDebugString node we added and splice print after it
for n in tge.list_all_nodes():
    if title(n) == "DrawDebugString":
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            # Append Format / Print
            get_tid = tge.add_get_member_variable_node("TableId")
            bel.set_node_pos(get_tid, pos(-100, 5450))
            get_ord = tge.add_get_member_variable_node("CurrentOrder")
            bel.set_node_pos(get_ord, pos(-100, 5550))
            get_pl = tge.add_get_member_variable_node("PatienceLeft")
            bel.set_node_pos(get_pl, pos(-100, 5650))
            # Build string with Append
            # "桌{id} {order} 耐心{pl}"
            to_id = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
            bel.set_node_pos(to_id, pos(150, 5450))
            connect(out_data(get_tid), find_pin(to_id, "InInt", "Input"), "id")
            to_pl = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
            if to_pl is None:
                to_pl = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
            bel.set_node_pos(to_pl, pos(150, 5650))
            connect(out_data(get_pl), find_pin(to_pl, "InDouble", "Input") or find_pin(to_pl, "InFloat", "Input") or find_pin(to_pl, "In", "Input"), "pl")
            # Map order EN to CN via Branch on CurrentDishId
            get_dish = tge.add_get_member_variable_node("CurrentDishId")
            bel.set_node_pos(get_dish, pos(150, 5750))
            eqd = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
            bel.set_node_pos(eqd, pos(400, 5750))
            setdef(find_pin(eqd, "B", "Input"), "1")
            connect(out_data(get_dish), find_pin(eqd, "A", "Input"), "dish")
            # Use Select via Branch for CN name into a temp — Print with two possible strings via Branch
            brd = tge.add_branch_node()
            bel.set_node_pos(brd, pos(400, 5400))
            connect(thenp, find_pin(brd, "execute", "Input"), "dbg->brd")
            connect(out_data(eqd), find_pin(brd, "Condition", "Input"), "eqd")
            # Salad print
            # Append many: "桌" + id + " " + cn + " " + pl + "s"
            ap1 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
            bel.set_node_pos(ap1, pos(700, 5300))
            setdef(find_pin(ap1, "A", "Input"), "\u684c")  # 桌
            connect(out_data(to_id), find_pin(ap1, "B", "Input"), "id")
            ap2 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
            bel.set_node_pos(ap2, pos(1000, 5300))
            connect(out_data(ap1), find_pin(ap2, "A", "Input"), "a")
            setdef(find_pin(ap2, "B", "Input"), " \u756a\u8304\u6c99\u62c9 ")  # 番茄沙拉
            ap3 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
            bel.set_node_pos(ap3, pos(1300, 5300))
            connect(out_data(ap2), find_pin(ap3, "A", "Input"), "a2")
            connect(out_data(to_pl), find_pin(ap3, "B", "Input"), "pl")
            pr1 = make_print(tge, 1600, 5280, "x", "0.0", key="RestOrderLine")
            # Need dynamic key per table — use Append key
            # For Key pin use "RestOrder" + id
            key_ap = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
            bel.set_node_pos(key_ap, pos(1300, 5150))
            setdef(find_pin(key_ap, "A", "Input"), "RestOrder")
            connect(out_data(to_id), find_pin(key_ap, "B", "Input"), "keyid")
            connect(out_data(key_ap), find_pin(pr1, "Key", "Input"), "key")
            connect(out_data(ap3), find_pin(pr1, "InString", "Input"), "str")
            connect(find_pin(brd, "then", "Output"), find_pin(pr1, "execute", "Input"), "salad")
            # Stew branch
            ap1b = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
            bel.set_node_pos(ap1b, pos(700, 5550))
            setdef(find_pin(ap1b, "A", "Input"), "\u684c")
            connect(out_data(to_id), find_pin(ap1b, "B", "Input"), "id2")
            ap2b = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
            bel.set_node_pos(ap2b, pos(1000, 5550))
            connect(out_data(ap1b), find_pin(ap2b, "A", "Input"), "a")
            setdef(find_pin(ap2b, "B", "Input"), " \u7096\u83dc ")
            ap3b = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
            bel.set_node_pos(ap3b, pos(1300, 5550))
            connect(out_data(ap2b), find_pin(ap3b, "A", "Input"), "a2")
            connect(out_data(to_pl), find_pin(ap3b, "B", "Input"), "pl2")
            pr2 = make_print(tge, 1600, 5530, "x", "0.0", key="RestOrderLine")
            connect(out_data(key_ap), find_pin(pr2, "Key", "Input"), "key2")
            connect(out_data(ap3b), find_pin(pr2, "InString", "Input"), "str2")
            connect(find_pin(brd, "else", "Output"), find_pin(pr2, "execute", "Input"), "stew")
            log("strip print wired on bubble refresh")
            break

# When not occupied, clear strip key — on DestroyGuestVisual end
des = find_custom(tge, "DestroyGuestVisual")
# find terminal print and add clear prints for RestOrder1 and RestOrder2 — clear this table's key
# Append after DestroyGuestVisual terminal
if des:
    call_clear_print = make_print(tge, 200, 4500, "", "0.0", key="RestOrderClear")
    # Better: build key RestOrder+TableId empty
    get_tid2 = tge.add_get_member_variable_node("TableId")
    bel.set_node_pos(get_tid2, pos(-200, 4550))
    to_id2 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
    bel.set_node_pos(to_id2, pos(0, 4550))
    connect(out_data(get_tid2), find_pin(to_id2, "InInt", "Input"), "id")
    key_ap2 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(key_ap2, pos(250, 4550))
    setdef(find_pin(key_ap2, "A", "Input"), "RestOrder")
    connect(out_data(to_id2), find_pin(key_ap2, "B", "Input"), "kid")
    pr_clear = make_print(tge, 550, 4500, " ", "0.0", key="RestOrderX")
    connect(out_data(key_ap2), find_pin(pr_clear, "Key", "Input"), "ckey")
    n = splice_after_terminals(tge, des, pr_clear, "Des->ClearPrint")
    log("clear print splice=" + str(n))

bel.compile_blueprint(tbp)

# Manager: wire EnsureOrderUI + RefreshOrderUI call from RestaurantTick
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
bel.compile_blueprint(mbp)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))

call_ens = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
bel.set_node_pos(call_ens, pos(-2800, 5700))
ref = find_custom(mge, "RefreshOrderUI")
if ref:
    connect(find_pin(ref, "then", "Output"), find_pin(call_ens, "execute", "Input"), "ref->ens")
    # Title print for strip header
    pr_h = make_print(mge, -2400, 5700, "\u8ba2\u5355", "0.0", key="RestOrderHeader")  # 订单
    connect(find_pin(call_ens, "then", "Output"), find_pin(pr_h, "execute", "Input"), "ens->hdr")

# Call RefreshOrderUI from RestaurantTick end
rt = find_custom(mge, "RestaurantTick")
call_ref = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:RefreshOrderUI")
bel.set_node_pos(call_ref, pos(3600, 400))
if rt:
    n = splice_after_terminals(mge, rt, call_ref, "Tick->RefreshUI")
    log("RestaurantTick splice=" + str(n))

# Also Ensure on BeginPlay
bpn = find_event(mge, "BeginPlay")
call_ens2 = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
bel.set_node_pos(call_ens2, pos(800, -200))
if bpn:
    n = splice_after_terminals(mge, bpn, call_ens2, "BP->EnsureUI")
    log("BeginPlay splice=" + str(n))

bel.compile_blueprint(mbp)
eas.save_asset(MGR)
bel.compile_blueprint(tbp)
eas.save_asset(TBL)
bel.compile_blueprint(gbp)
eas.save_asset(GUEST)
eas.save_asset(WBP_LIST)
try:
    eas.save_asset("/Game/Farm/UI/WBP_RestOrderBubble")
except Exception:
    pass

# Save level
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    log("level " + str(e))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# Error report
for path, label in ((TBL, "Table"), (MGR, "Manager"), (GUEST, "Guest")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    try:
        errs = list(ge.list_nodes_with_errors() or [])
        log("{} errors={}".format(label, len(errs)))
        for n in errs[:12]:
            log("  ERR " + title(n))
    except Exception as e:
        log("{} errlist {}".format(label, e))

log("ALL_DONE")
# write report
import json
out = unreal.Paths.project_saved_dir() + "RestaurantUI_wire_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("report " + out)
