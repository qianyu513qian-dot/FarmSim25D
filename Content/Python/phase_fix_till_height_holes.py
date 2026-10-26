# -*- coding: utf-8 -*-
"""Fix till soil height (Z~1.5) and restore grass on Empty (no harvest holes)."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
OFFSET_Z = "1.5"


def log(m):
    unreal.log("[FIX_TILL_HOLES] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip {} a={} b={}".format(label, a, b))
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {} -> {} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    name_substr = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if name_substr in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def set_val(pin, value, label=""):
    if not pin:
        unreal.log_warning("no pin " + label)
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def break_links(pin):
    if not pin:
        return
    try:
        pin.break_pin_links(False)
    except Exception:
        try:
            pin.break_pin_links()
        except Exception as e:
            log("break fail: " + str(e))


def build_grass_toggle_graph(bp, func_name, hidden):
    """Rebuild HideGrassAt / ShowGrassAt: ForLoop over StaticMeshActors, match VMF_Grass_X_Y."""
    graph = bel.find_graph(bp, func_name)
    if not graph:
        bel.add_function_graph(bp, func_name)
        graph = bel.find_graph(bp, func_name)
        log("created graph " + func_name)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)

    entry = None
    to_del = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            to_del.append(n)
    if to_del:
        ge.remove_nodes(to_del)
        log("{} removed {} old nodes".format(func_name, len(to_del)))
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

    if find_pin(entry, "GridX", "Output") is None:
        ip = unreal.EdGraphPinType()
        ip.import_text('(PinCategory="int")')
        ge.add_graph_input_parameter("GridX", ip)
        ge.add_graph_input_parameter("GridY", ip)
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n
        log("{} added GridX/GridY inputs".format(func_name))

    get_all = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(get_all, pos(300, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(get_all, "execute", "Input"), func_name + ".e->all")
    class_pin = find_pin(get_all, "ActorClass", "Input") or find_pin(get_all, "Class", "Input")
    set_val(class_pin, "/Script/Engine.StaticMeshActor", func_name + ".ActorClass")

    length = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Length")
    bel.set_node_pos(length, pos(600, 200))
    out_actors = find_pin(get_all, "OutActors", "Output") or find_pin(get_all, "Outactors", "Output")
    connect(out_actors, find_pin(length, "TargetArray", "Input") or find_pin(length, "Array", "Input"), func_name + ".arr->len")

    forloop = None
    for path in (
        "Utilities|FlowControl|ForLoop",
        "Flow Control|For Loop",
        "Utilities|FlowControl|For Loop",
    ):
        try:
            forloop = ge.create_node_from_name(path, unreal.Vector2D(900, 0), [])
            if forloop:
                log("{} ForLoop via {}".format(func_name, path))
                break
        except Exception as e:
            log("{} ForLoop try {}: {}".format(func_name, path, e))

    if not forloop:
        log("{} NO ForLoop — noop return".format(func_name))
        ret = ge.add_return_node()
        bel.set_node_pos(ret, pos(700, 0))
        connect(find_pin(get_all, "then", "Output"), find_pin(ret, "execute", "Input"), func_name + ".noop")
        return False

    bel.set_node_pos(forloop, pos(900, 0))
    connect(find_pin(get_all, "then", "Output"), find_pin(forloop, "execute", "Input"), func_name + ".all->for")
    set_val(find_pin(forloop, "FirstIndex", "Input") or find_pin(forloop, "First Index", "Input"), "0", func_name + ".first")

    sub = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_IntInt")
    bel.set_node_pos(sub, pos(700, 200))
    connect(find_pin(length, "ReturnValue", "Output"), find_pin(sub, "A", "Input"), func_name + ".len-A")
    set_val(find_pin(sub, "B", "Input"), "1", func_name + ".len-B")
    connect(find_pin(sub, "ReturnValue", "Output"),
            find_pin(forloop, "LastIndex", "Input") or find_pin(forloop, "Last Index", "Input"),
            func_name + ".last")

    get_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get_at, pos(1200, 80))
    connect(out_actors, find_pin(get_at, "TargetArray", "Input"), func_name + ".arr")
    connect(find_pin(forloop, "Index", "Output"), find_pin(get_at, "Index", "Input"), func_name + ".idx")

    get_name = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
    bel.set_node_pos(get_name, pos(1450, 80))
    connect(find_pin(get_at, "Item", "Output"), find_pin(get_name, "Object", "Input"), func_name + ".item->name")

    conv_x = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
    bel.set_node_pos(conv_x, pos(300, 320))
    connect(find_pin(entry, "GridX", "Output"), find_pin(conv_x, "InInt", "Input"), func_name + ".gx")
    conv_y = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
    bel.set_node_pos(conv_y, pos(300, 400))
    connect(find_pin(entry, "GridY", "Output"), find_pin(conv_y, "InInt", "Input"), func_name + ".gy")

    cat1 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(cat1, pos(600, 320))
    set_val(find_pin(cat1, "A", "Input"), "VMF_Grass_", func_name + ".pre")
    connect(find_pin(conv_x, "ReturnValue", "Output"), find_pin(cat1, "B", "Input"), func_name + ".x")
    cat2 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(cat2, pos(850, 320))
    connect(find_pin(cat1, "ReturnValue", "Output"), find_pin(cat2, "A", "Input"), func_name + ".a")
    set_val(find_pin(cat2, "B", "Input"), "_", func_name + ".us")
    cat3 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(cat3, pos(1100, 320))
    connect(find_pin(cat2, "ReturnValue", "Output"), find_pin(cat3, "A", "Input"), func_name + ".a2")
    connect(find_pin(conv_y, "ReturnValue", "Output"), find_pin(cat3, "B", "Input"), func_name + ".y")

    contains = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains")
    bel.set_node_pos(contains, pos(1700, 80))
    connect(find_pin(get_name, "ReturnValue", "Output"),
            find_pin(contains, "SearchIn", "Input") or find_pin(contains, "SourceString", "Input") or find_pin(contains, "search", "Input"),
            func_name + ".src")
    connect(find_pin(cat3, "ReturnValue", "Output"),
            find_pin(contains, "Substring", "Input") or find_pin(contains, "Find", "Input") or find_pin(contains, "substr", "Input"),
            func_name + ".sub")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(1950, 0))
    connect(find_pin(forloop, "LoopBody", "Output") or find_pin(forloop, "Then", "Output") or find_pin(forloop, "loop", "Output"),
            find_pin(br, "execute", "Input"), func_name + ".body->br")
    connect(find_pin(contains, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), func_name + ".cond")

    hid = ge.add_call_function_node("/Script/Engine.Actor:SetActorHiddenInGame")
    bel.set_node_pos(hid, pos(2250, -40))
    connect(find_pin(br, "then", "Output"), find_pin(hid, "execute", "Input"), func_name + ".br->hid")
    connect(find_pin(get_at, "Item", "Output"), find_pin(hid, "self", "Input"), func_name + ".item->hid")
    set_val(find_pin(hid, "bNewHidden", "Input") or find_pin(hid, "NewHidden", "Input"),
            "true" if hidden else "false",
            func_name + ".hidden")

    ret = ge.add_return_node()
    bel.set_node_pos(ret, pos(1200, 480))
    connect(find_pin(forloop, "Completed", "Output"), find_pin(ret, "execute", "Input"), func_name + ".done")
    log("{} built hidden={}".format(func_name, hidden))
    return True


def build_toggle_grass(bp):
    """ToggleGrassForState(GridX,GridY,State): State==0 Show else Hide; dual returns (no exec merge)."""
    fname = "ToggleGrassForState"
    graph = bel.find_graph(bp, fname)
    if not graph:
        bel.add_function_graph(bp, fname)
        graph = bel.find_graph(bp, fname)
        log("created " + fname)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)

    entry = None
    to_del = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            to_del.append(n)
    if to_del:
        ge.remove_nodes(to_del)
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

    # Ensure inputs GridX, GridY, State (byte)
    if find_pin(entry, "GridX", "Output") is None:
        ip = unreal.EdGraphPinType()
        ip.import_text('(PinCategory="int")')
        ge.add_graph_input_parameter("GridX", ip)
        ge.add_graph_input_parameter("GridY", ip)
    if find_pin(entry, "State", "Output") is None:
        bp_pin = unreal.EdGraphPinType()
        # EPlotState or byte — VisualizeCell uses byte Equal; use byte
        bp_pin.import_text('(PinCategory="byte")')
        try:
            ge.add_graph_input_parameter("State", bp_pin)
        except Exception:
            # fallback: uint8 / byte via enum if available
            try:
                ep = unreal.EdGraphPinType()
                ep.import_text('(PinCategory="byte",PinSubCategory="")')
                ge.add_graph_input_parameter("State", ep)
            except Exception as e:
                log("State input fail: " + str(e))
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

    eq0 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
    bel.set_node_pos(eq0, pos(400, -40))
    connect(find_pin(entry, "State", "Output"), find_pin(eq0, "A", "Input"), "tog.st")
    set_val(find_pin(eq0, "B", "Input"), "0", "tog.eq0")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(650, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "tog.e->br")
    connect(find_pin(eq0, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "tog.cond")

    show = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:ShowGrassAt")
    bel.set_node_pos(show, pos(950, -120))
    connect(find_pin(br, "then", "Output"), find_pin(show, "execute", "Input"), "tog.br->show")
    connect(find_pin(entry, "GridX", "Output"), find_pin(show, "GridX", "Input"), "tog.show.x")
    connect(find_pin(entry, "GridY", "Output"), find_pin(show, "GridY", "Input"), "tog.show.y")

    hide = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:HideGrassAt")
    bel.set_node_pos(hide, pos(950, 120))
    connect(find_pin(br, "else", "Output"), find_pin(hide, "execute", "Input"), "tog.br->hide")
    connect(find_pin(entry, "GridX", "Output"), find_pin(hide, "GridX", "Input"), "tog.hide.x")
    connect(find_pin(entry, "GridY", "Output"), find_pin(hide, "GridY", "Input"), "tog.hide.y")

    ret1 = ge.add_return_node()
    bel.set_node_pos(ret1, pos(1300, -120))
    connect(find_pin(show, "then", "Output"), find_pin(ret1, "execute", "Input"), "tog.show->ret")

    ret2 = ge.add_return_node()
    bel.set_node_pos(ret2, pos(1300, 120))
    connect(find_pin(hide, "then", "Output"), find_pin(ret2, "execute", "Input"), "tog.hide->ret")

    log("ToggleGrassForState built")
    return True


def lower_offset_z(ge):
    """Set VisualizeCell spawn offset MakeVector Z to OFFSET_Z; leave scale vectors alone."""
    changed = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "Make Vector" not in t and t != "MakeVector":
            continue
        zp = find_pin(n, "Z", "Input")
        xp = find_pin(n, "X", "Input")
        if not zp:
            continue
        try:
            zv = str(zp.get_pin_value())
            xv = str(xp.get_pin_value()) if xp else ""
        except Exception:
            zv, xv = "", ""
        log("MakeVector X={} Z={}".format(xv, zv))
        # Offset: Z was 3/25/40; scale has X~0.01
        is_scale = False
        try:
            xf = float(xv) if xv else 0.0
            if 0.001 <= abs(xf) <= 0.05:
                is_scale = True
        except Exception:
            pass
        if is_scale:
            log("skip scale MakeVector Z=" + zv)
            continue
        # Treat as offset if Z looks like height offset
        try:
            zf = float(zv) if zv else 0.0
        except Exception:
            zf = 0.0
        if zf >= 1.0 or zv in ("3", "3.0", "5", "5.0", "20", "20.0", "25", "25.0", "40", "40.0"):
            set_val(zp, OFFSET_Z, "off.Z")
            set_val(find_pin(n, "X", "Input"), "0.0", "off.X")
            set_val(find_pin(n, "Y", "Input"), "0.0", "off.Y")
            changed.append(OFFSET_Z)
            log("lowered offset Z -> " + OFFSET_Z)
    return changed


def splice_toggle_into_visualize(bp):
    """Replace entry->HideGrassAt->body with entry->ToggleGrassForState->body; remove orphan gate nodes."""
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))

    entry = None
    hide_node = None
    isvalid_node = None
    orphan_seq = []
    gate_branch = None
    gate_eq = None

    for n in ge.list_all_nodes():
        cls = n.get_class().get_name()
        t = bel.get_node_title(n)
        if cls == "K2Node_FunctionEntry":
            entry = n
        if "HideGrassAt" in t:
            hide_node = n
        if t == "IsValid" or "Is Valid" in t:
            isvalid_node = n
        if cls == "K2Node_ExecutionSequence":
            # orphan if no connections
            exe = find_pin(n, "execute", "Input")
            conns = list(exe.list_connected_pins()) if exe else []
            if not conns:
                orphan_seq.append(n)

    # Find IsValid Branch (body start)
    body_branch = None
    if isvalid_node:
        ret = find_pin(isvalid_node, "ReturnValue", "Output")
        if ret:
            for cp in ret.list_connected_pins():
                owner = cp.get_owning_node()
                if owner.get_class().get_name() == "K2Node_IfThenElse":
                    body_branch = owner
                    break

    # Find gate branch: Equal(State,0) feeding a Branch that is NOT the Empty-destroy path
    # After HideGrassAt, body should be IsValid branch. Gate leftover: Branch whose else->HideGrassAt
    if hide_node:
        exe = find_pin(hide_node, "execute", "Input")
        for cp in list(exe.list_connected_pins()) if exe else []:
            owner = cp.get_owning_node()
            if owner.get_class().get_name() == "K2Node_IfThenElse" and owner != body_branch:
                gate_branch = owner
                log("found gate_branch")

    # Find Equal feeding gate_branch
    if gate_branch:
        cond = find_pin(gate_branch, "Condition", "Input")
        if cond:
            for cp in cond.list_connected_pins():
                owner = cp.get_owning_node()
                if "Equal" in bel.get_node_title(owner).lower():
                    gate_eq = owner

    # Capture body start pin: currently HideGrassAt.then -> body
    body_exec_in = None
    if hide_node:
        thenp = find_pin(hide_node, "then", "Output")
        if thenp:
            for cp in thenp.list_connected_pins():
                body_exec_in = cp
                log("body_exec_in = {} @ {}".format(cp.get_pin_name(), bel.get_node_title(cp.get_owning_node())))
                break
    if body_exec_in is None and body_branch:
        body_exec_in = find_pin(body_branch, "execute", "Input")
        log("fallback body_exec_in = IsValid Branch")

    # Break entry / hide / gate links
    if entry:
        break_links(find_pin(entry, "then", "Output"))
    if hide_node:
        break_links(find_pin(hide_node, "execute", "Input"))
        break_links(find_pin(hide_node, "then", "Output"))
    if gate_branch:
        break_links(find_pin(gate_branch, "execute", "Input"))
        break_links(find_pin(gate_branch, "then", "Output"))
        break_links(find_pin(gate_branch, "else", "Output"))

    # Remove orphan / gate nodes
    to_remove = []
    to_remove.extend(orphan_seq)
    if gate_branch:
        to_remove.append(gate_branch)
    if gate_eq:
        to_remove.append(gate_eq)
    if hide_node:
        to_remove.append(hide_node)
    # dedupe
    seen = set()
    uniq = []
    for n in to_remove:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)
    if uniq:
        ge.remove_nodes(uniq)
        log("removed {} gate/orphan/old-hide nodes".format(len(uniq)))

    # Re-find entry & body after removals
    entry = None
    body_branch = None
    isvalid_node = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        if bel.get_node_title(n) == "IsValid" or "Is Valid" in bel.get_node_title(n):
            isvalid_node = n
    if isvalid_node:
        ret = find_pin(isvalid_node, "ReturnValue", "Output")
        if ret:
            for cp in ret.list_connected_pins():
                owner = cp.get_owning_node()
                if owner.get_class().get_name() == "K2Node_IfThenElse":
                    body_branch = owner
                    break
    body_exec_in = find_pin(body_branch, "execute", "Input") if body_branch else None
    if not body_exec_in:
        # Fallback: first Branch after entry that has IsValid-like structure — find Branch with Destroy on then
        for n in ge.list_all_nodes():
            if n.get_class().get_name() != "K2Node_IfThenElse":
                continue
            thenp = find_pin(n, "then", "Output")
            for cp in (thenp.list_connected_pins() if thenp else []):
                if "Destroy" in bel.get_node_title(cp.get_owning_node()) or "Cast" in bel.get_node_title(cp.get_owning_node()):
                    # might be empty-state branch; keep looking for IsValid one
                    pass
            cond = find_pin(n, "Condition", "Input")
            for cp in (cond.list_connected_pins() if cond else []):
                if "IsValid" in bel.get_node_title(cp.get_owning_node()) or "Is Valid" in bel.get_node_title(cp.get_owning_node()):
                    body_exec_in = find_pin(n, "execute", "Input")
                    body_branch = n
                    break
            if body_exec_in:
                break

    if not entry or not body_exec_in:
        unreal.log_error("Cannot splice Toggle: entry={} body={}".format(bool(entry), bool(body_exec_in)))
        return False

    # Break anything currently into body_exec_in
    break_links(body_exec_in)

    tog = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:ToggleGrassForState")
    bel.set_node_pos(tog, pos(200, -80))
    connect(find_pin(entry, "then", "Output"), find_pin(tog, "execute", "Input"), "e->tog")
    connect(find_pin(entry, "GridX", "Output"), find_pin(tog, "GridX", "Input"), "tog.x")
    connect(find_pin(entry, "GridY", "Output"), find_pin(tog, "GridY", "Input"), "tog.y")
    connect(find_pin(entry, "State", "Output"), find_pin(tog, "State", "Input"), "tog.state")
    connect(find_pin(tog, "then", "Output"), body_exec_in, "tog->body")
    log("spliced ToggleGrassForState into VisualizeCell")
    return True


def main():
    bp = unreal.load_asset(MGR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))

    # 1) Probe & lower Z
    log("=== step1 lower Z (was often 40) ===")
    changed = lower_offset_z(ge)
    log("Z changes: " + str(changed))

    # 2) Rebuild HideGrassAt + create ShowGrassAt
    log("=== step2 HideGrassAt / ShowGrassAt ===")
    build_grass_toggle_graph(bp, "HideGrassAt", hidden=True)
    build_grass_toggle_graph(bp, "ShowGrassAt", hidden=False)

    try:
        bel.compile_blueprint(bp)
        log("compile after grass graphs ok")
    except Exception as e:
        log("compile after grass graphs: " + str(e))

    # 3) ToggleGrassForState
    log("=== step3 ToggleGrassForState ===")
    build_toggle_grass(bp)
    try:
        bel.compile_blueprint(bp)
        log("compile after toggle ok")
    except Exception as e:
        log("compile after toggle: " + str(e))

    # 4) Splice into VisualizeCell
    log("=== step4 splice VisualizeCell ===")
    ok = splice_toggle_into_visualize(bp)
    log("splice ok=" + str(ok))

    # 5) Compile + verify
    try:
        bel.compile_blueprint(bp)
        log("final compile ok")
    except Exception as e:
        log("final compile: " + str(e))

    for fname in ("VisualizeCell", "HideGrassAt", "ShowGrassAt", "ToggleGrassForState", "HarvestCell"):
        g = bel.find_graph(bp, fname)
        if not g:
            log("{} MISSING".format(fname))
            continue
        fge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        errs = fge.list_nodes_with_errors()
        log("{} nodes={} errors={}".format(fname, len(list(fge.list_all_nodes())), len(errs)))
        for n in errs:
            log("  ERR " + bel.get_node_title(n))

    # Verify Z
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "Make Vector" in t or t == "MakeVector":
            log("VERIFY MakeVector X={} Y={} Z={}".format(
                find_pin(n, "X", "Input").get_pin_value() if find_pin(n, "X", "Input") else "?",
                find_pin(n, "Y", "Input").get_pin_value() if find_pin(n, "Y", "Input") else "?",
                find_pin(n, "Z", "Input").get_pin_value() if find_pin(n, "Z", "Input") else "?",
            ))
        if "ToggleGrass" in t or "HideGrass" in t or "ShowGrass" in t:
            log("VERIFY call: " + t)

    # entry chain
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            thenp = find_pin(n, "then", "Output")
            for cp in thenp.list_connected_pins():
                log("VERIFY entry.then -> " + bel.get_node_title(cp.get_owning_node()))

    unreal.EditorAssetLibrary.save_asset(MGR)
    log("saved " + MGR)
    log("=== DONE ===")


main()
