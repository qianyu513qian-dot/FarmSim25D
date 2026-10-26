# -*- coding: utf-8 -*-
"""Remove preset tilled farmland, block path/harbor/water/cliff/yard, spawn water airwalls."""
import unreal

TAG = "[BLOCK_ZONES]"
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
ENUM_PATH = "/Game/Farm/Grid/E_PlotState"
CUBE = "/Engine/BasicShapes/Cube"
GRASS_MESH = "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass"

CELL = 100.0
WIDTH = 40
HEIGHT = 40
UNIT = 0.01
Z_GRASS = 0.5
STATE_EMPTY = 0
STATE_BLOCKED = 5  # new enumerator after Empty/Tilled/Planted/Watered/Ready
AIRWALL_Z = 100.0
AIRWALL_H_SCALE = 2.2  # cube 100 -> ~220uu tall
AIRWALL_PREFIX = "AirWall_Water_"


def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def cell_center(cx, cy, z=0.0):
    return unreal.Vector(cx * CELL + CELL * 0.5, cy * CELL + CELL * 0.5, z)


def parse_cell(lab):
    parts = (lab or "").split("_")
    try:
        return int(parts[-2]), int(parts[-1])
    except Exception:
        return None


def water_edge_x(cy):
    base = 5
    wobble = (cy * 7 + 3) % 5
    if wobble == 0:
        return base - 1
    if wobble == 1:
        return base
    if wobble == 2:
        return base + 1
    if wobble == 3:
        return base
    return base + 2


def is_water_cell(cx, cy):
    return 0 <= cx < WIDTH and 0 <= cy < HEIGHT and cx <= water_edge_x(cy)


def ensure_blocked_enum():
    """Ensure E_PlotState has index 5 = Blocked. Returns blocked index."""
    ude = unreal.EditorAssetLibrary.load_asset(ENUM_PATH)
    if not ude:
        log("ERROR no enum")
        return STATE_BLOCKED
    # Try add enumerator until we have at least 6 (0..5)
    added = 0
    for libname in ("EnumEditorLibrary", "UserDefinedEnumLibrary"):
        lib = getattr(unreal, libname, None)
        if not lib:
            continue
        for _ in range(3):
            try:
                if hasattr(lib, "add_enumerator"):
                    lib.add_enumerator(ude)
                    added += 1
                    log("add_enumerator via " + libname)
                elif hasattr(lib, "insert_enumerator"):
                    lib.insert_enumerator(ude, 5)
                    added += 1
                    log("insert_enumerator via " + libname)
                    break
            except Exception as ex:
                log("add enum try: " + str(ex))
                break
        # rename last / index 5
        for setm in ("set_enumerator_user_facing_name", "set_enumerator_display_name",
                     "set_enumerator_display_name_string"):
            if not hasattr(lib, setm):
                continue
            try:
                if "string" in setm:
                    getattr(lib, setm)(ude, STATE_BLOCKED, "Blocked")
                else:
                    getattr(lib, setm)(ude, STATE_BLOCKED, unreal.Text("Blocked"))
                log("named Blocked via " + setm)
                break
            except Exception as ex:
                log("rename Blocked: " + str(ex))
        if added:
            break
    # Also try set_display_names full list
    if hasattr(unreal, "UserDefinedEnumLibrary"):
        try:
            names = ["Empty", "Tilled", "Planted", "Watered", "Ready", "Blocked"]
            arr = unreal.Array(unreal.Text)
            for n in names:
                arr.append(unreal.Text(n))
            unreal.UserDefinedEnumLibrary.set_display_names(ude, arr)
            log("set_display_names full list ok")
        except Exception as ex:
            log("set_display_names: " + str(ex))
    try:
        unreal.EditorAssetLibrary.save_asset(ENUM_PATH)
    except Exception as ex:
        log("save enum: " + str(ex))
    # verify bytes
    try:
        import os
        p = r"E:\UE\FarmSim25D\Content\Farm\Grid\E_PlotState.uasset"
        data = open(p, "rb").read()
        log("enum has Blocked bytes: " + str(b"Blocked" in data))
    except Exception as ex:
        log("byte check: " + str(ex))
    return STATE_BLOCKED


