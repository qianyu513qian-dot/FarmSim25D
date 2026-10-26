# -*- coding: utf-8 -*-
"""Import VectoRaith farm tiles, build unlit materials, apply grass to FarmGround.
Conservative: NO Blueprint graph edits, NO open_editor.
"""
import unreal
import os

ART = "/Game/Farm/Art"
MATS = ART + "/Mats"
TEX_DIR = ART  # textures live next to mats under /Game/Farm/Art/
DISK_TILES = r"E:\UE\FarmSim25D\Content\Farm\Art\Tiles"

# Destination package paths (without extension)
TEX = {
    "T_Grass":   DISK_TILES + r"\T_Grass.png",
    "T_Tilled":  DISK_TILES + r"\T_Tilled.png",
    "T_Planted": DISK_TILES + r"\T_Planted.png",
    "T_Watered": DISK_TILES + r"\T_Watered.png",
    "T_Ready":   DISK_TILES + r"\T_Ready.png",
}

# Opaque ground mats vs masked crop overlays
OPAQUE = {"T_Grass", "T_Tilled"}
MASKED = {"T_Planted", "T_Watered", "T_Ready"}

# Grass UV tiling: 20 cells across 2000uu plane
GRASS_TILING = 20.0


def log(msg):
    unreal.log("[ART_IMPORT] " + str(msg))


def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)
        log("mkdir " + path)


def import_texture(name, disk_path):
    dest = TEX_DIR + "/" + name
    if not os.path.isfile(disk_path):
        log("MISSING FILE " + disk_path)
        return None
    # Reimport if exists
    if unreal.EditorAssetLibrary.does_asset_exist(dest):
        log("texture exists, will reimport: " + dest)
        # delete then reimport for clean settings
        try:
            unreal.EditorAssetLibrary.delete_asset(dest)
            log("deleted old " + dest)
        except Exception as e:
            log("delete fail (will overwrite): " + str(e))

    task = unreal.AssetImportTask()
    task.filename = disk_path
    task.destination_path = TEX_DIR
    task.destination_name = name
    task.replace_existing = True
    task.automated = True
    task.save = True

    options = unreal.TextureFactory()
    # TextureFactory props applied via task.options when possible
    try:
        task.factory = options
    except Exception:
        pass

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    tex = unreal.EditorAssetLibrary.load_asset(dest)
    if not tex:
        log("ERROR import failed " + name)
        return None

    # Pixel-art friendly settings
    try:
        tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
        log(name + " Filter=Nearest")
    except Exception as e:
        log(name + " Filter fail: " + str(e))
    try:
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        log(name + " NoMipmaps")
    except Exception as e:
        log(name + " Mip fail: " + str(e))
    try:
        # Lossless / UI style
        tex.set_editor_property(
            "compression_settings",
            unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,
        )
        log(name + " Compression=VectorDisplacementmap")
    except Exception as e:
        try:
            tex.set_editor_property(
                "compression_settings",
                unreal.TextureCompressionSettings.TC_EDITOR_ICON,
            )
            log(name + " Compression=EditorIcon fallback")
        except Exception as e2:
            log(name + " Compression fail: " + str(e2))
    # Keep alpha for crop sprites
    try:
        tex.set_editor_property("compression_no_alpha", False)
    except Exception:
        pass
    try:
        unreal.EditorAssetLibrary.save_asset(dest)
    except Exception as e:
        log("save tex: " + str(e))
    log("OK texture " + dest)
    return tex


