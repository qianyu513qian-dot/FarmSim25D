# -*- coding: utf-8 -*-
import unreal
from collections import Counter

TAG = "[PROBE_ZONES]"
def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()

prefix_ctr = Counter()
cat = Counter()
samples = {k: [] for k in ("Soil","Hoe","Path","Water","Grass","Cliff","Bridge","Dock","Harbor","Pier","Crop","Tomato","Corn","Pumpkin","Yard","Deck","AirWall","FarmCollision")}

soil_actors = []
path_actors = []
water_actors = []
grass_by_cell = {}
crop_actors = []

def cell_from_lab(lab):
    # VMF_Soil_12_20 or VMF_Grass_12_20
    parts = lab.split("_")
    try:
        return int(parts[-2]), int(parts[-1])
    except Exception:
        return None

for a in actors:
    lab = a.get_actor_label() or a.get_name()
    if lab.startswith("VMF_"):
        bits = lab.split("_")
        pref = bits[1] if len(bits) > 1 else lab
        prefix_ctr[pref] += 1
    low = lab.lower()
    loc = a.get_actor_location()
    for k in samples:
        if k.lower() in low:
            cat[k] += 1
            if len(samples[k]) < 8:
                samples[k].append("{}@({:.0f},{:.0f},{:.0f})".format(lab, loc.x, loc.y, loc.z))
    if lab.startswith("VMF_Soil_") or ("Soil" in lab and lab.startswith("VMF_")):
        soil_actors.append((lab, loc.x, loc.y, loc.z, cell_from_lab(lab)))
    if lab.startswith("VMF_Path") or lab.startswith("VMF_DetailPath") or ("Path" in lab and lab.startswith("VMF_")):
        path_actors.append((lab, loc.x, loc.y, loc.z, cell_from_lab(lab)))
    if "Water" in lab or lab.startswith("VMF_Water"):
        water_actors.append((lab, loc.x, loc.y, loc.z))
        try:
            o, e = a.get_actor_bounds(False)
            samples.setdefault("WaterBounds", [])
            if len(samples.get("WaterBounds", [])) < 5:
                samples.setdefault("WaterBounds", []).append("{} o=({:.0f},{:.0f},{:.0f}) e=({:.0f},{:.0f},{:.0f})".format(lab, o.x,o.y,o.z, e.x,e.y,e.z))
        except Exception as ex:
            pass
    if lab.startswith("VMF_Grass_") and "Clump" not in lab:
        c = cell_from_lab(lab)
        if c:
            grass_by_cell[c] = lab
    if any(x in lab for x in ("Tomato","Corn","Pumpkin","Crop")) and lab.startswith("VMF_"):
        crop_actors.append((lab, loc.x, loc.y, loc.z, cell_from_lab(lab)))
    if lab.startswith("VMF_Bridge") or lab.startswith("VMF_Pier") or lab.startswith("VMF_Deck") or "Bridge" in lab:
        cat["BridgeLike"] = cat.get("BridgeLike", 0) + 1
    if "Yard" in lab and lab.startswith("VMF_"):
        cat["Yard"] += 1

log("prefix top: " + str(prefix_ctr.most_common(30)))
log("cats: " + str(dict(cat)))
for k,v in samples.items():
    if v:
        log("sample {}: {}".format(k, v))

log("soil count={} samples={}".format(len(soil_actors), soil_actors[:15]))
log("path count={} samples={}".format(len(path_actors), path_actors[:10]))
log("water count={} samples={}".format(len(water_actors), water_actors[:10]))
log("crop count={} samples={}".format(len(crop_actors), crop_actors[:15]))
log("grass cells={}".format(len(grass_by_cell)))

# soil cells missing grass?
missing_grass = []
for lab,x,y,z,c in soil_actors:
    if c and c not in grass_by_cell:
        missing_grass.append(c)
log("soil cells missing grass: n={} {}".format(len(missing_grass), missing_grass[:20]))

# E_PlotState enum
enum = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/E_PlotState")
log("enum type={} asset={}".format(type(enum).__name__, enum))
try:
    # UserDefinedEnum
    names = unreal.UserDefinedEnum.static_class()
    ude = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/E_PlotState")
    # try get enums
    if hasattr(ude, "get_editor_property"):
        for prop in ("Names", "DisplayNameMap", "Enums"):
            try:
                log("enum.{}={}".format(prop, ude.get_editor_property(prop)))
            except Exception as ex:
                pass
    # Enum entries via unreal
    try:
        entries = unreal.DataTableFunctionLibrary  # noop
    except: pass
except Exception as ex:
    log("enum err " + str(ex))

# Try list enum via asset registry / object
try:
    obj = unreal.load_object(None, "/Game/Farm/Grid/E_PlotState.E_PlotState")
    log("obj={}".format(obj))
    # UserDefinedEnum has GetDisplayNameTextByIndex
    for i in range(16):
        try:
            n = unreal.EnumBase  # 
        except: pass
except Exception as ex:
    log("load_object " + str(ex))

# GridManager
gm = None
for a in actors:
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    if "GridManager" in lab or "GridManager" in cn:
        gm = a
        log("GM actor={} class={} loc={}".format(lab, cn, a.get_actor_location()))
        for pname in ("CellSize","GridWidth","GridHeight","GridOrigin","PlotStates"):
            try:
                v = a.get_editor_property(pname)
                if pname == "PlotStates":
                    log("PlotStates len={} sample={}".format(len(v) if v else 0, list(v)[:8] if v else None))
                else:
                    log("{}={}".format(pname, v))
            except Exception as ex:
                log("{} err {}".format(pname, ex))

# BP_GridManager functions
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
log("BP_GridManager={}".format(bp))
try:
    cdo = unreal.get_default_object(bp.generated_class()) if hasattr(bp, "generated_class") else None
    log("CDO={}".format(cdo))
except Exception as ex:
    log("cdo " + str(ex))

# Bridge/Pier/Dock labels
for a in actors:
    lab = a.get_actor_label() or ""
    if any(x in lab for x in ("Bridge","Pier","Dock","Harbor","Deck","Port","Boat")):
        loc = a.get_actor_location()
        log("dockish {} ({:.0f},{:.0f},{:.0f})".format(lab, loc.x, loc.y, loc.z))

log("DONE")
