# -*- coding: utf-8 -*-
"""Day/night cycle (VISIBLE lighting) + auto growth on BP_GridManager.

- DayLengthSeconds=75 (~1.25 min/day)
- Tick advances TimeOfDay; wrap -> CurrentDay++ + AdvanceDayGrowth
- AdvanceDayGrowth: ForLoop all cells, GrowCell (Watered->Ready)
- ApplyDayNightVisuals: rotate DirectionalLight + strong intensity/color swing
- HUD PrintString Key=FarmDay "Day N"
Manual G still works. No IMC/Blocked/airwall changes.
"""
import unreal

TAG = "[DAY_CYCLE]"
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
DAY_LENGTH = 75.0
FOR_LOOP = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop"


def log(m):
    s = TAG + " " + str(m)
    unreal.log(s)
    print(s)


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def make_pin(text):
    p = unreal.EdGraphPinType()
    p.import_text(text)
    return p


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    want = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


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
        log("set fail {} : {}".format(label, e))
        return False


def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()


def var_names(bp):
    return [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]


def call(ge, path, x, y):
    n = ge.add_call_function_node(path)
    if n:
        bel.set_node_pos(n, pos(x, y))
    else:
        log("call FAIL " + path)
    return n


def ret_pin(node):
    return find_pin(node, "ReturnValue", "Output") or find_pin(node, "Return", "Output") or find_pin(node, "Result", "Output")


def ensure_vars(bp):
    specs = [
        ("CurrentDay", '(PinCategory="int",PinSubCategory="")'),
        ("TimeOfDay", '(PinCategory="real",PinSubCategory="")'),
        ("DayLengthSeconds", '(PinCategory="real",PinSubCategory="")'),
        ("SunActor", '(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/Engine.Actor")'),
        ("SkyLightActor", '(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/Engine.Actor")'),
    ]
    names = var_names(bp)
    for name, pin_text in specs:
        if name in names:
            log("var exists " + name)
            continue
        ok = bel.add_member_variable(bp, name, make_pin(pin_text))
        log("add var {} -> {}".format(name, ok))


def set_defaults(bp):
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        cdo.set_editor_property("CurrentDay", 1)
        cdo.set_editor_property("TimeOfDay", 0.25)
        cdo.set_editor_property("DayLengthSeconds", DAY_LENGTH)
        log("CDO Day={} TOD={} Len={}".format(
            cdo.get_editor_property("CurrentDay"),
            cdo.get_editor_property("TimeOfDay"),
            cdo.get_editor_property("DayLengthSeconds")))
    except Exception as e:
        log("CDO fail " + str(e))


def clear_fn(ge):
    entry = None
    kill = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            kill.append(n)
    if kill:
        ge.remove_nodes(kill)
    return entry


def ensure_fn(bp, name):
    graphs = [str(g) for g in bel.list_graph_names(bp)]
    if name not in graphs:
        bel.add_function_graph(bp, name)
        log("added fn " + name)
    else:
        log("fn exists " + name)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, name))
    entry = clear_fn(ge)
    return ge, entry


