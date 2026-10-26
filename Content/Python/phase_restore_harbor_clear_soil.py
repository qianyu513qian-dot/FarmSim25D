# -*- coding: utf-8 -*-
"""Clear leftover SoilDry visuals (Cliff/Yard/any Soil*) and restore harbor pier rails/posts.

Does NOT touch: BlockedIndices, TillCell, AirWalls, IMC, camera, Cropout.
Force-saves Lvl_TopDown + ExternalActors for World Partition persistence.
"""
import unreal
import time

TAG = "[RESTORE_HARBOR]"
CELL = 100.0
WIDTH = 40
HEIGHT = 40
UNIT = 0.01
Z_GRASS = 0.5
Z_BRIDGE = 5.0
Z_RAIL = 5.0

BRIDGE_MID_ROWS = (18, 19)
BRIDGE_SOUTH_ROWS = (4, 5)
BRIDGE_X0 = 2
BRIDGE_X1 = 16

GRASS_MESH = "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass"
MESH = {
    "FenceLow": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Fence_Low_Straight",
    "FenceLowEnd": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Fence_Low_EndPost",
    "FenceEnd": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Fence_Picket_EndPost",
    "FenceEndBasic": "/Game/Farm/VoxelMicroFarm/Models/Fences/SM_VMF_Fence_EndPost",
    "Grass": GRASS_MESH,
}


def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def cell_center(cx, cy, z=0.0):
    return unreal.Vector(cx * CELL + CELL * 0.5, cy * CELL + CELL * 0.5, z)


def water_edge_x(cy):
    base = 5
    wobble = (cy * 7 + 3) % 5
    if wobble == 0:
        return base - 1
    if wobble == 1:
        return base
    if wobble == 2:
        return base + 1
    if wobble == 3:
        return base
    return base + 2


def parse_cell(lab):
    parts = (lab or "").split("_")
    try:
        return int(parts[-2]), int(parts[-1])
    except Exception:
        return None


def load_mesh(key_or_path):
    path = MESH.get(key_or_path, key_or_path)
    return unreal.EditorAssetLibrary.load_asset(path)


def mesh_xy_size(mesh):
    try:
        b = mesh.get_bounding_box()
        return max(b.max.x - b.min.x, 1.0), max(b.max.y - b.min.y, 1.0)
    except Exception:
        try:
            # StaticMesh.get_bounds -> BoxSphereBounds
            bounds = mesh.get_editor_property("extended_bounds")
        except Exception:
            bounds = None
        if bounds is None:
            return 10000.0, 10000.0
        try:
            e = bounds.box_extent
            return max(e.x * 2.0, 1.0), max(e.y * 2.0, 1.0)
        except Exception:
            return 10000.0, 10000.0


def find_by_label(full):
    for a in eas().get_all_level_actors():
        if (a.get_actor_label() or "") == full:
            return a
    return None


def actor_mesh_path(a):
    try:
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            try:
                sm = c.get_editor_property("static_mesh")
                if sm:
                    return sm.get_path_name()
            except Exception:
                pass
    except Exception:
        pass
    return ""


def spawn_or_update(label, mesh_key, cx, cy, yaw=0.0, z=0.0, fit_cells=(1, 1), collision=True):
    mesh = load_mesh(mesh_key)
    if not mesh:
        log("MISSING mesh " + str(mesh_key))
        return None
    full = label if label.startswith("VMF_") else ("VMF_" + label)
    sx, sy = mesh_xy_size(mesh)
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
    loc = unreal.Vector(
        (cx + tw * 0.5) * CELL,
        (cy + th * 0.5) * CELL,
        z,
    )
    rot = unreal.Rotator(0.0, float(yaw), 0.0)
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
        if collision:
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        else:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
    try:
        actor.set_actor_hidden_in_game(False)
        actor.set_is_temporarily_hidden_in_editor(False)
        smc.set_visibility(True, True)
    except Exception:
        pass
    return actor


def ensure_grass(cx, cy, existing_grass):
    label = "VMF_Grass_{}_{}".format(cx, cy)
    if (cx, cy) in existing_grass:
        # unhide / ensure mesh
        a = find_by_label(label)
        if a:
            try:
                a.set_actor_hidden_in_game(False)
                a.set_is_temporarily_hidden_in_editor(False)
            except Exception:
                pass
        return False
    if find_by_label(label):
        return False
    spawn_or_update(label, "Grass", cx, cy, z=Z_GRASS, fit_cells=(1, 1), collision=False)
    return True


def collect_grass_cells():
    g = set()
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_Grass_") and "Clump" not in lab and "Tall" not in lab:
            c = parse_cell(lab)
            if c:
                g.add(c)
    return g


