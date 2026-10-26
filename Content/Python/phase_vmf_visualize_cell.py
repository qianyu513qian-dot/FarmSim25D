# -*- coding: utf-8 -*-
"""SAFE: Add VisualizeCell to BP_GridManager + splice into Till/Plant/Water/Grow/Harvest.
Uses SpawnActorfromClass + CastToBP_PlotVisual + PlotVisuals actor array.
No open_editor, no rename.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"
PV_CLASS = "/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C"

# State written by each cell func
STATE_BY_FUNC = {
    "TillCell": "1",
    "PlantCell": "2",
    "WaterCell": "3",
    "GrowCell": "4",
    "HarvestCell": "0",
}


def log(m):
    unreal.log("[VMF_VIZ] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def set_val(pin, value, label=""):
    if not pin:
        unreal.log_warning("no pin " + label)
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r} -> {!r}".format(label, value, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def make_int_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="int")')
    return p


def make_byte_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="byte")')
    return p


def ensure_plot_visuals_var(bp):
    names = [str(x) for x in bel.list_member_variable_names(bp)]
    short = [n.split(".")[-1] for n in names]
    if "PlotVisuals" in short:
        log("PlotVisuals var exists")
        return True
    pin = unreal.EdGraphPinType()
    # Actor array is safer for spawn ReturnValue assignment; cast when calling ApplyState
    pin.import_text(
        '(PinCategory="object",PinSubCategory="",'
        'PinSubCategoryObject="/Script/Engine.Actor",ContainerType=Array)'
    )
    try:
        ok = bel.add_member_variable(bp, "PlotVisuals", pin)
        log("add PlotVisuals -> " + str(ok))
    except Exception as e:
        log("add PlotVisuals fail: " + str(e))
        return False
    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        log("compile after var: " + str(e))
    unreal.EditorAssetLibrary.save_asset(MGR)
    return True


def build_visualize_cell(bp):
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    if "VisualizeCell" in graphs:
        log("VisualizeCell exists — leave body (skip rebuild to avoid crash)")
        return True

    bel.add_function_graph(bp, "VisualizeCell")
    graph = bel.find_graph(bp, "VisualizeCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    if not ge:
        unreal.log_error("no VisualizeCell GE")
        return False

    entry = None
    to_del = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            to_del.append(n)
    if to_del:
        ge.remove_nodes(to_del)

    if find_pin(entry, "GridX", "Output") is None:
        ge.add_graph_input_parameter("GridX", make_int_pin())
        ge.add_graph_input_parameter("GridY", make_int_pin())
        ge.add_graph_input_parameter("State", make_byte_pin())
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

    # idx = GY * Width + GX
    get_w = ge.add_get_member_variable_node("GridWidth")
    bel.set_node_pos(get_w, pos(200, 220))
    mul = ge.create_node_from_name("Utilities|Operators|Multiply", unreal.Vector2D(400, 220), [])
    bel.set_node_pos(mul, pos(400, 220))
    addn = ge.create_node_from_name("Utilities|Operators|Add", unreal.Vector2D(600, 220), [])
    bel.set_node_pos(addn, pos(600, 220))
    connect(find_pin(entry, "GridY", "Output"), find_pin(mul, "A", "Input"), "gy*")
    connect(find_pin(get_w, "GridWidth", "Output"), find_pin(mul, "B", "Input"), "*w")
    connect(find_pin(mul, "ReturnValue", "Output"), find_pin(addn, "A", "Input"), "mul+")
    connect(find_pin(entry, "GridX", "Output"), find_pin(addn, "B", "Input"), "+gx")

    get_vis = ge.add_get_member_variable_node("PlotVisuals")
    bel.set_node_pos(get_vis, pos(600, 40))
    get_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get_at, pos(850, 40))
    connect(find_pin(get_vis, "PlotVisuals", "Output"), find_pin(get_at, "TargetArray", "Input"), "arr")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(get_at, "Index", "Input"), "idx")

    is_valid = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
    bel.set_node_pos(is_valid, pos(1100, 40))
    connect(find_pin(get_at, "Item", "Output"), find_pin(is_valid, "Object", "Input") or find_pin(is_valid, "Base", "Input"), "item->valid")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(1300, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
    connect(find_pin(is_valid, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "valid->br")

    # ===== EXISTING VALID path =====
    # State == 0 ?
    eq0 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
    bel.set_node_pos(eq0, pos(1500, -40))
    connect(find_pin(entry, "State", "Output"), find_pin(eq0, "A", "Input"), "st->eq0")
    set_val(find_pin(eq0, "B", "Input"), "0", "eq0.B")

    br0 = ge.add_branch_node()
    bel.set_node_pos(br0, pos(1750, -80))
    connect(find_pin(br, "then", "Output"), find_pin(br0, "execute", "Input"), "br->br0")
    connect(find_pin(eq0, "ReturnValue", "Output"), find_pin(br0, "Condition", "Input"), "eq0->br0")

    # Destroy existing
    destroy = ge.add_call_function_node("/Script/Engine.Actor:K2_DestroyActor")
    bel.set_node_pos(destroy, pos(2050, -160))
    connect(find_pin(br0, "then", "Output"), find_pin(destroy, "execute", "Input"), "br0->destroy")
    connect(find_pin(get_at, "Item", "Output"), find_pin(destroy, "self", "Input"), "item->destroy")

    # Array_Set null
    set_null = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
    bel.set_node_pos(set_null, pos(2350, -160))
    connect(find_pin(destroy, "then", "Output"), find_pin(set_null, "execute", "Input"), "des->setnull")
    connect(find_pin(get_vis, "PlotVisuals", "Output"), find_pin(set_null, "TargetArray", "Input"), "arr-null")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(set_null, "Index", "Input"), "idx-null")
    set_val(find_pin(set_null, "bSizeToFit", "Input"), "true", "fit-null")
    # Item left empty/None

    ret_clear = ge.add_return_node()
    bel.set_node_pos(ret_clear, pos(2650, -160))
    connect(find_pin(set_null, "then", "Output"), find_pin(ret_clear, "execute", "Input"), "null->ret")

    # Existing + State!=0: Cast + ApplyState
    cast_n = ge.create_node_from_name("Utilities|Casting|CastToBP_PlotVisual", unreal.Vector2D(2050, 40), [])
    bel.set_node_pos(cast_n, pos(2050, 40))
    connect(find_pin(br0, "else", "Output"), find_pin(cast_n, "execute", "Input"), "br0else->cast")
    connect(find_pin(get_at, "Item", "Output"), find_pin(cast_n, "Object", "Input"), "item->cast")

    apply1 = ge.add_call_function_node("/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C:ApplyState")
    bel.set_node_pos(apply1, pos(2400, 40))
    connect(find_pin(cast_n, "then", "Output"), find_pin(apply1, "execute", "Input"), "cast->apply")
    as_pin = find_pin(cast_n, "AsBP Plot Visual", "Output") or find_pin(cast_n, "AsBP", "Output")
    connect(as_pin, find_pin(apply1, "self", "Input"), "as->self")
    connect(find_pin(entry, "State", "Output"), find_pin(apply1, "State", "Input"), "st->apply1")

    ret_upd = ge.add_return_node()
    bel.set_node_pos(ret_upd, pos(2700, 40))
    connect(find_pin(apply1, "then", "Output"), find_pin(ret_upd, "execute", "Input"), "apply1->ret")
    # CastFailed -> return
    ret_cf = ge.add_return_node()
    bel.set_node_pos(ret_cf, pos(2400, 180))
    connect(find_pin(cast_n, "CastFailed", "Output"), find_pin(ret_cf, "execute", "Input"), "castfail")

    # ===== INVALID / missing path =====
    # State == 0? just return
    eq0b = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
    bel.set_node_pos(eq0b, pos(1500, 320))
    connect(find_pin(entry, "State", "Output"), find_pin(eq0b, "A", "Input"), "st->eq0b")
    set_val(find_pin(eq0b, "B", "Input"), "0", "eq0b.B")

    br_miss = ge.add_branch_node()
    bel.set_node_pos(br_miss, pos(1750, 300))
    connect(find_pin(br, "else", "Output"), find_pin(br_miss, "execute", "Input"), "br else->miss")
    connect(find_pin(eq0b, "ReturnValue", "Output"), find_pin(br_miss, "Condition", "Input"), "eq0b->miss")

    ret_noop = ge.add_return_node()
    bel.set_node_pos(ret_noop, pos(2050, 280))
    connect(find_pin(br_miss, "then", "Output"), find_pin(ret_noop, "execute", "Input"), "miss0->ret")

    # Spawn new
    g2w = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GridToWorld")
    bel.set_node_pos(g2w, pos(2050, 420))
    connect(find_pin(br_miss, "else", "Output"), find_pin(g2w, "execute", "Input"), "miss->g2w")
    connect(find_pin(entry, "GridX", "Output"), find_pin(g2w, "Grid X", "Input") or find_pin(g2w, "GridX", "Input"), "gx-g2w")
    connect(find_pin(entry, "GridY", "Output"), find_pin(g2w, "Grid Y", "Input") or find_pin(g2w, "GridY", "Input"), "gy-g2w")

    # Location + (0,0,3)
    make_off = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(make_off, pos(2050, 560))
    set_val(find_pin(make_off, "X", "Input"), "0.0", "ox")
    set_val(find_pin(make_off, "Y", "Input"), "0.0", "oy")
    set_val(find_pin(make_off, "Z", "Input"), "3.0", "oz")
    add_v = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
    bel.set_node_pos(add_v, pos(2300, 480))
    connect(
        find_pin(g2w, "World Location", "Output") or find_pin(g2w, "ReturnValue", "Output") or find_pin(g2w, "WorldLocation", "Output"),
        find_pin(add_v, "A", "Input"),
        "loc+A",
    )
    connect(find_pin(make_off, "ReturnValue", "Output"), find_pin(add_v, "B", "Input"), "off+B")

    make_sc = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(make_sc, pos(2300, 620))
    set_val(find_pin(make_sc, "X", "Input"), "0.01", "sx")
    set_val(find_pin(make_sc, "Y", "Input"), "0.01", "sy")
    set_val(find_pin(make_sc, "Z", "Input"), "0.01", "sz")

    make_tf = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeTransform")
    bel.set_node_pos(make_tf, pos(2550, 480))
    connect(find_pin(add_v, "ReturnValue", "Output"), find_pin(make_tf, "Location", "Input"), "tf.loc")
    connect(find_pin(make_sc, "ReturnValue", "Output"), find_pin(make_tf, "Scale", "Input"), "tf.sc")

    spawn = ge.create_node_from_name("Game|SpawnActorfromClass", unreal.Vector2D(2850, 420), [])
    bel.set_node_pos(spawn, pos(2850, 420))
    connect(find_pin(g2w, "then", "Output"), find_pin(spawn, "execute", "Input"), "g2w->spawn")
    set_val(find_pin(spawn, "Class", "Input"), PV_CLASS, "spawn.class")
    connect(find_pin(make_tf, "ReturnValue", "Output"), find_pin(spawn, "SpawnTransform", "Input"), "tf->spawn")
    # Always spawn, ignore collision
    try:
        set_val(find_pin(spawn, "CollisionHandlingOverride", "Input"), "AlwaysSpawn", "coll")
    except Exception:
        pass

    # Array_Set spawned
    set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
    bel.set_node_pos(set_at, pos(3200, 420))
    connect(find_pin(spawn, "then", "Output"), find_pin(set_at, "execute", "Input"), "spawn->set")
    connect(find_pin(get_vis, "PlotVisuals", "Output"), find_pin(set_at, "TargetArray", "Input"), "arr-set")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(set_at, "Index", "Input"), "idx-set")
    connect(find_pin(spawn, "ReturnValue", "Output"), find_pin(set_at, "Item", "Input"), "item-set")
    set_val(find_pin(set_at, "bSizeToFit", "Input"), "true", "fit-set")

    # Cast spawned + ApplyState
    cast2 = ge.create_node_from_name("Utilities|Casting|CastToBP_PlotVisual", unreal.Vector2D(3500, 420), [])
    bel.set_node_pos(cast2, pos(3500, 420))
    connect(find_pin(set_at, "then", "Output"), find_pin(cast2, "execute", "Input"), "set->cast2")
    connect(find_pin(spawn, "ReturnValue", "Output"), find_pin(cast2, "Object", "Input"), "spawn->cast2")

    apply2 = ge.add_call_function_node("/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C:ApplyState")
    bel.set_node_pos(apply2, pos(3850, 420))
    connect(find_pin(cast2, "then", "Output"), find_pin(apply2, "execute", "Input"), "cast2->apply2")
    as2 = find_pin(cast2, "AsBP Plot Visual", "Output") or find_pin(cast2, "AsBP", "Output")
    connect(as2, find_pin(apply2, "self", "Input"), "as2->self")
    connect(find_pin(entry, "State", "Output"), find_pin(apply2, "State", "Input"), "st->apply2")

    ret_spawn = ge.add_return_node()
    bel.set_node_pos(ret_spawn, pos(4200, 420))
    connect(find_pin(apply2, "then", "Output"), find_pin(ret_spawn, "execute", "Input"), "apply2->ret")

    ret_cf2 = ge.add_return_node()
    bel.set_node_pos(ret_cf2, pos(3850, 560))
    connect(find_pin(cast2, "CastFailed", "Output"), find_pin(ret_cf2, "execute", "Input"), "cast2fail")

    try:
        bel.compile_blueprint(bp)
        log("VisualizeCell compile ok")
    except Exception as e:
        unreal.log_warning("VisualizeCell compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(MGR)
    return True


def splice_visualize_into(bp, func_name, state_val):
    """Insert VisualizeCell between DrawDebugBox.then and success Return."""
    g = bel.find_graph(bp, func_name)
    if not g:
        log("NO graph " + func_name)
        return False
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)

    # Already wired?
    for n in ge.list_all_nodes():
        try:
            t = bel.get_node_title(n)
        except Exception:
            t = ""
        if "VisualizeCell" in t:
            log(func_name + " already has VisualizeCell — skip")
            return True

    entry = None
    dbg = None
    success_ret = None
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == func_name or n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        if t == "DrawDebugBox":
            dbg = n
        if t == "Return Node":
            sp = find_pin(n, "Success", "Input")
            if sp:
                try:
                    v = str(sp.get_pin_value()).lower()
                except Exception:
                    v = ""
                if v in ("true", "1"):
                    # prefer the one connected from dbg
                    success_ret = n

    if not dbg:
        log(func_name + " no DrawDebugBox")
        return False

    # Find success return connected to dbg.then
    then_pin = find_pin(dbg, "then", "Output")
    if then_pin:
        for cp in list(then_pin.list_connected_pins()):
            own = cp.get_owning_node()
            if bel.get_node_title(own) == "Return Node":
                success_ret = own

    if not success_ret:
        log(func_name + " no success return")
        return False

    # Shorten debug duration
    set_val(find_pin(dbg, "Duration", "Input"), "1.5", func_name + ".dur")

    # Break dbg.then -> return.execute
    ret_exec = find_pin(success_ret, "execute", "Input")
    try:
        then_pin.break_pin_links(False)
        log(func_name + " broke dbg.then links")
    except Exception as e:
        log(func_name + " break_pin_links: " + str(e))
        try:
            then_pin.break_single_pin_link(ret_exec)
        except Exception as e2:
            log(func_name + " break_single: " + str(e2))

    # Add VisualizeCell call
    viz = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:VisualizeCell")
    # Place near dbg
    try:
        bel.set_node_pos(viz, pos(2500, 80))
    except Exception:
        pass

    connect(then_pin, find_pin(viz, "execute", "Input"), func_name + ".dbg->viz")
    connect(find_pin(viz, "then", "Output"), ret_exec, func_name + ".viz->ret")

    # GridX/GridY from entry
    connect(find_pin(entry, "GridX", "Output"), find_pin(viz, "Grid X", "Input") or find_pin(viz, "GridX", "Input"), func_name + ".gx")
    connect(find_pin(entry, "GridY", "Output"), find_pin(viz, "Grid Y", "Input") or find_pin(viz, "GridY", "Input"), func_name + ".gy")
    set_val(find_pin(viz, "State", "Input"), state_val, func_name + ".state")

    log(func_name + " spliced VisualizeCell state=" + state_val)
    return True


def main():
    log("=== START ===")
    bp = unreal.load_asset(MGR)
    ensure_plot_visuals_var(bp)
    bp = unreal.load_asset(MGR)
    ok = build_visualize_cell(bp)
    log("build_visualize_cell=" + str(ok))

    bp = unreal.load_asset(MGR)
    for fname, st in STATE_BY_FUNC.items():
        try:
            splice_visualize_into(bp, fname, st)
        except Exception as e:
            unreal.log_warning("splice {}: {}".format(fname, e))
            import traceback
            unreal.log_warning(traceback.format_exc())

    try:
        bel.compile_blueprint(bp)
        log("final compile ok")
    except Exception as e:
        unreal.log_warning("final compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(MGR)
    log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    log("=== END ===")


if __name__ == "__main__":
    main()
