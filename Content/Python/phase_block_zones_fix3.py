# -*- coding: utf-8 -*-
"""TillCell rejects BlockedIndices; fix InitBlockedFromIndices LastIndex hardcodes; keep airwalls/soil delete."""
import unreal

TAG = "[BLOCK_FIX3]"
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
WIDTH = 40
HEIGHT = 40


def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    ns = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if ns in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def out0(node):
    if not node:
        return None
    try:
        return bel.find_output_pin_by_index(node, 0)
    except Exception:
        for p in bel.list_all_pins(node):
            if "OUTPUT" in str(p.get_pin_direction()).upper():
                return p
    return None


def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label + " a={} b={}".format(a, b))
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def set_val(pin, value, label=""):
    if not pin:
        log("no pin " + label)
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, pin.get_pin_value()))
    except Exception as ex:
        log("set {} : {}".format(label, ex))


def break_links(pin):
    if not pin:
        return
    try:
        pin.break_pin_links(False)
    except Exception:
        try:
            pin.break_pin_links()
        except Exception:
            pass


def dump_pins(node, label):
    for p in bel.list_all_pins(node):
        log("  pin[{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def rebuild_init():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    fname = "InitBlockedFromIndices"
    graph = bel.find_graph(bp, fname)
    if not graph:
        bel.add_function_graph(bp, fname)
        graph = bel.find_graph(bp, fname)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    entry = None
    to_del = [n for n in ge.list_all_nodes() if n.get_class().get_name() != "K2Node_FunctionEntry"]
    if to_del:
        ge.remove_nodes(to_del)
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

    # Simple init: Print + NO clear of PlotStates.
    # Blocking is enforced in TillCell via Array_Contains(BlockedIndices).
    # Still size PlotStates to W*H Empty so other ops work.
    clear_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Clear")
    bel.set_node_pos(clear_n, pos(250, 0))
    get_ps = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_ps, pos(50, 150))
    connect(find_pin(entry, "then", "Output"), find_pin(clear_n, "execute", "Input"), "e->clear")
    connect(out0(get_ps) or find_pin(get_ps, "PlotStates", "Output"),
            find_pin(clear_n, "TargetArray", "Input") or find_pin(clear_n, "Array", "Input"), "ps")

    forloop = ge.create_node_from_name("Utilities|FlowControl|ForLoop", unreal.Vector2D(550, 0), [])
    bel.set_node_pos(forloop, pos(550, 0))
    connect(find_pin(clear_n, "then", "Output"), find_pin(forloop, "execute", "Input"), "c->f")
    set_val(find_pin(forloop, "FirstIndex", "Input") or find_pin(forloop, "First", "Input"), "0", "first")
    set_val(find_pin(forloop, "LastIndex", "Input") or find_pin(forloop, "Last", "Input"),
            str(WIDTH * HEIGHT - 1), "last=1599")

    add_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Add")
    bel.set_node_pos(add_n, pos(900, 60))
    get_ps2 = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_ps2, pos(700, 200))
    connect(find_pin(forloop, "LoopBody", "Output"), find_pin(add_n, "execute", "Input"), "body")
    connect(out0(get_ps2) or find_pin(get_ps2, "PlotStates", "Output"),
            find_pin(add_n, "TargetArray", "Input") or find_pin(add_n, "Array", "Input"), "ps2")
    set_val(find_pin(add_n, "NewItem", "Input") or find_pin(add_n, "Item", "Input"), "0", "Empty")

    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(1200, 0))
    connect(find_pin(forloop, "Completed", "Output"), find_pin(pr, "execute", "Input"), "done")
    set_val(find_pin(pr, "InString", "Input"), "Grid ready (blocked via TillCell)", "msg")

    # Ensure BeginPlay -> Init
    eg = bel.find_graph(bp, "EventGraph") or bel.find_event_graph(bp)
    ege = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    begin = None
    try:
        begin = ege.find_event_node("ReceiveBeginPlay")
    except Exception:
        pass
    if not begin:
        for n in ege.list_all_nodes():
            if n.get_class().get_name() == "K2Node_Event":
                try:
                    t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
                except Exception:
                    t = ""
                if "BeginPlay" in t:
                    begin = n
                    break
    then = find_pin(begin, "then", "Output") if begin else None
    break_links(then)
    # remove existing Init calls
    for n in list(ege.list_all_nodes()):
        try:
            t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
        except Exception:
            t = ""
        if "InitBlocked" in t:
            try:
                ege.remove_nodes([n])
            except Exception:
                pass
    call = None
    try:
        gc = bp.generated_class()
        call = ege.add_call_function_node(str(gc.get_path_name()) + ":" + fname)
    except Exception as ex:
        log("call: " + str(ex))
    if call and then:
        bel.set_node_pos(call, pos(280, 0))
        connect(then, find_pin(call, "execute", "Input"), "BP->init")
    try:
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(MGR)
        log("init rebuild ok")
    except Exception as ex:
        log("init compile: " + str(ex))


