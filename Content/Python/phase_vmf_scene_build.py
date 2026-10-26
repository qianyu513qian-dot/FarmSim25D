# -*- coding: utf-8 -*-
"""Rebuild Lvl_TopDown with VoxelMicroFarm 鈥?NEW isometric reference layout.
40x40 spacious farm. Water LEFT with brown cliff bank + TWO plank bridges.
Central N-S path; 2x2 plots mid-left; house top-center picket; forest RIGHT.
Camera: isometric 2.5D (pitch~-40, yaw~-45, ortho~2800).
Clears VMF_* / Scene_*; hides FarmGround; tiles VMF grass.
"""
import unreal

GAME = "/Game/Farm/VoxelMicroFarm"
MODELS = GAME + "/Models"
ART_MATS = "/Game/Farm/Art/Mats"
PLANE = "/Engine/BasicShapes/Plane"

CELL = 100.0
TILE_UU = 10000.0
UNIT = CELL / TILE_UU  # 0.01
WIDTH = 40
HEIGHT = 40
ORIGIN = unreal.Vector(0.0, 0.0, 0.0)

SCENE_PREFIX = "Scene_"
VMF_PREFIX = "VMF_"

Z_GRASS = 0.5
Z_WATER = 0.0
Z_CLIFF = 3.0
Z_PATH = 2.5
Z_BRIDGE = 5.0
Z_SOIL = 1.8
Z_YARD = 2.0
Z_PROP = 0.0

# Central vertical path (2 cells wide)
PATH_COLS = (17, 18)
PATH_V_Y0 = 3
PATH_V_Y1 = 31  # up to yard gate

# Two horizontal pier/bridges into LEFT water
BRIDGE_MID_ROWS = (18, 19)      # mid-left pier
BRIDGE_SOUTH_ROWS = (4, 5)      # bottom-left pier
BRIDGE_X0 = 2                   # deck starts over water
BRIDGE_X1 = 16                  # meets path

# East spur from path toward well/coop (short)
SPUR_ROWS = (28, 29)
SPUR_X0 = 19
SPUR_X1 = 24

# 2x2 four plots mid-left of path (3x3 beds + 1-cell gaps)
# TL corn, TR tomato, BL pumpkin, BR empty hoe
BED_TL = (8, 10, 24, 26)    # corn
BED_TR = (12, 14, 24, 26)   # tomato
BED_BL = (8, 10, 20, 22)    # pumpkin
HOE = (12, 14, 20, 22)      # empty SoilUntilled
SOIL_X0, SOIL_X1 = 8, 14
SOIL_Y0, SOIL_Y1 = 20, 26

# House yard top-center (slightly right of path)
YARD_X0, YARD_X1 = 15, 25
YARD_Y0, YARD_Y1 = 32, 36
FENCE_X0, FENCE_X1 = 14, 26
FENCE_Y0, FENCE_Y1 = 31, 37

# Tall-grass patch bottom-center
TALL_X0, TALL_X1 = 12, 22
TALL_Y0, TALL_Y1 = 1, 3

# PlayerStart on central path near fields
PS_CX, PS_CY = 17, 16

# Camera isometric 2.5D
CAM_PITCH = -40.0
CAM_YAW = -90.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0

MESH = {
    "FarmShed": MODELS + "/Expansion02/Buildings/SM_VMF_Building_FarmShed",
    "ToolShelter": MODELS + "/Expansion02/Buildings/SM_VMF_Building_ToolShelter",
    "ChickenCoop": MODELS + "/Expansion02/Buildings/SM_VMF_Building_ChickenCoop",
    "PathStraight": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_Path_Straight",
    "PathCorner": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_Path_Corner",
    "PathJunction": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_Path_Junction",
    "DetailPath": MODELS + "/Details/SM_VMF_Detail_Path",
    "SoilDry": MODELS + "/Terrain/SM_VMF_Soil_Dry",
    "SoilUntilled": MODELS + "/Terrain/SM_VMF_Soil_Untilled",
    "SoilWet": MODELS + "/Terrain/SM_VMF_Soil_Wet",
    "Grass": MODELS + "/Terrain/SM_VMF_Ground_Grass",
    "GrassA": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_Grass_A",
    "GrassB": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_Grass_B",
    "GrassC": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_Grass_C",
    "GrassClump": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_GrassClump_Low",
    "GrassClumpMed": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_GrassClump_Medium",
    "GrassClumpEdge": MODELS + "/Expansion02/GroundStudy/SM_VMF_GroundStudy_GrassClump_Edge",
    "CornMature": MODELS + "/Crops/SM_VMF_Crop_Corn_Mature",
    "TomatoMature": MODELS + "/Crops/SM_VMF_Crop_Tomato_Mature",
    "PumpkinMature": MODELS + "/Expansion02/Crops/SM_VMF_Crop_Pumpkin_Mature",
    "TreeTall": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Tree_Tall",
    "TreeBroad": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Tree_Broadleaf",
    "TreeStump": MODELS + "/Expansion02/Nature/SM_VMF_Nature_TreeStump",
    "Bush": MODELS + "/Nature/SM_VMF_Nature_Bush",
    "RockLarge": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Rock_Large",
    "RockMed": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Rock_Medium",
    "RockSmall": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Rock_Small",
    "FenceStraight": MODELS + "/Expansion02/Facilities/SM_VMF_Fence_Picket_Straight",
    "FenceCorner": MODELS + "/Expansion02/Facilities/SM_VMF_Fence_Picket_Corner",
    "FenceEnd": MODELS + "/Expansion02/Facilities/SM_VMF_Fence_Picket_EndPost",
    "FenceLow": MODELS + "/Expansion02/Facilities/SM_VMF_Fence_Low_Straight",
    "FarmGate": MODELS + "/Expansion02/Facilities/SM_VMF_Fence_FarmGate",
    "Well": MODELS + "/Expansion02/Facilities/SM_VMF_Facility_WaterWell",
    "Scarecrow": MODELS + "/Expansion01/SM_VMF_Prop_Scarecrow",
    "Barrel": MODELS + "/Expansion01/SM_VMF_Prop_Barrel",
    "HayBale": MODELS + "/Expansion01/SM_VMF_Prop_HayBale",
    "FarmSign": MODELS + "/Expansion01/SM_VMF_Prop_FarmSign",
    "Crate": MODELS + "/Props/SM_VMF_Prop_Crate",
    "ShippingChest": MODELS + "/Props/SM_VMF_Prop_ShippingChest",
    "Wheelbarrow": MODELS + "/Expansion02/Storage/SM_VMF_Prop_Wheelbarrow",
    "CrateStack": MODELS + "/Expansion02/Storage/SM_VMF_Set_CrateStack",
    "FlowerY": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Flower_Yellow",
    "FlowerW": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Flower_White",
    "FlowerPatchY": MODELS + "/Expansion02/Nature/SM_VMF_Nature_FlowerPatch_Yellow",
    "FlowerPatchW": MODELS + "/Expansion02/Nature/SM_VMF_Nature_FlowerPatch_White",
    "ShrubLow": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Shrub_Low",
    "ShrubTall": MODELS + "/Expansion02/Nature/SM_VMF_Nature_Shrub_Tall",
}


