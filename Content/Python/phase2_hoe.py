# -*- coding: utf-8 -*-
"""Phase2 hoe: Empty -> Tilled on foot cell. IA_Interact (E) + GridManager TillCell/GetPlotState + Character wire + Tick color."""
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
        unreal.log_warning("connect skip None " + label)
        return False
    ok = a.try_create_connection(b)
    unreal.log("connect {} {} -> {} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
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


def ensure_ia_interact():
    if unreal.EditorAssetLibrary.does_asset_exist(IA_PATH):
        ia = unreal.EditorAssetLibrary.load_asset(IA_PATH)
        unreal.log("IA_Interact exists")
    else:
        factory = unreal.InputActionFactory()
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        ia = tools.create_asset("IA_Interact", ACTIONS_DIR, unreal.InputAction, factory)
        unreal.log("Created IA_Interact")
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception as ex:
        unreal.log_warning("set value_type: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(IA_PATH)
    imc = unreal.EditorAssetLibrary.load_asset(IMC_PATH)
    try:
        imc.map_key(ia, unreal.Key.E)
        unreal.log("mapped E to IA_Interact")
    except Exception as ex:
        unreal.log_warning("map_key E: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(IMC_PATH)
    return ia


def ensure_manager_functions():
    """Add TillCell(GX,GY)->Bool and GetPlotState on GridManager if missing; wire simple graphs."""
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    if not bp:
        unreal.log_error("no mgr")
        return

    # List existing functions
    existing = []
    try:
        for g in bp.function_graphs:
            existing.append(str(g.get_name()))
    except Exception as ex:
        unreal.log_warning("list funcs: " + str(ex))
    unreal.log("mgr funcs: " + str(existing))

    # Prefer graph editing helper if available
    ge_event = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    # We'll wire TillCell via Character accessing PlotStates if functions hard;
    # First try create function graphs with BlueprintEditorLibrary
    for fname in ("GetPlotState", "TillCell"):
        if any(fname.lower() in e.lower() for e in existing):
            unreal.log(fname + " already exists")
            continue
        try:
            if hasattr(bel, "add_function_graph"):
                bel.add_function_graph(bp, fname)
                unreal.log("add_function_graph " + fname)
            elif hasattr(ge_event, "add_function_graph"):
                ge_event.add_function_graph(fname)
                unreal.log("ge add_function_graph " + fname)
            else:
                unreal.log_warning("no add_function_graph API for " + fname)
        except Exception as ex:
            unreal.log_warning("create func {}: {}".format(fname, ex))

    try:
        bel.compile_blueprint(bp)
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)


def wire_character_hoe():
    """Wire IA_Interact or InputKey E: foot cell Empty -> Tilled; Print; Tick box color by state."""
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    if not bp:
        unreal.log_error("no char")
        return
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

    # Avoid duplicate: if Print already says Tilled nearby, skip
    for n in ge.list_all_nodes():
        title = bel.get_node_title(n)
        if "IA_Interact" in title or (hasattr(n, "get_name") and "IA_Interact" in n.get_name()):
            unreal.log("IA_Interact node already present: " + title)
            # still continue to ensure wiring

    # Prefer Input Key E (Pressed) — more reliable to create than Enhanced Input node via API
    key_node = None
    try:
        key_node = ge.create_node_from_name("Input|Keyboard Events|E", unreal.Vector2D(-1600, 400), [])
    except Exception as ex:
        unreal.log_warning("create E key: " + str(ex))
    if not key_node:
        try:
            key_node = ge.create_node_from_name("Input Key", unreal.Vector2D(-1600, 400), [])
        except Exception as ex:
            unreal.log_warning("create Input Key: " + str(ex))
    if key_node:
        bel.set_node_pos(key_node, pos(-1600, 400))
        dump_pins(key_node, "key")
        # try set key to E
        for p in bel.list_all_pins(key_node):
            pn = str(p.get_pin_name()).lower()
            if "key" in pn and "input" in str(p.get_pin_direction()).lower():
                try:
                    p.set_pin_value("E")
                    unreal.log("set key pin E")
                except Exception as ex:
                    unreal.log_warning(str(ex))

    # Get GridManagerRef
    get_ref = ge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1300, 450))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output") or bel.find_output_pin_by_index(get_ref, 0)

    # Get Actor Location
    get_loc = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    if not get_loc:
        get_loc = ge.create_node_from_name("Get Actor Location", unreal.Vector2D(-1300, 550), [])
    bel.set_node_pos(get_loc, pos(-1300, 550))

    # WorldToGrid on GridManager (CallFunction on custom BP)
    # Use create_node_from_name for World To Grid with target
    w2g = None
    try:
        # Call function by path on BP_GridManager
        w2g = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    except Exception as ex:
        unreal.log_warning("w2g path: " + str(ex))
    if not w2g:
        w2g = ge.create_node_from_name("World To Grid", unreal.Vector2D(-1000, 450), [])
    if w2g:
        bel.set_node_pos(w2g, pos(-1000, 450))
        dump_pins(w2g, "w2g")
        # Target = GridManagerRef
        tgt = find_pin(w2g, "self", "Input") or find_pin(w2g, "Target", "Input")
        connect(ref_out, tgt, "ref->w2g")
        loc_out = find_pin(get_loc, "ReturnValue", "Output") or bel.find_output_pin_by_index(get_loc, 0)
        wl = find_pin(w2g, "World", "Input") or find_pin(w2g, "Location", "Input")
        connect(loc_out, wl, "loc->w2g")

    # IsValidCell
    valid = None
    try:
        valid = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:IsValidCell")
    except Exception:
        pass
    if not valid:
        valid = ge.create_node_from_name("Is Valid Cell", unreal.Vector2D(-700, 450), [])
    if valid:
        bel.set_node_pos(valid, pos(-700, 450))
        dump_pins(valid, "valid")
        connect(ref_out, find_pin(valid, "self", "Input") or find_pin(valid, "Target", "Input"), "ref->valid")
        if w2g:
            connect(find_pin(w2g, "Grid X", "Output") or find_pin(w2g, "X", "Output"),
                    find_pin(valid, "Grid X", "Input") or find_pin(valid, "X", "Input"), "gx")
            connect(find_pin(w2g, "Grid Y", "Output") or find_pin(w2g, "Y", "Output"),
                    find_pin(valid, "Grid Y", "Input") or find_pin(valid, "Y", "Input"), "gy")

    # Branch on IsValid
    branch = ge.create_node_from_name("Flow Control|Branch", unreal.Vector2D(-400, 400), [])
    if not branch:
        branch = ge.create_node_from_name("Branch", unreal.Vector2D(-400, 400), [])
    bel.set_node_pos(branch, pos(-400, 400))
    dump_pins(branch, "branch")

    # Exec from key Pressed
    pressed = find_pin(key_node, "Pressed", "Output") if key_node else None
    if not pressed and key_node:
        pressed = bel.find_then_pin(key_node) or find_pin(key_node, "then", "Output")
    connect(pressed, bel.find_execute_pin(branch) or find_pin(branch, "execute", "Input"), "key->branch")
    if valid:
        connect(find_pin(valid, "Return", "Output") or bel.find_output_pin_by_index(valid, 0),
                find_pin(branch, "Condition", "Input"), "valid->cond")

    # On True: Get PlotStates, compute index = GY*Width+GX, Get, Equal Empty, Branch2, Set Array Elem Tilled
    get_plots = None
    # Get member on other object: use Get PlotStates with Target pin via create
    get_plots = ge.create_node_from_name("Get PlotStates", unreal.Vector2D(-100, 350), [])
    if not get_plots:
        # Fallback: call a custom approach - VariableGet with pure
        try:
            get_plots = ge.add_get_member_variable_node("PlotStates")
        except Exception as ex:
            unreal.log_warning("get PlotStates: " + str(ex))
    if get_plots:
        bel.set_node_pos(get_plots, pos(-100, 300))
        dump_pins(get_plots, "plots")
        # If it has Target/self, connect ref
        connect(ref_out, find_pin(get_plots, "self", "Input") or find_pin(get_plots, "Target", "Input"), "ref->plots")

    # Get GridWidth from manager
    get_w = ge.create_node_from_name("Get GridWidth", unreal.Vector2D(-100, 450), [])
    if get_w:
        bel.set_node_pos(get_w, pos(-100, 500))
        connect(ref_out, find_pin(get_w, "self", "Input") or find_pin(get_w, "Target", "Input"), "ref->w")

    # Multiply GY * Width
    mul = ge.create_node_from_name("Utilities|Operators|Multiply", unreal.Vector2D(150, 450), [])
    bel.set_node_pos(mul, pos(150, 450))
    add = ge.create_node_from_name("Utilities|Operators|Add", unreal.Vector2D(300, 450), [])
    bel.set_node_pos(add, pos(300, 450))
    if w2g and get_w and mul and add:
        connect(find_pin(w2g, "Grid Y", "Output") or find_pin(w2g, "Y", "Output"),
                find_pin(mul, "A", "Input") or bel.find_input_pin_by_index(mul, 0), "gy*w")
        connect(find_pin(get_w, "GridWidth", "Output") or bel.find_output_pin_by_index(get_w, 0),
                find_pin(mul, "B", "Input") or bel.find_input_pin_by_index(mul, 1), "w")
        connect(bel.find_output_pin_by_index(mul, 0), find_pin(add, "A", "Input") or bel.find_input_pin_by_index(add, 0), "mul+")
        connect(find_pin(w2g, "Grid X", "Output") or find_pin(w2g, "X", "Output"),
                find_pin(add, "B", "Input") or bel.find_input_pin_by_index(add, 1), "+gx")

    # Get (array)
    get_at = ge.create_node_from_name("Utilities|Array|Get", unreal.Vector2D(500, 350), [])
    if not get_at:
        get_at = ge.create_node_from_name("Get", unreal.Vector2D(500, 350), [])
    if get_at:
        bel.set_node_pos(get_at, pos(500, 350))
        dump_pins(get_at, "get_at")
        if get_plots:
            connect(find_pin(get_plots, "PlotStates", "Output") or bel.find_output_pin_by_index(get_plots, 0),
                    find_pin(get_at, "TargetArray", "Input") or find_pin(get_at, "Array", "Input") or bel.find_input_pin_by_index(get_at, 0),
                    "arr")
        if add:
            connect(bel.find_output_pin_by_index(add, 0),
                    find_pin(get_at, "Index", "Input") or bel.find_input_pin_by_index(get_at, 1), "idx")

    # Equal enum Empty
    eq = ge.create_node_from_name("Utilities|Enum|Equal", unreal.Vector2D(700, 350), [])
    if not eq:
        eq = ge.create_node_from_name("Equal (Enum)", unreal.Vector2D(700, 350), [])
    if not eq:
        eq = ge.create_node_from_name("Utilities|Operators|Equal", unreal.Vector2D(700, 350), [])
    if eq:
        bel.set_node_pos(eq, pos(700, 350))
        dump_pins(eq, "eq")
        if get_at:
            connect(bel.find_output_pin_by_index(get_at, 0) or find_pin(get_at, "Item", "Output"),
                    find_pin(eq, "A", "Input") or bel.find_input_pin_by_index(eq, 0), "eqA")
        # Set B to Empty
        bpin = find_pin(eq, "B", "Input") or bel.find_input_pin_by_index(eq, 1)
        if bpin:
            for v in ("Empty", "NewEnumerator0", "E_PlotState::Empty", "0"):
                try:
                    bpin.set_pin_value(v)
                    unreal.log("eq B set " + v)
                    break
                except Exception as ex:
                    unreal.log_warning("eq B " + v + ": " + str(ex))

    branch2 = ge.create_node_from_name("Flow Control|Branch", unreal.Vector2D(900, 400), [])
    if not branch2:
        branch2 = ge.create_node_from_name("Branch", unreal.Vector2D(900, 400), [])
    bel.set_node_pos(branch2, pos(900, 400))
    connect(find_pin(branch, "True", "Output") or find_pin(branch, "then", "Output"),
            bel.find_execute_pin(branch2) or find_pin(branch2, "execute", "Input"), "b1->b2")
    if eq:
        connect(bel.find_output_pin_by_index(eq, 0) or find_pin(eq, "Return", "Output"),
                find_pin(branch2, "Condition", "Input"), "eq->b2")

    # Set Array Elem — need array by ref from GridManager. Use Set PlotStates via Set members or SetArrayElem
    set_elem = ge.create_node_from_name("Utilities|Array|Set Array Elem", unreal.Vector2D(1200, 350), [])
    if not set_elem:
        set_elem = ge.create_node_from_name("Set Array Elem", unreal.Vector2D(1200, 350), [])
    if set_elem:
        bel.set_node_pos(set_elem, pos(1200, 350))
        dump_pins(set_elem, "set_elem")
        connect(find_pin(branch2, "True", "Output"),
                bel.find_execute_pin(set_elem) or find_pin(set_elem, "execute", "Input"), "b2->set")
        # Target Array: need Get PlotStates again as ref — connect plots out
        if get_plots:
            connect(find_pin(get_plots, "PlotStates", "Output") or bel.find_output_pin_by_index(get_plots, 0),
                    find_pin(set_elem, "TargetArray", "Input") or find_pin(set_elem, "Array", "Input"),
                    "arr set")
        if add:
            connect(bel.find_output_pin_by_index(add, 0),
                    find_pin(set_elem, "Index", "Input"), "idx set")
        item = find_pin(set_elem, "Item", "Input") or find_pin(set_elem, "Value", "Input")
        if item:
            for v in ("Tilled", "NewEnumerator1", "E_PlotState::Tilled", "1"):
                try:
                    item.set_pin_value(v)
                    unreal.log("set item " + v)
                    break
                except Exception as ex:
                    unreal.log_warning("item " + v + ": " + str(ex))

    # Print success
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    if not pr:
        pr = ge.create_node_from_name("Print String", unreal.Vector2D(1500, 350), [])
    if pr:
        bel.set_node_pos(pr, pos(1500, 350))
        if set_elem:
            connect(bel.find_then_pin(set_elem) or find_pin(set_elem, "then", "Output"),
                    bel.find_execute_pin(pr) or find_pin(pr, "execute", "Input"), "set->print")
        insp = find_pin(pr, "InString", "Input") or find_pin(pr, "String", "Input")
        if insp:
            try:
                insp.set_pin_value("Tilled!")
            except Exception:
                pass

    try:
        bel.compile_blueprint(bp)
        unreal.log("Character compile ok")
    except Exception as ex:
        unreal.log_warning("char compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def main():
    unreal.log("=== phase2_hoe start ===")
    ensure_ia_interact()
    ensure_manager_functions()
    wire_character_hoe()
    unreal.log("=== phase2_hoe done ===")


if __name__ == "__main__":
    main()