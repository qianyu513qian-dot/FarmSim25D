# -*- coding: utf-8 -*-
"""Rotate entire VMF farm scene -90 deg yaw about farm center for camera yaw=-45.
+90 would put house bottom-left (wrong); -90 puts house top, water left, trees right.
Keeps camera, GridManager, IMC, VisualizeCell. Updates PlayerStart + FarmCollisionFloor.
"""
import unreal
import math

PREFIXES = ("VMF_", "Scene_")
KEEP_LABELS = {
    "BP_GridManager", "PlayerStart", "FarmCollisionFloor",
    "DirectionalLight", "SkyAtmosphere", "SkyLight",
    "ExponentialHeightFog", "VolumetricCloud", "WorldSettings",
    "AbstractNavData", "DefaultPhysicsVolume",
}
# Also skip BP_TopDown* placed pawns / template
SKIP_STARTSWITH = ("BP_", "Prototype", "TemplateFloor", "Floor_400x400")

ANGLE_DEG = -90.0  # CW; +90 leaves house bottom-left under yaw-45
CX, CY = 1950.0, 2000.0  # from probe AABB center

CELL = 100.0


def log(m):
    unreal.log("[ROT90] " + str(m))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def rot_xy(x, y, deg, cx, cy):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    dx, dy = x - cx, y - cy
    return cx + dx * c - dy * s, cy + dx * s + dy * c


def should_rotate(lab):
    if lab in KEEP_LABELS and lab not in ("PlayerStart", "FarmCollisionFloor"):
        # GridManager and lights stay; PlayerStart/floor handled specially
        if lab == "BP_GridManager":
            return False
        if lab in ("DirectionalLight", "SkyAtmosphere", "SkyLight",
                   "ExponentialHeightFog", "VolumetricCloud", "WorldSettings",
                   "AbstractNavData", "DefaultPhysicsVolume"):
            return False
    if lab.startswith("VMF_") or lab.startswith("Scene_"):
        return True
    if lab in ("PlayerStart", "FarmCollisionFloor"):
        return True  # move with farm
    return False


def hide_farmground():
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if lab in ("FarmGround", "FarmGround_Grass", "GroundPlane") or "FarmGround" in lab:
            try:
                a.set_actor_hidden_in_game(True)
                a.set_is_temporarily_hidden_in_editor(True)
                a.set_actor_location(unreal.Vector(-50000, -50000, -1000), False, True)
                try:
                    smc = a.static_mesh_component
                    if smc:
                        smc.set_visibility(False)
                        smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                except Exception:
                    pass
                log("hid " + lab)
            except Exception as e:
                log("hide fail {}: {}".format(lab, e))


