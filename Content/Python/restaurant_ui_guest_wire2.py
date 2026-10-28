# -*- coding: utf-8 -*-
"""Continue: finish Manager UI, tint guests, fix TrySeat-only-success spawn, compile report."""
import unreal
import json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"
WBP_LIST = "/Game/Farm/UI/WBP_RestOrderList"
MI_RED = "/Game/Farm/Restaurant/Guests/MI_GuestRed"
MI_BLUE = "/Game/Farm/Restaurant/Guests/MI_GuestBlue"
MI_GREEN = "/Game/Farm/Restaurant/Guests/MI_GuestGreen"

R = {"steps": [], "errors": [], "tryseat": [], "table_err": [], "mgr_err": [], "guest_err": []}

def log(m):
    unreal.log("[UI_WIRE2] " + str(m))
    print("[UI_WIRE2] " + str(m))
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
    for name in ("ReturnValue", "Return Value", "GuestActor", "OrderListWidget", "GuestMesh",
                 "bOccupied", "CurrentOrder", "CurrentDishId", "PatienceLeft", "TableId",
                 "TintIndex", "bIsOpenBusiness"):
        p = find_pin(node, name, "Output")
        if p:
            return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n = str(p.get_pin_name()).lower()
            if n not in ("outputdelegate", "then", "else", "completed", "loopbody"):
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
    if key:
        setdef(find_pin(pr, "Key", "Input"), key)
    return pr

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

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

def walk_then(start_node, max_d=40):
    thenp = find_pin(start_node, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen = []; seen_ids = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in seen_ids or d > max_d:
            continue
        seen_ids.add(id(cur)); seen.append(cur)
        for pn in ("then", "else", "Completed", "LoopBody"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d + 1))
    return seen

def dump_chain(start, label, maxn=40):
    nodes = walk_then(start, 50)
    R[label] = [title(n) for n in nodes[:maxn]]
    log(label + " chain: " + " -> ".join(R[label][:25]))

# ========== Inspect TrySeat: who calls SpawnGuestVisual? ==========
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
tryseat = find_custom(tge, "TrySeat")
dump_chain(tryseat, "tryseat")

# Find SpawnGuestVisual call nodes and who feeds them
spawn_calls = []
for n in tge.list_all_nodes():
    if "SpawnGuestVisual" in title(n) and n.get_class().get_name() == "K2Node_CallFunction":
        spawn_calls.append(n)
        exe = find_pin(n, "execute", "Input")
        preds = []
        if exe:
            for c in exe.list_connected_pins() or []:
                preds.append(title(c.get_owning_node()))
        log("SpawnGuestVisual call preds=" + str(preds))

# Ideal: only after successful seat PrintString. If Branch else also calls spawn, break else.
# Look for Branch nodes that feed SpawnGuestVisual — if both then and else feed, keep then only.
for n in spawn_calls:
    exe = find_pin(n, "execute", "Input")
    if not exe:
        continue
    for c in list(exe.list_connected_pins() or []):
        pred = c.get_owning_node()
        # If pred is PrintString with fail message, disconnect
        # Inspect PrintString InString default
        if title(pred) == "PrintString":
            isp = find_pin(pred, "InString", "Input")
            val = ""
            try:
                val = isp.get_default_as_string() if isp else ""
            except Exception:
                try:
                    val = str(isp.get_default_value()) if isp else ""
                except Exception:
                    val = ""
            log("pred PrintString text=" + repr(val)[:80])
            # Keep Chinese success messages; disconnect if looks like fail/occupied
            fail_keys = ("fail", "occupied", "\u5df2\u5360", "\u5931\u8d25", "closed", "\u5173\u95ed")
            if any(k in val.lower() for k in fail_keys if isinstance(k, str)):
                try:
                    c.break_link_to(exe) if hasattr(c, "break_link_to") else None
                except Exception:
                    pass
                try:
                    # break all links on this connection from pred then
                    thenp = find_pin(pred, "then", "Output")
                    if thenp:
                        # disconnect only this spawn target — break_pin_links then reconnect other?
                        # Safer: break exe pin of spawn and re-wire only success path later
                        pass
                except Exception:
                    pass

