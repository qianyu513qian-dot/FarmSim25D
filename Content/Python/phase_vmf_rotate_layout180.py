# -*- coding: utf-8 -*-
"""Second -90 yaw (total -180 from pre-fix) for Stardew sides under camera yaw=-45.
After first -90: house top-right, water top, trees bottom-right.
After second -90: house top-center, water left, trees right.
"""
import unreal
import math

ANGLE_DEG = -90.0
CX, CY = 1950.0, 2000.0
CELL = 100.0

def log(m):
    unreal.log("[ROT180] " + str(m))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def rot_xy(x, y, deg, cx, cy):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    dx, dy = x - cx, y - cy
    return cx + dx * c - dy * s, cy + dx * s + dy * c

def should_rotate(lab):
    if lab == "BP_GridManager":
        return False
    if lab in ("DirectionalLight", "SkyAtmosphere", "SkyLight",
               "ExponentialHeightFog", "VolumetricCloud", "WorldSettings",
               "AbstractNavData", "DefaultPhysicsVolume"):
        return False
    if lab.startswith("VMF_") or lab.startswith("Scene_"):
        return True
    if lab in ("PlayerStart", "FarmCollisionFloor"):
        return True
    return False

actors = [a for a in eas().get_all_level_actors() if should_rotate(a.get_actor_label())]
log("rotating {} actors by {}".format(len(actors), ANGLE_DEG))
moved = 0
xs, ys = [], []
for a in actors:
    lab = a.get_actor_label()
    loc = a.get_actor_location()
    nx, ny = rot_xy(loc.x, loc.y, ANGLE_DEG, CX, CY)
    try:
        old = a.get_actor_rotation()
        yaw = old.yaw + ANGLE_DEG
        while yaw > 180: yaw -= 360
        while yaw < -180: yaw += 360
        a.set_actor_location(unreal.Vector(nx, ny, loc.z), False, True)
        a.set_actor_rotation(unreal.Rotator(old.pitch, yaw, old.roll), False)
        moved += 1
        xs.append(nx); ys.append(ny)
    except Exception as e:
        log("fail {}: {}".format(lab, e))
log("moved={}".format(moved))

# PlayerStart
ps = None
for a in eas().get_all_level_actors():
    if a.get_actor_label() == "PlayerStart":
        ps = a
        break
