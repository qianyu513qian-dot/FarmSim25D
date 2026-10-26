# -*- coding: utf-8 -*-
"""SAFE harvest: HarvestCell Ready(4)->Empty(0) + white box; IA_Harvest H; ADD character wire only."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
IA_HARVEST = "/Game/TopDown/Input/Actions/IA_Harvest"
IA_PLANT = "/Game/TopDown/Input/Actions/IA_Plant"


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    unreal.log("conn[{}] : {}".format(label, ok))
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
        return
    try:
        pin.set_pin_value(str(value))
        unreal.log("set {}={!r}".format(label, value))
    except Exception as ex:
        unreal.log_warning(label + ": " + str(ex))


def make_int_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="int")')
    return p


def make_bool_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="bool")')
    return p


def build_harvest_cell():
    bp = unreal.load_asset(MGR)
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    if "HarvestCell" in graphs:
        unreal.log("HarvestCell exists — skip rebuild")
        return True

    bel.add_function_graph(bp, "HarvestCell")
    graph = bel.find_graph(bp, "HarvestCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    if not ge:
        unreal.log_error("no GE")
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
    has_succ = any(
        n.get_class().get_name() == "K2Node_FunctionResult" and find_pin(n, "Success")
        for n in ge.list_all_nodes()
    )
    if not has_succ:
        try:
            ge.add_graph_output_parameter("Success", make_bool_pin())
        except Exception as ex:
            unreal.log_warning(str(ex))
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

    valid = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:IsValidCell")
    bel.set_node_pos(valid, pos(250, 0))
    connect(find_pin(entry, "GridX", "Output"), find_pin(valid, "Grid X", "Input") or find_pin(valid, "GridX", "Input"), "gx-v")
    connect(find_pin(entry, "GridY", "Output"), find_pin(valid, "Grid Y", "Input") or find_pin(valid, "GridY", "Input"), "gy-v")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(500, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
    connect(find_pin(valid, "Return Value", "Output") or find_pin(valid, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "valid")

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
    set_val(find_pin(eq, "B", "Input"), "4", "eq.B=Ready")

    br2 = ge.add_branch_node()
    bel.set_node_pos(br2, pos(1550, 0))
    connect(find_pin(br, "then", "Output"), find_pin(br2, "execute", "Input"), "br->br2")
    connect(find_pin(eq, "ReturnValue", "Output"), find_pin(br2, "Condition", "Input"), "eq->br2")

    set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
    bel.set_node_pos(set_at, pos(1800, 0))
    connect(find_pin(br2, "then", "Output"), find_pin(set_at, "execute", "Input"), "br2->set")
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(set_at, "TargetArray", "Input"), "setarr")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(set_at, "Index", "Input"), "setidx")
    set_val(find_pin(set_at, "Item", "Input"), "0", "set.Item=Empty")
    set_val(find_pin(set_at, "bSizeToFit", "Input"), "true", "fit")

    g2w = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GridToWorld")
    bel.set_node_pos(g2w, pos(2050, 0))
    connect(find_pin(entry, "GridX", "Output"), find_pin(g2w, "Grid X", "Input") or find_pin(g2w, "GridX", "Input"), "gx-g2w")
    connect(find_pin(entry, "GridY", "Output"), find_pin(g2w, "Grid Y", "Input") or find_pin(g2w, "GridY", "Input"), "gy-g2w")

    dbg = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugBox")
    bel.set_node_pos(dbg, pos(2350, 0))
    if find_pin(g2w, "execute", "Input"):
        connect(find_pin(set_at, "then", "Output"), find_pin(g2w, "execute", "Input"), "set->g2w")
        connect(find_pin(g2w, "then", "Output"), find_pin(dbg, "execute", "Input"), "g2w->dbg")
    else:
        connect(find_pin(set_at, "then", "Output"), find_pin(dbg, "execute", "Input"), "set->dbg")
    connect(
        find_pin(g2w, "World Location", "Output") or find_pin(g2w, "ReturnValue", "Output"),
        find_pin(dbg, "Center", "Input"),
        "center",
    )
    make_v = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(make_v, pos(2150, 250))
    set_val(find_pin(make_v, "X", "Input"), "25.0", "X")
    set_val(find_pin(make_v, "Y", "Input"), "25.0", "Y")
    set_val(find_pin(make_v, "Z", "Input"), "4.0", "Z")
    connect(find_pin(make_v, "ReturnValue", "Output"), find_pin(dbg, "Extent", "Input"), "extent")
    set_val(find_pin(dbg, "LineColor", "Input"), "(R=1.0,G=1.0,B=1.0,A=1.0)", "white")
    set_val(find_pin(dbg, "Duration", "Input"), "2.0", "dur")
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

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("HarvestCell ok funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    return True


def ensure_ia_and_map():
    if not unreal.EditorAssetLibrary.does_asset_exist(IA_HARVEST):
        unreal.EditorAssetLibrary.duplicate_asset(IA_PLANT, IA_HARVEST)
    ia = unreal.load_asset(IA_HARVEST)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(IA_HARVEST)
    imc = unreal.load_asset(IMC)
    k = unreal.Key()
    k.import_text("H")
    try:
        imc.unmap_all_keys_from_action(ia)
    except Exception:
        pass
    imc.map_key(ia, k)
    unreal.EditorAssetLibrary.save_asset(IMC)
    txt = imc.get_editor_property("default_key_mappings").export_text()
    unreal.log("H=" + str("Key=H" in txt) + " Harvest=" + str("IA_Harvest" in txt) + " E=" + str("Key=E" in txt))


def wire_character_add_only():
    cbp = unreal.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
    for n in cge.list_all_nodes():
        try:
            t = bel.get_node_title(n)
        except Exception:
            t = str(n)
        if "IA_Harvest" in t:
            unreal.log("IA_Harvest already present — skip")
            return

    y = 2500
    ia = cge.create_node_from_name("Input|EnhancedActionEvents|IA_Harvest", unreal.Vector2D(-1800, y), [])
    if not ia:
        unreal.log_error("no IA_Harvest event")
        return
    bel.set_node_pos(ia, pos(-1800, y))

    get_ref = cge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1600, y + 80))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output")
    get_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1600, y + 220))
    w2g = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    bel.set_node_pos(w2g, pos(-1300, y + 80))
    connect(ref_out, find_pin(w2g, "self", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output"), find_pin(w2g, "WorldLocation", "Input") or find_pin(w2g, "World Location", "Input"), "loc")

    harvest = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:HarvestCell")
    bel.set_node_pos(harvest, pos(-950, y + 80))
    if harvest and len(bel.list_all_pins(harvest)) == 0:
        bel.compile_blueprint(cbp)
        cge.remove_nodes([harvest])
        harvest = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:HarvestCell")
        bel.set_node_pos(harvest, pos(-950, y + 80))
    connect(ref_out, find_pin(harvest, "self", "Input"), "ref-h")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(harvest, "GridX", "Input") or find_pin(harvest, "Grid X", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(harvest, "GridY", "Input") or find_pin(harvest, "Grid Y", "Input"), "gy")

    start = find_pin(ia, "Started", "Output") or find_pin(ia, "Triggered", "Output")
    if find_pin(w2g, "execute", "Input"):
        connect(start, find_pin(w2g, "execute", "Input"), "ia->w2g")
        connect(find_pin(w2g, "then", "Output"), find_pin(harvest, "execute", "Input"), "w2g->h")
    else:
        connect(start, find_pin(harvest, "execute", "Input"), "ia->h")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-650, y + 80))
    connect(find_pin(harvest, "then", "Output"), find_pin(br, "execute", "Input"), "h->br")
    connect(find_pin(harvest, "Success", "Output"), find_pin(br, "Condition", "Input"), "succ")

    pr_ok = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-350, y + 20))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    try:
        find_pin(pr_ok, "InString", "Input").set_default_value("Harvested!")
    except Exception:
        set_val(find_pin(pr_ok, "InString", "Input"), "Harvested!", "ok")

    pr_no = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-350, y + 180))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
    try:
        find_pin(pr_no, "InString", "Input").set_default_value("Cannot harvest")
    except Exception:
        set_val(find_pin(pr_no, "InString", "Input"), "Cannot harvest", "no")

    bel.compile_blueprint(cbp)
    unreal.EditorAssetLibrary.save_asset(CHAR)
    unreal.log("char harvest wire ok")


def main():
    unreal.log("=== phase6_harvest start ===")
    build_harvest_cell()
    ensure_ia_and_map()
    wire_character_add_only()
    unreal.log("=== phase6_harvest done ===")


if __name__ == "__main__":
    main()
