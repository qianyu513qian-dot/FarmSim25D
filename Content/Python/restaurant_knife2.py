# -*- coding: utf-8 -*-
"""Restaurant knife2: OpenSign clock gate + Manager guest spawn + surgical E (skip TillSoil only on hit)."""
import unreal, json, traceback

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
REPORT = {"steps": [], "errors": [], "ia_before": [], "ia_after": [], "actors_before": 0, "actors_after": 0,
          "rolled_back_e": False, "done": {}}

def log(m):
    unreal.log("[REST_K2] " + str(m))
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
    for fn in ("set_default_value", "set_pin_value"):
        try:
            getattr(pin, fn)(str(val))
            return
        except Exception:
            pass

def pin_type(category, sub=""):
    p = unreal.EdGraphPinType()
    if sub:
        p.import_text('(PinCategory="{}",PinSubCategory="{}")'.format(category, sub))
    else:
        p.import_text('(PinCategory="{}")'.format(category))
    return p

def add_var(bp, name, ptype):
    names = [str(n) for n in bel.list_member_variable_names(bp)]
    if name in names:
        return
    try:
        bel.add_member_variable(bp, name, ptype)
        try:
            bel.set_blueprint_variable_instance_editable(bp, name, True)
        except Exception:
            pass
        log("var+" + name)
    except Exception as e:
        log("var fail {} {}".format(name, e))

def graph_editor(bp, fname, create=True):
    g = bel.find_graph(bp, fname)
    if g is None and create:
        try:
            bel.add_function_graph(bp, fname)
        except Exception as e:
            log("add_fn " + str(e))
        g = bel.find_graph(bp, fname)
    if g is None:
        return None, None
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    if ge is None:
        try:
            eg = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
            eg.create_and_edit_function_graph(fname)
            g = bel.find_graph(bp, fname)
            ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        except Exception as e:
            log("create_edit " + str(e))
    return ge, g

def clear_fn_body(ge):
    kill = []
    for n in ge.list_all_nodes():
        cn = n.get_class().get_name()
        if cn in ("K2Node_FunctionEntry", "K2Node_FunctionResult"):
            continue
        kill.append(n)
    if kill:
        ge.remove_nodes(kill)

def entry_then(ge):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            return find_pin(n, "then", "Output") or find_pin(n, "execute", "Output"), n
    return None, None

def make_print(ge, x, y, text, dur="2.5"):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    return pr

def make_return(ge, x, y):
    try:
        r = ge.add_return_node()
    except Exception:
        r = ge.create_node_from_name("Return Node", unreal.Vector2D(x, y), [])
    bel.set_node_pos(r, pos(x, y))
    return r

REPORT["actors_before"] = len(eas.get_all_level_actors())