def log(msg):
    unreal.log("[VMF_SCENE] " + str(msg))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def find_by_label(label):
    for a in eas().get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def cell_center(cx, cy, z=0.0):
    return unreal.Vector(ORIGIN.x + (cx + 0.5) * CELL,
                         ORIGIN.y + (cy + 0.5) * CELL, z)


def load_mesh(key):
    path = MESH.get(key)
    if not path:
        return None
    m = unreal.EditorAssetLibrary.load_asset(path)
    if not m:
        assets = unreal.EditorAssetLibrary.list_assets(GAME, recursive=True)
        base = path.rsplit("/", 1)[-1]
        for a in assets:
            if a.endswith("/" + base) or a.endswith("." + base):
                m = unreal.EditorAssetLibrary.load_asset(a.split(".")[0])
                if m:
                    MESH[key] = a.split(".")[0]
                    log("resolved {} -> {}".format(key, MESH[key]))
                    break
    if not m:
        log("MISSING mesh " + key + " @ " + str(path))
    return m


def mesh_xy_size(mesh):
    try:
        box = mesh.get_bounding_box()
        return (
            abs(box.max.x - box.min.x),
            abs(box.max.y - box.min.y),
            abs(box.max.z - box.min.z),
        )
    except Exception:
        return (CELL, CELL, CELL)


def destroy_prefixed(*prefixes):
    to_kill = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        for p in prefixes:
            if lab.startswith(p):
                to_kill.append(a)
                break
    for a in to_kill:
        try:
            eas().destroy_actor(a)
        except Exception as e:
            log("destroy fail {}: {}".format(a.get_actor_label(), e))
    log("cleared {} actors matching {}".format(len(to_kill), prefixes))


def spawn_mesh(label, mesh_key, cx, cy, yaw=0.0, z=0.0, scale=None, fit_cells=None):
    mesh = load_mesh(mesh_key)
    if not mesh:
        return None
    full = VMF_PREFIX + label
    sx, sy, sz = mesh_xy_size(mesh)
    if scale is None:
        scale = unreal.Vector(UNIT, UNIT, UNIT)
    elif isinstance(scale, (int, float)):
        s = float(scale) * UNIT
        scale = unreal.Vector(s, s, s)
    if fit_cells is not None:
        tw, th = fit_cells
        target_x = max(tw * CELL, 1.0)
        target_y = max(th * CELL, 1.0)
        fx = target_x / max(sx, 1.0)
        fy = target_y / max(sy, 1.0)
        if abs(fx - fy) < 0.25:
            f = (fx + fy) * 0.5
            scale = unreal.Vector(f, f, f)
        else:
            scale = unreal.Vector(fx, fy, min(fx, fy))
    loc = cell_center(cx, cy, z)
    if fit_cells is not None:
        tw, th = fit_cells
        loc = unreal.Vector(
            ORIGIN.x + (cx + tw * 0.5) * CELL,
            ORIGIN.y + (cy + th * 0.5) * CELL,
            z,
        )
    rot = unreal.Rotator()
    rot.yaw = float(yaw)
    actor = find_by_label(full)
    if actor is None:
        actor = eas().spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
        actor.set_actor_label(full)
    else:
        actor.set_actor_location(loc, False, True)
        actor.set_actor_rotation(rot, False)
    actor.set_actor_scale3d(scale)
    smc = actor.static_mesh_component
    smc.set_static_mesh(mesh)
    try:
        groundish = mesh_key in (
            "SoilDry", "SoilUntilled", "SoilWet", "Grass", "GrassA", "GrassB", "GrassC",
            "PathStraight", "PathCorner", "PathJunction", "DetailPath",
            "GrassClump", "GrassClumpMed", "GrassClumpEdge",
        )
        if groundish:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        else:
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception:
        pass
    try:
        actor.set_actor_hidden_in_game(False)
        actor.set_is_temporarily_hidden_in_editor(False)
    except Exception:
        pass
    return actor


