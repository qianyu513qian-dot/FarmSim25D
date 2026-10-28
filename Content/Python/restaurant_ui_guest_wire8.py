# -*- coding: utf-8 -*-
"""Remove broken Manager ForEach bubble path (Tick handles it); verify final state."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"

R = {"steps": []}

def log(m):
    unreal.log("[UI_W8] " + str(m)); print("[UI_W8] " + str(m)); R["steps"].append(str(m))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def find_event(ge, name_substr):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_Event" and name_substr in title(n):
            return n
    return None

def walk_then(start, max_d=40):
    thenp = find_pin(start, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen = []; ids = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in ids or d > max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then", "else", "Completed", "LoopBody"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d + 1))
    return seen

mbp = unreal.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
ref = find_custom(mge, "RefreshOrderUI")

# Disconnect GetAllActors / ForEach / RefreshTableBubble from RefreshOrderUI chain
# Keep: EnsureOrderUI -> PrintString (header)
if ref:
    chain = walk_then(ref, 30)
    log("refresh before: " + " -> ".join(title(n) for n in chain))
    # Find PrintString that is header; break its then if it goes to GetAllActors
    for n in chain:
        if title(n) == "PrintString":
            thenp = find_pin(n, "then", "Output")
            if thenp:
                tgts = list(thenp.list_connected_pins() or [])
                for t in tgts:
                    own = t.get_owning_node()
                    if "GetAllActors" in title(own) or "For Each" in title(own):
                        try:
                            thenp.break_pin_links()
                            log("broke Print->GetAllActors")
                        except Exception as e:
                            log(str(e))
        if "GetAllActors" in title(n) or "For Each" in title(n) or title(n) == "RefreshTableBubble":
            for p in bel.list_all_pins(n):
                try: p.break_pin_links()
                except Exception: pass
            log("broke links on " + title(n))

bel.compile_blueprint(mbp)
eas.save_asset(MGR)

# Final compile all
for path in (TBL, MGR, GUEST):
    bel.compile_blueprint(unreal.load_asset(path))
    eas.save_asset(path)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level " + str(e))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# Final report
for path, key in ((TBL, "table"), (MGR, "mgr"), (GUEST, "guest")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    errs = [title(n) for n in (ge.list_nodes_with_errors() or [])]
    R[key + "_err"] = errs
    log("{} err={}".format(key, errs))

tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(TBL), "EventGraph"))
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(MGR), "EventGraph"))
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(GUEST), "EventGraph"))

def dump(ge, name, key):
    ev = find_custom(ge, name)
    chain = [title(n) for n in walk_then(ev, 40)] if ev else []
    R[key] = chain
    log(key + ": " + " -> ".join(chain[:30]))

dump(tge, "TrySeat", "tryseat")
dump(tge, "SpawnGuestVisual", "spawn")
dump(tge, "DestroyGuestVisual", "destroy")
dump(tge, "ClearSeat", "clear")
dump(tge, "RefreshTableBubble", "bubble")
dump(mge, "EnsureOrderUI", "ensure")
dump(mge, "RefreshOrderUI", "refresh")
dump(gge, "ApplyTint", "apply")

tick = find_event(tge, "Tick")
R["tick"] = [title(n) for n in walk_then(tick, 12)] if tick else []
log("tick: " + " -> ".join(R["tick"]))

bpn = find_event(mge, "BeginPlay")
R["mgr_bp"] = [title(n) for n in walk_then(bpn, 15)] if bpn else []
log("mgr_bp: " + " -> ".join(R["mgr_bp"][:15]))

# Asset checklist
eas_check = [
    "/Game/Farm/UI/WBP_RestOrderList",
    "/Game/Farm/UI/WBP_RestOrderBubble",
    "/Game/Farm/Restaurant/BP_RestGuest",
    "/Game/Farm/Restaurant/Guests/MI_GuestRed",
    "/Game/Farm/Restaurant/Guests/MI_GuestBlue",
    "/Game/Farm/Restaurant/Guests/MI_GuestGreen",
]
R["assets"] = {p: eas.does_asset_exist(p) for p in eas_check}
log("assets " + str(R["assets"]))

out = unreal.Paths.project_saved_dir() + "RestaurantUI_FINAL_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("FINAL " + out)