if ps:
    loc = ps.get_actor_location()
    px = max(150.0, min(3850.0, loc.x))
    py = max(150.0, min(3850.0, loc.y))
    # Prefer central path/grass — after 180 from original, PS ~ (1600,1600)-> another -90
    # Recalc: was (1600,1600): dx=-350,dy=-400 -> (-400,350)->(1550,2350)
    ps.set_actor_location(unreal.Vector(px, py, 100.0), False, True)
    log("PlayerStart ({:.0f},{:.0f}) Grid≈({},{})".format(px, py, int(px//CELL), int(py//CELL)))

# FarmCollisionFloor recenter
floor = None
for a in eas().get_all_level_actors():
    if a.get_actor_label() == "FarmCollisionFloor":
        floor = a
        break
if floor and xs:
    mid_x = (min(xs)+max(xs))*0.5
    mid_y = (min(ys)+max(ys))*0.5
    span_x = max(xs)-min(xs)+200
    span_y = max(ys)-min(ys)+200
    floor.set_actor_location(unreal.Vector(mid_x, mid_y, 0.0), False, True)
    floor.set_actor_scale3d(unreal.Vector(max(span_x,4200)/100.0, max(span_y,4200)/100.0, 1.0))
    log("floor ({:.0f},{:.0f})".format(mid_x, mid_y))

# Fix water to cliff band again
cx0=cy0=1e9; cx1=cy1=-1e9
for a in eas().get_all_level_actors():
    if a.get_actor_label().startswith("VMF_Cliff_"):
        loc = a.get_actor_location()
        cx0=min(cx0,loc.x); cx1=max(cx1,loc.x)
        cy0=min(cy0,loc.y); cy1=max(cy1,loc.y)
log("cliffs aabb x=[{:.0f},{:.0f}] y=[{:.0f},{:.0f}]".format(cx0,cx1,cy0,cy1))

water = None
for a in eas().get_all_level_actors():
    if a.get_actor_label() == "VMF_Water_Left":
        water = a
        break

# After second -90, cliffs should be at low X (left). Water offshore = further left (lower X).
if water and cx0 < 1e8:
    # Determine dominant cliff axis: if cliffs span more in Y than X, bank is vertical (left/right)
    span_cx = cx1 - cx0
    span_cy = cy1 - cy0
    log("cliff spans dx={:.0f} dy={:.0f}".format(span_cx, span_cy))
    if span_cy >= span_cx:
        # vertical bank (left or right edge) — water further in X away from farm center
        mid_y = (cy0 + cy1) * 0.5
        farm_cx = 2000.0
        if (cx0 + cx1) * 0.5 < farm_cx:
            # bank on left; water at even lower X
            water_x1 = cx0 + 50
            water_x0 = max(-200.0, cx0 - 900.0)
            mid_x = (water_x0 + water_x1) * 0.5
        else:
            water_x0 = cx1 - 50
            water_x1 = cx1 + 900.0
            mid_x = (water_x0 + water_x1) * 0.5
        span_x = abs(water_x1 - water_x0)
        span_y = (cy1 - cy0) + 400.0
        water.set_actor_location(unreal.Vector(mid_x, mid_y, -5.0), False, True)
        water.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
        water.set_actor_scale3d(unreal.Vector(span_x/100.0, span_y/100.0, 1.0))
        log("water vertical-bank @ ({:.0f},{:.0f}) scale=({:.1f},{:.1f})".format(
            mid_x, mid_y, span_x/100.0, span_y/100.0))
        # clear grass in water x-band
        band_x_max = max(water_x0, water_x1) + 50
        band_x_min = min(water_x0, water_x1) - 50
        # also include cliff x
        band_x_min = min(band_x_min, cx0 - 50)
        band_x_max = max(band_x_max, cx1 + 50)
        kill = []
        for a in eas().get_all_level_actors():
            lab = a.get_actor_label()
            if not (lab.startswith("VMF_GrassFill_") or lab.startswith("VMF_Grass_")):
                continue
            loc = a.get_actor_location()
            if band_x_min <= loc.x <= band_x_max and (cy0 - 200) <= loc.y <= (cy1 + 200):
                if loc.x <= cx1 + 80:  # water + cliff strip
                    kill.append(a)
        for a in kill:
            try: eas().destroy_actor(a)
            except Exception: pass
        log("removed {} grass in left water band".format(len(kill)))
    else:
        # horizontal bank
        mid_x = (cx0 + cx1) * 0.5
        farm_cy = 2000.0
        if (cy0 + cy1) * 0.5 < farm_cy:
            water_y1 = cy0 + 50
            water_y0 = max(-200.0, cy0 - 900.0)
            mid_y = (water_y0 + water_y1) * 0.5
        else:
            water_y0 = cy1 - 50
            water_y1 = cy1 + 900.0
            mid_y = (water_y0 + water_y1) * 0.5
        span_x = (cx1 - cx0) + 400.0
        span_y = abs(water_y1 - water_y0)
        water.set_actor_location(unreal.Vector(mid_x, mid_y, -5.0), False, True)
        water.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
        water.set_actor_scale3d(unreal.Vector(span_x/100.0, span_y/100.0, 1.0))
        log("water horiz-bank @ ({:.0f},{:.0f}) scale=({:.1f},{:.1f})".format(
            mid_x, mid_y, span_x/100.0, span_y/100.0))

# Centroids report
def centroid(pred):
    pts = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if pred(lab):
            loc = a.get_actor_location()
            pts.append((loc.x, loc.y))
    if not pts: return None
    return (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts), len(pts))

h = centroid(lambda l: "FarmShed" in l)
w = centroid(lambda l: l.startswith("VMF_Cliff_") or l == "VMF_Water_Left")
t = centroid(lambda l: "Tree" in l and l.startswith("VMF_"))
s = centroid(lambda l: "Soil" in l or "Crop" in l)
log("house={}".format(h))
log("water/cliff={}".format(w))
log("trees={}".format(t))
log("soil={}".format(s))

# Screen scores with CORRECT yaw-45 mapping: su=(dx-dy), sr=(dx+dy)
center = (1950.0, 2000.0)
def scr(p, name):
    if not p: return
    dx, dy = p[0]-center[0], p[1]-center[1]
    su = (dx - dy) / math.sqrt(2)
    sr = (dx + dy) / math.sqrt(2)
    log("{} screen_up={:.0f} screen_right={:.0f}".format(name, su, sr))
scr(h, "house")
scr(w, "water")
scr(t, "trees")
scr(s, "fields")

try:
    els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    log("save={}".format(els.save_current_level()))
except Exception as e:
    log("save fail " + str(e))
log("DONE")