# ---- occupancy (NEW reference: water LEFT only, irregular shore) ----

def water_edge_x(cy):
    """Irregular west shoreline X inclusive max water column."""
    # Jagged bank: base 5, push/pull by row
    base = 5
    wobble = (cy * 7 + 3) % 5  # 0..4
    if wobble == 0:
        return base - 1
    if wobble == 1:
        return base
    if wobble == 2:
        return base + 1
    if wobble == 3:
        return base
    return base + 2  # occasional deeper inlet


def is_water_cell(cx, cy):
    if cx < 0 or cy < 0 or cx >= WIDTH or cy >= HEIGHT:
        return False
    return cx <= water_edge_x(cy)


def is_bridge_cell(cx, cy):
    if cy in BRIDGE_MID_ROWS or cy in BRIDGE_SOUTH_ROWS:
        if BRIDGE_X0 <= cx <= BRIDGE_X1:
            return True
    return False


def is_path_cell(cx, cy):
    if cx in PATH_COLS and PATH_V_Y0 <= cy <= PATH_V_Y1:
        return True
    if is_bridge_cell(cx, cy):
        return True
    if cy in SPUR_ROWS and SPUR_X0 <= cx <= SPUR_X1:
        return True
    return False


def is_soil_cell(cx, cy):
    return SOIL_X0 <= cx <= SOIL_X1 and SOIL_Y0 <= cy <= SOIL_Y1


def is_yard_cell(cx, cy):
    return YARD_X0 <= cx <= YARD_X1 and YARD_Y0 <= cy <= YARD_Y1


def is_hoe_cell(cx, cy):
    x0, x1, y0, y1 = HOE
    return x0 <= cx <= x1 and y0 <= cy <= y1


def is_cliff_cell(cx, cy):
    """Brown dirt bank just inland of water (not path/bridge/soil/yard)."""
    if is_water_cell(cx, cy):
        return False
    if is_path_cell(cx, cy) or is_soil_cell(cx, cy) or is_yard_cell(cx, cy):
        return False
    edge = water_edge_x(cy)
    if cx > edge + 2:
        return False
    for dx, dy in ((-1, 0), (-1, -1), (-1, 1), (0, -1), (0, 1)):
        if is_water_cell(cx + dx, cy + dy):
            return True
    return False


def is_tall_grass_cell(cx, cy):
    return TALL_X0 <= cx <= TALL_X1 and TALL_Y0 <= cy <= TALL_Y1


def spawn_water_plane(label, cx, cy, tw, th, z=Z_WATER):
    full = VMF_PREFIX + label
    loc = unreal.Vector(
        ORIGIN.x + (cx + tw * 0.5) * CELL,
        ORIGIN.y + (cy + th * 0.5) * CELL,
        z,
    )
    rot = unreal.Rotator()
    rot.pitch = 0.0
    rot.yaw = 0.0
    rot.roll = 0.0
    actor = find_by_label(full)
    if actor is None:
        actor = eas().spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
        actor.set_actor_label(full)
    else:
        actor.set_actor_location(loc, False, True)
        actor.set_actor_rotation(rot, False)
    actor.set_actor_scale3d(unreal.Vector(float(tw), float(th), 1.0))
    smc = actor.static_mesh_component
    plane = unreal.EditorAssetLibrary.load_asset(PLANE)
    if plane:
        smc.set_static_mesh(plane)
    mat = unreal.EditorAssetLibrary.load_asset(ART_MATS + "/M_Water")
    if not mat:
        mat = unreal.EditorAssetLibrary.load_asset(ART_MATS + "/M_Water_Pond")
    if not mat:
        mat = unreal.EditorAssetLibrary.load_asset(ART_MATS + "/M_Water_Left")
    if mat:
        smc.set_material(0, mat)
    else:
        log("WARN no M_Water; water plane untextured")
    try:
        smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
    try:
        actor.set_actor_hidden_in_game(False)
        actor.set_is_temporarily_hidden_in_editor(False)
    except Exception:
        pass
    return actor


def place_water():
    """One wide left water plane covering max shoreline extent (visual under cliff)."""
    # Cover cols 0..7 across full height (irregular land tiles cover over-water land)
    spawn_water_plane("Water_Left", 0, 0, 8, HEIGHT, Z_WATER)
    log("water: left strip 8x40 under irregular shore")


def place_cliff_bank():
    """Brown dirt cliff tiles along irregular shoreline above water."""
    n = 0
    for cy in range(HEIGHT):
        for cx in range(WIDTH):
            if not is_cliff_cell(cx, cy):
                continue
            spawn_mesh("Cliff_{}_{}".format(cx, cy), "SoilDry", cx, cy,
                       yaw=0.0, z=Z_CLIFF, fit_cells=(1, 1))
            n += 1
    log("cliff bank tiles={}".format(n))
    return n


