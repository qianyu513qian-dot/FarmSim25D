# -*- coding: utf-8 -*-
"""Phase D: wire BeginPlay + Tick; fix sky intensity; movable lights; save."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
DAY_LENGTH = 75.0

def log(m):
    unreal.log("[DAY_D] " + str(m)); print("[DAY_D] " + str(m))
def pos(x, y): return unreal.IntPoint(int(x), int(y))
def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()
def find_pin(node, name_substr, direction=None):
    if not node: return None
    want = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None
def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok
def set_val(pin, value, label=""):
    if not pin: log("no " + label); return False
    try:
        pin.set_pin_value(str(value)); log("set {}={!r}".format(label, value)); return True
    except Exception as e:
        log("set fail {} {}".format(label, e)); return False
def ret(node):
    return find_pin(node, "ReturnValue", "Output") or find_pin(node, "Return", "Output")
def call(ge, path, x, y):
    n = ge.add_call_function_node(path)
    if n: bel.set_node_pos(n, pos(x, y))
    else: log("FAIL " + path)
    return n
def find_event(ge, want):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_Event" and want.lower() in title(n).lower():
            return n
    return None

def make_day_hud(ge, x, y, exec_from, label):
    get_d = ge.add_get_member_variable_node("CurrentDay"); bel.set_node_pos(get_d, pos(x, y + 180))
    to_s = call(ge, "/Script/Engine.KismetStringLibrary:Conv_IntToString", x + 200, y + 180)
    connect(find_pin(get_d, "CurrentDay", "Output"), find_pin(to_s, "InInt", "Input"), label + "d2s")
    ap = call(ge, "/Script/Engine.KismetStringLibrary:Concat_StrStr", x + 450, y + 180)
    set_val(find_pin(ap, "A", "Input"), "Day ", label + "A")
    connect(ret(to_s), find_pin(ap, "B", "Input"), label + "B")
    pr = call(ge, "/Script/Engine.KismetSystemLibrary:PrintString", x + 700, y)
    connect(exec_from, find_pin(pr, "execute", "Input"), label + "exec")
    connect(ret(ap), find_pin(pr, "InString", "Input"), label + "str")
    set_val(find_pin(pr, "Key", "Input"), "FarmDay", label + "key")
    set_val(find_pin(pr, "Duration", "Input"), "999.0", label + "dur")
    set_val(find_pin(pr, "TextColor", "Input"), "(R=1.000000,G=1.000000,B=0.150000,A=1.000000)", label + "col")
    set_val(find_pin(pr, "bPrintToScreen", "Input"), "true", label + "scr")
    return pr

def fix_sky_branch(bp):
    """SkyLight SetIntensity self won't connect — route br2.then to Return instead."""
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    br2 = None
    set_si = None
    rets = []
    for n in ge.list_all_nodes():
        t = title(n)
        if t == "Branch":
            # prefer the one whose then goes to SetIntensity
            thenp = find_pin(n, "then", "Output")
            links = list(thenp.list_connected_pins() or []) if thenp else []
            if links and "SetIntensity" in title(links[0].get_owning_node()):
                br2 = n
                set_si = links[0].get_owning_node()
        if n.get_class().get_name() == "K2Node_FunctionResult":
            rets.append(n)
    if not br2:
        log("no sky branch to fix")
        return
    thenp = find_pin(br2, "then", "Output")
    try:
        thenp.break_pin_links(False)
    except Exception:
        try: thenp.break_pin_links()
        except Exception as e: log("break " + str(e))
    # pick a return or create
    target = rets[0] if rets else ge.add_return_node()
    connect(thenp, find_pin(target, "execute", "Input"), "sky then->ret")
    # remove broken set_si if present
    if set_si:
        try:
            ge.remove_nodes([set_si])
            log("removed broken sky SetIntensity")
        except Exception as e:
            log("rm set_si " + str(e))
    log("sky branch fixed")

bp = unreal.load_asset(MGR)
fix_sky_branch(bp)

ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

# Idempotent: if Set SunActor already exists, skip begin/tick rebuild
already = any(title(n) == "Set SunActor" for n in ge.list_all_nodes())
if already:
    log("day wiring already present — skip rewire")
