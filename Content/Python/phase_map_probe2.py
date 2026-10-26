# -*- coding: utf-8 -*-
"""Probe floor meshes, materials, and spawn Z for farm ground placement."""
import unreal

def log(msg):
    unreal.log("[MAP_PROBE2] " + str(msg))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
for a in actors:
    cls = a.get_class().get_name()
    label = a.get_actor_label()
    loc = a.get_actor_location()
    # floors / static meshes / landscape-ish
    if ("StaticMesh" in cls or "Floor" in label or "Floor" in cls or "Plane" in label
        or "SM_" in label or "Ground" in label or "Cube" in label
        or isinstance(a, unreal.StaticMeshActor)):
        scale = a.get_actor_scale3d()
        log("MESH {} label={} loc=({:.1f},{:.1f},{:.1f}) scale=({:.3f},{:.3f},{:.3f}) class={}".format(
            a.get_name(), label, loc.x, loc.y, loc.z, scale.x, scale.y, scale.z, cls))
        try:
            smc = a.static_mesh_component
            mesh = smc.get_editor_property("static_mesh")
            log("  mesh=" + str(mesh))
            mats = smc.get_materials()
            for i, m in enumerate(mats):
                log("  mat[{}]={}".format(i, m))
        except Exception as e:
            log("  smc err " + str(e))

# PlayerStart + Grid again
for a in actors:
    label = a.get_actor_label()
    if "PlayerStart" in label or "GridManager" in label:
        loc = a.get_actor_location()
        log("KEY {} loc=({:.1f},{:.1f},{:.1f})".format(label, loc.x, loc.y, loc.z))

# Engine materials / meshes availability
for path in [
    "/Engine/BasicShapes/Plane",
    "/Engine/BasicShapes/Cube",
    "/Engine/BasicShapes/BasicShapeMaterial",
    "/Engine/EngineMaterials/DefaultMaterial",
    "/Engine/EngineMaterials/Widget3DPassThrough",
]:
    exists = unreal.EditorAssetLibrary.does_asset_exist(path)
    log("ASSET {} exists={}".format(path, exists))

# CDO via generated class properly
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
try:
    gen = bp.generated_class()
    log("generated_class=" + str(gen))
    cdo = unreal.get_default_object(gen)
    log("CDO=" + str(cdo))
    for name in ["cell_size", "grid_width", "grid_height", "grid_origin", "CellSize", "GridWidth", "GridHeight", "GridOrigin"]:
        try:
            v = cdo.get_editor_property(name)
            log("CDO.{}={}".format(name, v))
        except Exception as e:
            pass
except Exception as e:
    log("CDO err " + str(e))

log("DONE")
