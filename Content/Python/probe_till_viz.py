# -*- coding: utf-8 -*-
"""Probe TillCell/VisualizeCell graphs and near-spawn blockers."""
import unreal

def log(m):
    unreal.log("[PROBE2] " + str(m))
    print("[PROBE2] " + str(m))

GM = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
CELL = 100.0

def dump_fns(path):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    if not bp:
        log("missing " + path)
        return
    try:
        bel = unreal.BlueprintEditorLibrary
        names = []
        for n in bel.get_blueprint_function_names(bp) if hasattr(bel, "get_blueprint_function_names") else []:
            names.append(str(n))
        log(path + " fns=" + str(names))
    except Exception as e:
        log("fns err " + str(e))
    # ubergraph / graphs via asset
    try:
        for g in bp.get_editor_property("function_graphs"):
            log("  graph " + str(g.get_name()))
    except Exception as e:
        log("graphs " + str(e))
    try:
        ug = bp.get_editor_property("ubergraph_pages")
        for g in ug:
            log("  uber " + str(g.get_name()))
    except Exception:
        pass

dump_fns(GM)
dump_fns(CHAR)

# Look for VisualizeCell nodes in GridManager via find
bp = unreal.EditorAssetLibrary.load_asset(GM)
try:
    from unreal import BlueprintEditorLibrary as BEL
except Exception:
    BEL = None

# Actor labels near spawn + soil dry assets
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
near = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    loc = a.get_actor_location()
    if not lab.startswith("VMF_"):
        continue
    gx, gy = int(loc.x // CELL), int(loc.y // CELL)
    if 19 <= gx <= 25 and 14 <= gy <= 20:
        near.append((lab, gx, gy, round(loc.z)))
log("near spawn VMF: " + str(sorted(near, key=lambda t: (t[2], t[1]))))

for p in [
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Untilled",
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Tilled",
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Wet",
]:
    log("asset {} exists={}".format(p, unreal.EditorAssetLibrary.does_asset_exist(p)))

# list terrain meshes
try:
    assets = unreal.EditorAssetLibrary.list_assets("/Game/Farm/VoxelMicroFarm/Models/Terrain", True, False)
    soils = [a for a in assets if "Soil" in a or "soil" in a]
    log("soils: " + str(soils))
except Exception as e:
    log("list " + str(e))

# CDO defaults PlotStates?
try:
    gm_bp = unreal.EditorAssetLibrary.load_asset(GM)
    cdo = unreal.get_default_object(gm_bp.generated_class())
    for p in ("GridWidth", "GridHeight", "CellSize", "GridOrigin", "PlotStates", "plot_states"):
        try:
            log("CDO {}={}".format(p, cdo.get_editor_property(p)))
        except Exception as e:
            log("CDO {} fail {}".format(p, e))
except Exception as e:
    log("cdo " + str(e))

log("DONE")
