# -*- coding: utf-8 -*-
"""Import VoxelMicroFarm FBX + palette textures into /Game/Farm/VoxelMicroFarm.
Creates simple unlit materials from palette PNGs. No Blueprint edits.
"""
import unreal
import os

CONTENT_ROOT = r"E:\UE\FarmSim25D\Content\Farm\VoxelMicroFarm"
GAME_ROOT = "/Game/Farm/VoxelMicroFarm"
DISK_TEX = os.path.join(CONTENT_ROOT, "Textures")
DISK_MODELS = os.path.join(CONTENT_ROOT, "Models")

# Texture basename -> material name
PALETTE_MAP = {
    "T_VMF_Palette": "M_VMF_Palette",
    "T_VMF_Expansion01_Detail": "M_VMF_Expansion01",
    "T_VMF_Expansion02_Palette": "M_VMF_Expansion02",
    "T_VMF_Expansion02_Facilities_Palette": "M_VMF_Expansion02_Facilities",
    "T_VMF_Expansion02_Nature_Palette": "M_VMF_Expansion02_Nature",
    "T_VMF_GroundStudy_Palette": "M_VMF_GroundStudy",
    "T_VMF_ArtRefine_LegacyBase": "M_VMF_ArtRefine_LegacyBase",
    "T_VMF_ArtRefine_LegacyProps": "M_VMF_ArtRefine_LegacyProps",
}

# Heuristic: which mat to apply to which mesh folder prefix
FOLDER_MAT = {
    "Terrain": "M_VMF_Palette",
    "Crops": "M_VMF_Palette",
    "Harvest": "M_VMF_Palette",
    "Tools": "M_VMF_Palette",
    "Props": "M_VMF_Palette",
    "Fences": "M_VMF_Palette",
    "Nature": "M_VMF_Palette",  # base Nature
    "Details": "M_VMF_Palette",
    "Demo": "M_VMF_Palette",
    "Expansion01": "M_VMF_Expansion01",
    "GroundStudy": "M_VMF_GroundStudy",
    "Buildings": "M_VMF_Expansion02",
    "Facilities": "M_VMF_Expansion02_Facilities",
    "Storage": "M_VMF_Expansion02",
}


def log(msg):
    unreal.log("[VMF_IMPORT] " + str(msg))


def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)
        log("mkdir " + path)


def rel_game_path(disk_path):
    """E:\\...\\VoxelMicroFarm\\Models\\Terrain\\x.fbx -> /Game/Farm/VoxelMicroFarm/Models/Terrain"""
    rel = os.path.relpath(disk_path, CONTENT_ROOT)
    folder = os.path.dirname(rel).replace("\\", "/")
    if folder in (".", ""):
        return GAME_ROOT
    return GAME_ROOT + "/" + folder


def import_texture(disk_png):
    name = os.path.splitext(os.path.basename(disk_png))[0]
    dest_folder = rel_game_path(disk_png)
    ensure_dir(dest_folder)
    dest = dest_folder + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(dest):
        try:
            unreal.EditorAssetLibrary.delete_asset(dest)
        except Exception:
            pass
    task = unreal.AssetImportTask()
    task.filename = disk_png
    task.destination_path = dest_folder
    task.destination_name = name
    task.replace_existing = True
    task.automated = True
    task.save = True
    try:
        task.factory = unreal.TextureFactory()
    except Exception:
        pass
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = unreal.EditorAssetLibrary.load_asset(dest)
    if not tex:
        log("TEX FAIL " + disk_png)
        return None
    try:
        tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
    except Exception:
        pass
    try:
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    except Exception:
        pass
    try:
        tex.set_editor_property(
            "compression_settings",
            unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,
        )
    except Exception:
        pass
    try:
        tex.set_editor_property("srgb", True)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(dest)
    log("tex OK " + dest)
    return tex


