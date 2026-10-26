# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary

MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


def pos(x, y):
    return unreal.IntPoint(x, y)


def connect(a, b):
    if a is None or b is None:
        unreal.log_warning("connect skipped None")
        return False
    ok = a.try_create_connection(b)
    unreal.log("connect {} -> {} : {}".format(a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        pname = str(p.get_pin_name())
        direc = str(p.get_pin_direction())
        if name_substr.lower() in pname.lower():
            if direction is None or direction.lower() in direc.lower():
                return p
    return None


def dump_pins(node, label=""):
    for p in bel.list_all_pins(node):
        unreal.log("  pin[{}] {} | {} | {}".format(
            label, p.get_pin_name(), p.get_pin_direction(), p.get_pin_type_display_string()))


def ge_for(bp_path):
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    g = bel.find_event_graph(bp)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    return bp, ge


def wire_gridmanager_init():
    bp, ge = ge_for(MGR)
    begin = ge.find_event_node("ReceiveBeginPlay")
    bel.set_node_pos(begin, pos(0, 0))

    clear_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Clear")
    bel.set_node_pos(clear_n, pos(280, 0))
    dump_pins(clear_n, "clear")

    get_arr = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_arr, pos(80, 140))
    dump_pins(get_arr, "getarr")

    arr_pin = find_pin(clear_n, "TargetArray") or find_pin(clear_n, "Array")
    get_out = find_pin(get_arr, "PlotStates", "Output") or bel.find_output_pin_by_index(get_arr, 0)
    connect(get_out, arr_pin)

    begin_then = bel.find_then_pin(begin) or find_pin(begin, "then", "Output")
    clear_exec = bel.find_execute_pin(clear_n) or find_pin(clear_n, "execute", "Input")
    if begin_then:
        try:
            begin_then.break_pin_links()
        except Exception:
            pass
    connect(begin_then, clear_exec)

    for_n = ge.create_node_from_name("Utilities|FlowControl|ForLoop", unreal.Vector2D(600, 0), [])
    if for_n:
        bel.set_node_pos(for_n, pos(600, 0))
        dump_pins(for_n, "for")
    else:
        unreal.log_error("ForLoop create failed")
        return

    get_w = ge.add_get_member_variable_node("GridWidth")
    get_h = ge.add_get_member_variable_node("GridHeight")
    bel.set_node_pos(get_w, pos(320, 220))
    bel.set_node_pos(get_h, pos(320, 300))

    mul = ge.create_node_from_name("Utilities|Operators|integer * integer", unreal.Vector2D(450, 250), [])
    if not mul:
        mul = ge.create_node_from_name("Math|Integer|integer * integer", unreal.Vector2D(450, 250), [])
    if mul:
        bel.set_node_pos(mul, pos(450, 250))
        dump_pins(mul, "mul")
        w_out = find_pin(get_w, "GridWidth", "Output") or bel.find_output_pin_by_index(get_w, 0)
        h_out = find_pin(get_h, "GridHeight", "Output") or bel.find_output_pin_by_index(get_h, 0)
        mul_a = find_pin(mul, "A", "Input") or bel.find_input_pin_by_index(mul, 0)
        mul_b = find_pin(mul, "B", "Input") or bel.find_input_pin_by_index(mul, 1)
        connect(w_out, mul_a)
        connect(h_out, mul_b)
    else:
        unreal.log_error("multiply create failed")

    sub = ge.create_node_from_name("Utilities|Operators|integer - integer", unreal.Vector2D(520, 250), [])
    if sub:
        bel.set_node_pos(sub, pos(520, 250))
        dump_pins(sub, "sub")
        mul_out = bel.find_output_pin_by_index(mul, 0) if mul else None
        sub_a = find_pin(sub, "A", "Input") or bel.find_input_pin_by_index(sub, 0)
        sub_b = find_pin(sub, "B", "Input") or bel.find_input_pin_by_index(sub, 1)
        connect(mul_out, sub_a)
        if sub_b:
            sub_b.set_pin_value("1")
        last_pin = find_pin(for_n, "LastIndex") or find_pin(for_n, "Last")
        sub_out = bel.find_output_pin_by_index(sub, 0)
        connect(sub_out, last_pin)

    clear_then = bel.find_then_pin(clear_n) or find_pin(clear_n, "then", "Output")
    for_exec = bel.find_execute_pin(for_n) or find_pin(for_n, "execute", "Input")
    connect(clear_then, for_exec)

    add_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Add")
    bel.set_node_pos(add_n, pos(980, 80))
    dump_pins(add_n, "add")

    get_arr2 = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_arr2, pos(760, 220))
    arr_pin2 = find_pin(add_n, "TargetArray") or find_pin(add_n, "Array")
    get2_out = find_pin(get_arr2, "PlotStates", "Output") or bel.find_output_pin_by_index(get_arr2, 0)
    connect(get2_out, arr_pin2)

    item_pin = find_pin(add_n, "NewItem") or find_pin(add_n, "Item")
    if item_pin:
        for v in ("Empty", "0", "NewEnumerator0"):
            try:
                item_pin.set_pin_value(v)
                unreal.log("NewItem set to " + v)
                break
            except Exception as ex:
                unreal.log_warning("NewItem {}: {}".format(v, ex))

    loop_body = find_pin(for_n, "LoopBody") or find_pin(for_n, "Loop Body")
    add_exec = bel.find_execute_pin(add_n) or find_pin(add_n, "execute", "Input")
    connect(loop_body, add_exec)

    try:
        bel.compile_blueprint(bp)
        unreal.log("GridManager compile ok")
    except Exception as ex:
        unreal.log_warning("GridManager compile: {}".format(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)


def wire_character_cache():
    bp, ge = ge_for(CHAR)
    begin = ge.find_event_node("ReceiveBeginPlay")
    if not begin:
        try:
            bel.add_event_override(bp, "ReceiveBeginPlay")
            # refresh ge
            bp, ge = ge_for(CHAR)
            begin = ge.find_event_node("ReceiveBeginPlay")
        except Exception as ex:
            unreal.log_warning(str(ex))
    if not begin:
        unreal.log_error("no BeginPlay on character")
        return

    bel.set_node_pos(begin, pos(-1400, -900))

    get_cls = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
    bel.set_node_pos(get_cls, pos(-1100, -900))
    dump_pins(get_cls, "getactor")

    class_pin = find_pin(get_cls, "ActorClass") or find_pin(get_cls, "Actor Class")
    if class_pin:
        for v in (
            "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C",
            "BP_GridManager_C",
            "BP_GridManager",
        ):
            try:
                class_pin.set_pin_value(v)
                unreal.log("ActorClass=" + v)
                break
            except Exception as ex:
                unreal.log_warning("ActorClass {}: {}".format(v, ex))

    set_ref = ge.add_set_member_variable_node("GridManagerRef")
    bel.set_node_pos(set_ref, pos(-700, -900))
    dump_pins(set_ref, "setref")

    begin_then = bel.find_then_pin(begin) or find_pin(begin, "then", "Output")
    if begin_then:
        try:
            begin_then.break_pin_links()
        except Exception:
            pass
    get_exec = bel.find_execute_pin(get_cls) or find_pin(get_cls, "execute", "Input")
    connect(begin_then, get_exec)

    get_then = bel.find_then_pin(get_cls) or find_pin(get_cls, "then", "Output")
    set_exec = bel.find_execute_pin(set_ref) or find_pin(set_ref, "execute", "Input")
    connect(get_then, set_exec)

    ret = find_pin(get_cls, "ReturnValue") or find_pin(get_cls, "Return Value")
    set_val = None
    for p in bel.list_all_pins(set_ref):
        pn = str(p.get_pin_name())
        pd = str(p.get_pin_direction()).lower()
        if "input" in pd and "exec" not in pn.lower() and "self" not in pn.lower():
            set_val = p
            break
    connect(ret, set_val)

    get_ref = ge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-500, 40))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output") or bel.find_output_pin_by_index(get_ref, 0)

    for n in ge.list_all_nodes():
        title = bel.get_node_title(n)
        if "Get Actor Of Class" in title:
            unreal.log("retarget " + n.get_name())
            ret_pin = find_pin(n, "ReturnValue") or find_pin(n, "Return Value")
            if ret_pin and ref_out:
                for cp in list(ret_pin.list_connected_pins()):
                    try:
                        ret_pin.break_single_pin_link(cp)
                    except Exception as ex:
                        unreal.log_warning(str(ex))
                    connect(ref_out, cp)

    try:
        bel.compile_blueprint(bp)
        unreal.log("Character compile ok")
    except Exception as ex:
        unreal.log_warning("Character compile: {}".format(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def main():
    unreal.log("=== phase1_wire_beginplay start ===")
    wire_gridmanager_init()
    wire_character_cache()
    unreal.log("=== phase1_wire_beginplay done ===")


if __name__ == "__main__":
    main()