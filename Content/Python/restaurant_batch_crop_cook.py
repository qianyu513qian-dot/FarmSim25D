# -*- coding: utf-8 -*-
"""Rebuild stove StartSalad/StartStew: consume 1 CropCount via FarmSeedShop.TryConsumeCropForCook."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
PATH = "/Game/Farm/Restaurant/BP_RestaurantStove"
R = {"steps": [], "errors": [], "pins": {}}

def log(m):
    unreal.log("[cropcook] " + str(m)); R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Return Value", "Item", "bCooking", "bCookReady"):
        p = find_pin(node, name, "Output")
        if p:
            return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n = str(p.get_pin_name()).lower()
            if n not in ("outputdelegate", "then", "completed", "loopbody", "else"):
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

def pin_names(node):
    return [(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(node)]

bp = unreal.EditorAssetLibrary.load_asset(PATH)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

STARTS = ("StartSalad1", "StartSalad2", "StartStew1", "StartStew2")

def collect_chain(start):
    kill = set([start])
    queue = [start]
    while queue:
        cur = queue.pop(0)
        for pname in ("then", "else"):
            p = find_pin(cur, pname, "Output")
            if not p:
                continue
            for c in (p.list_connected_pins() or []):
                nxt = c.get_owning_node()
                if nxt not in kill:
                    if nxt.get_class().get_name() == "K2Node_CustomEvent":
                        continue
                    kill.add(nxt); queue.append(nxt)
    return list(kill)

kill_all = []
for n in list(ge.list_all_nodes()):
    if n.get_class().get_name() == "K2Node_CustomEvent" and bel.get_node_title(n) in STARTS:
        kill_all.extend(collect_chain(n))
seen = set(); uniq = []
for n in kill_all:
    if n not in seen:
        seen.add(n); uniq.append(n)
if uniq:
    ge.remove_nodes(uniq)
    log("rm Start* nodes " + str(len(uniq)))

# Probe GetPlayerPawn / TryConsume pin shapes once
probe_gpp = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
probe_cons = ge.add_call_function_node("/Script/FarmSim25D.FarmSeedShop:TryConsumeCropForCook")
R["pins"]["GetPlayerPawn"] = pin_names(probe_gpp)
R["pins"]["TryConsume"] = pin_names(probe_cons) if probe_cons else ["MISSING"]
ge.remove_nodes([n for n in (probe_gpp, probe_cons) if n])
log("probed pins")

MSG_FAIL = "\u6ca1\u6709\u98df\u6750\uff08\u5148\u53bb\u5730\u91cc\u6536\u4f5c\u7269\uff09"  # 没有食材（先去地里收作物）
Y = 1400

def start_cook(name, dish, table, time_s, order, y):
    ev = ge.add_custom_event_node(name)
    bel.set_node_pos(ev, pos(0, y))
    get_c = ge.add_get_member_variable_node("bCooking"); bel.set_node_pos(get_c, pos(220, y + 80))
    get_r = ge.add_get_member_variable_node("bCookReady"); bel.set_node_pos(get_r, pos(220, y + 160))
    or_b = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    bel.set_node_pos(or_b, pos(450, y + 100))
    connect(out_data(get_c), find_pin(or_b, "A", "Input"), name + "orA")
    connect(out_data(get_r), find_pin(or_b, "B", "Input"), name + "orB")
    br = ge.add_branch_node(); bel.set_node_pos(br, pos(700, y))
    connect(find_pin(ev, "then", "Output"), find_pin(br, "execute", "Input"), name)
    connect(out_data(or_b), find_pin(br, "Condition", "Input"), name + "busy")

    # GetPlayerPawn (often pure)
    gpp = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(gpp, pos(950, y + 100))
    setdef(find_pin(gpp, "PlayerIndex", "Input"), "0")
    gpp_exec = find_pin(gpp, "execute", "Input")
    gpp_then = find_pin(gpp, "then", "Output")

    cons = ge.add_call_function_node("/Script/FarmSim25D.FarmSeedShop:TryConsumeCropForCook")
    bel.set_node_pos(cons, pos(1250, y))
    if not cons:
        R["errors"].append(name + ": TryConsumeCropForCook node missing")
        return

    if gpp_exec and gpp_then:
        connect(find_pin(br, "else", "Output"), gpp_exec, name + "gpp")
        connect(gpp_then, find_pin(cons, "execute", "Input"), name + "cons")
    else:
        # pure GetPlayerPawn
        connect(find_pin(br, "else", "Output"), find_pin(cons, "execute", "Input"), name + "cons")

    pawn_out = out_data(gpp) or find_pin(gpp, "ReturnValue", "Output")
    pawn_in = find_pin(cons, "Pawn", "Input") or find_pin(cons, "pawn", "Input")
    connect(pawn_out, pawn_in, name + "pawn")

    brc = ge.add_branch_node(); bel.set_node_pos(brc, pos(1550, y))
    connect(find_pin(cons, "then", "Output"), find_pin(brc, "execute", "Input"), name + "brc")
    connect(out_data(cons) or find_pin(cons, "ReturnValue", "Output"), find_pin(brc, "Condition", "Input"), name + "ok?")

    pr_fail = make_print(ge, 1800, y + 140, MSG_FAIL)
    connect(find_pin(brc, "else", "Output"), find_pin(pr_fail, "execute", "Input"), name + "fail")

    prev = find_pin(brc, "then", "Output")
    x = 1800
    for vn, vv in [
        ("bCooking", "true"),
        ("bCookReady", "false"),
        ("CookingDishId", str(dish)),
        ("CookingTableId", str(table)),
        ("CookTimeLeft", str(time_s)),
        ("CookingOrder", order),
    ]:
        sn = ge.add_set_member_variable_node(vn)
        bel.set_node_pos(sn, pos(x, y))
        connect(prev, find_pin(sn, "execute", "Input"), name + vn)
        setdef(find_pin(sn, vn, "Input"), vv)
        prev = find_pin(sn, "then", "Output")
        x += 250
    pr = make_print(ge, x, y, "Restaurant COOK start {} for Table{} (~{}s) [-1 crop]".format(order, table, time_s))
    connect(prev, find_pin(pr, "execute", "Input"), name + "pr")
    log("built " + name)

start_cook("StartSalad1", 1, 1, 3.0, "TomatoSalad", Y)
start_cook("StartSalad2", 1, 2, 3.0, "TomatoSalad", Y + 380)
start_cook("StartStew1", 2, 1, 6.0, "Stew", Y + 760)
start_cook("StartStew2", 2, 2, 6.0, "Stew", Y + 1140)

bel.compile_blueprint(bp)
R["status"] = str(bp.get_editor_property("status"))
if "ERROR" in R["status"]:
    for n in ge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                R["errors"].append(bel.get_node_title(n) + ": " + str(em)[:220])
        except Exception:
            pass
else:
    unreal.EditorAssetLibrary.save_asset(PATH)
    log("saved")

# verify one chain
def walk(evname, limit=15):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and bel.get_node_title(n)==evname:
            chain=[evname]
            cur=n
            for _ in range(limit):
                thenp=find_pin(cur,"then","Output")
                if not thenp: break
                cons=thenp.list_connected_pins() or []
                if not cons: break
                nxt=cons[0].get_owning_node()
                chain.append(bel.get_node_title(nxt))
                cur=nxt
            return chain
    return []
R["walk_StartSalad1"]=walk("StartSalad1")

open(r"E:\UE\FarmSim25D\Saved\restaurant_crop_cook.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps({k:R[k] for k in ("status","errors","pins","walk_StartSalad1","steps")}, indent=2, ensure_ascii=False)[:9000])