# Better approach: break ALL inputs to SpawnGuestVisual call, then wire ONLY from the last success PrintString.
# Find success prints in TrySeat chain.
success_prints = []
if tryseat:
    for n in walk_then(tryseat, 50):
        if title(n) == "PrintString":
            isp = find_pin(n, "InString", "Input")
            val = ""
            try:
                val = isp.get_default_as_string() if isp else ""
            except Exception:
                try:
                    val = str(isp.get_default_value())
                except Exception:
                    val = ""
            log("TrySeat Print: " + repr(val)[:100])
            R["tryseat_prints"] = R.get("tryseat_prints", []) + [val]
            # Success typically mentions seat/order/guest \u5165\u5ea7 or dish
            if any(x in val for x in ("\u5165\u5ea7", "Tomato", "Stew", "\u6c99\u62c9", "\u7096", "order", "Order", "\u70b9\u9910")):
                success_prints.append(n)
            if "\u6210\u529f" in val or "seated" in val.lower() or "Sit" in val:
                success_prints.append(n)

# Break all exec into SpawnGuestVisual calls, reconnect from success terminals only
for n in spawn_calls:
    exe = find_pin(n, "execute", "Input")
    if exe:
        try:
            exe.break_pin_links()
            log("broke SpawnGuestVisual inputs")
        except Exception as e:
            log("break fail " + str(e))

# Prefer last PrintString in chain that is NOT an early exit — use last node before Spawn was spliced.
# Heuristic: find PrintString nodes whose then was empty before we spliced; now connected to Spawn.
# Re-wire: only from nodes that set bOccupied or set CurrentOrder near end.
set_nodes = []
if tryseat:
    for n in walk_then(tryseat, 50):
        t = title(n)
        if "Set " in t or t.startswith("Set"):
            set_nodes.append(t)
            log("TrySeat set: " + t)
R["tryseat_sets"] = set_nodes

# Wire SpawnGuestVisual after the LAST node in TrySeat walk that is PrintString OR Set bOccupied
last_good = None
if tryseat:
    chain = walk_then(tryseat, 50)
    for n in chain:
        t = title(n)
        if t == "PrintString" or "bOccupied" in t or "CurrentOrder" in t or "PatienceLeft" in t:
            # skip if it's the SpawnGuestVisual itself
            last_good = n
    if last_good is None and chain:
        last_good = chain[-1]
    log("last_good=" + (title(last_good) if last_good else "None"))

if spawn_calls and last_good:
    # If last_good is already SpawnGuestVisual, use previous
    if "SpawnGuestVisual" in title(last_good):
        chain = walk_then(tryseat, 50)
        for n in reversed(chain):
            if "SpawnGuestVisual" not in title(n):
                last_good = n
                break
    thenp = find_pin(last_good, "then", "Output")
    # If last_good then already goes elsewhere (old Clear etc), insert: break then, connect to Spawn, Spawn then to old
    old_targets = list(thenp.list_connected_pins() or []) if thenp else []
    # remove only links to SpawnGuestVisual from others already broken on exe side
    connect(thenp, find_pin(spawn_calls[0], "execute", "Input"), "success->Spawn")
    # If old targets exist that are NOT spawn, keep them from Spawn then
    for ot in old_targets:
        own = ot.get_owning_node()
        if "SpawnGuestVisual" not in title(own):
            connect(find_pin(spawn_calls[0], "then", "Output"), ot, "Spawn->old")

# ========== Apply tint after spawn ==========
# Find SpawnGuestVisual custom event chain terminal; append SetMaterial
sp_ev = find_custom(tge, "SpawnGuestVisual")
dump_chain(sp_ev, "spawn_chain")

