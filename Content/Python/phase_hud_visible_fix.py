# -*- coding: utf-8 -*-
"""Make Farm HUD clearly visible: loud PrintString + DrawDebugString on Tick.
Does NOT change camera. Force-saves. Tries UMG TextBlocks once more.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
WBP = "/Game/Farm/UI/WBP_FarmHUD"

def log(m):
    unreal.log("[HUD_FIX] " + str(m))
    print("[HUD_FIX] " + str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def conn(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name() if a else None, b.get_pin_name() if b else None, ok))
    return ok

def set_val(pin, value, label=""):
    if not pin:
        log("no pin " + label)
        return False
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, value))
        return True
    except Exception as e:
        log("set {} FAIL {}".format(label, e))
        return False

def out_pin(node, prefer=None):
    if prefer:
        p = find_pin(node, prefer, "Output")
        if p:
            return p
    outs = [p for p in bel.list_all_pins(node) if "output" in str(p.get_pin_direction()).lower()]
    return outs[0] if outs else None

# ---------------------------------------------------------------------------
# 1) Try UMG TextBlocks again (best effort; PrintString is the guarantee)
# ---------------------------------------------------------------------------
def try_build_umg():
    if not unreal.EditorAssetLibrary.does_asset_exist(WBP):
        factory = unreal.WidgetBlueprintFactory()
        try:
            factory.set_editor_property("parent_class", unreal.UserWidget)
        except Exception:
            pass
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        if not unreal.EditorAssetLibrary.does_directory_exist("/Game/Farm/UI"):
            unreal.EditorAssetLibrary.make_directory("/Game/Farm")
            unreal.EditorAssetLibrary.make_directory("/Game/Farm/UI")
        tools.create_asset("WBP_FarmHUD", "/Game/Farm/UI", unreal.WidgetBlueprint, factory)
        log("created WBP")
    wbp = unreal.load_asset(WBP)
    tree = unreal.load_object(wbp, "WidgetTree")
    log("tree=" + str(tree))
    canvas = None
    # Prefer call_method ConstructWidget
    for method in ("ConstructWidget",):
        try:
            canvas = tree.call_method(method, (unreal.CanvasPanel.static_class(), unreal.Name("RootCanvas")))
            log("ConstructWidget canvas=" + str(canvas))
            break
        except Exception as e:
            log("ConstructWidget: " + str(e))
    if not canvas:
        try:
            canvas = unreal.new_object(unreal.CanvasPanel, tree, unreal.Name("RootCanvas"))
            log("new_object canvas=" + str(canvas))
        except Exception as e:
            log("new_object: " + str(e))
            return False
    # Set root
    root_ok = False
    for fn, args in (
        ("SetRootWidget", (canvas,)),
        ("set_root_widget", (canvas,)),
    ):
        try:
            tree.call_method(fn, args)
            log(fn + " ok")
            root_ok = True
            break
        except Exception as e:
            log(fn + ": " + str(e))
    if not root_ok:
        for prop in ("RootWidget", "root_widget"):
            try:
                tree.set_editor_property(prop, canvas)
                log("set_editor_property " + prop + " ok")
                root_ok = True
                break
            except Exception as e:
                log("set " + prop + ": " + str(e))
    if not root_ok:
        log("UMG root still blocked - PrintString path only")
        return False

    # Add VerticalBox + TextBlocks
    try:
        vbox = tree.call_method("ConstructWidget", (unreal.VerticalBox.static_class(), unreal.Name("VBoxHUD")))
    except Exception:
        try:
            vbox = unreal.new_object(unreal.VerticalBox, tree, unreal.Name("VBoxHUD"))
        except Exception as e:
            log("vbox fail " + str(e))
            return False
    try:
        slot = canvas.add_child_to_canvas(vbox)
        try:
            slot.set_editor_property("anchors", unreal.Anchors(minimum=unreal.Vector2D(0, 0), maximum=unreal.Vector2D(0, 0)))
            slot.set_editor_property("position", unreal.Vector2D(24, 24))
            slot.set_editor_property("auto_size", True)
        except Exception as e:
            log("slot " + str(e))
    except Exception as e:
        log("add canvas child " + str(e))
        return False

    for name, default in (("TxtMoney", "Money: 50"), ("TxtSeeds", "Seeds: 5"), ("TxtCrops", "Crops: 0")):
        try:
            tb = tree.call_method("ConstructWidget", (unreal.TextBlock.static_class(), unreal.Name(name)))
        except Exception:
            tb = unreal.new_object(unreal.TextBlock, tree, unreal.Name(name))
        try:
            tb.set_editor_property("text", default)
        except Exception:
            try:
                tb.set_text(default)
            except Exception as e:
                log("text {}: {}".format(name, e))
        try:
            font = tb.get_editor_property("font")
            font.size = 28
            tb.set_editor_property("font", font)
        except Exception:
            pass
        try:
            vbox.add_child_to_vertical_box(tb)
            log("UMG added " + name)
        except Exception as e:
            log("add {}: {}".format(name, e))
    try:
        bel.compile_blueprint(wbp)
    except Exception as e:
        log("wbp compile " + str(e))
    unreal.EditorAssetLibrary.save_asset(WBP, only_if_is_dirty=False)
    log("UMG build attempted root_ok=" + str(root_ok))
    return root_ok

# ---------------------------------------------------------------------------
# 2) Patch UpdateFarmHUD PrintString to be loud + add DrawDebugString
# ---------------------------------------------------------------------------
def patch_update_farm_hud(bp):
    ug = bel.find_graph(bp, "UpdateFarmHUD")
    if not ug:
        log("NO UpdateFarmHUD graph")
        return False
    ge = unreal.BlueprintGraphEditor.get_graph_editor(ug)

    print_n = None
    ret_n = None
    entry = None
    for n in ge.list_all_nodes():
        t = title(n)
        cn = n.get_class().get_name()
        if "PrintString" in t or (cn == "K2Node_CallFunction" and "PrintString" in str(n.get_function_name() if hasattr(n, "get_function_name") else "")):
            # check pins for Key FarmHUD
            kp = find_pin(n, "Key", "Input")
            try:
                if kp and (kp.get_pin_value() or "") == "FarmHUD":
                    print_n = n
            except Exception:
                pass
            if not print_n and "Print" in t:
                print_n = n
        if cn == "K2Node_FunctionResult":
            ret_n = n
        if cn == "K2Node_FunctionEntry":
            entry = n

    # Also find by scanning PrintString nodes
    if not print_n:
        for n in ge.list_all_nodes():
            if title(n) == "PrintString":
                print_n = n
                break

    if not print_n:
        log("NO PrintString in UpdateFarmHUD")
        return False

    # Loud PrintString
    set_val(find_pin(print_n, "Duration", "Input"), "999.0", "Duration")
    set_val(find_pin(print_n, "Key", "Input"), "FarmHUD", "Key")
    set_val(find_pin(print_n, "bPrintToScreen", "Input"), "true", "screen")
    set_val(find_pin(print_n, "bPrintToLog", "Input"), "true", "log")
    set_val(find_pin(print_n, "TextColor", "Input"), "(R=1.000000,G=1.000000,B=0.000000,A=1.000000)", "yellow")

    # Prefixed literal on first Append "Money: " -> "*** Money: "
    for n in ge.list_all_nodes():
        if title(n) != "Append":
            continue
        ap = find_pin(n, "A", "Input")
        if not ap:
            continue
        # only if A is literal (no links) and looks like Money:
        if conn(ap):
            continue
        try:
            cur = ap.get_pin_value() or ""
        except Exception:
            cur = ""
        if cur.strip().startswith("Money"):
            set_val(ap, "*** Money: ", "prefix")
            break

    # Insert DrawDebugString after PrintString, before Return
    # Break print.then -> return, insert DrawDebugString
    then_print = find_pin(print_n, "then", "Output")
    # Remove any existing DrawDebugString we may have added previously
    existing_dds = []
    for n in list(ge.list_all_nodes()):
        t = title(n)
        if "DrawDebugString" in t:
            existing_dds.append(n)
    if existing_dds:
        for n in existing_dds:
            for p in bel.list_all_pins(n):
                try:
                    p.break_pin_links()
                except Exception:
                    pass
        try:
            ge.remove_nodes(existing_dds)
            log("removed old DrawDebugString x" + str(len(existing_dds)))
        except Exception as e:
            log("remove dds " + str(e))

    dds = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
    if not dds:
        # try alternate
        try:
            dds = ge.create_node_from_name("Development|Debug|Draw Debug String", unreal.Vector2D(2000, 0), [])
        except Exception as e:
            log("dds create fail " + str(e))
            dds = None
    if dds:
        bel.set_node_pos(dds, pos(1950, 80))
        # Wire exec: Print -> DDS -> Return
        if then_print:
            try:
                then_print.break_pin_links()
            except Exception:
                pass
        connect(then_print, find_pin(dds, "execute", "Input"), "print->dds")
        if ret_n:
            connect(find_pin(dds, "then", "Output"), find_pin(ret_n, "execute", "Input"), "dds->ret")

        # TextLocation = GetActorLocation + (0,0,140)
        get_loc = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
        bel.set_node_pos(get_loc, pos(1500, 300))
        add_v = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
        if not add_v:
            add_v = ge.create_node_from_name("Utilities|Operators|vector + vector", unreal.Vector2D(1700, 300), [])
        bel.set_node_pos(add_v, pos(1700, 300))
        connect(out_pin(get_loc, "ReturnValue"), find_pin(add_v, "A", "Input"), "loc->A")
        set_val(find_pin(add_v, "B", "Input"), "(X=0.000000,Y=0.000000,Z=140.000000)", "offsetZ")
        connect(out_pin(add_v, "ReturnValue"), find_pin(dds, "TextLocation", "Input") or find_pin(dds, "Location", "Input"), "pos->dds")

        # Text = same string as Print InString (already linked). Grab from Print's InString source.
        in_str = find_pin(print_n, "InString", "Input")
        srcs = conn(in_str) if in_str else []
        dds_text = find_pin(dds, "Text", "Input") or find_pin(dds, "InString", "Input")
        if srcs and dds_text:
            connect(srcs[0], dds_text, "str->dds")
        else:
            set_val(dds_text, "Money / Seeds / Crops", "dds_fallback")

        set_val(find_pin(dds, "Duration", "Input"), "0.05", "dds_dur")
        # TextColor yellow
        for pname in ("TextColor", "Color"):
            p = find_pin(dds, pname, "Input")
            if p:
                set_val(p, "(R=1.000000,G=1.000000,B=0.000000,A=1.000000)", "dds_color")
                break
        # TestBaseActor = self
        self_pin = find_pin(dds, "TestBaseActor", "Input") or find_pin(dds, "BaseActor", "Input")
        # leave default None / self optional
        log("DrawDebugString wired")
    else:
        # reconnect print -> return if we broke it
        if ret_n and then_print and not conn(then_print):
            connect(then_print, find_pin(ret_n, "execute", "Input"), "print->ret restore")
        log("NO DrawDebugString node - PrintString only")

    log("UpdateFarmHUD patched")
    return True

# ---------------------------------------------------------------------------
# 3) Call UpdateFarmHUD at end of Tick so HUD refreshes every frame
# ---------------------------------------------------------------------------
def wire_tick_hud(bp):
    eg = bel.find_graph(bp, "EventGraph")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    tick = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() != "K2Node_Event":
            continue
        if any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n)):
            tick = n
            break
    if not tick:
        log("NO Tick")
        return False

    # Walk to end of Tick chain
    last_then = find_pin(tick, "then", "Output")
    cur = tick
    seen = set()
    while last_then:
        cps = conn(last_then)
        if not cps:
            break
        nxt = cps[0].get_owning_node()
        if id(nxt) in seen:
            break
        seen.add(id(nxt))
        # If already UpdateFarmHUD at end, done
        if title(nxt) == "UpdateFarmHUD":
            log("Tick already ends with UpdateFarmHUD")
            return True
        nt = find_pin(nxt, "then", "Output")
        if not nt:
            # leaf without then - insert after if possible? break and append new from last_then of previous
            break
        last_then = nt
        cur = nxt

    log("Tick chain end=" + title(cur))

    # Avoid duplicate: if any UpdateFarmHUD already connected from Tick path, skip
    # Just append a new call at end
    upd = ge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:UpdateFarmHUD")
    if not upd:
        # try create_node
        try:
            upd = ge.create_node_from_name("UpdateFarmHUD", unreal.Vector2D(0, 0), [])
        except Exception as e:
            log("add UpdateFarmHUD fail " + str(e))
            return False
    bel.set_node_pos(upd, pos(2200, 600))
    connect(last_then, find_pin(upd, "execute", "Input"), "tick->upd")
    log("Tick -> UpdateFarmHUD")
    return True

# ---------------------------------------------------------------------------
# 4) Ensure BeginPlay still calls UpdateFarmHUD (already does, just verify)
# ---------------------------------------------------------------------------
def verify_beginplay(bp):
    eg = bel.find_graph(bp, "EventGraph")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    begin = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() != "K2Node_Event":
            continue
        if any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n)):
            continue
        begin = n
        break
    thenp = find_pin(begin, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in conn(thenp)]
    seen = set()
    found = False
    log("=== BeginPlay ===")
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in seen or d > 12:
            continue
        seen.add(id(cur))
        t = title(cur)
        log("  " * d + t)
        if t == "UpdateFarmHUD":
            found = True
        tp = find_pin(cur, "then", "Output")
        if tp:
            for c in conn(tp):
                queue.append((c.get_owning_node(), d + 1))
    if not found:
        log("BeginPlay missing UpdateFarmHUD - re-append")
        # find Set GridManagerRef
        set_gm = None
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_VariableSet" and find_pin(n, "GridManagerRef"):
                set_gm = n
                break
        if set_gm:
            last = find_pin(set_gm, "then", "Output")
            # if something already connected, walk to end
            cur = set_gm
            seen2 = set()
            while True:
                tp = find_pin(cur, "then", "Output")
                cps = conn(tp) if tp else []
                if not cps:
                    last = tp
                    break
                nxt = cps[0].get_owning_node()
                if id(nxt) in seen2:
                    last = tp
                    break
                seen2.add(id(nxt))
                cur = nxt
            upd = ge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:UpdateFarmHUD")
            bel.set_node_pos(upd, pos(1600, -200))
            connect(last, find_pin(upd, "execute", "Input"), "bp->upd")
            found = True
    log("BeginPlay has UpdateFarmHUD=" + str(found))
    return found

# ---------------------------------------------------------------------------
def main():
    # Enable screen messages
    try:
        unreal.SystemLibrary.execute_console_command(None, "EnableAllScreenMessages")
        log("EnableAllScreenMessages")
    except Exception as e:
        log("console " + str(e))

    umg_ok = False
    try:
        umg_ok = try_build_umg()
    except Exception as e:
        log("UMG exception " + str(e))

    bp = unreal.load_asset(CHAR)
    patch_update_farm_hud(bp)
    try:
        bel.compile_blueprint(bp)
        log("compile after patch")
    except Exception as e:
        log("compile1 " + str(e))

    verify_beginplay(bp)
    wire_tick_hud(bp)

    try:
        bel.compile_blueprint(bp)
        log("compile final")
    except Exception as e:
        log("compile final " + str(e))

    # Check UpdateFarmHUD errors
    ug = bel.find_graph(bp, "UpdateFarmHUD")
    uge = unreal.BlueprintGraphEditor.get_graph_editor(ug)
    try:
        errs = list(uge.list_nodes_with_errors())
        log("UpdateFarmHUD errs=" + str(len(errs)))
        for n in errs:
            log("  ERR " + title(n))
    except Exception as e:
        log(str(e))

    # Dump PrintString pins after patch
    for n in uge.list_all_nodes():
        if title(n) == "PrintString":
            for p in bel.list_all_pins(n):
                try:
                    val = p.get_pin_value()
                except Exception:
                    val = "?"
                log("Print pin {}={!r} links={}".format(p.get_pin_name(), val, len(conn(p))))

    eg = bel.find_graph(bp, "EventGraph")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    try:
        errs = list(ge.list_nodes_with_errors())
        log("EG errs=" + str(len(errs)))
        for n in errs[:12]:
            log("  ERR " + title(n))
    except Exception as e:
        log(str(e))

    # Force save
    unreal.EditorAssetLibrary.save_asset(CHAR, only_if_is_dirty=False)
    if unreal.EditorAssetLibrary.does_asset_exist(WBP):
        unreal.EditorAssetLibrary.save_asset(WBP, only_if_is_dirty=False)
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("save_dirty ok")
    except Exception as e:
        log("save_dirty " + str(e))
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        log("level saved")
    except Exception as e:
        log("level " + str(e))

    # CDO defaults
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        for prop in ("Money", "SeedCount", "CropCount", "TomatoSellPrice"):
            log("CDO {}={}".format(prop, cdo.get_editor_property(prop)))
    except Exception as e:
        log("CDO " + str(e))

    log("DONE umg_ok={} — Play should show yellow *** Money/Seeds/Crops (top) + above head".format(umg_ok))

main()