def create_unlit_material(mat_folder, mat_name, texture):
    ensure_dir(mat_folder)
    path = mat_folder + "/" + mat_name
    mel = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        try:
            unreal.EditorAssetLibrary.delete_asset(path)
        except Exception:
            pass
    factory = unreal.MaterialFactoryNew()
    mat = tools.create_asset(mat_name, mat_folder, unreal.Material, factory)
    if not mat:
        log("MAT FAIL " + mat_name)
        return None
    try:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    except Exception:
        pass
    try:
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    except Exception:
        pass
    try:
        mel.delete_all_material_expressions(mat)
    except Exception:
        pass
    tex_sample = mel.create_material_expression(
        mat, unreal.MaterialExpressionTextureSample, -350, 0
    )
    try:
        tex_sample.set_editor_property("texture", texture)
    except Exception:
        try:
            tex_sample.texture = texture
        except Exception as e:
            log("set tex: " + str(e))
    mel.connect_material_property(
        tex_sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
    )
    try:
        mel.recompile_material(mat)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(path)
    log("mat OK " + path)
    return mat


def import_fbx(disk_fbx):
    name = os.path.splitext(os.path.basename(disk_fbx))[0]
    dest_folder = rel_game_path(disk_fbx)
    ensure_dir(dest_folder)
    dest = dest_folder + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(dest):
        try:
            unreal.EditorAssetLibrary.delete_asset(dest)
        except Exception:
            pass
    task = unreal.AssetImportTask()
    task.filename = disk_fbx
    task.destination_path = dest_folder
    task.destination_name = name
    task.replace_existing = True
    task.automated = True
    task.save = True
    # FBX options
    try:
        options = unreal.FbxImportUI()
        options.set_editor_property("automated_import_should_detect_type", False)
        options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        options.set_editor_property("original_import_type", unreal.FBXImportType.FBXIT_STATIC_MESH)
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("import_materials", False)
        options.set_editor_property("import_textures", False)
        options.set_editor_property("import_animations", False)
        options.set_editor_property("create_physics_asset", False)
        sm = options.get_editor_property("static_mesh_import_data")
        try:
            sm.set_editor_property("combine_meshes", True)
        except Exception:
            pass
        try:
            sm.set_editor_property("auto_generate_collision", True)
        except Exception:
            pass
        try:
            # Unity cm -> UE cm usually fine; convert scene off, force front X
            sm.set_editor_property("convert_scene", True)
            sm.set_editor_property("force_front_x_axis", False)
            sm.set_editor_property("convert_scene_unit", True)
        except Exception:
            pass
        try:
            sm.set_editor_property("import_uniform_scale", 100.0)  # Unity meters -> UE cm
        except Exception:
            pass
        task.options = options
    except Exception as e:
        log("fbx options warn: " + str(e))
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.EditorAssetLibrary.load_asset(dest)
    if not mesh:
        # sometimes FBX creates slightly different name
        assets = unreal.EditorAssetLibrary.list_assets(dest_folder, recursive=False)
        for a in assets:
            if name in a:
                mesh = unreal.EditorAssetLibrary.load_asset(a)
                dest = a
                break
    if not mesh:
        log("FBX FAIL " + disk_fbx)
        return None
    log("fbx OK " + dest)
    return mesh, dest


def pick_mat_for_path(disk_fbx, mats):
    # Expansion02 Nature BEFORE folder walk ("Nature" alone maps to base palette)
    if "Expansion02" in disk_fbx and "Nature" in disk_fbx:
        return mats.get("M_VMF_Expansion02_Nature")
    if "Expansion02" in disk_fbx and "Facilities" in disk_fbx:
        return mats.get("M_VMF_Expansion02_Facilities")
    if "GroundStudy" in disk_fbx:
        return mats.get("M_VMF_GroundStudy")
    if "Expansion02" in disk_fbx:
        return mats.get("M_VMF_Expansion02")
    if "Expansion01" in disk_fbx:
        return mats.get("M_VMF_Expansion01")
    parts = disk_fbx.replace("\\", "/").split("/")
    # walk from leaf folder up
    for part in reversed(parts):
        if part in FOLDER_MAT:
            mname = FOLDER_MAT[part]
            if mname in mats:
                return mats[mname]
    # Expansion02 crops etc. (kept for safety; primary checks above)
    if "Expansion02" in disk_fbx and "Nature" in disk_fbx:
        return mats.get("M_VMF_Expansion02_Nature")
    if "Expansion02" in disk_fbx and "Facilities" in disk_fbx:
        return mats.get("M_VMF_Expansion02_Facilities")
    if "Expansion02" in disk_fbx:
        return mats.get("M_VMF_Expansion02")
    if "Expansion01" in disk_fbx:
        return mats.get("M_VMF_Expansion01")
    if "GroundStudy" in disk_fbx:
        return mats.get("M_VMF_GroundStudy")
    return mats.get("M_VMF_Palette")


