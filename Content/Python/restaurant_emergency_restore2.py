# -*- coding: utf-8 -*-
"""Restore IA_Interact Started -> TillSoil only; strip restaurant graph helpers."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
REPORT = {"steps": [], "ia_chain": [], "rest_left": []}

def log(m):
    unreal.log("[EM_RESTORE] " + str(m))
    REPORT["steps"].append(str(m))

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

cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

ia = till = None
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IA_Interact" in t: ia = n
    if t == "TillSoil": till = n

started = find_pin(ia, "Started", "Output") if ia else None
log("ia={} till={} started={}".format(ia is not None, till is not None, started is not None))

# Walk from Started and collect restaurant helper nodes (keep TillSoil, IA)
kill = []
if started:
    stack = list(started.list_connected_pins())
    seen = set()
    while stack:
        p = stack.pop(0)
        n = p.get_owning_node()
        if id(n) in seen: continue
        seen.add(id(n))
        t = bel.get_node_title(n)
        if t == "TillSoil" or "IA_Interact" in t:
            continue
        kill.append(n)
        for pp in bel.list_all_pins(n):
            for cp in pp.list_connected_pins():
                stack.append(cp)

# Also kill by title keywords leftover
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if any(k in t for k in ("GetAllActorsWithTag", "For Each Loop", "Distance2D", "Concat_StrStr", "GetDisplayName", "GetActorLabel")):
        kill.append(n)
    if t == "PrintString":
        for p in bel.list_all_pins(n):
            if "string" in str(p.get_pin_name()).lower():
                try:
                    dv = str(p.get_default_value() or "")
                except Exception:
                    dv = ""
                if any(k in dv for k in ("Restaurant", "RestInteract", "E:", "OPEN", "STOVE", "TABLE", "TRASH")):
                    kill.append(n)
    if "Cast To BP_Restaurant" in t:
        kill.append(n)

kill = [n for n in kill if bel.get_node_title(n) != "TillSoil" and "IA_Interact" not in bel.get_node_title(n)]
kill = list({id(n): n for n in kill}.values())
if kill:
    cge.remove_nodes(kill)
    log("removed {}".format(len(kill)))
else:
    log("no helpers to remove")

# Break Started and reconnect to TillSoil
if started:
    try:
        bel.break_pin_links(started)
    except Exception:
        for cp in list(started.list_connected_pins()):
            try: started.break_link_to(cp)
            except Exception: pass
    log("started_links_after_break={}".format(len(list(started.list_connected_pins()))))

till_exec = find_pin(till, "execute", "Input") if till else None
ok = connect(started, till_exec, "IA->TillSoil")

bel.compile_blueprint(cbp)
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
log("character_saved")

# Verify chain
chain = []
if started:
    for cp in started.list_connected_pins():
        chain.append(bel.get_node_title(cp.get_owning_node()))
REPORT["ia_chain"] = chain

# Confirm no restaurant actors
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        REPORT["rest_left"].append(lab)
REPORT["total_actors"] = len(eas.get_all_level_actors())

# Save level again to flush
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level_saved_via_LES")
except Exception as e:
    try:
        unreal.EditorLevelLibrary.save_current_level(); log("level_saved_legacy")
    except Exception as e2:
        log("level_save_fail "+str(e2))

open(r"E:\UE\FarmSim25D\Saved\restaurant_emergency_restore2.json","w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
