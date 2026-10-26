# -*- coding: utf-8 -*-
"""Fix blocked till: enum Blocked, CDO BlockedIndices, BeginPlay InitBlockedFromIndices via ForLoop."""
import unreal

TAG = "[BLOCK_FIX2]"
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
ENUM_PATH = "/Game/Farm/Grid/E_PlotState"
CELL = 100.0
WIDTH = 40
HEIGHT = 40
STATE_BLOCKED = 5


def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def parse_cell(lab):
    parts = (lab or "").split("_")
    try:
        return int(parts[-2]), int(parts[-1])
    except Exception:
        return None


def water_edge_x(cy):
    base = 5
    wobble = (cy * 7 + 3) % 5
    return {0: base - 1, 1: base, 2: base + 1, 3: base}.get(wobble, base + 2)


def collect_blocked():
    path, bridge, cliff, yard = set(), set(), set(), set()
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        c = parse_cell(lab)
        if not c:
            continue
        if lab.startswith("VMF_Path"):
            path.add(c)
        elif lab.startswith("VMF_Bridge"):
            bridge.add(c)
        elif lab.startswith("VMF_Cliff_"):
            cliff.add(c)
        elif lab.startswith("VMF_Yard_"):
            yard.add(c)
    water = {(cx, cy) for cy in range(HEIGHT) for cx in range(WIDTH) if cx <= water_edge_x(cy)}
    blocked = path | bridge | water | cliff | yard
    log("blocked path={} bridge={} water={} cliff={} yard={} total={}".format(
        len(path), len(bridge), len(water), len(cliff), len(yard), len(blocked)))
    return blocked


def ensure_enum_blocked():
    ude = unreal.EditorAssetLibrary.load_asset(ENUM_PATH)
    log("enum libs: UDE={} EnumEd={}".format(
        hasattr(unreal, "UserDefinedEnumLibrary"), hasattr(unreal, "EnumEditorLibrary")))
    # Dump ALL unreal attrs with Enum in name
    enum_attrs = [a for a in dir(unreal) if "num" in a.lower()]
    log("unreal *num* attrs: " + str(enum_attrs[:40]))

    # Try EditorAssetLibrary / AssetTools to re-create with 6 names — DANGEROUS for refs.
    # Safer: use unreal.EnumEditorLibrary if present after loading plugin module
    for mod in ("unreal",):
        pass

    # Direct UEnum Names via set_editor_property on DisplayNameMap if map-like
    # Try call_method with various signatures
    for meth, args in (
        ("AddUserDefinedEnumEntry", ()),
        ("AddEnumerator", ()),
        ("InsertEnumerator", (5,)),
    ):
        try:
            r = ude.call_method(meth, args)
            log("call_method {} -> {}".format(meth, r))
        except Exception as ex:
            log("call_method {} : {}".format(meth, ex))

    # Use KismetSystemLibrary / BlueprintEditorLibrary helpers
    for name in dir(bel):
        if "enum" in name.lower():
            log("bel." + name)

    # Recreate approach used in phase3: set_display_names with 6 entries forces resize on some UE
    names = ["Empty", "Tilled", "Planted", "Watered", "Ready", "Blocked"]
    if hasattr(unreal, "UserDefinedEnumLibrary"):
        try:
            arr = unreal.Array(unreal.Text)
            for n in names:
                arr.append(unreal.Text(n))
            unreal.UserDefinedEnumLibrary.set_display_names(ude, arr)
            log("UDE set_display_names 6")
        except Exception as ex:
            log("UDE set_display_names: " + str(ex))

    if hasattr(unreal, "EnumEditorLibrary"):
        lib = unreal.EnumEditorLibrary
        log("EnumEditorLibrary methods: " + str([x for x in dir(lib) if not x.startswith("_")]))
        # ensure 6 entries
        for i in range(6):
            if i > 0:
                for addm in ("add_enumerator", "add_user_defined_enum_entry", "insert_enumerator"):
                    if hasattr(lib, addm):
                        try:
                            if "insert" in addm:
                                getattr(lib, addm)(ude, i)
                            else:
                                getattr(lib, addm)(ude)
                            log("added via " + addm)
                        except Exception as ex:
                            log("{}: {}".format(addm, ex))
            for setm in ("set_enumerator_user_facing_name", "set_enumerator_display_name",
                         "set_enumerator_display_name_string", "set_enumerator_name"):
                if hasattr(lib, setm):
                    try:
                        if "string" in setm or setm.endswith("_name") and "facing" not in setm and "display" not in setm:
                            try:
                                getattr(lib, setm)(ude, i, names[i])
                            except Exception:
                                getattr(lib, setm)(ude, i, unreal.Text(names[i]))
                        else:
                            getattr(lib, setm)(ude, i, unreal.Text(names[i]))
                        log("named {} idx {} via {}".format(names[i], i, setm))
                        break
                    except Exception as ex:
                        log("{} idx{}: {}".format(setm, i, ex))

    # Fallback: delete+recreate enum (PlotStates refs use path; numeric indices stay valid)
    import os
    p = r"E:\UE\FarmSim25D\Content\Farm\Grid\E_PlotState.uasset"
    data = open(p, "rb").read() if os.path.isfile(p) else b""
    if b"Blocked" not in data:
        log("Blocked still missing — recreate enum asset")
        try:
            # Don't delete — create sibling and... no, refs would break.
            # Instead write NewEnumerator5 display via rename in editor subsystem
            pass
        except Exception:
            pass
        # Try AssetImportData path: EnumFactory create temporary then copy
        try:
            factory = unreal.EnumFactory()
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            # Can't create same path. Add entries by duplicating?
            dup = unreal.EditorAssetLibrary.duplicate_asset("/Game/Farm/Grid/E_PlotState_TmpBlocked", ENUM_PATH)
            log("dup=" + str(dup))
        except Exception as ex:
            log("dup: " + str(ex))

    unreal.EditorAssetLibrary.save_asset(ENUM_PATH)
    data = open(p, "rb").read() if os.path.isfile(p) else b""
    log("final Blocked in uasset: {}".format(b"Blocked" in data))
    log("final NewEnumerator in uasset: {}".format(b"NewEnumerator" in data))
    # Count NewEnumeratorN
    for i in range(8):
        key = "NewEnumerator{}".format(i).encode()
        log("has {}: {}".format(key, key in data))


