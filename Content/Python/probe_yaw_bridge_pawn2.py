# -*- coding: utf-8 -*-
"""Deeper probe: all character-like actors, gamemode, bridge mesh sizes."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def log(m):
    unreal.log("[PROBE2] " + str(m))
    print("[PROBE2] " + str(m))

# All actors whose class/label smells like a pawn
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    cls = a.get_class().get_name()
    path = ""
    try:
        path = a.get_path_name()
    except Exception:
        pass
    hit = False
    for k in ("Character", "Pawn", "Mannequin", "Player", "DefaultPawn", "Spectator", "TopDown", "Farmer", "NPC"):
        if k.lower() in cls.lower() or k.lower() in lab.lower():
            hit = True
            break
    if hit:
        loc = a.get_actor_location()
        log("HIT lab={} cls={} path={} @({:.0f},{:.0f},{:.0f})".format(lab, cls, path, loc.x, loc.y, loc.z))

# World settings / game mode
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    ws = world.get_world_settings()
    log("WorldSettings={}".format(ws))
    try:
        gm = ws.get_editor_property("default_game_mode")
        log("default_game_mode={}".format(gm))
    except Exception as e:
        log("gm prop: " + str(e))
    try:
        gmoh = ws.get_editor_property("game_mode_override")
        log("game_mode_override={}".format(gmoh))
    except Exception as e:
        log("gmoh: " + str(e))
except Exception as e:
    log("world err " + str(e))

# Check BP_TopDownGameMode default pawn
for p in (
    "/Game/TopDown/Blueprints/BP_TopDownGameMode",
    "/Game/TopDown/Blueprints/BP_TopDownPlayerController",
    "/Game/TopDown/Blueprints/BP_TopDownCharacter",
):
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        a = unreal.EditorAssetLibrary.load_asset(p)
        log("asset {} class={}".format(p, a.get_class().get_name() if a else None))
        if a and "GameMode" in p:
            try:
                cdo = unreal.get_default_object(a.generated_class()) if hasattr(a, "generated_class") else None
                if cdo:
                    for prop in ("default_pawn_class", "DefaultPawnClass", "hud_class"):
                        try:
                            log("  {}={}".format(prop, cdo.get_editor_property(prop)))
                        except Exception:
                            pass
            except Exception as e:
                log("  cdo err " + str(e))

# Bridge sample mesh info
n_bridge = 0
n_rail = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not lab.startswith("VMF_Bridge"):
        continue
    if "Rail" in lab or "Post" in lab:
        n_rail += 1
    else:
        n_bridge += 1
    if n_bridge + n_rail <= 4 or ("Rail" in lab and n_rail <= 2):
        try:
            smc = a.static_mesh_component
            mesh = smc.get_editor_property("static_mesh")
            sc = smc.get_editor_property("relative_scale3d")
            log("bridge {} mesh={} scale=({},{},{}) rot={}".format(
                lab, mesh.get_name() if mesh else None, sc.x, sc.y, sc.z, a.get_actor_rotation()))
        except Exception as e:
            log("bridge info err " + str(e))
log("totals deckish~ bridge_nonrail count via labels: will recount")
deck = rail = post = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not lab.startswith("VMF_Bridge"):
        continue
    if "Rail" in lab:
        rail += 1
    elif "Post" in lab:
        post += 1
    else:
        deck += 1
log("Bridge deck={} rail={} post={}".format(deck, rail, post))

# PlayerStart details
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "PlayerStart":
        log("PlayerStart label={} rot={} loc={}".format(
            a.get_actor_label(), a.get_actor_rotation(), a.get_actor_location()))
