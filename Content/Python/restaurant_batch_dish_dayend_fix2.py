# -*- coding: utf-8 -*-
"""Unwire PrintDayEndSummary from BeginPlay ApplySignClosed (->EnsureOrderUI) only."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
R = {"steps": [], "ok": []}

def log(m):
    unreal.log("[DISHFIX2] " + str(m)); print("[DISHFIX2] " + str(m)); R["steps"].append(str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

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

mbp = eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

fixed = 0
for n in list(mge.list_all_nodes()):
    if title(n) != "ApplySignClosed" or n.get_class().get_name() != "K2Node_CallFunction":
        continue
    tp = find_pin(n, "then", "Output")
    if not tp: continue
    nxts = [c.get_owning_node() for c in (tp.list_connected_pins() or [])]
    if not nxts: continue
    if "PrintDayEndSummary" not in title(nxts[0]):
        continue
    # Walk past summary to see ultimate
    sum_n = nxts[0]
    stp = find_pin(sum_n, "then", "Output")
    after = [c.get_owning_node() for c in (stp.list_connected_pins() or [])] if stp else []
    after_titles = [title(a) for a in after]
    log("chain after sum: " + str(after_titles))
    # If after is EnsureOrderUI (BeginPlay init), bypass summary
    if any("EnsureOrderUI" in t for t in after_titles):
        try: tp.break_pin_links()
        except: pass
        try: stp.break_pin_links()
        except: pass
        for a in after:
            ap = find_pin(a, "execute", "Input")
            connect(tp, ap, "bypass->Ensure")
        # leave orphan PrintDayEndSummary call (no exec in) — remove it
        mge.remove_nodes([sum_n])
        fixed += 1
        log("bypassed BeginPlay summary")
        R["ok"].append("bypass_beginplay")

bel.compile_blueprint(mbp)
R["mgr"] = str(mbp.get_editor_property("status"))
log("mgr " + R["mgr"])

# re-verify close chains
close_chains = []
for n in mge.list_all_nodes():
    if title(n) != "ApplySignClosed" or n.get_class().get_name() != "K2Node_CallFunction":
        continue
    chain = [title(n)]; cur = n
    for _ in range(8):
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
        chain.append(title(cur))
    close_chains.append(chain)
R["close_chains"] = close_chains
R["fixed"] = fixed

if "ERROR" not in R["mgr"]:
    eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_dish_dayend_fix2.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False,default=str))
print(json.dumps(R, indent=2, ensure_ascii=False, default=str))
