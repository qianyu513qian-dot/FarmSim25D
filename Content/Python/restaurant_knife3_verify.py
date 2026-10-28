# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {"ok": [], "gaps": [], "statuses": {}}

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def pin_links(p):
    if not p: return -1
    try: return len(list(p.list_connected_pins()))
    except: return -1

def follow(start, max_d=15):
    out = []
    vis = set(); q = [(start, 0)]
    while q:
        cur, d = q.pop(0)
        if id(cur) in vis or d > max_d: continue
        vis.add(id(cur))
        out.append(bel.get_node_title(cur))
        for pn in ("then", "else", "LoopBody"):
            p = find_pin(cur, pn, "Output")
            if not p: continue
            for cp in p.list_connected_pins():
                q.append((cp.get_owning_node(), d+1))
    return out

def compile(path):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    bel.compile_blueprint(bp)
    st = str(bp.get_editor_property("status"))
    R["statuses"][path.split("/")[-1]] = st
    return bp, st

# Trash ClearHeld
MP = "/Game/Farm/Restaurant/BP_RestaurantManager"
mbp, _ = compile(MP)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_CustomEvent" and bel.get_node_title(n) == "HandleTrashE":
        chain = follow(n)
        R["trash_chain"] = chain
        if "ClearHeld" in chain:
            R["ok"].append("Trash->ClearHeld")
        else:
            # wire it: find Branch then -> Print then dangling or end
            for n2 in mge.list_all_nodes():
                if n2.get_class().get_name() != "K2Node_IfThenElse":
                    continue
                # near HandleTrashE y~3600
                if abs(int(bel.get_node_pos(n2).y) - int(bel.get_node_pos(n).y)) > 200:
                    continue
                thenp = find_pin(n2, "then", "Output")
                # follow to last then
                cur = n2
                last_then = thenp
                for _ in range(5):
                    if not last_then or pin_links(last_then) == 0:
                        break
                    nxt = list(last_then.list_connected_pins())[0].get_owning_node()
                    nt = find_pin(nxt, "then", "Output")
                    if not nt:
                        break
                    cur = nxt
                    last_then = nt
                if last_then and pin_links(last_then) == 0:
                    call = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearHeld")
                    if call:
                        bel.set_node_pos(call, unreal.IntPoint(int(bel.get_node_pos(cur).x)+400, int(bel.get_node_pos(cur).y)))
                        last_then.try_create_connection(find_pin(call, "execute", "Input"))
                        R["ok"].append("wired Trash ClearHeld")
            bel.compile_blueprint(mbp)
            unreal.EditorAssetLibrary.save_asset(MP)

# Critical path checks
checks = [
    (MP, "HandlePlayerE", ["DispatchNonSignE"], "OpenSign else->Dispatch"),
    (MP, "DispatchNonSignE", ["HandleStoveE", "HandleTrashE", "HandleTableE"], "Dispatch routes"),
    (MP, "HandleStoveE", ["PlayerE"], "StoveE->PlayerE"),
    (MP, "HandleTableE", ["PushContextAndEval"], "TableE->Push"),
    (MP, "EvalTableE", ["BeginEatOnlyIfId1", "WrongLeaveOnlyIfId1"], "Eval serve"),
    ("/Game/Farm/Restaurant/BP_RestaurantStove", "PlayerE", ["ReceiveSalad1", "TryClaimCook", "ForceClear"], "Stove PlayerE"),
    ("/Game/Farm/Restaurant/BP_RestaurantTable", "TryClaimCook", ["StartSalad1", "StartStew1"], "ClaimCook"),
    ("/Game/Farm/Restaurant/BP_RestaurantTable", "PayAndClear", ["OnGuestPaidSalad", "ClearSeat"], "Pay"),
    ("/Game/Farm/Restaurant/BP_RestaurantTable", "TimeoutLeave", ["VoidIfTable", "ClearSeat"], "Timeout"),
]
for path, ev, need, label in checks:
    bp = unreal.EditorAssetLibrary.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    evn = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() in ("K2Node_CustomEvent", "K2Node_Event") and bel.get_node_title(n) == ev:
            evn = n; break
        if bel.get_node_title(n) == ev and "Event" in n.get_class().get_name():
            evn = n; break
    if not evn:
        # Custom event title exact
        for n in ge.list_all_nodes():
            if bel.get_node_title(n) == ev:
                evn = n; break
    if not evn:
        R["gaps"].append(label + ": event missing " + ev)
        continue
    chain = follow(evn)
    missing = [x for x in need if x not in chain]
    if missing:
        R["gaps"].append(label + ": missing " + str(missing) + " in " + str(chain[:25]))
    else:
        R["ok"].append(label)

# HandlePlayerE may be named exactly — check OpenSign Contains else
for n in mge.list_all_nodes():
    if bel.get_node_title(n) != "Contains":
        continue
    sub = find_pin(n, "Substring", "Input")
    try:
        v = str(sub.get_pin_value()) if sub else ""
    except: v = ""
    if "OpenSign" in v:
        ret = find_pin(n, "ReturnValue", "Output")
        for cp in ret.list_connected_pins():
            br = cp.get_owning_node()
            elsep = find_pin(br, "else", "Output")
            if elsep:
                tgts = [bel.get_node_title(p.get_owning_node()) for p in elsep.list_connected_pins()]
                if "DispatchNonSignE" in tgts:
                    R["ok"].append("OpenSign else->Dispatch")
                else:
                    R["gaps"].append("OpenSign else -> " + str(tgts))

# Tick eat/pat
TP = "/Game/Farm/Restaurant/BP_RestaurantTable"
tbp = unreal.EditorAssetLibrary.load_asset(TP)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
for n in tge.list_all_nodes():
    if bel.get_node_title(n) == "Set EatLeft" and abs(int(bel.get_node_pos(n).x)-1750)<80:
        ch = follow(n)
        if "PayAndClear" in ch: R["ok"].append("Tick eat->PayAndClear")
        else: R["gaps"].append("Tick eat chain " + str(ch[:10]))
    if bel.get_node_title(n) == "Set PatienceLeft" and abs(int(bel.get_node_pos(n).x)-2300)<80:
        ch = follow(n)
        if "TimeoutLeave" in ch: R["ok"].append("Tick pat->TimeoutLeave")
        else: R["gaps"].append("Tick pat chain " + str(ch[:10]))

for path in [MP, "/Game/Farm/Restaurant/BP_RestaurantStove", TP,
             "/Game/ThirdPerson/Blueprints/BP_TopDownCharacter"]:
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        compile(path)

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_verify.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False))