def make_var_editable():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    # Ensure BlockedIndices exists as int array
    names = [str(x) for x in bel.list_member_variable_names(bp)]
    if "BlockedIndices" not in names:
        pin = unreal.EdGraphPinType()
        try:
            pin.import_text('(PinCategory="int",ContainerType=Array)')
        except Exception as ex:
            log("import_text: " + str(ex))
            try:
                pin.pin_category = "int"
                pin.container_type = unreal.EdGraphPinContainerType.ARRAY
            except Exception as ex2:
                log("pin fields: " + str(ex2))
        bel.add_member_variable(bp, "BlockedIndices", pin)
        log("added BlockedIndices")
    # Try set instance editable / blueprint read write
    for api in (
        "set_blueprint_variable_instance_editable",
        "set_blueprint_variable_expose_on_spawn",
        "set_variable_instance_editable",
    ):
        if hasattr(bel, api):
            try:
                getattr(bel, api)(bp, "BlockedIndices", True)
                getattr(bel, api)(bp, "PlotStates", True)
                log(api + " ok")
            except Exception as ex:
                log(api + ": " + str(ex))
    # Variable flags via get_member_variable_guid?
    try:
        # BlueprintEditorLibrary.set_blueprint_variable_flags?
        for name in dir(bel):
            if "variable" in name.lower() and ("edit" in name.lower() or "flag" in name.lower() or "default" in name.lower()):
                log("bel var api: " + name)
    except Exception:
        pass
    try:
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(MGR)
    except Exception as ex:
        log("compile: " + str(ex))