def place_grass_floor():
    variants = ["Grass", "GrassA", "GrassB", "GrassC"]
    usable = []
    for k in variants:
        if load_mesh(k):
            usable.append(k)
    if not usable:
        log("ERROR: no grass meshes loaded")
        return 0
    n = 0
    for cy in range(HEIGHT):
        for cx in range(WIDTH):
            if is_water_cell(cx, cy):
                continue
            if is_path_cell(cx, cy):
                continue
            if is_soil_cell(cx, cy):
                continue
            if is_yard_cell(cx, cy):
                continue
            if is_cliff_cell(cx, cy):
                continue
            key = usable[(cx * 3 + cy * 5) % len(usable)]
            spawn_mesh("Grass_{}_{}".format(cx, cy), key, cx, cy,
                       yaw=float((cx + cy) % 4) * 90.0, z=Z_GRASS, fit_cells=(1, 1))
            n += 1
    # shore clumps + tall-grass accents
    clumps = 0
    for cy in range(HEIGHT):
        for cx in range(WIDTH):
            if is_water_cell(cx, cy) or is_path_cell(cx, cy) or is_soil_cell(cx, cy) or is_yard_cell(cx, cy):
                continue
            near_water = is_cliff_cell(cx, cy)
            if not near_water:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if is_water_cell(cx + dx, cy + dy):
                        near_water = True
                        break
            if near_water and ((cx + cy) % 2 == 0):
                ck = "GrassClumpEdge" if load_mesh("GrassClumpEdge") else "GrassClump"
                spawn_mesh("ShoreClump_{}_{}".format(cx, cy), ck, cx, cy,
                           yaw=float(cx * 20 % 360), z=Z_CLIFF + 0.5, scale=1.0)
                clumps += 1
            elif is_tall_grass_cell(cx, cy):
                ck = "GrassClumpMed" if load_mesh("GrassClumpMed") else "GrassClump"
                spawn_mesh("TallGrass_{}_{}".format(cx, cy), ck, cx, cy,
                           yaw=float(cy * 30 % 360), z=Z_GRASS + 0.5, scale=1.2)
                clumps += 1
    log("grass floor tiles={} clumps/tall={}".format(n, clumps))
    return n


def place_bridges():
    """Two plank bridges mid-left and bottom-left, path westward into water."""
    for tag, rows in (("Mid", BRIDGE_MID_ROWS), ("South", BRIDGE_SOUTH_ROWS)):
        for cy in rows:
            for cx in range(BRIDGE_X0, BRIDGE_X1 + 1):
                spawn_mesh("Bridge{}_{}_{}".format(tag, cx, cy), "PathStraight", cx, cy,
                           yaw=0.0, z=Z_BRIDGE, fit_cells=(1, 1))
            # low rails on N/S of deck
            rail_n = rows[-1] + 1
            rail_s = rows[0] - 1
            for cx in range(BRIDGE_X0, min(BRIDGE_X1, water_edge_x(cy) + 3) + 1):
                if 0 <= rail_n < HEIGHT:
                    spawn_mesh("Bridge{}RailN_{}".format(tag, cx), "FenceLow", cx, rail_n,
                               yaw=0.0, z=Z_BRIDGE, fit_cells=(1, 1))
                if 0 <= rail_s < HEIGHT:
                    spawn_mesh("Bridge{}RailS_{}".format(tag, cx), "FenceLow", cx, rail_s,
                               yaw=0.0, z=Z_BRIDGE, fit_cells=(1, 1))
        # end posts at water tip
        tip = BRIDGE_X0
        spawn_mesh("Bridge{}PostN".format(tag), "FenceEnd", tip, rows[-1],
                   yaw=90.0, z=Z_BRIDGE, fit_cells=(1, 1))
        spawn_mesh("Bridge{}PostS".format(tag), "FenceEnd", tip, rows[0],
                   yaw=90.0, z=Z_BRIDGE, fit_cells=(1, 1))
    log("bridges: mid rows {} + south rows {} x=[{},{}]".format(
        BRIDGE_MID_ROWS, BRIDGE_SOUTH_ROWS, BRIDGE_X0, BRIDGE_X1))


def place_path_run():
    n = 0
    for cy in range(PATH_V_Y0, PATH_V_Y1 + 1):
        for cx in PATH_COLS:
            # skip cells that are bridge deck (already placed)
            if is_bridge_cell(cx, cy):
                continue
            spawn_mesh("PathV_{}_{}".format(cx, cy), "PathStraight", cx, cy,
                       yaw=90.0, z=Z_PATH, fit_cells=(1, 1))
            n += 1
    # east spur toward well/coop
    for cx in range(SPUR_X0, SPUR_X1 + 1):
        for cy in SPUR_ROWS:
            spawn_mesh("PathSpur_{}_{}".format(cx, cy), "PathStraight", cx, cy,
                       yaw=0.0, z=Z_PATH, fit_cells=(1, 1))
            n += 1
    # T-junction markers at mid bridge meet
    for cy in BRIDGE_MID_ROWS:
        for cx in PATH_COLS:
            spawn_mesh("PathJuncMid_{}_{}".format(cx, cy), "PathJunction", cx, cy,
                       yaw=0.0, z=Z_PATH + 0.15, fit_cells=(1, 1))
    for cy in BRIDGE_SOUTH_ROWS:
        for cx in PATH_COLS:
            spawn_mesh("PathJuncS_{}_{}".format(cx, cy), "PathJunction", cx, cy,
                       yaw=0.0, z=Z_PATH + 0.15, fit_cells=(1, 1))
    # steps into house yard gate
    for cx in PATH_COLS:
        spawn_mesh("PathStep_{}_{}".format(cx, PATH_V_Y1), "PathCorner", cx, PATH_V_Y1,
                   yaw=0.0 if cx == PATH_COLS[0] else 90.0, z=Z_PATH + 0.2, fit_cells=(1, 1))
    log("path tiles ~{}".format(n))