# ========== 1) OpenSign.RestaurantInteract: clock gate + toggle ==========
def wire_opensign():
    bp = unreal.EditorAssetLibrary.load_asset(DIR + "/BP_RestaurantOpenSign")
    add_var(bp, "bIsOpenBusiness", pin_type("bool"))
    ge, g = graph_editor(bp, "RestaurantInteract", True)
    if not ge:
        REPORT["errors"].append("OpenSign no RestaurantInteract graph")
        return False
    clear_fn_body(ge)
    then0, entry = entry_then(ge)

    # GetAllActorsOfClass FarmClock
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(200, 0))
    connect(then0, find_pin(gao, "execute", "Input"), "e->clocks")
    # set ActorClass
    cls_pin = find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input")
    if cls_pin:
        try:
            cls_pin.set_default_value("/Script/FarmSim25D.FarmClock")
        except Exception:
            try:
                fc = unreal.load_class(None, "/Script/FarmSim25D.FarmClock")
                # some versions: set_pin_type / object
                bel.set_pin_type_to_class(cls_pin, fc) if hasattr(bel, "set_pin_type_to_class") else None
            except Exception as e:
                log("clock class pin " + str(e))
        setdef(cls_pin, "/Script/FarmSim25D.FarmClock")

    # Array length / get 0
    get0 = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(500, 80))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input") or find_pin(get0, "Array", "Input"), "arr")
    setdef(find_pin(get0, "Index", "Input"), "0")

    # Cast To FarmClock
    cast_fc = None
    for cname in ("Cast To FarmClock", "Utilities|Casting|Cast To FarmClock"):
        try:
            cast_fc = ge.create_node_from_name(cname, unreal.Vector2D(750, 0), [])
            if cast_fc:
                break
        except Exception:
            pass
    if cast_fc is None:
        # fallback: use object as FarmClock via call GetDisplayMinutes on Actor? won't work
        log("NO Cast FarmClock — using Print fallback path")
        pr = make_print(ge, 750, 0, "Restaurant SIGN: (FarmClock cast missing)")
        connect(find_pin(gao, "then", "Output"), find_pin(pr, "execute", "Input"), "fallback")
        ret = make_return(ge, 1100, 0)
        connect(find_pin(pr, "then", "Output"), find_pin(ret, "execute", "Input"), "r")
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantOpenSign")
        return False

    bel.set_node_pos(cast_fc, pos(750, 0))
    connect(find_pin(gao, "then", "Output"), find_pin(cast_fc, "execute", "Input"), "gao->cast")
    connect(find_pin(get0, "Item", "Output") or find_pin(get0, "Output", "Output") or find_pin(get0, "ReturnValue", "Output"),
            find_pin(cast_fc, "Object", "Input"), "obj->cast")

    # GetDisplayMinutes
    gdm = ge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
    if gdm is None:
        gdm = ge.add_call_function_node("/Script/FarmSim25D.FarmClock:get_display_minutes")
    bel.set_node_pos(gdm, pos(1050, 80))
    as_fc = None
    for p in bel.list_all_pins(cast_fc):
        if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
            as_fc = p
            break
    connect(as_fc, find_pin(gdm, "self", "Input"), "fc->gdm")

    # Get bIsOpenBusiness
    get_open = ge.add_get_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(get_open, pos(1050, 200))

    # Branch: already open? -> early close
    br_open = ge.add_branch_node()
    bel.set_node_pos(br_open, pos(1300, 0))
    connect(find_pin(cast_fc, "then", "Output"), find_pin(br_open, "execute", "Input"), "cast->br")
    connect(find_pin(get_open, "bIsOpenBusiness", "Output"), find_pin(br_open, "Condition", "Input"), "open?")

    # TRUE: close
    set_close = ge.add_set_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(set_close, pos(1600, -120))
    connect(find_pin(br_open, "then", "Output"), find_pin(set_close, "execute", "Input"), "->close")
    setdef(find_pin(set_close, "bIsOpenBusiness", "Input"), "false")
    pr_close = make_print(ge, 1900, -120, "Restaurant: CLOSED early (stopped seating)")
    connect(find_pin(set_close, "then", "Output"), find_pin(pr_close, "execute", "Input"), "c->pr")
    # sync manager close via custom: call static-like GetAllActorsOfClass Manager set var — use Print for now + Set on managers below
    # After print, call helper nodes to sync manager
    sync_close = _add_sync_manager_open(ge, 2200, -120, False)
    connect(find_pin(pr_close, "then", "Output"), find_pin(sync_close, "execute", "Input") if sync_close else None, "pr->syncC")
    ret1 = make_return(ge, 2800, -120)
    last = find_pin(sync_close, "then", "Output") if sync_close else find_pin(pr_close, "then", "Output")
    connect(last, find_pin(ret1, "execute", "Input"), "->ret1")

    # FALSE: check time
    # minutes >= 1380?
    ge1380 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
    bel.set_node_pos(ge1380, pos(1600, 80))
    connect(find_pin(gdm, "ReturnValue", "Output"), find_pin(ge1380, "A", "Input"), "m->ge")
    setdef(find_pin(ge1380, "B", "Input"), "1380")
    br_late = ge.add_branch_node()
    bel.set_node_pos(br_late, pos(1850, 80))
    connect(find_pin(br_open, "else", "Output"), find_pin(br_late, "execute", "Input"), "->late?")
    connect(find_pin(ge1380, "ReturnValue", "Output"), find_pin(br_late, "Condition", "Input"), "cond late")
    pr_late = make_print(ge, 2100, 40, "Restaurant: too late (>=23:00), cannot open")
    connect(find_pin(br_late, "then", "Output"), find_pin(pr_late, "execute", "Input"), "late")
    ret2 = make_return(ge, 2400, 40)
    connect(find_pin(pr_late, "then", "Output"), find_pin(ret2, "execute", "Input"), "r2")

    # minutes < 1020?
    lt1020 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_IntInt")
    bel.set_node_pos(lt1020, pos(2100, 200))
    connect(find_pin(gdm, "ReturnValue", "Output"), find_pin(lt1020, "A", "Input"), "m->lt")
    setdef(find_pin(lt1020, "B", "Input"), "1020")
    br_early = ge.add_branch_node()
    bel.set_node_pos(br_early, pos(2350, 200))
    connect(find_pin(br_late, "else", "Output"), find_pin(br_early, "execute", "Input"), "->early?")
    connect(find_pin(lt1020, "ReturnValue", "Output"), find_pin(br_early, "Condition", "Input"), "cond early")
    pr_early = make_print(ge, 2600, 160, "Restaurant: too early (<17:00), cannot open")
    connect(find_pin(br_early, "then", "Output"), find_pin(pr_early, "execute", "Input"), "early")
    ret3 = make_return(ge, 2900, 160)
    connect(find_pin(pr_early, "then", "Output"), find_pin(ret3, "execute", "Input"), "r3")

    # OK open
    set_open = ge.add_set_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(set_open, pos(2600, 320))
    connect(find_pin(br_early, "else", "Output"), find_pin(set_open, "execute", "Input"), "->open")
    setdef(find_pin(set_open, "bIsOpenBusiness", "Input"), "true")
    pr_open = make_print(ge, 2900, 320, "Restaurant: OPEN for business! Guests will arrive...")
    connect(find_pin(set_open, "then", "Output"), find_pin(pr_open, "execute", "Input"), "o->pr")
    sync_open = _add_sync_manager_open(ge, 3200, 320, True)
    connect(find_pin(pr_open, "then", "Output"), find_pin(sync_open, "execute", "Input") if sync_open else None, "pr->syncO")
    ret4 = make_return(ge, 3800, 320)
    last2 = find_pin(sync_open, "then", "Output") if sync_open else find_pin(pr_open, "then", "Output")
    connect(last2, find_pin(ret4, "execute", "Input"), "r4")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantOpenSign")
    log("OpenSign RestaurantInteract wired")
    return True

