# -*- coding: utf-8 -*-
"""Phase2 hoe v2: GridManager.TillCell(GX,GY) + Character E key calls it."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
ENUM = "/Game/Farm/Grid/E_PlotState"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
ACTIONS_DIR = "/Game/TopDown/Input/Actions"
IMC_PATH = "/Game/TopDown/Input/IMC_Default"
IA_PATH = ACTIONS_DIR + "/IA_Interact"


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip None " + label)
        return False
    ok = a.try_create_connection(b)
    unreal.log("conn[{}] {} -> {} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if node is None:
        return None
    for p in bel.list_all_pins(node):
        pname = str(p.get_pin_name())
        direc = str(p.get_pin_direction())
        if name_substr.lower() in pname.lower():
            if direction is None or direction.lower() in direc.lower():
                return p
    return None


def dump_pins(node, label=""):
    if not node:
        return
    for p in bel.list_all_pins(node):
        unreal.log("  pin[{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def make_int_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="int")')
    return p


def make_bool_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="bool")')
    return p


def ensure_ia_interact():
    if unreal.EditorAssetLibrary.does_asset_exist(IA_PATH):
        ia = unreal.EditorAssetLibrary.load_asset(IA_PATH)
        unreal.log("IA_Interact exists")
    else:
        factory = unreal.InputAction_Factory()
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        ia = tools.create_asset("IA_Interact", ACTIONS_DIR, unreal.InputAction, factory)
        unreal.log("Created IA_Interact " + str(ia))
    if ia:
        try:
            ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
        except Exception as ex:
            unreal.log_warning(str(ex))
        unreal.EditorAssetLibrary.save_asset(IA_PATH)
        imc = unreal.EditorAssetLibrary.load_asset(IMC_PATH)
        try:
            imc.map_key(ia, unreal.Key.E)
            unreal.log("mapped E")
        except Exception as ex:
            unreal.log_warning("map E: " + str(ex))
        unreal.EditorAssetLibrary.save_asset(IMC_PATH)


def ensure_till_cell():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    funcs = list(bel.list_functions(bp)) if hasattr(bel, "list_functions") else []
    unreal.log("funcs: " + str(funcs))
    if any("TillCell" == str(f) or str(f).endswith("TillCell") for f in funcs):
        unreal.log("TillCell exists, skip create")
        return

    # create function graph
    try:
        bel.add_function_graph(bp, "TillCell")
        unreal.log("add_function_graph TillCell ok")
    except Exception as ex:
        unreal.log_warning("add_function_graph: " + str(ex))
        try:
            ge0 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
            ge0.create_and_edit_function_graph("TillCell")
            unreal.log("create_and_edit_function_graph ok")
        except Exception as ex2:
            unreal.log_error("cannot create TillCell: " + str(ex2))
            return

    # open function graph editor
    graph = bel.find_graph(bp, "TillCell")
    if not graph:
        # try list
        names = list(bel.list_graph_names(bp))
        unreal.log("graphs: " + str(names))
        for n in names:
            if "TillCell" in str(n):
                graph = bel.find_graph(bp, n)
                break
    if not graph:
        unreal.log_error("TillCell graph not found")
        return

    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    unreal.log("editing TillCell")

    # Add inputs GridX, GridY and output Success
    try:
        ge.add_graph_input_parameter("GridX", make_int_pin())
        ge.add_graph_input_parameter("GridY", make_int_pin())
        ge.add_graph_output_parameter("Success", make_bool_pin())
        unreal.log("params added")
    except Exception as ex:
        unreal.log_warning("params: " + str(ex))

    # Find entry / function entry node
    entry = None
    for n in ge.list_all_nodes():
        cls = n.get_class().get_name()
        title = bel.get_node_title(n)
        unreal.log("TillCell node: " + title + " | " + cls)
        if "FunctionEntry" in cls or "Function Entry" in title or cls == "K2Node_FunctionEntry":
            entry = n
    if not entry:
        unreal.log_error("no function entry")
        return

    dump_pins(entry, "entry")

    # IsValidCell call
    valid = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:IsValidCell")
    if not valid:
        valid = ge.create_node_from_name("Is Valid Cell", unreal.Vector2D(200, 0), [])
    bel.set_node_pos(valid, pos(200, 0))
    dump_pins(valid, "valid")

    # Connect GridX/Y from entry
    connect(find_pin(entry, "GridX", "Output") or find_pin(entry, "Grid X", "Output"),
            find_pin(valid, "Grid X", "Input") or find_pin(valid, "GridX", "Input"), "gx->valid")
    connect(find_pin(entry, "GridY", "Output") or find_pin(entry, "Grid Y", "Output"),
            find_pin(valid, "Grid Y", "Input") or find_pin(valid, "GridY", "Input"), "gy->valid")

    branch = ge.add_branch_node()
    if not branch:
        branch = ge.create_node_from_name("Branch", unreal.Vector2D(450, 0), [])
    bel.set_node_pos(branch, pos(450, 0))
    connect(bel.find_then_pin(entry) or find_pin(entry, "then", "Output") or find_pin(entry, "execute", "Output"),
            bel.find_execute_pin(branch) or find_pin(branch, "execute", "Input"), "entry->br")
    connect(find_pin(valid, "Return", "Output") or bel.find_output_pin_by_index(valid, 0),
            find_pin(branch, "Condition", "Input"), "valid->cond")

    # Get PlotStates
    get_plots = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_plots, pos(450, 200))
    dump_pins(get_plots, "plots")

    get_w = ge.add_get_member_variable_node("GridWidth")
    bel.set_node_pos(get_w, pos(450, 300))

    mul = ge.create_node_from_name("Utilities|Operators|Multiply", unreal.Vector2D(650, 250), [])
    bel.set_node_pos(mul, pos(650, 250))
    addn = ge.create_node_from_name("Utilities|Operators|Add", unreal.Vector2D(800, 250), [])
    bel.set_node_pos(addn, pos(800, 250))

    connect(find_pin(entry, "GridY", "Output") or find_pin(entry, "Grid Y", "Output"),
            find_pin(mul, "A", "Input") or bel.find_input_pin_by_index(mul, 0), "gy*")
    connect(find_pin(get_w, "GridWidth", "Output") or bel.find_output_pin_by_index(get_w, 0),
            find_pin(mul, "B", "Input") or bel.find_input_pin_by_index(mul, 1), "*w")
    connect(bel.find_output_pin_by_index(mul, 0), find_pin(addn, "A", "Input") or bel.find_input_pin_by_index(addn, 0), "mul+")
    connect(find_pin(entry, "GridX", "Output") or find_pin(entry, "Grid X", "Output"),
            find_pin(addn, "B", "Input") or bel.find_input_pin_by_index(addn, 1), "+gx")

    get_at = ge.create_node_from_name("Utilities|Array|Get", unreal.Vector2D(1000, 200), [])
    if not get_at:
        get_at = ge.create_node_from_name("Get", unreal.Vector2D(1000, 200), [])
    bel.set_node_pos(get_at, pos(1000, 200))
    dump_pins(get_at, "get")
    connect(find_pin(get_plots, "PlotStates", "Output") or bel.find_output_pin_by_index(get_plots, 0),
            find_pin(get_at, "TargetArray", "Input") or find_pin(get_at, "Array", "Input") or bel.find_input_pin_by_index(get_at, 0),
            "arr")
    connect(bel.find_output_pin_by_index(addn, 0),
            find_pin(get_at, "Index", "Input") or bel.find_input_pin_by_index(get_at, 1), "idx")

    eq = ge.create_node_from_name("Equal (Enum)", unreal.Vector2D(1200, 200), [])
    if not eq:
        eq = ge.create_node_from_name("Utilities|Enum|Equal", unreal.Vector2D(1200, 200), [])
    if not eq:
        eq = ge.create_node_from_name("Utilities|Operators|EqualEqual_ByteByte", unreal.Vector2D(1200, 200), [])
    if eq:
        bel.set_node_pos(eq, pos(1200, 200))
        dump_pins(eq, "eq")
        connect(bel.find_output_pin_by_index(get_at, 0) or find_pin(get_at, "Item", "Output"),
                find_pin(eq, "A", "Input") or bel.find_input_pin_by_index(eq, 0), "eqA")
        bpin = find_pin(eq, "B", "Input") or bel.find_input_pin_by_index(eq, 1)
        if bpin:
            for v in ("Empty", "NewEnumerator0", "0"):
                try:
                    bpin.set_pin_value(v)
                    unreal.log("eqB=" + v)
                    break
                except Exception as ex:
                    unreal.log_warning(str(ex))

    branch2 = ge.add_branch_node()
    bel.set_node_pos(branch2, pos(1400, 0))
    connect(find_pin(branch, "True", "Output"), bel.find_execute_pin(branch2), "br->br2")
    if eq:
        connect(bel.find_output_pin_by_index(eq, 0), find_pin(branch2, "Condition", "Input"), "eq->br2")

    # Set Array Elem — use get PlotStates again for ref; in same BP Get member is by ref for set
    set_elem = ge.create_node_from_name("Utilities|Array|Set Array Elem", unreal.Vector2D(1650, 0), [])
    if not set_elem:
        set_elem = ge.create_node_from_name("Set Array Elem", unreal.Vector2D(1650, 0), [])
    bel.set_node_pos(set_elem, pos(1650, 0))
    dump_pins(set_elem, "set")
    connect(find_pin(branch2, "True", "Output"), bel.find_execute_pin(set_elem), "br2->set")
    connect(find_pin(get_plots, "PlotStates", "Output") or bel.find_output_pin_by_index(get_plots, 0),
            find_pin(set_elem, "TargetArray", "Input") or find_pin(set_elem, "Array", "Input"), "setarr")
    connect(bel.find_output_pin_by_index(addn, 0), find_pin(set_elem, "Index", "Input"), "setidx")
    item = find_pin(set_elem, "Item", "Input")
    if item:
        for v in ("Tilled", "NewEnumerator1", "1"):
            try:
                item.set_pin_value(v)
                unreal.log("item=" + v)
                break
            except Exception as ex:
                unreal.log_warning(str(ex))

    # Size to Fit / bSizeToFit
    try:
        sfit = find_pin(set_elem, "SizeToFit", "Input") or find_pin(set_elem, "bSizeToFit", "Input")
        if sfit:
            sfit.set_pin_value("true")
    except Exception:
        pass

    # Return True after set
    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(1950, 0))
    dump_pins(ret_ok, "ret_ok")
    connect(bel.find_then_pin(set_elem) or find_pin(set_elem, "then", "Output"),
            bel.find_execute_pin(ret_ok) or find_pin(ret_ok, "execute", "Input"), "set->ret")
    succ = find_pin(ret_ok, "Success", "Input") or find_pin(ret_ok, "ReturnValue", "Input")
    if succ:
        try:
            succ.set_pin_value("true")
        except Exception as ex:
            unreal.log_warning(str(ex))

    # Return False on fail paths
    ret_fail = ge.add_return_node()
    bel.set_node_pos(ret_fail, pos(1650, 200))
    connect(find_pin(branch, "False", "Output"), bel.find_execute_pin(ret_fail), "brF->ret")
    # also branch2 false
    ret_fail2 = ge.add_return_node()
    bel.set_node_pos(ret_fail2, pos(1650, 350))
    connect(find_pin(branch2, "False", "Output"), bel.find_execute_pin(ret_fail2), "br2F->ret")
    for rn in (ret_fail, ret_fail2):
        sp = find_pin(rn, "Success", "Input") or find_pin(rn, "ReturnValue", "Input")
        if sp:
            try:
                sp.set_pin_value("false")
            except Exception:
                pass

    try:
        bel.compile_blueprint(bp)
        unreal.log("TillCell compile ok")
    except Exception as ex:
        unreal.log_warning("compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)


def wire_character_e():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    # Remove prior failed hoe nodes if marked - skip for now
    key_node = ge.create_node_from_name("Input|Keyboard Events|E", unreal.Vector2D(-1800, 600), [])
    if not key_node:
        key_node = ge.create_node_from_name("E", unreal.Vector2D(-1800, 600), [])
    if not key_node:
        # list available
        try:
            avail = ge.list_available_nodes("E")
            unreal.log("avail E: " + str(avail[:30] if avail else avail))
        except Exception as ex:
            unreal.log_warning(str(ex))
        key_node = ge.create_node_from_name("Input Key", unreal.Vector2D(-1800, 600), [])
    bel.set_node_pos(key_node, pos(-1800, 600))
    dump_pins(key_node, "key")

    get_ref = ge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1500, 650))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output") or bel.find_output_pin_by_index(get_ref, 0)

    get_loc = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1500, 750))

    w2g = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    if not w2g:
        w2g = ge.create_node_from_name("World To Grid", unreal.Vector2D(-1200, 650), [])
    bel.set_node_pos(w2g, pos(-1200, 650))
    dump_pins(w2g, "w2g")
    connect(ref_out, find_pin(w2g, "self", "Input") or find_pin(w2g, "Target", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output") or bel.find_output_pin_by_index(get_loc, 0),
            find_pin(w2g, "World", "Input") or find_pin(w2g, "Location", "Input"), "loc-w2g")

    till = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:TillCell")
    if not till:
        till = ge.create_node_from_name("Till Cell", unreal.Vector2D(-800, 650), [])
    bel.set_node_pos(till, pos(-800, 650))
    dump_pins(till, "till")
    connect(ref_out, find_pin(till, "self", "Input") or find_pin(till, "Target", "Input"), "ref-till")
    connect(find_pin(w2g, "Grid X", "Output") or find_pin(w2g, "X", "Output"),
            find_pin(till, "GridX", "Input") or find_pin(till, "Grid X", "Input"), "gx")
    connect(find_pin(w2g, "Grid Y", "Output") or find_pin(w2g, "Y", "Output"),
            find_pin(till, "GridY", "Input") or find_pin(till, "Grid Y", "Input"), "gy")

    pressed = find_pin(key_node, "Pressed", "Output")
    if not pressed:
        pressed = bel.find_then_pin(key_node) or find_pin(key_node, "then", "Output")
    connect(pressed, bel.find_execute_pin(till) or find_pin(till, "execute", "Input"), "E->till")

    # Branch on Success then Print
    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(-500, 650))
    connect(bel.find_then_pin(till) or find_pin(till, "then", "Output"), bel.find_execute_pin(br), "till->br")
    connect(find_pin(till, "Success", "Output") or find_pin(till, "ReturnValue", "Output") or bel.find_output_pin_by_index(till, 0),
            find_pin(br, "Condition", "Input"), "succ")

    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(-200, 650))
    connect(find_pin(br, "True", "Output"), bel.find_execute_pin(pr), "brT->pr")
    insp = find_pin(pr, "InString", "Input")
    if insp:
        try:
            insp.set_pin_value("Tilled!")
        except Exception:
            pass

    pr2 = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr2, pos(-200, 800))
    connect(find_pin(br, "False", "Output"), bel.find_execute_pin(pr2), "brF->pr")
    insp2 = find_pin(pr2, "InString", "Input")
    if insp2:
        try:
            insp2.set_pin_value("Cannot till")
        except Exception:
            pass

    try:
        bel.compile_blueprint(bp)
        unreal.log("char compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def main():
    unreal.log("=== phase2_hoe_v2 start ===")
    ensure_ia_interact()
    ensure_till_cell()
    wire_character_e()
    unreal.log("=== phase2_hoe_v2 done ===")


if __name__ == "__main__":
    main()