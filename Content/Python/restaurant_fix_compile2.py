# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {"steps": []}

def log(m):
    unreal.log("[FIXC2] " + str(m))
    R["steps"].append(str(m))

def status_of(bp):
    return str(bp.get_editor_property("status"))

def find_pin(node, substr, direction=None):
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

# Manager: remove ClearGuests CallFunction with zero pins OR no exec connection and no pins
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
kill = []
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "ClearGuests":
        continue
    if n.get_class().get_name() != "K2Node_CallFunction":
        continue
    pins = list(bel.list_all_pins(n))
    ex = find_pin(n, "execute", "Input")
    then = find_pin(n, "then", "Output")
    # broken: no pins at all
    if len(pins) == 0:
        kill.append(n)
        log("kill 0-pin ClearGuests")
        continue
    # orphan: exec not connected AND then not connected - unused duplicate
    ex_n = len(ex.list_connected_pins()) if ex else -1
    then_n = len(then.list_connected_pins()) if then else -1
    if ex_n == 0:
        kill.append(n)
        log("kill orphan ClearGuests exec_in=0")
if kill:
    ge.remove_nodes(kill)

# Table: remove unused GetDisplayName/GetObjectName that have no output links (orphans from knife2)
tbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
tkill = []
for n in tge.list_all_nodes():
    t = bel.get_node_title(n)
    if t in ("GetDisplayName", "GetObjectName", "GetActorLabel"):
        ret = find_pin(n, "ReturnValue", "Output")
        if ret and len(ret.list_connected_pins()) == 0:
            tkill.append(n)
            log("table kill orphan " + t)
        elif "ActorLabel" in t:
            tkill.append(n)
            log("table kill label " + t)
# Also if GetObjectName unused
if tkill:
    tge.remove_nodes(tkill)

# Ensure OpenSign detection still works: Contains SearchIn must be linked
contains_ok = False
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "Contains":
        sin = find_pin(n, "SearchIn", "Input")
        contains_ok = bool(sin and sin.list_connected_pins())
        R["contains_from"] = [bel.get_node_title(c.get_owning_node()) for c in sin.list_connected_pins()] if sin else []
R["contains_ok"] = contains_ok

bel.compile_blueprint(bp)
bel.compile_blueprint(tbp)
unreal.EditorAssetLibrary.save_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
unreal.EditorAssetLibrary.save_asset("/Game/Farm/Restaurant/BP_RestaurantTable")

R["manager"] = status_of(bp)
R["table"] = status_of(tbp)

# node error scan
def scan_errors(ge, label):
    errs = []
    for n in ge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip() and str(em) not in ("None",):
                errs.append(bel.get_node_title(n) + ": " + str(em)[:200])
        except Exception:
            pass
    R[label + "_node_errs"] = errs

scan_errors(ge, "mgr")
scan_errors(tge, "tbl")

# fresh log tail only after now - mark with timestamp by reading last 100 lines for Restaurant Error
msgs = []
with open(r"E:\UE\FarmSim25D\Saved\Logs\FarmSim25D.log", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()[-400:]
for line in lines:
    if "BP_Restaurant" in line and ("Error:" in line or "failed to compile" in line):
        msgs.append(line.strip()[:300])
R["recent_errors"] = msgs[-15:]

# IA check
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia = {}
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        p = find_pin(n, "Started", "Output")
        ia["Started"] = [bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]
    if bel.get_node_title(n) == "TillSoil":
        p = find_pin(n, "execute", "Input")
        ia["TillSoil"] = [bel.get_node_title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in p.list_connected_pins()]
R["ia"] = ia
R["actors"] = len(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())

open(r"E:\UE\FarmSim25D\Saved\restaurant_fix_compile2.json", "w", encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False))