def place_soil_and_crops():
    """2x2 four plots: corn / tomato / pumpkin / empty hoe."""
    for cy in range(SOIL_Y0, SOIL_Y1 + 1):
        for cx in range(SOIL_X0, SOIL_X1 + 1):
            key = "SoilUntilled" if is_hoe_cell(cx, cy) else "SoilDry"
            spawn_mesh("Soil_{}_{}".format(cx, cy), key, cx, cy,
                       yaw=0.0, z=Z_SOIL, fit_cells=(1, 1))

    for lab, key, rect in (
        ("CropCorn", "CornMature", BED_TL),
        ("CropTom", "TomatoMature", BED_TR),
        ("CropPump", "PumpkinMature", BED_BL),
    ):
        x0, x1, y0, y1 = rect
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                spawn_mesh("{}_{}_{}".format(lab, cx, cy), key, cx, cy,
                           yaw=float((cx + cy) * 30 % 360), z=Z_SOIL + 0.2, scale=1.0)
    log("soil+crops 2x2: TL corn TR tomato BL pumpkin BR hoe@{}".format(HOE))


def place_buildings():
    """House top-center picket; well + coop right of house."""
    for cy in range(YARD_Y0, YARD_Y1 + 1):
        for cx in range(YARD_X0, YARD_X1 + 1):
            spawn_mesh("Yard_{}_{}".format(cx, cy), "SoilDry", cx, cy,
                       yaw=0.0, z=Z_YARD, fit_cells=(1, 1))

    # shed facing south toward path; slightly right of path center
    spawn_mesh("House_FarmShed", "FarmShed", 17, 32, yaw=180.0, z=Z_YARD, fit_cells=(5, 4))
    spawn_mesh("Well", "Well", 23, 33, yaw=0.0, z=Z_YARD, scale=1.0)
    spawn_mesh("ChickenCoop", "ChickenCoop", 25, 32, yaw=-90.0, z=Z_YARD, fit_cells=(2, 2))
    if load_mesh("ToolShelter"):
        spawn_mesh("ToolShelter", "ToolShelter", 21, 34, yaw=90.0, z=Z_YARD, fit_cells=(2, 2))

    # picket enclosure
    for cx in range(FENCE_X0, FENCE_X1 + 1):
        spawn_mesh("FenceN_{}".format(cx), "FenceStraight", cx, FENCE_Y1, yaw=0.0, z=Z_YARD, fit_cells=(1, 1))
    spawn_mesh("FenceNW", "FenceCorner", FENCE_X0, FENCE_Y1, yaw=180.0, z=Z_YARD, fit_cells=(1, 1))
    spawn_mesh("FenceNE", "FenceCorner", FENCE_X1, FENCE_Y1, yaw=90.0, z=Z_YARD, fit_cells=(1, 1))
    for cy in range(FENCE_Y0, FENCE_Y1):
        spawn_mesh("FenceW_{}".format(cy), "FenceStraight", FENCE_X0, cy, yaw=90.0, z=Z_YARD, fit_cells=(1, 1))
        spawn_mesh("FenceE_{}".format(cy), "FenceStraight", FENCE_X1, cy, yaw=90.0, z=Z_YARD, fit_cells=(1, 1))
    for cx in range(FENCE_X0, FENCE_X1 + 1):
        if cx in PATH_COLS:
            continue
        spawn_mesh("FenceS_{}".format(cx), "FenceStraight", cx, FENCE_Y0, yaw=0.0, z=Z_YARD, fit_cells=(1, 1))
    if load_mesh("FarmGate"):
        spawn_mesh("FenceGate", "FarmGate", PATH_COLS[0], FENCE_Y0, yaw=0.0, z=Z_YARD, fit_cells=(2, 1))
    else:
        spawn_mesh("FenceGateL", "FenceEnd", PATH_COLS[0] - 1, FENCE_Y0, yaw=0.0, z=Z_YARD, fit_cells=(1, 1))
        spawn_mesh("FenceGateR", "FenceEnd", PATH_COLS[1] + 1, FENCE_Y0, yaw=0.0, z=Z_YARD, fit_cells=(1, 1))
    log("buildings: house top-center, well+coop right, picket yard")


