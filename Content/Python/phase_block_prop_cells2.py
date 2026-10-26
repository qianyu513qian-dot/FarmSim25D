# -*- coding: utf-8 -*-
"""Rebuild BlockedIndices = zone(path/bridge/cliff/yard/water) + prop cells; tight footprints."""
import unreal
from collections import defaultdict

TAG = "[BLOCK_PROPS2]"
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

CELL = 100.0
WIDTH = 40
HEIGHT = 40

PROP_PREFIXES = (
    "VMF_Tree", "VMF_Crate", "VMF_Barrel", "VMF_Bush", "VMF_Rock", "VMF_Fence",
    "VMF_Scarecrow", "VMF_House", "VMF_Well", "VMF_ToolShelter", "VMF_ChickenCoop",
    "VMF_ShippingChest", "VMF_HayBale", "VMF_Wheelbarrow", "VMF_Mailbox",
    "VMF_Flower", "VMF_Shrub", "VMF_Stump", "VMF_TallGrass", "VMF_ShoreClump",
    "VMF_Clump", "VMF_PumpAccent",
)

# Only large buildings use AABB footprint
FOOTPRINT_PREFIXES = ("VMF_House", "VMF_ToolShelter", "VMF_ChickenCoop", "VMF_Well")


def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def loc_to_cell(x, y):
    return int(x // CELL), int(y // CELL)


def parse_cell(lab):
    parts = (lab or "").split("_")
    try:
        return int(parts[-2]), int(parts[-1])
    except Exception:
        return None


def in_grid(gx, gy):
    return 0 <= gx < WIDTH and 0 <= gy < HEIGHT


def flat_index(gx, gy):
    return gy * WIDTH + gx


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


def is_water_cell(cx, cy):
    return 0 <= cx < WIDTH and 0 <= cy < HEIGHT and cx <= water_edge_x(cy)


def cells_from_bounds(actor, pad=12.0):
    cells = set()
    try:
        origin, extent = actor.get_actor_bounds(False)
        minx = origin.x - extent.x + pad
        maxx = origin.x + extent.x - pad
        miny = origin.y - extent.y + pad
        maxy = origin.y + extent.y - pad
        if maxx < minx:
            minx = maxx = origin.x
        if maxy < miny:
            miny = maxy = origin.y
        gx0, gy0 = loc_to_cell(minx, miny)
        gx1, gy1 = loc_to_cell(maxx, maxy)
        if gx0 > gx1:
            gx0, gx1 = gx1, gx0
        if gy0 > gy1:
            gy0, gy1 = gy1, gy0
        for gy in range(gy0, gy1 + 1):
            for gx in range(gx0, gx1 + 1):
                if in_grid(gx, gy):
                    cells.add((gx, gy))
    except Exception as ex:
        log("bounds: " + str(ex))
    return cells


def collect_zone_cells():
    path, bridge, cliff, yard = set(), set(), set(), set()
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        c = parse_cell(lab)
        if not c:
            # PathV_12 etc may be VMF_PathV_x_y
            if lab.startswith("VMF_Path") or lab.startswith("VMF_Bridge") or lab.startswith("VMF_Cliff_") or lab.startswith("VMF_Yard_"):
                loc = a.get_actor_location()
                c = loc_to_cell(loc.x, loc.y)
            else:
                continue
        if not in_grid(*c):
            continue
        if lab.startswith("VMF_Path"):
            path.add(c)
        elif lab.startswith("VMF_Bridge"):
            bridge.add(c)
        elif lab.startswith("VMF_Cliff_"):
            cliff.add(c)
        elif lab.startswith("VMF_Yard_"):
            yard.add(c)
    water = {(cx, cy) for cy in range(HEIGHT) for cx in range(WIDTH) if is_water_cell(cx, cy)}
    log("zones path={} bridge={} cliff={} yard={} water={}".format(
        len(path), len(bridge), len(cliff), len(yard), len(water)))
    return path | bridge | cliff | yard | water


def collect_prop_cells():
    cells = set()
    by_cat = defaultdict(set)
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        matched = None
        for pref in PROP_PREFIXES:
            if lab.startswith(pref):
                matched = pref.replace("VMF_", "")
                break
        if matched is None and "Clump" in lab and lab.startswith("VMF_"):
            matched = "Clump"
        if matched is None:
            continue

        if any(lab.startswith(p) for p in FOOTPRINT_PREFIXES):
            cset = cells_from_bounds(a)
            if not cset:
                loc = a.get_actor_location()
                c = parse_cell(lab) or loc_to_cell(loc.x, loc.y)
                cset = {c} if in_grid(*c) else set()
        else:
            loc = a.get_actor_location()
            c = parse_cell(lab)
            if c is None:
                c = loc_to_cell(loc.x, loc.y)
            cset = {c} if in_grid(*c) else set()

        for c in cset:
            cells.add(c)
            by_cat[matched].add(c)
    log("prop cells={}".format(len(cells)))
    for cat in sorted(by_cat.keys()):
        log("  {}={}".format(cat, len(by_cat[cat])))
    # scarecrow should be 1 cell now
    sc = by_cat.get("Scarecrow", set())
    log("Scarecrow cells={}".format(sorted(sc)))
    house = by_cat.get("House", set())
    log("House cells n={} sample={}".format(len(house), sorted(house)[:12]))
    return cells, by_cat


def find_gm():
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        cn = a.get_class().get_name()
        if "GridManager" in lab or "GridManager" in cn:
            return a
    return None


def apply_indices(blocked_cells):
    indices = sorted(flat_index(gx, gy) for gx, gy in blocked_cells if in_grid(gx, gy))
    # unique
    indices = sorted(set(indices))
    ua = unreal.Array(int)
    for i in indices:
        ua.append(int(i))

    gm = find_gm()
    if gm:
        gm.set_editor_property("BlockedIndices", ua)
        log("GM BlockedIndices={}".format(len(indices)))
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("BlockedIndices", ua)
    log("CDO BlockedIndices={}".format(len(indices)))

    try:
        bel.compile_blueprint(bp)
        log("compile OK")
    except Exception as ex:
        log("compile: " + str(ex))
    try:
        unreal.EditorAssetLibrary.save_asset(MGR)
    except Exception as ex:
        log("save bp: " + str(ex))
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as ex:
        log("dirty: " + str(ex))
    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        els.save_current_level()
        log("level saved")
    except Exception as ex:
        log("level save: " + str(ex))

    # verify spots
    s = set(indices)
    for name, gx, gy in (("Crate_1", 22, 16), ("Scarecrow", 21, 22), ("Barrel", 20, 27),
                         ("blank_near", 25, 20), ("Tree", 38, 34)):
        log("spot {} ({},{}) blocked={}".format(name, gx, gy, flat_index(gx, gy) in s))
    return indices


def main():
    log("BEGIN rebuild")
    zones = collect_zone_cells()
    props, cats = collect_prop_cells()
    blocked = zones | props
    log("union blocked cells={}".format(len(blocked)))
    indices = apply_indices(blocked)
    log("SUMMARY total_blocked={} zone={} prop={} cats={}".format(
        len(indices), len(zones), len(props), {k: len(v) for k, v in sorted(cats.items())}))
    log("DONE")


main()
