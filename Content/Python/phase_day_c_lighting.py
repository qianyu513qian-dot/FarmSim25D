# -*- coding: utf-8 -*-
"""Phase C: ApplyDayNightVisuals — strong DirectionalLight + SkyLight swing."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[DAY_C] " + str(m)); print("[DAY_C] " + str(m))
def pos(x, y): return unreal.IntPoint(int(x), int(y))
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

bp = unreal.load_asset(MGR)
graphs = [str(g) for g in bel.list_graph_names(bp)]
if "ApplyDayNightVisuals" in graphs:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    entry = None; kill = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry": entry = n
        else: kill.append(n)
    if kill: ge.remove_nodes(kill)
else:
    bel.add_function_graph(bp, "ApplyDayNightVisuals")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    entry = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry": entry = n

bel.set_node_pos(entry, pos(0, 0))
get_tod = ge.add_get_member_variable_node("TimeOfDay"); bel.set_node_pos(get_tod, pos(0, 160))

# DayAmount = MapRangeClamped(Sin((TOD-0.25)*2PI), 0, 1, 0, 1)
sub = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", 250, 160)
connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(sub, "A", "Input"), "tod-")
set_val(find_pin(sub, "B", "Input"), "0.25", "0.25")
mul = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 500, 160)
connect(ret(sub), find_pin(mul, "A", "Input"), "*2pi")
set_val(find_pin(mul, "B", "Input"), "6.283185", "2pi")
sinn = call(ge, "/Script/Engine.KismetMathLibrary:Sin", 750, 160)
connect(ret(mul), find_pin(sinn, "A", "Input"), "sin")
day = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1000, 160)
connect(ret(sinn), find_pin(day, "Value", "Input"), "sun")
set_val(find_pin(day, "InRangeA", "Input"), "0.0", "inA")
set_val(find_pin(day, "InRangeB", "Input"), "1.0", "inB")
set_val(find_pin(day, "OutRangeA", "Input"), "0.0", "outA")
set_val(find_pin(day, "OutRangeB", "Input"), "1.0", "outB")

# Intensity 0.15..8.0 (obvious)
inten = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1280, 40)
connect(ret(day), find_pin(inten, "Value", "Input"), "dI")
set_val(find_pin(inten, "InRangeA", "Input"), "0.0", "iA")
set_val(find_pin(inten, "InRangeB", "Input"), "1.0", "iB")
set_val(find_pin(inten, "OutRangeA", "Input"), "0.15", "nI")
set_val(find_pin(inten, "OutRangeB", "Input"), "8.0", "dI")

# Pitch 20 .. -75
pitch = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1280, 220)
connect(ret(day), find_pin(pitch, "Value", "Input"), "dP")
set_val(find_pin(pitch, "InRangeA", "Input"), "0.0", "pA")
set_val(find_pin(pitch, "InRangeB", "Input"), "1.0", "pB")
set_val(find_pin(pitch, "OutRangeA", "Input"), "20.0", "nP")
set_val(find_pin(pitch, "OutRangeB", "Input"), "-75.0", "dP")

yaw = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 250, 320)
connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(yaw, "A", "Input"), "yaw*")
set_val(find_pin(yaw, "B", "Input"), "360.0", "360")

night = call(ge, "/Script/Engine.KismetMathLibrary:MakeColor", 1000, 400)
dayc = call(ge, "/Script/Engine.KismetMathLibrary:MakeColor", 1000, 560)
set_val(find_pin(night, "R", "Input"), "0.12", "nR")
set_val(find_pin(night, "G", "Input"), "0.18", "nG")
set_val(find_pin(night, "B", "Input"), "0.90", "nB")
set_val(find_pin(night, "A", "Input"), "1.0", "nA")
set_val(find_pin(dayc, "R", "Input"), "1.0", "dR")
set_val(find_pin(dayc, "G", "Input"), "0.92", "dG")
set_val(find_pin(dayc, "B", "Input"), "0.70", "dB")
set_val(find_pin(dayc, "A", "Input"), "1.0", "dA")
lerp = call(ge, "/Script/Engine.KismetMathLibrary:LinearColorLerp", 1280, 420)
connect(ret(night), find_pin(lerp, "A", "Input"), "cA")
connect(ret(dayc), find_pin(lerp, "B", "Input"), "cB")
connect(ret(day), find_pin(lerp, "Alpha", "Input"), "cAl")

make_rot = call(ge, "/Script/Engine.KismetMathLibrary:MakeRotator", 1550, 200)
connect(ret(pitch), find_pin(make_rot, "Pitch", "Input"), "pitch")
connect(ret(yaw), find_pin(make_rot, "Yaw", "Input"), "yaw")
set_val(find_pin(make_rot, "Roll", "Input"), "0.0", "roll")

get_sun = ge.add_get_member_variable_node("SunActor"); bel.set_node_pos(get_sun, pos(1550, 40))
isv = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 1750, 40)
connect(find_pin(get_sun, "SunActor", "Output"), find_pin(isv, "Object", "Input"), "valid")
br = ge.add_branch_node(); bel.set_node_pos(br, pos(1950, 0))
connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
connect(ret(isv), find_pin(br, "Condition", "Input"), "cond")

set_rot = call(ge, "/Script/Engine.Actor:K2_SetActorRotation", 2200, 0)
connect(find_pin(br, "then", "Output"), find_pin(set_rot, "execute", "Input"), "br->rot")
connect(find_pin(get_sun, "SunActor", "Output"), find_pin(set_rot, "self", "Input"), "sunself")
connect(ret(make_rot), find_pin(set_rot, "NewRotation", "Input"), "newrot")
set_val(find_pin(set_rot, "bTeleportPhysics", "Input"), "true", "tele")

get_comp = call(ge, "/Script/Engine.Actor:GetComponentByClass", 2200, 200)
connect(find_pin(get_sun, "SunActor", "Output"), find_pin(get_comp, "self", "Input"), "suncomp")
set_val(find_pin(get_comp, "ComponentClass", "Input"), "/Script/Engine.DirectionalLightComponent", "DL")

set_i = call(ge, "/Script/Engine.LightComponent:SetIntensity", 2550, 0)
connect(find_pin(set_rot, "then", "Output"), find_pin(set_i, "execute", "Input"), "rot->I")
connect(ret(get_comp), find_pin(set_i, "self", "Input"), "compI")
connect(ret(inten), find_pin(set_i, "NewIntensity", "Input"), "Ival")

set_c = call(ge, "/Script/Engine.LightComponent:SetLightColor", 2850, 0)
connect(find_pin(set_i, "then", "Output"), find_pin(set_c, "execute", "Input"), "I->C")
connect(ret(get_comp), find_pin(set_c, "self", "Input"), "compC")
connect(ret(lerp), find_pin(set_c, "NewLightColor", "Input"), "Cval")

# SkyLight
get_sky = ge.add_get_member_variable_node("SkyLightActor"); bel.set_node_pos(get_sky, pos(2850, 220))
isv2 = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 3050, 220)
connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(isv2, "Object", "Input"), "skyv")
br2 = ge.add_branch_node(); bel.set_node_pos(br2, pos(3250, 0))
connect(find_pin(set_c, "then", "Output"), find_pin(br2, "execute", "Input"), "C->br2")
connect(ret(isv2), find_pin(br2, "Condition", "Input"), "skycond")

sky_i = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 3050, 360)
connect(ret(day), find_pin(sky_i, "Value", "Input"), "dSky")
set_val(find_pin(sky_i, "InRangeA", "Input"), "0.0", "sA")
set_val(find_pin(sky_i, "InRangeB", "Input"), "1.0", "sB")
set_val(find_pin(sky_i, "OutRangeA", "Input"), "0.05", "sN")
set_val(find_pin(sky_i, "OutRangeB", "Input"), "1.2", "sD")

get_sc = call(ge, "/Script/Engine.Actor:GetComponentByClass", 3450, 80)
connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(get_sc, "self", "Input"), "skyself")
set_val(find_pin(get_sc, "ComponentClass", "Input"), "/Script/Engine.SkyLightComponent", "SkyComp")

# SkyLightComponent inherits LightComponentBase — SetIntensity is on LightComponent
# Try LightComponent path; SkyLightComponent may use same
set_si = call(ge, "/Script/Engine.LightComponent:SetIntensity", 3700, 0)
if not set_si:
    set_si = call(ge, "/Script/Engine.SkyLightComponent:SetIntensity", 3700, 0)
connect(find_pin(br2, "then", "Output"), find_pin(set_si, "execute", "Input"), "br2->sI")
connect(ret(get_sc), find_pin(set_si, "self", "Input"), "scI")
connect(ret(sky_i), find_pin(set_si, "NewIntensity", "Input"), "sIval")

ret_ok = ge.add_return_node(); bel.set_node_pos(ret_ok, pos(4000, 0))
connect(find_pin(set_si, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "ok")
ret_nosky = ge.add_return_node(); bel.set_node_pos(ret_nosky, pos(3450, 280))
connect(find_pin(br2, "else", "Output"), find_pin(ret_nosky, "execute", "Input"), "nosky")
ret_skip = ge.add_return_node(); bel.set_node_pos(ret_skip, pos(2200, 400))
connect(find_pin(br, "else", "Output"), find_pin(ret_skip, "execute", "Input"), "nosun")

try:
    bel.compile_blueprint(bp); log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)
log("DONE")