def place_props_nature():
    # props per reference
    spawn_mesh("Scarecrow", "Scarecrow", 21, 22, yaw=45.0, z=0.0, scale=1.0)
    spawn_mesh("Barrel", "Barrel", 20, 27, yaw=0.0, z=0.0, scale=1.0)
    spawn_mesh("HayBale_1", "HayBale", 22, 14, yaw=20.0, z=0.0, scale=1.0)
    spawn_mesh("HayBale_2", "HayBale", 24, 12, yaw=-15.0, z=0.0, scale=1.0)
    spawn_mesh("ShippingChest", "ShippingChest", 19, 12, yaw=0.0, z=0.0, scale=1.0)
    spawn_mesh("CrateStack", "CrateStack", 23, 15, yaw=15.0, z=0.0, scale=1.0)
    spawn_mesh("Crate_1", "Crate", 22, 16, yaw=10.0, z=0.0, scale=1.0)
    spawn_mesh("Crate_2", "Crate", 24, 16, yaw=-20.0, z=0.0, scale=1.0)
    spawn_mesh("Wheelbarrow", "Wheelbarrow", 15, 6, yaw=-30.0, z=0.0, scale=1.0)  # near south bridge
    spawn_mesh("Mailbox", "FarmSign", 18, 30, yaw=180.0, z=0.0, scale=1.0)
    # orange pumpkin accents lower-mid (extra mature pumpkins on grass)
    for i, (cx, cy) in enumerate(((20, 10), (21, 9), (23, 11), (19, 8))):
        spawn_mesh("PumpAccent_{}".format(i), "PumpkinMature", cx, cy,
                   yaw=float(i * 40), z=0.0, scale=0.9)

    # shore trees along bank (left of path, inland of cliff)
    shore_trees = [
        ("Tree_Shore1", "TreeBroad", 7, 30),
        ("Tree_Shore2", "TreeTall", 8, 28),
        ("Tree_Shore3", "TreeBroad", 7, 16),
        ("Tree_Shore4", "TreeTall", 8, 12),
        ("Tree_Shore5", "TreeBroad", 7, 8),
        ("Tree_Shore6", "TreeTall", 9, 32),
        ("Tree_HouseN1", "TreeBroad", 16, 37),
        ("Tree_HouseN2", "TreeTall", 20, 37),
        ("Tree_HouseN3", "TreeBroad", 24, 37),
        ("Tree_HouseE1", "TreeTall", 27, 34),
    ]
    # DENSE forest RIGHT third (cx >= 28)
    forest = []
    idx = 0
    for cy in range(2, 38, 2):
        for cx in range(28, 39, 2):
            # irregular edge: skip some near path
            if cx == 28 and (cy % 4 == 0):
                continue
            key = "TreeBroad" if (cx + cy) % 3 else "TreeTall"
            forest.append(("Tree_F{}_{}".format(cx, cy), key, cx, cy))
            idx += 1
    # scattered into central grass from forest edge
    forest += [
        ("Tree_Edge1", "TreeBroad", 26, 20),
        ("Tree_Edge2", "TreeTall", 27, 14),
        ("Tree_Edge3", "TreeBroad", 26, 8),
        ("Tree_Edge4", "TreeTall", 27, 26),
        ("Tree_Edge5", "TreeBroad", 25, 18),
        ("Stump_1", "TreeStump", 27, 16),
        ("Stump_2", "TreeStump", 30, 10),
        ("Stump_3", "TreeStump", 29, 22),
    ]

    for lab, key, cx, cy in shore_trees + forest:
        if cx < 0 or cy < 0 or cx >= WIDTH or cy >= HEIGHT:
            continue
        if is_water_cell(cx, cy) or is_path_cell(cx, cy) or is_soil_cell(cx, cy) or is_yard_cell(cx, cy):
            continue
        spawn_mesh(lab, key, cx, cy, yaw=float(cx * 15 % 360), z=0.0, scale=1.0)

    deco = [
        ("Rock_1", "RockLarge", 29, 24),
        ("Rock_2", "RockMed", 32, 18),
        ("Rock_3", "RockSmall", 27, 12),
        ("Rock_4", "RockLarge", 34, 28),
        ("Rock_5", "RockMed", 31, 8),
        ("Rock_6", "RockSmall", 26, 22),
        ("Rock_7", "RockMed", 36, 14),
        ("Rock_8", "RockSmall", 10, 30),
        ("Flower_1", "FlowerY", 20, 24),
        ("Flower_2", "FlowerW", 22, 20),
        ("Flower_3", "FlowerPatchY", 15, 14),
        ("Flower_4", "FlowerPatchW", 24, 18),
        ("Flower_5", "FlowerY", 16, 10),
        ("Shrub_1", "ShrubLow", 27, 30),
        ("Shrub_2", "ShrubTall", 33, 32),
        ("Shrub_3", "ShrubLow", 28, 6),
        ("Bush_1", "Bush", 26, 28),
        ("Bush_2", "Bush", 30, 20),
        ("Clump_1", "GrassClumpMed", 14, 12),
        ("Clump_2", "GrassClump", 22, 8),
        ("Clump_3", "GrassClumpMed", 10, 16),
    ]
    for lab, key, cx, cy in deco:
        if is_water_cell(cx, cy) or is_path_cell(cx, cy) or is_soil_cell(cx, cy):
            continue
        spawn_mesh(lab, key, cx, cy, yaw=float(cy * 17 % 360), z=0.0, scale=1.0)
    log("props+nature: shore trees, dense right forest, scarecrow/crates/hay")


def cleanup_duplicate_pawns():
    spawn = cell_center(PS_CX, PS_CY, 100.0)
    kept_ps = None
    to_kill = []
    pawnish = 0
    for a in eas().get_all_level_actors():
        cn = a.get_class().get_name()
        lab = a.get_actor_label()
        if cn == "PlayerStart" or "PlayerStart" in cn:
            if kept_ps is None:
                kept_ps = a
                a.set_actor_location(spawn, False, True)
                try:
                    a.set_actor_label("PlayerStart")
                except Exception:
                    pass
            else:
                to_kill.append(a)
            continue
        is_pawn = False
        for token in ("TopDownCharacter", "Mannequin", "DefaultPawn", "Character", "Pawn"):
            if token in cn:
                is_pawn = True
                break
        if not is_pawn:
            for token in ("TopDownCharacter", "Mannequin", "BP_ThirdPerson", "Quinn", "Steve"):
                if token in lab:
                    is_pawn = True
                    break
        if is_pawn and not lab.startswith(VMF_PREFIX) and not lab.startswith(SCENE_PREFIX):
            if cn == "StaticMeshActor":
                continue
            to_kill.append(a)
            pawnish += 1

    for a in to_kill:
        lab = a.get_actor_label()
        try:
            eas().destroy_actor(a)
            log("removed duplicate pawn: {} ({})".format(lab, a.get_class().get_name()))
        except Exception as e:
            try:
                a.set_actor_location(unreal.Vector(-50000, -50000, -50000), False, True)
                a.set_actor_hidden_in_game(True)
                log("hid stray pawn {}: {}".format(lab, e))
            except Exception as e2:
                log("pawn cleanup fail {}: {}".format(lab, e2))

    if kept_ps:
        log("PlayerStart kept @ {}".format(spawn))
    else:
        try:
            ps = eas().spawn_actor_from_class(unreal.PlayerStart, spawn, unreal.Rotator())
            ps.set_actor_label("PlayerStart")
            log("spawned new PlayerStart")
        except Exception as e:
            log("no PlayerStart and spawn failed: " + str(e))
    log("duplicate pawn cleanup done (removed ~{})".format(pawnish))