def collect_zone_cells():
    path, bridge, cliff, yard, soil, crops = set(), set(), set(), set(), set(), set()
    grass = set()
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        c = parse_cell(lab)
        if lab.startswith("VMF_Path") and c:
            path.add(c)
        elif lab.startswith("VMF_Bridge") and c:
            bridge.add(c)
        elif lab.startswith("VMF_Cliff_") and c:
            cliff.add(c)
        elif lab.startswith("VMF_Yard_") and c:
            yard.add(c)
        elif lab.startswith("VMF_Soil_") and c:
            soil.add(c)
        elif lab.startswith("VMF_Crop") and c:
            crops.add(c)
        elif lab.startswith("VMF_Grass_") and "Clump" not in lab and c:
            grass.add(c)
    water = set()
    for cy in range(HEIGHT):
        for cx in range(WIDTH):
            if is_water_cell(cx, cy):
                water.add((cx, cy))
    log("zones path={} bridge={} cliff={} yard={} water={} soil={} crop={} grass={}".format(
        len(path), len(bridge), len(cliff), len(yard), len(water), len(soil), len(crops), len(grass)))
    return {
        "path": path, "bridge": bridge, "cliff": cliff, "yard": yard,
        "water": water, "soil": soil, "crops": crops, "grass": grass,
    }


def destroy_preset_farmland():
    """Delete VMF_Soil_* and VMF_Crop* preset actors. Keep grass/trees/house/path/water."""
    killed = []
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_Soil_"):
            killed.append(lab)
            try:
                eas().destroy_actor(a)
            except Exception as ex:
                log("destroy soil fail {}: {}".format(lab, ex))
        elif lab.startswith("VMF_Crop"):
            killed.append(lab)
            try:
                eas().destroy_actor(a)
            except Exception as ex:
                log("destroy crop fail {}: {}".format(lab, ex))
    log("deleted preset farmland n={} sample={}".format(len(killed), killed[:12]))
    return killed


def restore_grass(cells, existing_grass):
    mesh = unreal.EditorAssetLibrary.load_asset(GRASS_MESH)
    if not mesh:
        log("ERROR no grass mesh")
        return 0
    spawned = 0
    for cx, cy in sorted(cells):
        if (cx, cy) in existing_grass:
            continue
        label = "VMF_Grass_{}_{}".format(cx, cy)
        # skip if somehow exists
        found = None
        for a in eas().get_all_level_actors():
            if (a.get_actor_label() or "") == label:
                found = a
                break
        loc = cell_center(cx, cy, Z_GRASS)
        if found is None:
            found = eas().spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator())
            found.set_actor_label(label)
            spawned += 1
        found.set_actor_location(loc, False, True)
        found.set_actor_scale3d(unreal.Vector(UNIT, UNIT, UNIT))
        smc = found.static_mesh_component
        smc.set_static_mesh(mesh)
        try:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            pass
        try:
            found.set_actor_hidden_in_game(False)
            found.set_is_temporarily_hidden_in_editor(False)
        except Exception:
            pass
    log("restored grass tiles n={}".format(spawned))
    return spawned


def destroy_old_airwalls():
    n = 0
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if lab.startswith(AIRWALL_PREFIX) or lab.startswith("AirWall_"):
            try:
                eas().destroy_actor(a)
                n += 1
            except Exception:
                pass
    log("cleared old airwalls n={}".format(n))
    return n


