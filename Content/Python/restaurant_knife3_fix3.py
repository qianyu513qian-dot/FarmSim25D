# -*- coding: utf-8 -*-
import unreal, json, re
bel = unreal.BlueprintEditorLibrary
R = {"steps": [], "errors": [], "statuses": {}, "probe": {}}

def log(m):
    unreal.log("[K3F3] " + str(m)); R["steps"].append(str(m))

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

def out_data(node):
    if not node: return None
    for name in ("ReturnValue", "Item", "EatLeft", "PatienceLeft"):
        p = find_pin(node, name, "Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            nm = str(p.get_pin_name()).lower()
            if nm not in ("outputdelegate", "then", "completed", "loopbody"):
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

TP = "/Game/Farm/Restaurant/BP_RestaurantTable"
tbp = unreal.EditorAssetLibrary.load_asset(TP)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))

# List all variable gets/sets
gets = []
for n in tge.list_all_nodes():
    c = n.get_class().get_name()
    t = bel.get_node_title(n)
    if "Variable" in c or c in ("K2Node_VariableGet", "K2Node_VariableSet"):
        gets.append({"c": c, "t": t, "x": int(bel.get_node_pos(n).x), "y": int(bel.get_node_pos(n).y)})
    if "Less" in t or "Equal" in t:
        gets.append({"c": c, "t": t, "x": int(bel.get_node_pos(n).x), "y": int(bel.get_node_pos(n).y)})
R["probe"]["vars"] = gets

# Read original table script for Tick structure
src = open(r"E:\UE\FarmSim25D\Content\Python\restaurant_knife3_table.py", encoding="utf-8", errors="ignore").read()
# find make_print texts
prints = re.findall(r'make_print\([^,]+,\s*[^,]+,\s*[^,]+,\s*"([^"]+)"', src)
prints += re.findall(r'setdef\(find_pin\(pr[^,]+,\s*"InString"[^,]+,\s*"([^"]+)"', src)
R["probe"]["prints_src"] = prints

# Member var names on table
R["probe"]["members"] = [str(n) for n in bel.list_member_variable_names(tbp, False)]

# Find Get nodes for EatLeft / PatienceLeft by title contains
for n in tge.list_all_nodes():
    t = bel.get_node_title(n)
    if "EatLeft" not in t and "PatienceLeft" not in t:
        continue
    kind = "eat" if "EatLeft" in t else "patience"
    outp = out_data(n)
    if not outp:
        log("no out " + t); continue
    # Follow to Less* then Branch
    for cp in outp.list_connected_pins():
        le = cp.get_owning_node()
        lt = bel.get_node_title(le)
        log("Eat/Pat {} -> {}".format(t, lt))
        ret = find_pin(le, "ReturnValue", "Output")
        if not ret:
            # maybe connected as A to Less — this Get IS the source into Less A
            # cp is on Less's A input, so le is Less
            pass
        # If Get connected to Less A, le is LessEqual
        if "Less" in lt or "Equal" in lt.lower() or "Nearly" in lt:
            ret = find_pin(le, "ReturnValue", "Output")
            if not ret:
                continue
            for bp in ret.list_connected_pins():
                br = bp.get_owning_node()
                if br.get_class().get_name() != "K2Node_IfThenElse":
                    continue
                thenp = find_pin(br, "then", "Output")
                # What does then currently do?
                cur = [bel.get_node_title(p.get_owning_node()) for p in thenp.list_connected_pins()] if thenp else []
                log("{} branch then -> {}".format(kind, cur))
                thenp.break_pin_links()
                if kind == "eat":
                    call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:PayAndClear")
                    bel.set_node_pos(call, pos(int(bel.get_node_pos(br).x) + 450, int(bel.get_node_pos(br).y)))
                    connect(thenp, find_pin(call, "execute", "Input"), "Pay")
                else:
                    call = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:TimeoutLeave")
                    bel.set_node_pos(call, pos(int(bel.get_node_pos(br).x) + 450, int(bel.get_node_pos(br).y)))
                    connect(thenp, find_pin(call, "execute", "Input"), "TO")

# If no EatLeft gets found by title, search pins named EatLeft
if not any("EatLeft" in g["t"] for g in gets):
    log("no EatLeft get by title — scanning pins")
    for n in tge.list_all_nodes():
        for p in bel.list_all_pins(n):
            if "eatleft" in str(p.get_pin_name()).lower() and "OUTPUT" in str(p.get_pin_direction()):
                log("found pin EatLeft on " + bel.get_node_title(n))

compile_save(tbp, TP, "table")

# Trash ClearHeld on manager — find HandleTrashE branch then chain
MP = "/Game/Farm/Restaurant/BP_RestaurantManager"
mbp = unreal.EditorAssetLibrary.load_asset(MP)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
for n in mge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_CustomEvent" or bel.get_node_title(n) != "HandleTrashE":
        continue
    # BFS exec
    visited = set()
    stack = [n]
    while stack:
        cur = stack.pop()
        if id(cur) in visited:
            continue
        visited.add(id(cur))
        for pname in ("then", "else"):
            p = find_pin(cur, pname, "Output")
            if not p:
                continue
            for cp in p.list_connected_pins():
                stack.append(cp.get_owning_node())
            if pin_links(p) == 0 and bel.get_node_title(cur) == "Print String" and pname == "then":
                call = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
                if call:
                    bel.set_node_pos(call, pos(int(bel.get_node_pos(cur).x) + 400, int(bel.get_node_pos(cur).y)))
                    connect(p, find_pin(call, "execute", "Input"), "trashClear")
                    log("trash ClearHeld")
            # Also: if Branch then goes to Print and Print then dangling
            if pin_links(p) == 0 and cur.get_class().get_name() == "K2Node_IfThenElse" and pname == "then":
                # holding true path with no link?
                pass

compile_save(mbp, MP, "manager")

# Verify critical customs callable: try create call nodes
for path, events, key in [
    (SP := "/Game/Farm/Restaurant/BP_RestaurantStove", ["PlayerE", "ForceClear", "StartSalad1"], "stove_call"),
    (MP, ["HandleStoveE", "DispatchNonSignE", "ClearHeld", "ReceiveSalad1", "EvalTableE"], "mgr_call"),
    (TP, ["TryClaimCook", "PayAndClear", "PushContextAndEval", "BeginEatOnlyIfId1"], "tbl_call"),
]:
    bp = unreal.EditorAssetLibrary.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    ok = {}
    for ev in events:
        # path form
        cls = path.split("/")[-1]
        call = ge.add_call_function_node("{}.{}_C:{}".format(path, cls, ev))
        ok[ev] = call is not None
        if call:
            ge.remove_nodes([call])
    R["probe"][key] = ok
    compile_save(bp, path, key)

# Character still compiles?
CP = "/Game/ThirdPerson/Blueprints/BP_TopDownCharacter"
if not unreal.EditorAssetLibrary.does_asset_exist(CP):
    # find
    CP = "/Game/Farm/Blueprints/BP_TopDownCharacter"
# search
assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False)
char = [a for a in assets if "TopDownCharacter" in a or "BP_Player" in a]
R["probe"]["chars"] = char[:10]
for a in char[:3]:
    if a.endswith(".") or "/BP_" not in a:
        continue
    bp = unreal.EditorAssetLibrary.load_asset(a.split(".")[0])
    if bp and hasattr(bp, "get_editor_property"):
        try:
            bel.compile_blueprint(bp)
            R["statuses"]["char:" + a.split("/")[-1]] = str(bp.get_editor_property("status"))
        except Exception as e:
            R["errors"].append(str(e))

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_fix3.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False)[:10000])