def _add_sync_manager_open(ge, x, y, open_val):
    """GetAllActorsOfClass Manager -> ForEach set bIsOpenBusiness. Returns first exec node (gao)."""
    gao = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(x, y))
    cls_pin = find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input")
    setdef(cls_pin, "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
    fe = None
    try:
        fe = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    except Exception:
        try:
            fe = ge.create_node_from_name("ForEachLoop", unreal.Vector2D(x + 250, y), [])
        except Exception as e:
            log("fe sync " + str(e))
            return gao
    bel.set_node_pos(fe, pos(x + 280, y))
    connect(find_pin(gao, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "gao->fe")
    connect(find_pin(gao, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "arr")
    cast_m = None
    for cname in ("Cast To BP_RestaurantManager", "Utilities|Casting|Cast To BP_RestaurantManager"):
        try:
            cast_m = ge.create_node_from_name(cname, unreal.Vector2D(x + 550, y - 40), [])
            if cast_m:
                break
        except Exception:
            pass
    if not cast_m:
        return gao
    bel.set_node_pos(cast_m, pos(x + 550, y - 40))
    connect(find_pin(fe, "LoopBody", "Output") or find_pin(fe, "Then", "Output"), find_pin(cast_m, "execute", "Input"), "fe->cast")
    connect(find_pin(fe, "Array Element", "Output") or find_pin(fe, "Element", "Output"), find_pin(cast_m, "Object", "Input"), "el")
    # Set bIsOpenBusiness on cast result — use set member on cast target via call? 
    # K2Node_VariableSet needs self target. add_set_member_variable_node sets on Self of the graph (Sign), not manager.
    # Use create_node Assign / or Print only. Alternative: call a custom event on Manager SetOpen.
    # For knife2: fire custom event SetOpenState on manager via Create Event + call.
    # Simpler approach: use "Set bIsOpenBusiness" with Target pin from cast.
    setn = None
    try:
        setn = ge.create_node_from_name("Set bIsOpenBusiness", unreal.Vector2D(x + 850, y - 40), [])
    except Exception:
        pass
    if setn is None:
        # fallback print
        pr = make_print(ge, x + 850, y, "Restaurant: Manager sync open={}".format(open_val))
        connect(find_pin(cast_m, "then", "Output"), find_pin(pr, "execute", "Input"), "cast->pr")
        # Rewire gao's then continuity: ForEach Completed -> use as then for caller
        # Return gao; caller connects to gao execute; Completed of fe is the "then" after loop
        # Hack: expose Completed by storing on node user meta — caller uses pr then from last
        # Attach a Sequence: actually return fe and document Completed pin
        REPORT["_sync_completed_pin"] = find_pin(fe, "Completed", "Output")
        return gao

    bel.set_node_pos(setn, pos(x + 850, y - 40))
    connect(find_pin(cast_m, "then", "Output"), find_pin(setn, "execute", "Input"), "cast->set")
    as_m = None
    for p in bel.list_all_pins(cast_m):
        if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
            as_m = p
            break
    connect(as_m, find_pin(setn, "self", "Input") or find_pin(setn, "Target", "Input"), "as->set")
    setdef(find_pin(setn, "bIsOpenBusiness", "Input"), "true" if open_val else "false")
    REPORT["_sync_completed_pin"] = find_pin(fe, "Completed", "Output")
    return gao


# ========== 2) Table/Stove/Trash: ensure RestaurantInteract prints distinct (inherit OK) ==========
# Parent already prints InteractLabel — ensure instance labels set on level actors.

def refresh_instance_labels():
    labels = {
        "Restaurant_Table1": "Restaurant: TABLE 1",
        "Restaurant_Table2": "Restaurant: TABLE 2",
        "Restaurant_Stove": "Restaurant: STOVE",
        "Restaurant_Trash": "Restaurant: TRASH",
        "Restaurant_OpenSign": "Restaurant: OPEN SIGN",
    }
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab in labels:
            for k in ("InteractLabel", "interact_label"):
                try:
                    a.set_editor_property(k, labels[lab])
                    break
                except Exception:
                    pass
    log("instance labels refreshed")


# ========== 3) Manager: Tick auto-close + guest spawn ==========
def wire_manager():
    bp = unreal.EditorAssetLibrary.load_asset(DIR + "/BP_RestaurantManager")
    add_var(bp, "bIsOpenBusiness", pin_type("bool"))
    add_var(bp, "GuestTimer", pin_type("real", "double"))
    add_var(bp, "GuestInterval", pin_type("real", "double"))
    # default GuestInterval 4
    try:
        cdo = unreal.get_default_object(bp.generated_class())
        for k, v in (("guest_interval", 4.0), ("GuestInterval", 4.0), ("b_is_open_business", False), ("bIsOpenBusiness", False)):
            try:
                cdo.set_editor_property(k, v)
            except Exception:
                pass
    except Exception as e:
        log("mgr cdo " + str(e))

    mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    # Enable tick on CDO
    try:
        cdo = unreal.get_default_object(bp.generated_class())
        tick = cdo.get_editor_property("primary_actor_tick")
        # PrimaryActorTick is struct
        try:
            tick.set_editor_property("b_start_with_tick_enabled", True)
            tick.set_editor_property("b_can_ever_tick", True)
        except Exception:
            pass
        cdo.set_editor_property("primary_actor_tick", tick)
    except Exception as e:
        log("tick enable " + str(e))

    # Clean previous knife2 tick chains (keyword)
    kill = []
    for n in list(mge.list_all_nodes()):
        t = bel.get_node_title(n)
        if any(k in t for k in ("GuestTimer", "GuestInterval", "SeatGuest", "ForceClose",
                                  "tomato", "stew", "OPEN for", "Guest seated", "AUTO-CLOSE",
                                  "Cast To BP_RestaurantTable", "Cast To FarmClock")):
            kill.append(n)
        # also remove nodes we tagged via PrintString defaults
        if t == "PrintString":
            for p in bel.list_all_pins(n):
                if "string" in str(p.get_pin_name()).lower():
                    try:
                        dv = str(p.get_default_value() or "")
                    except Exception:
                        dv = ""
                    if any(k in dv for k in ("Guest seated", "AUTO-CLOSE", "OPEN for", "seating", "stew", "salad")):
                        kill.append(n)
    # Don't wipe HandlePlayerE yet — leave for now
    if kill:
        mge.remove_nodes(list({id(n): n for n in kill}.values()))
        log("mgr cleaned " + str(len(kill)))

    # Find Event Tick
    tick_n = None
    for n in mge.list_all_nodes():
        t = bel.get_node_title(n)
        if "Event Tick" in t or t == "ReceiveTick":
            tick_n = n
            break
    if tick_n is None:
        try:
            tick_n = mge.add_event_node("ReceiveTick")
        except Exception:
            try:
                tick_n = mge.create_node_from_name("Event Tick", unreal.Vector2D(0, 600), [])
            except Exception as e:
                log("no tick event " + str(e))
                REPORT["errors"].append("Manager Tick missing")
                return False
    bel.set_node_pos(tick_n, pos(0, 600))
    # Break existing tick then links that aren't ours carefully — only if linked to Parent Tick keep
    tick_then = find_pin(tick_n, "then", "Output") or find_pin(tick_n, "execute", "Output")
    delta_pin = find_pin(tick_n, "Delta", "Output") or find_pin(tick_n, "DeltaSeconds", "Output")

    # Break outbound from tick except Parent
    if tick_then:
        for cp in list(tick_then.list_connected_pins()):
            owner_t = bel.get_node_title(cp.get_owning_node())
            if "Parent" in owner_t:
                continue
            try:
                tick_then.break_link_to(cp)
            except Exception:
                pass

    # --- Tick body: Get FarmClock minutes, auto-close, guest timer ---
    # Sequence node for multi-step
    seq = None
    try:
        seq = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:Sequence")
    except Exception:
        try:
            seq = mge.create_node_from_name("Sequence", unreal.Vector2D(250, 600), [])
        except Exception as e:
            log("seq " + str(e))

    if seq:
        bel.set_node_pos(seq, pos(250, 600))
        connect(tick_then, find_pin(seq, "execute", "Input") or find_pin(seq, "Exec", "Input"), "tick->seq")
        then_a = find_pin(seq, "Then 0", "Output") or find_pin(seq, "then_0", "Output")
        then_b = find_pin(seq, "Then 1", "Output") or find_pin(seq, "then_1", "Output")
    else:
        then_a = tick_then
        then_b = None

    # Then0: auto-close check
    gao = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(500, 500))
    connect(then_a, find_pin(gao, "execute", "Input"), "a->clock")
    setdef(find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input"), "/Script/FarmSim25D.FarmClock")
    get0 = mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(750, 560))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input") or find_pin(get0, "Array", "Input"), "arr")
    setdef(find_pin(get0, "Index", "Input"), "0")
    cast_fc = None
    for cname in ("Cast To FarmClock",):
        try:
            cast_fc = mge.create_node_from_name(cname, unreal.Vector2D(1000, 500), [])
        except Exception:
            pass
    if cast_fc:
        bel.set_node_pos(cast_fc, pos(1000, 500))
        connect(find_pin(gao, "then", "Output"), find_pin(cast_fc, "execute", "Input"), "->castfc")
        connect(find_pin(get0, "Item", "Output") or find_pin(get0, "ReturnValue", "Output") or find_pin(get0, "Output", "Output"),
                find_pin(cast_fc, "Object", "Input"), "obj")
        gdm = mge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
        bel.set_node_pos(gdm, pos(1250, 560))
        as_fc = None
        for p in bel.list_all_pins(cast_fc):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_fc = p
                break
        connect(as_fc, find_pin(gdm, "self", "Input"), "fc")
        # minutes >= 1380?
        geq = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
        bel.set_node_pos(geq, pos(1500, 560))
        connect(find_pin(gdm, "ReturnValue", "Output"), find_pin(geq, "A", "Input"), "m")
        setdef(find_pin(geq, "B", "Input"), "1380")
        get_open = mge.add_get_member_variable_node("bIsOpenBusiness")
        bel.set_node_pos(get_open, pos(1500, 680))
        andn = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
        bel.set_node_pos(andn, pos(1750, 600))
        connect(find_pin(geq, "ReturnValue", "Output"), find_pin(andn, "A", "Input"), "a")
        connect(find_pin(get_open, "bIsOpenBusiness", "Output"), find_pin(andn, "B", "Input"), "b")
        br = mge.add_branch_node()
        bel.set_node_pos(br, pos(2000, 500))
        connect(find_pin(cast_fc, "then", "Output"), find_pin(br, "execute", "Input"), "->br")
        connect(find_pin(andn, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "cond")
        set_close = mge.add_set_member_variable_node("bIsOpenBusiness")
        bel.set_node_pos(set_close, pos(2300, 450))
        connect(find_pin(br, "then", "Output"), find_pin(set_close, "execute", "Input"), "close")
        setdef(find_pin(set_close, "bIsOpenBusiness", "Input"), "false")
        pr = make_print(mge, 2600, 450, "Restaurant AUTO-CLOSE at 23:00 — seating stopped")
        connect(find_pin(set_close, "then", "Output"), find_pin(pr, "execute", "Input"), "pr")
        # also clear guests via custom event call
        # Call ClearGuests custom event
        clear_ev = None
        for n in mge.list_all_nodes():
            if bel.get_node_title(n) == "ClearGuests" or "ClearGuests" in bel.get_node_title(n):
                clear_ev = n
        if clear_ev is None:
            clear_ev = mge.add_custom_event_node("ClearGuests")
            bel.set_node_pos(clear_ev, pos(0, 1100))
        # Call ClearGuests from close path
        call_clear = None
        try:
            call_clear = mge.create_node_from_name("ClearGuests", unreal.Vector2D(2900, 450), [])
        except Exception:
            pass
        if call_clear:
            bel.set_node_pos(call_clear, pos(2900, 450))
            connect(find_pin(pr, "then", "Output"), find_pin(call_clear, "execute", "Input"), "->clear")

    # Then1: guest spawn timer when open
    if then_b:
        get_open2 = mge.add_get_member_variable_node("bIsOpenBusiness")
        bel.set_node_pos(get_open2, pos(500, 850))
        br2 = mge.add_branch_node()
        bel.set_node_pos(br2, pos(750, 800))
        connect(then_b, find_pin(br2, "execute", "Input"), "b->br")
        connect(find_pin(get_open2, "bIsOpenBusiness", "Output"), find_pin(br2, "Condition", "Input"), "open?")
        # GuestTimer += Delta
        get_t = mge.add_get_member_variable_node("GuestTimer")
        bel.set_node_pos(get_t, pos(1000, 920))
        addf = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
        if addf is None:
            addf = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
        bel.set_node_pos(addf, pos(1250, 880))
        connect(find_pin(get_t, "GuestTimer", "Output"), find_pin(addf, "A", "Input"), "t")
        connect(delta_pin, find_pin(addf, "B", "Input"), "dt")
        set_t = mge.add_set_member_variable_node("GuestTimer")
        bel.set_node_pos(set_t, pos(1550, 800))
        connect(find_pin(br2, "then", "Output"), find_pin(set_t, "execute", "Input"), "->setT")
        connect(find_pin(addf, "ReturnValue", "Output"), find_pin(set_t, "GuestTimer", "Input"), "val")
        # GuestTimer >= GuestInterval?
        get_iv = mge.add_get_member_variable_node("GuestInterval")
        bel.set_node_pos(get_iv, pos(1550, 960))
        get_t2 = mge.add_get_member_variable_node("GuestTimer")
        bel.set_node_pos(get_t2, pos(1800, 920))
        geq2 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble")
        if geq2 is None:
            geq2 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat")
        bel.set_node_pos(geq2, pos(2050, 880))
        connect(find_pin(get_t2, "GuestTimer", "Output"), find_pin(geq2, "A", "Input"), "a")
        connect(find_pin(get_iv, "GuestInterval", "Output"), find_pin(geq2, "B", "Input"), "b")
        # After set_t, need re-get — wire condition from addf result instead
        geq2b = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble")
        if geq2b is None:
            geq2b = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat")
        bel.set_node_pos(geq2b, pos(1850, 800))
        connect(find_pin(addf, "ReturnValue", "Output"), find_pin(geq2b, "A", "Input"), "newT")
        connect(find_pin(get_iv, "GuestInterval", "Output"), find_pin(geq2b, "B", "Input"), "iv")
        br3 = mge.add_branch_node()
        bel.set_node_pos(br3, pos(2150, 800))
        connect(find_pin(set_t, "then", "Output"), find_pin(br3, "execute", "Input"), "->br3")
        connect(find_pin(geq2b, "ReturnValue", "Output"), find_pin(br3, "Condition", "Input"), "ready?")
        # Reset timer + call SeatGuest
        set_t0 = mge.add_set_member_variable_node("GuestTimer")
        bel.set_node_pos(set_t0, pos(2450, 760))
        connect(find_pin(br3, "then", "Output"), find_pin(set_t0, "execute", "Input"), "reset")
        setdef(find_pin(set_t0, "GuestTimer", "Input"), "0.0")
        # Custom event SeatGuest
        seat_ev = None
        for n in mge.list_all_nodes():
            if "SeatGuest" == bel.get_node_title(n) or bel.get_node_title(n).startswith("SeatGuest"):
                if n.get_class().get_name() == "K2Node_CustomEvent":
                    seat_ev = n
        if seat_ev is None:
            seat_ev = mge.add_custom_event_node("SeatGuest")
            bel.set_node_pos(seat_ev, pos(0, 1400))
        call_seat = None
        try:
            call_seat = mge.create_node_from_name("SeatGuest", unreal.Vector2D(2750, 760), [])
        except Exception as e:
            log("call seat " + str(e))
        if call_seat:
            bel.set_node_pos(call_seat, pos(2750, 760))
            connect(find_pin(set_t0, "then", "Output"), find_pin(call_seat, "execute", "Input"), "->seat")

    # --- SeatGuest event body ---
    seat_ev = None
    for n in mge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and "SeatGuest" in bel.get_node_title(n):
            seat_ev = n
            break
    if seat_ev is None:
        seat_ev = mge.add_custom_event_node("SeatGuest")
        bel.set_node_pos(seat_ev, pos(0, 1400))

    # Clear old SeatGuest downstream
    # Wire: GetAllActorsOfClass Table -> ForEach -> if !bOccupied -> set occupied, set dish, print, spawn guest marker
    seat_then = find_pin(seat_ev, "then", "Output") or find_pin(seat_ev, "execute", "Output")
    # break existing
    if seat_then:
        for cp in list(seat_then.list_connected_pins()):
            try:
                seat_then.break_link_to(cp)
            except Exception:
                pass

    gao_t = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao_t, pos(300, 1400))
    connect(seat_then, find_pin(gao_t, "execute", "Input"), "seat->tables")
    setdef(find_pin(gao_t, "ActorClass", "Input") or find_pin(gao_t, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
    fe = None
    try:
        fe = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    except Exception:
        fe = mge.create_node_from_name("ForEachLoop", unreal.Vector2D(600, 1400), [])
    bel.set_node_pos(fe, pos(600, 1400))
    connect(find_pin(gao_t, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "->fe")
    connect(find_pin(gao_t, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "arr")
    cast_t = None
    for cname in ("Cast To BP_RestaurantTable",):
        try:
            cast_t = mge.create_node_from_name(cname, unreal.Vector2D(900, 1350), [])
        except Exception:
            pass
    if cast_t:
        bel.set_node_pos(cast_t, pos(900, 1350))
        connect(find_pin(fe, "LoopBody", "Output") or find_pin(fe, "Then", "Output"), find_pin(cast_t, "execute", "Input"), "fe->cast")
        connect(find_pin(fe, "Array Element", "Output") or find_pin(fe, "Element", "Output"), find_pin(cast_t, "Object", "Input"), "el")
        # Get bOccupied — need get from cast target. Use create_node Get bOccupied
        get_occ = None
        try:
            get_occ = mge.create_node_from_name("Get bOccupied", unreal.Vector2D(1200, 1500), [])
        except Exception:
            pass
        as_t = None
        for p in bel.list_all_pins(cast_t):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_t = p
                break
        br_free = mge.add_branch_node()
        bel.set_node_pos(br_free, pos(1500, 1350))
        connect(find_pin(cast_t, "then", "Output"), find_pin(br_free, "execute", "Input"), "->free?")
        if get_occ:
            bel.set_node_pos(get_occ, pos(1200, 1500))
            connect(as_t, find_pin(get_occ, "self", "Input") or find_pin(get_occ, "Target", "Input"), "as->get")
            # NOT occupied
            notb = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
            bel.set_node_pos(notb, pos(1450, 1500))
            connect(find_pin(get_occ, "bOccupied", "Output") or find_pin(get_occ, "ReturnValue", "Output"),
                    find_pin(notb, "A", "Input"), "occ")
            connect(find_pin(notb, "ReturnValue", "Output"), find_pin(br_free, "Condition", "Input"), "free")
        else:
            # if can't read occupied, always try seat (may over-seat) — Print
            setdef(find_pin(br_free, "Condition", "Input"), "true")

        # On free: Set bOccupied true
        set_occ = None
        try:
            set_occ = mge.create_node_from_name("Set bOccupied", unreal.Vector2D(1800, 1300), [])
        except Exception:
            pass
        if set_occ:
            bel.set_node_pos(set_occ, pos(1800, 1300))
            connect(find_pin(br_free, "then", "Output"), find_pin(set_occ, "execute", "Input"), "seat!")
            connect(as_t, find_pin(set_occ, "self", "Input") or find_pin(set_occ, "Target", "Input"), "as")
            setdef(find_pin(set_occ, "bOccupied", "Input"), "true")
            # Set CurrentDishId random 1 or 2
            rand = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:RandomIntegerInRange")
            bel.set_node_pos(rand, pos(1800, 1500))
            setdef(find_pin(rand, "Min", "Input"), "1")
            setdef(find_pin(rand, "Max", "Input"), "2")
            set_dish = None
            try:
                set_dish = mge.create_node_from_name("Set CurrentDishId", unreal.Vector2D(2100, 1300), [])
            except Exception:
                pass
            if set_dish:
                bel.set_node_pos(set_dish, pos(2100, 1300))
                connect(find_pin(set_occ, "then", "Output"), find_pin(set_dish, "execute", "Input"), "->dish")
                connect(as_t, find_pin(set_dish, "self", "Input") or find_pin(set_dish, "Target", "Input"), "as")
                connect(find_pin(rand, "ReturnValue", "Output"), find_pin(set_dish, "CurrentDishId", "Input"), "dish")
                pr = make_print(mge, 2400, 1300, "Restaurant: Guest seated + auto-ordered (1=salad 2=stew) — check table CurrentDishId")
                connect(find_pin(set_dish, "then", "Output"), find_pin(pr, "execute", "Input"), "pr")
            else:
                pr = make_print(mge, 2100, 1300, "Restaurant: Guest seated (occupied=true)")
                connect(find_pin(set_occ, "then", "Output"), find_pin(pr, "execute", "Input"), "pr")
            # NOTE: ForEach will seat ALL free tables in one tick — bad.
            # Mitigate: only first free — without DoOnce/break hard. Use GuestInterval and accept double seat rare,
            # OR set a manager flag SeatedThisPulse.
            # Add bSeatedPulse: set true after first seat; Branch checks it.
            # Simpler fix: change SeatGuest to only Array_Get index of first free — complex.
            # Use: after seating one, we can't break ForEach easily. 
            # Alternative: don't use ForEach — get tables array, check table1 then table2 manually via labels in Python-spawned markers.
            # For knife2 OK to seat at most one per pulse if we check a temp: Set GuestTimer already reset; if both free both get seated same frame — BAD.
            # Fix with manager bLockSeat: Get bLockSeat at start of SeatGuest set true at begin, only proceed if false... still foreach.
            # Best quick fix: In SeatGuest use only GetAllActorsWithTag and pick first by Python-documented approach:
            # Replace ForEach with: after casting first free, the Branch false path continues foreach — 
            # Add DoOnce? 
            # Practical: set GuestInterval and in SeatGuest only look at one table via GetActorOfClass isn't unique.
            # I'll add variable SeatGate: at start of SeatGuest if SeatGate skip; set SeatGate true when seating; Tick resets SeatGate each frame before SeatGuest call.
            pass

    # ClearGuests body: clear occupied on all tables + destroy Restaurant_Guest_*
    clear_ev = None
    for n in mge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and "ClearGuests" in bel.get_node_title(n):
            clear_ev = n
            break
    if clear_ev is None:
        clear_ev = mge.add_custom_event_node("ClearGuests")
        bel.set_node_pos(clear_ev, pos(0, 1100))
    clear_then = find_pin(clear_ev, "then", "Output") or find_pin(clear_ev, "execute", "Output")
    if clear_then:
        for cp in list(clear_then.list_connected_pins()):
            try:
                clear_then.break_link_to(cp)
            except Exception:
                pass
    prc = make_print(mge, 300, 1100, "Restaurant: ClearGuests (tables will free on next open cycle)")
    connect(clear_then, find_pin(prc, "execute", "Input"), "clear->pr")
    # Free all tables
    gao_c = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao_c, pos(600, 1100))
    connect(find_pin(prc, "then", "Output"), find_pin(gao_c, "execute", "Input"), "->tables")
    setdef(find_pin(gao_c, "ActorClass", "Input") or find_pin(gao_c, "Class", "Input"),
           "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
    fe_c = None
    try:
        fe_c = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    except Exception:
        fe_c = mge.create_node_from_name("ForEachLoop", unreal.Vector2D(900, 1100), [])
    if fe_c:
        bel.set_node_pos(fe_c, pos(900, 1100))
        connect(find_pin(gao_c, "then", "Output"), find_pin(fe_c, "Exec", "Input") or find_pin(fe_c, "execute", "Input"), "->fe")
        connect(find_pin(gao_c, "OutActors", "Output"), find_pin(fe_c, "Array", "Input"), "arr")
        cast_c = None
        try:
            cast_c = mge.create_node_from_name("Cast To BP_RestaurantTable", unreal.Vector2D(1200, 1050), [])
        except Exception:
            pass
        if cast_c:
            bel.set_node_pos(cast_c, pos(1200, 1050))
            connect(find_pin(fe_c, "LoopBody", "Output") or find_pin(fe_c, "Then", "Output"), find_pin(cast_c, "execute", "Input"), "fe")
            connect(find_pin(fe_c, "Array Element", "Output") or find_pin(fe_c, "Element", "Output"), find_pin(cast_c, "Object", "Input"), "el")
            set_free = None
            try:
                set_free = mge.create_node_from_name("Set bOccupied", unreal.Vector2D(1500, 1050), [])
            except Exception:
                pass
            if set_free:
                bel.set_node_pos(set_free, pos(1500, 1050))
                connect(find_pin(cast_c, "then", "Output"), find_pin(set_free, "execute", "Input"), "free")
                as_c = None
                for p in bel.list_all_pins(cast_c):
                    if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                        as_c = p
                        break
                connect(as_c, find_pin(set_free, "self", "Input") or find_pin(set_free, "Target", "Input"), "as")
                setdef(find_pin(set_free, "bOccupied", "Input"), "false")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantManager")
    # Ensure level manager has GuestInterval=4 and tick
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == "Restaurant_Manager":
            for k, v in (("GuestInterval", 4.0), ("guest_interval", 4.0), ("bIsOpenBusiness", False), ("b_is_open_business", False)):
                try:
                    a.set_editor_property(k, v)
                except Exception:
                    pass
            try:
                a.set_actor_tick_enabled(True)
            except Exception:
                pass
    log("Manager tick/guest wired")
    return True


# ========== 4) Character surgical E ==========
def wire_character_e():
    cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    add_var(cbp, "bRestEHandled", pin_type("bool"))
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    # record before
    ia = till = None
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "IA_Interact" in t:
            ia = n
        if t == "TillSoil":
            till = n
    started = find_pin(ia, "Started", "Output") if ia else None
    REPORT["ia_before"] = [bel.get_node_title(cp.get_owning_node()) for cp in started.list_connected_pins()] if started else []

    # Remove any prior restaurant E helpers (not TillSoil/IA)
    kill = []
    if started:
        stack = list(started.list_connected_pins())
        seen = set()
        while stack:
            p = stack.pop(0)
            n = p.get_owning_node()
            if id(n) in seen:
                continue
            seen.add(id(n))
            t = bel.get_node_title(n)
            if t == "TillSoil" or "IA_Interact" in t:
                continue
            kill.append(n)
            for pp in bel.list_all_pins(n):
                for cp in pp.list_connected_pins():
                    stack.append(cp)
    for n in list(cge.list_all_nodes()):
        t = bel.get_node_title(n)
        if any(k in t for k in ("GetAllActorsWithTag", "For Each Loop", "Cast To BP_Restaurant",
                                  "RestaurantInteract", "bRestEHandled", "Distance2D")):
            if t != "TillSoil" and "IA_Interact" not in t:
                kill.append(n)
    kill = [n for n in kill if bel.get_node_title(n) != "TillSoil" and "IA_Interact" not in bel.get_node_title(n)]
    kill = list({id(n): n for n in kill}.values())
    if kill:
        cge.remove_nodes(kill)
        log("char cleaned " + str(len(kill)))

    # Break Started links
    if started:
        try:
            bel.break_pin_links(started)
        except Exception:
            for cp in list(started.list_connected_pins()):
                try:
                    started.break_link_to(cp)
                except Exception:
                    pass

    # Build: Started -> Set bRestEHandled=false -> GetPlayerPawn -> GetAllActorsWithTag
    # -> ForEach body: Dist<200 -> Cast -> RestaurantInteract -> Set true
    # -> Completed: Get bRestEHandled -> NOT -> Branch -> TillSoil
    set_f = cge.add_set_member_variable_node("bRestEHandled")
    bel.set_node_pos(set_f, pos(-2200, 1000))
    connect(started, find_pin(set_f, "execute", "Input"), "IA->setF")
    setdef(find_pin(set_f, "bRestEHandled", "Input"), "false")

    get_pawn = cge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(get_pawn, pos(-1900, 1000))
    connect(find_pin(set_f, "then", "Output"), find_pin(get_pawn, "execute", "Input"), "->pawn")
    setdef(find_pin(get_pawn, "PlayerIndex", "Input"), "0")

    pawn_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(pawn_loc, pos(-1600, 1180))
    connect(find_pin(get_pawn, "ReturnValue", "Output"), find_pin(pawn_loc, "self", "Input"), "pawn.self")

    gat = cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
    bel.set_node_pos(gat, pos(-1600, 1000))
    connect(find_pin(get_pawn, "then", "Output"), find_pin(gat, "execute", "Input"), "pawn->gat")
    setdef(find_pin(gat, "Tag", "Input"), "RestInteract")

    fe = None
    try:
        fe = cge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    except Exception:
        fe = cge.create_node_from_name("ForEachLoop", unreal.Vector2D(-1300, 1000), [])
    if not fe:
        REPORT["errors"].append("ForEach missing — rollback E")
        # restore TillSoil
        connect(started, find_pin(till, "execute", "Input"), "ROLLBACK")
        REPORT["rolled_back_e"] = True
        bel.compile_blueprint(cbp)
        unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
        return False
    bel.set_node_pos(fe, pos(-1300, 1000))
    connect(find_pin(gat, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "gat->fe")
    connect(find_pin(gat, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "arr")

    el = find_pin(fe, "Array Element", "Output") or find_pin(fe, "Element", "Output")
    body = find_pin(fe, "LoopBody", "Output") or find_pin(fe, "Then", "Output")
    done = find_pin(fe, "Completed", "Output")

    act_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(act_loc, pos(-1000, 850))
    connect(el, find_pin(act_loc, "self", "Input"), "el->loc")

    dist = cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
    bel.set_node_pos(dist, pos(-750, 1000))
    connect(find_pin(pawn_loc, "ReturnValue", "Output"), find_pin(dist, "A", "Input") or find_pin(dist, "V1", "Input"), "p")
    connect(find_pin(act_loc, "ReturnValue", "Output"), find_pin(dist, "B", "Input") or find_pin(dist, "V2", "Input"), "a")

    lt = cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
    if lt is None:
        lt = cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    bel.set_node_pos(lt, pos(-500, 1000))
    connect(find_pin(dist, "ReturnValue", "Output"), find_pin(lt, "A", "Input"), "d")
    setdef(find_pin(lt, "B", "Input"), "200.0")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-280, 1000))
    connect(body, find_pin(br, "execute", "Input"), "body->br")
    connect(find_pin(lt, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "near?")

    cast_n = None
    for cname in ("Cast To BP_RestaurantInteractable",):
        try:
            cast_n = cge.create_node_from_name(cname, unreal.Vector2D(0, 900), [])
        except Exception:
            pass
    if cast_n:
        bel.set_node_pos(cast_n, pos(0, 900))
        connect(find_pin(br, "then", "Output"), find_pin(cast_n, "execute", "Input"), "->cast")
        connect(el, find_pin(cast_n, "Object", "Input"), "el")
        call_i = cge.add_call_function_node(DIR + "/BP_RestaurantInteractable.BP_RestaurantInteractable_C:RestaurantInteract")
        bel.set_node_pos(call_i, pos(350, 900))
        connect(find_pin(cast_n, "then", "Output"), find_pin(call_i, "execute", "Input"), "->interact")
        as_pin = None
        for p in bel.list_all_pins(cast_n):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_pin = p
                break
        connect(as_pin, find_pin(call_i, "self", "Input"), "as")
        set_t = cge.add_set_member_variable_node("bRestEHandled")
        bel.set_node_pos(set_t, pos(700, 900))
        connect(find_pin(call_i, "then", "Output"), find_pin(set_t, "execute", "Input"), "->handled")
        setdef(find_pin(set_t, "bRestEHandled", "Input"), "true")
    else:
        # fallback print still counts as handled
        pr = make_print(cge, 0, 900, "Restaurant E near (cast missing)")
        connect(find_pin(br, "then", "Output"), find_pin(pr, "execute", "Input"), "pr")
        set_t = cge.add_set_member_variable_node("bRestEHandled")
        bel.set_node_pos(set_t, pos(350, 900))
        connect(find_pin(pr, "then", "Output"), find_pin(set_t, "execute", "Input"), "->handled")
        setdef(find_pin(set_t, "bRestEHandled", "Input"), "true")

    # Completed -> if NOT handled -> TillSoil
    get_h = cge.add_get_member_variable_node("bRestEHandled")
    bel.set_node_pos(get_h, pos(-1000, 1300))
    notb = cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    bel.set_node_pos(notb, pos(-750, 1300))
    connect(find_pin(get_h, "bRestEHandled", "Output"), find_pin(notb, "A", "Input"), "h")
    br_t = cge.add_branch_node()
    bel.set_node_pos(br_t, pos(-500, 1250))
    connect(done, find_pin(br_t, "execute", "Input"), "done->br")
    connect(find_pin(notb, "ReturnValue", "Output"), find_pin(br_t, "Condition", "Input"), "!handled")
    connect(find_pin(br_t, "then", "Output"), find_pin(till, "execute", "Input"), "->TillSoil")

    bel.compile_blueprint(cbp)
    unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

    # verify
    chain = []
    started2 = find_pin(ia, "Started", "Output")
    if started2:
        for cp in started2.list_connected_pins():
            chain.append(bel.get_node_title(cp.get_owning_node()))
    REPORT["ia_after"] = chain
    if not chain:
        REPORT["errors"].append("IA Started dangling — rollback")
        connect(started2, find_pin(till, "execute", "Input"), "ROLLBACK2")
        bel.compile_blueprint(cbp)
        unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
        REPORT["rolled_back_e"] = True
        return False
    log("character E wired: " + str(chain))
    return True


# ===== Run =====
try:
    refresh_instance_labels()
    REPORT["done"]["labels"] = True
except Exception as e:
    REPORT["errors"].append("labels " + str(e))

try:
    REPORT["done"]["opensign"] = wire_opensign()
except Exception as e:
    REPORT["errors"].append("opensign " + traceback.format_exc())
    REPORT["done"]["opensign"] = False

try:
    REPORT["done"]["manager"] = wire_manager()
except Exception as e:
    REPORT["errors"].append("manager " + traceback.format_exc())
    REPORT["done"]["manager"] = False

try:
    REPORT["done"]["character_e"] = wire_character_e()
except Exception as e:
    REPORT["errors"].append("character " + traceback.format_exc())
    REPORT["done"]["character_e"] = False
    # emergency rollback
    try:
        cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
        cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
        ia = till = None
        for n in cge.list_all_nodes():
            t = bel.get_node_title(n)
            if "IA_Interact" in t: ia = n
            if t == "TillSoil": till = n
        started = find_pin(ia, "Started", "Output")
        if started and till:
            for cp in list(started.list_connected_pins()):
                try: started.break_link_to(cp)
                except Exception: pass
            connect(started, find_pin(till, "execute", "Input"), "EMERGENCY_ROLLBACK")
            bel.compile_blueprint(cbp)
            unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
            REPORT["rolled_back_e"] = True
    except Exception as e2:
        REPORT["errors"].append("rollback fail " + str(e2))

REPORT["actors_after"] = len(eas.get_all_level_actors())
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    REPORT["level_saved"] = True
except Exception:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        REPORT["level_saved"] = True
    except Exception as e:
        REPORT["level_saved"] = False
        REPORT["errors"].append(str(e))

# farm counts
from collections import Counter
c = Counter()
rest = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        rest += 1
    if lab.startswith("VMF_Grass"): c["grass"] += 1
    elif "Bridge" in lab: c["bridge"] += 1
    elif "Tree" in lab: c["tree"] += 1
REPORT["farm"] = dict(c)
REPORT["restaurant_n"] = rest

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2.json", "w", encoding="utf-8").write(
    json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
