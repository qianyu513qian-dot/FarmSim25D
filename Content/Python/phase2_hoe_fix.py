# -*- coding: utf-8 -*-
"""Fix TillCell + wire IA_Interact Started -> foot WorldToGrid -> TillCell."""
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


def rebuild_till_cell():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    # remove existing TillCell if any
    try:
        bel.remove_function_graph(bp, "TillCell")
        unreal.log("removed old TillCell")
    except Exception as ex:
        unreal.log_warning("remove: " + str(ex))

    bel.add_function_graph(bp, "TillCell")
    graph = bel.find_graph(bp, "TillCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)

    # clear auto return? keep entry
    # remove all except entry
    entry = None
    to_del = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            to_del.append(n)
    if to_del:
        ge.remove_nodes(to_del)

    # ensure params
    # re-add if missing
    has_gx = find_pin(entry, "GridX", "Output") is not None
    if not has_gx:
        ge.add_graph_input_parameter("GridX", make_int_pin())
        ge.add_graph_input_parameter("GridY", make_int_pin())
    # always ensure Success output
    has_succ = False
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionResult":
            if find_pin(n, "Success"):
                has_succ = True
    if not has_succ:
        try:
            ge.add_graph_output_parameter("Success", make_bool_pin())
        except Exception as ex:
            unreal.log_warning("out param: " + str(ex))

    # refresh entry
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
    dump(get_at, "get")
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(get_at, "TargetArray", "Input"), "arr")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(get_at, "Index", "Input"), "idx")

    eq = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
    bel.set_node_pos(eq, pos(1350, 180))
    dump(eq, "eq")
    connect(find_pin(get_at, "Item", "Output"), find_pin(eq, "A", "Input"), "eqA")
    bpin = find_pin(eq, "B", "Input")
    if bpin:
        # Empty = 0
        try:
            bpin.set_pin_value("0")
            unreal.log("eqB=0 Empty")
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
    item = find_pin(set_at, "Item", "Input")
    if item:
        try:
            item.set_pin_value("1")  # Tilled
            unreal.log("set Item=1 Tilled")
        except Exception as ex:
            unreal.log_warning(str(ex))
    sfit = find_pin(set_at, "bSizeToFit", "Input")
    if sfit:
        try:
            sfit.set_pin_value("true")
        except Exception:
            pass

    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(2100, 0))
    connect(find_pin(set_at, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "set->ret")
    sp = find_pin(ret_ok, "Success", "Input")
    if sp:
        try:
            sp.set_pin_value("true")
        except Exception as ex:
            unreal.log_warning(str(ex))

    ret_f1 = ge.add_return_node()
    bel.set_node_pos(ret_f1, pos(1800, 200))
    connect(find_pin(br, "else", "Output"), find_pin(ret_f1, "execute", "Input"), "br else")
    ret_f2 = ge.add_return_node()
    bel.set_node_pos(ret_f2, pos(1800, 350))
    connect(find_pin(br2, "else", "Output"), find_pin(ret_f2, "execute", "Input"), "br2 else")
    for rn in (ret_f1, ret_f2):
        sp = find_pin(rn, "Success", "Input")
        if sp:
            try:
                sp.set_pin_value("false")
            except Exception:
                pass

    try:
        bel.compile_blueprint(bp)
        unreal.log("TillCell rebuilt compile ok")
    except Exception as ex:
        unreal.log_warning("compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)


def cleanup_and_wire_character():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    # Remove orphan TillCell / Branch / Print from failed attempt (nodes not connected from IA)
    # Keep if we rewire carefully: remove Call TillCell and nearby branch/prints that are loose
    remove = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        cls = n.get_class().get_name()
        if t == "TillCell" or (cls == "K2Node_IfThenElse" and bel.get_node_pos(n).x < -100 and bel.get_node_pos(n).y > 500):
            # check if connected from Enhanced input - if not, remove
            exe = find_pin(n, "execute", "Input")
            linked = list(exe.list_connected_pins()) if exe else []
            if not linked:
                remove.append(n)
                unreal.log("remove orphan " + t)
        if t == "Print String":
            # remove prints that say Tilled/Cannot if orphan
            insp = find_pin(n, "InString", "Input")
            val = ""
            try:
                val = insp.get_pin_value() if insp else ""
            except Exception:
                pass
            if val in ("Tilled!", "Cannot till"):
                remove.append(n)
    if remove:
        ge.remove_nodes(remove)

    # Create IA_Interact Enhanced Action Events
    ia_node = ge.create_node_from_name("Input|EnhancedActionEvents|IA_Interact", unreal.Vector2D(-1800, 700), [])
    if not ia_node:
        ia_node = ge.create_node_from_name("Input|KeyboardEvents|E", unreal.Vector2D(-1800, 700), [])
        unreal.log("fallback Keyboard E " + str(bool(ia_node)))
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
    dump(till, "till")
    connect(ref_out, find_pin(till, "self", "Input"), "ref-till")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(till, "GridX", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(till, "GridY", "Input"), "gy")

    # Prefer Started for boolean press; else Pressed; else Triggered
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

    # Map E on IMC if possible
    try:
        ia = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/Actions/IA_Interact")
        imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
        k = unreal.Key()
        k.set_editor_property("key_name", "E")
        imc.map_key(ia, k)
        unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Input/IMC_Default")
        unreal.log("mapped E via Key key_name")
    except Exception as ex:
        unreal.log_warning("map E: " + str(ex))

    try:
        bel.compile_blueprint(bp)
        unreal.log("char compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def main():
    unreal.log("=== phase2_hoe_fix start ===")
    rebuild_till_cell()
    cleanup_and_wire_character()
    unreal.log("=== phase2_hoe_fix done ===")


if __name__ == "__main__":
    main()