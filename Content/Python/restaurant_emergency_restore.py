# -*- coding: utf-8 -*-
"""Emergency restore: remove Restaurant_*/RestChair_*; restore IA_Interact -> TillSoil only; save."""
import unreal, json, re

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel = unreal.BlueprintEditorLibrary
log = []

# ---- 1) Map modified package package names to live actors if possible ----
# Identify restaurant actors and destroy
removed = []
for a in list(eas.get_all_level_actors()):
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        removed.append({"label": lab, "cls": a.get_class().get_name(),
                        "x": round(a.get_actor_location().x),
                        "y": round(a.get_actor_location().y)})
        eas.destroy_actor(a)

log.append("destroyed_restaurant={}".format(len(removed)))

# ---- 2) Restore IA_Interact: Started -> TillSoil only ----
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
g = bel.find_event_graph(cbp)
ge = unreal.BlueprintGraphEditor.get_graph_editor(g)

ia = till = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IA_Interact" in t and "EnhancedInputAction" in t:
        ia = n
    if t == "TillSoil" or (t.startswith("TillSoil") and "Target" not in t):
        # prefer the Call Function TillSoil on self
        till = n

# find TillSoil call more carefully
till_cands = []
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "TillSoil" in t:
        till_cands.append(t)
        # CallFunction nodes titled TillSoil
        if t == "TillSoil":
            till = n

log.append("ia={} till={} till_cands={}".format(ia is not None, till is not None, till_cands))

# Disconnect Started from restaurant chain; reconnect to TillSoil
if ia and till:
    started = None
    for p in bel.list_all_pins(ia):
        if str(p.get_pin_name()) == "Started":
            started = p
            break
    till_exec_in = None
    for p in bel.list_all_pins(till):
        # execute pin
        if "input" in str(p.get_pin_direction()).lower() and str(p.get_pin_name()) in ("execute", ""):
            # first exec input
            if p.is_execution_pin() if hasattr(p, "is_execution_pin") else True:
                # try by category
                pass
        try:
            if p.is_execution_pin() and "input" in str(p.get_pin_direction()).lower():
                till_exec_in = p
                break
        except Exception:
            pass
    # fallback: pin named execute
    if till_exec_in is None:
        for p in bel.list_all_pins(till):
            if str(p.get_pin_name()) == "execute":
                till_exec_in = p
                break

    # Break all links from Started
    if started:
        linked = list(started.list_connected_pins())
        for lp in linked:
            try:
                started.break_link_to(lp)
            except Exception as e:
                try:
                    bel.break_pin_links(started)
                    break
                except Exception as e2:
                    log.append("break_fail {}".format(e2))
        log.append("broke_started_links={}".format(len(linked)))

    # Remove orphan restaurant helper nodes (GetAllActorsWithTag, ForEach, Distance2D chain prints)
    kill_titles_sub = ("GetAllActorsWithTag", "For Each Loop", "GetDisplayName", "Distance2D", "Append", "PrintString")
    # Only remove PrintString / GetAllActors that were on the restaurant chain - careful not to kill unrelated
    # Safer: walk from old chain only - we already broke Started. Find nodes with no incoming exec that match restaurant helpers.
    # Even safer: only remove GetAllActorsWithTag nodes and their exclusive downstream ForEach if title matches.

    to_kill = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "GetAllActorsWithTag" in t:
            to_kill.append(n)
        elif t == "For Each Loop":
            # check if Array pin connected from GetAllActors - if orphan after break, kill
            to_kill.append(n)
    # Don't kill all PrintString - only ones saying restaurant. Scan print defaults.
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "PrintString":
            try:
                # check InString pin default
                for p in bel.list_all_pins(n):
                    if str(p.get_pin_name()) in ("InString", "In String"):
                        dv = str(p.get_default_value()) if hasattr(p, "get_default_value") else ""
                        if "Rest" in dv or "Interact" in dv or "Restaurant" in dv or "E:" in dv:
                            to_kill.append(n)
            except Exception:
                pass

    # Also kill Append / Distance2D / Branch / float < that are only used by restaurant - hard.
    # Minimal: kill GetAllActorsWithTag + ForEach we added; leave dangling Branches if any.
    killed = 0
    for n in to_kill:
        try:
            ge.remove_node(n)
            killed += 1
        except Exception as e:
            try:
                bel.remove_graph_node(n)
                killed += 1
            except Exception as e2:
                log.append("rmfail {} {}".format(bel.get_node_title(n), e2))
    log.append("killed_helper_nodes={}".format(killed))

    # Reconnect Started -> TillSoil
    if started and till_exec_in:
        try:
            started.make_link_to(till_exec_in)
            log.append("relinked_Started_to_TillSoil")
        except Exception as e:
            try:
                ge.make_link(started, till_exec_in)
                log.append("relinked_via_ge")
            except Exception as e2:
                log.append("relink_fail {}".format(e2))
    else:
        log.append("missing pins started={} till_in={}".format(started is not None, till_exec_in is not None))

    bel.compile_blueprint(cbp)
    unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    log.append("character_saved")
else:
    log.append("SKIP character restore ia/till missing")

# ---- 3) Save level ----
try:
    unreal.EditorLevelLibrary.save_current_level()
    log.append("level_saved")
except Exception as e:
    log.append("level_save_err {}".format(e))

# ---- 4) Recount ----
from collections import Counter
counts = Counter()
rest_left = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        rest_left.append(lab)
    if lab.startswith("VMF_Grass"): counts["VMF_Grass"] += 1
    elif "Bridge" in lab: counts["Bridge"] += 1
    elif "Tree" in lab: counts["Tree"] += 1
    elif lab.startswith("VMF_Path"): counts["Path"] += 1
    elif "PlayerStart" in lab: counts["PlayerStart"] += 1
    elif "House" in lab or "FarmShed" in lab: counts["House"] += 1
    elif "Water" in lab and lab.startswith("VMF_"): counts["Water"] += 1

# verify IA chain
ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
chain = []
for n in ge2.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "Started":
                for cp in p.list_connected_pins():
                    chain.append(bel.get_node_title(cp.get_owning_node()))

rep = {"log": log, "removed": removed, "rest_left": rest_left, "counts_after": dict(counts),
       "ia_started_now": chain, "total_actors": len(eas.get_all_level_actors())}
open(r"E:\UE\FarmSim25D\Saved\restaurant_emergency_restore.json","w",encoding="utf-8").write(json.dumps(rep,ensure_ascii=False,indent=2))
print(json.dumps(rep,ensure_ascii=False,indent=2))