def build_advance_day_growth(bp):
    ge, entry = ensure_fn(bp, "AdvanceDayGrowth")
    if not entry:
        return False
    bel.set_node_pos(entry, pos(0, 0))

    get_w = ge.add_get_member_variable_node("GridWidth")
    get_h = ge.add_get_member_variable_node("GridHeight")
    bel.set_node_pos(get_w, pos(0, 160))
    bel.set_node_pos(get_h, pos(0, 240))

    mul = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_IntInt", 220, 180)
    sub = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_IntInt", 450, 180)
    connect(find_pin(get_w, "GridWidth", "Output"), find_pin(mul, "A", "Input"), "w*")
    connect(find_pin(get_h, "GridHeight", "Output"), find_pin(mul, "B", "Input"), "h*")
    connect(ret_pin(mul), find_pin(sub, "A", "Input"), "mul-")
    set_val(find_pin(sub, "B", "Input"), "1", "sub1")

    for_n = ge.create_node_from_name("Utilities|FlowControl|ForLoop", unreal.Vector2D(700, 0), [])
    if not for_n:
        for_n = ge.add_macro_node(FOR_LOOP)
    if not for_n:
        log("FATAL ForLoop")
        return False
    bel.set_node_pos(for_n, pos(700, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(for_n, "execute", "Input"), "e->for")
    set_val(find_pin(for_n, "FirstIndex", "Input"), "0", "first")
    connect(ret_pin(sub), find_pin(for_n, "LastIndex", "Input"), "last")

    get_w2 = ge.add_get_member_variable_node("GridWidth")
    bel.set_node_pos(get_w2, pos(900, 220))
    idx = find_pin(for_n, "Index", "Output")

    div = call(ge, "/Script/Engine.KismetMathLibrary:Divide_IntInt", 1100, 160)
    mod = call(ge, "/Script/Engine.KismetMathLibrary:Percent_IntInt", 1100, 280)
    connect(idx, find_pin(div, "A", "Input"), "idx/")
    connect(find_pin(get_w2, "GridWidth", "Output"), find_pin(div, "B", "Input"), "w/")
    connect(idx, find_pin(mod, "A", "Input"), "idx%")
    connect(find_pin(get_w2, "GridWidth", "Output"), find_pin(mod, "B", "Input"), "w%")

    grow = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GrowCell", 1400, 40)
    connect(find_pin(for_n, "LoopBody", "Output"), find_pin(grow, "execute", "Input"), "body->grow")
    connect(ret_pin(mod), find_pin(grow, "GridX", "Input") or find_pin(grow, "Grid X", "Input"), "gx")
    connect(ret_pin(div), find_pin(grow, "GridY", "Input") or find_pin(grow, "Grid Y", "Input"), "gy")

    ret = ge.add_return_node()
    bel.set_node_pos(ret, pos(1400, 320))
    connect(find_pin(for_n, "Completed", "Output"), find_pin(ret, "execute", "Input"), "done")
    log("AdvanceDayGrowth OK")
    return True


def build_apply_day_night(bp):
    """Strong day/night: intensity 0.15..8, color blue->warm, pitch 15..-70, yaw spins."""
    ge, entry = ensure_fn(bp, "ApplyDayNightVisuals")
    if not entry:
        return False
    bel.set_node_pos(entry, pos(0, 0))

    get_tod = ge.add_get_member_variable_node("TimeOfDay")
    bel.set_node_pos(get_tod, pos(0, 160))

    # sun = Sin((TOD - 0.25) * 2PI)  peak at noon 0.5
    sub = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", 250, 160)
    connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(sub, "A", "Input"), "tod-")
    set_val(find_pin(sub, "B", "Input"), "0.25", "0.25")

    mul = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 500, 160)
    connect(ret_pin(sub), find_pin(mul, "A", "Input"), "*2pi")
    set_val(find_pin(mul, "B", "Input"), "6.283185", "2pi")

    sinn = call(ge, "/Script/Engine.KismetMathLibrary:Sin", 750, 160)
    connect(ret_pin(mul), find_pin(sinn, "A", "Input"), "sin")

    # DayAmount 0..1 (night clamped)
    day = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1000, 160)
    connect(ret_pin(sinn), find_pin(day, "Value", "Input"), "sun")
    set_val(find_pin(day, "InRangeA", "Input"), "0.0", "inA")
    set_val(find_pin(day, "InRangeB", "Input"), "1.0", "inB")
    set_val(find_pin(day, "OutRangeA", "Input"), "0.0", "outA")
    set_val(find_pin(day, "OutRangeB", "Input"), "1.0", "outB")

    # Intensity: night 0.15 -> day 8.0 (very obvious)
    inten = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1280, 40)
    connect(ret_pin(day), find_pin(inten, "Value", "Input"), "d->I")
    set_val(find_pin(inten, "InRangeA", "Input"), "0.0", "iA")
    set_val(find_pin(inten, "InRangeB", "Input"), "1.0", "iB")
    set_val(find_pin(inten, "OutRangeA", "Input"), "0.15", "nightI")
    set_val(find_pin(inten, "OutRangeB", "Input"), "8.0", "dayI")

    # Pitch: night +20 (low) -> day -75 (high sun)
    pitch = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1280, 220)
    connect(ret_pin(day), find_pin(pitch, "Value", "Input"), "d->P")
    set_val(find_pin(pitch, "InRangeA", "Input"), "0.0", "pA")
    set_val(find_pin(pitch, "InRangeB", "Input"), "1.0", "pB")
    set_val(find_pin(pitch, "OutRangeA", "Input"), "20.0", "nightP")
    set_val(find_pin(pitch, "OutRangeB", "Input"), "-75.0", "dayP")

    # Yaw = TOD * 360
    yaw = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 250, 320)
    connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(yaw, "A", "Input"), "tod*yaw")
    set_val(find_pin(yaw, "B", "Input"), "360.0", "360")

    # Colors: deep night blue -> warm noon
    night = call(ge, "/Script/Engine.KismetMathLibrary:MakeColor", 1000, 400)
    dayc = call(ge, "/Script/Engine.KismetMathLibrary:MakeColor", 1000, 560)
    set_val(find_pin(night, "R", "Input"), "0.15", "nR")
    set_val(find_pin(night, "G", "Input"), "0.22", "nG")
    set_val(find_pin(night, "B", "Input"), "0.85", "nB")
    set_val(find_pin(night, "A", "Input"), "1.0", "nA")
    set_val(find_pin(dayc, "R", "Input"), "1.0", "dR")
    set_val(find_pin(dayc, "G", "Input"), "0.92", "dG")
    set_val(find_pin(dayc, "B", "Input"), "0.75", "dB")
    set_val(find_pin(dayc, "A", "Input"), "1.0", "dA")

    lerp = call(ge, "/Script/Engine.KismetMathLibrary:LinearColorLerp", 1280, 420)
    connect(ret_pin(night), find_pin(lerp, "A", "Input"), "cA")
    connect(ret_pin(dayc), find_pin(lerp, "B", "Input"), "cB")
    connect(ret_pin(day), find_pin(lerp, "Alpha", "Input"), "cAlpha")

    make_rot = call(ge, "/Script/Engine.KismetMathLibrary:MakeRotator", 1550, 200)
    connect(ret_pin(pitch), find_pin(make_rot, "Pitch", "Input"), "pitch")
    connect(ret_pin(yaw), find_pin(make_rot, "Yaw", "Input"), "yaw")
    set_val(find_pin(make_rot, "Roll", "Input"), "0.0", "roll")

    get_sun = ge.add_get_member_variable_node("SunActor")
    bel.set_node_pos(get_sun, pos(1550, 40))

    isv = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 1750, 40)
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(isv, "Object", "Input"), "valid")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(1950, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
    connect(ret_pin(isv), find_pin(br, "Condition", "Input"), "cond")

    set_rot = call(ge, "/Script/Engine.Actor:K2_SetActorRotation", 2200, 0)
    connect(find_pin(br, "then", "Output"), find_pin(set_rot, "execute", "Input"), "br->rot")
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(set_rot, "self", "Input"), "sun self")
    connect(ret_pin(make_rot), find_pin(set_rot, "NewRotation", "Input"), "newrot")
    set_val(find_pin(set_rot, "bTeleportPhysics", "Input"), "true", "tele")

    get_comp = call(ge, "/Script/Engine.Actor:GetComponentByClass", 2200, 200)
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(get_comp, "self", "Input"), "sun comp")
    set_val(find_pin(get_comp, "ComponentClass", "Input"), "/Script/Engine.DirectionalLightComponent", "DLComp")

    set_i = call(ge, "/Script/Engine.LightComponent:SetIntensity", 2550, 0)
    connect(find_pin(set_rot, "then", "Output"), find_pin(set_i, "execute", "Input"), "rot->I")
    connect(ret_pin(get_comp), find_pin(set_i, "self", "Input"), "comp->I")
    connect(ret_pin(inten), find_pin(set_i, "NewIntensity", "Input"), "Ival")

    set_c = call(ge, "/Script/Engine.LightComponent:SetLightColor", 2850, 0)
    connect(find_pin(set_i, "then", "Output"), find_pin(set_c, "execute", "Input"), "I->C")
    connect(ret_pin(get_comp), find_pin(set_c, "self", "Input"), "comp->C")
    connect(ret_pin(lerp), find_pin(set_c, "NewLightColor", "Input"), "Cval")

    # SkyLight intensity swing (optional)
    get_sky = ge.add_get_member_variable_node("SkyLightActor")
    bel.set_node_pos(get_sky, pos(2850, 220))
    isv2 = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 3050, 220)
    connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(isv2, "Object", "Input"), "sky valid")
    br2 = ge.add_branch_node()
    bel.set_node_pos(br2, pos(3250, 0))
    connect(find_pin(set_c, "then", "Output"), find_pin(br2, "execute", "Input"), "C->br2")
    connect(ret_pin(isv2), find_pin(br2, "Condition", "Input"), "skycond")

    sky_inten = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 3050, 360)
    connect(ret_pin(day), find_pin(sky_inten, "Value", "Input"), "d->skyI")
    set_val(find_pin(sky_inten, "InRangeA", "Input"), "0.0", "sA")
    set_val(find_pin(sky_inten, "InRangeB", "Input"), "1.0", "sB")
    set_val(find_pin(sky_inten, "OutRangeA", "Input"), "0.05", "skyNight")
    set_val(find_pin(sky_inten, "OutRangeB", "Input"), "1.0", "skyDay")

    get_sky_comp = call(ge, "/Script/Engine.Actor:GetComponentByClass", 3450, 80)
    connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(get_sky_comp, "self", "Input"), "sky self")
    set_val(find_pin(get_sky_comp, "ComponentClass", "Input"), "/Script/Engine.SkyLightComponent", "SkyComp")

    set_si = call(ge, "/Script/Engine.LightComponent:SetIntensity", 3700, 0)
    connect(find_pin(br2, "then", "Output"), find_pin(set_si, "execute", "Input"), "br2->sI")
    connect(ret_pin(get_sky_comp), find_pin(set_si, "self", "Input"), "skycomp->I")
    connect(ret_pin(sky_inten), find_pin(set_si, "NewIntensity", "Input"), "skyIval")

    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(4000, 0))
    connect(find_pin(set_si, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "sI->ret")

    ret_nosky = ge.add_return_node()
    bel.set_node_pos(ret_nosky, pos(3450, 280))
    connect(find_pin(br2, "else", "Output"), find_pin(ret_nosky, "execute", "Input"), "nosky")

    ret_skip = ge.add_return_node()
    bel.set_node_pos(ret_skip, pos(2200, 400))
    connect(find_pin(br, "else", "Output"), find_pin(ret_skip, "execute", "Input"), "nosun")

    log("ApplyDayNightVisuals OK")
    return True


def find_event(ge, want):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_Event" and want.lower() in title(n).lower():
            return n
    return None


def make_day_hud(ge, x, y, exec_from, label):
    get_d = ge.add_get_member_variable_node("CurrentDay")
    bel.set_node_pos(get_d, pos(x, y + 180))
    to_s = call(ge, "/Script/Engine.KismetStringLibrary:Conv_IntToString", x + 200, y + 180)
    connect(find_pin(get_d, "CurrentDay", "Output"), find_pin(to_s, "InInt", "Input"), label + "d2s")
    ap = call(ge, "/Script/Engine.KismetStringLibrary:Concat_StrStr", x + 450, y + 180)
    set_val(find_pin(ap, "A", "Input"), "Day ", label + "A")
    connect(ret_pin(to_s), find_pin(ap, "B", "Input"), label + "B")
    pr = call(ge, "/Script/Engine.KismetSystemLibrary:PrintString", x + 700, y)
    connect(exec_from, find_pin(pr, "execute", "Input"), label + "exec")
    connect(ret_pin(ap), find_pin(pr, "InString", "Input"), label + "str")
    set_val(find_pin(pr, "Key", "Input"), "FarmDay", label + "key")
    set_val(find_pin(pr, "Duration", "Input"), "999.0", label + "dur")
    set_val(find_pin(pr, "TextColor", "Input"), "(R=1.000000,G=1.000000,B=0.150000,A=1.000000)", label + "col")
    set_val(find_pin(pr, "bPrintToScreen", "Input"), "true", label + "scr")
    return pr


def strip_old_day_nodes(ge):
    """Remove previously wired day-cycle nodes from EventGraph (idempotent rebuild)."""
    markers = (
        "Set SunActor", "Set SkyLightActor", "Set CurrentDay", "Set TimeOfDay",
        "ApplyDayNightVisuals", "AdvanceDayGrowth", "GetAllActorsOfClass",
    )
    # Also remove Tick chain if it points into day logic
    kill = []
    for n in ge.list_all_nodes():
        t = title(n)
        cls = n.get_class().get_name()
        if cls == "K2Node_Event":
            continue
        # Keep original BeginPlay PlotStates init nodes
        if t in ("Clear", "Add", "For Loop", "InitBlockedFromIndices") and cls in (
            "K2Node_CallArrayFunction", "K2Node_MacroInstance", "K2Node_CallFunction"
        ):
            # Only keep if NOT our second ForLoop for growth (those live in function graphs)
            # EventGraph For Loop is the PlotStates one — keep
            if t == "For Loop":
                continue
            if t in ("Clear", "Add", "InitBlockedFromIndices"):
                continue
        if any(m in t for m in markers):
            kill.append(n)
            continue
        if t.startswith("Set ") and any(v in t for v in ("SunActor", "SkyLight", "CurrentDay", "TimeOfDay", "DayLength")):
            kill.append(n)
            continue
        # PrintString with FarmDay key
        if t == "PrintString":
            kp = find_pin(n, "Key", "Input")
            try:
                if kp and kp.get_pin_value() == "FarmDay":
                    kill.append(n)
                    continue
            except Exception:
                pass
        # Orphan math used only by day — harder; leave if not connected from tick after break
    if kill:
        log("removing {} old day nodes".format(len(kill)))
        ge.remove_nodes(kill)

    # Break Tick then links so we can rewire
    tick = find_event(ge, "Tick")
    if tick:
        thenp = find_pin(tick, "then", "Output")
        if thenp:
            try:
                thenp.break_pin_links(False)
            except Exception:
                try:
                    thenp.break_pin_links()
                except Exception as e:
                    log("break tick " + str(e))


def wire_beginplay(bp):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    begin = find_event(ge, "BeginPlay")
    if not begin:
        log("no BeginPlay")
        return False

    # Find chain end from BeginPlay
    cur = begin
    seen = set()
    while True:
        tp = find_pin(cur, "then", "Output") or find_pin(cur, "Completed", "Output")
        if not tp:
            break
        links = list(tp.list_connected_pins() or [])
        if not links:
            break
        nxt = links[0].get_owning_node()
        if id(nxt) in seen:
            break
        # Stop before any leftover day nodes
        if any(m in title(nxt) for m in ("GetAllActorsOfClass", "Set SunActor", "ApplyDayNight")):
            # disconnect and use previous as end
            try:
                tp.break_pin_links(False)
            except Exception:
                try:
                    tp.break_pin_links()
                except Exception:
                    pass
            break
        seen.add(id(nxt))
        cur = nxt
    log("BeginPlay end=" + title(cur))

    bx, by = 400, -450

    # DirectionalLight
    get_all = call(ge, "/Script/Engine.GameplayStatics:GetAllActorsOfClass", bx, by)
    set_val(find_pin(get_all, "ActorClass", "Input"), "/Script/Engine.DirectionalLight", "DL class")
    connect(find_pin(cur, "then", "Output") or find_pin(cur, "Completed", "Output"),
            find_pin(get_all, "execute", "Input"), "end->getDL")

    arr = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", bx + 320, by)  # pure
    # Array_Get is pure — no exec. Wire data only.
    connect(find_pin(get_all, "OutActors", "Output"), find_pin(arr, "TargetArray", "Input"), "actors")
    set_val(find_pin(arr, "Index", "Input"), "0", "i0")

    set_sun = ge.add_set_member_variable_node("SunActor")
    bel.set_node_pos(set_sun, pos(bx + 600, by))
    connect(find_pin(get_all, "then", "Output"), find_pin(set_sun, "execute", "Input"), "get->setsun")
    connect(find_pin(arr, "Item", "Output"), find_pin(set_sun, "SunActor", "Input"), "item sun")

    # SkyLight
    get_sky = call(ge, "/Script/Engine.GameplayStatics:GetAllActorsOfClass", bx + 900, by)
    set_val(find_pin(get_sky, "ActorClass", "Input"), "/Script/Engine.SkyLight", "Sky class")
    connect(find_pin(set_sun, "then", "Output"), find_pin(get_sky, "execute", "Input"), "sun->getsky")
    arr2 = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", bx + 1180, by)
    connect(find_pin(get_sky, "OutActors", "Output"), find_pin(arr2, "TargetArray", "Input"), "skyactors")
    set_val(find_pin(arr2, "Index", "Input"), "0", "si0")

    set_sky = ge.add_set_member_variable_node("SkyLightActor")
    bel.set_node_pos(set_sky, pos(bx + 1450, by))
    connect(find_pin(get_sky, "then", "Output"), find_pin(set_sky, "execute", "Input"), "getsky->set")
    connect(find_pin(arr2, "Item", "Output"), find_pin(set_sky, "SkyLightActor", "Input"), "item sky")

    set_day = ge.add_set_member_variable_node("CurrentDay")
    bel.set_node_pos(set_day, pos(bx + 1750, by))
    connect(find_pin(set_sky, "then", "Output"), find_pin(set_day, "execute", "Input"), "sky->day")
    set_val(find_pin(set_day, "CurrentDay", "Input"), "1", "day1")

    set_tod = ge.add_set_member_variable_node("TimeOfDay")
    bel.set_node_pos(set_tod, pos(bx + 2050, by))
    connect(find_pin(set_day, "then", "Output"), find_pin(set_tod, "execute", "Input"), "day->tod")
    set_val(find_pin(set_tod, "TimeOfDay", "Input"), "0.25", "tod025")

    set_len = ge.add_set_member_variable_node("DayLengthSeconds")
    bel.set_node_pos(set_len, pos(bx + 2350, by))
    connect(find_pin(set_tod, "then", "Output"), find_pin(set_len, "execute", "Input"), "tod->len")
    set_val(find_pin(set_len, "DayLengthSeconds", "Input"), str(DAY_LENGTH), "len75")

    apply = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:ApplyDayNightVisuals", bx + 2650, by)
    connect(find_pin(set_len, "then", "Output"), find_pin(apply, "execute", "Input"), "len->apply")
    make_day_hud(ge, bx + 2900, by, find_pin(apply, "then", "Output"), "BP")
    log("BeginPlay wired")
    return True


def wire_tick(bp):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    tick = find_event(ge, "Tick")
    if not tick:
        log("no Tick")
        return False

    # Clean any dangling tick targets already broken in strip
    bx, by = 0, 520

    get_tod = ge.add_get_member_variable_node("TimeOfDay")
    get_len = ge.add_get_member_variable_node("DayLengthSeconds")
    bel.set_node_pos(get_tod, pos(bx + 180, by + 200))
    bel.set_node_pos(get_len, pos(bx + 180, by + 280))

    div = call(ge, "/Script/Engine.KismetMathLibrary:Divide_DoubleDouble", bx + 450, by + 220)
    ds = find_pin(tick, "DeltaSeconds", "Output")
    connect(ds, find_pin(div, "A", "Input"), "ds/")
    connect(find_pin(get_len, "DayLengthSeconds", "Output"), find_pin(div, "B", "Input"), "len/")

    addn = call(ge, "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", bx + 720, by + 200)
    connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(addn, "A", "Input"), "tod+")
    connect(ret_pin(div), find_pin(addn, "B", "Input"), "frac+")

    cmp = call(ge, "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble", bx + 980, by + 200)
    connect(ret_pin(addn), find_pin(cmp, "A", "Input"), "cmpA")
    set_val(find_pin(cmp, "B", "Input"), "1.0", "cmp1")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(bx + 1220, by))
    connect(find_pin(tick, "then", "Output"), find_pin(br, "execute", "Input"), "tick->br")
    connect(ret_pin(cmp), find_pin(br, "Condition", "Input"), "cond")

    # FALSE: set TOD, apply, HUD
    set_f = ge.add_set_member_variable_node("TimeOfDay")
    bel.set_node_pos(set_f, pos(bx + 1500, by + 220))
    connect(find_pin(br, "else", "Output"), find_pin(set_f, "execute", "Input"), "else->set")
    connect(ret_pin(addn), find_pin(set_f, "TimeOfDay", "Input"), "newtod")
    apply_f = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:ApplyDayNightVisuals", bx + 1800, by + 220)
    connect(find_pin(set_f, "then", "Output"), find_pin(apply_f, "execute", "Input"), "set->applyF")
    make_day_hud(ge, bx + 2100, by + 220, find_pin(apply_f, "then", "Output"), "TF")

    # TRUE: wrap, day++, growth, apply, HUD
    sub1 = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", bx + 1500, by - 60)
    connect(ret_pin(addn), find_pin(sub1, "A", "Input"), "wrapA")
    set_val(find_pin(sub1, "B", "Input"), "1.0", "wrap1")

    set_t = ge.add_set_member_variable_node("TimeOfDay")
    bel.set_node_pos(set_t, pos(bx + 1780, by - 120))
    connect(find_pin(br, "then", "Output"), find_pin(set_t, "execute", "Input"), "then->setT")
    connect(ret_pin(sub1), find_pin(set_t, "TimeOfDay", "Input"), "wrapped")

    get_day = ge.add_get_member_variable_node("CurrentDay")
    bel.set_node_pos(get_day, pos(bx + 1780, by + 40))
    add_day = call(ge, "/Script/Engine.KismetMathLibrary:Add_IntInt", bx + 2000, by + 40)
    connect(find_pin(get_day, "CurrentDay", "Output"), find_pin(add_day, "A", "Input"), "day+")
    set_val(find_pin(add_day, "B", "Input"), "1", "+1")

    set_day = ge.add_set_member_variable_node("CurrentDay")
    bel.set_node_pos(set_day, pos(bx + 2250, by - 120))
    connect(find_pin(set_t, "then", "Output"), find_pin(set_day, "execute", "Input"), "tod->day")
    connect(ret_pin(add_day), find_pin(set_day, "CurrentDay", "Input"), "newday")

    adv = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:AdvanceDayGrowth", bx + 2550, by - 120)
    connect(find_pin(set_day, "then", "Output"), find_pin(adv, "execute", "Input"), "day->adv")

    apply_t = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:ApplyDayNightVisuals", bx + 2850, by - 120)
    connect(find_pin(adv, "then", "Output"), find_pin(apply_t, "execute", "Input"), "adv->apply")
    make_day_hud(ge, bx + 3150, by - 120, find_pin(apply_t, "then", "Output"), "TT")

    log("Tick wired")
    return True