# After PrintString at end of SpawnGuestVisual, cast GuestActor and SetMaterial on GuestMesh
# Get GuestActor -> Cast to BP_RestGuest_C -> Get GuestMesh -> SetMaterial(1, MI)
# Choose MI by TableId: 1=Red, 2=Blue, else Green

term = None
if sp_ev:
    chain = walk_then(sp_ev, 30)
    for n in chain:
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            term = n
    log("spawn terminal=" + (title(term) if term else "None"))

if term:
    get_g = tge.add_get_member_variable_node("GuestActor")
    bel.set_node_pos(get_g, pos(400, 4700))
    cast = tge.add_cast_node(unreal.load_asset(GUEST).generated_class())
    bel.set_node_pos(cast, pos(650, 4700))
    connect(out_data(get_g), find_pin(cast, "Object", "Input"), "g->cast")
    get_mesh = tge.add_get_member_variable_node("GuestMesh")
    # Get GuestMesh from cast As BP_RestGuest
    # For cast, the output "As BP_RestGuest" feeds self of Get GuestMesh — but Get member needs target.
    # Use CallFunction get on component: better SetMaterial via GetComponent
    # Simpler: call ApplyTint custom on guest if it exists, or Set TintIndex + call ApplyTint
    # Check guest for ApplyTint
    gbp = unreal.load_asset(GUEST)
    gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
    apply = find_custom(gge, "ApplyTint")
    log("Guest ApplyTint exists=" + str(apply is not None))

    # Set TintIndex on guest = TableId, then call ApplyTint
    get_tid = tge.add_get_member_variable_node("TableId")
    bel.set_node_pos(get_tid, pos(400, 4900))
    set_tint = tge.add_set_member_variable_node("TintIndex")
    # Need target = cast result. Set member on other object: use CallFunction path
    # Actually Set Member Variable node is always on Self. So we need to call a custom on Guest.
    # Ensure Guest has ApplyTint that reads TintIndex and SetMaterial.

# Build ApplyTint on Guest BP properly
gbp = unreal.load_asset(GUEST)
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
# Remove old ApplyTint if any
old = find_custom(gge, "ApplyTint")
if old:
    for p in bel.list_all_pins(old):
        try: p.break_pin_links()
        except Exception: pass

at = gge.add_custom_event_node("ApplyTint")
bel.set_node_pos(at, pos(-800, 200))
get_ti = gge.add_get_member_variable_node("TintIndex")
bel.set_node_pos(get_ti, pos(-500, 300))
# Branch TintIndex==1 -> Red, ==2 Blue, else Green
eq1 = gge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq1, pos(-250, 250))
setdef(find_pin(eq1, "B", "Input"), "1")
connect(out_data(get_ti), find_pin(eq1, "A", "Input"), "ti==1")
br1 = gge.add_branch_node()
bel.set_node_pos(br1, pos(0, 200))
connect(find_pin(at, "then", "Output"), find_pin(br1, "execute", "Input"), "at->br1")
connect(out_data(eq1), find_pin(br1, "Condition", "Input"), "eq1")

get_mesh = gge.add_get_member_variable_node("GuestMesh")
bel.set_node_pos(get_mesh, pos(-250, 400))

def make_set_mat(ge, x, y, mi_path, mesh_get):
    sm = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
    bel.set_node_pos(sm, pos(x, y))
    setdef(find_pin(sm, "ElementIndex", "Input") or find_pin(sm, "Index", "Input"), "1")  # clothes slot paint
    mi = unreal.load_asset(mi_path)
    mp = find_pin(sm, "Material", "Input")
    if mp and mi:
        try:
            mp.set_default_object(mi)
        except Exception:
            setdef(mp, mi.get_path_name())
    connect(out_data(mesh_get), find_pin(sm, "self", "Input"), "mesh->sm")
    return sm

sm_r = make_set_mat(gge, 350, 150, MI_RED, get_mesh)
sm_b = make_set_mat(gge, 350, 350, MI_BLUE, get_mesh)
sm_g = make_set_mat(gge, 350, 550, MI_GREEN, get_mesh)

