# -*- coding: utf-8 -*-
"""Phase B: AdvanceDayGrowth — ForLoop all cells, call GrowCell."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
FOR_LOOP = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop"

def log(m):
    unreal.log("[DAY_B] " + str(m)); print("[DAY_B] " + str(m))
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
if "AdvanceDayGrowth" in graphs:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "AdvanceDayGrowth"))
    entry = None; kill = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry": entry = n
        else: kill.append(n)
    if kill: ge.remove_nodes(kill)
else:
    bel.add_function_graph(bp, "AdvanceDayGrowth")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "AdvanceDayGrowth"))
    entry = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry": entry = n

bel.set_node_pos(entry, pos(0, 0))
get_w = ge.add_get_member_variable_node("GridWidth"); bel.set_node_pos(get_w, pos(0, 160))
get_h = ge.add_get_member_variable_node("GridHeight"); bel.set_node_pos(get_h, pos(0, 240))
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
    log("FATAL ForLoop"); raise SystemExit(1)
bel.set_node_pos(for_n, pos(700, 0))
connect(find_pin(entry, "then", "Output"), find_pin(for_n, "execute", "Input"), "e")
set_val(find_pin(for_n, "FirstIndex", "Input"), "0", "first")
connect(ret(sub), find_pin(for_n, "LastIndex", "Input"), "last")

get_w2 = ge.add_get_member_variable_node("GridWidth"); bel.set_node_pos(get_w2, pos(900, 220))
idx = find_pin(for_n, "Index", "Output")
div = call(ge, "/Script/Engine.KismetMathLibrary:Divide_IntInt", 1100, 160)
mod = call(ge, "/Script/Engine.KismetMathLibrary:Percent_IntInt", 1100, 280)
connect(idx, find_pin(div, "A", "Input"), "idx/")
connect(find_pin(get_w2, "GridWidth", "Output"), find_pin(div, "B", "Input"), "w/")
connect(idx, find_pin(mod, "A", "Input"), "idx%")
connect(find_pin(get_w2, "GridWidth", "Output"), find_pin(mod, "B", "Input"), "w%")

grow = call(ge, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GrowCell", 1400, 40)
connect(find_pin(for_n, "LoopBody", "Output"), find_pin(grow, "execute", "Input"), "body")
connect(ret(mod), find_pin(grow, "GridX", "Input") or find_pin(grow, "Grid X", "Input"), "gx")
connect(ret(div), find_pin(grow, "GridY", "Input") or find_pin(grow, "Grid Y", "Input"), "gy")
rn = ge.add_return_node(); bel.set_node_pos(rn, pos(1400, 320))
connect(find_pin(for_n, "Completed", "Output"), find_pin(rn, "execute", "Input"), "done")

try:
    bel.compile_blueprint(bp); log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)
log("DONE")