def ensure_lights_movable():
    try:
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    except Exception:
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for a in actors:
        cls = a.get_class().get_name()
        if cls in ("DirectionalLight", "SkyLight"):
            try:
                for c in a.get_components_by_class(unreal.LightComponentBase):
                    c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                    log("{} mobility=Movable inten={}".format(a.get_name(), c.get_editor_property("intensity")))
            except Exception as e:
                log("mobility {}: {}".format(a.get_name(), e))


def verify(bp):
    graphs = [str(g) for g in bel.list_graph_names(bp)]
    log("graphs has Advance={} Apply={}".format("AdvanceDayGrowth" in graphs, "ApplyDayNightVisuals" in graphs))
    names = var_names(bp)
    for v in ("CurrentDay", "TimeOfDay", "DayLengthSeconds", "SunActor", "SkyLightActor"):
        log("var {}={}".format(v, v in names))
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    tick = find_event(ge, "Tick")
    links = list(find_pin(tick, "then", "Output").list_connected_pins() or []) if tick else []
    log("Tick->" + str([title(c.get_owning_node()) for c in links]))


def main():
    log("=== start DayLengthSeconds={} ===".format(DAY_LENGTH))
    bp = unreal.load_asset(MGR)
    if not bp:
        log("FATAL no manager")
        return

    ensure_vars(bp)
    unreal.EditorAssetLibrary.save_asset(MGR)

    ok1 = build_advance_day_growth(bp)
    ok2 = build_apply_day_night(bp)
    log("fns ok adv={} apply={}".format(ok1, ok2))

    try:
        bel.compile_blueprint(bp)
        log("mid compile ok")
    except Exception as e:
        log("mid compile " + str(e))

    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    strip_old_day_nodes(ge)

    ok3 = wire_beginplay(bp)
    ok4 = wire_tick(bp)
    log("wire begin={} tick={}".format(ok3, ok4))

    try:
        bel.compile_blueprint(bp)
        log("final compile ok")
    except Exception as e:
        log("final compile " + str(e))

    set_defaults(bp)
    try:
        bel.compile_blueprint(bp)
        log("post-default compile ok")
    except Exception as e:
        log("post-default compile " + str(e))

    unreal.EditorAssetLibrary.save_asset(MGR)
    ensure_lights_movable()
    try:
        unreal.EditorLevelLibrary.save_current_level()
        log("level saved")
    except Exception as e:
        try:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
            log("level saved (subsys)")
        except Exception as e2:
            log("level save fail {} / {}".format(e, e2))

    verify(bp)
    log("=== DONE ===")


if __name__ == "__main__":
    main()
