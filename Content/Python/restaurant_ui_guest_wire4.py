# -*- coding: utf-8 -*-
"""Fix ComponentClass, Tick->Bubble, Create class, BeginPlay Ensure; verify assets."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"
WBP_LIST = "/Game/Farm/UI/WBP_RestOrderList"
WBP_BUB = "/Game/Farm/UI/WBP_RestOrderBubble"

R = {"steps": [], "verify": {}}

def log(m):
    unreal.log("[UI_W4] " + str(m)); print("[UI_W4] " + str(m)); R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Return Value", "GuestActor", "OrderListWidget"):
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
    for fn in ("set_pin_value", "set_default_value", "set_default_as_string"):
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
    for fn in ("get_default_as_string", "get_default_value", "get_pin_value"):
        if hasattr(pin, fn):
            try: return str(getattr(pin, fn)())
            except Exception: pass
    try:
        return str(pin.default_value)
    except Exception:
        return "?"

# ---- Verify assets ----
for p in [WBP_LIST, WBP_BUB, GUEST,
          "/Game/Farm/Restaurant/Guests/MI_GuestRed",
          "/Game/Farm/Restaurant/Guests/MI_GuestBlue",
          "/Game/Farm/Restaurant/Guests/MI_GuestGreen"]:
    R["verify"][p] = eas.does_asset_exist(p)
    log("asset {} {}".format(p, R["verify"][p]))

# ---- Fix GetComponentByClass ComponentClass ----
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
for n in tge.list_all_nodes():
    if title(n) == "GetComponentByClass":
        cp = find_pin(n, "ComponentClass", "Input")
        log("GetComponentByClass class default before=" + repr(pin_default(cp)))
        # Try select class via set_default_object with UClass
        sk = unreal.SkeletalMeshComponent.static_class()
        ok = False
        if cp:
            try:
                cp.set_default_object(sk); ok = True; log("set_default_object SkeletalMeshComponent OK")
            except Exception as e:
                log("set_default_object fail " + str(e)[:100])
            if not ok:
                # try soft path forms
                for v in ("SkeletalMeshComponent", "/Script/Engine.SkeletalMeshComponent",
                          "Class'/Script/Engine.SkeletalMeshComponent'"):
                    if setdef(cp, v):
                        log("setdef ComponentClass=" + v + " now=" + repr(pin_default(cp)))
                        break
        log("GetComponentByClass class after=" + repr(pin_default(cp)))
        # Also check self connected
        sp = find_pin(n, "self", "Input")
        log("GetComponentByClass self linked=" + str(bool(sp and list(sp.list_connected_pins() or []))))

# ---- Fix Create Widget Class on Manager ----
mbp = unreal.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
for n in mge.list_all_nodes():
    if title(n) in ("Create", "Create Widget"):
        cp = find_pin(n, "Class", "Input") or find_pin(n, "WidgetType", "Input")
        log("Create class before=" + repr(pin_default(cp)))
        wbp_cls = unreal.load_asset(WBP_LIST).generated_class()
        if cp and wbp_cls:
            try:
                cp.set_default_object(wbp_cls); log("Create set_default_object OK")
            except Exception as e:
                log("Create set_default_object " + str(e)[:80])
                setdef(cp, wbp_cls.get_path_name())
        log("Create class after=" + repr(pin_default(cp)))

# ---- Tick -> RefreshTableBubble ----
tick = find_event(tge, "Tick")
has = any("RefreshTableBubble" in title(n) for n in walk_then(tick, 60)) if tick else False
log("Tick has RefreshTableBubble=" + str(has))
if tick:
    chain = [title(n) for n in walk_then(tick, 40)]
    log("Tick chain sample: " + " -> ".join(chain[:20]))
    # Find ANY node in tick chain with empty then, including filtered ones; also try last node
    terms = []
    for n in walk_then(tick, 60):
        thenp = find_pin(n, "then", "Output")
        if thenp is None:
            continue
        if not list(thenp.list_connected_pins() or []):
            terms.append(n)
    log("ALL Tick empty-then: " + str([title(t) for t in terms]))
    if not has:
        call_refb = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:RefreshTableBubble")
        bel.set_node_pos(call_refb, pos(4800, 2500))
        if terms:
            for t in terms[:5]:
                connect(find_pin(t, "then", "Output"), find_pin(call_refb, "execute", "Input"), "Tick->" + title(t))
        else:
            # Force: find last Set or Print in chain and append
            chain_nodes = walk_then(tick, 60)
            if chain_nodes:
                last = chain_nodes[-1]
                thenp = find_pin(last, "then", "Output")
                if thenp:
                    # may already have connections — insert after by also linking from call? 
                    # If last has connections, add parallel from a Sequence — skip, use add from ReceiveTick then via Sequence at start
                    connect(thenp, find_pin(call_refb, "execute", "Input"), "TickLast->" + title(last))
            # Also try connecting from ReceiveTick then in parallel via re-get
            # Use macro Sequence: add Sequence after first node of tick
            # Simpler backup: wire RefreshTableBubble from Event Tick THEN in parallel by NOT breaking — 
            # K2 allows multiple then outputs? No, one then. Use Sequence node.
            seq = tge.add_macro_node("/Script/BlueprintGraph.Sequence")  # may fail
            if seq is None:
                # try Engine
                for path in ("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:Sequence",
                             "Sequence"):
                    try:
                        seq = tge.add_macro_node(path)
                        if seq: break
                    except Exception:
                        pass
            log("Sequence macro=" + str(seq))
            if seq is None:
                # Fallback: call RefreshTableBubble from SpawnGuestVisual end AND from a custom that Manager invokes — 
                # OR hook onto End of Destroy and spawn is not enough for tick update.
                # Best fallback without Sequence: use Timer? 
                # Actually: Event Tick always fires — if chain has a node with then going somewhere, 
                # we can insert Sequence: break first link, Sequence then0=old, then1=Refresh.
                first_then = find_pin(tick, "then", "Output")
                first_tgts = list(first_then.list_connected_pins() or []) if first_then else []
                if first_tgts:
                    # Try add_call Sequence from Kismet — doesn't exist.
                    # Use DoOnce? No.
                    # Parallel: Custom event RefreshTableBubble called from Manager RestaurantTick via GetAllActorsOfClass — heavy.
                    # SIMPLEST reliable: in Manager RefreshOrderUI, GetAllActorsOfClass BP_RestaurantTable and ForEach Call RefreshTableBubble.
                    log("will add table bubble refresh from Manager RefreshOrderUI")
                    R["need_mgr_bubble"] = True

# If Tick couldn't get bubble, add to Manager RefreshOrderUI: GetAllActorsOfClass + ForEachLoop + RefreshTableBubble
if R.get("need_mgr_bubble") or not has:
    mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
    ref = find_custom(mge, "RefreshOrderUI")
    # Check if already has GetAllActors
    already = ref and any("GetAllActorsOfClass" in title(n) for n in walk_then(ref, 30))
    if ref and not already:
        # Append after Ensure/Print terminal
        term = None
        for n in walk_then(ref, 20):
            thenp = find_pin(n, "then", "Output")
            if thenp and not list(thenp.list_connected_pins() or []):
                term = n
        getall = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
        bel.set_node_pos(getall, pos(-2000, 5900))
        tcp = find_pin(getall, "ActorClass", "Input") or find_pin(getall, "Class", "Input")
        tcls = unreal.load_asset(TBL).generated_class()
        if tcp and tcls:
            try: tcp.set_default_object(tcls); log("GetAllActors class OK")
            except Exception: setdef(tcp, tcls.get_path_name())
        # ForEachLoop macro
        foreach = None
        for path in (
            "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop",
            "ForEachLoop",
        ):
            try:
                foreach = mge.add_macro_node(path)
                if foreach: break
            except Exception as e:
                log("foreach try " + str(e)[:60])
        log("foreach=" + str(foreach))
        if foreach and term:
            bel.set_node_pos(foreach, pos(-1600, 5900))
            connect(find_pin(term, "then", "Output"), find_pin(foreach, "execute", "Input") or find_pin(foreach, "Exec", "Input"), "term->fe")
            # Array pin
            arr = find_pin(foreach, "Array", "Input") or find_pin(foreach, "TargetArray", "Input")
            connect(out_data(getall) or find_pin(getall, "OutActors", "Output"), arr, "actors->fe")
            # LoopBody -> RefreshTableBubble on Array Element
            call_rb = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:RefreshTableBubble")
            bel.set_node_pos(call_rb, pos(-1200, 5900))
            body = find_pin(foreach, "LoopBody", "Output") or find_pin(foreach, "Then", "Output")
            connect(body, find_pin(call_rb, "execute", "Input"), "fe->rb")
            elem = find_pin(foreach, "Array Element", "Output") or find_pin(foreach, "Element", "Output") or find_pin(foreach, "ArrayElement", "Output")
            connect(elem, find_pin(call_rb, "self", "Input"), "elem->self")
            # list foreach pins for debug
            for p in bel.list_all_pins(foreach):
                log("fe pin " + str(p.get_pin_name()) + " " + str(p.get_pin_direction()))
            log("Manager Refresh calls table bubbles via ForEach")
        elif term:
            # Without ForEach: just Print that UI refresh ran — tables need Tick hook
            # Try connecting Refresh from Event Tick using a second custom path:
            # Add to Table: bind Timer on BeginPlay that loops RefreshTableBubble
            log("ForEach unavailable — using Table BeginPlay SetTimer")
            R["use_timer"] = True

# Table BeginPlay SetTimer for RefreshTableBubble if needed
if not has or R.get("use_timer"):
    # Re-check has after possible tick wire
    tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
    tick = find_event(tge, "Tick")
    has = any("RefreshTableBubble" in title(n) for n in walk_then(tick, 60)) if tick else False
    if not has:
        # SetTimer by Event RefreshTableBubble every 0.2s from BeginPlay
        bp = find_event(tge, "BeginPlay")
        timer = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:K2_SetTimer")
        # or SetTimerDelegate — Custom Event name
        if timer is None:
            timer = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:SetTimer")
        log("timer node=" + str(timer))
        # Prefer K2_SetTimer with FunctionName = RefreshTableBubble
        timer = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:K2_SetTimer")
        bel.set_node_pos(timer, pos(2000, -400))
        if timer:
            for p in bel.list_all_pins(timer):
                log("timer pin " + str(p.get_pin_name()) + " " + str(p.get_pin_type_display_string())[:50])
            setdef(find_pin(timer, "FunctionName", "Input"), "RefreshTableBubble")
            setdef(find_pin(timer, "Time", "Input"), "0.25")
            setdef(find_pin(timer, "bLooping", "Input") or find_pin(timer, "Looping", "Input"), "true")
            if bp:
                # append to BeginPlay terminal
                terms = [n for n in walk_then(bp, 40) if find_pin(n, "then", "Output") and not list(find_pin(n, "then", "Output").list_connected_pins() or [])]
                log("Table BP terminals: " + str([title(t) for t in terms]))
                if terms:
                    connect(find_pin(terms[0], "then", "Output"), find_pin(timer, "execute", "Input"), "BP->timer")
                else:
                    # parallel from BeginPlay — break and sequence manually: connect timer from last node then even if connected
                    chain = walk_then(bp, 40)
                    if chain:
                        connect(find_pin(chain[-1], "then", "Output"), find_pin(timer, "execute", "Input"), "BPlast->timer")
                    else:
                        connect(find_pin(bp, "then", "Output"), find_pin(timer, "execute", "Input"), "BP->timer direct")
            log("SetTimer RefreshTableBubble 0.25s")

# BeginPlay Manager Ensure — force from first then via inserting at end of known chain
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
bpn = find_event(mge, "BeginPlay")
has_ens = bpn and any("EnsureOrderUI" in title(n) for n in walk_then(bpn, 50))
log("Mgr BeginPlay has Ensure=" + str(has_ens))
if bpn and not has_ens:
    call_ens = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
    bel.set_node_pos(call_ens, pos(2000, -300))
    chain = walk_then(bpn, 50)
    terms = [n for n in chain if find_pin(n, "then", "Output") and not list(find_pin(n, "then", "Output").list_connected_pins() or [])]
    log("Mgr BP terms: " + str([title(t) for t in terms]) + " chainlen=" + str(len(chain)))
    if terms:
        for t in terms[:2]:
            connect(find_pin(t, "then", "Output"), find_pin(call_ens, "execute", "Input"), "BP->" + title(t))
    elif chain:
        connect(find_pin(chain[-1], "then", "Output"), find_pin(call_ens, "execute", "Input"), "BPlast->Ensure")
    else:
        connect(find_pin(bpn, "then", "Output"), find_pin(call_ens, "execute", "Input"), "BPdirect->Ensure")

# Verify Spawn class / Finish
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
for n in tge.list_all_nodes():
    if "BeginDeferredActorSpawnFromClass" in title(n):
        cp = find_pin(n, "ActorClass", "Input") or find_pin(n, "Class", "Input")
        log("Spawn class=" + repr(pin_default(cp)))
        gcls = unreal.load_asset(GUEST).generated_class()
        if cp and gcls:
            try:
                cp.set_default_object(gcls); log("Spawn class forced OK")
            except Exception as e:
                setdef(cp, gcls.get_path_name()); log("Spawn class setdef " + str(e)[:60])
        log("Spawn class after=" + repr(pin_default(cp)))

# Verify OrderBubble widget class on table defaults if possible
# Check Guest mesh component exists
gbp = unreal.load_asset(GUEST)
comps = []
try:
    # SCS
    for name in bel.list_member_variable_names(gbp, False):
        comps.append(str(name))
except Exception:
    pass
R["guest_vars"] = comps
log("guest vars: " + str(comps))

# Guest ApplyTint chain
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
at = find_custom(gge, "ApplyTint")
if at:
    log("ApplyTint: " + " -> ".join(title(n) for n in walk_then(at, 20)))
else:
    log("NO ApplyTint")

# Clear RestOrder print key on Destroy — ensure present
des = find_custom(tge, "DestroyGuestVisual")
if des and not any(title(n) == "PrintString" and n != walk_then(des, 20)[0] for n in walk_then(des, 20) if False):
    # Check if clear print exists
    prints_in_des = [n for n in walk_then(des, 20) if title(n) == "PrintString"]
    log("Destroy PrintString count=" + str(len(prints_in_des)))

bel.compile_blueprint(tbp); eas.save_asset(TBL)
bel.compile_blueprint(mbp); eas.save_asset(MGR)
bel.compile_blueprint(gbp); eas.save_asset(GUEST)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level " + str(e))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# Final error + chain dump
for path, key in ((TBL, "table"), (MGR, "mgr"), (GUEST, "guest")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    errs = []
    try:
        errs = [title(n) for n in (ge.list_nodes_with_errors() or [])]
    except Exception as e:
        errs = [str(e)]
    R[key + "_err"] = errs
    log("{} err={} {}".format(key, len(errs), errs[:10]))

tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(TBL), "EventGraph"))
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(MGR), "EventGraph"))
for label, ge, name in (
    ("tryseat", tge, "TrySeat"), ("spawn", tge, "SpawnGuestVisual"), ("destroy", tge, "DestroyGuestVisual"),
    ("clear", tge, "ClearSeat"), ("bubble", tge, "RefreshTableBubble"),
    ("ensure", mge, "EnsureOrderUI"), ("refresh", mge, "RefreshOrderUI"),
):
    ev = find_custom(ge, name)
    R[label] = [title(n) for n in walk_then(ev, 40)] if ev else []
    log(label + ": " + " -> ".join(R[label][:25]))

tick = find_event(tge, "Tick")
R["tick_has_bubble"] = any("RefreshTableBubble" in title(n) for n in walk_then(tick, 60)) if tick else False
bpn = find_event(mge, "BeginPlay")
R["mgr_bp_has_ensure"] = any("EnsureOrderUI" in title(n) for n in walk_then(bpn, 50)) if bpn else False
log("tick_has_bubble=" + str(R["tick_has_bubble"]) + " mgr_bp_ensure=" + str(R["mgr_bp_has_ensure"]))

# Check timer on table beginplay
tbp2 = find_event(tge, "BeginPlay")
R["table_bp"] = [title(n) for n in walk_then(tbp2, 30)] if tbp2 else []
log("table_bp: " + " -> ".join(R["table_bp"][:20]))

out = unreal.Paths.project_saved_dir() + "RestaurantUI_wire4_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("report " + out)
log("ALL_DONE")
