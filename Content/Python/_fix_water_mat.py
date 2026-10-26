# -*- coding: utf-8 -*-
"""Reimport T_Water and rebuild M_Water with cell-matched tiling; keep planes flat."""
import unreal
import os

def log(m):
    unreal.log("[WATER] " + str(m))

TEX = "/Game/Farm/Art/T_Water"
MAT = "/Game/Farm/Art/Mats/M_Water"
DISK = r"E:\UE\FarmSim25D\Content\Farm\Art\Tiles\T_Water.png"

# Reimport texture
if unreal.EditorAssetLibrary.does_asset_exist(TEX):
    try:
        unreal.EditorAssetLibrary.delete_asset(TEX)
    except Exception as e:
        log("del tex " + str(e))
task = unreal.AssetImportTask()
task.filename = DISK
task.destination_path = "/Game/Farm/Art"
task.destination_name = "T_Water"
task.replace_existing = True
task.automated = True
task.save = True
try:
    task.factory = unreal.TextureFactory()
except Exception:
    pass
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
tex = unreal.EditorAssetLibrary.load_asset(TEX)
if not tex:
    log("IMPORT FAIL")
else:
    try:
        tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
        tex.set_editor_property("compression_no_alpha", False)
    except Exception as e:
        log("tex props " + str(e))
    unreal.EditorAssetLibrary.save_asset(TEX)
    log("tex OK")

# Recreate M_Water opaque unlit, tiling=1 (scale-driven look via world; plane UV 0-1)
# For tilemap: set tiling high enough that waves aren't huge. Use 1.0 and rely on
# per-cell feel by setting Water actor materials with tessellation... simplest: tiling=4
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
path = MAT
if unreal.EditorAssetLibrary.does_asset_exist(path):
    try:
        unreal.EditorAssetLibrary.delete_asset(path)
    except Exception as e:
        log("del mat " + str(e))
factory = unreal.MaterialFactoryNew()
mat = tools.create_asset("M_Water", "/Game/Farm/Art/Mats", unreal.Material, factory)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
mat.set_editor_property("two_sided", True)
try:
    mel.delete_all_material_expressions(mat)
except Exception:
    pass
tex_coord = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -600, 0)
# Moderate tiling so water reads as pond fill not giant stamp, not crazy icons
tex_coord.set_editor_property("u_tiling", 6.0)
tex_coord.set_editor_property("v_tiling", 6.0)
tex_sample = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -350, 0)
tex_sample.set_editor_property("texture", tex)
mel.connect_material_expressions(tex_coord, "", tex_sample, "UVs")
mel.connect_material_property(tex_sample, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.recompile_material(mat)
unreal.EditorAssetLibrary.save_asset(path)
log("mat OK tiling=6")

# Re-assign to water planes
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mat = unreal.EditorAssetLibrary.load_asset(path)
for lab in ("Scene_Water_Left", "Scene_Water_Bottom", "Scene_Pond_NE"):
    for a in eas.get_all_level_actors():
        if a.get_actor_label() != lab:
            continue
        a.static_mesh_component.set_material(0, mat)
        a.set_actor_rotation(unreal.Rotator(), False)
        log("assigned %s rot flat" % lab)

try:
    ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("save " + str(ok))
except Exception as e:
    log("save " + str(e))
log("DONE")