def spawn_water_airwalls(water_cells, bridge_cells):
    """Invisible blocking cubes on water cells except bridge/pier walkways."""
    cube = unreal.EditorAssetLibrary.load_asset(CUBE)
    if not cube:
        log("ERROR no Cube mesh")
        return 0
    destroy_old_airwalls()
    spawned = 0
    for cx, cy in sorted(water_cells):
        if (cx, cy) in bridge_cells:
            continue
        label = "{}{}_{}".format(AIRWALL_PREFIX, cx, cy)
        loc = cell_center(cx, cy, AIRWALL_Z)
        actor = eas().spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator())
        actor.set_actor_label(label)
        # slightly inset XY so bridge edges stay walkable
        actor.set_actor_scale3d(unreal.Vector(0.92, 0.92, AIRWALL_H_SCALE))
        smc = actor.static_mesh_component
        smc.set_static_mesh(cube)
        try:
            smc.set_visibility(False, True)
        except Exception:
            pass
        try:
            actor.set_actor_hidden_in_game(True)
        except Exception:
            pass
        try:
            # keep visible in editor wireframe? hide in editor too for cleanliness
            actor.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass
        try:
            actor.set_actor_enable_collision(True)
        except Exception:
            pass
        try:
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        except Exception:
            try:
                smc.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            except Exception as ex:
                log("airwall coll enable fail: " + str(ex))
        for prop, val in (
            ("collision_profile_name", "BlockAll"),
            ("CollisionProfileName", "BlockAll"),
        ):
            try:
                smc.set_editor_property(prop, val)
                break
            except Exception:
                pass
        # Ensure pawn blocked
        try:
            smc.set_editor_property("generate_overlap_events", False)
        except Exception:
            pass
        spawned += 1
    log("spawned water airwalls n={}".format(spawned))
    return spawned


def find_grid_manager():
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        cn = a.get_class().get_name()
        if "GridManager" in lab or "GridManager" in cn:
            return a
    return None


def apply_plotstates_blocked(blocked_cells):
    """Fill PlotStates[W*H] Empty, set blocked cells to STATE_BLOCKED on GM instance + CDO."""
    gm = find_grid_manager()
    if not gm:
        log("ERROR no GridManager actor")
        return 0
    n = WIDTH * HEIGHT
    # Build python list then assign
    # PlotStates is TArray of byte/enum — set via editor property with Array
    try:
        arr = gm.get_editor_property("PlotStates")
    except Exception as ex:
        log("get PlotStates: " + str(ex))
        arr = None

    # Create fresh array of correct length using unreal.Array
    # Enum typed array: use ints and let engine coerce
    new_arr = []
    for i in range(n):
        new_arr.append(STATE_EMPTY)
    for cx, cy in blocked_cells:
        if 0 <= cx < WIDTH and 0 <= cy < HEIGHT:
            new_arr[cy * WIDTH + cx] = STATE_BLOCKED
    blocked_n = sum(1 for v in new_arr if v == STATE_BLOCKED)

    # Assign via set_editor_property — need unreal.Array
    try:
        ua = unreal.Array(int)
        # PlotStates may be enum array; try byte/int
        for v in new_arr:
            ua.append(int(v))
        gm.set_editor_property("PlotStates", ua)
        log("set instance PlotStates len={} blocked={}".format(n, blocked_n))
    except Exception as ex:
        log("set PlotStates int Array fail: " + str(ex))
        # Fallback: resize via repeated - try Enum
        try:
            # Clear and use modify on actor
            gm.set_editor_property("PlotStates", [])
            # Can't easily append enum in python; store BlockedIndices instead
            log("will rely on BlockedIndices + BeginPlay")
        except Exception as ex2:
            log("clear fail: " + str(ex2))

    # Also store BlockedIndices for BeginPlay apply
    indices = []
    for cx, cy in sorted(blocked_cells):
        if 0 <= cx < WIDTH and 0 <= cy < HEIGHT:
            indices.append(cy * WIDTH + cx)
    ensure_blocked_indices_var()
    try:
        bi = unreal.Array(int)
        for i in indices:
            bi.append(int(i))
        gm.set_editor_property("BlockedIndices", bi)
        log("set BlockedIndices n={}".format(len(indices)))
    except Exception as ex:
        log("set BlockedIndices: " + str(ex))

    # Verify
    try:
        ps = gm.get_editor_property("PlotStates")
        log("verify PlotStates len={} sample0={} blocked_count~{}".format(
            len(ps) if ps is not None else None,
            ps[0] if ps else None,
            blocked_n))
    except Exception as ex:
        log("verify: " + str(ex))
    return blocked_n


