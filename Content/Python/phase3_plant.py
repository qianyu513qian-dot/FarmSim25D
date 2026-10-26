# -*- coding: utf-8 -*-
"""Phase3 planting: PlantCell + IA_Plant(F) + character wire. No open_editor, no rename."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
IA_PLANT = "/Game/TopDown/Input/Actions/IA_Plant"
ACTIONS_DIR = "/Game/TopDown/Input/Actions"

# Enum indices (numeric pins; names may be absent on UserDefinedEnum)
# 0=Empty, 1=Tilled, 2=Planted


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
        unreal.log_warning("dump none " + label)
        return
    for p in bel.list_all_pins(node):
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def ensure_ia_plant():
    if unreal.EditorAssetLibrary.does_asset_exist(IA_PLANT):
        ia = unreal.EditorAssetLibrary.load_asset(IA_PLANT)
        unreal.log("IA_Plant exists")
    else:
        factory = unreal.InputActionFactory()
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        ia = tools.create_asset("IA_Plant", ACTIONS_DIR, unreal.InputAction, factory)
        unreal.log("created IA_Plant " + str(ia))
    # Boolean / Digital press (same as Interact)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
        unreal.log("IA_Plant value_type BOOLEAN")
    except Exception as ex:
        unreal.log_warning("value_type: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(IA_PLANT)
    return ia


def map_f_key(ia):
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    try:
        imc.unmap_all_keys_from_action(ia)
        unreal.log("unmapped old IA_Plant keys")
    except Exception as ex:
        unreal.log_warning("unmap: " + str(ex))
    mapped = False
    for key_try in (
        lambda: unreal.Key.F,
        lambda: unreal.Key("F"),
    ):
        try:
            k = key_try()
            m = imc.map_key(ia, k)
            unreal.log("map_key F -> " + str(m))
            mapped = True
            break
        except Exception as ex:
            unreal.log_warning("map try: " + str(ex))
    if not mapped:
        try:
            k = unreal.Key()
            k.set_editor_property("key_name", "F")
            m = imc.map_key(ia, k)
            unreal.log("map_key Key(name F) -> " + str(m))
        except Exception as ex:
            unreal.log_warning("map name F: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(IMC)


def build_plant_cell():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    unreal.log("graphs before=" + str(graphs))

    if "PlantCell" in graphs:
        # Conservative: remove and rebuild once (not rename)
        try:
            bel.remove_function_graph(bp, "PlantCell")
            unreal.log("removed existing PlantCell")
        except Exception as ex:
            unreal.log_warning("remove PlantCell: " + str(ex))

    bel.add_function_graph(bp, "PlantCell")
    graph = bel.find_graph(bp, "PlantCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    if not ge:
        unreal.log_error("no PlantCell graph editor")
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
        if n.get_class().get_name() == "K2Node_FunctionResult":
            if find_pin(n, "Success"):
                has_succ = True
    if not has_succ:
        try:
            ge.add_graph_output_parameter("Success", make_bool_pin())
        except Exception as ex:
            unreal.log_warning("out Success: " + str(ex))

    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
    dump(entry, "entry")

    valid = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:IsValidCell")
    bel.set_node_pos(valid, pos(250, 0))
    connect(find_pin(entry, "GridX", "Output"), find_pin(valid, "Grid X", "Input") or find_pin(valid, "GridX", "Input"), "gx-valid")
    connect(find_pin(entry, "GridY", "Output"), find_pin(valid, "Grid Y", "Input") or find_pin(valid, "GridY", "Input"), "gy-valid")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(500, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "entry->br")
    connect(
        find_pin(valid, "Return Value", "Output") or find_pin(valid, "ReturnValue", "Output"),
        find_pin(br, "Condition", "Input"),
        "valid->br",
    )

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
    set_val(find_pin(eq, "B", "Input"), "1", "eq.B=Tilled")  # must be Tilled

    br2 = ge.add_branch_node()
    bel.set_node_pos(br2, pos(1550, 0))
    connect(find_pin(br, "then", "Output"), find_pin(br2, "execute", "Input"), "br->br2")
    connect(find_pin(eq, "ReturnValue", "Output"), find_pin(br2, "Condition", "Input"), "eq->br2")

    set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
    bel.set_node_pos(set_at, pos(1800, 0))
    connect(find_pin(br2, "then", "Output"), find_pin(set_at, "execute", "Input"), "br2->set")
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(set_at, "TargetArray", "Input"), "setarr")
    connect(find_pin(addn, "ReturnValue", "Output"), find_pin(set_at, "Index", "Input"), "setidx")
    set_val(find_pin(set_at, "Item", "Input"), "2", "set.Item=Planted")
    set_val(find_pin(set_at, "bSizeToFit", "Input"), "true", "sizefit")

    # Visual: GridToWorld -> DrawDebugBox green
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
    set_val(find_pin(make_v, "X", "Input"), "40.0", "ext.X")
    set_val(find_pin(make_v, "Y", "Input"), "40.0", "ext.Y")
    set_val(find_pin(make_v, "Z", "Input"), "4.0", "ext.Z")
    connect(find_pin(make_v, "ReturnValue", "Output"), find_pin(dbg, "Extent", "Input"), "extent")

    # Lime/green
    set_val(find_pin(dbg, "LineColor", "Input"), "(R=0.20,G=0.85,B=0.25,A=1.0)", "color")
    set_val(find_pin(dbg, "Duration", "Input"), "99999.0", "dur")
    set_val(find_pin(dbg, "Thickness", "Input"), "3.0", "thick")

    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(2650, 0))
    connect(find_pin(dbg, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "dbg->ret")
    set_val(find_pin(ret_ok, "Success", "Input"), "true", "ret.ok")

    ret_f1 = ge.add_return_node()
    bel.set_node_pos(ret_f1, pos(1800, 200))
    connect(find_pin(br, "else", "Output"), find_pin(ret_f1, "execute", "Input"), "br else")
    ret_f2 = ge.add_return_node()
    bel.set_node_pos(ret_f2, pos(1800, 350))
    connect(find_pin(br2, "else", "Output"), find_pin(ret_f2, "execute", "Input"), "br2 else")
    for rn in (ret_f1, ret_f2):
        set_val(find_pin(rn, "Success", "Input"), "false", "ret.fail")

    try:
        bel.compile_blueprint(bp)
        unreal.log("PlantCell compile ok")
    except Exception as ex:
        unreal.log_warning("PlantCell compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    return True


def wire_character():
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    # Remove prior Plant chain only (do not touch IA_Interact / Till)
    remove = []
    ia_plant_node = None
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "IA_Plant" in t:
            ia_plant_node = n
            start = find_pin(n, "Started", "Output") or find_pin(n, "Triggered", "Output")
            if start:
                frontier = [cp.get_owning_node() for cp in list(start.list_connected_pins())]
                seen = set()
                while frontier:
                    nn = frontier.pop(0)
                    if id(nn) in seen:
                        continue
                    seen.add(id(nn))
                    remove.append(nn)
                    for p in bel.list_all_pins(nn):
                        if "OUTPUT" in str(p.get_pin_direction()):
                            for cp in list(p.list_connected_pins()):
                                frontier.append(cp.get_owning_node())
        if t == "PlantCell" or t.startswith("Plant Cell"):
            remove.append(n)
        if t == "Print String":
            insp = find_pin(n, "InString", "Input")
            val = ""
            if insp:
                try:
                    val = insp.get_default_as_string()
                except Exception:
                    try:
                        val = insp.get_pin_value()
                    except Exception:
                        val = ""
            if val in ("Planted!", "Cannot plant"):
                remove.append(n)

    remove = list({id(n): n for n in remove}.values())
    # Never remove IA_Interact / TillCell / Tick helpers
    safe = []
    for n in remove:
        t = bel.get_node_title(n)
        if "IA_Interact" in t or t == "TillCell" or t in ("ReceiveTick", "ReceiveBeginPlay", "Event Tick", "Event BeginPlay"):
            continue
        if val_in_till_chain(n):
            continue
        safe.append(n)
    if safe:
        cge.remove_nodes(safe)
        unreal.log("removed plant leftovers " + str(len(safe)))

    # Create IA_Plant event node
    if not ia_plant_node:
        for n in cge.list_all_nodes():
            if "IA_Plant" in bel.get_node_title(n):
                ia_plant_node = n
                break
    if not ia_plant_node:
        ia_plant_node = cge.create_node_from_name(
            "Input|EnhancedActionEvents|IA_Plant", unreal.Vector2D(-1800, 1200), []
        )
        if ia_plant_node:
            bel.set_node_pos(ia_plant_node, pos(-1800, 1200))
            unreal.log("created IA_Plant event node")
        else:
            unreal.log_warning("IA_Plant event create failed - fallback Keyboard F")
            ia_plant_node = cge.create_node_from_name(
                "Input|KeyboardEvents|F", unreal.Vector2D(-1800, 1200), []
            )
            if ia_plant_node:
                bel.set_node_pos(ia_plant_node, pos(-1800, 1200))

    dump(ia_plant_node, "ia_plant")

    get_ref = cge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1600, 1280))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output")

    get_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1600, 1420))

    w2g = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    bel.set_node_pos(w2g, pos(-1300, 1280))
    connect(ref_out, find_pin(w2g, "self", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output"), find_pin(w2g, "WorldLocation", "Input"), "loc")

    plant = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:PlantCell")
    bel.set_node_pos(plant, pos(-950, 1280))
    dump(plant, "plant")
    if plant and len(bel.list_all_pins(plant)) == 0:
        try:
            bel.compile_blueprint(cbp)
        except Exception:
            pass
        cge.remove_nodes([plant])
        plant = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:PlantCell")
        bel.set_node_pos(plant, pos(-950, 1280))
        dump(plant, "plant2")

    connect(ref_out, find_pin(plant, "self", "Input"), "ref-plant")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(plant, "GridX", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(plant, "GridY", "Input"), "gy")

    start = (
        find_pin(ia_plant_node, "Started", "Output")
        or find_pin(ia_plant_node, "Pressed", "Output")
        or find_pin(ia_plant_node, "Triggered", "Output")
    )
    # Prefer: Started -> WorldToGrid (if impure) -> PlantCell
    w2g_exec = find_pin(w2g, "execute", "Input")
    if w2g_exec:
        connect(start, w2g_exec, "ia->w2g")
        connect(find_pin(w2g, "then", "Output"), find_pin(plant, "execute", "Input"), "w2g->plant")
    else:
        connect(start, find_pin(plant, "execute", "Input"), "ia->plant")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-650, 1280))
    connect(find_pin(plant, "then", "Output"), find_pin(br, "execute", "Input"), "plant->br")
    connect(find_pin(plant, "Success", "Output"), find_pin(br, "Condition", "Input"), "succ")

    pr_ok = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-350, 1220))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    try:
        find_pin(pr_ok, "InString", "Input").set_default_value("Planted!")
    except Exception:
        set_val(find_pin(pr_ok, "InString", "Input"), "Planted!", "print.ok")

    pr_no = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-350, 1380))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
    try:
        find_pin(pr_no, "InString", "Input").set_default_value("Cannot plant")
    except Exception:
        set_val(find_pin(pr_no, "InString", "Input"), "Cannot plant", "print.no")

    try:
        bel.compile_blueprint(cbp)
        unreal.log("char compile ok")
    except Exception as ex:
        unreal.log_warning("char compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def val_in_till_chain(n):
    """Heuristic: skip nodes that look like till prints."""
    t = bel.get_node_title(n)
    if t == "Print String":
        insp = find_pin(n, "InString", "Input")
        val = ""
        if insp:
            try:
                val = insp.get_default_as_string()
            except Exception:
                try:
                    val = str(insp.get_pin_value())
                except Exception:
                    val = ""
        if val in ("Tilled!", "Cannot till"):
            return True
    return False


def main():
    unreal.log("=== phase3_plant start ===")
    ia = ensure_ia_plant()
    map_f_key(ia)
    ok = build_plant_cell()
    if not ok:
        unreal.log_error("PlantCell build failed")
        return
    wire_character()
    # Final compile both
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    try:
        bel.compile_blueprint(bp)
        bel.compile_blueprint(cbp)
        unreal.log("final compile ok")
    except Exception as ex:
        unreal.log_warning("final compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.EditorAssetLibrary.save_asset(CHAR)
    unreal.EditorAssetLibrary.save_asset(IMC)
    unreal.EditorAssetLibrary.save_asset(IA_PLANT)
    unreal.log("=== phase3_plant done ===")


if __name__ == "__main__":
    main()
