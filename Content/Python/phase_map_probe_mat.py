# -*- coding: utf-8 -*-
"""Probe material params for brown dirt MI."""
import unreal

def log(m):
    unreal.log("[MAP_MAT] " + str(m))

for path in [
    "/Engine/BasicShapes/BasicShapeMaterial",
    "/Game/LevelPrototyping/Materials/MI_PrototypeGrid_Gray",
    "/Game/TopDown/MI_Colorway",
    "/Game/LevelPrototyping/Materials/M_PrototypeGrid",
]:
    a = unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    log("{} -> {}".format(path, a))
    if a is None:
        continue
    try:
        if isinstance(a, unreal.MaterialInstanceConstant) or a.__class__.__name__.find("MaterialInstance") >= 0:
            # list scalar/vector params via MaterialEditingLibrary
            mel = unreal.MaterialEditingLibrary
            try:
                # get base property overrides / set vector
                log("  is MIC")
            except Exception as e:
                log("  " + str(e))
            # try common param names
            for pname in ["Color", "BaseColor", "Base Color", "Tint", "DiffuseColor", "Roughness"]:
                try:
                    # vector
                    v = mel.get_material_instance_vector_parameter_value(a, pname)
                    log("  vec {}={}".format(pname, v))
                except Exception as e:
                    pass
                try:
                    s = mel.get_material_instance_scalar_parameter_value(a, pname)
                    log("  scl {}={}".format(pname, s))
                except Exception:
                    pass
            try:
                parent = a.get_editor_property("parent")
                log("  parent=" + str(parent))
            except Exception as e:
                log("  parent err " + str(e))
        elif isinstance(a, unreal.Material):
            log("  is Material")
    except Exception as e:
        log("err " + str(e))

# List Farm folder
assets = unreal.EditorAssetLibrary.list_assets("/Game/Farm", recursive=True)
log("Farm assets: " + str(assets))

# Plane mesh bounds
plane = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
log("Plane=" + str(plane))
try:
    box = plane.get_bounding_box()
    log("Plane bbox=" + str(box))
except Exception as e:
    log("bbox " + str(e))
try:
    # SM_Cube size
    cube = unreal.EditorAssetLibrary.load_asset("/Game/LevelPrototyping/Meshes/SM_Cube")
    log("SM_Cube=" + str(cube))
except Exception as e:
    log(str(e))

log("DONE")
