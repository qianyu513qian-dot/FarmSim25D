# -*- coding: utf-8 -*-
"""Harden AirWall_Water_* collision: BlockAll + QueryAndPhysics + Block Pawn channel."""
import unreal

TAG = "[AIRWALL_HARDEN]"
def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
n = 0
fail = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not lab.startswith("AirWall_Water_"):
        continue
    smc = a.static_mesh_component
    if not smc:
        fail += 1
        continue
    try:
        a.set_actor_enable_collision(True)
    except Exception:
        pass
    try:
        a.set_actor_hidden_in_game(True)
    except Exception:
        pass
    try:
        smc.set_visibility(False, True)
    except Exception:
        pass
    try:
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception as ex:
        log("set_collision_enabled: " + str(ex))
    # Profile
    for prop, val in (("collision_profile_name", "BlockAll"), ("CollisionProfileName", "BlockAll")):
        try:
            smc.set_editor_property(prop, val)
            break
        except Exception:
            pass
    # Body instance responses
    try:
        bi = smc.get_editor_property("body_instance")
        try:
            bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        except Exception:
            pass
        try:
            bi.set_editor_property("collision_profile_name", "BlockAll")
        except Exception:
            pass
        smc.set_editor_property("body_instance", bi)
    except Exception as ex:
        if n == 0:
            log("body_instance: " + str(ex))
    # Explicit pawn block
    try:
        smc.set_collision_response_to_channel(unreal.CollisionChannel.PAWN, unreal.CollisionResponse.BLOCK)
    except Exception:
        try:
            smc.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponse.ECR_BLOCK)
        except Exception as ex:
            if n == 0:
                log("pawn channel: " + str(ex))
    try:
        smc.set_collision_response_to_all_channels(unreal.CollisionResponse.BLOCK)
    except Exception:
        try:
            smc.set_collision_response_to_all_channels(unreal.CollisionResponse.ECR_BLOCK)
        except Exception as ex:
            if n == 0:
                log("all channels: " + str(ex))
    n += 1

log("hardened n={} fail={}".format(n, fail))
# Sample one via component methods
for a in eas.get_all_level_actors():
    if (a.get_actor_label() or "").startswith("AirWall_Water_0_0"):
        smc = a.static_mesh_component
        try:
            log("sample enabled={}".format(smc.get_collision_enabled()))
        except Exception as e:
            log("get_collision_enabled " + str(e))
        try:
            log("sample profile={}".format(smc.get_collision_profile_name()))
        except Exception as e:
            log("get_profile " + str(e))
        break

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.EditorAssetLibrary.save_directory("/Game/__ExternalActors__/TopDown/Lvl_TopDown", True, True)
except Exception as e:
    log("save " + str(e))
log("DONE")
