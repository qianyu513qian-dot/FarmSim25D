# -*- coding: utf-8 -*-
"""Phase C: UpdateFarmHUD function + BeginPlay create/update + Plant seed check + Harvest money.

HUD: PrintString Key=FarmHUD (persistent on-screen). WBP_FarmHUD shell exists but
UE5.8 Python cannot set WidgetTree.RootWidget; TextBlocks need designer if upgrading later.
Does NOT touch camera/scene rotation.
"""
import unreal

TAG = "[INV_C] "
bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
WBP = "/Game/Farm/UI/WBP_FarmHUD"

def log(m):
    s = TAG + str(m)
    unreal.log(s)
    print(s)

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
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
        log("no pin " + label)
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, value))
    except Exception as e:
        log("set {} FAIL {}".format(label, e))

def conn_pins(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

def break_all(p, label=""):
    if not p:
        return
    try:
        p.break_pin_links()
        log("broke " + label)
    except Exception as e:
        log("break {} FAIL {}".format(label, e))

def build_update_farm_hud(bp):
    graphs = [str(g) for g in bel.list_graph_names(bp)]
    if "UpdateFarmHUD" in graphs:
        try:
            bel.remove_function_graph(bp, "UpdateFarmHUD")
            log("removed old UpdateFarmHUD")
        except Exception as e:
            log("remove UpdateFarmHUD: " + str(e))
            return False

    bel.add_function_graph(bp, "UpdateFarmHUD")
    graph = bel.find_graph(bp, "UpdateFarmHUD")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    if not ge:
        log("no GE UpdateFarmHUD")
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

    # Get Money / SeedCount / CropCount
    get_m = ge.add_get_member_variable_node("Money")
    bel.set_node_pos(get_m, pos(200, 200))
    get_s = ge.add_get_member_variable_node("SeedCount")
    bel.set_node_pos(get_s, pos(200, 320))
    get_c = ge.add_get_member_variable_node("CropCount")
    bel.set_node_pos(get_c, pos(200, 440))

    # Format: Money:{0}  Seeds:{1}  Crops:{2}
    fmt = ge.create_node_from_name("Utilities|String|Format", unreal.Vector2D(500, 200), [])
    # Prefer Format Text if available
    if not fmt:
        fmt = None
        for cand in (
            "Utilities|Text|Format Text",
            "Utilities|String|Format",
            "Format Text",
        ):
            try:
                fmt = ge.create_node_from_name(cand, unreal.Vector2D(500, 200), [])
                if fmt:
                    log("fmt via " + cand)
                    break
            except Exception:
                pass
    # Fallback: use Format Text node class via add if needed
    if not fmt:
        # Build with Append / Conv_IntToString chain instead
        log("no Format node - using Append chain")
        return build_update_hud_append(ge, entry, get_m, get_s, get_c)

    bel.set_node_pos(fmt, pos(500, 200))
    # Detect Format vs FormatText pins
    pins = [str(p.get_pin_name()) for p in bel.list_all_pins(fmt)]
    log("fmt pins=" + str(pins))
    # Set format string
    for pname in ("InPattern", "Format", "In Format"):
        p = find_pin(fmt, pname, "Input")
        if p:
            set_val(p, "Money: {0}   Seeds: {1}   Crops: {2}", "fmt")
            break
    # Argument pins - Format Text uses Argument_0 etc after setting pattern; Format string uses similar
    # Try connecting Money to first arg pin
    arg_pins = [p for p in bel.list_all_pins(fmt)
                if "input" in str(p.get_pin_direction()).lower()
                and str(p.get_pin_name()) not in ("InPattern", "Format", "In Format", "self")]
    log("fmt arg pins=" + str([p.get_pin_name() for p in arg_pins]))

    # Ensure wildcard args exist by setting pattern first then refreshing pins
    # Re-get pins after set
    arg_pins = []
    for p in bel.list_all_pins(fmt):
        pn = str(p.get_pin_name())
        if "input" in str(p.get_pin_direction()).lower() and pn not in ("InPattern", "Format", "In Format", "self"):
            arg_pins.append(p)

    gets = [get_m, get_s, get_c]
    names = ["Money", "SeedCount", "CropCount"]
    for i, gnode in enumerate(gets):
        if i >= len(arg_pins):
            break
        src = find_pin(gnode, names[i], "Output") or find_pin(gnode, "Output", "Output")
        # Variable get pins are usually named after variable
        if not src:
            outs = [p for p in bel.list_all_pins(gnode) if "output" in str(p.get_pin_direction()).lower()]
            src = outs[0] if outs else None
        connect(src, arg_pins[i], "arg{}".format(i))

    # Conv result to string if text
    result_pin = find_pin(fmt, "Result", "Output") or find_pin(fmt, "ReturnValue", "Output")
    print_n = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(print_n, pos(900, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(print_n, "execute", "Input"), "e->print")
    # If format returns Text, convert
    if result_pin:
        # try direct connect; if fails, insert conv
        in_str = find_pin(print_n, "InString", "Input")
        ok = connect(result_pin, in_str, "fmt->print")
        if not ok:
            conv = ge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_TextToString")
            if not conv:
                conv = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_TextToString")
            bel.set_node_pos(conv, pos(750, 200))
            connect(result_pin, find_pin(conv, "InText", "Input") or find_pin(conv, "In Text", "Input"), "fmt->conv")
            connect(find_pin(conv, "ReturnValue", "Output"), in_str, "conv->print")
    set_val(find_pin(print_n, "Key", "Input"), "FarmHUD", "key")
    set_val(find_pin(print_n, "Duration", "Input"), "0.0", "dur")  # 0 = sticky with key
    set_val(find_pin(print_n, "bPrintToScreen", "Input"), "true", "screen")
    set_val(find_pin(print_n, "TextColor", "Input"), "(R=1.0,G=1.0,B=0.2,A=1.0)", "yellow")

    ret = ge.add_return_node()
    bel.set_node_pos(ret, pos(1200, 0))
    connect(find_pin(print_n, "then", "Output"), find_pin(ret, "execute", "Input"), "print->ret")
    log("UpdateFarmHUD built")
    return True

def build_update_hud_append(ge, entry, get_m, get_s, get_c):
    """Fallback: Conv_IntToString + Append."""
    def get_out(gnode, name):
        p = find_pin(gnode, name, "Output")
        if p:
            return p
        outs = [p for p in bel.list_all_pins(gnode) if "output" in str(p.get_pin_direction()).lower()]
        return outs[0] if outs else None

    def to_str(ge, src_pin, x, y, label):
        n = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
        bel.set_node_pos(n, pos(x, y))
        connect(src_pin, find_pin(n, "InInt", "Input"), label)
        return find_pin(n, "ReturnValue", "Output")

    sm = to_str(ge, get_out(get_m, "Money"), 450, 200, "m")
    ss = to_str(ge, get_out(get_s, "SeedCount"), 450, 320, "s")
    sc = to_str(ge, get_out(get_c, "CropCount"), 450, 440, "c")

    # Build "Money: " + m + "  Seeds: " + s + "  Crops: " + c
    def append(ge, a_val, b_pin, x, y, label, a_is_literal=True):
        n = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(n, pos(x, y))
        if a_is_literal:
            set_val(find_pin(n, "A", "Input"), a_val, label + ".A")
        else:
            connect(a_val, find_pin(n, "A", "Input"), label + ".A")
        connect(b_pin, find_pin(n, "B", "Input"), label + ".B")
        return find_pin(n, "ReturnValue", "Output")

    p1 = append(ge, "Money: ", sm, 700, 200, "p1")
    # need Seeds part: p1 + "  Seeds: " then + ss
    nmid = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(nmid, pos(900, 200))
    connect(p1, find_pin(nmid, "A", "Input"), "p1a")
    set_val(find_pin(nmid, "B", "Input"), "   Seeds: ", "seeds_lit")
    p2 = find_pin(nmid, "ReturnValue", "Output")
    p3 = append(ge, p2, ss, 1100, 200, "p3", a_is_literal=False)
    nmid2 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(nmid2, pos(1300, 200))
    connect(p3, find_pin(nmid2, "A", "Input"), "p3a")
    set_val(find_pin(nmid2, "B", "Input"), "   Crops: ", "crops_lit")
    p4 = find_pin(nmid2, "ReturnValue", "Output")
    p5 = append(ge, p4, sc, 1500, 200, "p5", a_is_literal=False)

    print_n = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(print_n, pos(1750, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(print_n, "execute", "Input"), "e->print")
    connect(p5, find_pin(print_n, "InString", "Input"), "str->print")
    set_val(find_pin(print_n, "Key", "Input"), "FarmHUD", "key")
    set_val(find_pin(print_n, "Duration", "Input"), "0.0", "dur")
    set_val(find_pin(print_n, "bPrintToScreen", "Input"), "true", "screen")
    set_val(find_pin(print_n, "TextColor", "Input"), "(R=1.0,G=1.0,B=0.2,A=1.0)", "yellow")
    ret = ge.add_return_node()
    bel.set_node_pos(ret, pos(2000, 0))
    connect(find_pin(print_n, "then", "Output"), find_pin(ret, "execute", "Input"), "print->ret")
    log("UpdateFarmHUD append built")
    return True

def wire_beginplay_hud(bp):
    eg = bel.find_graph(bp, "EventGraph")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    nodes = list(ge.list_all_nodes())

    begin = None
    for n in nodes:
        if n.get_class().get_name() != "K2Node_Event":
            continue
        if any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n)):
            continue
        begin = n
        break
    if not begin:
        log("NO BeginPlay")
        return False

    # Find end of BeginPlay chain
    thenp = find_pin(begin, "then", "Output")
    cur = begin
    visited = set()
    last_then = thenp
    while True:
        cps = conn_pins(last_then)
        if not cps:
            break
        nxt = cps[0].get_owning_node()
        if id(nxt) in visited:
            break
        visited.add(id(nxt))
        nt = find_pin(nxt, "then", "Output")
        if not nt:
            break
        last_then = nt
        cur = nxt
    log("BeginPlay chain end node=" + cur.get_name())

    # If UpdateFarmHUD already called from BeginPlay, skip
    for n in nodes:
        # check for existing call
        pass

    # Place CreateWidget + AddToViewport + Set FarmHUDWidget + UpdateFarmHUD at end
    # Create Widget
    create = None
    try:
        create = ge.add_call_function_node("/Script/UMG.WidgetBlueprintLibrary:Create")
    except Exception:
        create = None
    if not create:
        # K2Node_CreateWidget
        try:
            create = ge.create_node_from_name("User Interface|Widget|Create Widget", unreal.Vector2D(0, 0), [])
        except Exception as e:
            log("create widget node fail " + str(e))
    if create:
        bel.set_node_pos(create, pos(2400, -400))
        # set class
        class_pin = find_pin(create, "Class", "Input")
        if class_pin:
            set_val(class_pin, "WBP_FarmHUD_C'/Game/Farm/UI/WBP_FarmHUD.WBP_FarmHUD_C'", "class")
            # try alternate
            try:
                class_pin.set_default_value("/Game/Farm/UI/WBP_FarmHUD.WBP_FarmHUD_C")
            except Exception:
                pass
        connect(last_then, find_pin(create, "execute", "Input"), "bp->create")
        addv = ge.add_call_function_node("/Script/UMG.UserWidget:AddToViewport")
        bel.set_node_pos(addv, pos(2700, -400))
        connect(find_pin(create, "then", "Output"), find_pin(addv, "execute", "Input"), "create->add")
        connect(find_pin(create, "ReturnValue", "Output"), find_pin(addv, "self", "Input"), "widget->self")
        # Set FarmHUDWidget
        set_w = ge.add_set_member_variable_node("FarmHUDWidget")
        bel.set_node_pos(set_w, pos(3000, -400))
        connect(find_pin(addv, "then", "Output"), find_pin(set_w, "execute", "Input"), "add->set")
        connect(find_pin(create, "ReturnValue", "Output"), find_pin(set_w, "FarmHUDWidget", "Input"), "w->var")
        last_then = find_pin(set_w, "then", "Output")
        log("CreateWidget chain added")
    else:
        log("SKIP CreateWidget - will Print HUD only")

    # Call UpdateFarmHUD
    upd = ge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:UpdateFarmHUD")
    bel.set_node_pos(upd, pos(3300, -400))
    connect(last_then, find_pin(upd, "execute", "Input"), "->upd")
    log("BeginPlay -> UpdateFarmHUD")
    return True

def find_ia_chain(ge, ia_short):
    """Return (ia_node, w2g, cellop, branch) for given IA_* name."""
    nodes = list(ge.list_all_nodes())
    ia_node = None
    for n in nodes:
        p = find_pin(n, "InputAction", "Output") or find_pin(n, "InputAction", None)
        if not p:
            continue
        try:
            val = p.get_pin_value() or ""
        except Exception:
            val = ""
        if ia_short in val:
            ia_node = n
            break
    if not ia_node:
        return None
    started = find_pin(ia_node, "Started", "Output")
    w2g = conn_pins(started)[0].get_owning_node()
    cell = conn_pins(find_pin(w2g, "then", "Output"))[0].get_owning_node()
    br = conn_pins(find_pin(cell, "then", "Output"))[0].get_owning_node()
    return ia_node, w2g, cell, br

def find_print_by_string(ge, text):
    for n in ge.list_all_nodes():
        p = find_pin(n, "InString", "Input")
        if not p:
            continue
        try:
            if p.get_pin_value() == text:
                return n
        except Exception:
            pass
    return None

def wire_plant_seeds(bp):
    eg = bel.find_graph(bp, "EventGraph")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    chain = find_ia_chain(ge, "IA_Plant")
    if not chain:
        log("NO plant chain")
        return False
    ia, w2g, cell, br = chain
    log("Plant chain ok cell={} br={}".format(cell.get_name(), br.get_name()))

    planted = find_print_by_string(ge, "Planted!")
    cannot = find_print_by_string(ge, "Cannot plant")

    # --- Insert seed check between WorldToGrid and PlantCell ---
    w2g_then = find_pin(w2g, "then", "Output")
    cell_exec = find_pin(cell, "execute", "Input")
    # break existing
    break_all(w2g_then, "w2g.then")
    # also break cell_exec inbound by reconnecting fresh

    get_seeds = ge.add_get_member_variable_node("SeedCount")
    bel.set_node_pos(get_seeds, pos(200, 2200))
    # Greater (SeedCount > 0)
    gt = ge.create_node_from_name("Utilities|Operators|>", unreal.Vector2D(400, 2200), [])
    if not gt:
        gt = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_IntInt")
    bel.set_node_pos(gt, pos(400, 2200))
    seed_out = find_pin(get_seeds, "SeedCount", "Output")
    if not seed_out:
        outs = [p for p in bel.list_all_pins(get_seeds) if "output" in str(p.get_pin_direction()).lower()]
        seed_out = outs[0] if outs else None
    connect(seed_out, find_pin(gt, "A", "Input"), "seed>A")
    set_val(find_pin(gt, "B", "Input"), "0", "gt.B")

    seed_br = ge.add_branch_node()
    bel.set_node_pos(seed_br, pos(650, 2000))
    connect(w2g_then, find_pin(seed_br, "execute", "Input"), "w2g->seedbr")
    connect(find_pin(gt, "ReturnValue", "Output"), find_pin(seed_br, "Condition", "Input"), "gt->cond")
    connect(find_pin(seed_br, "then", "Output"), cell_exec, "seedok->plant")

    # else: Cannot plant (no seeds)
    if cannot:
        connect(find_pin(seed_br, "else", "Output"), find_pin(cannot, "execute", "Input"), "noseed->cannot")
    else:
        pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, pos(900, 2300))
        set_val(find_pin(pr, "InString", "Input"), "Cannot plant", "noseed")
        connect(find_pin(seed_br, "else", "Output"), find_pin(pr, "execute", "Input"), "noseed->pr")

    # --- On PlantCell success: SeedCount-- , UpdateFarmHUD, Print Planted! ---
    br_then = find_pin(br, "then", "Output")
    break_all(br_then, "plantbr.then")

    get_s2 = ge.add_get_member_variable_node("SeedCount")
    bel.set_node_pos(get_s2, pos(200, 2500))
    sub = ge.create_node_from_name("Utilities|Operators|Subtract", unreal.Vector2D(450, 2500), [])
    if not sub:
        sub = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_IntInt")
    bel.set_node_pos(sub, pos(450, 2500))
    s2_out = find_pin(get_s2, "SeedCount", "Output")
    if not s2_out:
        outs = [p for p in bel.list_all_pins(get_s2) if "output" in str(p.get_pin_direction()).lower()]
        s2_out = outs[0] if outs else None
    connect(s2_out, find_pin(sub, "A", "Input"), "s-A")
    set_val(find_pin(sub, "B", "Input"), "1", "s-B")
    set_s = ge.add_set_member_variable_node("SeedCount")
    bel.set_node_pos(set_s, pos(700, 2450))
    connect(br_then, find_pin(set_s, "execute", "Input"), "ok->setseed")
    connect(find_pin(sub, "ReturnValue", "Output"), find_pin(set_s, "SeedCount", "Input"), "newseed")

    upd = ge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:UpdateFarmHUD")
    bel.set_node_pos(upd, pos(1000, 2450))
    connect(find_pin(set_s, "then", "Output"), find_pin(upd, "execute", "Input"), "set->upd")

    if not planted:
        planted = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(planted, pos(1300, 2450))
        set_val(find_pin(planted, "InString", "Input"), "Planted!", "planted")
    connect(find_pin(upd, "then", "Output"), find_pin(planted, "execute", "Input"), "upd->planted")
    log("Plant inventory wired")
    return True