def set_cdo_blocked_indices(blocked):
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    gc = bp.generated_class()
    cdo = unreal.get_default_object(gc)
    indices = sorted(cy * WIDTH + cx for cx, cy in blocked if 0 <= cx < WIDTH and 0 <= cy < HEIGHT)
    bi = unreal.Array(int)
    for i in indices:
        bi.append(int(i))
    try:
        cdo.set_editor_property("BlockedIndices", bi)
        log("CDO BlockedIndices set n={}".format(len(indices)))
    except Exception as ex:
        log("CDO set BlockedIndices: " + str(ex))
    # Also try set default via Bel
    for api in ("set_blueprint_variable_default_value", "set_variable_default_value"):
        if hasattr(bel, api):
            try:
                # format as (1,2,3)
                s = "(" + ",".join(str(i) for i in indices[:50]) + ")"  # may truncate
                getattr(bel, api)(bp, "BlockedIndices", s)
                log(api + " tried")
            except Exception as ex:
                log(api + ": " + str(ex))
    # Verify
    try:
        v = cdo.get_editor_property("BlockedIndices")
        log("CDO verify len={} head={}".format(len(v) if v else 0, list(v)[:8] if v else None))
    except Exception as ex:
        log("verify: " + str(ex))
    # Pre-size PlotStates on CDO with Empty, then stamp blocked
    try:
        # PlotStates is enum array — try int coerce
        ps = unreal.Array(int)
        n = WIDTH * HEIGHT
        for i in range(n):
            ps.append(STATE_BLOCKED if i in set(indices) else 0)
        cdo.set_editor_property("PlotStates", ps)
        log("CDO PlotStates set len={}".format(n))
    except Exception as ex:
        log("CDO PlotStates: " + str(ex))
        # Try empty then only BlockedIndices path
    try:
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(MGR)
    except Exception as ex:
        log("save: " + str(ex))
    return indices


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