def destroy_brown_soil_visuals():
    """Remove Cliff/Yard SoilDry tiles and any leftover Soil/Crop/Hoe labeled actors.
    Keep path/bridge/deck/water/airwall/house/fence/props.
    """
    killed = []
    cells_need_grass = set()
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        mpath = actor_mesh_path(a)
        kill = False
        reason = ""

        # Never touch these
        if lab.startswith("AirWall") or lab.startswith("VMF_Bridge") or lab.startswith("VMF_Path"):
            continue
        if lab.startswith("VMF_Fence") or lab.startswith("VMF_House") or lab.startswith("VMF_Water"):
            continue
        if any(lab.startswith(p) for p in (
            "VMF_Tree", "VMF_Scarecrow", "VMF_Barrel", "VMF_Hay", "VMF_Crate",
            "VMF_Shipping", "VMF_Wheel", "VMF_Mailbox", "VMF_Well", "VMF_Chicken",
            "VMF_Tool", "VMF_Flower", "VMF_Bush", "VMF_Rock", "VMF_Stump",
            "VMF_Shrub", "VMF_Clump", "VMF_Shore", "VMF_Tall", "VMF_Pump",
            "VMF_Grass",
        )):
            # unless mesh is Soil (shouldn't be)
            if "Soil" not in mpath:
                continue

        low = lab.lower()
        if lab.startswith("VMF_Cliff_"):
            kill = True
            reason = "cliff_SoilDry"
        elif lab.startswith("VMF_Yard_"):
            kill = True
            reason = "yard_SoilDry"
        elif lab.startswith("VMF_Soil_") or lab.startswith("VMF_Crop"):
            kill = True
            reason = "preset_soil_crop"
        elif any(k in lab for k in ("Soil", "Hoe", "Untilled")) and "Path" not in lab:
            kill = True
            reason = "label_soilish"
        elif "Soil" in mpath and not lab.startswith("VMF_Bridge") and not lab.startswith("VMF_Path"):
            # any other actor still using Soil mesh
            kill = True
            reason = "mesh_Soil"

        if not kill:
            continue

        c = parse_cell(lab)
        if c:
            cells_need_grass.add(c)
        try:
            eas().destroy_actor(a)
            killed.append((lab, reason))
        except Exception as ex:
            log("destroy fail {}: {}".format(lab, ex))

    log("deleted brown/soil visuals n={}".format(len(killed)))
    # summarize reasons
    from collections import Counter
    rc = Counter(r for _, r in killed)
    log("delete reasons " + str(dict(rc)))
    log("delete sample " + str(killed[:20]))
    return killed, cells_need_grass


def restore_grass_on(cells):
    existing = collect_grass_cells()
    n = 0
    for cx, cy in sorted(cells):
        if not (0 <= cx < WIDTH and 0 <= cy < HEIGHT):
            continue
        # skip water cells (visual under water plane)
        if cx <= water_edge_x(cy):
            continue
        if ensure_grass(cx, cy, existing):
            n += 1
            existing.add((cx, cy))
    log("restored grass on cleared cells n={}".format(n))
    return n


def restore_harbor_piers():
    """Re-place low fence rails + end posts along Mid/South bridge decks."""
    # Prefer Low_EndPost for thick pier posts; fallback to Picket EndPost / basic EndPost
    post_key = "FenceLowEnd"
    if not load_mesh(post_key):
        post_key = "FenceEnd" if load_mesh("FenceEnd") else "FenceEndBasic"
    rail_key = "FenceLow"
    if not load_mesh(rail_key):
        log("ERROR no FenceLow mesh — cannot restore pier rails")
        return 0, 0

    rails = 0
    posts = 0
    for tag, rows in (("Mid", BRIDGE_MID_ROWS), ("South", BRIDGE_SOUTH_ROWS)):
        rail_n = rows[-1] + 1
        rail_s = rows[0] - 1
        # rails only over water + near shore (match original: up to water_edge+3, capped at BRIDGE_X1)
        mid_cy = rows[0]
        x_max = min(BRIDGE_X1, water_edge_x(mid_cy) + 3)
        for cx in range(BRIDGE_X0, x_max + 1):
            if 0 <= rail_n < HEIGHT:
                if spawn_or_update("Bridge{}RailN_{}".format(tag, cx), rail_key,
                                   cx, rail_n, yaw=0.0, z=Z_RAIL, fit_cells=(1, 1), collision=True):
                    rails += 1
            if 0 <= rail_s < HEIGHT:
                if spawn_or_update("Bridge{}RailS_{}".format(tag, cx), rail_key,
                                   cx, rail_s, yaw=0.0, z=Z_RAIL, fit_cells=(1, 1), collision=True):
                    rails += 1
            # thick posts every cell along both rails (harbor look from old reference)
            if 0 <= rail_n < HEIGHT:
                if spawn_or_update("Bridge{}PostN_{}".format(tag, cx), post_key,
                                   cx, rail_n, yaw=90.0, z=Z_RAIL, fit_cells=(1, 1), collision=True):
                    posts += 1
            if 0 <= rail_s < HEIGHT:
                if spawn_or_update("Bridge{}PostS_{}".format(tag, cx), post_key,
                                   cx, rail_s, yaw=90.0, z=Z_RAIL, fit_cells=(1, 1), collision=True):
                    posts += 1

        # tip posts at water end (cx=BRIDGE_X0) on deck rows — classic scene_build labels
        tip = BRIDGE_X0
        if spawn_or_update("Bridge{}PostN".format(tag), post_key,
                           tip, rows[-1], yaw=90.0, z=Z_RAIL, fit_cells=(1, 1), collision=True):
            posts += 1
        if spawn_or_update("Bridge{}PostS".format(tag), post_key,
                           tip, rows[0], yaw=90.0, z=Z_RAIL, fit_cells=(1, 1), collision=True):
            posts += 1

    log("restored pier rails={} posts={} (post_mesh={})".format(rails, posts, post_key))
    return rails, posts