def splice_tillcell_blocked_check():
    """
    Insert after IsValidCell True branch, before Empty check:
      flat = GY*Width+GX
      if Array_Contains(BlockedIndices, flat) -> Result Success=false
    """
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    graph = bel.find_graph(bp, "TillCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)

    # Map nodes
    entry = None
    valid_branch = None  # first IfThenElse after IsValidCell
    empty_branch = None
    nodes = list(ge.list_all_nodes())
    for n in nodes:
        cls = n.get_class().get_name()
        if cls == "K2Node_FunctionEntry":
            entry = n
        elif cls == "K2Node_IfThenElse":
            if valid_branch is None:
                valid_branch = n
            else:
                empty_branch = n

    log("TillCell entry={} valid_branch={} empty_branch={}".format(entry, valid_branch, empty_branch))
    if not valid_branch or not empty_branch:
        # dump all
        for n in nodes:
            try:
                t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
            except Exception:
                t = n.get_class().get_name()
            log("  node " + t)
        # try identify by connections
        branches = [n for n in nodes if n.get_class().get_name() == "K2Node_IfThenElse"]
        log("branches n=" + str(len(branches)))
        if len(branches) >= 2:
            valid_branch, empty_branch = branches[0], branches[1]
        elif len(branches) == 1:
            empty_branch = branches[0]
            valid_branch = branches[0]

    if not empty_branch:
        log("FATAL no empty branch")
        return False

    # Find exec into empty_branch
    empty_exec = find_pin(empty_branch, "execute", "Input")
    # Who feeds it?
    feeders = []
    try:
        for lp in empty_exec.get_linked_to():
            feeders.append(lp)
            log("empty_branch fed by {} {}".format(lp.get_owning_node().get_class().get_name(), lp.get_pin_name()))
    except Exception as ex:
        log("feeder: " + str(ex))

    # Also find GridX/GridY from entry and GridWidth get
    # We'll insert NEW branch between valid then and empty_branch execute.

    # Get pins from entry
    gx = find_pin(entry, "GridX", "Output") or find_pin(entry, "Grid X", "Output")
    gy = find_pin(entry, "GridY", "Output") or find_pin(entry, "Grid Y", "Output")
    dump_pins(entry, "entry")

    # Create: mul = GY * GridWidth; add = mul + GX; contains; branch; false result
    get_w = ge.add_get_member_variable_node("GridWidth")
    bel.set_node_pos(get_w, pos(400, 600))

    mul = ge.create_node_from_name("Utilities|Operators|integer * integer", unreal.Vector2D(600, 600), [])
    if not mul:
        mul = ge.create_node_from_name("Math|Integer|integer * integer", unreal.Vector2D(600, 600), [])
    bel.set_node_pos(mul, pos(600, 600))
    dump_pins(mul, "mul")

    add = ge.create_node_from_name("Utilities|Operators|integer + integer", unreal.Vector2D(800, 600), [])
    if not add:
        add = ge.create_node_from_name("Math|Integer|integer + integer", unreal.Vector2D(800, 600), [])
    bel.set_node_pos(add, pos(800, 600))

    # GY * Width
    connect(gy or find_pin(entry, "Y", "Output"), find_pin(mul, "A", "Input"), "gy->mulA")
    connect(out0(get_w) or find_pin(get_w, "GridWidth", "Output"), find_pin(mul, "B", "Input"), "w->mulB")
    # + GX
    connect(out0(mul), find_pin(add, "A", "Input"), "mul->addA")
    connect(gx or find_pin(entry, "X", "Output"), find_pin(add, "B", "Input"), "gx->addB")

    get_bi = ge.add_get_member_variable_node("BlockedIndices")
    bel.set_node_pos(get_bi, pos(700, 750))
    contains = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Contains")
    bel.set_node_pos(contains, pos(1000, 600))
    dump_pins(contains, "contains")
    connect(out0(get_bi) or find_pin(get_bi, "BlockedIndices", "Output"),
            find_pin(contains, "TargetArray", "Input") or find_pin(contains, "Array", "Input"), "bi")
    connect(out0(add), find_pin(contains, "ItemToFind", "Input") or find_pin(contains, "Item", "Input") or find_pin(contains, "Item to Find", "Input"), "flat")

    # New branch: if contains -> fail result; else -> original empty_branch
    blocked_br = ge.create_node_from_name("Utilities|FlowControl|Branch", unreal.Vector2D(1200, 400), [])
    if not blocked_br:
        # K2Node_IfThenElse
        try:
            blocked_br = ge.add_node_to_graph  # invalid
        except Exception:
            pass
        # create via class
        for path in ("Branch", "Flow Control|Branch", "Utilities|FlowControl|Branch"):
            try:
                blocked_br = ge.create_node_from_name(path, unreal.Vector2D(1200, 400), [])
                if blocked_br:
                    break
            except Exception:
                pass
    if not blocked_br:
        # Use another IfThenElse by duplicating - create_node_from_name IfThenElse
        try:
            blocked_br = ge.create_node_from_name("If Then Else", unreal.Vector2D(1200, 400), [])
        except Exception as ex:
            log("branch create: " + str(ex))
    bel.set_node_pos(blocked_br, pos(1200, 400))
    dump_pins(blocked_br, "blocked_br")

    # Condition = contains return
    connect(find_pin(contains, "ReturnValue", "Output") or out0(contains),
            find_pin(blocked_br, "Condition", "Input"), "cond")

    # Rewire: whatever fed empty_branch.execute now feeds blocked_br.execute
    # blocked_br.else -> empty_branch.execute
    # blocked_br.then -> FunctionResult Success=false
    break_links(empty_exec)
    # Find valid_branch then pin and connect to blocked_br
    valid_then = find_pin(valid_branch, "then", "Output")
    # Also may have been connected from something else - re-link feeders to blocked
    if valid_then:
        # valid then may still link to empty - break and reconnect
        break_links(valid_then)
        connect(valid_then, find_pin(blocked_br, "execute", "Input"), "valid->blocked_br")
    for fp in feeders:
        # already broken from empty_exec; connect feeder to blocked_br if not valid_then
        try:
            if fp.get_owning_node() != valid_branch:
                connect(fp, find_pin(blocked_br, "execute", "Input"), "feeder->br")
        except Exception:
            pass

    connect(find_pin(blocked_br, "else", "Output"), empty_exec, "not_blocked->empty_check")

    # Fail result on then (is blocked)
    fail = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() != "K2Node_FunctionResult":
            continue
        sp = find_pin(n, "Success", "Input")
        if sp and str(sp.get_pin_value()) in ("false", "False", "0"):
            fail = n
            break
    if not fail:
        # add new result
        try:
            fail = ge.create_node_from_name("Function Result", unreal.Vector2D(1500, 300), [])
        except Exception:
            # duplicate existing result node pattern via add
            for n in ge.list_all_nodes():
                if n.get_class().get_name() == "K2Node_FunctionResult":
                    fail = n
                    break
    if fail:
        bel.set_node_pos(fail, pos(1500, 250))
        connect(find_pin(blocked_br, "then", "Output"), find_pin(fail, "execute", "Input"), "blocked->fail")
        set_val(find_pin(fail, "Success", "Input"), "false", "fail.Success")
    else:
        log("WARN no fail result node")

    # Print Cannot till on blocked path optional - skip

    try:
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(MGR)
        log("TillCell blocked splice compile ok")
        return True
    except Exception as ex:
        log("TillCell compile: " + str(ex))
        return False


def verify_cdo_blocked():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        bi = cdo.get_editor_property("BlockedIndices")
        log("CDO BlockedIndices len={} head={}".format(len(bi) if bi else 0, list(bi)[:10] if bi else None))
        # spot check: path cell (17,16) -> 16*40+17=657
        flat = 16 * WIDTH + 17
        log("path(17,16) flat={} in_blocked={}".format(flat, flat in list(bi) if bi else None))
        # grass open cell e.g. (23,16) spawn
        flat2 = 16 * WIDTH + 23
        log("grass(23,16) flat={} in_blocked={}".format(flat2, flat2 in list(bi) if bi else None))
    except Exception as ex:
        log("verify: " + str(ex))


def force_save():
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    except Exception:
        pass
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception:
        pass
    try:
        unreal.EditorAssetLibrary.save_directory("/Game/__ExternalActors__/TopDown/Lvl_TopDown", True, True)
    except Exception:
        pass
    log("saved")


def main():
    log("=== start ===")
    verify_cdo_blocked()
    rebuild_init()
    ok = splice_tillcell_blocked_check()
    force_save()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    air = sum(1 for a in eas.get_all_level_actors() if (a.get_actor_label() or "").startswith("AirWall_Water_"))
    soil = sum(1 for a in eas.get_all_level_actors() if (a.get_actor_label() or "").startswith("VMF_Soil_"))
    crop = sum(1 for a in eas.get_all_level_actors() if (a.get_actor_label() or "").startswith("VMF_Crop"))
    log("FINAL airwalls={} soil={} crop={} till_splice={}".format(air, soil, crop, ok))
    log("=== done ===")


main()
