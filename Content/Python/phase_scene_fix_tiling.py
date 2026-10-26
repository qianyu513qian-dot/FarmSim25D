# -*- coding: utf-8 -*-
"""Fix UV tiling on large Scene ground planes so dirt/water/tilled/terrace tile per-cell."""
import unreal

ART = "/Game/Farm/Art"
MATS = ART + "/Mats"
TEX_DIR = ART
PLANE = "/Engine/BasicShapes/Plane"

def log(msg):
    unreal.log("[SCENE_FIX] " + str(msg))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def find_by_label(label):
    for a in eas().get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None

def create_tiled_mat(mat_name, tex_name, u_tile, v_tile, masked=False):
    mel = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    path = MATS + "/" + mat_name
    tex = unreal.EditorAssetLibrary.load_asset(TEX_DIR + "/" + tex_name)
    if not tex:
        log("no tex " + tex_name)
        return None
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        try:
            unreal.EditorAssetLibrary.delete_asset(path)
        except Exception:
            pass
    mat = tools.create_asset(mat_name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    if not mat:
        return None
    try:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property(
            "blend_mode",
            unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE,
        )
        mat.set_editor_property("two_sided", True)
    except Exception:
        pass
    try:
        mel.delete_all_material_expressions(mat)
    except Exception:
        pass
    tc = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -600, 0)
    try:
        tc.set_editor_property("u_tiling", float(u_tile))
        tc.set_editor_property("v_tiling", float(v_tile))
    except Exception:
        pass
    ts = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -350, 0)
    try:
        ts.set_editor_property("texture", tex)
    except Exception:
        ts.texture = tex
    mel.connect_material_expressions(tc, "", ts, "UVs")
    mel.connect_material_property(ts, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if masked:
        mel.connect_material_property(ts, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    try:
        mel.recompile_material(mat)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(path)
    log("mat {} u={} v={}".format(mat_name, u_tile, v_tile))
    return mat

def apply(label, mat):
    a = find_by_label(label)
    if not a or not mat:
        log("skip " + label)
        return
    a.static_mesh_component.set_material(0, mat)
    log("applied " + label)

def main():
    # Ground overlays: tiling = plane scale in cells
    specs = [
        ("Scene_Water_Left", "M_Water_Left", "T_Water", 3, 28, False),
        ("Scene_Water_Bottom", "M_Water_Bottom", "T_Water", 25, 3, False),
        ("Scene_Pond_NE", "M_Water_Pond", "T_Water", 3, 3, False),
        ("Scene_Path_V", "M_Dirt_PathV", "T_Dirt", 2, 17, False),
        ("Scene_Path_H", "M_Dirt_PathH", "T_Dirt", 9, 2, False),
        ("Scene_Tilled", "M_Tilled_Patch", "T_Tilled", 7, 9, False),
        ("Scene_Terrace", "M_Terrace_Pad", "T_TerraceTop", 9, 7, False),
        ("Scene_Cliff_S", "M_Cliff_S", "T_CliffS", 9, 1, False),
        ("Scene_Fence_N", "M_Fence_N", "T_FenceH", 9, 1, True),
        ("Scene_Fence_W", "M_Fence_W", "T_FenceDetail", 1, 6, True),
        ("Scene_Fence_E", "M_Fence_E", "T_FenceDetail", 1, 6, True),
    ]
    for label, mname, tname, u, v, masked in specs:
        mat = create_tiled_mat(mname, tname, u, v, masked)
        apply(label, mat)

    # Verify grid
    gm = find_by_label("BP_GridManager")
    if gm:
        log("Grid {}x{} cell={}".format(
            gm.get_editor_property("GridWidth"),
            gm.get_editor_property("GridHeight"),
            gm.get_editor_property("CellSize")))
    fg = find_by_label("FarmGround")
    if fg:
        log("FarmGround scale={}".format(fg.get_actor_scale3d()))
    ps = find_by_label("PlayerStart")
    if ps:
        log("PlayerStart={}".format(ps.get_actor_location()))

    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        log("save -> {}".format(els.save_current_level()))
    except Exception as e:
        log("save fail " + str(e))
    log("=== DONE FIX ===")

main()