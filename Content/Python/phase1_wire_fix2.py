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
        unreal.log("  pin[{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def fix_gridmanager_lastindex():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    # find ForLoop
    for_n = None
    for n in ge.list_all_nodes():
        if "ForLoop" in n.get_class().get_name() or "For Loop" in bel.get_node_title(n):
            for_n = n
            unreal.log("found for " + n.get_name())
            break
    if not for_n:
        unreal.log_error("no ForLoop")
        return

    # remove stray Multiply from probe if any without connections - optional
    get_w = ge.add_get_member_variable_node("GridWidth")
    get_h = ge.add_get_member_variable_node("GridHeight")
    bel.set_node_pos(get_w, pos(300, 220))
    bel.set_node_pos(get_h, pos(300, 300))

    mul = ge.create_node_from_name("Utilities|Operators|Multiply", unreal.Vector2D(450, 250), [])
    bel.set_node_pos(mul, pos(450, 250))
    dump_pins(mul, "mul")

    # promote pins to int by setting values / connecting ints
    w_out = find_pin(get_w, "GridWidth", "Output") or bel.find_output_pin_by_index(get_w, 0)
    h_out = find_pin(get_h, "GridHeight", "Output") or bel.find_output_pin_by_index(get_h, 0)
    mul_a = find_pin(mul, "A", "Input") or bel.find_input_pin_by_index(mul, 0)
    mul_b = find_pin(mul, "B", "Input") or bel.find_input_pin_by_index(mul, 1)
    connect(w_out, mul_a)
    connect(h_out, mul_b)
    dump_pins(mul, "mul_after")

    sub = ge.create_node_from_name("Utilities|Operators|Subtract", unreal.Vector2D(560, 250), [])
    if not sub:
        sub = ge.create_node_from_name("Utilities|Operators|-", unreal.Vector2D(560, 250), [])
    bel.set_node_pos(sub, pos(560, 250))
    dump_pins(sub, "sub")
    mul_out = bel.find_output_pin_by_index(mul, 0) or find_pin(mul, "Return", "Output")
    sub_a = find_pin(sub, "A", "Input") or bel.find_input_pin_by_index(sub, 0)
    sub_b = find_pin(sub, "B", "Input") or bel.find_input_pin_by_index(sub, 1)
    connect(mul_out, sub_a)
    if sub_b:
        try:
            sub_b.set_pin_value("1")
        except Exception as ex:
            unreal.log_warning(str(ex))
    last_pin = find_pin(for_n, "LastIndex")
    sub_out = bel.find_output_pin_by_index(sub, 0) or find_pin(sub, "Return", "Output")
    # break existing lastindex links
    if last_pin:
        try:
            last_pin.break_pin_links()
        except Exception:
            pass
    connect(sub_out, last_pin)

    try:
        bel.compile_blueprint(bp)
        unreal.log("GridManager compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)


def wire_character():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    begin = bel.add_event_override(bp, "ReceiveBeginPlay", pos(-1400, -900))
    unreal.log("begin=" + str(begin))
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    if not begin:
        begin = ge.find_event_node("ReceiveBeginPlay")
    if not begin:
        unreal.log_error("still no begin")
        return

    get_cls = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
    bel.set_node_pos(get_cls, pos(-1100, -900))
    dump_pins(get_cls, "getactor")

    class_pin = find_pin(get_cls, "ActorClass")
    if class_pin:
        for v in (
            "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C",
            "BP_GridManager_C",
        ):
            try:
                class_pin.set_pin_value(v)
                unreal.log("ActorClass set " + v)
                break
            except Exception as ex:
                unreal.log_warning(str(ex))

    set_ref = ge.add_set_member_variable_node("GridManagerRef")
    bel.set_node_pos(set_ref, pos(-700, -900))
    dump_pins(set_ref, "setref")

    begin_then = bel.find_then_pin(begin) or find_pin(begin, "then", "Output")
    if begin_then:
        try:
            begin_then.break_pin_links()
        except Exception:
            pass
    connect(begin_then, bel.find_execute_pin(get_cls) or find_pin(get_cls, "execute", "Input"))
    connect(bel.find_then_pin(get_cls) or find_pin(get_cls, "then", "Output"),
            bel.find_execute_pin(set_ref) or find_pin(set_ref, "execute", "Input"))

    ret = find_pin(get_cls, "ReturnValue")
    set_val = None
    for p in bel.list_all_pins(set_ref):
        pn = str(p.get_pin_name())
        pd = str(p.get_pin_direction()).lower()
        if "input" in pd and "exec" not in pn.lower() and "self" not in pn.lower():
            set_val = p
            break
    connect(ret, set_val)

    # Retarget Tick GetActorOfClass return -> GridManagerRef get
    get_ref = ge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-500, 40))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output") or bel.find_output_pin_by_index(get_ref, 0)

    for n in ge.list_all_nodes():
        if "Get Actor Of Class" in bel.get_node_title(n):
            unreal.log("retarget " + n.get_name())
            ret_pin = find_pin(n, "ReturnValue")
            if ret_pin and ref_out:
                for cp in list(ret_pin.list_connected_pins()):
                    try:
                        ret_pin.break_single_pin_link(cp)
                    except Exception as ex:
                        unreal.log_warning(str(ex))
                    connect(ref_out, cp)
            # Bypass GetActorOfClass in exec chain: Tick -> next after GetActor
            # Find what GetActor then connects to, connect Tick then to that, leave GetActor orphaned for now
            tick = ge.find_event_node("ReceiveTick")
            if tick:
                tick_then = bel.find_then_pin(tick) or find_pin(tick, "then", "Output")
                get_exec_in = bel.find_execute_pin(n) or find_pin(n, "execute", "Input")
                get_then = bel.find_then_pin(n) or find_pin(n, "then", "Output")
                # if tick connects to this getactor, skip over it
                if tick_then and get_then:
                    next_pins = list(get_then.list_connected_pins())
                    try:
                        tick_then.break_pin_links()
                    except Exception:
                        pass
                    for np in next_pins:
                        connect(tick_then, np)

    try:
        bel.compile_blueprint(bp)
        unreal.log("Character compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def main():
    unreal.log("=== phase1_fix2 start ===")
    fix_gridmanager_lastindex()
    wire_character()
    unreal.log("=== phase1_fix2 done ===")


if __name__ == "__main__":
    main()