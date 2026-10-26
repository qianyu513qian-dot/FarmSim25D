# -*- coding: utf-8 -*-
"""Deeper camera probe: controller CDO, inherited components, BP parent."""
import unreal

def log(m):
    unreal.log("[CAMP2] " + str(m))

def dump_cdo(path):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    if not bp:
        log("missing " + path)
        return
    try:
        gen = bp.generated_class()
    except Exception:
        gen = None
    log("=== " + path + " gen=" + str(gen))
    if not gen:
        return
    cdo = unreal.get_default_object(gen)
    log("CDO class=" + cdo.get_class().get_name())
    # all components
    try:
        comps = cdo.get_components_by_class(unreal.ActorComponent)
        log("comps count=" + str(len(comps)))
        for c in comps:
            log("  " + c.get_name() + " | " + c.get_class().get_name())
    except Exception as e:
        log("comps err " + str(e))
    # parent class
    try:
        parent = gen.get_super_class()
        log("super=" + str(parent))
        while parent:
            pname = parent.get_name()
            log("  ancestor " + pname)
            if pname in ("Object", "Actor", "Pawn", "Character", "Controller", "PlayerController"):
                break
            try:
                parent = parent.get_super_class()
            except Exception:
                break
    except Exception as e:
        log("super err " + str(e))
    # try get_editor_property on known camera names via find
    for name in ["CameraBoom", "SpringArm", "TopDownCamera", "FollowCamera",
                 "CameraComponent", "SpringArmComponent", "Camera"]:
        try:
            c = cdo.get_editor_property(name)
            log("prop " + name + "=" + str(c) + " type=" + str(type(c)))
            if c:
                try:
                    rr = c.get_relative_rotation()
                    log("  rot p={} y={} r={}".format(rr.pitch, rr.yaw, rr.roll))
                except Exception as e:
                    log("  rot fail " + str(e))
                for prop in ["target_arm_length", "projection_mode", "ortho_width", "field_of_view",
                             "relative_rotation", "relative_location"]:
                    try:
                        log("  {}={}".format(prop, c.get_editor_property(prop)))
                    except Exception:
                        pass
        except Exception as e:
            pass

dump_cdo("/Game/TopDown/Blueprints/BP_TopDownCharacter")
dump_cdo("/Game/TopDown/Blueprints/BP_TopDownController")

# Also search for any SpringArm in /Game
assets = unreal.EditorAssetLibrary.list_assets("/Game/TopDown", recursive=True, include_folder=False)
log("TopDown assets:")
for a in assets:
    log("  " + a)

# Check GameMode default pawn / camera
for p in ["/Game/TopDown/Blueprints/BP_TopDownGameMode",
          "/Game/TopDown/Blueprints/BP_TopDownPlayerController",
          "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"]:
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        log("exists " + p)
        dump_cdo(p)

# Level camera actors
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    cls = a.get_class().get_name()
    if "Camera" in cls or "Spring" in cls:
        log("LEVEL " + a.get_actor_label() + " " + cls)
        rot = a.get_actor_rotation()
        log("  rot=({},{},{})".format(rot.pitch, rot.yaw, rot.roll))

# Try SubobjectDataSubsystem on character BP
try:
    bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    # get handles
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    log("subobject handles=" + str(len(handles)))
    for h in handles:
        try:
            data = sds.k2_find_subobject_data_from_handle(h)
            # data is SubobjectData struct-ish
            log("  handle data=" + str(data))
        except Exception as e:
            try:
                name = unreal.SubobjectDataBlueprintFunctionLibrary.get_variable_name(h)
                log("  var=" + str(name))
                obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(h)
                log("    obj=" + str(obj) + " " + (obj.get_class().get_name() if obj else ""))
                if obj and isinstance(obj, unreal.SceneComponent):
                    rr = obj.get_editor_property("relative_rotation")
                    log("    rot=({},{},{})".format(rr.pitch, rr.yaw, rr.roll))
                    for prop in ["target_arm_length", "projection_mode", "ortho_width"]:
                        try:
                            log("    {}={}".format(prop, obj.get_editor_property(prop)))
                        except Exception:
                            pass
            except Exception as e2:
                log("  sub err " + str(e) + " / " + str(e2))
except Exception as e:
    log("sds fail " + str(e))
