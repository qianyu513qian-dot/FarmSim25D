# -*- coding: utf-8 -*-
"""Fix water plane after -90 rot; clear grass that landed in water/cliff band."""
import unreal

def log(m):
    unreal.log("[WFIX] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# Collect cliff AABB
cx0 = cy0 = 1e9
cx1 = cy1 = -1e9
ncliff = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if not lab.startswith("VMF_Cliff_"):
        continue
    loc = a.get_actor_location()
    cx0 = min(cx0, loc.x); cx1 = max(cx1, loc.x)
    cy0 = min(cy0, loc.y); cy1 = max(cy1, loc.y)
    ncliff += 1
log("cliffs n={} aabb x=[{:.0f},{:.0f}] y=[{:.0f},{:.0f}]".format(ncliff, cx0, cx1, cy0, cy1))

# Water should sit on the offshore side of cliffs (lower Y than bank)
# Bank at y~500-800; water fills y from ~0 to bank, x across cliff span
water = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "VMF_Water_Left":
        water = a
        break

if water:
    # Plane 100uu; cover x [cx0-100, cx1+100] and y [0, cy1] roughly
    # After -90, water strip is along X (horizontal), thin in Y
    mid_x = (cx0 + cx1) * 0.5
    # water surface slightly below bank, covering from y=0 to just past cliffs
    water_y1 = cy1 + 50.0
    water_y0 = 0.0
    mid_y = (water_y0 + water_y1) * 0.5
    span_x = (cx1 - cx0) + 400.0
    span_y = max(water_y1 - water_y0, 400.0)
    sx = span_x / 100.0
    sy = span_y / 100.0
    water.set_actor_location(unreal.Vector(mid_x, mid_y, -5.0), False, True)
    water.set_actor_rotation(unreal.Rotator(0.0, 0.0, 0.0), False)
    water.set_actor_scale3d(unreal.Vector(sx, sy, 1.0))
    try:
        smc = water.static_mesh_component
        smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
    log("Water_Left -> ({:.0f},{:.0f},-5) scale=({:.1f},{:.1f}) span=({:.0f},{:.0f})".format(
        mid_x, mid_y, sx, sy, span_x, span_y))
else:
    log("NO VMF_Water_Left — spawn one")
    plane = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    mid_x = (cx0 + cx1) * 0.5
    mid_y = cy1 * 0.5
    span_x = (cx1 - cx0) + 400.0
    span_y = max(cy1, 400.0)
    water = eas.spawn_actor_from_class(unreal.StaticMeshActor,
                                       unreal.Vector(mid_x, mid_y, -5.0), unreal.Rotator())
    water.set_actor_label("VMF_Water_Left")
    water.set_actor_scale3d(unreal.Vector(span_x/100.0, span_y/100.0, 1.0))
    smc = water.static_mesh_component
    smc.set_static_mesh(plane)
    # try assign a blue-ish material if present
    for mp in (
        "/Game/Farm/Art/Mats/M_Water",
        "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Water",
        "/Engine/BasicShapes/BasicShapeMaterial",
    ):
        mat = unreal.EditorAssetLibrary.load_asset(mp)
        if mat:
            smc.set_material(0, mat)
            log("water mat " + mp)
            break
    smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)

# Destroy grass fills / grass tiles that sit in water band (y < cy1+100 and within cliff x)
kill = []
band_y = cy1 + 150.0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if not (lab.startswith("VMF_GrassFill_") or lab.startswith("VMF_Grass_")):
        continue
    loc = a.get_actor_location()
    if loc.y <= band_y and (cx0 - 150) <= loc.x <= (cx1 + 150):
        # keep grass that is clearly on farm side of bank? Bank is the cliff line;
        # anything with y < cy0-50 is deep water; between cy0 and cy1 is cliff cells
        # Remove grass in y < cy1 (water + cliff zone)
        if loc.y < cy1 + 50:
            kill.append(a)

removed = 0
for a in kill:
    try:
        eas.destroy_actor(a)
        removed += 1
    except Exception as e:
        log("destroy fail: " + str(e))
log("removed {} grass in water/cliff band y<={:.0f}".format(removed, band_y))

# Also remove grass that overlaps bridge cells? bridges are fine on top of water.
# Bridges at y~300-1300 — grass under bridge ok to remove in water band only.

try:
    els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    ok = els.save_current_level()
    log("save={}".format(ok))
except Exception as e:
    log("save fail " + str(e))

# Final summary
house = water_c = tree_c = None
hx = hy = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    loc = a.get_actor_location()
    if "FarmShed" in lab:
        house = (loc.x, loc.y)
    if lab == "PlayerStart":
        log("PlayerStart ({:.0f},{:.0f}) Grid≈({},{})".format(
            loc.x, loc.y, int(loc.x//100), int(loc.y//100)))
if house:
    log("house ({:.0f},{:.0f})".format(house[0], house[1]))
w = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "VMF_Water_Left":
        w = a.get_actor_location()
        sc = a.get_actor_scale3d()
        log("water final ({:.0f},{:.0f}) scale=({:.1f},{:.1f})".format(w.x, w.y, sc.x, sc.y))
log("DONE")
