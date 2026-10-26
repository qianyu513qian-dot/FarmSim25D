# -*- coding: utf-8 -*-
"""Find camera setup: parent class, graph nodes, PlayerCameraManager, etc."""
import unreal

def log(m):
    unreal.log("[CAMP3] " + str(m))

# Character parent via UE reflection
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
gen = bp.generated_class()
cdo = unreal.get_default_object(gen)
# parent
try:
    parent = cdo.get_class().get_super_class() if hasattr(cdo.get_class(), "get_super_class") else None
except Exception:
    parent = None
log("class=" + cdo.get_class().get_name())
# use unreal.SystemLibrary / get_class hierarchy
cls = cdo.get_class()
for i in range(8):
    log("cls[{}]={}".format(i, cls.get_name() if cls else None))
    try:
        # UE Python: Class.get_super_class may not exist; try __class__ chain via get_editor_property ParentClass on BP
        break
    except Exception:
        break

# Blueprint parent class property
try:
    pc = bp.get_editor_property("parent_class")
    log("BP parent_class=" + str(pc))
except Exception as e:
    log("parent_class fail " + str(e))

# SubobjectDataBlueprintFunctionLibrary properly
try:
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in handles:
        try:
            # try various APIs
            for meth in ["get_variable_name", "get_display_name", "get_object_for_blueprint",
                         "get_object", "is_component", "get_blueprint"]:
                if hasattr(lib, meth):
                    try:
                        v = getattr(lib, meth)(h)
                        log("  {} -> {}".format(meth, v))
                    except Exception as e:
                        pass
            # handle methods
            if hasattr(h, "get_variable_name"):
                log("  h.get_variable_name=" + str(h.get_variable_name()))
        except Exception as e:
            log("h err " + str(e))
    # list lib methods
    meths = [m for m in dir(lib) if "get" in m.lower() or "sub" in m.lower() or "name" in m.lower()]
    log("lib meths sample: " + str(meths[:40]))
except Exception as e:
    log("sds2 fail " + str(e))

# Check controller for camera boom creation in graph - list functions
ctrl = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownController")
try:
    uber = unreal.BlueprintEditorLibrary.get_all_graphs(ctrl) if hasattr(unreal, "BlueprintEditorLibrary") else None
    log("graphs via BEL=" + str(uber))
except Exception as e:
    log("BEL " + str(e))

# Try get_editor_property CameraBoom on controller CDO with different casing
ctrl_cdo = unreal.get_default_object(ctrl.generated_class())
props_try = []
for name in dir(ctrl_cdo):
    if "cam" in name.lower() or "spring" in name.lower() or "arm" in name.lower() or "boom" in name.lower():
        props_try.append(name)
log("ctrl attrs cam/spring: " + str(props_try))

char_attrs = []
for name in dir(cdo):
    if "cam" in name.lower() or "spring" in name.lower() or "arm" in name.lower() or "boom" in name.lower():
        char_attrs.append(name)
log("char attrs cam/spring: " + str(char_attrs))

# Check if TopDownCharacter is from a C++ class that adds camera in constructor not visible on CDO components list
# Look at default values via export
try:
    # PlayerCameraManager class on controller
    pcm = ctrl_cdo.get_editor_property("player_camera_manager_class")
    log("pcm_class=" + str(pcm))
except Exception as e:
    log("pcm " + str(e))

# ViewTarget / camera style
for prop in ["b_auto_manage_active_camera_target", "smooth_target_view_rotation_speed",
             "player_camera_manager_class", "default_fov", "input_yaw_scale"]:
    try:
        log("ctrl.{}={}".format(prop, ctrl_cdo.get_editor_property(prop)))
    except Exception as e:
        pass

# Search ALL blueprints for SpringArm
assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False)
for a in assets:
    if "Camera" in a or "Spring" in a or "Boom" in a:
        log("asset hit " + a)

# Check Engine TopDown C++ - maybe camera is spawned at runtime from Controller BeginPlay
# Read BP event graphs node count without opening editor heavily
try:
    # Use AssetRegistry tags
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    data = ar.get_asset_by_object_path("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    log("asset data=" + str(data))
except Exception as e:
    log("ar " + str(e))

# Spawn a temp character in editor world and inspect components (PIE not needed - place actor)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
# load class
cls = unreal.EditorAssetLibrary.load_blueprint_class("/Game/TopDown/Blueprints/BP_TopDownCharacter")
log("load_blueprint_class=" + str(cls))
if cls:
    actor = eas.spawn_actor_from_class(cls, unreal.Vector(-5000, -5000, 200), unreal.Rotator(0,0,0))
    if actor:
        log("spawned " + actor.get_name())
        comps = actor.get_components_by_class(unreal.ActorComponent)
        for c in comps:
            log("  live " + c.get_name() + " | " + c.get_class().get_name())
            if "Spring" in c.get_class().get_name() or "Camera" in c.get_class().get_name():
                try:
                    rr = c.get_relative_rotation()
                    log("    ROT pitch={} yaw={} roll={}".format(rr.pitch, rr.yaw, rr.roll))
                except Exception:
                    pass
                for prop in ["target_arm_length", "projection_mode", "ortho_width", "field_of_view"]:
                    try:
                        log("    {}={}".format(prop, c.get_editor_property(prop)))
                    except Exception:
                        pass
        # destroy temp
        eas.destroy_actor(actor)
        log("destroyed temp")
