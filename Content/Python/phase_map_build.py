# -*- coding: utf-8 -*-
"""Build farm MAP: dirt plane + borders + move PlayerStart onto farm center.
Conservative: does NOT edit BP_GridManager graphs / TillCell.
Grid stays 20x20, CellSize=100, Origin=(0,0,0). Farm AABB = [0,2000]x[0,2000].
"""
import unreal

MAP_DIR = "/Game/Farm/Map"
MI_PATH = MAP_DIR + "/MI_FarmDirt"
PARENT_MI = "/Game/LevelPrototyping/Materials/MI_DefaultColorway"
PLANE_PATH = "/Engine/BasicShapes/Plane"
CUBE_PATH = "/Game/LevelPrototyping/Meshes/SM_Cube"

CELL = 100.0
WIDTH = 20
HEIGHT = 20
ORIGIN = unreal.Vector(0.0, 0.0, 0.0)
FARM_W = WIDTH * CELL   # 2000
FARM_H = HEIGHT * CELL  # 2000
CENTER = unreal.Vector(ORIGIN.x + FARM_W * 0.5, ORIGIN.y + FARM_H * 0.5, 1.0)
# Spawn at cell (10,10) center
SPAWN = unreal.Vector(ORIGIN.x + 10.5 * CELL, ORIGIN.y + 10.5 * CELL, 100.0)
# Dirt brown (linear)
DIRT = unreal.LinearColor(0.28, 0.16, 0.08, 1.0)
BORDER = unreal.LinearColor(0.12, 0.18, 0.06, 1.0)  # olive edge


def log(msg):
    unreal.log("[MAP_BUILD] " + str(msg))


def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)
        log("mkdir " + path)


def ensure_dirt_mi():
    ensure_dir("/Game/Farm")
    ensure_dir(MAP_DIR)
    mel = unreal.MaterialEditingLibrary
    if unreal.EditorAssetLibrary.does_asset_exist(MI_PATH):
        mi = unreal.EditorAssetLibrary.load_asset(MI_PATH)
        log("MI exists, updating color")
    else:
        parent = unreal.EditorAssetLibrary.load_asset(PARENT_MI)
        if not parent:
            # fallback to gray prototype
            parent = unreal.EditorAssetLibrary.load_asset(
                "/Game/LevelPrototyping/Materials/MI_PrototypeGrid_Gray")
        factory = unreal.MaterialInstanceConstantFactoryNew()
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mi = tools.create_asset("MI_FarmDirt", MAP_DIR, unreal.MaterialInstanceConstant, factory)
        if not mi:
            log("ERROR create MI_FarmDirt failed")
            return None
        if parent:
            mel.set_material_instance_parent(mi, parent)
        log("MI created")
    # Set Base Color (MI_Colorway style) and also Color if present
    for pname in ["Base Color", "Color", "BaseColor"]:
        try:
            mel.set_material_instance_vector_parameter_value(mi, pname, DIRT)
            log("set vec " + pname)
        except Exception as e:
            log("set {} fail: {}".format(pname, e))
    try:
        mel.update_material_instance(mi)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(MI_PATH)
    return mi


def ensure_border_mi():
    path = MAP_DIR + "/MI_FarmBorder"
    mel = unreal.MaterialEditingLibrary
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mi = unreal.EditorAssetLibrary.load_asset(path)
    else:
        parent = unreal.EditorAssetLibrary.load_asset(PARENT_MI)
        factory = unreal.MaterialInstanceConstantFactoryNew()
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mi = tools.create_asset("MI_FarmBorder", MAP_DIR, unreal.MaterialInstanceConstant, factory)
        if mi and parent:
            mel.set_material_instance_parent(mi, parent)
    if not mi:
        return None
    for pname in ["Base Color", "Color", "BaseColor"]:
        try:
            mel.set_material_instance_vector_parameter_value(mi, pname, BORDER)
        except Exception:
            pass
    try:
        mel.update_material_instance(mi)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(path)
    return mi


