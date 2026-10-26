# -*- coding: utf-8 -*-
"""Dump TillCell node titles for VisualizeCell splice + Character IA_Move."""
import unreal

bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[DUMP] " + str(m))
    print("[DUMP] " + str(m))

def dump_func(path, fname):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    g = bel.find_graph(bp, fname)
    if not g:
        log("NO GRAPH " + fname)
        return
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    if not ge:
        # try uber for character
        log("no GE for " + fname)
        return
    for n in ge.list_all_nodes():
        t = ""
        try:
            t = n.get_node_title(unreal.NodeTitleType.FULL_TITLE)
        except Exception:
            t = n.get_class().get_name()
        log("{} :: {}".format(fname, t))

dump_func("/Game/Farm/Grid/BP_GridManager", "TillCell")
dump_func("/Game/Farm/Grid/BP_GridManager", "VisualizeCell")
dump_func("/Game/Farm/Grid/BP_GridManager", "BeginPlay")
# Character event graph
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
try:
    names = [str(x) for x in bel.list_graph_names(bp)]
    log("char graphs: " + str(names))
except Exception as e:
    log("list_graph " + str(e))
for gname in ("EventGraph", "AI", "UserConstructionScript"):
    try:
        g = bel.find_graph(bp, gname)
        if not g:
            continue
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        if not ge:
            continue
        for n in ge.list_all_nodes():
            t = ""
            try:
                t = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
            except Exception:
                t = n.get_class().get_name()
            if any(k in t for k in ("Move", "IA_", "AddMovement", "Enhanced", "Forward", "Right", "Axis", "WASD", "Input")):
                log("CHAR[{}] {}".format(gname, t))
    except Exception as e:
        log("char dump " + str(e))

# PlayerStart rotation
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if (a.get_actor_label() or "") == "PlayerStart" or a.get_class().get_name() == "PlayerStart":
        r = a.get_actor_rotation()
        log("PS loc={} rot={}".format(a.get_actor_location(), r))

# Character CDO rotation use
try:
    cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    cdo = unreal.get_default_object(cbp.generated_class())
    for p in ("use_controller_rotation_yaw", "b_use_controller_rotation_yaw",
              "use_controller_rotation_pitch", "use_controller_rotation_roll"):
        try:
            log("charCDO {}={}".format(p, cdo.get_editor_property(p)))
        except Exception:
            pass
except Exception as e:
    log("cdo " + str(e))

log("DONE")