else:
    begin = find_event(ge, "BeginPlay")
    tick = find_event(ge, "Tick")

    # Find BeginPlay chain end
    cur = begin
    seen = set()
    while True:
        tp = find_pin(cur, "then", "Output") or find_pin(cur, "Completed", "Output")
        if not tp: break
        links = list(tp.list_connected_pins() or [])
        if not links: break
        nxt = links[0].get_owning_node()
        if id(nxt) in seen: break
        seen.add(id(nxt)); cur = nxt
    log("BeginPlay end=" + title(cur))

    bx, by = 400, -450
    get_all = call(ge, "/Script/Engine.GameplayStatics:GetAllActorsOfClass", bx, by)
    set_val(find_pin(get_all, "ActorClass", "Input"), "/Script/Engine.DirectionalLight", "DL")
    connect(find_pin(cur, "then", "Output") or find_pin(cur, "Completed", "Output"),
            find_pin(get_all, "execute", "Input"), "end->DL")

    arr = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", bx + 320, by)
    connect(find_pin(get_all, "OutActors", "Output"), find_pin(arr, "TargetArray", "Input"), "actors")
    set_val(find_pin(arr, "Index", "Input"), "0", "i0")

    set_sun = ge.add_set_member_variable_node("SunActor"); bel.set_node_pos(set_sun, pos(bx + 600, by))
    connect(find_pin(get_all, "then", "Output"), find_pin(set_sun, "execute", "Input"), "->sun")
    connect(find_pin(arr, "Item", "Output"), find_pin(set_sun, "SunActor", "Input"), "item")

    get_sky = call(ge, "/Script/Engine.GameplayStatics:GetAllActorsOfClass", bx + 900, by)
    set_val(find_pin(get_sky, "ActorClass", "Input"), "/Script/Engine.SkyLight", "Sky")
    connect(find_pin(set_sun, "then", "Output"), find_pin(get_sky, "execute", "Input"), "sun->sky")
    arr2 = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", bx + 1180, by)
    connect(find_pin(get_sky, "OutActors", "Output"), find_pin(arr2, "TargetArray", "Input"), "skyA")
    set_val(find_pin(arr2, "Index", "Input"), "0", "si0")

    set_sky = ge.add_set_member_variable_node("SkyLightActor"); bel.set_node_pos(set_sky, pos(bx + 1450, by))
    connect(find_pin(get_sky, "then", "Output"), find_pin(set_sky, "execute", "Input"), "->setsky")
    connect(find_pin(arr2, "Item", "Output"), find_pin(set_sky, "SkyLightActor", "Input"), "skyitem")

    set_day = ge.add_set_member_variable_node("CurrentDay"); bel.set_node_pos(set_day, pos(bx + 1750, by))
    connect(find_pin(set_sky, "then", "Output"), find_pin(set_day, "execute", "Input"), "->day")
    set_val(find_pin(set_day, "CurrentDay", "Input"), "1", "day1")

    set_tod = ge.add_set_member_variable_node("TimeOfDay"); bel.set_node_pos(set_tod, pos(bx + 2050, by))
    connect(find_pin(set_day, "then", "Output"), find_pin(set_tod, "execute", "Input"), "->tod")
    set_val(find_pin(set_tod, "TimeOfDay", "Input"), "0.25", "tod")

    set_len = ge.add_set_member_variable_node("DayLengthSeconds"); bel.set_node_pos(set_len, pos(bx + 2350, by))
    connect(find_pin(set_tod, "then", "Output"), find_pin(set_len, "execute", "Input"), "->len")
    set_val(find_pin(set_len, "DayLengthSeconds", "Input"), str(DAY_LENGTH), "len")

    apply = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:ApplyDayNightVisuals", bx + 2650, by)
    connect(find_pin(set_len, "then", "Output"), find_pin(apply, "execute", "Input"), "->apply")
    make_day_hud(ge, bx + 2900, by, find_pin(apply, "then", "Output"), "BP")
    log("BeginPlay wired")

    # Tick
    thenp = find_pin(tick, "then", "Output")
    if thenp and list(thenp.list_connected_pins() or []):
        try: thenp.break_pin_links(False)
        except Exception:
            try: thenp.break_pin_links()
            except Exception as e: log("break tick " + str(e))

    bx, by = 0, 520
    get_tod = ge.add_get_member_variable_node("TimeOfDay"); bel.set_node_pos(get_tod, pos(bx + 180, by + 200))
    get_len = ge.add_get_member_variable_node("DayLengthSeconds"); bel.set_node_pos(get_len, pos(bx + 180, by + 280))
    div = call(ge, "/Script/Engine.KismetMathLibrary:Divide_DoubleDouble", bx + 450, by + 220)
    connect(find_pin(tick, "DeltaSeconds", "Output"), find_pin(div, "A", "Input"), "ds")
    connect(find_pin(get_len, "DayLengthSeconds", "Output"), find_pin(div, "B", "Input"), "len")
    addn = call(ge, "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", bx + 720, by + 200)
    connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(addn, "A", "Input"), "tod+")
    connect(ret(div), find_pin(addn, "B", "Input"), "frac")
    cmp = call(ge, "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble", bx + 980, by + 200)
    connect(ret(addn), find_pin(cmp, "A", "Input"), "cmpA")
    set_val(find_pin(cmp, "B", "Input"), "1.0", "1")
    br = ge.add_branch_node(); bel.set_node_pos(br, pos(bx + 1220, by))
    connect(find_pin(tick, "then", "Output"), find_pin(br, "execute", "Input"), "tick->br")
    connect(ret(cmp), find_pin(br, "Condition", "Input"), "cond")

    # else: set TOD, apply, HUD
    set_f = ge.add_set_member_variable_node("TimeOfDay"); bel.set_node_pos(set_f, pos(bx + 1500, by + 220))
    connect(find_pin(br, "else", "Output"), find_pin(set_f, "execute", "Input"), "else")
    connect(ret(addn), find_pin(set_f, "TimeOfDay", "Input"), "newtod")
    apply_f = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:ApplyDayNightVisuals", bx + 1800, by + 220)
    connect(find_pin(set_f, "then", "Output"), find_pin(apply_f, "execute", "Input"), "applyF")
    make_day_hud(ge, bx + 2100, by + 220, find_pin(apply_f, "then", "Output"), "TF")

    # then: wrap
    sub1 = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", bx + 1500, by - 60)
    connect(ret(addn), find_pin(sub1, "A", "Input"), "wrapA")
    set_val(find_pin(sub1, "B", "Input"), "1.0", "w1")
    set_t = ge.add_set_member_variable_node("TimeOfDay"); bel.set_node_pos(set_t, pos(bx + 1780, by - 120))
    connect(find_pin(br, "then", "Output"), find_pin(set_t, "execute", "Input"), "then")
    connect(ret(sub1), find_pin(set_t, "TimeOfDay", "Input"), "wrapped")

    get_day = ge.add_get_member_variable_node("CurrentDay"); bel.set_node_pos(get_day, pos(bx + 1780, by + 40))
    add_day = call(ge, "/Script/Engine.KismetMathLibrary:Add_IntInt", bx + 2000, by + 40)
    connect(find_pin(get_day, "CurrentDay", "Output"), find_pin(add_day, "A", "Input"), "day+")
    set_val(find_pin(add_day, "B", "Input"), "1", "+1")
    set_day = ge.add_set_member_variable_node("CurrentDay"); bel.set_node_pos(set_day, pos(bx + 2250, by - 120))
    connect(find_pin(set_t, "then", "Output"), find_pin(set_day, "execute", "Input"), "->day")
    connect(ret(add_day), find_pin(set_day, "CurrentDay", "Input"), "newday")

    adv = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:AdvanceDayGrowth", bx + 2550, by - 120)
    connect(find_pin(set_day, "then", "Output"), find_pin(adv, "execute", "Input"), "adv")
    apply_t = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:ApplyDayNightVisuals", bx + 2850, by - 120)
    connect(find_pin(adv, "then", "Output"), find_pin(apply_t, "execute", "Input"), "applyT")
    make_day_hud(ge, bx + 3150, by - 120, find_pin(apply_t, "then", "Output"), "TT")
    log("Tick wired")

try:
    bel.compile_blueprint(bp); log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

# Movable lights
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
    if a.get_class().get_name() in ("DirectionalLight", "SkyLight"):
        try:
            for c in a.get_components_by_class(unreal.LightComponentBase):
                c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                log("{} Movable inten={}".format(a.get_name(), c.get_editor_property("intensity")))
        except Exception as e:
            log("mob " + str(e))
try:
    unreal.EditorLevelLibrary.save_current_level(); log("level saved")
except Exception as e:
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level(); log("level saved2")
    except Exception as e2:
        log("level {} / {}".format(e, e2))

# verify
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
tick = find_event(ge, "Tick")
links = list(find_pin(tick, "then", "Output").list_connected_pins() or []) if tick else []
log("Tick->" + str([title(c.get_owning_node()) for c in links]))
log("graphs=" + str([str(g) for g in bel.list_graph_names(bp) if "Day" in str(g) or "Advance" in str(g) or "Apply" in str(g)]))
log("DONE DayLengthSeconds={}".format(DAY_LENGTH))