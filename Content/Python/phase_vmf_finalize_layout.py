# -*- coding: utf-8 -*-
"""Nudge PlayerStart onto central path near fields; verify final composition."""
import unreal
import math

def log(m):
    unreal.log("[FINAL] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CELL = 100.0

# Find a path tile near fields (soil centroid ~987,1595)
path_pts = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("VMF_Path"):
        loc = a.get_actor_location()
        path_pts.append((loc.x, loc.y, lab))

soil_pts = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if "Soil" in lab or "Hoe" in lab or lab.startswith("VMF_Crop"):
        loc = a.get_actor_location()
        soil_pts.append((loc.x, loc.y))

if soil_pts:
    scx = sum(p[0] for p in soil_pts)/len(soil_pts)
    scy = sum(p[1] for p in soil_pts)/len(soil_pts)
    log("fields centroid ({:.0f},{:.0f}) n={}".format(scx, scy, len(soil_pts)))
else:
    scx, scy = 1200.0, 1800.0

# Pick path point closest to fields but slightly toward map center
best = None
best_d = 1e18
for x, y, lab in path_pts:
    # prefer near fields
    d = (x-scx)**2 + (y-scy)**2
    # slight bias toward open grass (away from water x<800)
    if x < 900:
        d += 200000
    if d < best_d:
        best_d = d
        best = (x, y, lab)
log("best path near fields: {} @ ({:.0f},{:.0f})".format(best[2], best[0], best[1]))

ps = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "PlayerStart":
        ps = a
        break
if ps and best:
    # Stand on path cell center, Z=100; face toward fields
    px, py = best[0], best[1]
    # offset one cell toward fields if possible
    fx = scx - px
    fy = scy - py
    # keep on path; just use path center
    ps.set_actor_location(unreal.Vector(px, py, 100.0), False, True)
    yaw = math.degrees(math.atan2(fy, fx)) if (fx or fy) else 0.0
    ps.set_actor_rotation(unreal.Rotator(0.0, yaw, 0.0), False)
    log("PlayerStart -> ({:.0f},{:.0f},100) yaw={:.0f} Grid≈({},{})".format(
        px, py, yaw, int(px//CELL), int(py//CELL)))

# Hide FarmGround again
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if "FarmGround" in lab:
        a.set_actor_hidden_in_game(True)
        a.set_is_temporarily_hidden_in_editor(True)
        a.set_actor_location(unreal.Vector(-50000,-50000,-1000), False, True)
        log("hid "+lab)

# Camera still good?
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    obj = lib.get_object_for_blueprint(lib.get_data(h), bp)
    if obj and "SpringArm" in obj.get_class().get_name():
        r = obj.get_editor_property("relative_rotation")
        log("SpringArm p={:.0f} y={:.0f} arm={}".format(
            r.pitch, r.yaw, obj.get_editor_property("target_arm_length")))

# Counts
vmf = sum(1 for a in eas.get_all_level_actors() if a.get_actor_label().startswith("VMF_"))
log("VMF_* count={}".format(vmf))

# Screen composition summary
center = (1950.0, 2000.0)
def report(name, pred):
    pts = []
    for a in eas.get_all_level_actors():
        if pred(a.get_actor_label()):
            loc = a.get_actor_location()
            pts.append((loc.x, loc.y))
    if not pts:
        log(name+" none")
        return
    cx = sum(p[0] for p in pts)/len(pts)
    cy = sum(p[1] for p in pts)/len(pts)
    dx, dy = cx-center[0], cy-center[1]
    su = (dx - dy) / math.sqrt(2)
    sr = (dx + dy) / math.sqrt(2)
    side_v = "top" if su > 400 else ("bottom" if su < -400 else "mid")
    side_h = "right" if sr > 400 else ("left" if sr < -400 else "center")
    log("{} world=({:.0f},{:.0f}) n={} screen≈{}/{}".format(
        name, cx, cy, len(pts), side_v, side_h))

report("house", lambda l: "FarmShed" in l or "Well" in l)
report("water", lambda l: l.startswith("VMF_Cliff_") or l=="VMF_Water_Left")
report("trees", lambda l: l.startswith("VMF_") and "Tree" in l)
report("fields", lambda l: "Soil" in l or "Crop" in l)
report("path", lambda l: l.startswith("VMF_Path"))
report("bridge", lambda l: "Bridge" in l or "Pier" in l)

els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("save={}".format(els.save_current_level()))
log("DONE")