def main():
    hide_farmground()

    actors = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if should_rotate(lab):
            actors.append(a)

    log("will rotate {} actors by {} deg about ({},{})".format(
        len(actors), ANGLE_DEG, CX, CY))

    moved = 0
    xs, ys = [], []
    house_after = None
    water_xs, water_ys = [], []
    tree_xs, tree_ys = [], []
    ps_after = None

    for a in actors:
        lab = a.get_actor_label()
        loc = a.get_actor_location()
        nx, ny = rot_xy(loc.x, loc.y, ANGLE_DEG, CX, CY)
        nz = loc.z
        try:
            old_rot = a.get_actor_rotation()
            new_yaw = old_rot.yaw + ANGLE_DEG
            # normalize
            while new_yaw > 180.0:
                new_yaw -= 360.0
            while new_yaw < -180.0:
                new_yaw += 360.0
            new_rot = unreal.Rotator(old_rot.pitch, new_yaw, old_rot.roll)
            a.set_actor_location(unreal.Vector(nx, ny, nz), False, True)
            a.set_actor_rotation(new_rot, False)
            moved += 1
            xs.append(nx)
            ys.append(ny)
            if "FarmShed" in lab or lab == "VMF_House_FarmShed":
                house_after = (nx, ny, nz)
            if any(k in lab for k in ("Water", "Cliff", "Bank", "Pond")):
                water_xs.append(nx)
                water_ys.append(ny)
            if "Tree" in lab or "Bush" in lab or "Shrub" in lab:
                tree_xs.append(nx)
                tree_ys.append(ny)
            if lab == "PlayerStart" or "PlayerStart" in a.get_class().get_name():
                ps_after = (nx, ny, nz)
        except Exception as e:
            log("fail {}: {}".format(lab, e))

    log("moved={}".format(moved))
    if xs:
        log("new AABB x=[{:.0f},{:.0f}] y=[{:.0f},{:.0f}]".format(
            min(xs), max(xs), min(ys), max(ys)))
        mid_x = (min(xs) + max(xs)) * 0.5
        mid_y = (min(ys) + max(ys)) * 0.5
        span_x = max(xs) - min(xs) + 200.0
        span_y = max(ys) - min(ys) + 200.0
    else:
        mid_x, mid_y, span_x, span_y = CX, CY, 4000.0, 4000.0

    if house_after:
        log("house after @ ({:.0f},{:.0f})".format(house_after[0], house_after[1]))
    if water_xs:
        log("water centroid after ({:.0f},{:.0f})".format(
            sum(water_xs)/len(water_xs), sum(water_ys)/len(water_ys)))
    if tree_xs:
        log("tree centroid after ({:.0f},{:.0f})".format(
            sum(tree_xs)/len(tree_xs), sum(tree_ys)/len(tree_ys)))

    # PlayerStart: ensure on grass/path, Z=100, facing toward fields (roughly toward center)
    ps = None
    for a in eas().get_all_level_actors():
        if a.get_actor_label() == "PlayerStart" or "PlayerStart" in a.get_class().get_name():
            if a.get_actor_label() == "PlayerStart" or ps is None:
                ps = a
    if ps:
        loc = ps.get_actor_location()
        # Keep rotated position but clamp into farm and lift Z
        px, py = loc.x, loc.y
        # Prefer near path: after -90 path was around x~1900-2200 varying y; player went to ~1600,1600
        # Nudge toward open mid field if needed
        px = max(150.0, min(3850.0, px))
        py = max(150.0, min(3850.0, py))
        ps.set_actor_location(unreal.Vector(px, py, 100.0), False, True)
        # Face toward house-ish / farmable (screen-up roughly +X for our mapping after rot? use yaw 0)
        try:
            face = unreal.Rotator(0.0, 0.0, 0.0)
            ps.set_actor_rotation(face, False)
        except Exception:
            pass
        gx = int(px // CELL)
        gy = int(py // CELL)
        log("PlayerStart @ ({:.0f},{:.0f},100) Grid≈({},{})".format(px, py, gx, gy))
    else:
        log("WARN no PlayerStart")

    # Resize/recenter FarmCollisionFloor to cover new AABB
    floor = None
    for a in eas().get_all_level_actors():
        if a.get_actor_label() == "FarmCollisionFloor":
            floor = a
            break
    if floor:
        floor.set_actor_location(unreal.Vector(mid_x, mid_y, 0.0), False, True)
        # Plane default 100uu; scale so size ~= span
        sx = max(span_x, 4200.0) / 100.0
        sy = max(span_y, 4200.0) / 100.0
        floor.set_actor_scale3d(unreal.Vector(sx, sy, 1.0))
        try:
            smc = floor.static_mesh_component
            if smc:
                smc.set_visibility(False)
                smc.set_hidden_in_game(True)
                smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        except Exception as e:
            log("floor smc: " + str(e))
        log("FarmCollisionFloor center=({:.0f},{:.0f}) scale=({:.1f},{:.1f})".format(
            mid_x, mid_y, sx, sy))
    else:
        # spawn invisible collision plane
        try:
            plane = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
            loc = unreal.Vector(mid_x, mid_y, 0.0)
            floor = eas().spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator())
            floor.set_actor_label("FarmCollisionFloor")
            sx = max(span_x, 4200.0) / 100.0
            sy = max(span_y, 4200.0) / 100.0
            floor.set_actor_scale3d(unreal.Vector(sx, sy, 1.0))
            smc = floor.static_mesh_component
            smc.set_static_mesh(plane)
            smc.set_visibility(False)
            smc.set_hidden_in_game(True)
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            log("spawned FarmCollisionFloor")
        except Exception as e:
            log("spawn floor fail: " + str(e))

    # Fill grass holes: any grid cell in [0,40) with no VMF_Grass_* nearby get a grass tile
    # Build occupancy from existing grass centers
    grass_keys = set()
    grass_mesh = None
    unit = 0.01
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("VMF_Grass_"):
            loc = a.get_actor_location()
            gx = int(round((loc.x - 50.0) / CELL))
            gy = int(round((loc.y - 50.0) / CELL))
            grass_keys.add((gx, gy))
            if grass_mesh is None:
                try:
                    grass_mesh = a.static_mesh_component.static_mesh
                except Exception:
                    pass
    if grass_mesh is None:
        grass_mesh = unreal.EditorAssetLibrary.load_asset(
            "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass")
        if not grass_mesh:
            # try GroundStudy
            for p in (
                "/Game/Farm/VoxelMicroFarm/Models/Expansion02/GroundStudy/SM_VMF_GroundStudy_Grass_A",
                "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass",
            ):
                grass_mesh = unreal.EditorAssetLibrary.load_asset(p)
                if grass_mesh:
                    break

    # Occupancy of ANY ground-ish VMF (path/soil/water/cliff/bridge/grass) to avoid stacking
    occupied = set(grass_keys)
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if not lab.startswith("VMF_"):
            continue
        if any(k in lab for k in ("Path", "Soil", "Water", "Cliff", "Bridge", "Pier",
                                   "Deck", "Yard", "Bank", "Pond", "Grass")):
            loc = a.get_actor_location()
            gx = int(round((loc.x - 50.0) / CELL))
            gy = int(round((loc.y - 50.0) / CELL))
            occupied.add((gx, gy))

    # Fill bounding box of farm with grass where empty (walkable island solid)
    filled = 0
    if grass_mesh and xs:
        x0 = int(max(0, math.floor(min(xs) / CELL)))
        x1 = int(min(39, math.ceil(max(xs) / CELL)))
        y0 = int(max(0, math.floor(min(ys) / CELL)))
        y1 = int(min(39, math.ceil(max(ys) / CELL)))
        log("fill grass window x=[{},{}] y=[{},{}] occupied={}".format(
            x0, x1, y0, y1, len(occupied)))
        for gx in range(x0, x1 + 1):
            for gy in range(y0, y1 + 1):
                if (gx, gy) in occupied:
                    continue
                # skip deep water region: if near water centroid and far from grass? just fill all empty
                loc = unreal.Vector((gx + 0.5) * CELL, (gy + 0.5) * CELL, 0.5)
                actor = eas().spawn_actor_from_class(
                    unreal.StaticMeshActor, loc, unreal.Rotator())
                actor.set_actor_label("VMF_GrassFill_{}_{}".format(gx, gy))
                actor.set_actor_scale3d(unreal.Vector(unit, unit, unit))
                smc = actor.static_mesh_component
                smc.set_static_mesh(grass_mesh)
                try:
                    smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                except Exception:
                    pass
                filled += 1
                occupied.add((gx, gy))
        log("filled {} grass tiles".format(filled))
    else:
        log("skip grass fill (mesh={} xs={})".format(bool(grass_mesh), len(xs)))

    # Save
    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = els.save_current_level()
        log("save_current_level={}".format(ok))
    except Exception as e:
        log("save fail: " + str(e))

    log("DONE angle={} moved={} filled_grass={}".format(ANGLE_DEG, moved, filled))


main()