def ensure_blocked_indices_var():
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    names = [str(x) for x in bel.list_member_variable_names(bp)]
    if "BlockedIndices" not in names:
        pin = unreal.EdGraphPinType()
        # int array
        try:
            pin.pin_category = "int"
            pin.container_type = unreal.EdGraphPinContainerType.ARRAY
        except Exception:
            try:
                pin.import_text('(PinCategory="int",ContainerType=Array)')
            except Exception as ex:
                log("pin type: " + str(ex))
        try:
            bel.add_member_variable(bp, "BlockedIndices", pin)
            log("added BlockedIndices member")
        except Exception as ex:
            log("add BlockedIndices: " + str(ex))
            # alternate API
            try:
                bel.add_member_variable(bp, "BlockedIndices", unreal.EdGraphPinType())
            except Exception as ex2:
                log("add2: " + str(ex2))
    try:
        bel.compile_blueprint(bp)
    except Exception as ex:
        log("compile after var: " + str(ex))
    try:
        unreal.EditorAssetLibrary.save_asset(MGR)
    except Exception:
        pass


def break_beginplay_clear():
    """Ensure BeginPlay does not Clear PlotStates (keeps editor-filled blocked states)."""
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    eg = bel.find_graph(bp, "EventGraph") or bel.find_event_graph(bp)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    begin = None
    try:
        begin = ge.find_event_node("ReceiveBeginPlay")
    except Exception:
        pass
    if not begin:
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_Event":
                try:
                    t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
                except Exception:
                    t = ""
                if "BeginPlay" in t:
                    begin = n
                    break
    if not begin:
        log("no BeginPlay node found")
        return
    then = None
    for p in bel.list_all_pins(begin):
        if str(p.get_pin_name()).lower() == "then":
            then = p
            break
    if then:
        try:
            then.break_pin_links(False)
        except Exception:
            try:
                then.break_pin_links()
            except Exception as ex:
                log("break then: " + str(ex))
        log("BeginPlay then links broken (preserve PlotStates)")
    # Also break execute on Array_Clear if orphaned chain could run somehow — already broken
    try:
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(MGR)
        log("GridManager compile+save ok")
    except Exception as ex:
        log("compile/save: " + str(ex))


