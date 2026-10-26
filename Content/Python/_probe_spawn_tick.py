# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[SPAWNCHK] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# All playerstarts, pawns, characters in level
for a in eas.get_all_level_actors():
    cn = a.get_class().get_name()
    lab = a.get_actor_label()
    name = a.get_name()
    if any(k in cn or k in lab or k in name for k in (
        "PlayerStart", "Character", "Pawn", "TopDown", "GridManager", "DefaultPawn")):
        loc = a.get_actor_location()
        log("ACTOR %s label=%s cls=%s loc=(%.1f,%.1f,%.1f)" % (name, lab, cn, loc.x, loc.y, loc.z))

# GameMode defaults
for path in ("/Game/TopDown/Blueprints/BP_TopDownGameMode",
             "/Game/TopDown/Blueprints/BP_TopDownPlayerController",
             "/Game/TopDown/Variant_Strategy/Blueprints/BP_StrategyPlayerController",
             "/Game/TopDown/Variant_Strategy/Blueprints/BP_StrategyGameMode"):
    exists = unreal.EditorAssetLibrary.does_asset_exist(path)
    log("asset %s exist=%s" % (path, exists))

# World settings / game mode override on level
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
except Exception:
    world = None
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = les.get_current_level()  # may be ULevel
    log("current level type " + str(type(world)))
except Exception as e:
    log("les " + str(e))

# Dump Format Text + Tick chain details
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
tick = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "Tick" in bel.get_node_title(n):
        tick = n
        break

def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

# BFS from tick
if tick:
    start = find_pin(tick, "then", "Output") or bel.find_then_pin(tick)
    frontier = [cp.get_owning_node() for cp in list(start.list_connected_pins())] if start else []
    seen = set()
    order = []
    while frontier and len(order) < 40:
        n = frontier.pop(0)
        if id(n) in seen:
            continue
        seen.add(id(n))
        order.append(n)
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()):
                for cp in list(p.list_connected_pins()):
                    frontier.append(cp.get_owning_node())
    log("TICK CHAIN len=%d" % len(order))
    for n in order:
        title = bel.get_node_title(n)
        cls = n.get_class().get_name()
        bits = []
        for p in bel.list_all_pins(n):
            pn = str(p.get_pin_name())
            try:
                dv = str(p.get_default_as_string())
            except Exception:
                dv = ""
            conns = []
            try:
                for cp in list(p.list_connected_pins()):
                    conns.append("%s@%s" % (cp.get_pin_name(), bel.get_node_title(cp.get_owning_node())[:40]))
            except Exception:
                pass
            if conns or (dv and dv not in ("", "0", "0.0", "None", "false", "true", "True", "False")):
                bits.append("%s dv=%s ->[%s]" % (pn, dv[:40], ";".join(conns)[:100]))
        log("  %s | %s" % (title[:80], " || ".join(bits)[:300]))

# WorldToGrid wiring
bp2 = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp2, "WorldToGrid"))
log("=== WorldToGrid wiring ===")
for n in ge2.list_all_nodes():
    title = bel.get_node_title(n)
    bits = []
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        try:
            dv = str(p.get_default_as_string())
        except Exception:
            dv = ""
        conns = []
        for cp in list(p.list_connected_pins()):
            conns.append("%s@%s" % (cp.get_pin_name(), bel.get_node_title(cp.get_owning_node())[:40]))
        if conns or dv not in ("", "0", "0.0", "None", "false", "true", "True", "False", None):
            bits.append("%s dv=%s ->[%s]" % (pn, dv[:40], ";".join(conns)[:120]))
    log("  %s | %s" % (title[:60], " || ".join(bits)[:350]))

log("DONE")