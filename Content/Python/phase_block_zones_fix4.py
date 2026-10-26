# -*- coding: utf-8 -*-
"""Fix TillCell blocked flat-index math (mul/add pins) so Array_Contains gets real cell index."""
import unreal

TAG = "[BLOCK_FIX4]"
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


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
        p = bel.find_output_pin_by_index(node, 0)
        if p:
            return p
    except Exception:
        pass
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()).upper():
            return p
    return None


def in_pin(node, idx=0, names=None):
    if not node:
        return None
    if names:
        for n in names:
            p = find_pin(node, n, "Input")
            if p:
                return p
    try:
        return bel.find_input_pin_by_index(node, idx)
    except Exception:
        pins = [p for p in bel.list_all_pins(node) if "INPUT" in str(p.get_pin_direction()).upper()
                and str(p.get_pin_name()).lower() not in ("execute", "self")]
        return pins[idx] if idx < len(pins) else None


def connect(a, b, label=""):
    if a is None or b is None:
        log("skip {} a={} b={}".format(label, a, b))
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
        log("set {}: {}".format(label, ex))


def dump(node, label):
    if not node:
        log("dump {} NONE".format(label))
        return
    log("dump {} cls={}".format(label, node.get_class().get_name()))
    for p in bel.list_all_pins(node):
        log("  {} | {} | {}".format(p.get_pin_name(), p.get_pin_direction(), p.get_pin_type_display_string()))


def make_int_op(ge, op_paths, xy):
    for path in op_paths:
        try:
            n = ge.create_node_from_name(path, unreal.Vector2D(xy[0], xy[1]), [])
            if n:
                log("created op via " + path)
                return n
        except Exception as ex:
            log("op try {}: {}".format(path, ex))
    # Promotable operator fallback
    try:
        n = ge.create_node_from_name("Utilities|Operators|Multiply", unreal.Vector2D(xy[0], xy[1]), [])
        if n:
            return n
    except Exception:
        pass
    return None


def main():
    log("=== start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    graph = bel.find_graph(bp, "TillCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)

    # Find our recently added nodes: BlockedIndices get, Array_Contains, blocked Branch
    entry = None
    contains = None
    blocked_br = None
    get_bi = None
    get_w = None
    valid_branch = None
    empty_branch = None
    branches = []
    for n in ge.list_all_nodes():
        cls = n.get_class().get_name()
        if cls == "K2Node_FunctionEntry":
            entry = n
        elif cls == "K2Node_IfThenElse":
            branches.append(n)
        elif cls == "K2Node_CallArrayFunction":
            # Array_Contains has ItemToFind
            if find_pin(n, "ItemToFind", "Input"):
                contains = n
        elif cls == "K2Node_VariableGet":
            if find_pin(n, "BlockedIndices", "Output"):
                get_bi = n
            if find_pin(n, "GridWidth", "Output"):
                get_w = n
        elif cls == "K2Node_MacroInstance" or "Branch" in cls:
            if find_pin(n, "Condition", "Input") and find_pin(n, "else", "Output"):
                # might be our blocked branch if fed by contains
                pass

    # Identify Branch nodes: utilities Branch vs IfThenElse
    for n in ge.list_all_nodes():
        if find_pin(n, "Condition", "Input") and find_pin(n, "then", "Output") and find_pin(n, "else", "Output"):
            # Check if condition linked from contains
            cond = find_pin(n, "Condition", "Input")
            # Heuristic: if this is NOT one of the first two IfThenElse used for valid/empty
            if n not in branches[:2]:
                blocked_br = n
            elif contains:
                # check title
                try:
                    t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
                except Exception:
                    t = ""
                if "Branch" in t and n.get_class().get_name() != "K2Node_IfThenElse":
                    blocked_br = n

    # Also find Branch by class name containing Branch but not IfThenElse from our create
    for n in ge.list_all_nodes():
        cn = n.get_class().get_name()
        if cn == "K2Node_MacroInstance":
            try:
                t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
            except Exception:
                t = ""
            if "Branch" in t:
                blocked_br = n
                log("found macro Branch")

    if len(branches) >= 2:
        valid_branch, empty_branch = branches[0], branches[1]
    # If we added a third IfThenElse as blocked
    if len(branches) >= 3:
        # find which has condition from contains
        blocked_br = branches[-1]

    log("entry={} contains={} blocked_br={} get_bi={} get_w={} branches={}".format(
        bool(entry), bool(contains), bool(blocked_br), bool(get_bi), bool(get_w), len(branches)))

    # Remove broken mul/add promotable ops if any orphan near y=600
    # Create fresh Multiply / Add using CallFunction int nodes
    mul = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Multiply_IntInt")
    if not mul:
        mul = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Multiply")
    add = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_IntInt")
    if not add:
        add = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add")
    log("mul={} add={}".format(mul, add))
    dump(mul, "mul")
    dump(add, "add")

    if not mul or not add:
        # Try promotable with force
        mul = make_int_op(ge, [
            "Utilities|Operators|integer * integer",
            "Math|Integer|integer * integer",
            "integer * integer",
        ], (600, 900))
        add = make_int_op(ge, [
            "Utilities|Operators|integer + integer",
            "Math|Integer|integer + integer",
            "integer + integer",
        ], (800, 900))
        dump(mul, "mul2")
        dump(add, "add2")

    if not mul or not add or not contains or not entry:
        log("FATAL missing nodes")
        return

    bel.set_node_pos(mul, pos(600, 900))
    bel.set_node_pos(add, pos(850, 900))
    if not get_w:
        get_w = ge.add_get_member_variable_node("GridWidth")
        bel.set_node_pos(get_w, pos(400, 950))
    if not get_bi:
        get_bi = ge.add_get_member_variable_node("BlockedIndices")
        bel.set_node_pos(get_bi, pos(700, 1050))

    gx = find_pin(entry, "GridX", "Output")
    gy = find_pin(entry, "GridY", "Output")
    dump(entry, "entry")

    # Break ItemToFind links then reconnect
    item_pin = find_pin(contains, "ItemToFind", "Input")
    try:
        item_pin.break_pin_links(False)
    except Exception:
        try:
            item_pin.break_pin_links()
        except Exception:
            pass

    # mul: A=GY B=Width
    mul_a = in_pin(mul, 0, ("A", "X"))
    mul_b = in_pin(mul, 1, ("B", "Y"))
    add_a = in_pin(add, 0, ("A", "X"))
    add_b = in_pin(add, 1, ("B", "Y"))
    log("pins mulA={} mulB={} addA={} addB={}".format(mul_a, mul_b, add_a, add_b))

    connect(gy, mul_a, "GY*W")
    connect(out0(get_w) or find_pin(get_w, "GridWidth", "Output"), mul_b, "W")
    connect(out0(mul), add_a, "mul+")
    connect(gx, add_b, "+GX")
    connect(out0(add), item_pin, "flat->contains")

    # Ensure BI connected
    connect(out0(get_bi) or find_pin(get_bi, "BlockedIndices", "Output"),
            find_pin(contains, "TargetArray", "Input"), "bi")

    # Ensure branch wiring still ok
    if blocked_br:
        connect(find_pin(contains, "ReturnValue", "Output") or out0(contains),
                find_pin(blocked_br, "Condition", "Input"), "cond")

    try:
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(MGR)
        log("compile ok")
    except Exception as ex:
        log("compile: " + str(ex))

    # Verify pin values / links by dumping contains
    dump(contains, "contains_final")
    dump(mul, "mul_final")
    dump(add, "add_final")

    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    except Exception:
        pass
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception:
        pass
    log("=== done ===")


main()
