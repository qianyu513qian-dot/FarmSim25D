# -*- coding: utf-8 -*-
"""Stove: Tick cook progress + VoidIfTable + status helpers."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
PATH = "/Game/Farm/Restaurant/BP_RestaurantStove"
R = {"steps": [], "errors": []}

def log(m):
    unreal.log("[K3S] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def out_data(node):
    if not node:
        return None
    for name in ("ReturnValue", "bCooking", "bCookReady", "CookingDishId", "CookingTableId", "CookTimeLeft", "CookingOrder"):
        p = find_pin(node, name, "Output")
        if p:
            return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            if str(p.get_pin_name()).lower() not in ("outputdelegate", "then", "completed", "loopbody"):
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok)); return ok

def setdef(pin, val):
    if not pin:
        return
    try:
        pin.set_pin_value(str(val))
    except Exception:
        try:
            pin.set_default_value(str(val))
        except Exception:
            pass

def make_print(ge, x, y, text):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), "2.5")
    return pr

def sub_d(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble")
    if n is None:
        n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_FloatFloat")
    bel.set_node_pos(n, pos(x, y)); return n

def cmp_le(ge, x, y):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble")
    if n is None:
        n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_FloatFloat")
    bel.set_node_pos(n, pos(x, y)); return n

bp = unreal.EditorAssetLibrary.load_asset(PATH)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# purge non-parent nodes except keep BeginPlay/Overlap
kill = []
tick = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    c = n.get_class().get_name()
    if c == "K2Node_Event" and ("BeginPlay" in t or "ActorBeginOverlap" in t):
        continue
    if c == "K2Node_CallParentFunction":
        continue
    if c == "K2Node_Event" and t == "Event Tick":
        then = find_pin(n, "then", "Output")
        if then:
            then.break_pin_links()
        tick = n
        continue
    kill.append(n)
if kill:
    ge.remove_nodes(kill); log("purged " + str(len(kill)))
if tick is None:
    try:
        tick = bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(0, 0))
        log("tick override")
    except Exception as e:
        R["errors"].append(str(e))

def clear_stove_chain(ge, start_exec, y, label):
    prev = start_exec
    x = 400
    for name, val in [
        ("bCooking", "false"),
        ("bCookReady", "false"),
        ("CookingDishId", "0"),
        ("CookingTableId", "0"),
        ("CookTimeLeft", "0.0"),
        ("CookingOrder", ""),
    ]:
        sn = ge.add_set_member_variable_node(name)
        bel.set_node_pos(sn, pos(x, y))
        connect(prev, find_pin(sn, "execute", "Input"), label + name)
        setdef(find_pin(sn, name, "Input"), val)
        prev = find_pin(sn, "then", "Output")
        x += 260
    return prev

# VoidIfTable = force void current cook (v1)
void = ge.add_custom_event_node("VoidIfTable")
bel.set_node_pos(void, pos(0, 200))
get_c = ge.add_get_member_variable_node("bCooking")
bel.set_node_pos(get_c, pos(200, 280))
get_r = ge.add_get_member_variable_node("bCookReady")
bel.set_node_pos(get_r, pos(200, 360))
# or_bool
or_b = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
bel.set_node_pos(or_b, pos(450, 300))
connect(out_data(get_c), find_pin(or_b, "A", "Input"), "orA")
connect(out_data(get_r), find_pin(or_b, "B", "Input"), "orB")
br = ge.add_branch_node(); bel.set_node_pos(br, pos(700, 200))
connect(find_pin(void, "then", "Output"), find_pin(br, "execute", "Input"), "void")
connect(out_data(or_b), find_pin(br, "Condition", "Input"), "busy?")
pr = make_print(ge, 1000, 150, "Restaurant STOVE voided (timeout/cancel)")
connect(find_pin(br, "then", "Output"), find_pin(pr, "execute", "Input"), "vpr")
clear_stove_chain(ge, find_pin(pr, "then", "Output"), 200, "void_")

# ForceClear (same)
fc = ge.add_custom_event_node("ForceClear")
bel.set_node_pos(fc, pos(0, 500))
clear_stove_chain(ge, find_pin(fc, "then", "Output"), 500, "fc_")

# Event Tick cooking
if tick:
    bel.set_node_pos(tick, pos(0, 900))
    get_cook = ge.add_get_member_variable_node("bCooking"); bel.set_node_pos(get_cook, pos(250, 980))
    brc = ge.add_branch_node(); bel.set_node_pos(brc, pos(500, 900))
    connect(find_pin(tick, "then", "Output"), find_pin(brc, "execute", "Input"), "tick")
    connect(out_data(get_cook), find_pin(brc, "Condition", "Input"), "cooking?")
    get_tl = ge.add_get_member_variable_node("CookTimeLeft"); bel.set_node_pos(get_tl, pos(750, 980))
    sub = sub_d(ge, 1000, 980)
    connect(out_data(get_tl), find_pin(sub, "A", "Input"), "A")
    connect(find_pin(tick, "DeltaSeconds", "Output"), find_pin(sub, "B", "Input"), "dt")
    set_tl = ge.add_set_member_variable_node("CookTimeLeft"); bel.set_node_pos(set_tl, pos(1300, 900))
    connect(find_pin(brc, "then", "Output"), find_pin(set_tl, "execute", "Input"), "set")
    connect(out_data(sub), find_pin(set_tl, "CookTimeLeft", "Input"), "v")
    le = cmp_le(ge, 1600, 980)
    connect(out_data(sub), find_pin(le, "A", "Input"), "leA")
    setdef(find_pin(le, "B", "Input"), "0.0")
    brd = ge.add_branch_node(); bel.set_node_pos(brd, pos(1850, 900))
    connect(find_pin(set_tl, "then", "Output"), find_pin(brd, "execute", "Input"), "done?")
    connect(out_data(le), find_pin(brd, "Condition", "Input"), "doneC")
    set_cfalse = ge.add_set_member_variable_node("bCooking"); bel.set_node_pos(set_cfalse, pos(2150, 850))
    connect(find_pin(brd, "then", "Output"), find_pin(set_cfalse, "execute", "Input"), "stopcook")
    setdef(find_pin(set_cfalse, "bCooking", "Input"), "false")
    set_ready = ge.add_set_member_variable_node("bCookReady"); bel.set_node_pos(set_ready, pos(2450, 850))
    connect(find_pin(set_cfalse, "then", "Output"), find_pin(set_ready, "execute", "Input"), "ready")
    setdef(find_pin(set_ready, "bCookReady", "Input"), "true")
    pr2 = make_print(ge, 2750, 850, "Restaurant STOVE READY — press E to pick up")
    connect(find_pin(set_ready, "then", "Output"), find_pin(pr2, "execute", "Input"), "pr")

bel.compile_blueprint(bp)
R["status"] = str(bp.get_editor_property("status"))
if "ERROR" not in R["status"]:
    unreal.EditorAssetLibrary.save_asset(PATH)
else:
    for n in ge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                R["errors"].append(bel.get_node_title(n) + ": " + str(em)[:200])
        except Exception:
            pass
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_stove.json","w",encoding="utf-8").write(json.dumps(R, indent=2))
print(json.dumps(R, indent=2, ensure_ascii=False)[:4000])