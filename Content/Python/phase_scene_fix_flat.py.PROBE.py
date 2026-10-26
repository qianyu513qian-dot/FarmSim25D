# -*- coding: utf-8 -*-
"""Probe spawn/grid/scene after billboard mess for flat-tile revert."""
import unreal

def log(m):
    unreal.log("[FIXPROBE] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# PlayerStart + GridManager + FarmGround + key Scene
want = (
    "PlayerStart", "BP_GridManager", "FarmGround",
    "Scene_House", "Scene_Terrace", "Scene_Tree_NE", "Scene_Tree_NW",
    "Scene_Path_V", "Scene_Water_Left", "Scene_Fence_N", "Scene_Lamp",
    "Scene_Crop_TL", "Scene_Cliff_S", "Scene_Stairs",
)
found = {w: None for w in want}
others_blackish = []
for a in eas.get_all_level_actors():
    try:
        lab = a.get_actor_label()
    except Exception:
        continue
    if lab in found:
        found[lab] = a
    # catch any large dark-looking or Scene_ with odd rot
    if lab.startswith("Scene_") or lab in ("PlayerStart", "BP_GridManager", "FarmGround"):
        loc = a.get_actor_location()
        rr = a.get_actor_rotation()
        sc = a.get_actor_scale3d()
        log("{} loc=({},{},{}) rot=p{} y{} r{} sc=({},{},{}) cls={}".format(
            lab, round(loc.x,1), round(loc.y,1), round(loc.z,1),
            round(rr.pitch,1), round(rr.yaw,1), round(rr.roll,1),
            round(sc.x,2), round(sc.y,2), round(sc.z,2),
            a.get_class().get_name()))

# GridManager props
gm = found["BP_GridManager"]
if gm:
    for prop in ("GridWidth", "GridHeight", "CellSize", "GridOrigin",
                 "grid_width", "grid_height", "cell_size", "grid_origin"):
        try:
            v = gm.get_editor_property(prop)
            log("GM.{} = {}".format(prop, v))
        except Exception:
            pass
    # try WorldToGrid if callable on BP
    try:
        # CDO / instance functions
        for name in dir(gm):
            if "Grid" in name or "Origin" in name or "Cell" in name:
                if not name.startswith("_"):
                    log("GM attr " + name)
    except Exception as e:
        log("dir gm " + str(e))

ps = found["PlayerStart"]
if ps:
    loc = ps.get_actor_location()
    log("PlayerStart OK at ({},{},{})".format(round(loc.x), round(loc.y), round(loc.z)))
    # estimate grid: Origin 0, Cell 100 -> gx=floor(x/100)
    gx = int(loc.x // 100)
    gy = int(loc.y // 100)
    log("PlayerStart estimated Grid {},{}".format(gx, gy))
else:
    log("NO PlayerStart found by label - scanning class")
    for a in eas.get_all_level_actors():
        cn = a.get_class().get_name()
        if "PlayerStart" in cn or "PlayerStart" in a.get_name():
            loc = a.get_actor_location()
            log("FOUND alt {} label={} loc=({},{},{})".format(
                a.get_name(), a.get_actor_label(), round(loc.x), round(loc.y), round(loc.z)))

# House material / mesh
house = found["Scene_House"]
if house:
    smc = house.static_mesh_component
    mesh = smc.get_editor_property("static_mesh")
    mat = smc.get_material(0)
    log("House mesh={} mat={}".format(
        mesh.get_name() if mesh else None,
        mat.get_path_name() if mat else None))
    # bounds
    try:
        b = house.get_actor_bounds(False)
        # returns (origin, extent) tuple in some versions
        log("House bounds raw={}".format(b))
    except Exception as e:
        log("bounds " + str(e))

# Camera SpringArm
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
        log("SpringArm template p={} y={} r={} len={}".format(rr.pitch, rr.yaw, rr.roll, tl))
    if cn == "CameraComponent":
        try:
            log("Cam ortho={} proj={}".format(
                obj.get_editor_property("ortho_width"),
                obj.get_editor_property("projection_mode")))
        except Exception as e:
            log("cam " + str(e))

# List all Scene_ with non-zero rotation (billboard leftovers)
nonzero = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if not lab.startswith("Scene_"):
        continue
    rr = a.get_actor_rotation()
    if abs(rr.pitch) > 0.1 or abs(rr.yaw) > 0.1 or abs(rr.roll) > 0.1:
        nonzero += 1
log("Scene_* with non-zero rot count={}".format(nonzero))

# Check materials exist
for p in ("/Game/Farm/Art/Mats/M_House", "/Game/Farm/Art/Mats/M_Water",
          "/Game/Farm/Art/Mats/M_TreeRound", "/Game/Farm/Art/Mats/M_Terrace",
          "/Game/Farm/Art/Mats/M_Grass", "/Game/Farm/Art/T_House",
          "/Game/Farm/Art/T_Water"):
    log("asset {} exists={}".format(p, unreal.EditorAssetLibrary.does_asset_exist(p)))

log("DONE probe")