def hide_farmground():
    for lab in ("FarmGround", "FarmGround_Grass", "GroundPlane"):
        fg = find_by_label(lab)
        if not fg:
            continue
        try:
            fg.set_actor_hidden_in_game(True)
            fg.set_is_temporarily_hidden_in_editor(True)
            fg.set_actor_location(unreal.Vector(-50000, -50000, -1000), False, True)
            try:
                smc = fg.static_mesh_component
                if smc:
                    smc.set_visibility(False)
                    smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            except Exception:
                pass
            log("hid textured plane " + lab)
        except Exception as e:
            log("hide FarmGround fail: " + str(e))


def bump_camera_iso():
    """Isometric / 2.5D: pitch ~-40, yaw ~-45, orthographic wide."""
    bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    if not bp:
        log("WARN no BP_TopDownCharacter for camera bump")
        return
    try:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        handles = sds.k2_gather_subobject_data_for_blueprint(bp)
        for h in handles:
            data = lib.get_data(h)
            name = str(lib.get_variable_name(data))
            obj = lib.get_object_for_blueprint(data, bp)
            if not obj:
                continue
            cname = obj.get_class().get_name()
            if "SpringArm" in cname or name == "SpringArm":
                try:
                    obj.set_editor_property("target_arm_length", CAM_ARM)
                except Exception as e:
                    log("arm len fail: " + str(e))
                for prop, val in (
                    ("do_collision_test", False),
                    ("use_pawn_control_rotation", False),
                    ("inherit_pitch", False),
                    ("inherit_yaw", False),
                    ("inherit_roll", False),
                ):
                    try:
                        obj.set_editor_property(prop, val)
                    except Exception:
                        pass
                try:
                    rot = unreal.Rotator()
                    rot.pitch = CAM_PITCH
                    rot.yaw = CAM_YAW
                    rot.roll = 0.0
                    obj.set_editor_property("relative_rotation", rot)
                    now = obj.get_editor_property("relative_rotation")
                    log("SpringArm arm={} relRot p={} y={} r={}".format(
                        CAM_ARM, now.pitch, now.yaw, now.roll))
                except Exception as e:
                    log("arm rot fail: " + str(e))
            if cname == "CameraComponent" or name == "Camera":
                try:
                    obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                    obj.set_editor_property("ortho_width", CAM_ORTHO)
                    cam_rot = unreal.Rotator()
                    cam_rot.pitch = 0.0
                    cam_rot.yaw = 0.0
                    cam_rot.roll = 0.0
                    try:
                        obj.set_editor_property("relative_rotation", cam_rot)
                    except Exception:
                        pass
                    log("Camera ortho_width={} ORTHOGRAPHIC".format(CAM_ORTHO))
                except Exception as e:
                    log("cam bump fail: " + str(e))
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        except Exception as e:
            log("cam compile: " + str(e))
        unreal.EditorAssetLibrary.save_asset(bp_path)
        log("camera BP saved (iso pitch={} yaw={} ortho={})".format(
            CAM_PITCH, CAM_YAW, CAM_ORTHO))
    except Exception as e:
        log("bump_camera_iso fail: " + str(e))


def ensure_grid_and_player():
    gm = find_by_label("BP_GridManager")
    if gm:
        try:
            gm.set_editor_property("GridWidth", WIDTH)
            gm.set_editor_property("GridHeight", HEIGHT)
            gm.set_editor_property("CellSize", CELL)
            gm.set_editor_property("GridOrigin", ORIGIN)
            log("GridManager {}x{} Cell={} Origin=({},{})".format(
                WIDTH, HEIGHT, CELL, ORIGIN.x, ORIGIN.y))
        except Exception as e:
            log("GridManager set fail: " + str(e))
    else:
        log("WARNING no BP_GridManager")

    hide_farmground()
    cleanup_duplicate_pawns()
    bump_camera_iso()


def hide_template_clutter():
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith(VMF_PREFIX) or lab.startswith("BP_") or lab in (
            "PlayerStart", "DirectionalLight", "SkyAtmosphere",
            "SkyLight", "ExponentialHeightFog", "VolumetricCloud", "WorldSettings",
            "AbstractNavData", "DefaultPhysicsVolume",
        ):
            continue
        if lab.startswith("Scene_"):
            continue
        kill_tokens = ("Prototype", "TemplateFloor", "Floor_400x400", "GeometryScript",
                       "Cube", "BP_Sky_Sphere", "FarmGround")
        for t in kill_tokens:
            if t in lab:
                try:
                    a.set_actor_hidden_in_game(True)
                    a.set_is_temporarily_hidden_in_editor(True)
                    log("hid clutter " + lab)
                except Exception:
                    pass
                break