def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def set_val(pin, value, label=""):
    if not pin:
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, pin.get_pin_value()))
    except Exception as ex:
        log("set {} : {}".format(label, ex))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def rebuild_init_fn(indices_count):
    """InitBlockedFromIndices: Clear PlotStates; ForLoop Add Empty; ForLoop over BlockedIndices Get+SetArrayElem Blocked."""
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    fname = "InitBlockedFromIndices"
    graph = bel.find_graph(bp, fname)
    if not graph:
        bel.add_function_graph(bp, fname)
        graph = bel.find_graph(bp, fname)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    entry = None
    to_del = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            to_del.append(n)
    if to_del:
        ge.remove_nodes(to_del)
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

    # --- Clear ---
    clear_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Clear")
    bel.set_node_pos(clear_n, pos(250, 0))
    get_ps1 = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_ps1, pos(50, 160))
    connect(find_pin(entry, "then", "Output"), find_pin(clear_n, "execute", "Input"), "e->clear")
    connect(find_pin(get_ps1, "PlotStates", "Output") or bel.find_output_pin_by_index(get_ps1, 0),
            find_pin(clear_n, "TargetArray", "Input") or find_pin(clear_n, "Array", "Input"), "ps clear")

    # --- ForLoop fill Empty ---
    forloop = None
    for path in ("Utilities|FlowControl|ForLoop", "Flow Control|For Loop"):
        try:
            forloop = ge.create_node_from_name(path, unreal.Vector2D(550, 0), [])
            if forloop:
                log("ForLoop ok " + path)
                break
        except Exception as ex:
            log("ForLoop " + str(ex))
    if not forloop:
        log("FATAL no ForLoop")
        return False
    bel.set_node_pos(forloop, pos(550, 0))
    connect(find_pin(clear_n, "then", "Output"), find_pin(forloop, "execute", "Input"), "clear->for")

    get_w = ge.add_get_member_variable_node("GridWidth")
    get_h = ge.add_get_member_variable_node("GridHeight")
    bel.set_node_pos(get_w, pos(300, 220))
    bel.set_node_pos(get_h, pos(300, 300))
    mul = ge.create_node_from_name("Utilities|Operators|integer * integer", unreal.Vector2D(450, 250), [])
    if not mul:
        mul = ge.create_node_from_name("Math|Integer|integer * integer", unreal.Vector2D(450, 250), [])
    bel.set_node_pos(mul, pos(450, 250))
    connect(find_pin(get_w, "GridWidth", "Output") or bel.find_output_pin_by_index(get_w, 0), find_pin(mul, "A", "Input"), "w")
    connect(find_pin(get_h, "GridHeight", "Output") or bel.find_output_pin_by_index(get_h, 0), find_pin(mul, "B", "Input"), "h")
    sub = ge.create_node_from_name("Utilities|Operators|integer - integer", unreal.Vector2D(580, 250), [])
    if not sub:
        sub = ge.create_node_from_name("Math|Integer|integer - integer", unreal.Vector2D(580, 250), [])
    bel.set_node_pos(sub, pos(580, 250))
    connect(bel.find_output_pin_by_index(mul, 0), find_pin(sub, "A", "Input"), "mul")
    set_val(find_pin(sub, "B", "Input"), "1", "sub1")
    connect(bel.find_output_pin_by_index(sub, 0), find_pin(forloop, "LastIndex", "Input") or find_pin(forloop, "Last", "Input"), "last")
    set_val(find_pin(forloop, "FirstIndex", "Input") or find_pin(forloop, "First", "Input"), "0", "first")

    add_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Add")
    bel.set_node_pos(add_n, pos(900, 60))
    get_ps2 = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_ps2, pos(700, 200))
    connect(find_pin(forloop, "LoopBody", "Output"), find_pin(add_n, "execute", "Input"), "body->add")
    connect(find_pin(get_ps2, "PlotStates", "Output") or bel.find_output_pin_by_index(get_ps2, 0),
            find_pin(add_n, "TargetArray", "Input") or find_pin(add_n, "Array", "Input"), "ps add")
    set_val(find_pin(add_n, "NewItem", "Input") or find_pin(add_n, "Item", "Input"), "0", "Empty")

    # --- ForLoop2 over BlockedIndices length ---
    for2 = ge.create_node_from_name("Utilities|FlowControl|ForLoop", unreal.Vector2D(1200, 0), [])
    if not for2:
        for2 = ge.create_node_from_name("Flow Control|For Loop", unreal.Vector2D(1200, 0), [])
    bel.set_node_pos(for2, pos(1200, 0))
    connect(find_pin(forloop, "Completed", "Output"), find_pin(for2, "execute", "Input"), "done->for2")

    get_bi = ge.add_get_member_variable_node("BlockedIndices")
    bel.set_node_pos(get_bi, pos(950, 320))
    len_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Length")
    bel.set_node_pos(len_n, pos(1100, 320))
    connect(find_pin(get_bi, "BlockedIndices", "Output") or bel.find_output_pin_by_index(get_bi, 0),
            find_pin(len_n, "TargetArray", "Input") or find_pin(len_n, "Array", "Input"), "bi->len")
    sub2 = ge.create_node_from_name("Utilities|Operators|integer - integer", unreal.Vector2D(1250, 320), [])
    if not sub2:
        sub2 = ge.create_node_from_name("Math|Integer|integer - integer", unreal.Vector2D(1250, 320), [])
    bel.set_node_pos(sub2, pos(1250, 320))
    connect(find_pin(len_n, "ReturnValue", "Output") or bel.find_output_pin_by_index(len_n, 0),
            find_pin(sub2, "A", "Input"), "len")
    set_val(find_pin(sub2, "B", "Input"), "1", "len-1")
    connect(bel.find_output_pin_by_index(sub2, 0), find_pin(for2, "LastIndex", "Input") or find_pin(for2, "Last", "Input"), "for2 last")
    set_val(find_pin(for2, "FirstIndex", "Input") or find_pin(for2, "First", "Input"), "0", "for2 first")

    # Get BlockedIndices[Index]
    get_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get_at, pos(1500, 200))
    get_bi2 = ge.add_get_member_variable_node("BlockedIndices")
    bel.set_node_pos(get_bi2, pos(1350, 280))
    connect(find_pin(get_bi2, "BlockedIndices", "Output") or bel.find_output_pin_by_index(get_bi2, 0),
            find_pin(get_at, "TargetArray", "Input") or find_pin(get_at, "Array", "Input"), "bi get")
    connect(find_pin(for2, "Index", "Output"), find_pin(get_at, "Index", "Input"), "idx")

    # Set PlotStates[flat] = Blocked
    set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
    bel.set_node_pos(set_at, pos(1800, 60))
    get_ps3 = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_ps3, pos(1600, 250))
    connect(find_pin(for2, "LoopBody", "Output"), find_pin(set_at, "execute", "Input"), "for2->set")
    connect(find_pin(get_ps3, "PlotStates", "Output") or bel.find_output_pin_by_index(get_ps3, 0),
            find_pin(set_at, "TargetArray", "Input") or find_pin(set_at, "Array", "Input"), "ps set")
    connect(find_pin(get_at, "ReturnValue", "Output") or find_pin(get_at, "Item", "Output") or bel.find_output_pin_by_index(get_at, 0),
            find_pin(set_at, "Index", "Input"), "flat->idx")
    set_val(find_pin(set_at, "Item", "Input"), str(STATE_BLOCKED), "Blocked5")
    set_val(find_pin(set_at, "bSizeToFit", "Input") or find_pin(set_at, "SizeToFit", "Input"), "true", "fit")

    # Print for debug once
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(2100, 0))
    connect(find_pin(for2, "Completed", "Output"), find_pin(pr, "execute", "Input"), "done print")
    set_val(find_pin(pr, "InString", "Input"), "Blocked cells applied", "print")

    try:
        bel.compile_blueprint(bp)
        log("InitBlockedFromIndices compiled")
    except Exception as ex:
        log("compile init: " + str(ex))

    # Wire BeginPlay -> call InitBlockedFromIndices
    eg = bel.find_graph(bp, "EventGraph") or bel.find_event_graph(bp)
    ege = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    begin = None
    try:
        begin = ege.find_event_node("ReceiveBeginPlay")
    except Exception:
        pass
    if not begin:
        for n in ege.list_all_nodes():
            if n.get_class().get_name() == "K2Node_Event":
                try:
                    t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
                except Exception:
                    t = ""
                if "BeginPlay" in t:
                    begin = n
                    break
    if not begin:
        log("no BeginPlay")
        return False
    then = find_pin(begin, "then", "Output")
    if then:
        try:
            then.break_pin_links(False)
        except Exception:
            try:
                then.break_pin_links()
            except Exception:
                pass

    # Remove old call nodes to InitBlocked if any
    for n in list(ege.list_all_nodes()):
        try:
            t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
        except Exception:
            t = ""
        if "InitBlocked" in t:
            try:
                ege.remove_nodes([n])
                log("removed old " + t)
            except Exception:
                pass

    call = None
    # Preferred: add_call_function on self function
    try:
        # Get UFunction from generated class
        gc = bp.generated_class()
        fn = unreal.EditorAssetLibrary.load_asset  # noop keep
        # Use graph editor helper
        call = ege.add_call_function_node(str(gc.get_path_name()) + ":" + fname)
        log("call via generated path " + str(call))
    except Exception as ex:
        log("call generated: " + str(ex))
    if not call:
        try:
            call = ege.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:" + fname)
        except Exception as ex:
            log("call C path: " + str(ex))
    if not call:
        # Custom: K2Node_CallFunction create and set function
        try:
            call = ege.create_node_from_name("Call Function", unreal.Vector2D(300, 0), [])
            log("generic Call Function " + str(call))
        except Exception as ex:
            log("generic call: " + str(ex))
    if call:
        bel.set_node_pos(call, pos(280, 0))
        connect(then, find_pin(call, "execute", "Input"), "BP->init")
        # Self target implicit for member
        log("BeginPlay wired to init")
    else:
        log("WARN BeginPlay not wired — TillCell will use SizeToFit without blocked")

    try:
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(MGR)
        log("final compile ok")
        return True
    except Exception as ex:
        log("final compile: " + str(ex))
        return False


def force_save():
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    except Exception:
        try:
            unreal.EditorLevelLibrary.save_current_level()
        except Exception:
            pass
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception:
        pass
    try:
        unreal.EditorAssetLibrary.save_directory("/Game/__ExternalActors__/TopDown/Lvl_TopDown", True, True)
    except Exception:
        pass
    log("saved")


def main():
    log("=== start ===")
    ensure_enum_blocked()
    make_var_editable()
    blocked = collect_blocked()
    indices = set_cdo_blocked_indices(blocked)
    ok = rebuild_init_fn(len(indices))
    force_save()
    # verify airwalls still there
    air = sum(1 for a in eas().get_all_level_actors() if (a.get_actor_label() or "").startswith("AirWall_Water_"))
    soil = sum(1 for a in eas().get_all_level_actors() if (a.get_actor_label() or "").startswith("VMF_Soil_"))
    log("verify airwalls={} soil_left={} init_ok={}".format(air, soil, ok))
    log("=== done ===")


main()