def create_unlit_material(mat_name, texture, tiling=1.0, masked=False):
    """Create/overwrite a simple Unlit material: TexCoord*tiling -> TextureSample -> Emissive (+ OpacityMask)."""
    ensure_dir(MATS)
    path = MATS + "/" + mat_name
    mel = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()

    if unreal.EditorAssetLibrary.does_asset_exist(path):
        try:
            unreal.EditorAssetLibrary.delete_asset(path)
            log("deleted old mat " + path)
        except Exception as e:
            log("mat delete fail: " + str(e))

    factory = unreal.MaterialFactoryNew()
    mat = tools.create_asset(mat_name, MATS, unreal.Material, factory)
    if not mat:
        log("ERROR create material " + mat_name)
        return None

    # Unlit + blend
    try:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    except Exception as e:
        log("shading_model: " + str(e))
    if masked:
        try:
            mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        except Exception as e:
            log("blend_mode: " + str(e))
    else:
        try:
            mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
        except Exception:
            pass
    # Two-sided for flat planes viewed from any angle
    try:
        mat.set_editor_property("two_sided", True)
    except Exception:
        pass

    # Clear any default expressions if present
    try:
        mel.delete_all_material_expressions(mat)
    except Exception:
        pass

    # Nodes
    tex_coord = mel.create_material_expression(
        mat, unreal.MaterialExpressionTextureCoordinate, -600, 0
    )
    try:
        tex_coord.set_editor_property("u_tiling", float(tiling))
        tex_coord.set_editor_property("v_tiling", float(tiling))
    except Exception as e:
        log("tiling prop: " + str(e))

    tex_sample = mel.create_material_expression(
        mat, unreal.MaterialExpressionTextureSample, -350, 0
    )
    try:
        tex_sample.set_editor_property("texture", texture)
    except Exception:
        try:
            tex_sample.texture = texture
        except Exception as e:
            log("set texture fail: " + str(e))

    mel.connect_material_expressions(tex_coord, "", tex_sample, "UVs")
    # Emissive for unlit look
    mel.connect_material_property(
        tex_sample, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    )
    if masked:
        mel.connect_material_property(
            tex_sample, "A", unreal.MaterialProperty.MP_OPACITY_MASK
        )

    try:
        mel.recompile_material(mat)
    except Exception as e:
        log("recompile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(path)
    log("OK material {} tiling={} masked={}".format(mat_name, tiling, masked))
    return mat


def find_actor_by_label(label):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def apply_grass_to_farmground(mat):
    actor = find_actor_by_label("FarmGround")
    if not actor:
        log("ERROR FarmGround not found in current level")
        return False
    smc = actor.static_mesh_component
    smc.set_material(0, mat)
    loc = actor.get_actor_location()
    sc = actor.get_actor_scale3d()
    log("FarmGround material set. loc=({:.1f},{:.1f},{:.1f}) scale=({:.2f},{:.2f},{:.2f})".format(
        loc.x, loc.y, loc.z, sc.x, sc.y, sc.z))
    return True


def save_level():
    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = els.save_current_level()
        log("save_current_level -> " + str(ok))
    except Exception as e:
        log("LevelEditorSubsystem save fail: " + str(e))
        try:
            unreal.EditorLevelLibrary.save_current_level()
            log("EditorLevelLibrary.save_current_level ok")
        except Exception as e2:
            log("save fail: " + str(e2))


def main():
    log("=== START ART IMPORT ===")
    ensure_dir("/Game/Farm")
    ensure_dir(ART)
    ensure_dir(MATS)
    ensure_dir(ART)  # tiles import dest

    textures = {}
    for name, disk in TEX.items():
        textures[name] = import_texture(name, disk)

    mats = {}
    # Grass: tiled across farm
    if textures.get("T_Grass"):
        mats["M_Grass"] = create_unlit_material(
            "M_Grass", textures["T_Grass"], tiling=GRASS_TILING, masked=False
        )
    # Tilled: per-cell plane will use tiling=1
    if textures.get("T_Tilled"):
        mats["M_Tilled"] = create_unlit_material(
            "M_Tilled", textures["T_Tilled"], tiling=1.0, masked=False
        )
    for tname, mname in [
        ("T_Planted", "M_Planted"),
        ("T_Watered", "M_Watered"),
        ("T_Ready", "M_Ready"),
    ]:
        if textures.get(tname):
            mats[mname] = create_unlit_material(
                mname, textures[tname], tiling=1.0, masked=True
            )

    grass = mats.get("M_Grass")
    if grass:
        apply_grass_to_farmground(grass)
    else:
        log("SKIP FarmGround — no M_Grass")

    # Persist
    for name in TEX:
        p = TEX_DIR + "/" + name
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            unreal.EditorAssetLibrary.save_asset(p)
    for mname in mats:
        p = MATS + "/" + mname
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            unreal.EditorAssetLibrary.save_asset(p)

    save_level()

    # Summary
    assets = unreal.EditorAssetLibrary.list_assets(ART, recursive=True)
    log("Art assets (" + str(len(assets)) + "):")
    for a in assets:
        log("  " + a)
    log("Plot visuals: MATERIALS READY only — VisualizeCell NOT wired (avoid BP crash risk).")
    log("=== END ART IMPORT ===")


main()
