# -*- coding: utf-8 -*-
"""SAFE phase5: add GrowCell only. No open_editor, no rename, no character edits.
Watered(3) -> Ready(4) + yellow debug box. Does NOT remove existing graphs.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    unreal.log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
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
        unreal.log("set {}={!r} -> {!r}".format(label, value, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def make_int_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="int")')
    return p


def make_bool_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="bool")')
    return p


def dump(node, label):
    if not node:
        return
    for p in bel.list_all_pins(node):
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def ensure_ready_enum():
    """Best-effort add Ready display name; numeric 4 used regardless."""
    path = "/Game/Farm/Grid/E_PlotState"
    e = unreal.load_asset(path)
    if not e:
        unreal.log_warning("no enum")
        return
    try:
        # Try common editor API
        if hasattr(unreal, "UserDefinedEnumEditorUtils"):
            unreal.log("has UserDefinedEnumEditorUtils")
        for meth in dir(e):
            if "enumer" in meth.lower() or "add" in meth.lower():
                if not meth.startswith("_"):
                    unreal.log("enum." + meth)
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(path)


def build_grow_cell():
    bp = unreal.load_asset(MGR)
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    unreal.log("graphs=" + str(graphs))
    if "GrowCell" in graphs:
        unreal.log("GrowCell already exists — leave it, skip rebuild to avoid crash")
        return True

    bel.add_function_graph(bp, "GrowCell")
    graph = bel.find_graph(bp, "GrowCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    if not ge:
        unreal.log_error("no GrowCell GE")
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
    has_succ = False
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionResult" and find_pin(n, "Success"):
            has_succ = True
    if not has_succ:
        try:
            ge.add_graph_output_parameter("Success", make_bool_pin())
        except Exception as ex:
            unreal.log_warning(str(ex))

    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
    dump(entry, "entry")

    # IsValidCell assumed Pure after user fix — use return only
    valid = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:IsValidCell")
    bel.set_node_pos(valid, pos(250, 0))
    connect(find_pin(entry, "GridX", "Output"), find_pin(valid, "Grid X", "Input") or find_pin(valid, "GridX", "Input"), "gx-v")
    connect(find_pin(entry, "GridY", "Output"), find_pin(valid, "Grid Y", "Input") or find_pin(valid, "GridY", "Input"), "gy-v")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(500, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
    connect(find_pin(valid, "Return Value", "Output") or find_pin(valid, "ReturnValue", "Output"),
            find_pin(br, "Condition", "Input"), "valid")

    get_plots = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_plots, pos(500, 180))
    get_w = ge.add_get_member_variable_node("GridWidth")
    bel.set_node_pos(get_w, pos(500, 280))

    mul = ge.create_node_from_name("Utilities|Operators|Multiply", unreal.Vector2D(700, 220), [])
    bel.set_node_pos(mul, pos(700, 220))
    addn = ge.create_node_from_name("Utilities|Operators|Add", unreal.Vector2D(900, 220), [])
    bel.set_node_pos(addn, pos(900, 220))
    connect(find_pin(entry, "GridY", "Output"), find_pin(mul, "A", "Input"), "gy*")
    connect(find_pin(get_w, "GridWidth", "Output"), find_pin(mul, "B", "Input"), "*w")
    connect(find_pin(mul, "ReturnValue", "Output"), find_pin(addn, "A", "Input"), "mul+")
    connect(find_pin(entry, "GridX", "Output"), find_pin(addn, "B", "Input"), "+gx")

    get_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get_at, pos(1100, 180))
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(get_at, "TargetArray", "Input"), "arr")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(get_at, "Index", "Input"), "idx")

    eq = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
    bel.set_node_pos(eq, pos(1350, 180))
    connect(find_pin(get_at, "Item", "Output"), find_pin(eq, "A", "Input"), "eqA")
    set_val(find_pin(eq, "B", "Input"), "3", "eq.B=Watered")

    br2 = ge.add_branch_node()
    bel.set_node_pos(br2, pos(1550, 0))
    connect(find_pin(br, "then", "Output"), find_pin(br2, "execute", "Input"), "br->br2")
    connect(find_pin(eq, "ReturnValue", "Output"), find_pin(br2, "Condition", "Input"), "eq->br2")

    set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
    bel.set_node_pos(set_at, pos(1800, 0))
    connect(find_pin(br2, "then", "Output"), find_pin(set_at, "execute", "Input"), "br2->set")
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(set_at, "TargetArray", "Input"), "setarr")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(set_at, "Index", "Input"), "setidx")
    set_val(find_pin(set_at, "Item", "Input"), "4", "set.Item=Ready")
    set_val(find_pin(set_at, "bSizeToFit", "Input"), "true", "fit")

    g2w = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GridToWorld")
    bel.set_node_pos(g2w, pos(2050, 0))
    connect(find_pin(entry, "GridX", "Output"), find_pin(g2w, "Grid X", "Input") or find_pin(g2w, "GridX", "Input"), "gx-g2w")
    connect(find_pin(entry, "GridY", "Output"), find_pin(g2w, "Grid Y", "Input") or find_pin(g2w, "GridY", "Input"), "gy-g2w")

    dbg = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugBox")
    bel.set_node_pos(dbg, pos(2350, 0))
    g2w_exec = find_pin(g2w, "execute", "Input")
    if g2w_exec:
        connect(find_pin(set_at, "then", "Output"), g2w_exec, "set->g2w")
        connect(find_pin(g2w, "then", "Output"), find_pin(dbg, "execute", "Input"), "g2w->dbg")
    else:
        connect(find_pin(set_at, "then", "Output"), find_pin(dbg, "execute", "Input"), "set->dbg")
    connect(
        find_pin(g2w, "World Location", "Output") or find_pin(g2w, "ReturnValue", "Output") or find_pin(g2w, "WorldLocation", "Output"),
        find_pin(dbg, "Center", "Input"),
        "center",
    )

    make_v = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(make_v, pos(2150, 250))
    set_val(find_pin(make_v, "X", "Input"), "30.0", "X")
    set_val(find_pin(make_v, "Y", "Input"), "30.0", "Y")
    set_val(find_pin(make_v, "Z", "Input"), "4.0", "Z")
    connect(find_pin(make_v, "ReturnValue", "Output"), find_pin(dbg, "Extent", "Input"), "extent")
    set_val(find_pin(dbg, "LineColor", "Input"), "(R=1.0,G=0.9,B=0.1,A=1.0)", "yellow")
    set_val(find_pin(dbg, "Duration", "Input"), "99999.0", "dur")
    set_val(find_pin(dbg, "Thickness", "Input"), "3.0", "th")

    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(2650, 0))
    connect(find_pin(dbg, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "dbg->ret")
    set_val(find_pin(ret_ok, "Success", "Input"), "true", "ok")

    ret_f1 = ge.add_return_node()
    bel.set_node_pos(ret_f1, pos(1800, 200))
    connect(find_pin(br, "else", "Output"), find_pin(ret_f1, "execute", "Input"), "br else")
    ret_f2 = ge.add_return_node()
    bel.set_node_pos(ret_f2, pos(1800, 350))
    connect(find_pin(br2, "else", "Output"), find_pin(ret_f2, "execute", "Input"), "br2 else")
    for rn in (ret_f1, ret_f2):
        set_val(find_pin(rn, "Success", "Input"), "false", "fail")

    try:
        bel.compile_blueprint(bp)
        unreal.log("GrowCell compile ok")
    except Exception as ex:
        unreal.log_warning("compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    return True


def main():
    unreal.log("=== phase5_grow_cell start ===")
    ensure_ready_enum()
    ok = build_grow_cell()
    unreal.log("=== phase5_grow_cell done ok=" + str(ok) + " ===")


if __name__ == "__main__":
    main()
