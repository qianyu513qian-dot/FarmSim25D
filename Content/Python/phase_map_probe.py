# -*- coding: utf-8 -*-
"""Probe GridManager CDO/instance + PlayerStart for farm map alignment."""
import unreal

MGR_PATH = "/Game/Farm/Grid/BP_GridManager"
LEVEL = "Lvl_TopDown"

def log(msg):
    unreal.log("[MAP_PROBE] " + str(msg))

def get_var_default(bp, name):
    try:
        # BlueprintEditorLibrary / generated class CDO
        gen = bp.generated_class
        cdo = unreal.get_default_object(gen)
        try:
            return cdo.get_editor_property(name)
        except Exception:
            pass
        # try snake/camel
        for alt in [name, name[0].lower()+name[1:]]:
            try:
                return getattr(cdo, alt)
            except Exception:
                pass
    except Exception as e:
        return "ERR:"+str(e)
    return None

def main():
    log("=== START ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR_PATH)
    log("BP=" + str(bp))
    if bp:
        for name in ["CellSize", "GridWidth", "GridHeight", "GridOrigin", "PlotStates"]:
            v = get_var_default(bp, name)
            log("CDO.{} = {}".format(name, v))
        # Also list new variables via BlueprintEditorLibrary
        try:
            bel = unreal.BlueprintEditorLibrary
            if hasattr(bel, "get_new_variables"):
                vars = bel.get_new_variables(bp)
                for v in vars:
                    try:
                        vn = v.get_editor_property("VarName") if hasattr(v, "get_editor_property") else str(v)
                    except Exception:
                        vn = str(v)
                    log("VAR:" + str(vn) + " -> " + str(v))
        except Exception as e:
            log("get_new_variables: " + str(e))

    # Level actors
    eas = unreal.EditorActorSubsystem()
    actors = eas.get_all_level_actors()
    log("actors_count=" + str(len(actors)))
    for a in actors:
        cls = a.get_class().get_name()
        label = a.get_actor_label()
        loc = a.get_actor_location()
        if "Grid" in cls or "Grid" in label or "PlayerStart" in cls or "PlayerStart" in label or "TopDownCharacter" in cls or "Farm" in label or "Farm" in cls:
            log("ACTOR {} label={} loc=({}, {}, {}) class={}".format(
                a.get_name(), label, loc.x, loc.y, loc.z, cls))
            # if GridManager, read instance props
            if "GridManager" in cls or "GridManager" in label:
                for name in ["CellSize", "GridWidth", "GridHeight", "GridOrigin"]:
                    try:
                        v = a.get_editor_property(name)
                        log("  INST.{}={}".format(name, v))
                    except Exception as e:
                        try:
                            v = a.get_editor_property(name[0].lower()+name[1:])
                            log("  INST.{}={}".format(name, v))
                        except Exception as e2:
                            log("  INST.{} ERR {}".format(name, e2))

    # World / level info
    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
        log("world=" + str(world))
    except Exception as e:
        log("world err " + str(e))
    try:
        # Current level path
        soft = unreal.SystemLibrary.get_object_path(unreal.EditorLevelLibrary.get_editor_world())
        log("world_path=" + str(soft))
    except Exception as e:
        log("world_path err " + str(e))

    log("=== END ===")

main()
