# -*- coding: utf-8 -*-
"""Move till zone off the mid bridge: keep Hoe only at Grid(23-26,20-23)+HOE(25-27,20-22)."""
import unreal

def log(m):
    unreal.log("[CAMTILL2] " + str(m))
    print("[CAMTILL2] " + str(m))

CELL = 100.0
ORIGIN = unreal.Vector(0.0, 0.0, 0.0)
UNTILLED = "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Untilled"
Z_SOIL = 1.8
PATH_COLS = (21, 22)
# Bridge mid rows stay 18-19 after mirror; do not place hoe there
BRIDGE_ROWS = (18, 19)

TILL_X0, TILL_X1 = 23, 26
TILL_Y0, TILL_Y1 = 20, 23
HOE_X0, HOE_X1 = 25, 27
HOE_Y0, HOE_Y1 = 20, 22


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def cell_center(cx, cy, z=0.0):
    return unreal.Vector(ORIGIN.x + (cx + 0.5) * CELL,
                         ORIGIN.y + (cy + 0.5) * CELL, z)


def grid_of(a):
    loc = a.get_actor_location()
    return int(loc.x // CELL), int(loc.y // CELL)


def mesh_xy_size(mesh):
    try:
        box = mesh.get_bounding_box()
        return abs(box.max.x - box.min.x), abs(box.max.y - box.min.y)
    except Exception:
        return CELL, CELL


def wanted(gx, gy):
    if gy in BRIDGE_ROWS:
        return False
    if gx in PATH_COLS:
        return False
    in_till = TILL_X0 <= gx <= TILL_X1 and TILL_Y0 <= gy <= TILL_Y1
    in_hoe = HOE_X0 <= gx <= HOE_X1 and HOE_Y0 <= gy <= HOE_Y1
    return in_till or in_hoe


def main():
    # Remove ALL existing Hoe tiles (rebuild clean)
    removed = 0
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_Hoe_"):
            try:
                eas().destroy_actor(a)
                removed += 1
            except Exception:
                pass
    log("removed old Hoe={}".format(removed))

    # Also clear blockers in new till rect (soil/crop/tree/clump) but keep bridge/path/grass
    blockers = []
    keep_sub = ("Grass", "Path", "Water", "Bridge", "House", "Fence", "Cliff", "Bank", "Yard", "FarmShed")
    kill_sub = ("Soil", "Crop", "Corn", "Tomato", "Pumpkin", "Tree", "Bush", "Rock", "Clump", "Flower", "Crate", "Chest", "Hoe")
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if not lab.startswith("VMF_"):
            continue
        if any(k in lab for k in keep_sub):
            continue
        if not any(k in lab for k in kill_sub):
            continue
        gx, gy = grid_of(a)
        if wanted(gx, gy) or (TILL_X0 <= gx <= TILL_X1 and TILL_Y0 <= gy <= TILL_Y1):
            try:
                eas().destroy_actor(a)
                blockers.append(lab)
            except Exception:
                pass
    log("cleared blockers n={}: {}".format(len(blockers), blockers[:20]))

    mesh = unreal.EditorAssetLibrary.load_asset(UNTILLED)
    if not mesh:
        log("MISSING untilled")
        return
    sx, sy = mesh_xy_size(mesh)
    f = CELL / max(max(sx, sy), 1.0)
    scale = unreal.Vector(f, f, f)

    cells = set()
    for cy in range(TILL_Y0, TILL_Y1 + 1):
        for cx in range(TILL_X0, TILL_X1 + 1):
            if wanted(cx, cy):
                cells.add((cx, cy))
    for cy in range(HOE_Y0, HOE_Y1 + 1):
        for cx in range(HOE_X0, HOE_X1 + 1):
            if wanted(cx, cy):
                cells.add((cx, cy))

    placed = 0
    for cx, cy in sorted(cells):
        lab = "VMF_Hoe_{}_{}".format(cx, cy)
        loc = cell_center(cx, cy, Z_SOIL)
        actor = eas().spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator())
        actor.set_actor_label(lab)
        actor.set_actor_scale3d(scale)
        smc = actor.static_mesh_component
        smc.set_static_mesh(mesh)
        try:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            actor.set_actor_enable_collision(False)
        except Exception:
            pass
        placed += 1
    log("placed Hoe n={} cells={}".format(placed, sorted(cells)))

    try:
        unreal.EditorLevelLibrary.save_current_level()
        log("level saved")
    except Exception as e:
        log("save fail " + str(e))
        try:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
            log("level saved LES")
        except Exception as e2:
            log("save fail2 " + str(e2))

    # verify none on bridge
    bad = []
    good = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_Hoe_"):
            gx, gy = grid_of(a)
            if gy in BRIDGE_ROWS:
                bad.append((lab, gx, gy))
            else:
                good.append((lab, gx, gy))
    log("VERIFY good={} bad_on_bridge={}".format(len(good), bad))
    log("VERIFY cells={}".format(sorted(good, key=lambda t: (t[2], t[1]))))
    log("=== DONE ===")


if __name__ == "__main__":
    main()