eq2 = gge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq2, pos(0, 400))
setdef(find_pin(eq2, "B", "Input"), "2")
connect(out_data(get_ti), find_pin(eq2, "A", "Input"), "ti==2")
br2 = gge.add_branch_node()
bel.set_node_pos(br2, pos(150, 350))

connect(find_pin(br1, "then", "Output"), find_pin(sm_r, "execute", "Input"), "->red")
connect(find_pin(br1, "else", "Output"), find_pin(br2, "execute", "Input"), "else->br2")
connect(out_data(eq2), find_pin(br2, "Condition", "Input"), "eq2")
connect(find_pin(br2, "then", "Output"), find_pin(sm_b, "execute", "Input"), "->blue")
connect(find_pin(br2, "else", "Output"), find_pin(sm_g, "execute", "Input"), "->green")

# Also set on BeginPlay
bp_g = find_event(gge, "BeginPlay")
call_at = gge.add_call_function_node("/Game/Farm/Restaurant/BP_RestGuest.BP_RestGuest_C:ApplyTint")
bel.set_node_pos(call_at, pos(-400, 0))
if bp_g:
    thenp = find_pin(bp_g, "then", "Output")
    old = list(thenp.list_connected_pins() or []) if thenp else []
    if thenp:
        try: thenp.break_pin_links()
        except Exception: pass
    connect(thenp, find_pin(call_at, "execute", "Input"), "BP->ApplyTint")
    if old:
        connect(find_pin(call_at, "then", "Output"), old[0], "Apply->old")

bel.compile_blueprint(gbp)
eas.save_asset(GUEST)
log("Guest ApplyTint compiled")

# From Table SpawnGuestVisual terminal: Cast Guest, Set TintIndex = TableId, Call ApplyTint
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
sp_ev = find_custom(tge, "SpawnGuestVisual")
term = None
if sp_ev:
    for n in walk_then(sp_ev, 30):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            term = n
log("spawn term2=" + (title(term) if term else "None"))

if term:
    get_g = tge.add_get_member_variable_node("GuestActor")
    bel.set_node_pos(get_g, pos(400, 5000))
    cast = tge.add_cast_node(unreal.load_asset(GUEST).generated_class())
    bel.set_node_pos(cast, pos(700, 5000))
    connect(out_data(get_g), find_pin(cast, "Object", "Input"), "g->cast")
    connect(find_pin(term, "then", "Output"), find_pin(cast, "execute", "Input"), "term->cast")

    # Set TintIndex via Call "Set TintIndex" — use add_set on cast? 
    # Use Assign via K2Node_VariableSet with self pin — VariableSet might only be Self.
    # Alternative: expose TintIndex as public Instance Editable, set via "Set TintIndex" generated.
    # Path after compile: /Game/.../BP_RestGuest_C:SetTintIndex if BlueprintSetter — usually just variable set with target.
    
    # Try CallFunction SetTintIndex — won't exist.
    # Use ProcessEvent style: add_call_function for ApplyTint after setting via a custom SetTintAndApply on Guest.

# Add Guest custom SetTintAndApply(int Tint)
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
# Custom event with int input — need add_node_pin
st = gge.add_custom_event_node("SetTintAndApply")
bel.set_node_pos(st, pos(-800, 800))
# Try add pin for TintIndex input
try:
    # common API
    ge_api = [x for x in dir(gge) if "pin" in x.lower() or "param" in x.lower() or "input" in x.lower()]
    log("ge pin apis: " + str(ge_api)[:200])
except Exception as e:
    log(str(e))

# Try bel.add_graph_input_parameter or ge.add_node_pin
ok_pin = False
for api_name in ("add_custom_event_input", "add_event_parameter", "add_node_pin"):
    if hasattr(gge, api_name):
        log("has " + api_name)

# Inspect pins on custom event
for p in bel.list_all_pins(st):
    log("SetTintAndApply pin " + str(p.get_pin_name()) + " " + str(p.get_pin_direction()))