def save_level():
    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = els.save_current_level()
        log("save_current_level -> " + str(ok))
    except Exception as e:
        log("save fail: " + str(e))
        try:
            unreal.EditorLevelLibrary.save_current_level()
        except Exception as e2:
            log("save2 fail: " + str(e2))



# POST_MIRROR_X_FOR_YAW135: with CAM_YAW=135, +Y reads TOP on screen but +X reads LEFT.
# Authored layout is water=LOW_X / forest=HIGH_X; mirror X after spawn so silhouette matches reference.
def post_mirror_x_for_yaw135():
    map_w = float(WIDTH) * CELL
    eas_ = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    n = 0
    for a in eas_.get_all_level_actors():
        lab = a.get_actor_label() or ""
        cn = a.get_class().get_name()
        if not (lab.startswith(VMF_PREFIX) or lab.startswith(SCENE_PREFIX) or cn == "PlayerStart" or lab == "PlayerStart"):
            continue
        if "FarmGround" in lab:
            continue
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        new_loc = unreal.Vector(map_w - loc.x, loc.y, loc.z)
        new_rot = unreal.Rotator()
        new_rot.pitch = rot.pitch
        new_rot.yaw = -rot.yaw
        new_rot.roll = rot.roll
        a.set_actor_location(new_loc, False, True)
        a.set_actor_rotation(new_rot, False)
        n += 1
    log("post_mirror_x_for_yaw135 moved={}".format(n))

def main():
    log("=== START VMF SCENE BUILD ISO REF 40x40 ===")
    destroy_prefixed(SCENE_PREFIX, VMF_PREFIX)

    for k in ("FarmShed", "SoilDry", "PathStraight", "CornMature", "FenceLow",
              "FenceEnd", "Grass", "GrassA", "ShippingChest", "FarmGate", "Well",
              "ChickenCoop", "TreeBroad", "TreeTall", "PumpkinMature", "TomatoMature"):
        load_mesh(k)

    place_water()
    place_cliff_bank()
    place_grass_floor()
    place_bridges()
    place_path_run()
    place_soil_and_crops()
    place_buildings()
    place_props_nature()
    ensure_grid_and_player()
    hide_template_clutter()
    # DISABLED: no scene mirror/rotate — camera yaw only
    save_level()

    vmf = []
    counts = {"Water": 0, "Bridge": 0, "Cliff": 0, "Grass": 0, "Path": 0, "Soil": 0,
              "Crop": 0, "Fence": 0, "Tree": 0, "Yard": 0, "Shore": 0, "Tall": 0,
              "PumpAccent": 0, "Hay": 0}
    key_pos = {}
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if not lab.startswith(VMF_PREFIX):
            continue
        loc = a.get_actor_location()
        vmf.append((lab, round(loc.x), round(loc.y), round(loc.z)))
        tagged = False
        for k in ("Water", "Bridge", "Cliff", "Path", "Soil", "Crop", "Fence", "Tree",
                  "Yard", "Shore", "Tall", "PumpAccent", "Hay"):
            if lab.startswith(VMF_PREFIX + k) or (k == "Hay" and "HayBale" in lab):
                counts[k] += 1
                tagged = True
                break
        if not tagged:
            if "Grass_" in lab or "Clump_" in lab or "ShoreClump" in lab:
                counts["Grass"] += 1
            elif "ShoreClump" in lab:
                counts["Shore"] += 1
        if lab in (
            "VMF_House_FarmShed", "VMF_Well", "VMF_ChickenCoop", "VMF_Scarecrow",
            "VMF_ShippingChest", "VMF_Wheelbarrow", "VMF_Mailbox", "VMF_FenceGate",
            "VMF_Water_Left", "VMF_BridgeMid_2_18", "VMF_BridgeSouth_2_4",
            "VMF_PathV_17_16",
        ):
            key_pos[lab] = (round(loc.x), round(loc.y), round(loc.z))

    vmf.sort(key=lambda t: t[0])
    ps = cell_center(PS_CX, PS_CY, 100.0)
    log("VMF actors TOTAL: {}".format(len(vmf)))
    log("counts: {}".format(counts))
    log("key positions: {}".format(key_pos))
    log("Grid={}x{} Cell={} worldAABB=[0,{}]^2".format(WIDTH, HEIGHT, int(CELL), int(WIDTH * CELL)))
    log("PlayerStart Grid({},{}) world=({:.0f},{:.0f},{:.0f})".format(
        PS_CX, PS_CY, ps.x, ps.y, ps.z))
    log("Hoe empty 3x3: {}; Camera iso pitch={} yaw={} ortho={}".format(
        HOE, CAM_PITCH, CAM_YAW, CAM_ORTHO))
    for t in vmf[:12]:
        log("  {} @ ({},{},{})".format(t[0], t[1], t[2], t[3]))
    if len(vmf) > 12:
        log("  ... +{} more".format(len(vmf) - 12))

    fg = find_by_label("FarmGround")
    if fg:
        log("FarmGround present (should be hidden/relocated)")
    else:
        log("FarmGround not found (ok)")

    pawns = []
    for a in eas().get_all_level_actors():
        cn = a.get_class().get_name()
        if any(t in cn for t in ("TopDownCharacter", "Mannequin", "Character", "Pawn")):
            if "PlayerStart" in cn:
                continue
            if a.get_actor_label().startswith(VMF_PREFIX):
                continue
            pawns.append((a.get_actor_label(), cn))
    log("remaining non-PS pawn-like: {}".format(pawns))
    log("=== END VMF SCENE BUILD ISO REF 40x40 ===")


main()