def wire_harvest_reward(bp):
    eg = bel.find_graph(bp, "EventGraph")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    chain = find_ia_chain(ge, "IA_Harvest")
    if not chain:
        log("NO harvest chain")
        return False
    ia, w2g, cell, br = chain
    harvested = find_print_by_string(ge, "Harvested!")
    br_then = find_pin(br, "then", "Output")
    # Break Branch.then -> Harvested
    break_all(br_then, "harvbr.then")

    # CropCount++
    get_c = ge.add_get_member_variable_node("CropCount")
    bel.set_node_pos(get_c, pos(200, 2800))
    addc = ge.create_node_from_name("Utilities|Operators|Add", unreal.Vector2D(450, 2800), [])
    if not addc:
        addc = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_IntInt")
    bel.set_node_pos(addc, pos(450, 2800))
    c_out = find_pin(get_c, "CropCount", "Output")
    if not c_out:
        outs = [p for p in bel.list_all_pins(get_c) if "output" in str(p.get_pin_direction()).lower()]
        c_out = outs[0] if outs else None
    connect(c_out, find_pin(addc, "A", "Input"), "c+A")
    set_val(find_pin(addc, "B", "Input"), "1", "c+B")
    set_c = ge.add_set_member_variable_node("CropCount")
    bel.set_node_pos(set_c, pos(700, 2750))
    connect(br_then, find_pin(set_c, "execute", "Input"), "ok->setcrop")
    connect(find_pin(addc, "ReturnValue", "Output"), find_pin(set_c, "CropCount", "Input"), "newcrop")

    # Money += TomatoSellPrice
    get_m = ge.add_get_member_variable_node("Money")
    bel.set_node_pos(get_m, pos(200, 3000))
    get_p = ge.add_get_member_variable_node("TomatoSellPrice")
    bel.set_node_pos(get_p, pos(200, 3120))
    addm = ge.create_node_from_name("Utilities|Operators|Add", unreal.Vector2D(450, 3000), [])
    if not addm:
        addm = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_IntInt")
    bel.set_node_pos(addm, pos(450, 3000))
    m_out = find_pin(get_m, "Money", "Output")
    if not m_out:
        outs = [p for p in bel.list_all_pins(get_m) if "output" in str(p.get_pin_direction()).lower()]
        m_out = outs[0] if outs else None
    p_out = find_pin(get_p, "TomatoSellPrice", "Output")
    if not p_out:
        outs = [p for p in bel.list_all_pins(get_p) if "output" in str(p.get_pin_direction()).lower()]
        p_out = outs[0] if outs else None
    connect(m_out, find_pin(addm, "A", "Input"), "m+A")
    connect(p_out, find_pin(addm, "B", "Input"), "m+B")
    set_m = ge.add_set_member_variable_node("Money")
    bel.set_node_pos(set_m, pos(1000, 2750))
    connect(find_pin(set_c, "then", "Output"), find_pin(set_m, "execute", "Input"), "crop->money")
    connect(find_pin(addm, "ReturnValue", "Output"), find_pin(set_m, "Money", "Input"), "newmoney")

    upd = ge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:UpdateFarmHUD")
    bel.set_node_pos(upd, pos(1300, 2750))
    connect(find_pin(set_m, "then", "Output"), find_pin(upd, "execute", "Input"), "money->upd")

    if not harvested:
        harvested = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(harvested, pos(1600, 2750))
        set_val(find_pin(harvested, "InString", "Input"), "Harvested!", "harv")
    connect(find_pin(upd, "then", "Output"), find_pin(harvested, "execute", "Input"), "upd->harv")
    log("Harvest reward wired")
    return True

def main():
    bp = unreal.load_asset(CHAR)
    ok1 = build_update_farm_hud(bp)
    try:
        bel.compile_blueprint(bp)
        log("compile after UpdateFarmHUD")
    except Exception as e:
        log("compile1 " + str(e))

    ok2 = wire_beginplay_hud(bp)
    ok3 = wire_plant_seeds(bp)
    ok4 = wire_harvest_reward(bp)

    try:
        bel.compile_blueprint(bp)
        log("compile final")
    except Exception as e:
        log("compile final " + str(e))
    unreal.EditorAssetLibrary.save_asset(CHAR)
    if unreal.EditorAssetLibrary.does_asset_exist(WBP):
        unreal.EditorAssetLibrary.save_asset(WBP)
    # save level
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("save_dirty ok")
    except Exception as e:
        log("save_dirty " + str(e))
    try:
        eas = unreal.EditorAssetLibrary
        # force save character disk
        eas.save_asset(CHAR, only_if_is_dirty=False)
    except Exception as e:
        log(str(e))
    log("RESULT update={} begin={} plant={} harvest={}".format(ok1, ok2, ok3, ok4))

main()
