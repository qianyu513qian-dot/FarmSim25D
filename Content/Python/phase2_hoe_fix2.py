# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


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


def dump(node, label):
    for p in bel.list_all_pins(node):
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def make_int_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="int")')
    return p


def make_bool_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="bool")')
    return p


def open_till_ge(bp):
    # Prefer create_and_edit
    event_ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    try:
        event_ge.create_and_edit_function_graph("TillCell")
        unreal.log("create_and_edit_function_graph")
    except Exception as ex:
        unreal.log_warning("create_and_edit: " + str(ex))
        try:
            bel.add_function_graph(bp, "TillCell")
        except Exception as ex2:
            unreal.log_warning("add_function_graph: " + str(ex2))

    names = list(bel.list_graph_names(bp))
    unreal.log("graphs: " + str(names))
    graph = None
    for n in names:
        if "TillCell" in str(n):
            graph = bel.find_graph(bp, n)
            unreal.log("found graph " + str(n) + " -> " + str(graph))
            break
    if graph:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
        if ge:
            return ge
        ge = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "TillCell")
        unreal.log("by_name " + str(ge))
        return ge
    # try get_graph_editor_by_name directly
    ge = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "TillCell")
    unreal.log("direct by_name " + str(ge))
    return ge


def rebuild_till_cell():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    # remove if exists
    try:
        bel.remove_function_graph(bp, "TillCell")
        unreal.log("removed TillCell")
    except Exception as ex:
        unreal.log_warning(str(ex))

    ge = open_till_ge(bp)
    if not ge:
        unreal.log_error("no TillCell graph editor")
        return

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
    try:
        ge.add_graph_output_parameter("Success", make_bool_pin())
    except Exception as ex:
        unreal.log_warning("out: " + str(ex))

    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
    dump(entry, "entry")

    valid = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:IsValidCell")
    bel.set_node_pos(valid, pos(250, 0))
    connect(find_pin(entry, "GridX", "Output"), find_pin(valid, "Grid X", "Input"), "gx")
    connect(find_pin(entry, "GridY", "Output"), find_pin(valid, "Grid Y", "Input"), "gy")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(500, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "entry->br")
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
    try:
        find_pin(eq, "B", "Input").set_pin_value("0")
    except Exception as ex:
        unreal.log_warning(str(ex))

    br2 = ge.add_branch_node()
    bel.set_node_pos(br2, pos(1550, 0))
    connect(find_pin(br, "then", "Output"), find_pin(br2, "execute", "Input"), "br->br2")
    connect(find_pin(eq, "ReturnValue", "Output"), find_pin(br2, "Condition", "Input"), "eq->br2")

    set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
    bel.set_node_pos(set_at, pos(1800, 0))
    dump(set_at, "set")
    connect(find_pin(br2, "then", "Output"), find_pin(set_at, "execute", "Input"), "br2->set")
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(set_at, "TargetArray", "Input"), "setarr")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(set_at, "Index", "Input"), "setidx")
    try:
        find_pin(set_at, "Item", "Input").set_pin_value("1")
        unreal.log("Item=1")
    except Exception as ex:
        unreal.log_warning(str(ex))
    try:
        find_pin(set_at, "bSizeToFit", "Input").set_pin_value("true")
    except Exception:
        pass

    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(2100, 0))
    connect(find_pin(set_at, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "set->ret")
    try:
        find_pin(ret_ok, "Success", "Input").set_pin_value("true")
    except Exception as ex:
        unreal.log_warning(str(ex))

    ret_f1 = ge.add_return_node()
    bel.set_node_pos(ret_f1, pos(1800, 200))
    connect(find_pin(br, "else", "Output"), find_pin(ret_f1, "execute", "Input"), "br else")
    ret_f2 = ge.add_return_node()
    bel.set_node_pos(ret_f2, pos(1800, 350))
    connect(find_pin(br2, "else", "Output"), find_pin(ret_f2, "execute", "Input"), "br2 else")
    for rn in (ret_f1, ret_f2):
        try:
            find_pin(rn, "Success", "Input").set_pin_value("false")
        except Exception:
            pass

    try:
        bel.compile_blueprint(bp)
        unreal.log("TillCell compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)


def wire_character():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    remove = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "TillCell":
            exe = find_pin(n, "execute", "Input")
            if exe and not list(exe.list_connected_pins()):
                remove.append(n)
        if t == "Print String":
            insp = find_pin(n, "InString", "Input")
            try:
                val = insp.get_pin_value() if insp else ""
            except Exception:
                val = ""
            if val in ("Tilled!", "Cannot till"):
                remove.append(n)
        # orphan branches near hoe area
        if n.get_class().get_name() == "K2Node_IfThenElse":
            p = bel.get_node_pos(n)
            if p.x < 0 and p.y > 500:
                exe = find_pin(n, "execute", "Input")
                if exe and not list(exe.list_connected_pins()):
                    remove.append(n)
    if remove:
        ge.remove_nodes(list(set(remove)))
        unreal.log("removed orphans " + str(len(remove)))

    ia_node = ge.create_node_from_name("Input|EnhancedActionEvents|IA_Interact", unreal.Vector2D(-1800, 700), [])
    if not ia_node:
        ia_node = ge.create_node_from_name("Input|KeyboardEvents|E", unreal.Vector2D(-1800, 700), [])
    bel.set_node_pos(ia_node, pos(-1800, 700))
    dump(ia_node, "ia")

    get_ref = ge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1500, 750))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output")

    get_loc = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1500, 850))

    w2g = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    bel.set_node_pos(w2g, pos(-1200, 750))
    connect(ref_out, find_pin(w2g, "self", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output"), find_pin(w2g, "WorldLocation", "Input"), "loc")

    till = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:TillCell")
    bel.set_node_pos(till, pos(-850, 750))
    connect(ref_out, find_pin(till, "self", "Input"), "ref-till")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(till, "GridX", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(till, "GridY", "Input"), "gy")

    start = find_pin(ia_node, "Started", "Output") or find_pin(ia_node, "Pressed", "Output") or find_pin(ia_node, "Triggered", "Output")
    connect(start, find_pin(till, "execute", "Input"), "ia->till")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(-550, 750))
    connect(find_pin(till, "then", "Output"), find_pin(br, "execute", "Input"), "till->br")
    connect(find_pin(till, "Success", "Output"), find_pin(br, "Condition", "Input"), "succ")

    pr_ok = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-250, 700))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    try:
        find_pin(pr_ok, "InString", "Input").set_pin_value("Tilled!")
    except Exception:
        pass

    pr_no = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-250, 850))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
    try:
        find_pin(pr_no, "InString", "Input").set_pin_value("Cannot till")
    except Exception:
        pass

    try:
        ia = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/Actions/IA_Interact")
        imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
        k = unreal.Key()
        k.set_editor_property("key_name", "E")
        imc.map_key(ia, k)
        unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Input/IMC_Default")
        unreal.log("E mapped")
    except Exception as ex:
        unreal.log_warning("map: " + str(ex))

    try:
        bel.compile_blueprint(bp)
        unreal.log("char ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def main():
    unreal.log("=== phase2_hoe_fix2 start ===")
    rebuild_till_cell()
    wire_character()
    unreal.log("=== phase2_hoe_fix2 done ===")


if __name__ == "__main__":
    main()