def find_actor_by_label(label):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def spawn_or_update_mesh(label, mesh_path, location, scale, material):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    if not mesh:
        log("ERROR missing mesh " + mesh_path)
        return None
    actor = find_actor_by_label(label)
    if actor is None:
        # spawn StaticMeshActor
        actor = eas.spawn_actor_from_class(
            unreal.StaticMeshActor, location, unreal.Rotator(0, 0, 0))
        if not actor:
            log("ERROR spawn failed " + label)
            return None
        actor.set_actor_label(label)
        log("spawned " + label)
    else:
        actor.set_actor_location(location, False, False)
        log("updated loc " + label)
    actor.set_actor_scale3d(scale)
    smc = actor.static_mesh_component
    smc.set_editor_property("static_mesh", mesh)
    if material:
        smc.set_material(0, material)
    # collision: keep QueryAndPhysics so player can stand if slightly raised; plane at z=1 is fine
    try:
        smc.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception:
        pass
    return actor


def move_player_start():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ps = None
    for a in eas.get_all_level_actors():
        if a.get_class().get_name() == "PlayerStart" or a.get_actor_label() == "PlayerStart":
            ps = a
            break
    if not ps:
        log("ERROR no PlayerStart")
        return
    old = ps.get_actor_location()
    ps.set_actor_location(SPAWN, False, False)
    log("PlayerStart {} -> {}".format(old, SPAWN))


def verify_grid_instance():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if "GridManager" in a.get_class().get_name() or a.get_actor_label() == "BP_GridManager":
            for name in ["CellSize", "GridWidth", "GridHeight", "GridOrigin"]:
                try:
                    v = a.get_editor_property(name)
                    log("Grid INST.{}={}".format(name, v))
                except Exception as e:
                    log("Grid INST.{} ERR {}".format(name, e))
            # keep actor at origin (GridOrigin is the logical origin)
            return a
    log("WARN no GridManager in level")
    return None


def save_level():
    try:
        # UE5.8 preferred
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = els.save_current_level()
        log("save_current_level -> " + str(ok))
    except Exception as e:
        log("LevelEditorSubsystem save fail: " + str(e))
        try:
            unreal.EditorLevelLibrary.save_current_level()
            log("EditorLevelLibrary.save_current_level ok")
        except Exception as e2:
            log("save fail: " + str(e2))


def main():
    log("=== START MAP BUILD ===")
    log("Farm AABB Origin={} size={}x{} center={}".format(ORIGIN, FARM_W, FARM_H, CENTER))
    dirt = ensure_dirt_mi()
    border_mi = ensure_border_mi()
    verify_grid_instance()

    # Plane: 100x100 units, scale so W/H world size
    plane_scale = unreal.Vector(FARM_W / 100.0, FARM_H / 100.0, 1.0)  # (20,20,1)
    spawn_or_update_mesh("FarmGround", PLANE_PATH, CENTER, plane_scale, dirt)

    # Thin border rails along edges (SM_Cube = 100^3)
    # thickness 20uu, height 30uu
    thick = 0.2   # 20 uu
    height_s = 0.3  # 30 uu
    half_w = FARM_W * 0.5
    half_h = FARM_H * 0.5
    z = 15.0
    borders = [
        # label, loc, scale
        ("FarmBorder_W", unreal.Vector(ORIGIN.x, CENTER.y, z),
         unreal.Vector(thick, FARM_H / 100.0, height_s)),
        ("FarmBorder_E", unreal.Vector(ORIGIN.x + FARM_W, CENTER.y, z),
         unreal.Vector(thick, FARM_H / 100.0, height_s)),
        ("FarmBorder_S", unreal.Vector(CENTER.x, ORIGIN.y, z),
         unreal.Vector(FARM_W / 100.0, thick, height_s)),
        ("FarmBorder_N", unreal.Vector(CENTER.x, ORIGIN.y + FARM_H, z),
         unreal.Vector(FARM_W / 100.0, thick, height_s)),
    ]
    for label, loc, sc in borders:
        spawn_or_update_mesh(label, CUBE_PATH, loc, sc, border_mi)

    move_player_start()
    save_level()

    # Final verify
    for label in ["FarmGround", "FarmBorder_W", "FarmBorder_E", "FarmBorder_S", "FarmBorder_N", "PlayerStart"]:
        a = find_actor_by_label(label)
        if a:
            loc = a.get_actor_location()
            sc = a.get_actor_scale3d()
            log("OK {} loc=({:.1f},{:.1f},{:.1f}) scale=({:.2f},{:.2f},{:.2f})".format(
                label, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z))
        else:
            log("MISSING " + label)
    log("=== END MAP BUILD ===")


main()
