# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {"steps": [], "errors": [], "statuses": {}, "probe": {}}

def log(m):
    unreal.log("[K3F4] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok)); return ok

def pin_links(p):
    if not p: return -1
    try: return len(list(p.list_connected_pins()))
    except: return -1

def compile_save(bp, path, key):
    bel.compile_blueprint(bp)
    st = str(bp.get_editor_property("status"))
    R["statuses"][key] = st
    if "ERROR" in st:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
        for n in ge.list_all_nodes():
            try:
                em = n.get_editor_property("error_msg")
                if em and str(em).strip():
                    R["errors"].append(key + ":" + bel.get_node_title(n) + ":" + str(em)[:180])
            except Exception: pass
    else:
        unreal.EditorAssetLibrary.save_asset(path)

def follow_exec(start, max_depth=12):
    """BFS exec outputs, return list of (node, title)."""
    out = []
    visited = set()
    stack = [(start, 0)]
    while stack:
        cur, d = stack.pop(0)
        if id(cur) in visited or d > max_depth:
            continue
        visited.add(id(cur))
        out.append((cur, bel.get_node_title(cur), d))
        for pname in ("then", "else", "LoopBody", "Completed"):
            p = find_pin(cur, pname, "Output")
            if not p:
                continue
            for cp in p.list_connected_pins():
                stack.append((cp.get_owning_node(), d + 1))
    return out

TP = "/Game/Farm/Restaurant/BP_RestaurantTable"
tbp = unreal.EditorAssetLibrary.load_asset(TP)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))

# Find Set EatLeft at ~1750,1850 and Set PatienceLeft at ~2300,2150
set_eat = set_pat = None
for n in tge.list_all_nodes():
    t = bel.get_node_title(n)
    p = bel.get_node_pos(n)
    if t == "Set EatLeft" and abs(int(p.x) - 1750) < 80 and abs(int(p.y) - 1850) < 80:
        set_eat = n
    if t == "Set PatienceLeft" and abs(int(p.x) - 2300) < 80 and abs(int(p.y) - 2150) < 80:
        set_pat = n

R["probe"]["set_eat"] = set_eat is not None
R["probe"]["set_pat"] = set_pat is not None

def patch_after_set(set_node, event_name, label):
    if not set_node:
        log("missing " + label); return
    chain = follow_exec(set_node)
    R["probe"][label + "_chain"] = [(t, d) for _, t, d in chain[:20]]
    # Find first Branch after set; its then should go to done handling
    branch = None
    for node, title, d in chain:
        if node.get_class().get_name() == "K2Node_IfThenElse" and d >= 1:
            branch = node
            break
    if not branch:
        # Maybe LessEqual is after set then directly - look for dangling then on set
        then = find_pin(set_node, "then", "Output")
        log(label + " no branch, then links=" + str(pin_links(then)))
        # Find Less* connected from subtract result — search nearby Branch by Y
        sy = int(bel.get_node_pos(set_node).y)
        for n in tge.list_all_nodes():
            if n.get_class().get_name() != "K2Node_IfThenElse":
                continue
            if abs(int(bel.get_node_pos(n).y) - sy) < 150 and int(bel.get_node_pos(n).x) > int(bel.get_node_pos(set_node).x):
                branch = n
                break
    if not branch:
        log(label + " FAILED find branch"); return
    thenp = find_pin(branch, "then", "Output")
    cur = [bel.get_node_title(p.get_owning_node()) for p in thenp.list_connected_pins()] if thenp else []
    log(label + " branch then was -> " + str(cur))
    thenp.break_pin_links()
    call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:" + event_name)
    if call is None:
        log("NULL " + event_name); return
    bel.set_node_pos(call, pos(int(bel.get_node_pos(branch).x) + 450, int(bel.get_node_pos(branch).y)))
    connect(thenp, find_pin(call, "execute", "Input"), label)
    # Soft: also wire else leave empty (continue counting)

patch_after_set(set_eat, "PayAndClear", "eat")
patch_after_set(set_pat, "TimeoutLeave", "pat")

# Also: orphan ClearSeat at 4100 with no preds — remove to avoid confusion
kill = []
for n in tge.list_all_nodes():
    if "ClearSeat" not in bel.get_node_title(n):
        continue
    if n.get_class().get_name() != "K2Node_CallFunction":
        continue
    exe = find_pin(n, "execute", "Input")
    if pin_links(exe) == 0:
        p = bel.get_node_pos(n)
        if int(p.x) >= 4000:
            kill.append(n)
if kill:
    tge.remove_nodes(kill)
    log("removed orphan ClearSeat " + str(len(kill)))

compile_save(tbp, TP, "table")

# Verify Tick chain now
tbp = unreal.EditorAssetLibrary.load_asset(TP)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
for n in tge.list_all_nodes():
    if bel.get_node_title(n) == "Set EatLeft" and abs(int(bel.get_node_pos(n).x) - 1750) < 80:
        R["probe"]["eat_after"] = [(t, d) for _, t, d in follow_exec(n)[:15]]
    if bel.get_node_title(n) == "Set PatienceLeft" and abs(int(bel.get_node_pos(n).x) - 2300) < 80:
        R["probe"]["pat_after"] = [(t, d) for _, t, d in follow_exec(n)[:15]]

# Final compile all restaurant BPs + character
for path in [
    "/Game/Farm/Restaurant/BP_RestaurantStove",
    "/Game/Farm/Restaurant/BP_RestaurantManager",
    "/Game/Farm/Restaurant/BP_RestaurantTable",
    "/Game/ThirdPerson/Blueprints/BP_TopDownCharacter",
]:
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        # try find TopDown
        if "TopDown" in path:
            for a in unreal.EditorAssetLibrary.list_assets("/Game", True, False):
                if "BP_TopDownCharacter" in a and a.endswith("BP_TopDownCharacter"):
                    path = a.split(".")[0]
                    break
            else:
                continue
        else:
            continue
    bp = unreal.EditorAssetLibrary.load_asset(path)
    compile_save(bp, path, path.split("/")[-1])

# Sanity: Manager HeldOrder exists?
mbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
R["probe"]["mgr_vars"] = [str(n) for n in bel.list_member_variable_names(mbp, False)]
sbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
R["probe"]["stove_vars"] = [str(n) for n in bel.list_member_variable_names(sbp, False)]

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_fix4.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False)[:9000])