# Fallback without input param: Table sets variable via "Set" member with Cast as target.
# In UE5 Python, K2Node_VariableSet can have Self pin if created with make_variable_set targeting...
# Try: tge.add_set_member_variable_node("TintIndex") and connect cast As to Self pin if present.

tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
sp_ev = find_custom(tge, "SpawnGuestVisual")
term = None
if sp_ev:
    for n in walk_then(sp_ev, 40):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            term = n

get_g = tge.add_get_member_variable_node("GuestActor")
bel.set_node_pos(get_g, pos(500, 5100))
cast = tge.add_cast_node(unreal.load_asset(GUEST).generated_class())
bel.set_node_pos(cast, pos(800, 5100))
connect(out_data(get_g), find_pin(cast, "Object", "Input"), "g->cast2")
if term:
    connect(find_pin(term, "then", "Output"), find_pin(cast, "execute", "Input"), "term->cast2")

get_tid = tge.add_get_member_variable_node("TableId")
bel.set_node_pos(get_tid, pos(500, 5300))
set_ti = tge.add_set_member_variable_node("TintIndex")
bel.set_node_pos(set_ti, pos(1100, 5100))
# List pins on set_ti
for p in bel.list_all_pins(set_ti):
    log("setTint pin " + str(p.get_pin_name()) + " dir=" + str(p.get_pin_direction()) + " type=" + str(p.get_pin_type_display_string())[:40])

# Connect cast output to self if exists
self_pin = find_pin(set_ti, "self", "Input") or find_pin(set_ti, "Target", "Input")
as_pin = None
for p in bel.list_all_pins(cast):
    log("cast pin " + str(p.get_pin_name()) + " " + str(p.get_pin_direction()))
    if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
        if "bool" not in str(p.get_pin_type_display_string()).lower():
            as_pin = p
connect(find_pin(cast, "then", "Output"), find_pin(set_ti, "execute", "Input"), "cast->setTI")
connect(as_pin, self_pin, "as->self")
connect(out_data(get_tid), find_pin(set_ti, "TintIndex", "Input"), "tid->tint")

# Call ApplyTint on guest
call_at2 = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestGuest.BP_RestGuest_C:ApplyTint")
bel.set_node_pos(call_at2, pos(1450, 5100))
connect(find_pin(set_ti, "then", "Output"), find_pin(call_at2, "execute", "Input"), "set->apply")
connect(as_pin, find_pin(call_at2, "self", "Input"), "as->applySelf")
pr = make_print(tge, 1750, 5100, "Restaurant UI tint applied", "1.0")
connect(find_pin(call_at2, "then", "Output"), find_pin(pr, "execute", "Input"), "apply->pr")

bel.compile_blueprint(tbp)
eas.save_asset(TBL)
log("Table tint wire compiled")

# ========== MANAGER UI ==========
mbp = unreal.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))

# Ensure OrderListWidget var exists (already from prior)
names = [str(n) for n in bel.list_member_variable_names(mbp, False)]
log("mgr vars has OrderListWidget=" + str("OrderListWidget" in names))

for old in ("EnsureOrderUI", "RefreshOrderUI"):
    ev = find_custom(mge, old)
    if ev:
        # keep if already wired; check
        chain = walk_then(ev, 20)
        log(old + " existing chain len=" + str(len(chain)) + " " + ",".join(title(x) for x in chain[:8]))

ens = find_custom(mge, "EnsureOrderUI")
if ens is None or len(walk_then(ens, 10)) == 0:
    # rebuild EnsureOrderUI
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
    connect(out_data(get_w), opin, "w->valid")
    br = mge.add_branch_node()
    bel.set_node_pos(br, pos(-2300, 5200))
    connect(find_pin(ens, "then", "Output"), find_pin(br, "execute", "Input"), "ens->br")
    connect(out_data(is_v), find_pin(br, "Condition", "Input"), "v->c")
    create = mge.add_call_function_node("/Script/UMG.WidgetBlueprintLibrary:Create")
    bel.set_node_pos(create, pos(-1950, 5350))
    wbp_cls = unreal.load_asset(WBP_LIST).generated_class()
    cp = find_pin(create, "Class", "Input") or find_pin(create, "WidgetType", "Input")
    if cp and wbp_cls:
        try:
            cp.set_default_object(wbp_cls); log("Create class ok")
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
    log("EnsureOrderUI built")

