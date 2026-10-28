# -*- coding: utf-8 -*-
"""Fix Manager ForEach (wire GetAllActors exec); fix GuestMesh component; fix Tick bubble misuse."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"
MI_RED = "/Game/Farm/Restaurant/Guests/MI_GuestRed"
MI_BLUE = "/Game/Farm/Restaurant/Guests/MI_GuestBlue"
MI_GREEN = "/Game/Farm/Restaurant/Guests/MI_GuestGreen"

R = {"steps": []}

def log(m):
    unreal.log("[UI_W5] " + str(m)); print("[UI_W5] " + str(m)); R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Return Value", "OutActors", "GuestActor", "OrderListWidget", "Array Element"):
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
    for fn in ("set_pin_value", "set_default_value"):
        if hasattr(pin, fn):
            try:
                getattr(pin, fn)(str(val)); return True
            except Exception:
                pass
    return False

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

def walk_then(start, max_d=50):
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

def pin_default(pin):
    if not pin: return None
    for fn in ("get_default_as_string", "get_default_value"):
        if hasattr(pin, fn):
            try: return str(getattr(pin, fn)())
            except Exception: pass
    return "?"

# ===== Guest SCS / mesh component name =====
gbp = unreal.load_asset(GUEST)
# Try BlueprintEditorLibrary / SubobjectData
try:
    scs = gbp.simple_construction_script
    if scs:
        for node in scs.get_all_nodes():
            log("SCS node " + str(node.get_variable_name()) + " class=" + str(node.component_class))
except Exception as e:
    log("scs " + str(e))

# list get member possibilities
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
# Try get GuestMesh
gm = gge.add_get_member_variable_node("GuestMesh")
log("Get GuestMesh node=" + str(gm))
if gm:
    for p in bel.list_all_pins(gm):
        log("  pin " + str(p.get_pin_name()) + " " + str(p.get_pin_type_display_string())[:60])

# Try Mesh, SkeletalMesh, CharacterMesh, Mannequin
for name in ("Mesh", "GuestMesh", "SkeletalMesh", "CharacterMesh0", "SK_Manny"):
    n = gge.add_get_member_variable_node(name)
    log("get {} = {}".format(name, n is not None and title(n)))

# Rebuild ApplyTint properly using GetComponentByClass on Self
at = find_custom(gge, "ApplyTint")
if at:
    # break old chain
    for n in walk_then(at, 20):
        for p in bel.list_all_pins(n):
            try: p.break_pin_links()
            except Exception: pass
    for p in bel.list_all_pins(at):
        try: p.break_pin_links()
        except Exception: pass

at = find_custom(gge, "ApplyTint")
if at is None:
    at = gge.add_custom_event_node("ApplyTint")
    bel.set_node_pos(at, pos(-1000, 200))

getc = gge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
bel.set_node_pos(getc, pos(-700, 300))
setdef(find_pin(getc, "ComponentClass", "Input"), "/Script/Engine.SkeletalMeshComponent")
# self is implicit for Actor call on self? Need self pin — leave default Self

get_ti = gge.add_get_member_variable_node("TintIndex")
bel.set_node_pos(get_ti, pos(-700, 450))
eq1 = gge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq1, pos(-400, 400))
setdef(find_pin(eq1, "B", "Input"), "1")
connect(out_data(get_ti), find_pin(eq1, "A", "Input"), "ti==1")
br1 = gge.add_branch_node()
bel.set_node_pos(br1, pos(-150, 200))
connect(find_pin(at, "then", "Output"), find_pin(br1, "execute", "Input"), "at->br1")
connect(out_data(eq1), find_pin(br1, "Condition", "Input"), "eq1")

def make_sm(ge, x, y, mi_path, mesh_src):
    sm = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
    bel.set_node_pos(sm, pos(x, y))
    setdef(find_pin(sm, "ElementIndex", "Input") or find_pin(sm, "Index", "Input"), "1")
    mi = unreal.load_asset(mi_path)
    mp = find_pin(sm, "Material", "Input")
    if mp and mi:
        setdef(mp, mi.get_path_name())
    connect(out_data(mesh_src), find_pin(sm, "self", "Input"), "mesh->sm")
    return sm

sm_r = make_sm(gge, 200, 100, MI_RED, getc)
sm_b = make_sm(gge, 200, 300, MI_BLUE, getc)
sm_g = make_sm(gge, 200, 500, MI_GREEN, getc)
eq2 = gge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq2, pos(-150, 400))
setdef(find_pin(eq2, "B", "Input"), "2")
connect(out_data(get_ti), find_pin(eq2, "A", "Input"), "ti==2")
br2 = gge.add_branch_node()
bel.set_node_pos(br2, pos(0, 350))
connect(find_pin(br1, "then", "Output"), find_pin(sm_r, "execute", "Input"), "red")
connect(find_pin(br1, "else", "Output"), find_pin(br2, "execute", "Input"), "else")
connect(out_data(eq2), find_pin(br2, "Condition", "Input"), "eq2")
connect(find_pin(br2, "then", "Output"), find_pin(sm_b, "execute", "Input"), "blue")
connect(find_pin(br2, "else", "Output"), find_pin(sm_g, "execute", "Input"), "green")
log("ApplyTint rebuilt")

# After spawn on Table: also set TintIndex somehow — Table already SetMaterial via GetComponentByClass
# Set TintIndex on guest by calling a custom SetTintIndex event with... without cast, use:
# Add custom event ReceiveTint(int) on guest — still need to call with target.
# Table SetMaterial path is enough for v1.

bel.compile_blueprint(gbp)
eas.save_asset(GUEST)

# ===== Fix Manager RefreshOrderUI ForEach =====
mbp = unreal.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
ref = find_custom(mge, "RefreshOrderUI")

# Find ForEach and GetAllActors nodes; rewire: Print/Ensure term -> GetAllActors -> ForEach
getall = None
foreach = None
for n in walk_then(ref, 40) if ref else []:
    if "GetAllActorsOfClass" in title(n):
        getall = n
    if "For Each" in title(n) or "ForEach" in title(n).replace(" ", ""):
        foreach = n
log("found getall={} foreach={}".format(getall is not None, foreach is not None))

# If getall missing, create
if ref and getall is None:
    getall = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(getall, pos(-2100, 5900))
if getall:
    tcp = find_pin(getall, "ActorClass", "Input") or find_pin(getall, "Class", "Input")
    setdef(tcp, unreal.load_asset(TBL).generated_class().get_path_name())
    log("GetAllActors class=" + repr(pin_default(tcp)))
    for p in bel.list_all_pins(getall):
        log("getall pin " + str(p.get_pin_name()) + " " + str(p.get_pin_direction()) + " " + str(p.get_pin_type_display_string())[:40])

if ref and foreach:
    # Break foreach exec inputs; rewire Ensure/Print -> GetAllActors -> ForEach
    # Find EnsureOrderUI call or PrintString before foreach
    # Current: EnsureOrderUI -> PrintString -> For Each Loop
    # Want: EnsureOrderUI -> PrintString -> GetAllActors -> ForEach
    fe_exec = find_pin(foreach, "Exec", "Input") or find_pin(foreach, "execute", "Input")
    preds = []
    if fe_exec:
        for c in list(fe_exec.list_connected_pins() or []):
            preds.append(c.get_owning_node())
        try: fe_exec.break_pin_links()
        except Exception: pass
    log("foreach preds were " + str([title(p) for p in preds]))

    # GetAllActors exec
    ga_exec = find_pin(getall, "execute", "Input")
    ga_then = find_pin(getall, "then", "Output")
    if preds:
        connect(find_pin(preds[0], "then", "Output"), ga_exec, "pred->getall")
    connect(ga_then, fe_exec, "getall->fe")
    # Array
    arr = find_pin(foreach, "Array", "Input")
    out_actors = find_pin(getall, "OutActors", "Output")
    if arr:
        try: arr.break_pin_links()
        except Exception: pass
    connect(out_actors, arr, "out->arr")
    # LoopBody -> RefreshTableBubble
    body = find_pin(foreach, "LoopBody", "Output")
    # find existing RefreshTableBubble call or create
    rb = None
    for n in mge.list_all_nodes():
        if title(n) == "RefreshTableBubble" and n.get_class().get_name() == "K2Node_CallFunction":
            rb = n; break
    if rb is None:
        rb = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:RefreshTableBubble")
        bel.set_node_pos(rb, pos(-1200, 5900))
    rb_exec = find_pin(rb, "execute", "Input")
    if rb_exec:
        try: rb_exec.break_pin_links()
        except Exception: pass
    connect(body, rb_exec, "fe->rb")
    elem = find_pin(foreach, "Array Element", "Output")
    connect(elem, find_pin(rb, "self", "Input"), "elem->self")
    log("ForEach rewired with GetAllActors exec")

# ===== Disconnect RefreshTableBubble from PayAndClear/TimeoutLeave only-path misuse =====
# Actually having it AFTER pay/timeout is OK as extra; continuous comes from Manager.
# But wait - we connected Tick empty-then (PayAndClear.then and TimeoutLeave.then) to RefreshTableBubble.
# That means after PayAndClear returns, Refresh runs — fine as cleanup.
# Continuous: Manager RestaurantTick -> RefreshOrderUI -> GetAllActors -> ForEach -> RefreshTableBubble. Good.

# Also call RefreshTableBubble every Tick properly via Timer on Table BeginPlay
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
# Check if Tick has any path that always runs Refresh — look for RefreshTableBubble preds
for n in tge.list_all_nodes():
    if title(n) == "RefreshTableBubble" and n.get_class().get_name() == "K2Node_CallFunction":
        exe = find_pin(n, "execute", "Input")
        preds = [title(c.get_owning_node()) for c in (exe.list_connected_pins() or [])] if exe else []
        log("RefreshTableBubble call preds=" + str(preds))

# Add K2_SetTimer on Table BeginPlay for continuous bubble (0.2s)
bp = find_event(tge, "BeginPlay")
has_timer = bp and any("SetTimer" in title(n) or "Timer" in title(n) for n in walk_then(bp, 30))
log("Table BP has timer=" + str(has_timer) + " chain=" + str([title(n) for n in walk_then(bp, 20)] if bp else []))
if bp and not has_timer:
    timer = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:K2_SetTimer")
    bel.set_node_pos(timer, pos(800, -200))
    if timer:
        setdef(find_pin(timer, "FunctionName", "Input"), "RefreshTableBubble")
        setdef(find_pin(timer, "Time", "Input"), "0.2")
        lp = find_pin(timer, "bLooping", "Input") or find_pin(timer, "Looping", "Input")
        setdef(lp, "true")
        # Object pin = self default
        thenp = find_pin(bp, "then", "Output")
        # BeginPlay chain empty — connect direct (may parallel if something else linked)
        old = list(thenp.list_connected_pins() or []) if thenp else []
        connect(thenp, find_pin(timer, "execute", "Input"), "BP->timer")
        if old:
            # also keep old — thenp can have multiple? In UE usually one. We may have stolen.
            # Reconnect old from timer then
            connect(find_pin(timer, "then", "Output"), old[0], "timer->old")
        log("Table BeginPlay SetTimer RefreshTableBubble")
        for p in bel.list_all_pins(timer):
            log("timer " + str(p.get_pin_name()) + " def=" + repr(pin_default(p))[:40])

# Clear order strip on destroy: append empty print with RestOrder{id}
des = find_custom(tge, "DestroyGuestVisual")
if des:
    term = None
    for n in walk_then(des, 20):
        thenp = find_pin(n, "then", "Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            term = n
    # Check if already has clear with Key RestOrder
    # Add clear print
    if term:
        get_tid = tge.add_get_member_variable_node("TableId")
        bel.set_node_pos(get_tid, pos(400, 4500))
        to_id = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
        bel.set_node_pos(to_id, pos(650, 4500))
        connect(out_data(get_tid), find_pin(to_id, "InInt", "Input"), "id")
        key_ap = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(key_ap, pos(900, 4500))
        setdef(find_pin(key_ap, "A", "Input"), "RestOrder")
        connect(out_data(to_id), find_pin(key_ap, "B", "Input"), "kid")
        pr = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, pos(1200, 4450))
        setdef(find_pin(pr, "InString", "Input"), " ")
        setdef(find_pin(pr, "Duration", "Input"), "0.0")
        connect(out_data(key_ap), find_pin(pr, "Key", "Input"), "key")
        connect(find_pin(term, "then", "Output"), find_pin(pr, "execute", "Input"), "des->clearPrint")
        log("destroy clear strip")

bel.compile_blueprint(tbp); eas.save_asset(TBL)
bel.compile_blueprint(mbp); eas.save_asset(MGR)
bel.compile_blueprint(gbp); eas.save_asset(GUEST)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level " + str(e))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# Errors + dumps
for path, key in ((TBL, "table"), (MGR, "mgr"), (GUEST, "guest")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    errs = []
    try:
        errs = [title(n) for n in (ge.list_nodes_with_errors() or [])]
    except Exception as e:
        errs = [str(e)]
    R[key + "_err"] = errs
    log("{} err={} {}".format(key, len(errs), errs[:12]))
    # detail first error pins
    try:
        for n in (ge.list_nodes_with_errors() or [])[:3]:
            log("  ERRNODE " + title(n))
            for p in bel.list_all_pins(n):
                linked = list(p.list_connected_pins() or [])
                log("    {} {} linked={} def={}".format(p.get_pin_name(), p.get_pin_direction(), len(linked), repr(pin_default(p))[:50]))
    except Exception as e:
        log("errdetail " + str(e))

tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(TBL), "EventGraph"))
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(MGR), "EventGraph"))
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(GUEST), "EventGraph"))
for label, ge, name in (
    ("tryseat", tge, "TrySeat"), ("spawn", tge, "SpawnGuestVisual"), ("destroy", tge, "DestroyGuestVisual"),
    ("bubble", tge, "RefreshTableBubble"), ("ensure", mge, "EnsureOrderUI"), ("refresh", mge, "RefreshOrderUI"),
    ("apply", gge, "ApplyTint"),
):
    ev = find_custom(ge, name)
    chain = [title(n) for n in walk_then(ev, 40)] if ev else []
    R[label] = chain
    log(label + ": " + " -> ".join(chain[:30]))

out = unreal.Paths.project_saved_dir() + "RestaurantUI_wire5_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("report " + out)
log("ALL_DONE")
