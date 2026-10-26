# -*- coding: utf-8 -*-
import unreal

def log(m):
    unreal.log("[FIXPROBE] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

for a in eas.get_all_level_actors():
    try:
        lab = a.get_actor_label()
    except Exception:
        continue
    if not (lab.startswith("Scene_") or lab in ("PlayerStart", "BP_GridManager", "FarmGround")):
        continue
    loc = a.get_actor_location()
    rr = a.get_actor_rotation()
    sc = a.get_actor_scale3d()
    log("%s loc=(%.1f,%.1f,%.1f) rot=p%.1f y%.1f r%.1f sc=(%.2f,%.2f,%.2f) cls=%s" % (
        lab, loc.x, loc.y, loc.z, rr.pitch, rr.yaw, rr.roll, sc.x, sc.y, sc.z, a.get_class().get_name()))

gm = None
ps = None
house = None
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab == "BP_GridManager":
        gm = a
    elif lab == "PlayerStart":
        ps = a
    elif lab == "Scene_House":
        house = a
    cn = a.get_class().get_name()
    if ps is None and ("PlayerStart" in cn or "PlayerStart" in a.get_name()):
        log("ALT_START name=%s label=%s loc=(%.1f,%.1f,%.1f)" % (
            a.get_name(), lab, a.get_actor_location().x, a.get_actor_location().y, a.get_actor_location().z))

if gm:
    for prop in ("GridWidth", "GridHeight", "CellSize", "GridOrigin"):
        try:
            log("GM.%s = %s" % (prop, gm.get_editor_property(prop)))
        except Exception as e:
            log("GM.%s FAIL %s" % (prop, e))

if ps:
    loc = ps.get_actor_location()
    log("PlayerStart at (%.1f,%.1f,%.1f) grid~(%d,%d)" % (loc.x, loc.y, loc.z, int(loc.x // 100), int(loc.y // 100)))
else:
    log("NO PlayerStart label")

if house:
    smc = house.static_mesh_component
    mesh = smc.get_editor_property("static_mesh")
    mat = smc.get_material(0)
    log("House mesh=%s mat=%s" % (mesh.get_name() if mesh else None, mat.get_path_name() if mat else None))
    try:
        log("House bounds=%s" % (house.get_actor_bounds(False),))
    except Exception as e:
        log("bounds %s" % e)

bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(bp_path)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cn = obj.get_class().get_name()
    if "SpringArm" in cn:
        rr = obj.get_editor_property("relative_rotation")
        try:
            tl = obj.get_editor_property("target_arm_length")
        except Exception:
            tl = "?"
        log("SpringArm p=%.1f y=%.1f r=%.1f len=%s" % (rr.pitch, rr.yaw, rr.roll, tl))
    if cn == "CameraComponent":
        try:
            log("Cam ortho=%s proj=%s" % (obj.get_editor_property("ortho_width"), obj.get_editor_property("projection_mode")))
        except Exception as e:
            log("cam %s" % e)

nonzero = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if not lab.startswith("Scene_"):
        continue
    rr = a.get_actor_rotation()
    if abs(rr.pitch) > 0.1 or abs(rr.yaw) > 0.1 or abs(rr.roll) > 0.1:
        nonzero += 1
log("nonzero_rot_Scene=%d" % nonzero)

for p in ("/Game/Farm/Art/Mats/M_House", "/Game/Farm/Art/Mats/M_Water",
          "/Game/Farm/Art/Mats/M_TreeRound", "/Game/Farm/Art/Mats/M_Terrace",
          "/Game/Farm/Art/Mats/M_Grass", "/Game/Farm/Art/T_House", "/Game/Farm/Art/T_Water"):
    log("asset %s exists=%s" % (p, unreal.EditorAssetLibrary.does_asset_exist(p)))

log("DONE probe")