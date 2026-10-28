# -*- coding: utf-8 -*-
"""Repair both dish paths -> Spawn; tint via GetComponentByClass; finish Manager UI; strip; compile."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"
WBP_LIST = "/Game/Farm/UI/WBP_RestOrderList"
MI_RED = "/Game/Farm/Restaurant/Guests/MI_GuestRed"
MI_BLUE = "/Game/Farm/Restaurant/Guests/MI_GuestBlue"
MI_GREEN = "/Game/Farm/Restaurant/Guests/MI_GuestGreen"

R = {"steps": []}

def log(m):
    unreal.log("[UI_W3] " + str(m)); print("[UI_W3] " + str(m)); R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Return Value", "GuestActor", "OrderListWidget", "GuestMesh",
                 "bOccupied", "CurrentOrder", "CurrentDishId", "PatienceLeft", "TableId", "TintIndex"):
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
        log("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok)); return ok

def setdef(pin, val):
    if not pin: return False
    try:
        pin.set_pin_value(str(val)); return True
    except Exception:
        try:
            pin.set_default_value(str(val)); return True
        except Exception as e:
            log("setdef " + str(e)[:80]); return False

def make_print(ge, x, y, text, dur="1.5", key=""):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    if key: setdef(find_pin(pr, "Key", "Input"), key)
    return pr

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

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

def walk_then(start, max_d=40):
    thenp = find_pin(start, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen = []; ids = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in ids or d > max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then", "else", "Completed", "LoopBody"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d + 1))
    return seen

def dump(start, label):
    chain = [title(n) for n in walk_then(start, 40)]
    log(label + ": " + " -> ".join(chain[:30]))
    R[label] = chain

# ========== TABLE: both PrintString success -> Spawn ==========
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
tryseat = find_custom(tge, "TrySeat")

spawn_call = None
for n in tge.list_all_nodes():
    if title(n) == "SpawnGuestVisual" and n.get_class().get_name() == "K2Node_CallFunction":
        spawn_call = n; break

# Find PrintString nodes in TrySeat with empty then OR already to Spawn — wire ALL TrySeat-terminal prints to Spawn
prints = []
if tryseat:
    for n in walk_then(tryseat, 40):
        if title(n) == "PrintString":
            thenp = find_pin(n, "then", "Output")
            tgts = [title(c.get_owning_node()) for c in (thenp.list_connected_pins() or [])] if thenp else []
            prints.append((n, tgts))
            log("TrySeat Print then->" + str(tgts))

if spawn_call:
    exe = find_pin(spawn_call, "execute", "Input")
    for n, tgts in prints:
        if "SpawnGuestVisual" not in tgts:
            connect(find_pin(n, "then", "Output"), exe, "Print->Spawn")

# ========== SpawnGuestVisual: append tint via GetComponentByClass ==========
sp_ev = find_custom(tge, "SpawnGuestVisual")
term = None
if sp_ev:
    for n in walk_then(sp_ev, 30):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            term = n
log("spawn term=" + (title(term) if term else "None"))

# Avoid duplicate tint if already present
already_tint = sp_ev and any("SetMaterial" in title(n) or "GetComponentByClass" in title(n) for n in walk_then(sp_ev, 40))
if term and not already_tint:
    get_g = tge.add_get_member_variable_node("GuestActor")
    bel.set_node_pos(get_g, pos(400, 4800))
    getc = tge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
    bel.set_node_pos(getc, pos(700, 4800))
    # ComponentClass = SkeletalMeshComponent
    cp = find_pin(getc, "ComponentClass", "Input")
    sk_cls = unreal.load_object(None, "/Script/Engine.SkeletalMeshComponent")
    if cp and sk_cls:
        try:
            cp.set_default_object(sk_cls); log("skel class set")
        except Exception as e:
            setdef(cp, "/Script/Engine.SkeletalMeshComponent"); log("skel path " + str(e)[:40])
    connect(out_data(get_g), find_pin(getc, "self", "Input"), "g->getc")

    get_tid = tge.add_get_member_variable_node("TableId")
    bel.set_node_pos(get_tid, pos(400, 5000))
    eq1 = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(eq1, pos(700, 5000))
    setdef(find_pin(eq1, "B", "Input"), "1")
    connect(out_data(get_tid), find_pin(eq1, "A", "Input"), "tid==1")
    br1 = tge.add_branch_node()
    bel.set_node_pos(br1, pos(1000, 4750))
    connect(find_pin(term, "then", "Output"), find_pin(br1, "execute", "Input"), "term->br1")
    connect(out_data(eq1), find_pin(br1, "Condition", "Input"), "eq1")

    def make_sm(ge, x, y, mi_path):
        sm = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
        bel.set_node_pos(sm, pos(x, y))
        setdef(find_pin(sm, "ElementIndex", "Input") or find_pin(sm, "Index", "Input"), "1")
        mi = unreal.load_asset(mi_path)
        mp = find_pin(sm, "Material", "Input")
        if mp and mi:
            try: mp.set_default_object(mi)
            except Exception: setdef(mp, mi.get_path_name())
        # self = GetComponentByClass return — connect later
        return sm

    sm_r = make_sm(tge, 1350, 4600, MI_RED)
    sm_b = make_sm(tge, 1350, 4850, MI_BLUE)
    sm_g = make_sm(tge, 1350, 5100, MI_GREEN)
    for sm in (sm_r, sm_b, sm_g):
        connect(out_data(getc), find_pin(sm, "self", "Input"), "mesh->sm")

    eq2 = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(eq2, pos(1000, 5000))
    setdef(find_pin(eq2, "B", "Input"), "2")
    connect(out_data(get_tid), find_pin(eq2, "A", "Input"), "tid==2")
    br2 = tge.add_branch_node()
    bel.set_node_pos(br2, pos(1200, 4900))

    connect(find_pin(br1, "then", "Output"), find_pin(sm_r, "execute", "Input"), "->red")
    connect(find_pin(br1, "else", "Output"), find_pin(br2, "execute", "Input"), "else->br2")
    connect(out_data(eq2), find_pin(br2, "Condition", "Input"), "eq2")
    connect(find_pin(br2, "then", "Output"), find_pin(sm_b, "execute", "Input"), "->blue")
    connect(find_pin(br2, "else", "Output"), find_pin(sm_g, "execute", "Input"), "->green")
    pr = make_print(tge, 1700, 4850, "Restaurant UI guest tint", "1.0")
    connect(find_pin(sm_r, "then", "Output"), find_pin(pr, "execute", "Input"), "r->pr")
    connect(find_pin(sm_b, "then", "Output"), find_pin(pr, "execute", "Input"), "b->pr")
    connect(find_pin(sm_g, "then", "Output"), find_pin(pr, "execute", "Input"), "g->pr")
    log("tint wired")

# ========== Guest ApplyTint self (BeginPlay) using GuestMesh ==========
gbp = unreal.load_asset(GUEST)
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
# Clear orphan GetActorOfClass / SetMaterial from probe
for n in list(gge.list_all_nodes()):
    if n.get_class().get_name() == "K2Node_CallFunction":
        exe = find_pin(n, "execute", "Input")
        has_in = bool(exe and list(exe.list_connected_pins() or []))
        # also pure nodes
        if title(n) in ("GetActorOfClass",) or (not has_in and title(n) in ("SetMaterial", "GetComponentByClass")):
            for p in bel.list_all_pins(n):
                try: p.break_pin_links()
                except Exception: pass
            log("orphan break " + title(n))

at = find_custom(gge, "ApplyTint")
if at is None or len(walk_then(at, 10)) == 0:
    if at:
        for p in bel.list_all_pins(at):
            try: p.break_pin_links()
            except Exception: pass
    else:
        at = gge.add_custom_event_node("ApplyTint")
        bel.set_node_pos(at, pos(-800, 200))
    get_ti = gge.add_get_member_variable_node("TintIndex")
    bel.set_node_pos(get_ti, pos(-500, 300))
    get_mesh = gge.add_get_member_variable_node("GuestMesh")
    bel.set_node_pos(get_mesh, pos(-500, 450))
    eq1 = gge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(eq1, pos(-250, 250))
    setdef(find_pin(eq1, "B", "Input"), "1")
    connect(out_data(get_ti), find_pin(eq1, "A", "Input"), "ti==1")
    br1 = gge.add_branch_node()
    bel.set_node_pos(br1, pos(0, 200))
    connect(find_pin(at, "then", "Output"), find_pin(br1, "execute", "Input"), "at->br1")
    connect(out_data(eq1), find_pin(br1, "Condition", "Input"), "eq1")

    def gsm(ge, x, y, mi_path, mesh_get):
        sm = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
        bel.set_node_pos(sm, pos(x, y))
        setdef(find_pin(sm, "ElementIndex", "Input") or find_pin(sm, "Index", "Input"), "1")
        mi = unreal.load_asset(mi_path)
        mp = find_pin(sm, "Material", "Input")
        if mp and mi:
            try: mp.set_default_object(mi)
            except Exception: setdef(mp, mi.get_path_name())
        connect(out_data(mesh_get), find_pin(sm, "self", "Input"), "mesh")
        return sm

    sm_r = gsm(gge, 350, 150, MI_RED, get_mesh)
    sm_b = gsm(gge, 350, 350, MI_BLUE, get_mesh)
    sm_g = gsm(gge, 350, 550, MI_GREEN, get_mesh)
    eq2 = gge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(eq2, pos(0, 400))
    setdef(find_pin(eq2, "B", "Input"), "2")
    connect(out_data(get_ti), find_pin(eq2, "A", "Input"), "ti==2")
    br2 = gge.add_branch_node()
    bel.set_node_pos(br2, pos(150, 350))
    connect(find_pin(br1, "then", "Output"), find_pin(sm_r, "execute", "Input"), "red")
    connect(find_pin(br1, "else", "Output"), find_pin(br2, "execute", "Input"), "else")
    connect(out_data(eq2), find_pin(br2, "Condition", "Input"), "eq2")
    connect(find_pin(br2, "then", "Output"), find_pin(sm_b, "execute", "Input"), "blue")
    connect(find_pin(br2, "else", "Output"), find_pin(sm_g, "execute", "Input"), "green")
    log("Guest ApplyTint built")

# BeginPlay -> ApplyTint; also set default TintIndex from a random? leave 0=green; Table overrides via SetMaterial
bp_g = find_event(gge, "BeginPlay")
if bp_g and not any("ApplyTint" in title(n) for n in walk_then(bp_g, 10)):
    call_at = gge.add_call_function_node("/Game/Farm/Restaurant/BP_RestGuest.BP_RestGuest_C:ApplyTint")
    bel.set_node_pos(call_at, pos(-400, 0))
    thenp = find_pin(bp_g, "then", "Output")
    old = list(thenp.list_connected_pins() or []) if thenp else []
    if thenp:
        try: thenp.break_pin_links()
        except Exception: pass
    connect(thenp, find_pin(call_at, "execute", "Input"), "BP->Apply")
    if old:
        connect(find_pin(call_at, "then", "Output"), old[0], "Apply->old")

bel.compile_blueprint(gbp)
eas.save_asset(GUEST)

# ========== RefreshTableBubble strip if missing ==========
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
refb = find_custom(tge, "RefreshTableBubble")
dump(refb, "bubble_before")
has_print = refb and any(title(n) == "PrintString" for n in walk_then(refb, 40))
if refb and not has_print:
    # find occupied-branch then terminal
    term = None
    for n in walk_then(refb, 40):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            term = n
    if term is None:
        for n in walk_then(refb, 40):
            if title(n) in ("DrawDebugString", "DrawDebugBox"):
                term = n
    if term:
        get_tid = tge.add_get_member_variable_node("TableId")
        bel.set_node_pos(get_tid, pos(0, 5800))
        get_pl = tge.add_get_member_variable_node("PatienceLeft")
        bel.set_node_pos(get_pl, pos(0, 5900))
        get_dish = tge.add_get_member_variable_node("CurrentDishId")
        bel.set_node_pos(get_dish, pos(0, 6000))
        to_id = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
        bel.set_node_pos(to_id, pos(250, 5800))
        connect(out_data(get_tid), find_pin(to_id, "InInt", "Input"), "id")
        to_pl = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
        if to_pl is None:
            to_pl = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
        bel.set_node_pos(to_pl, pos(250, 5900))
        pin_pl = find_pin(to_pl, "InDouble", "Input") or find_pin(to_pl, "InFloat", "Input")
        if pin_pl is None:
            for p in bel.list_all_pins(to_pl):
                if "INPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
                    pin_pl = p; break
        connect(out_data(get_pl), pin_pl, "pl")
        eqd = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
        bel.set_node_pos(eqd, pos(250, 6000))
        setdef(find_pin(eqd, "B", "Input"), "1")
        connect(out_data(get_dish), find_pin(eqd, "A", "Input"), "dish")
        key_ap = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(key_ap, pos(500, 5700))
        setdef(find_pin(key_ap, "A", "Input"), "RestOrder")
        connect(out_data(to_id), find_pin(key_ap, "B", "Input"), "kid")
        brd = tge.add_branch_node()
        bel.set_node_pos(brd, pos(500, 5850))
        connect(find_pin(term, "then", "Output"), find_pin(brd, "execute", "Input"), "term->brd")
        connect(out_data(eqd), find_pin(brd, "Condition", "Input"), "eqd")
        # salad
        a1 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(a1, pos(800, 5750))
        setdef(find_pin(a1, "A", "Input"), "\u684c")
        connect(out_data(to_id), find_pin(a1, "B", "Input"), "id")
        a2 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(a2, pos(1100, 5750))
        connect(out_data(a1), find_pin(a2, "A", "Input"), "a")
        setdef(find_pin(a2, "B", "Input"), " \u756a\u8304\u6c99\u62c9 ")
        a3 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(a3, pos(1400, 5750))
        connect(out_data(a2), find_pin(a3, "A", "Input"), "a2")
        connect(out_data(to_pl), find_pin(a3, "B", "Input"), "pl")
        pr1 = make_print(tge, 1700, 5750, "x", "0.0", key="RestOrderX")
        connect(out_data(key_ap), find_pin(pr1, "Key", "Input"), "k")
        connect(out_data(a3), find_pin(pr1, "InString", "Input"), "s")
        connect(find_pin(brd, "then", "Output"), find_pin(pr1, "execute", "Input"), "salad")
        # stew
        b1 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(b1, pos(800, 6000))
        setdef(find_pin(b1, "A", "Input"), "\u684c")
        connect(out_data(to_id), find_pin(b1, "B", "Input"), "id")
        b2 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(b2, pos(1100, 6000))
        connect(out_data(b1), find_pin(b2, "A", "Input"), "a")
        setdef(find_pin(b2, "B", "Input"), " \u7096\u83dc ")
        b3 = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(b3, pos(1400, 6000))
        connect(out_data(b2), find_pin(b3, "A", "Input"), "a2")
        connect(out_data(to_pl), find_pin(b3, "B", "Input"), "pl")
        pr2 = make_print(tge, 1700, 6000, "x", "0.0", key="RestOrderX")
        connect(out_data(key_ap), find_pin(pr2, "Key", "Input"), "k2")
        connect(out_data(b3), find_pin(pr2, "InString", "Input"), "s2")
        connect(find_pin(brd, "else", "Output"), find_pin(pr2, "execute", "Input"), "stew")
        log("strip added")

# Tick -> RefreshTableBubble
tick = find_event(tge, "Tick")
if tick and not any("RefreshTableBubble" in title(n) for n in walk_then(tick, 50)):
    call_refb = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:RefreshTableBubble")
    bel.set_node_pos(call_refb, pos(4500, 2400))
    terms = []
    for n in walk_then(tick, 50):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            if title(n) not in ("PayAndClear", "TimeoutLeave", "ClearSeat", "SpawnGuestVisual", "DestroyGuestVisual"):
                terms.append(n)
    log("Tick terminals: " + str([title(t) for t in terms]))
    for t in terms[:3]:
        connect(find_pin(t, "then", "Output"), find_pin(call_refb, "execute", "Input"), "Tick->" + title(t))

# Fix DrawDebugString Text if empty
for n in tge.list_all_nodes():
    if title(n) == "DrawDebugString":
        tp = find_pin(n, "Text", "Input")
        if tp and not list(tp.list_connected_pins() or []):
            get_dish = tge.add_get_member_variable_node("CurrentDishId")
            bel.set_node_pos(get_dish, pos(-900, 5400))
            conv = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
            bel.set_node_pos(conv, pos(-650, 5400))
            connect(out_data(get_dish), find_pin(conv, "InInt", "Input"), "dish")
            # prefix "Order#"
            ap = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
            bel.set_node_pos(ap, pos(-400, 5400))
            setdef(find_pin(ap, "A", "Input"), "Order#")
            connect(out_data(conv), find_pin(ap, "B", "Input"), "n")
            connect(out_data(ap), tp, "txt")
            log("fixed DrawDebugString")

bel.compile_blueprint(tbp)
eas.save_asset(TBL)

# ========== MANAGER EnsureOrderUI + RefreshOrderUI ==========
mbp = unreal.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))

# Ensure var
names = [str(n) for n in bel.list_member_variable_names(mbp, False)]
if "OrderListWidget" not in names:
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/UMG.UserWidget")')
    bel.add_member_variable(mbp, "OrderListWidget", p)
    log("added OrderListWidget")

ens = find_custom(mge, "EnsureOrderUI")
need_ens = ens is None or len(walk_then(ens, 15)) == 0
if need_ens:
    if ens:
        for p in bel.list_all_pins(ens):
            try: p.break_pin_links()
            except Exception: pass
    else:
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
    connect(out_data(get_w), opin, "w->v")
    br = mge.add_branch_node()
    bel.set_node_pos(br, pos(-2300, 5200))
    connect(find_pin(ens, "then", "Output"), find_pin(br, "execute", "Input"), "ens->br")
    connect(out_data(is_v), find_pin(br, "Condition", "Input"), "v")
    create = mge.add_call_function_node("/Script/UMG.WidgetBlueprintLibrary:Create")
    bel.set_node_pos(create, pos(-1950, 5350))
    wbp_cls = unreal.load_asset(WBP_LIST).generated_class()
    cp = find_pin(create, "Class", "Input") or find_pin(create, "WidgetType", "Input")
    if cp and wbp_cls:
        try: cp.set_default_object(wbp_cls); log("Create class ok")
        except Exception: setdef(cp, wbp_cls.get_path_name())
    addv = mge.add_call_function_node("/Script/UMG.UserWidget:AddToViewport")
    bel.set_node_pos(addv, pos(-1550, 5350))
    set_w = mge.add_set_member_variable_node("OrderListWidget")
    bel.set_node_pos(set_w, pos(-1200, 5350))
    connect(find_pin(br, "else", "Output"), find_pin(create, "execute", "Input"), "else->create")
    connect(find_pin(create, "then", "Output"), find_pin(addv, "execute", "Input"), "c->add")
    connect(out_data(create), find_pin(addv, "self", "Input"), "w->self")
    connect(find_pin(addv, "then", "Output"), find_pin(set_w, "execute", "Input"), "add->set")
    connect(out_data(create), find_pin(set_w, "OrderListWidget", "Input"), "w->var")
    pr = make_print(mge, -900, 5350, "Restaurant OrderUI ready", "2.0")
    connect(find_pin(set_w, "then", "Output"), find_pin(pr, "execute", "Input"), "set->pr")
    # also show header via Print Key
    log("EnsureOrderUI built")

ref = find_custom(mge, "RefreshOrderUI")
if ref is None:
    ref = mge.add_custom_event_node("RefreshOrderUI")
    bel.set_node_pos(ref, pos(-3200, 5700))

# Mid-compile so EnsureOrderUI is callable
bel.compile_blueprint(mbp)

mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
ens = find_custom(mge, "EnsureOrderUI")
ref = find_custom(mge, "RefreshOrderUI")

if ref and not any("EnsureOrderUI" in title(n) for n in walk_then(ref, 15)):
    call_ens = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
    bel.set_node_pos(call_ens, pos(-2800, 5700))
    thenp = find_pin(ref, "then", "Output")
    old = list(thenp.list_connected_pins() or []) if thenp else []
    if thenp:
        try: thenp.break_pin_links()
        except Exception: pass
    connect(thenp, find_pin(call_ens, "execute", "Input"), "ref->ens")
    pr_h = make_print(mge, -2400, 5700, "\u8ba2\u5355", "0.0", key="RestOrderHeader")
    if old:
        connect(find_pin(call_ens, "then", "Output"), old[0], "ens->old")
    else:
        connect(find_pin(call_ens, "then", "Output"), find_pin(pr_h, "execute", "Input"), "ens->hdr")
    log("Refresh->Ensure")

rt = find_custom(mge, "RestaurantTick")
if rt and not any("RefreshOrderUI" in title(n) for n in walk_then(rt, 50)):
    call_ref = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:RefreshOrderUI")
    bel.set_node_pos(call_ref, pos(3800, 400))
    terms = [n for n in walk_then(rt, 50) if (find_pin(n, "then", "Output") and not list(find_pin(n, "then", "Output").list_connected_pins() or []))]
    log("RT terminals " + str([title(t) for t in terms]))
    for t in terms[:4]:
        connect(find_pin(t, "then", "Output"), find_pin(call_ref, "execute", "Input"), "RT->" + title(t))

bpn = find_event(mge, "BeginPlay")
if bpn and not any("EnsureOrderUI" in title(n) for n in walk_then(bpn, 40)):
    call_ens2 = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
    bel.set_node_pos(call_ens2, pos(1400, -200))
    terms = [n for n in walk_then(bpn, 40) if (find_pin(n, "then", "Output") and not list(find_pin(n, "then", "Output").list_connected_pins() or []))]
    for t in terms[:3]:
        connect(find_pin(t, "then", "Output"), find_pin(call_ens2, "execute", "Input"), "BP->" + title(t))
    log("BP Ensure terminals=" + str(len(terms)))

bel.compile_blueprint(mbp)
eas.save_asset(MGR)
bel.compile_blueprint(tbp)
eas.save_asset(TBL)
bel.compile_blueprint(gbp)
eas.save_asset(GUEST)
try:
    eas.save_asset(WBP_LIST)
    eas.save_asset("/Game/Farm/UI/WBP_RestOrderBubble")
except Exception:
    pass
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level " + str(e))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# Final dumps + errors
for path, key in ((TBL, "table"), (MGR, "mgr"), (GUEST, "guest")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    try:
        errs = [title(n) for n in (ge.list_nodes_with_errors() or [])]
        R[key + "_err"] = errs[:20]
        log("{} err={} {}".format(key, len(errs), errs[:8]))
    except Exception as e:
        R[key + "_err"] = [str(e)]

tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(TBL), "EventGraph"))
dump(find_custom(tge, "TrySeat"), "tryseat")
dump(find_custom(tge, "SpawnGuestVisual"), "spawn")
dump(find_custom(tge, "DestroyGuestVisual"), "destroy")
dump(find_custom(tge, "ClearSeat"), "clear")
dump(find_custom(tge, "RefreshTableBubble"), "bubble")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(MGR), "EventGraph"))
dump(find_custom(mge, "EnsureOrderUI"), "ensure")
dump(find_custom(mge, "RefreshOrderUI"), "refresh")

out = unreal.Paths.project_saved_dir() + "RestaurantUI_wire3_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("report " + out)
log("ALL_DONE")