def wire_beginplay_apply_blocked():
    """
    Prefer: BeginPlay -> InitBlockedFromIndices custom fn.
    Build InitBlockedFromIndices: ForEach BlockedIndices -> SetArrayElem PlotStates Item=5.
    Also: if PlotStates length < W*H, fill Empty first.
    Fallback if graph wiring fails: rely on editor-filled PlotStates + broken Clear.
    """
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    # Create function graph
    fname = "InitBlockedFromIndices"
    graph = bel.find_graph(bp, fname)
    if not graph:
        try:
            bel.add_function_graph(bp, fname)
            graph = bel.find_graph(bp, fname)
            log("created " + fname)
        except Exception as ex:
            log("add_function_graph: " + str(ex))
            return False
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    # Clear old nodes except entry
    entry = None
    to_del = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            to_del.append(n)
    if to_del:
        ge.remove_nodes(to_del)
        log("{} removed {} nodes".format(fname, len(to_del)))
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

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
            log("skip conn " + label)
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
            log("set {} fail: {}".format(label, ex))

    def pos(x, y):
        return unreal.IntPoint(int(x), int(y))

    # Ensure PlotStates sized: Length; Branch; if short, skip (editor fill) — keep simple:
    # ForEachLoop BlockedIndices -> SetArrayElem
    get_bi = ge.add_get_member_variable_node("BlockedIndices")
    bel.set_node_pos(get_bi, pos(200, 200))

    foreach = None
    for path in (
        "Utilities|FlowControl|ForEachLoop",
        "Flow Control|For Each Loop",
        "Utilities|FlowControl|For Each Loop",
    ):
        try:
            foreach = ge.create_node_from_name(path, unreal.Vector2D(500, 0), [])
            if foreach:
                log("ForEach via " + path)
                break
        except Exception as ex:
            log("ForEach try {}: {}".format(path, ex))
    if not foreach:
        # Array ForEach via macro instance alternate
        try:
            foreach = ge.create_node_from_name("For Each Loop", unreal.Vector2D(500, 0), [])
        except Exception as ex:
            log("ForEach name fail: " + str(ex))
    if not foreach:
        log("WARN no ForEach — skip BP init wire")
        return False

    bel.set_node_pos(foreach, pos(500, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(foreach, "execute", "Input"), "entry->fe")
    connect(find_pin(get_bi, "BlockedIndices", "Output") or bel.find_output_pin_by_index(get_bi, 0),
            find_pin(foreach, "Array", "Input") or find_pin(foreach, "TargetArray", "Input"), "bi->arr")

    get_ps = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_ps, pos(700, 250))
    set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
    if not set_at:
        set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:SetArrayElem")
    bel.set_node_pos(set_at, pos(900, 80))
    connect(find_pin(foreach, "LoopBody", "Output") or find_pin(foreach, "Element", "Output") and find_pin(foreach, "then", "Output"),
            find_pin(set_at, "execute", "Input"), "body->set")
    # LoopBody is exec; Array Element / Index are data
    loop_body = find_pin(foreach, "LoopBody", "Output")
    if loop_body:
        connect(loop_body, find_pin(set_at, "execute", "Input"), "body->set2")
    connect(find_pin(get_ps, "PlotStates", "Output") or bel.find_output_pin_by_index(get_ps, 0),
            find_pin(set_at, "TargetArray", "Input") or find_pin(set_at, "Array", "Input"), "ps->arr")
    # Index = Array Index from foreach (the blocked flat index is the ARRAY ELEMENT, not loop index)
    # BlockedIndices stores flat cell indices; ForEach Element = that index; use Element as Array_Set Index
    elem = find_pin(foreach, "Array Element", "Output") or find_pin(foreach, "Element", "Output") or find_pin(foreach, "Item", "Output")
    connect(elem, find_pin(set_at, "Index", "Input"), "elem->idx")
    set_val(find_pin(set_at, "Item", "Input"), str(STATE_BLOCKED), "Item=Blocked")
    size_pin = find_pin(set_at, "bSizeToFit", "Input") or find_pin(set_at, "SizeToFit", "Input")
    set_val(size_pin, "true", "SizeToFit")

    # Also need PlotStates pre-sized to W*H Empty. Add prefix: Clear+ForLoop Add Empty then ForEach.
    # Rebuild more carefully — clear graph again and do full chain
    to_del = [n for n in ge.list_all_nodes() if n.get_class().get_name() != "K2Node_FunctionEntry"]
    if to_del:
        ge.remove_nodes(to_del)

    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

    # Clear
    clear_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Clear")
    bel.set_node_pos(clear_n, pos(300, 0))
    get_ps1 = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_ps1, pos(100, 180))
    connect(find_pin(entry, "then", "Output"), find_pin(clear_n, "execute", "Input"), "e->clear")
    connect(find_pin(get_ps1, "PlotStates", "Output") or bel.find_output_pin_by_index(get_ps1, 0),
            find_pin(clear_n, "TargetArray", "Input") or find_pin(clear_n, "Array", "Input"), "ps->clear")

    # ForLoop 0 .. W*H-1
    forloop = None
    for path in ("Utilities|FlowControl|ForLoop", "Flow Control|For Loop", "Utilities|FlowControl|For Loop"):
        try:
            forloop = ge.create_node_from_name(path, unreal.Vector2D(600, 0), [])
            if forloop:
                break
        except Exception:
            pass
    if not forloop:
        log("no ForLoop")
        return False
    bel.set_node_pos(forloop, pos(600, 0))
    connect(find_pin(clear_n, "then", "Output"), find_pin(forloop, "execute", "Input"), "clear->for")

    get_w = ge.add_get_member_variable_node("GridWidth")
    get_h = ge.add_get_member_variable_node("GridHeight")
    bel.set_node_pos(get_w, pos(350, 250))
    bel.set_node_pos(get_h, pos(350, 330))
    mul = None
    for path in ("Utilities|Operators|integer * integer", "Math|Integer|integer * integer"):
        try:
            mul = ge.create_node_from_name(path, unreal.Vector2D(500, 280), [])
            if mul:
                break
        except Exception:
            pass
    if mul:
        bel.set_node_pos(mul, pos(500, 280))
        connect(find_pin(get_w, "GridWidth", "Output") or bel.find_output_pin_by_index(get_w, 0),
                find_pin(mul, "A", "Input"), "w")
        connect(find_pin(get_h, "GridHeight", "Output") or bel.find_output_pin_by_index(get_h, 0),
                find_pin(mul, "B", "Input"), "h")
    sub = None
    for path in ("Utilities|Operators|integer - integer", "Math|Integer|integer - integer"):
        try:
            sub = ge.create_node_from_name(path, unreal.Vector2D(620, 280), [])
            if sub:
                break
        except Exception:
            pass
    if sub and mul:
        bel.set_node_pos(sub, pos(620, 280))
        connect(bel.find_output_pin_by_index(mul, 0) or find_pin(mul, "Return", "Output"),
                find_pin(sub, "A", "Input"), "mul->sub")
        set_val(find_pin(sub, "B", "Input"), "1", "sub.B")
        connect(bel.find_output_pin_by_index(sub, 0) or find_pin(sub, "Return", "Output"),
                find_pin(forloop, "LastIndex", "Input") or find_pin(forloop, "Last", "Input"), "last")
    set_val(find_pin(forloop, "FirstIndex", "Input") or find_pin(forloop, "First", "Input"), "0", "first")

    add_n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Add")
    bel.set_node_pos(add_n, pos(950, 80))
    get_ps2 = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_ps2, pos(750, 220))
    connect(find_pin(forloop, "LoopBody", "Output"), find_pin(add_n, "execute", "Input"), "for->add")
    connect(find_pin(get_ps2, "PlotStates", "Output") or bel.find_output_pin_by_index(get_ps2, 0),
            find_pin(add_n, "TargetArray", "Input") or find_pin(add_n, "Array", "Input"), "ps->add")
    set_val(find_pin(add_n, "NewItem", "Input") or find_pin(add_n, "Item", "Input"), "0", "Add Empty")

    # After Completed: ForEach BlockedIndices SetArrayElem
    foreach = None
    for path in ("Utilities|FlowControl|ForEachLoop", "Flow Control|For Each Loop", "Utilities|FlowControl|For Each Loop"):
        try:
            foreach = ge.create_node_from_name(path, unreal.Vector2D(1200, 0), [])
            if foreach:
                break
        except Exception:
            pass
    if not foreach:
        log("no ForEach after fill")
        # Still compile what we have
    else:
        bel.set_node_pos(foreach, pos(1200, 0))
        connect(find_pin(forloop, "Completed", "Output"), find_pin(foreach, "execute", "Input"), "done->fe")
        get_bi = ge.add_get_member_variable_node("BlockedIndices")
        bel.set_node_pos(get_bi, pos(1000, 300))
        connect(find_pin(get_bi, "BlockedIndices", "Output") or bel.find_output_pin_by_index(get_bi, 0),
                find_pin(foreach, "Array", "Input") or find_pin(foreach, "TargetArray", "Input"), "bi")
        set_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Set")
        bel.set_node_pos(set_at, pos(1600, 80))
        get_ps3 = ge.add_get_member_variable_node("PlotStates")
        bel.set_node_pos(get_ps3, pos(1400, 250))
        connect(find_pin(foreach, "LoopBody", "Output"), find_pin(set_at, "execute", "Input"), "fe->set")
        connect(find_pin(get_ps3, "PlotStates", "Output") or bel.find_output_pin_by_index(get_ps3, 0),
                find_pin(set_at, "TargetArray", "Input") or find_pin(set_at, "Array", "Input"), "ps->set")
        elem = (find_pin(foreach, "Array Element", "Output") or find_pin(foreach, "Element", "Output")
                or find_pin(foreach, "Item", "Output"))
        connect(elem, find_pin(set_at, "Index", "Input"), "elem->idx")
        set_val(find_pin(set_at, "Item", "Input"), str(STATE_BLOCKED), "Blocked")
        set_val(find_pin(set_at, "bSizeToFit", "Input") or find_pin(set_at, "SizeToFit", "Input"), "true", "fit")

    # Wire EventGraph BeginPlay -> InitBlockedFromIndices
    eg = bel.find_graph(bp, "EventGraph") or bel.find_event_graph(bp)
    ege = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    begin = None
    try:
        begin = ege.find_event_node("ReceiveBeginPlay")
    except Exception:
        pass
    if not begin:
        for n in ege.list_all_nodes():
            if n.get_class().get_name() != "K2Node_Event":
                continue
            try:
                t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
            except Exception:
                t = ""
            if "BeginPlay" in t:
                begin = n
                break
    if begin:
        then = find_pin(begin, "then", "Output")
        if then:
            try:
                then.break_pin_links(False)
            except Exception:
                try:
                    then.break_pin_links()
                except Exception:
                    pass
        # Call function
        call = None
        try:
            call = ege.add_call_function_node(bp.get_path_name() + ":" + fname)
        except Exception:
            call = None
        if not call:
            try:
                # Member function call node
                call = ege.create_node_from_name("Call Function|" + fname, unreal.Vector2D(300, 0), [])
            except Exception as ex:
                log("call node: " + str(ex))
        if not call:
            # K2Node_CallFunction on self
            try:
                call = ege.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:" + fname)
            except Exception as ex:
                log("call2: " + str(ex))
        if call:
            bel.set_node_pos(call, pos(300, 0))
            connect(find_pin(begin, "then", "Output"), find_pin(call, "execute", "Input"), "BP->init")
            log("BeginPlay -> " + fname)
        else:
            log("WARN could not create call to " + fname + "; relying on editor PlotStates")
            # Keep BeginPlay disconnected
    try:
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(MGR)
        log("InitBlockedFromIndices compile ok")
        return True
    except Exception as ex:
        log("compile init: " + str(ex))
        return False