def apply_material(mesh, mat):
    if not mesh or not mat:
        return
    try:
        # StaticMesh: set material slot 0
        mats = mesh.static_materials
        if mats is not None and len(mats) > 0:
            slot = mats[0]
            slot.set_editor_property("material_interface", mat)
            mats[0] = slot
            mesh.set_editor_property("static_materials", mats)
        else:
            unreal.EditorAssetLibrary.set_metadata_tag  # noop guard
            # fallback via EditorStaticMeshLibrary if available
            try:
                unreal.EditorStaticMeshLibrary.set_material(mesh, 0, mat)
            except Exception:
                pass
    except Exception as e:
        try:
            mesh.set_material(0, mat)
        except Exception as e2:
            log("set mat fail: {} / {}".format(e, e2))


def walk_files(root, ext):
    out = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(ext):
                out.append(os.path.join(dirpath, f))
    out.sort()
    return out


def main():
    log("=== START VMF IMPORT ===")
    ensure_dir("/Game/Farm")
    ensure_dir(GAME_ROOT)
    ensure_dir(GAME_ROOT + "/Materials")
    ensure_dir(GAME_ROOT + "/Textures")
    ensure_dir(GAME_ROOT + "/Models")

    # 1) textures
    tex_by_name = {}
    for png in walk_files(DISK_TEX, ".png"):
        tex = import_texture(png)
        if tex:
            tex_by_name[os.path.splitext(os.path.basename(png))[0]] = (
                tex,
                rel_game_path(png) + "/" + os.path.splitext(os.path.basename(png))[0],
            )

    # 2) materials
    mats = {}
    mat_folder = GAME_ROOT + "/Materials"
    for tname, mname in PALETTE_MAP.items():
        entry = tex_by_name.get(tname)
        if not entry:
            log("missing palette tex " + tname)
            continue
        mat = create_unlit_material(mat_folder, mname, entry[0])
        if mat:
            mats[mname] = mat

    # 3) FBX
    ok = 0
    fail = 0
    bounds_samples = []
    for fbx in walk_files(DISK_MODELS, ".fbx"):
        result = import_fbx(fbx)
        if not result:
            fail += 1
            continue
        mesh, dest = result
        mat = pick_mat_for_path(fbx, mats)
        apply_material(mesh, mat)
        try:
            unreal.EditorAssetLibrary.save_asset(dest)
        except Exception:
            pass
        ok += 1
        if ok <= 8 or "FarmShed" in fbx or "Farm_11x9" in fbx or "Soil_Dry" in fbx or "Ground_Grass" in fbx:
            try:
                box = mesh.get_bounding_box()
                mn = box.min
                mx = box.max
                bounds_samples.append(
                    (
                        os.path.basename(fbx),
                        round(mx.x - mn.x, 1),
                        round(mx.y - mn.y, 1),
                        round(mx.z - mn.z, 1),
                    )
                )
            except Exception as e:
                bounds_samples.append((os.path.basename(fbx), "err", str(e), ""))

    log("FBX imported ok={} fail={}".format(ok, fail))
    for b in bounds_samples:
        log("bounds {} size=({},{},{})".format(b[0], b[1], b[2], b[3]))

    assets = unreal.EditorAssetLibrary.list_assets(GAME_ROOT, recursive=True)
    log("total assets under VMF: {}".format(len(assets)))
    log("=== END VMF IMPORT ===")


main()

