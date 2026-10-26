# -*- coding: utf-8 -*-
"""Probe VMF layout centroids for house/water/trees/path vs camera yaw-45."""
import unreal
import math

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def log(m):
    unreal.log("[LAYOUT] " + str(m))

cats = {
    "house": [],
    "water": [],
    "tree": [],
    "path": [],
    "soil": [],
    "fence": [],
    "grass": [],
    "bridge": [],
    "other": [],
    "floor": [],
    "player": [],
}

def classify(lab):
    l = lab.lower()
    if "playerstart" in l or lab == "PlayerStart":
        return "player"
    if "farmcollision" in l or lab == "FarmCollisionFloor":
        return "floor"
    if not lab.startswith("VMF_") and not lab.startswith("Scene_"):
        return None
    if any(k in lab for k in ("FarmShed", "House", "ToolShelter", "ChickenCoop", "Well")):
        return "house"
    if any(k in lab for k in ("Water", "Pond", "Lake", "Cliff", "Bank")):
        return "water"
    if any(k in lab for k in ("Tree", "Bush", "Forest", "Shrub", "Nature_Tree")):
        return "tree"
    if any(k in lab for k in ("Path", "Road", "Bridge", "Pier", "Deck")):
        if "Bridge" in lab or "Pier" in lab or "Deck" in lab:
            return "bridge"
        return "path"
    if any(k in lab for k in ("Soil", "Crop", "Bed", "Hoe", "Scarecrow")):
        return "soil"
    if "Fence" in lab or "Gate" in lab or "Yard" in lab:
        return "fence"
    if "Grass" in lab or "Ground" in lab:
        return "grass"
    return "other"

counts = {k: 0 for k in cats}
xs_all, ys_all = [], []
samples = {k: [] for k in cats}

for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    cat = classify(lab)
    if cat is None:
        continue
    loc = a.get_actor_location()
    cats[cat].append((lab, loc.x, loc.y, loc.z))
    counts[cat] += 1
    if cat not in ("player", "floor"):
        xs_all.append(loc.x)
        ys_all.append(loc.y)
    if len(samples[cat]) < 5:
        samples[cat].append((lab, round(loc.x), round(loc.y), round(loc.z)))

def centroid(items):
    if not items:
        return None
    cx = sum(t[1] for t in items) / len(items)
    cy = sum(t[2] for t in items) / len(items)
    cz = sum(t[3] for t in items) / len(items)
    return (cx, cy, cz)

log("counts=" + str(counts))
if xs_all:
    log("AABB x=[{:.0f},{:.0f}] y=[{:.0f},{:.0f}] center=({:.0f},{:.0f})".format(
        min(xs_all), max(xs_all), min(ys_all), max(ys_all),
        (min(xs_all)+max(xs_all))/2, (min(ys_all)+max(ys_all))/2))

for k in ("house", "water", "tree", "path", "soil", "fence", "bridge", "grass", "player", "floor"):
    c = centroid(cats[k])
    if c:
        log("{} n={} centroid=({:.0f},{:.0f},{:.0f})".format(k, len(cats[k]), c[0], c[1], c[2]))
    else:
        log("{} n=0".format(k))
    for s in samples[k]:
        log("  sample {} @ ({},{},{})".format(s[0], s[1], s[2], s[3]))

# GridManager / SpringArm
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "BP_GridManager":
        log("Grid W={} H={} Cell={} Origin={}".format(
            a.get_editor_property("GridWidth"),
            a.get_editor_property("GridHeight"),
            a.get_editor_property("CellSize"),
            a.get_editor_property("GridOrigin")))

# Camera from BP
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cn = obj.get_class().get_name()
    if "SpringArm" in cn:
        try:
            r = obj.get_editor_property("relative_rotation")
            log("SpringArm pitch={:.1f} yaw={:.1f} roll={:.1f} arm={}".format(
                r.pitch, r.yaw, r.roll, obj.get_editor_property("target_arm_length")))
        except Exception as e:
            log("SpringArm err " + str(e))

# With yaw=-45: screen-up world dir approx (-1, +1) or need check
# House should be "top" = higher along screen-up = more -X+Y
# Report house vs trees relative to farm center
hc = centroid(cats["house"])
tc = centroid(cats["tree"])
wc = centroid(cats["water"])
center = ((min(xs_all)+max(xs_all))/2, (min(ys_all)+max(ys_all))/2) if xs_all else (2000, 2000)
log("farm_center=({:.0f},{:.0f})".format(center[0], center[1]))
if hc:
    # screen-up for yaw-45 camera looking from (+X,-Y): screen up ~ (-X,+Y)
    su_h = (-(hc[0]-center[0]) + (hc[1]-center[1])) / math.sqrt(2)
    sr_h = ( (hc[0]-center[0]) + (hc[1]-center[1])) / math.sqrt(2)
    log("house screen_up={:.0f} screen_right={:.0f} (yaw-45 approx)".format(su_h, sr_h))
if tc:
    su_t = (-(tc[0]-center[0]) + (tc[1]-center[1])) / math.sqrt(2)
    sr_t = ( (tc[0]-center[0]) + (tc[1]-center[1])) / math.sqrt(2)
    log("tree  screen_up={:.0f} screen_right={:.0f}".format(su_t, sr_t))
if wc:
    su_w = (-(wc[0]-center[0]) + (wc[1]-center[1])) / math.sqrt(2)
    sr_w = ( (wc[0]-center[0]) + (wc[1]-center[1])) / math.sqrt(2)
    log("water screen_up={:.0f} screen_right={:.0f}".format(su_w, sr_w))

log("DONE")
