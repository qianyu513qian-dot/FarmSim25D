# -*- coding: utf-8 -*-
"""Surgical fix: replace yaw MapRangeClamped(0..1->35..185) with TOD*360."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[FIX_YAW] " + str(m))
    print("[FIX_YAW] " + str(m))


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


def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()


def ret(node):
    return find_pin(node, "ReturnValue", "Output") or find_pin(node, "Return", "Output")


log("START surgical yaw")
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

get_tod = None
make_rot = None
yaw_map = None
for n in ge.list_all_nodes():
    t = title(n)
    if t == "Get TimeOfDay":
        get_tod = n
    if t == "MakeRotator":
        make_rot = n
    if "MapRangeClamped" in t:
        val_pin = find_pin(n, "Value", "Input")
        out_a = find_pin(n, "OutRangeA", "Input")
        out_b = find_pin(n, "OutRangeB", "Input")
        try:
            oa = out_a.get_pin_value() if out_a else ""
            ob = out_b.get_pin_value() if out_b else ""
        except Exception:
            oa, ob = "", ""
        val_from_tod = False
        if val_pin:
            for c in val_pin.list_connected_pins():
                if "TimeOfDay" in title(c.get_owning_node()):
                    val_from_tod = True
        if val_from_tod or str(oa) in ("35.0", "35") or str(ob) in ("185.0", "185"):
            yaw_map = n
            log("found yaw MapRange OutA={!r} OutB={!r} fromTOD={}".format(oa, ob, val_from_tod))

if not get_tod or not make_rot:
    log("FATAL missing tod/makerot")
    raise SystemExit(1)

yaw_pin = find_pin(make_rot, "Yaw", "Input")
try:
    yaw_pin.break_pin_links(False)
except Exception:
    try:
        yaw_pin.break_pin_links()
    except Exception as e:
        log("break yaw " + str(e))

yaw_mul = None
try:
    yaw_mul = ge.create_node_from_name("Utilities|Operators|Multiply", unreal.Vector2D(520, 360), [])
except Exception as e:
    log("create Multiply: " + str(e))
if not yaw_mul:
    yaw_mul = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble")
if not yaw_mul:
    yaw_mul = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Multiply_FloatFloat")
if not yaw_mul:
    log("FATAL no mul")
    raise SystemExit(1)
bel.set_node_pos(yaw_mul, pos(520, 360))
log("added " + title(yaw_mul))
connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(yaw_mul, "A", "Input"), "tod->A")
set_val(find_pin(yaw_mul, "B", "Input"), "360.0", "360")
connect(ret(yaw_mul), yaw_pin, "mul->yaw")

if yaw_map:
    for p in bel.list_all_pins(yaw_map):
        try:
            p.break_pin_links(False)
        except Exception:
            try:
                p.break_pin_links()
            except Exception:
                pass
    try:
        ge.remove_nodes([yaw_map])
        log("removed old yaw MapRange")
    except Exception as e:
        log("remove " + str(e))

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
for n in ge.list_all_nodes():
    if title(n) == "MakeRotator":
        yp = find_pin(n, "Yaw", "Input")
        cps = [(title(c.get_owning_node()), str(c.get_pin_name())) for c in yp.list_connected_pins()]
        log("VERIFY MakeRotator.Yaw <- {}".format(cps))
    if "*" in title(n) or "Multiply" in title(n):
        bp_ = find_pin(n, "B", "Input")
        try:
            v = bp_.get_pin_value() if bp_ else None
        except Exception:
            v = None
        if v and "360" in str(v):
            log("VERIFY mul B={}".format(v))
log("DONE")