def force_save_level():
    results = {}
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        results["save_current_level"] = bool(les.save_current_level())
    except Exception as e:
        results["save_current_level"] = str(e)
        try:
            unreal.EditorLevelLibrary.save_current_level()
            results["save_current_level_ell"] = True
        except Exception as e2:
            results["save_current_level_ell"] = str(e2)
    try:
        results["save_dirty"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
    except Exception as e:
        results["save_dirty"] = str(e)
    try:
        results["save_ext"] = bool(unreal.EditorAssetLibrary.save_directory(
            "/Game/__ExternalActors__/TopDown/Lvl_TopDown", True, True))
    except Exception as e:
        results["save_ext"] = str(e)
    try:
        results["save_lvl"] = bool(unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Lvl_TopDown"))
    except Exception as e:
        results["save_lvl"] = str(e)
    # second pass
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception:
        pass
    log("save results " + str(results))
    return results


def main():
    log("=== start ===")
    blocked_idx = ensure_blocked_enum()
    log("STATE_BLOCKED=" + str(blocked_idx))

    zones = collect_zone_cells()
    soil_cells = set(zones["soil"]) | set(zones["crops"])

    deleted = destroy_preset_farmland()
    # refresh grass set after deletes
    zones2 = collect_zone_cells()
    grass_restored = restore_grass(soil_cells, zones2["grass"])

    # Block: path (road), bridge (harbor/pier), water, cliff, yard (not blank grass)
    blocked = set()
    blocked |= zones["path"]
    blocked |= zones["bridge"]
    blocked |= zones["water"]
    blocked |= zones["cliff"]
    blocked |= zones["yard"]
    log("blocked total uniq={}".format(len(blocked)))

    blocked_n = apply_plotstates_blocked(blocked)
    air_n = spawn_water_airwalls(zones["water"], zones["bridge"])

    # Wire runtime init (Clear+fill Empty+apply BlockedIndices) OR break Clear
    wired = wire_beginplay_apply_blocked()
    if not wired:
        break_beginplay_clear()
        # re-apply plotstates after break
        apply_plotstates_blocked(blocked)

    # Final counts
    soil_left = sum(1 for a in eas().get_all_level_actors() if (a.get_actor_label() or "").startswith("VMF_Soil_"))
    crop_left = sum(1 for a in eas().get_all_level_actors() if (a.get_actor_label() or "").startswith("VMF_Crop"))
    air_left = sum(1 for a in eas().get_all_level_actors() if (a.get_actor_label() or "").startswith(AIRWALL_PREFIX))
    log("remaining Soil={} Crop={} AirWalls={}".format(soil_left, crop_left, air_left))

    force_save_level()
    try:
        unreal.EditorAssetLibrary.save_asset(MGR)
    except Exception:
        pass

    log("SUMMARY deleted={} grass_restored={} blocked_cells={} airwalls={} wired_init={}".format(
        len(deleted), grass_restored, len(blocked), air_n, wired))
    log("=== done ===")


main()
