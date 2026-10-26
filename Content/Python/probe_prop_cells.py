# -*- coding: utf-8 -*-
"""Probe prop labels and map to grid cells; report current BlockedIndices."""
import unreal
from collections import Counter, defaultdict

TAG = "[PROBE_PROPS]"
CELL = 100.0
WIDTH = 40
HEIGHT = 40

def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()

# Allowed walkable / tillable terrain labels (NOT props)
TERRAIN_KEEP = (
    "VMF_Grass_", "VMF_Path", "VMF_Bridge", "VMF_Water", "VMF_Cliff_", "VMF_Yard_",
    "VMF_Soil_", "VMF_Crop", "AirWall_", "PlotVisual", "BP_", "Player", "Camera",
    "Directional", "Sky", "Fog", "PostProcess", "Light", "Floor", "Template",
    "Default", "WorldSettings", "AbstractNav", "Gameplay", "HUD", "GameMode",
)

prefix_ctr = Counter()
all_labels = []
prop_cells = set()
prop_by_cat = defaultdict(set)
samples = defaultdict(list)

def loc_to_cell(loc):
    gx = int(loc.x // CELL)
    gy = int(loc.y // CELL)
    return gx, gy

def parse_cell(lab):
    parts = (lab or "").split("_")
    try:
        return int(parts[-2]), int(parts[-1])
    except Exception:
        return None

for a in actors:
    lab = a.get_actor_label() or a.get_name() or ""
    cn = a.get_class().get_name()
    loc = a.get_actor_location()
    all_labels.append(lab)

    if lab.startswith("VMF_"):
        bits = lab.split("_")
        pref = bits[1] if len(bits) > 1 else "?"
        # multi-word like GrassClump, DetailPath
        if len(bits) > 2 and bits[1] in ("Grass", "Detail", "Crop"):
            # VMF_Grass_Clump_x_y or VMF_Grass_x_y
            if bits[2] == "Clump" or not bits[2].isdigit():
                pref = bits[1] + "_" + bits[2]
        prefix_ctr[pref] += 1

# Log all VMF prefixes
log("VMF prefixes: " + str(prefix_ctr.most_common(60)))

# Also non-VMF StaticMeshActors
non_vmf_sma = Counter()
for a in actors:
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    if "StaticMesh" in cn and not lab.startswith("VMF_") and not lab.startswith("AirWall_"):
        non_vmf_sma[lab.split("_")[0] if lab else cn] += 1
        if non_vmf_sma[lab.split("_")[0] if lab else cn] <= 3:
            loc = a.get_actor_location()
            log("nonVMF SMA {} class={} @({:.0f},{:.0f},{:.0f})".format(lab, cn, loc.x, loc.y, loc.z))
log("nonVMF SMA tops: " + str(non_vmf_sma.most_common(30)))

# Prop keywords
PROP_KEYS = (
    "Crate", "Chest", "Barrel", "Box", "Cart", "Scarecrow", "Sign", "Fence",
    "Gate", "Post", "Tree", "Bush", "Rock", "Clump", "Pot", "House", "Shed",
    "Barn", "Well", "Pumpkin", "Decoration", "Prop", "Stake", "Pillar", "Rail",
    "Lamp", "Bench", "Table", "Chair", "Flower", "Weed", "Mushroom", "Stump",
    "Log", "Hay", "Sack", "Bag", "Bucket", "Trough", "Anvil", "Tool",
    "DockPost", "PierPost", "Piling", "Pylon", "Wall", "Building",
)

# Explicit terrain that should NOT be treated as prop-block for till
# (path/bridge already blocked; grass alone is tillable)
SKIP_AS_PROP = (
    "VMF_Grass_",  # plain grass tiles — but NOT Grass_Clump
    "VMF_Path", "VMF_Bridge", "VMF_Water", "VMF_Cliff_", "VMF_Yard_",
    "VMF_Soil_", "AirWall_",
)

for a in actors:
    lab = a.get_actor_label() or ""
    loc = a.get_actor_location()
    cn = a.get_class().get_name()

    # Skip plain grass (exact VMF_Grass_X_Y without Clump)
    if lab.startswith("VMF_Grass_") and "Clump" not in lab:
        continue
    if any(lab.startswith(s) for s in ("VMF_Path", "VMF_Bridge", "VMF_Water", "VMF_Cliff_", "VMF_Yard_", "VMF_Soil_", "AirWall_", "PlotVisual")):
        continue
    if "GridManager" in lab or "GridManager" in cn:
        continue
    if lab.startswith("BP_") or "Character" in cn or "Pawn" in cn or "Controller" in cn:
        continue
    if any(x in lab for x in ("DirectionalLight", "SkyAtmosphere", "SkyLight", "ExponentialHeightFog", "PostProcess", "WorldSettings", "AbstractNavData", "DefaultPhysicsVolume", "GameplayDebugger")):
        continue

    is_prop = False
    cat = None
    for k in PROP_KEYS:
        if k.lower() in lab.lower():
            is_prop = True
            cat = k
            break
    # Also any remaining VMF_ that isn't terrain
    if not is_prop and lab.startswith("VMF_"):
        is_prop = True
        bits = lab.split("_")
        cat = bits[1] if len(bits) > 1 else "VMF"
    # StaticMeshActor not otherwise classified
    if not is_prop and "StaticMesh" in cn:
        # Check mesh name
        try:
            sm = a.static_mesh_component.static_mesh
            mn = sm.get_name() if sm else ""
        except Exception:
            mn = ""
        for k in PROP_KEYS:
            if k.lower() in (mn or "").lower() or k.lower() in lab.lower():
                is_prop = True
                cat = k
                break
        if not is_prop and mn and "Ground" not in mn and "Grass" not in mn and "Path" not in mn and "Water" not in mn and "Cliff" not in mn:
            is_prop = True
            cat = "SMA:" + mn[:40]

    if not is_prop:
        continue

    c = parse_cell(lab)
    if c is None:
        c = loc_to_cell(loc)
    gx, gy = c
    if not (0 <= gx < WIDTH and 0 <= gy < HEIGHT):
        continue
    prop_cells.add((gx, gy))
    prop_by_cat[cat].add((gx, gy))
    if len(samples[cat]) < 5:
        samples[cat].append("{}@({},{}) loc=({:.0f},{:.0f},{:.0f})".format(lab, gx, gy, loc.x, loc.y, loc.z))

log("prop cells unique={}".format(len(prop_cells)))
for cat in sorted(prop_by_cat.keys()):
    log("cat {} cells={} samples={}".format(cat, len(prop_by_cat[cat]), samples[cat][:3]))

# Current BlockedIndices
gm = None
for a in actors:
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    if "GridManager" in lab or "GridManager" in cn:
        gm = a
        break
if gm:
    try:
        bi = gm.get_editor_property("BlockedIndices")
        log("GM BlockedIndices len={} head={}".format(len(bi) if bi else 0, list(bi)[:15] if bi else None))
    except Exception as ex:
        log("GM BI: " + str(ex))
else:
    log("NO GM actor")

bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
try:
    cdo = unreal.get_default_object(bp.generated_class())
    bi = cdo.get_editor_property("BlockedIndices")
    log("CDO BlockedIndices len={} head={}".format(len(bi) if bi else 0, list(bi)[:15] if bi else None))
except Exception as ex:
    log("CDO: " + str(ex))

# PlotVisual leftovers
pv = []
for a in actors:
    lab = a.get_actor_label() or ""
    if "PlotVisual" in lab or lab.startswith("PV_"):
        loc = a.get_actor_location()
        c = loc_to_cell(loc)
        pv.append((lab, c))
log("PlotVisual count={} samples={}".format(len(pv), pv[:10]))

# Overlap: prop cells already in blocked?
if gm:
    try:
        bi = list(gm.get_editor_property("BlockedIndices") or [])
        blocked_set = set(bi)
        already = 0
        missing = []
        for gx, gy in sorted(prop_cells):
            flat = gy * WIDTH + gx
            if flat in blocked_set:
                already += 1
            else:
                missing.append((gx, gy, flat))
        log("prop already blocked={} missing={} sample_missing={}".format(already, len(missing), missing[:20]))
    except Exception as ex:
        log("overlap: " + str(ex))

log("DONE")
