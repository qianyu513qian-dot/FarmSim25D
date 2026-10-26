# -*- coding: utf-8 -*-
"""
phase_fix_day_night_light.py
Tune FarmSim25D day/night lighting:
- Raise night brightness floor (DirectionalLight + SkyLight)
- Softer cool night tint (not near-black / pure blue)
- Realistic continuous sun arc (pitch noon high, dawn/dusk near horizon,
  night shallow moon angle; yaw east->west sweep, no full 360 spin)
Does NOT touch AdvanceDayGrowth / Day counter / IMC / grid / airwalls.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

# ---- Tunables (old -> new documented in log) ----
# OLD: Intensity night 0.15 -> day 8.0
# OLD: Pitch night +20 -> day -75
# OLD: Yaw = TOD * 360
# OLD: Night color (0.12, 0.18, 0.90); Day (1.0, 0.92, 0.70)
# OLD: Sky night 0.05 -> day 1.2 (and SetIntensity was disconnected)
MIN_NIGHT_INTENSITY = 2.0
MAX_DAY_INTENSITY = 8.0
NIGHT_PITCH = -18.0   # shallow moon-like (always from above)
DAY_PITCH = -62.0     # high noon
YAW_DAWN = 35.0       # east-ish
YAW_DUSK = 185.0      # west-ish (~150 deg sweep)
SKY_NIGHT = 0.70
SKY_DAY = 1.80
NIGHT_RGB = (0.55, 0.65, 0.85)
DAY_RGB = (1.00, 0.94, 0.78)


def log(m):
    unreal.log("[FIX_DN] " + str(m))
    print("[FIX_DN] " + str(m))


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
        log("set {}={!r}".format(label, value))
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


log("OLD: inten 0.15..8.0 | pitch +20..-75 | yaw TOD*360 | nightRGB(0.12,0.18,0.90) | sky 0.05..1.2 (disconnected)")
log("NEW: inten {:.1f}..{:.1f} | pitch {:.0f}..{:.0f} | yaw {:.0f}..{:.0f} | nightRGB{} | sky {:.2f}..{:.2f}".format(
    MIN_NIGHT_INTENSITY, MAX_DAY_INTENSITY, NIGHT_PITCH, DAY_PITCH,
    YAW_DAWN, YAW_DUSK, NIGHT_RGB, SKY_NIGHT, SKY_DAY))

bp = unreal.load_asset(MGR)
graphs = [str(g) for g in bel.list_graph_names(bp)]
if "ApplyDayNightVisuals" not in graphs:
    bel.add_function_graph(bp, "ApplyDayNightVisuals")

ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

# Clear all nodes except entry
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
if not entry:
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
bel.set_node_pos(entry, pos(0, 0))

# --- Math: elev = Sin((TOD-0.25)*2PI) ---
get_tod = ge.add_get_member_variable_node("TimeOfDay")
bel.set_node_pos(get_tod, pos(0, 180))

sub = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", 260, 180)
connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(sub, "A", "Input"), "tod-")
set_val(find_pin(sub, "B", "Input"), "0.25", "0.25")

mul = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 520, 180)
connect(ret(sub), find_pin(mul, "A", "Input"), "*2pi")
set_val(find_pin(mul, "B", "Input"), "6.283185", "2pi")

sinn = call(ge, "/Script/Engine.KismetMathLibrary:Sin", 780, 180)
connect(ret(mul), find_pin(sinn, "A", "Input"), "sin")
# elev = Sin(...) in [-1, 1]

# DayAmt = MapRangeClamped(elev, 0, 1, 0, 1)  for color lerp (night when elev<=0)
day = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1040, 180)
connect(ret(sinn), find_pin(day, "Value", "Input"), "elev->day")
set_val(find_pin(day, "InRangeA", "Input"), "0.0", "dayInA")
set_val(find_pin(day, "InRangeB", "Input"), "1.0", "dayInB")
set_val(find_pin(day, "OutRangeA", "Input"), "0.0", "dayOutA")
set_val(find_pin(day, "OutRangeB", "Input"), "1.0", "dayOutB")

# Intensity from elev continuously with night floor (never below MIN_NIGHT)
inten = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1320, 40)
connect(ret(sinn), find_pin(inten, "Value", "Input"), "elev->I")
set_val(find_pin(inten, "InRangeA", "Input"), "-1.0", "iInA")
set_val(find_pin(inten, "InRangeB", "Input"), "1.0", "iInB")
set_val(find_pin(inten, "OutRangeA", "Input"), str(MIN_NIGHT_INTENSITY), "MinNightI")
set_val(find_pin(inten, "OutRangeB", "Input"), str(MAX_DAY_INTENSITY), "MaxDayI")

# Pitch from elev: midnight shallow moon -> noon high (always negative = from above)
pitch = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1320, 240)
connect(ret(sinn), find_pin(pitch, "Value", "Input"), "elev->P")
set_val(find_pin(pitch, "InRangeA", "Input"), "-1.0", "pInA")
set_val(find_pin(pitch, "InRangeB", "Input"), "1.0", "pInB")
set_val(find_pin(pitch, "OutRangeA", "Input"), str(NIGHT_PITCH), "nightP")
set_val(find_pin(pitch, "OutRangeB", "Input"), str(DAY_PITCH), "dayP")

# Yaw: east->west sweep over TOD (no full spin)
yaw = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 520, 360)
connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(yaw, "Value", "Input"), "tod->yaw")
set_val(find_pin(yaw, "InRangeA", "Input"), "0.0", "yInA")
set_val(find_pin(yaw, "InRangeB", "Input"), "1.0", "yInB")
set_val(find_pin(yaw, "OutRangeA", "Input"), str(YAW_DAWN), "yawDawn")
set_val(find_pin(yaw, "OutRangeB", "Input"), str(YAW_DUSK), "yawDusk")

# Colors
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

# --- Apply to DirectionalLight ---
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

# --- SkyLight fill (use SkyLightComponent:SetIntensity — works in UE5.8) ---
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
sky_self_ok = connect(ret(get_sc), find_pin(set_si, "self", "Input"), "scI")
connect(ret(sky_i), find_pin(set_si, "NewIntensity", "Input"), "sIval")

# Also tint sky light color for readable cool fill at night
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

if not sky_self_ok:
    log("WARN: SkyLight SetIntensity self did not connect — falling back to skip sky intensity")
    # re-route br2.then to return if broken
    thenp = find_pin(br2, "then", "Output")
    try:
        thenp.break_pin_links(False)
    except Exception:
        try:
            thenp.break_pin_links()
        except Exception:
            pass
    connect(thenp, find_pin(ret_ok, "execute", "Input"), "sky fallback ret")

try:
    bel.compile_blueprint(bp)
    log("compile ok status={}".format(getattr(bp, "status", "?")))
except Exception as e:
    log("compile " + str(e))

unreal.EditorAssetLibrary.save_asset(MGR)

# Bump editor-default sky so PIE first frame isn't dark if BP lags
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
    cn = a.get_class().get_name()
    if cn == "SkyLight":
        for c in a.get_components_by_class(unreal.LightComponentBase):
            try:
                c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                c.set_editor_property("intensity", SKY_NIGHT)
                log("SkyLight editor inten -> {}".format(SKY_NIGHT))
            except Exception as e:
                log("sky edit " + str(e))
    if cn == "DirectionalLight":
        for c in a.get_components_by_class(unreal.LightComponentBase):
            try:
                c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                log("DirectionalLight movable inten={}".format(c.get_editor_property("intensity")))
            except Exception as e:
                log("dl edit " + str(e))

try:
    unreal.EditorLevelLibrary.save_current_level()
    log("level saved")
except Exception:
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        log("level saved2")
    except Exception as e:
        log("level save " + str(e))

# Verify graph constants
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
for n in ge.list_all_nodes():
    t = title(n)
    if "MapRange" in t:
        vals = {}
        for p in bel.list_all_pins(n):
            if "OutRange" in str(p.get_pin_name()) or "InRange" in str(p.get_pin_name()):
                try:
                    vals[str(p.get_pin_name())] = p.get_pin_value()
                except Exception:
                    pass
        log("verify MapRange {} {}".format(t, vals))
    if "MakeColor" in t:
        vals = {}
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) in ("R", "G", "B", "A"):
                try:
                    vals[str(p.get_pin_name())] = p.get_pin_value()
                except Exception:
                    pass
        log("verify color {}".format(vals))
    if "SetIntensity" in t:
        # check self linked
        sp = find_pin(n, "self", "Input")
        links = list(sp.list_connected_pins() or []) if sp else []
        log("verify {} self_links={}".format(t, len(links)))

# Confirm growth graphs untouched
graphs = [str(g) for g in bel.list_graph_names(bp)]
log("AdvanceDayGrowth intact={}".format("AdvanceDayGrowth" in graphs))
log("ApplyDayNightVisuals intact={}".format("ApplyDayNightVisuals" in graphs))
log("DONE")
