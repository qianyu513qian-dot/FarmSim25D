# -*- coding: utf-8 -*-
"""Probe BP_TopDownCharacter camera/springarm defaults via SCS."""
import unreal

def log(m):
    unreal.log("[CAMPPROBE] " + str(m))

path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(path)
log("bp=" + str(bp) + " type=" + str(type(bp)))

# Try SimpleConstructionScript components
try:
    scs = bp.simple_construction_script
    nodes = scs.get_all_nodes()
    log("scs nodes=" + str(len(nodes)))
    for n in nodes:
        try:
            tmpl = n.component_template
            cname = n.variable_name if hasattr(n, "variable_name") else n.get_variable_name()
            log("node var=" + str(cname) + " tmpl=" + str(type(tmpl).__name__))
            if tmpl is None:
                continue
            # relative rotation / location
            try:
                rr = tmpl.get_editor_property("relative_rotation")
                rl = tmpl.get_editor_property("relative_location")
                log("  relRot=({},{},{}) relLoc=({},{},{})".format(
                    rr.pitch, rr.yaw, rr.roll, rl.x, rl.y, rl.z))
            except Exception as e:
                log("  rel fail " + str(e))
            for prop in ["target_arm_length", "socket_offset", "target_offset",
                         "b_use_pawn_control_rotation", "b_do_collision_test",
                         "b_inherit_pitch", "b_inherit_yaw", "b_inherit_roll",
                         "projection_mode", "ortho_width", "ortho_near_clip_plane",
                         "field_of_view", "aspect_ratio"]:
                try:
                    v = tmpl.get_editor_property(prop)
                    log("  {}={}".format(prop, v))
                except Exception:
                    pass
        except Exception as e:
            log("node err " + str(e))
except Exception as e:
    log("scs fail " + str(e))

# Also try Controller
path2 = "/Game/TopDown/Blueprints/BP_TopDownController"
bp2 = unreal.EditorAssetLibrary.load_asset(path2)
log("controller=" + str(bp2))
try:
    scs2 = bp2.simple_construction_script
    nodes2 = scs2.get_all_nodes()
    log("ctrl nodes=" + str(len(nodes2)))
    for n in nodes2:
        try:
            tmpl = n.component_template
            cname = n.get_variable_name() if hasattr(n, "get_variable_name") else getattr(n, "variable_name", "?")
            log("ctrl node=" + str(cname) + " " + str(type(tmpl).__name__ if tmpl else None))
            if tmpl:
                for prop in ["target_arm_length", "relative_rotation", "projection_mode", "ortho_width"]:
                    try:
                        v = tmpl.get_editor_property(prop)
                        log("  {}={}".format(prop, v))
                    except Exception:
                        pass
        except Exception as e:
            log("ctrl node err " + str(e))
except Exception as e:
    log("ctrl scs fail " + str(e))

# Default object of generated class
try:
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    log("CDO=" + str(cdo))
    for c in cdo.get_components_by_class(unreal.SceneComponent):
        cn = c.get_name()
        log("CDO comp " + cn + " " + c.get_class().get_name())
        try:
            rr = c.get_relative_rotation()
            rl = c.get_relative_location()
            log("  rot=({},{},{}) loc=({},{},{})".format(rr.pitch, rr.yaw, rr.roll, rl.x, rl.y, rl.z))
        except Exception:
            pass
        for prop in ["target_arm_length", "projection_mode", "ortho_width", "field_of_view"]:
            try:
                log("  {}={}".format(prop, c.get_editor_property(prop)))
            except Exception:
                pass
except Exception as e:
    log("CDO fail " + str(e))
