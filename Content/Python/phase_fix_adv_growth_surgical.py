# -*- coding: utf-8 -*-
"""Surgical: AdvanceDayGrowth LoopBody = Watered(3)->Ready(4)+VisualizeCell. Remove GrowCell."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
WATERED = "3"
READY = "4"


def log(m):
    unreal.log("[FIX_ADV] " + str(m))
    print("[FIX_ADV] " + str(m))


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
        log("set {}={!r} now={!r}".format(label, value, pin.get_pin_value()))
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


def call(ge, path, x, y):
    n = ge.add_call_function_node(path)
    if n:
        bel.set_node_pos(n, pos(x, y))
        log("add " + path.split(":")[-1])
    else:
        log("FAIL " + path)
    return n


log("START surgical AdvanceDayGrowth")
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "AdvanceDayGrowth"))

for_n = None
grow = None
div_n = None
mod_n = None
for n in list(ge.list_all_nodes()):
    t = title(n)
    if t == "For Loop":
        for_n = n
    if t == "GrowCell":
        grow = n
    if t in ("int / int", "Divide"):
        div_n = n
    if "%" in t or "Percent" in t:
        mod_n = n

if not for_n:
    log("FATAL no ForLoop")
    raise SystemExit(1)

body = find_pin(for_n, "LoopBody", "Output")
try:
    body.break_pin_links(False)
except Exception:
    try:
        body.break_pin_links()
    except Exception as e:
        log("break body: " + str(e))

if grow:
    try:
        ge.remove_nodes([grow])
        log("removed GrowCell from AdvanceDayGrowth")
    except Exception as e:
        log("remove grow: " + str(e))

idx = find_pin(for_n, "Index", "Output")

get_w2 = None
for n in ge.list_all_nodes():
    if title(n) == "Get GridWidth":
        gw = find_pin(n, "GridWidth", "Output")
        if gw and list(gw.list_connected_pins()):
            get_w2 = n
if not get_w2:
    get_w2 = ge.add_get_member_variable_node("GridWidth")
    bel.set_node_pos(get_w2, pos(900, 260))

if not div_n:
    div_n = call(ge, "/Script/Engine.KismetMathLibrary:Divide_IntInt", 1100, 160)
    connect(idx, find_pin(div_n, "A", "Input"), "idx/")
    connect(find_pin(get_w2, "GridWidth", "Output"), find_pin(div_n, "B", "Input"), "w/")
if not mod_n:
    mod_n = call(ge, "/Script/Engine.KismetMathLibrary:Percent_IntInt", 1100, 280)
    connect(idx, find_pin(mod_n, "A", "Input"), "idx%")
    connect(find_pin(get_w2, "GridWidth", "Output"), find_pin(mod_n, "B", "Input"), "w%")

get_plots = ge.add_get_member_variable_node("PlotStates")
bel.set_node_pos(get_plots, pos(1100, 40))

get_at = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", 1350, 40)
connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(get_at, "TargetArray", "Input"), "arr")
connect(idx, find_pin(get_at, "Index", "Input"), "getidx")

eq = call(ge, "/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte", 1600, 40)
connect(find_pin(get_at, "Item", "Output"), find_pin(eq, "A", "Input"), "eqA")
set_val(find_pin(eq, "B", "Input"), WATERED, "eq.B=Watered")

br = ge.add_branch_node()
bel.set_node_pos(br, pos(1850, 0))
connect(body, find_pin(br, "execute", "Input"), "body->br")
connect(ret(eq), find_pin(br, "Condition", "Input"), "eq->br")

set_at = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Set", 2100, 0)
connect(find_pin(br, "then", "Output"), find_pin(set_at, "execute", "Input"), "br->set")
connect(find_pin(get_plots, "PlotStates", "Output"), find_pin(set_at, "TargetArray", "Input"), "setarr")
connect(idx, find_pin(set_at, "Index", "Input"), "setidx")
set_val(find_pin(set_at, "Item", "Input"), READY, "set.Item=Ready")
set_val(find_pin(set_at, "bSizeToFit", "Input"), "true", "fit")

viz = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:VisualizeCell", 2400, 0)
connect(find_pin(set_at, "then", "Output"), find_pin(viz, "execute", "Input"), "set->viz")
connect(ret(mod_n), find_pin(viz, "GridX", "Input") or find_pin(viz, "Grid X", "Input"), "viz.gx")
connect(ret(div_n), find_pin(viz, "GridY", "Input") or find_pin(viz, "Grid Y", "Input"), "viz.gy")
set_val(find_pin(viz, "State", "Input"), READY, "viz.State=Ready")

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "AdvanceDayGrowth"))
has_grow = any(title(n) == "GrowCell" for n in ge.list_all_nodes())
has_viz = any(title(n) == "VisualizeCell" for n in ge.list_all_nodes())
eqb = None
for n in ge.list_all_nodes():
    if "equal" in title(n).lower():
        p = find_pin(n, "B", "Input")
        eqb = p.get_pin_value() if p else None
log("VERIFY GrowCell={} VisualizeCell={} Equal.B={!r} errors={}".format(
    has_grow, has_viz, eqb, len(ge.list_nodes_with_errors())))
log("DONE")
