# -*- coding: utf-8 -*-
"""Probe camera springarm, floor, hoe, playerstart."""
import unreal

def log(m):
    unreal.log("[PROBE] " + str(m))
    print("[PROBE] " + str(m))

BP = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

bp = unreal.EditorAssetLibrary.load_asset(BP)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cname = obj.get_class().get_name()
    name = str(lib.get_variable_name(data))
    if "SpringArm" in cname or name == "SpringArm" or cname == "CameraComponent" or name == "Camera" or "CharacterMovement" in cname:
        log("COMP {} name={}".format(cname, name))
        try:
            r = obj.get_editor_property("relative_rotation")
            log("  rel_rot p={:.1f} y={:.1f} r={:.1f}".format(r.pitch, r.yaw, r.roll))
        except Exception as e:
            log("  no rel_rot " + str(e))
        for prop in ("target_arm_length", "ortho_width", "projection_mode",
                     "do_collision_test", "use_pawn_control_rotation",
                     "inherit_pitch", "inherit_yaw", "orient_rotation_to_movement",
                     "b_orient_rotation_to_movement"):
            try:
                log("  {}={}".format(prop, obj.get_editor_property(prop)))
            except Exception:
                pass

hoe = []
floors = []
ps = []
vmf_near = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    loc = a.get_actor_location()
    if lab.startswith("VMF_Hoe_") or "Hoe" in lab:
        hoe.append((lab, round(loc.x), round(loc.y), round(loc.z)))
    if "Floor" in lab or "Floor" in cn or lab.startswith("CollisionFloor") or lab.startswith("FarmColl"):
        floors.append((lab, cn, round(loc.x), round(loc.y), round(loc.z), a.get_actor_scale3d()))
    if "PlayerStart" in cn or lab == "PlayerStart":
        ps.append((lab, cn, round(loc.x), round(loc.y), round(loc.z)))
    if lab.startswith("VMF_") and 1800 <= loc.x <= 2600 and 1400 <= loc.y <= 2200:
        vmf_near.append((lab, round(loc.x), round(loc.y), round(loc.z)))

log("PlayerStarts: " + str(ps))
log("Hoe count={} sample={}".format(len(hoe), hoe[:12]))
log("Floors: " + str(floors[:10]))
log("VMF near spawn count={} sample={}".format(len(vmf_near), vmf_near[:20]))

# Grid manager
for a in eas.get_all_level_actors():
    cn = a.get_class().get_name()
    if "GridManager" in cn or "Grid" in (a.get_actor_label() or ""):
        log("GRID actor {} lab={}".format(cn, a.get_actor_label()))
        for p in ("GridWidth", "GridHeight", "CellSize", "GridOrigin", "grid_width", "grid_height", "cell_size", "grid_origin"):
            try:
                log("  {}={}".format(p, a.get_editor_property(p)))
            except Exception:
                pass
log("DONE")