def harden_airwall_invisibility():
    """If any AirWall cube somehow visible, hide mesh but keep collision."""
    n = 0
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if not lab.startswith("AirWall"):
            continue
        try:
            a.set_actor_hidden_in_game(True)
            a.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass
        try:
            smc = a.static_mesh_component
            smc.set_visibility(False, True)
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        except Exception:
            pass
        n += 1
    log("airwalls re-hidden n={}".format(n))
    return n


def force_save_level():
    results = {}
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        results["save_current_level"] = bool(les.save_current_level())
    except Exception as e:
        results["save_current_level"] = str(e)
        try:
            unreal.EditorLevelLibrary.save_current_level()
            results["save_current_level_ell"] = True
        except Exception as e2:
            results["save_current_level_ell"] = str(e2)
    try:
        results["save_dirty"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
    except Exception as e:
        results["save_dirty"] = str(e)
    try:
        results["save_ext"] = bool(unreal.EditorAssetLibrary.save_directory(
            "/Game/__ExternalActors__/TopDown/Lvl_TopDown", True, True))
    except Exception as e:
        results["save_ext"] = str(e)
    try:
        results["save_lvl"] = bool(unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Lvl_TopDown"))
    except Exception as e:
        results["save_lvl"] = str(e)
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception:
        pass
    log("save results " + str(results))
    return results


def verify():
    n_cliff = n_yard = n_soil_lab = n_soil_mesh = n_rail = n_post = n_deck = 0
    brown_left = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        mp = actor_mesh_path(a)
        if lab.startswith("VMF_Cliff_"):
            n_cliff += 1
        if lab.startswith("VMF_Yard_"):
            n_yard += 1
        if "Soil" in lab:
            n_soil_lab += 1
        if "Soil" in mp and not lab.startswith("VMF_Bridge") and not lab.startswith("VMF_Path"):
            n_soil_mesh += 1
            brown_left.append(lab)
        if "Rail" in lab and "Bridge" in lab:
            n_rail += 1
        if "Post" in lab and "Bridge" in lab:
            n_post += 1
        if lab.startswith("VMF_BridgeMid_") or lab.startswith("VMF_BridgeSouth_"):
            if "Rail" not in lab and "Post" not in lab:
                n_deck += 1
    log("VERIFY cliff={} yard={} soil_lab={} soil_mesh={} rails={} posts={} decks={}".format(
        n_cliff, n_yard, n_soil_lab, n_soil_mesh, n_rail, n_post, n_deck))
    if brown_left:
        log("VERIFY brown leftover sample " + str(brown_left[:15]))
    return {
        "cliff": n_cliff, "yard": n_yard, "soil_lab": n_soil_lab,
        "soil_mesh": n_soil_mesh, "rails": n_rail, "posts": n_post, "decks": n_deck,
    }


def main():
    log("=== start ===")
    killed, cells = destroy_brown_soil_visuals()
    grass_n = restore_grass_on(cells)
    rails, posts = restore_harbor_piers()
    harden_airwall_invisibility()
    # brief yield for World Partition
    try:
        time.sleep(0.3)
    except Exception:
        pass
    v = verify()
    save = force_save_level()
    # second verify after save
    try:
        time.sleep(0.2)
    except Exception:
        pass
    v2 = verify()
    log("SUMMARY deleted={} grass={} rails={} posts={} verify={} save={}".format(
        len(killed), grass_n, rails, posts, v2, save))
    log("=== done ===")


main()