ref = find_custom(mge, "RefreshOrderUI")
if ref is None:
    ref = mge.add_custom_event_node("RefreshOrderUI")
    bel.set_node_pos(ref, pos(-3200, 5700))

# Wire Refresh -> Ensure if not already
ref_chain = walk_then(ref, 15)
if not any("EnsureOrderUI" in title(n) for n in ref_chain):
    call_ens = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
    bel.set_node_pos(call_ens, pos(-2800, 5700))
    # prepend: break ref then, Ensure then -> old
    thenp = find_pin(ref, "then", "Output")
    old = list(thenp.list_connected_pins() or []) if thenp else []
    if thenp:
        try: thenp.break_pin_links()
        except Exception: pass
    connect(thenp, find_pin(call_ens, "execute", "Input"), "ref->ens")
    if old:
        connect(find_pin(call_ens, "then", "Output"), old[0], "ens->old")
    else:
        pr_h = make_print(mge, -2400, 5700, "\u8ba2\u5355", "0.0", key="RestOrderHeader")
        connect(find_pin(call_ens, "then", "Output"), find_pin(pr_h, "execute", "Input"), "ens->hdr")
    log("Refresh->Ensure wired")

# Splice RefreshOrderUI from RestaurantTick if missing
rt = find_custom(mge, "RestaurantTick")
has_ref_call = False
if rt:
    for n in walk_then(rt, 40):
        if "RefreshOrderUI" in title(n):
            has_ref_call = True
            break
if rt and not has_ref_call:
    call_ref = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:RefreshOrderUI")
    bel.set_node_pos(call_ref, pos(3600, 400))
    # Find true terminals of RestaurantTick (nodes with empty then)
    terms = []
    for n in walk_then(rt, 40):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            terms.append(n)
    log("RestaurantTick terminals: " + str([title(t) for t in terms]))
    for t in terms:
        connect(find_pin(t, "then", "Output"), find_pin(call_ref, "execute", "Input"), "RT->" + title(t))
    if not terms:
        # connect from last node
        chain = walk_then(rt, 40)
        if chain:
            connect(find_pin(chain[-1], "then", "Output"), find_pin(call_ref, "execute", "Input"), "RT last")

# BeginPlay Ensure
bpn = find_event(mge, "BeginPlay")
has_ens = False
if bpn:
    for n in walk_then(bpn, 40):
        if "EnsureOrderUI" in title(n):
            has_ens = True; break
if bpn and not has_ens:
    call_ens2 = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
    bel.set_node_pos(call_ens2, pos(1200, -200))
    terms = []
    for n in walk_then(bpn, 40):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            terms.append(n)
    for t in terms[:3]:
        connect(find_pin(t, "then", "Output"), find_pin(call_ens2, "execute", "Input"), "BP->" + title(t))
    log("BeginPlay->Ensure terminals=" + str(len(terms)))

bel.compile_blueprint(mbp)
eas.save_asset(MGR)

# Fix DrawDebugString Text: CurrentOrder may be Name — add Conv
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
for n in tge.list_all_nodes():
    if title(n) == "DrawDebugString":
        tp = find_pin(n, "Text", "Input")
        if tp and not list(tp.list_connected_pins() or []):
            get_ord = tge.add_get_member_variable_node("CurrentOrder")
            bel.set_node_pos(get_ord, pos(-1000, 5350))
            # try Name to String
            conv = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_NameToString")
            if conv is None:
                conv = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_TextToString")
            bel.set_node_pos(conv, pos(-700, 5350))
            if conv:
                connect(out_data(get_ord), find_pin(conv, "InName", "Input") or find_pin(conv, "InText", "Input") or find_pin(conv, "In", "Input"), "ord->conv")
                connect(out_data(conv), tp, "conv->text")
            else:
                connect(out_data(get_ord), tp, "ord->text")
            log("fixed DrawDebugString Text")

