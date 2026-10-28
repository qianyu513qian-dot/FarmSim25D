# -*- coding: utf-8 -*-
"""Probe restaurant BPs, FarmClock, character IA chain before knife2."""
import unreal, json
bel = unreal.BlueprintEditorLibrary

def bp_info(path):
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        return {"exists": False}
    bp = unreal.EditorAssetLibrary.load_asset(path)
    vars_ = []
    try:
        for n in bel.list_member_variable_names(bp):
            vars_.append(str(n))
    except Exception as e:
        vars_ = ["err:"+str(e)]
    funcs = []
    try:
        # list function graphs
        for g in bel.get_all_graphs(bp) if hasattr(bel, "get_all_graphs") else []:
            funcs.append(str(g.get_name()))
    except Exception:
        pass
    # try ubergraph + named
    try:
        eg = bel.find_event_graph(bp)
        if eg: funcs.append("EventGraph:"+eg.get_name())
    except Exception: pass
    for fname in ("RestaurantInteract", "HandlePlayerE", "TryPlayerInteract", "ToggleOpen", "TickGuest"):
        try:
            g = bel.find_graph(bp, fname) if hasattr(bel, "find_graph") else None
            if g: funcs.append("fn:"+fname)
        except Exception: pass
    # nodes in event graph sample
    nodes = []
    try:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
        for n in ge.list_all_nodes()[:40]:
            nodes.append(bel.get_node_title(n))
    except Exception as e:
        nodes = [str(e)]
    return {"exists": True, "vars": vars_, "funcs_graphs": funcs, "event_nodes_sample": nodes}

# FarmClock C++ class
fc = {}
try:
    cls = unreal.load_class(None, "/Script/FarmSim25D.FarmClock")
    fc["class"] = str(cls)
except Exception as e:
    fc["class_err"] = str(e)
# find FarmClock actor in level
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if "FarmClock" in (a.get_actor_label() or "") or "FarmClock" in a.get_class().get_name():
        fc["actor"] = a.get_actor_label()
        fc["cls"] = a.get_class().get_name()
        # list properties
        props = []
        for name in ("Minutes", "minutes", "State", "CurrentMinutes", "GetMinutes", "TimeOfDayMinutes"):
            try:
                v = a.get_editor_property(name)
                props.append({name: str(v)[:120]})
            except Exception:
                pass
        fc["props_try"] = props
        break

# Character IA
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
chain = []
all_near_ia = []
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IA_Interact" in t or t == "TillSoil" or "Rest" in t:
        pins = []
        for p in bel.list_all_pins(n):
            pins.append("{}:{} linked={}".format(p.get_pin_name(), p.get_pin_direction(),
                [bel.get_node_title(cp.get_owning_node()) for cp in p.list_connected_pins()][:4]))
        all_near_ia.append({"title": t, "pins": pins[:12]})
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "Started":
                for cp in p.list_connected_pins():
                    chain.append(bel.get_node_title(cp.get_owning_node()))

rep = {
    "bps": {
        "Interactable": bp_info("/Game/Farm/Restaurant/BP_RestaurantInteractable"),
        "Table": bp_info("/Game/Farm/Restaurant/BP_RestaurantTable"),
        "Stove": bp_info("/Game/Farm/Restaurant/BP_RestaurantStove"),
        "Trash": bp_info("/Game/Farm/Restaurant/BP_RestaurantTrash"),
        "Sign": bp_info("/Game/Farm/Restaurant/BP_RestaurantOpenSign"),
        "Manager": bp_info("/Game/Farm/Restaurant/BP_RestaurantManager"),
    },
    "farmclock": fc,
    "ia_started": chain,
    "ia_nodes": all_near_ia,
    "total_actors": len(eas.get_all_level_actors()),
}
# FarmClock.h via reading is external - try unreal reflection
try:
    cls = unreal.FarmClock
    fc_methods = [x for x in dir(cls) if not x.startswith("_") and ("minut" in x.lower() or "time" in x.lower() or "state" in x.lower() or "get" in x.lower())]
    rep["farmclock_py"] = fc_methods[:40]
except Exception as e:
    rep["farmclock_py"] = str(e)

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_probe.json","w",encoding="utf-8").write(json.dumps(rep,ensure_ascii=False,indent=2))
print(json.dumps(rep, ensure_ascii=False, indent=2))
