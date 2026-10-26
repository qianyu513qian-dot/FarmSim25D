# -*- coding: utf-8 -*-
"""
phase_fix_sun_teleport_grow.py
Fix two FarmSim25D bugs:
1) Sun yaw teleport at day wrap: Yaw = TimeOfDay * 360 (continuous; 360≡0).
   Keep elev=Sin((TOD-0.25)*2π) for Pitch/Intensity/Sky/Color (night floor).
2) Day-wrap growth without watering: rebuild AdvanceDayGrowth to ONLY promote
   Watered(3)->Ready/Grown(4)+VisualizeCell(4). Do NOT call GrowCell.
   Also rebuild GrowCell so Equal is forced to Watered(3)->Ready(4).

Does NOT touch Day counter wiring, IMC, grid size, airwalls, BlockedIndices.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
FOR_LOOP = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop"

# Day/night tunables (match phase_fix_day_night_light.py floors/colors)
MIN_NIGHT_INTENSITY = 2.0
MAX_DAY_INTENSITY = 8.0
NIGHT_PITCH = -18.0
DAY_PITCH = -62.0
SKY_NIGHT = 0.70
SKY_DAY = 1.80
NIGHT_RGB = (0.55, 0.65, 0.85)
DAY_RGB = (1.00, 0.94, 0.78)

WATERED = "3"
READY = "4"


def log(m):
    unreal.log("[FIX_SG] " + str(m))
    print("[FIX_SG] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


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
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def set_val(pin, value, label=""):
    if not pin:
        log("no " + label)
        return False
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r} (now {!r})".format(label, value, pin.get_pin_value()))
        return True
    except Exception as e:
        log("set fail {} {}".format(label, e))
        return False


def ret(node):
    return find_pin(node, "ReturnValue", "Output") or find_pin(node, "Return", "Output")


def call(ge, path, x, y):
    n = ge.add_call_function_node(path)
    if n:
        bel.set_node_pos(n, pos(x, y))
    else:
        log("FAIL " + path)
    return n


def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()


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
        log("cleared {} nodes".format(len(kill)))
    return entry


def make_int_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="int")')
    return p


def make_bool_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="bool")')
    return p


# ---------------------------------------------------------------------------
# Bug 1: ApplyDayNightVisuals — continuous yaw
# ---------------------------------------------------------------------------
def rebuild_apply_day_night(bp):
    log("=== rebuild ApplyDayNightVisuals (yaw=TOD*360) ===")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    entry = clear_fn(ge)
    if not entry:
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n
    bel.set_node_pos(entry, pos(0, 0))

    get_tod = ge.add_get_member_variable_node("TimeOfDay")
    bel.set_node_pos(get_tod, pos(0, 180))

    # elev = Sin((TOD-0.25)*2PI)
    sub = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", 260, 180)
    connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(sub, "A", "Input"), "tod-")
    set_val(find_pin(sub, "B", "Input"), "0.25", "0.25")

    mul = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 520, 180)
    connect(ret(sub), find_pin(mul, "A", "Input"), "*2pi")
    set_val(find_pin(mul, "B", "Input"), "6.283185", "2pi")

    sinn = call(ge, "/Script/Engine.KismetMathLibrary:Sin", 780, 180)
    connect(ret(mul), find_pin(sinn, "A", "Input"), "sin")

    # DayAmt for color lerp (night when elev<=0)
    day = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1040, 180)
    connect(ret(sinn), find_pin(day, "Value", "Input"), "elev->day")
    set_val(find_pin(day, "InRangeA", "Input"), "0.0", "dayInA")
    set_val(find_pin(day, "InRangeB", "Input"), "1.0", "dayInB")
    set_val(find_pin(day, "OutRangeA", "Input"), "0.0", "dayOutA")
    set_val(find_pin(day, "OutRangeB", "Input"), "1.0", "dayOutB")

    inten = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1320, 40)
    connect(ret(sinn), find_pin(inten, "Value", "Input"), "elev->I")
    set_val(find_pin(inten, "InRangeA", "Input"), "-1.0", "iInA")
    set_val(find_pin(inten, "InRangeB", "Input"), "1.0", "iInB")
    set_val(find_pin(inten, "OutRangeA", "Input"), str(MIN_NIGHT_INTENSITY), "MinNightI")
    set_val(find_pin(inten, "OutRangeB", "Input"), str(MAX_DAY_INTENSITY), "MaxDayI")

    pitch = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1320, 240)
    connect(ret(sinn), find_pin(pitch, "Value", "Input"), "elev->P")
    set_val(find_pin(pitch, "InRangeA", "Input"), "-1.0", "pInA")
    set_val(find_pin(pitch, "InRangeB", "Input"), "1.0", "pInB")
    set_val(find_pin(pitch, "OutRangeA", "Input"), str(NIGHT_PITCH), "nightP")
    set_val(find_pin(pitch, "OutRangeB", "Input"), str(DAY_PITCH), "dayP")

    # Yaw continuous full orbit — no 35→185 wrap teleport
    yaw = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 520, 360)
    connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(yaw, "A", "Input"), "tod*yaw")
    set_val(find_pin(yaw, "B", "Input"), "360.0", "yaw360")

    night = call(ge, "/Script/Engine.KismetMathLibrary:MakeColor", 1040, 420)
    dayc = call(ge, "/Script/Engine.KismetMathLibrary:MakeColor", 1040, 580)
    set_val(find_pin(night, "R", "Input"), str(NIGHT_RGB[0]), "nR")
    set_val(find_pin(night, "G", "Input"), str(NIGHT_RGB[1]), "nG")
    set_val(find_pin(night, "B", "Input"), str(NIGHT_RGB[2]), "nB")
    set_val(find_pin(night, "A", "Input"), "1.0", "nA")
    set_val(find_pin(dayc, "R", "Input"), str(DAY_RGB[0]), "dR")
    set_val(find_pin(dayc, "G", "Input"), str(DAY_RGB[1]), "dG")
    set_val(find_pin(dayc, "B", "Input"), str(DAY_RGB[2]), "dB")
    set_val(find_pin(dayc, "A", "Input"), "1.0", "dA")

    lerp = call(ge, "/Script/Engine.KismetMathLibrary:LinearColorLerp", 1320, 440)
    connect(ret(night), find_pin(lerp, "A", "Input"), "cA")
    connect(ret(dayc), find_pin(lerp, "B", "Input"), "cB")
    connect(ret(day), find_pin(lerp, "Alpha", "Input"), "cAl")

    make_rot = call(ge, "/Script/Engine.KismetMathLibrary:MakeRotator", 1600, 220)
    connect(ret(pitch), find_pin(make_rot, "Pitch", "Input"), "pitch")
    connect(ret(yaw), find_pin(make_rot, "Yaw", "Input"), "yaw")
    set_val(find_pin(make_rot, "Roll", "Input"), "0.0", "roll")

    get_sun = ge.add_get_member_variable_node("SunActor")
    bel.set_node_pos(get_sun, pos(1600, 40))
    isv = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 1820, 40)
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(isv, "Object", "Input"), "sun valid")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(2050, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
    connect(ret(isv), find_pin(br, "Condition", "Input"), "cond")

    set_rot = call(ge, "/Script/Engine.Actor:K2_SetActorRotation", 2300, 0)
    connect(find_pin(br, "then", "Output"), find_pin(set_rot, "execute", "Input"), "br->rot")
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(set_rot, "self", "Input"), "sunself")
    connect(ret(make_rot), find_pin(set_rot, "NewRotation", "Input"), "newrot")
    set_val(find_pin(set_rot, "bTeleportPhysics", "Input"), "true", "tele")

    get_comp = call(ge, "/Script/Engine.Actor:GetComponentByClass", 2300, 200)
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(get_comp, "self", "Input"), "suncomp")
    set_val(find_pin(get_comp, "ComponentClass", "Input"), "/Script/Engine.DirectionalLightComponent", "DL")

    set_i = call(ge, "/Script/Engine.LightComponent:SetIntensity", 2650, 0)
    connect(find_pin(set_rot, "then", "Output"), find_pin(set_i, "execute", "Input"), "rot->I")
    connect(ret(get_comp), find_pin(set_i, "self", "Input"), "compI")
    connect(ret(inten), find_pin(set_i, "NewIntensity", "Input"), "Ival")

    set_c = call(ge, "/Script/Engine.LightComponent:SetLightColor", 2950, 0)
    connect(find_pin(set_i, "then", "Output"), find_pin(set_c, "execute", "Input"), "I->C")
    connect(ret(get_comp), find_pin(set_c, "self", "Input"), "compC")
    connect(ret(lerp), find_pin(set_c, "NewLightColor", "Input"), "Cval")

    sky_i = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 2650, 360)
    connect(ret(sinn), find_pin(sky_i, "Value", "Input"), "elev->sky")
    set_val(find_pin(sky_i, "InRangeA", "Input"), "-1.0", "sInA")
    set_val(find_pin(sky_i, "InRangeB", "Input"), "1.0", "sInB")
    set_val(find_pin(sky_i, "OutRangeA", "Input"), str(SKY_NIGHT), "skyNight")
    set_val(find_pin(sky_i, "OutRangeB", "Input"), str(SKY_DAY), "skyDay")

    get_sky = ge.add_get_member_variable_node("SkyLightActor")
    bel.set_node_pos(get_sky, pos(2950, 220))
    isv2 = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 3180, 220)
    connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(isv2, "Object", "Input"), "skyv")

    br2 = ge.add_branch_node()
    bel.set_node_pos(br2, pos(3400, 0))
    connect(find_pin(set_c, "then", "Output"), find_pin(br2, "execute", "Input"), "C->br2")
    connect(ret(isv2), find_pin(br2, "Condition", "Input"), "skycond")

    get_sc = call(ge, "/Script/Engine.Actor:GetComponentByClass", 3600, 80)
    connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(get_sc, "self", "Input"), "skyself")
    set_val(find_pin(get_sc, "ComponentClass", "Input"), "/Script/Engine.SkyLightComponent", "SkyComp")

    set_si = call(ge, "/Script/Engine.SkyLightComponent:SetIntensity", 3900, 0)
    connect(find_pin(br2, "then", "Output"), find_pin(set_si, "execute", "Input"), "br2->sI")
    connect(ret(get_sc), find_pin(set_si, "self", "Input"), "scI")
    connect(ret(sky_i), find_pin(set_si, "NewIntensity", "Input"), "sIval")

    set_sc = call(ge, "/Script/Engine.SkyLightComponent:SetLightColor", 4200, 0)
    connect(find_pin(set_si, "then", "Output"), find_pin(set_sc, "execute", "Input"), "sI->sC")
    connect(ret(get_sc), find_pin(set_sc, "self", "Input"), "scC")
    connect(ret(lerp), find_pin(set_sc, "NewLightColor", "Input"), "sCval")

    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(4500, 0))
    connect(find_pin(set_sc, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "ok")

    ret_nosky = ge.add_return_node()
    bel.set_node_pos(ret_nosky, pos(3600, 280))
    connect(find_pin(br2, "else", "Output"), find_pin(ret_nosky, "execute", "Input"), "nosky")

    ret_skip = ge.add_return_node()
    bel.set_node_pos(ret_skip, pos(2300, 400))
    connect(find_pin(br, "else", "Output"), find_pin(ret_skip, "execute", "Input"), "nosun")

    errs = ge.list_nodes_with_errors()
    log("ApplyDayNightVisuals errors={}".format(len(errs)))
    return len(errs) == 0


# ---------------------------------------------------------------------------
# Bug 2a: AdvanceDayGrowth — Watered-only inline (no GrowCell)
# ---------------------------------------------------------------------------
def rebuild_advance_day_growth(bp):
    log("=== rebuild AdvanceDayGrowth (Watered->Ready only, no GrowCell) ===")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "AdvanceDayGrowth"))
    entry = clear_fn(ge)
    if not entry:
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n
    bel.set_node_pos(entry, pos(0, 0))

    get_w = ge.add_get_member_variable_node("GridWidth")
    get_h = ge.add_get_member_variable_node("GridHeight")
    bel.set_node_pos(get_w, pos(0, 160))
    bel.set_node_pos(get_h, pos(0, 240))

    mul = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_IntInt", 220, 180)
    sub = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_IntInt", 450, 180)
    connect(find_pin(get_w, "GridWidth", "Output"), find_pin(mul, "A", "Input"), "w")
    connect(find_pin(get_h, "GridHeight", "Output"), find_pin(mul, "B", "Input"), "h")
    connect(ret(mul), find_pin(sub, "A", "Input"), "mul")
    set_val(find_pin(sub, "B", "Input"), "1", "1")

    for_n = ge.create_node_from_name("Utilities|FlowControl|ForLoop", unreal.Vector2D(700, 0), [])
    if not for_n:
        for_n = ge.add_macro_node(FOR_LOOP)
    if not for_n:
        log("FATAL ForLoop")
        return False
    bel.set_node_pos(for_n, pos(700, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(for_n, "execute", "Input"), "e")
    set_val(find_pin(for_n, "FirstIndex", "Input"), "0", "first")
    connect(ret(sub), find_pin(for_n, "LastIndex", "Input"), "last")

    get_w2 = ge.add_get_member_variable_node("GridWidth")
    bel.set_node_pos(get_w2, pos(900, 260))
    idx = find_pin(for_n, "Index", "Output")

    # GridX = index % width, GridY = index / width
    div = call(ge, "/Script/Engine.KismetMathLibrary:Divide_IntInt", 1100, 160)
    mod = call(ge, "/Script/Engine.KismetMathLibrary:Percent_IntInt", 1100, 280)
    connect(idx, find_pin(div, "A", "Input"), "idx/")
    connect(find_pin(get_w2, "GridWidth", "Output"), find_pin(div, "B", "Input"), "w/")
    connect(idx, find_pin(mod, "A", "Input"), "idx%")
    connect(find_pin(get_w2, "GridWidth", "Output"), find_pin(mod, "B", "Input"), "w%")

    # PlotStates[index]
    get_plots = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_plots, pos(1100, 40))
    get_at = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", 1350, 40)
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(get_at, "TargetArray", "Input"), "arr")
    connect(idx, find_pin(get_at, "Index", "Input"), "getidx")

    # Equal Watered(3)
    eq = call(ge, "/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte", 1600, 40)
    connect(find_pin(get_at, "Item", "Output"), find_pin(eq, "A", "Input"), "eqA")
    set_val(find_pin(eq, "B", "Input"), WATERED, "eq.B=Watered")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(1850, 0))
    connect(find_pin(for_n, "LoopBody", "Output"), find_pin(br, "execute", "Input"), "body->br")
    connect(ret(eq), find_pin(br, "Condition", "Input"), "eq->br")

    # Set Ready(4)
    set_at = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Set", 2100, 0)
    connect(find_pin(br, "then", "Output"), find_pin(set_at, "execute", "Input"), "br->set")
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(set_at, "TargetArray", "Input"), "setarr")
    connect(idx, find_pin(set_at, "Index", "Input"), "setidx")
    set_val(find_pin(set_at, "Item", "Input"), READY, "set.Item=Ready")
    set_val(find_pin(set_at, "bSizeToFit", "Input"), "true", "fit")

    # VisualizeCell(GridX, GridY, 4)
    viz = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:VisualizeCell", 2400, 0)
    connect(find_pin(set_at, "then", "Output"), find_pin(viz, "execute", "Input"), "set->viz")
    connect(ret(mod), find_pin(viz, "GridX", "Input") or find_pin(viz, "Grid X", "Input"), "viz.gx")
    connect(ret(div), find_pin(viz, "GridY", "Input") or find_pin(viz, "Grid Y", "Input"), "viz.gy")
    set_val(find_pin(viz, "State", "Input"), READY, "viz.State=Ready")

    # Completed -> return
    rn = ge.add_return_node()
    bel.set_node_pos(rn, pos(1850, 320))
    connect(find_pin(for_n, "Completed", "Output"), find_pin(rn, "execute", "Input"), "done")

    # Verify no GrowCell node left
    for n in ge.list_all_nodes():
        if title(n) == "GrowCell":
            log("WARN: GrowCell still present in AdvanceDayGrowth")

    errs = ge.list_nodes_with_errors()
    log("AdvanceDayGrowth errors={}".format(len(errs)))
    for e in errs:
        log("  err node=" + title(e))
    return len(errs) == 0


# ---------------------------------------------------------------------------
# Bug 2b: GrowCell — force Watered(3)->Ready(4)+VisualizeCell
# ---------------------------------------------------------------------------
def rebuild_grow_cell(bp):
    log("=== rebuild GrowCell (Watered->Ready only) ===")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
    entry = clear_fn(ge)
    if not entry:
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n

    # Ensure inputs/outputs exist
    if find_pin(entry, "GridX", "Output") is None:
        ge.add_graph_input_parameter("GridX", make_int_pin())
        ge.add_graph_input_parameter("GridY", make_int_pin())
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n
    has_succ = False
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionResult" and find_pin(n, "Success"):
            has_succ = True
    if not has_succ:
        try:
            ge.add_graph_output_parameter("Success", make_bool_pin())
        except Exception as ex:
            log("add Success out: " + str(ex))
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n

    bel.set_node_pos(entry, pos(0, 0))

    # Entry -> IsValidCell -> Branch
    valid = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:IsValidCell", 250, 0)
    connect(find_pin(entry, "GridX", "Output"), find_pin(valid, "Grid X", "Input") or find_pin(valid, "GridX", "Input"), "gx-v")
    connect(find_pin(entry, "GridY", "Output"), find_pin(valid, "Grid Y", "Input") or find_pin(valid, "GridY", "Input"), "gy-v")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(520, 0))
    # Prefer exec chain Entry->IsValidCell->Branch if IsValidCell has exec
    iv_exec = find_pin(valid, "execute", "Input")
    if iv_exec:
        connect(find_pin(entry, "then", "Output"), iv_exec, "e->iv")
        connect(find_pin(valid, "then", "Output"), find_pin(br, "execute", "Input"), "iv->br")
    else:
        connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
    connect(ret(valid) or find_pin(valid, "Return Value", "Output"), find_pin(br, "Condition", "Input"), "valid")

    get_plots = ge.add_get_member_variable_node("PlotStates")
    bel.set_node_pos(get_plots, pos(520, 200))
    get_w = ge.add_get_member_variable_node("GridWidth")
    bel.set_node_pos(get_w, pos(520, 300))

    mul = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_IntInt", 780, 240)
    addn = call(ge, "/Script/Engine.KismetMathLibrary:Add_IntInt", 1000, 240)
    connect(find_pin(entry, "GridY", "Output"), find_pin(mul, "A", "Input"), "gy*")
    connect(find_pin(get_w, "GridWidth", "Output"), find_pin(mul, "B", "Input"), "*w")
    connect(ret(mul), find_pin(addn, "A", "Input"), "mul+")
    connect(find_pin(entry, "GridX", "Output"), find_pin(addn, "B", "Input"), "+gx")

    get_at = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", 1220, 200)
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(get_at, "TargetArray", "Input"), "arr")
    connect(ret(addn), find_pin(get_at, "Index", "Input"), "idx")

    eq = call(ge, "/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte", 1480, 200)
    connect(find_pin(get_at, "Item", "Output"), find_pin(eq, "A", "Input"), "eqA")
    set_val(find_pin(eq, "B", "Input"), WATERED, "eq.B=Watered")

    br2 = ge.add_branch_node()
    bel.set_node_pos(br2, pos(1720, 0))
    connect(find_pin(br, "then", "Output"), find_pin(br2, "execute", "Input"), "br->br2")
    connect(ret(eq), find_pin(br2, "Condition", "Input"), "eq->br2")

    set_at = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Set", 1980, 0)
    connect(find_pin(br2, "then", "Output"), find_pin(set_at, "execute", "Input"), "br2->set")
    connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(set_at, "TargetArray", "Input"), "setarr")
    connect(ret(addn), find_pin(set_at, "Index", "Input"), "setidx")
    set_val(find_pin(set_at, "Item", "Input"), READY, "set.Item=Ready")
    set_val(find_pin(set_at, "bSizeToFit", "Input"), "true", "fit")

    viz = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:VisualizeCell", 2260, 0)
    connect(find_pin(set_at, "then", "Output"), find_pin(viz, "execute", "Input"), "set->viz")
    connect(find_pin(entry, "GridX", "Output"), find_pin(viz, "GridX", "Input") or find_pin(viz, "Grid X", "Input"), "viz.gx")
    connect(find_pin(entry, "GridY", "Output"), find_pin(viz, "GridY", "Input") or find_pin(viz, "Grid Y", "Input"), "viz.gy")
    set_val(find_pin(viz, "State", "Input"), READY, "viz.State=Ready")

    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(2540, 0))
    connect(find_pin(viz, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "viz->ret")
    set_val(find_pin(ret_ok, "Success", "Input"), "true", "ok")

    ret_f1 = ge.add_return_node()
    bel.set_node_pos(ret_f1, pos(1720, 220))
    connect(find_pin(br, "else", "Output"), find_pin(ret_f1, "execute", "Input"), "br else")
    set_val(find_pin(ret_f1, "Success", "Input"), "false", "fail1")

    ret_f2 = ge.add_return_node()
    bel.set_node_pos(ret_f2, pos(1980, 280))
    connect(find_pin(br2, "else", "Output"), find_pin(ret_f2, "execute", "Input"), "br2 else")
    set_val(find_pin(ret_f2, "Success", "Input"), "false", "fail2")

    # Verify Equal B
    for n in ge.list_all_nodes():
        if "equal" in title(n).lower():
            bp_pin = find_pin(n, "B", "Input")
            log("GrowCell Equal.B verify={!r}".format(bp_pin.get_pin_value() if bp_pin else None))

    errs = ge.list_nodes_with_errors()
    log("GrowCell errors={}".format(len(errs)))
    for e in errs:
        log("  err node=" + title(e))
    return len(errs) == 0


def main():
    log("START")
    bp = unreal.load_asset(MGR)
    if not bp:
        log("NO BP_GridManager")
        return

    ok1 = rebuild_apply_day_night(bp)
    ok2 = rebuild_advance_day_growth(bp)
    ok3 = rebuild_grow_cell(bp)

    try:
        bel.compile_blueprint(bp)
        log("compile ok")
    except Exception as e:
        log("compile " + str(e))

    saved = unreal.EditorAssetLibrary.save_asset(MGR)
    log("save MGR={}".format(saved))

    # Post-verify
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    for n in ge.list_all_nodes():
        t = title(n)
        if "float * float" in t or "double * double" in t.lower() or t.startswith("float *"):
            for p in bel.list_all_pins(n):
                try:
                    v = p.get_pin_value()
                except Exception:
                    v = "?"
                if str(p.get_pin_name()) == "B" and "360" in str(v):
                    log("VERIFY yaw mul B={}".format(v))
        if "MapRangeClamped" in t:
            # ensure no 35/185 yaw map remains
            for p in bel.list_all_pins(n):
                try:
                    v = p.get_pin_value()
                except Exception:
                    v = "?"
                if str(v) in ("35.0", "185.0", "35", "185"):
                    log("WARN leftover yaw arc val {} on {}".format(v, t))

    ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "AdvanceDayGrowth"))
    has_grow = any(title(n) == "GrowCell" for n in ge2.list_all_nodes())
    has_viz = any(title(n) == "VisualizeCell" for n in ge2.list_all_nodes())
    eq_b = None
    for n in ge2.list_all_nodes():
        if "equal" in title(n).lower():
            bp_pin = find_pin(n, "B", "Input")
            eq_b = bp_pin.get_pin_value() if bp_pin else None
    log("VERIFY AdvanceDayGrowth GrowCell={} VisualizeCell={} Equal.B={!r}".format(has_grow, has_viz, eq_b))

    ge3 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
    for n in ge3.list_all_nodes():
        if "equal" in title(n).lower():
            bp_pin = find_pin(n, "B", "Input")
            log("VERIFY GrowCell Equal.B={!r}".format(bp_pin.get_pin_value() if bp_pin else None))

    log("DONE ok_sun={} ok_adv={} ok_grow={}".format(ok1, ok2, ok3))


if __name__ == "__main__":
    main()