# Ensure Tick calls RefreshTableBubble — find Event Tick terminals properly
tick = find_event(tge, "Tick")
has_bub = False
if tick:
    for n in walk_then(tick, 50):
        if "RefreshTableBubble" in title(n):
            has_bub = True; break
    log("Tick has RefreshTableBubble=" + str(has_bub))
    if not has_bub:
        call_refb = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:RefreshTableBubble")
        bel.set_node_pos(call_refb, pos(4500, 2400))
        terms = []
        for n in walk_then(tick, 50):
            thenp = find_pin(n, "then", "Output")
            if thenp and not list(thenp.list_connected_pins() or []):
                # skip PayAndClear / TimeoutLeave if they appear (shouldn't from Tick)
                if title(n) in ("PayAndClear", "TimeoutLeave", "ClearSeat"):
                    continue
                terms.append(n)
        log("Tick true terminals: " + str([title(t) for t in terms]))
        for t in terms[:4]:
            connect(find_pin(t, "then", "Output"), find_pin(call_refb, "execute", "Input"), "Tick->" + title(t))

# Fix strip print wiring if DrawDebugString was fixed — check RefreshTableBubble has Print
refb = find_custom(tge, "RefreshTableBubble")
dump_chain(refb, "bubble_chain")
if refb and not any(title(n) == "PrintString" for n in walk_then(refb, 40)):
    log("WARN: no PrintString in RefreshTableBubble — adding strip")
    # Find terminal and add simple print with CurrentOrder + TableId
    term = None
    for n in walk_then(refb, 40):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            term = n
    if term is None:
        # occupied branch then might end at DrawDebugString
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
        connect(out_data(get_pl), find_pin(to_pl, "InDouble", "Input") or find_pin(to_pl, "InFloat", "Input") or find_pin(to_pl, "", "Input"), "pl")
        eqd = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
        bel.set_node_pos(eqd, pos(250, 6000))
        setdef(find_pin(eqd, "B", "Input"), "1")
        connect(out_data(get_dish), find_pin(eqd, "A", "Input"), "dish")
        key_ap = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(key_ap, pos(500, 5750))
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

bel.compile_blueprint(tbp)
eas.save_asset(TBL)
bel.compile_blueprint(mbp)
eas.save_asset(MGR)
bel.compile_blueprint(gbp)
eas.save_asset(GUEST)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level " + str(e))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# Error report
for path, key in ((TBL, "table_err"), (MGR, "mgr_err"), (GUEST, "guest_err")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    try:
        errs = list(ge.list_nodes_with_errors() or [])
        R[key] = [title(n) for n in errs[:20]]
        log("{} errors={} {}".format(key, len(errs), R[key][:10]))
    except Exception as e:
        R[key] = [str(e)]
        log("{} errlist {}".format(key, e))

# Final dumps
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(TBL), "EventGraph"))
dump_chain(find_custom(tge, "TrySeat"), "tryseat_final")
dump_chain(find_custom(tge, "SpawnGuestVisual"), "spawn_final")
dump_chain(find_custom(tge, "DestroyGuestVisual"), "destroy_final")
dump_chain(find_custom(tge, "ClearSeat"), "clear_final")
dump_chain(find_custom(tge, "RefreshTableBubble"), "bubble_final")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(MGR), "EventGraph"))
dump_chain(find_custom(mge, "EnsureOrderUI"), "ensure_final")
dump_chain(find_custom(mge, "RefreshOrderUI"), "refresh_final")

out = unreal.Paths.project_saved_dir() + "RestaurantUI_wire2_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("report " + out)
log("ALL_DONE")
