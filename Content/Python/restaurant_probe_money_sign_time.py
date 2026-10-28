# -*- coding: utf-8 -*-
"""Probe: pay events, OpenSign, Money, FarmClock, IMC keys."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
R = {"steps": []}

def log(m):
    unreal.log("[PROBE_BATCH] " + str(m))
    print("[PROBE_BATCH] " + str(m))
    R["steps"].append(str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def walk_then(start, max_d=30):
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

def dump_custom_chains(path, names):
    bp = unreal.load_asset(path)
    if not bp:
        log("MISSING " + path); return
    g = bel.find_event_graph(bp) or bel.find_graph(bp, "EventGraph")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    out = {}
    for n in ge.list_all_nodes():
        if n.get_class().get_name() != "K2Node_CustomEvent":
            continue
        t = title(n)
        if t in names or any(nm in t for nm in names):
            chain = [title(x) for x in walk_then(n)]
            out[t] = chain
    R[path.split("/")[-1]] = out
    log(path.split("/")[-1] + " customs: " + str(list(out.keys())))

dump_custom_chains("/Game/Farm/Restaurant/BP_RestaurantManager",
                   ["OnGuestPaidSalad", "OnGuestPaidStew", "HandlePlayerE", "RefreshOrderUI"])

# OpenSign RestaurantInteract graph
osbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantOpenSign")
R["opensign_vars"] = list(bel.list_member_variable_names(osbp)) if hasattr(bel, "list_member_variable_names") else []
log("opensign vars: " + str(R["opensign_vars"][:40]))

# Try find RestaurantInteract graph
graphs = []
for gname in ("EventGraph", "RestaurantInteract"):
    try:
        g = bel.find_graph(osbp, gname)
        if g:
            ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
            nodes = [title(n) for n in ge.list_all_nodes()]
            graphs.append({"name": gname, "nodes": nodes[:60]})
    except Exception as e:
        graphs.append({"name": gname, "err": str(e)})
R["opensign_graphs"] = graphs

# Character
cbp = unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
R["char_vars"] = [v for v in bel.list_member_variable_names(cbp) if any(k in str(v) for k in ("Money", "HUD", "Seed", "Crop", "Farm", "Clock", "Skip"))]
log("char vars: " + str(R["char_vars"]))

# UpdateFarmHUD graph
try:
    ug = bel.find_graph(cbp, "UpdateFarmHUD")
    if ug:
        uge = unreal.BlueprintGraphEditor.get_graph_editor(ug)
        R["UpdateFarmHUD_nodes"] = [title(n) for n in uge.list_all_nodes()][:40]
        log("UpdateFarmHUD nodes=" + str(len(R["UpdateFarmHUD_nodes"])))
    else:
        log("no UpdateFarmHUD graph")
except Exception as e:
    R["uhud_err"] = str(e)

# EventGraph look for EnhancedInput
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia_nodes = []
for n in cge.list_all_nodes():
    t = title(n)
    if "Input" in t or "IA_" in t or "Enhanced" in t or "Skip" in t:
        ia_nodes.append(t)
R["char_input_nodes"] = ia_nodes[:50]
log("char input-ish: " + str(ia_nodes[:30]))

# IMC assets
imc_hits = []
for a in unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False):
    an = a.split("/")[-1]
    if an.startswith("IMC_") or an.startswith("IA_") or "InputMapping" in a:
        imc_hits.append(a)
R["input_assets"] = imc_hits[:60]
log("input assets n=" + str(len(imc_hits)))

# OpenSign CDO comps
try:
    cdo = unreal.get_default_object(osbp.generated_class())
    comps = []
    for c in cdo.get_components_by_class(unreal.PrimitiveComponent.static_class()):
        comps.append(c.get_name() + ":" + c.get_class().get_name())
    for c in cdo.get_components_by_class(unreal.ActorComponent.static_class()):
        if "Mesh" in c.get_class().get_name() or "Text" in c.get_class().get_name() or "Billboard" in c.get_class().get_name():
            comps.append(c.get_name() + ":" + c.get_class().get_name())
    R["opensign_comps"] = list(dict.fromkeys(comps))
except Exception as e:
    R["opensign_comps_err"] = str(e)

# FarmClock
try:
    methods = [m for m in dir(unreal.FarmClock) if not m.startswith("_") and any(k in m.lower() for k in ("minute", "clock", "restore", "display", "pause", "advance", "state"))]
    R["farmclock_methods"] = methods
except Exception as e:
    R["farmclock_err"] = str(e)

# Manager vars
mbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
R["mgr_vars"] = [v for v in bel.list_member_variable_names(mbp) if any(k in str(v) for k in ("Money", "Open", "Held", "Guest", "Order"))]
log("mgr vars: " + str(R["mgr_vars"]))

out = unreal.Paths.project_saved_dir() + "restaurant_probe_money_sign_time.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, indent=2, ensure_ascii=False)
log("WROTE " + out)
