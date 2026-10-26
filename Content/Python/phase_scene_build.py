# -*- coding: utf-8 -*-
"""Build Stardew-like initial farm SCENE in Lvl_TopDown.
Expands grid 20->28, spawns VectoRaith tile planes. NO Blueprint graph edits.
"""
import unreal
import os

ART = "/Game/Farm/Art"
MATS = ART + "/Mats"
TEX_DIR = ART
DISK_TILES = r"E:\UE\FarmSim25D\Content\Farm\Art\Tiles"
PLANE = "/Engine/BasicShapes/Plane"

CELL = 100.0
# Reference footprint ~ house+farm+path+water+margin → 28×28
WIDTH = 28
HEIGHT = 28
ORIGIN = unreal.Vector(0.0, 0.0, 0.0)
FARM_W = WIDTH * CELL   # 2800
FARM_H = HEIGHT * CELL  # 2800

# Z layers (FarmGround at ~1)
Z_WATER = 2.0
Z_PATH = 3.0
Z_TILLED = 3.5
Z_TERRACE = 4.0
Z_PROP = 5.0
Z_PROP2 = 6.0
Z_HOUSE = 7.0

SCENE_PREFIX = "Scene_"\

def billboard_rot():
    """UE5.8 Python Rotator(a,b,c)=(roll,pitch,yaw); use fields. Face camera on -X."""
    r = unreal.Rotator()
    r.pitch = 0.0
    r.yaw = -90.0
    r.roll = 90.0
    return r

UPRIGHT_LABELS = set([
    "House", "Lamp", "Crate", "Sign",
    "Fence_N", "Fence_W", "Fence_E",
    "Tree_NE", "Tree_E", "Tree_SE", "Tree_NW", "Tree_W", "Tree_SW_Island", "Tree_S", "Tree_PathR",
    "Rock_1", "Rock_2", "Rock_3", "Stump_1",
    "Flower_1", "Flower_2", "Flower_3", "Flower_4",
    "Reed_1", "Reed_2", "Reed_3",
    "Crop_TL", "Crop_TR", "Crop_BL",
])


# Textures to import (name -> filename under Tiles)
IMPORT_TEX = [
    "T_Dirt", "T_Water", "T_WaterBank", "T_Bridge", "T_BridgeWood",
    "T_Stairs", "T_TerraceTop", "T_CliffS", "T_CliffN", "T_CliffW", "T_CliffE",
    "T_House", "T_FenceH", "T_FenceH2", "T_FenceDetail", "T_FencePost",
    "T_Crate", "T_Lamp", "T_Sign",
    "T_TreeRound", "T_TreePine", "T_TreePink", "T_TreeOrchard",
    "T_RockLarge", "T_RockSmall", "T_Stump",
    "T_FlowerPink", "T_FlowerYellow", "T_Reed",
    "T_CropBedWheat", "T_CropBedTomato", "T_CropBedPepper", "T_CropBedMelon",
    "T_CropWheat", "T_CropTomato",
]


def log(msg):
    unreal.log("[SCENE] " + str(msg))


def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def cell_center(cx, cy, z=0.0):
    return unreal.Vector(ORIGIN.x + (cx + 0.5) * CELL,
                         ORIGIN.y + (cy + 0.5) * CELL, z)


def rect_center(cx, cy, tw, th, z=0.0):
    """Center of a tw×th cell rectangle with min corner (cx,cy)."""
    return unreal.Vector(ORIGIN.x + (cx + tw * 0.5) * CELL,
                         ORIGIN.y + (cy + th * 0.5) * CELL, z)


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def find_by_label(label):
    for a in eas().get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def destroy_scene_actors():
    to_kill = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith(SCENE_PREFIX):
            to_kill.append(a)
    for a in to_kill:
        try:
            eas().destroy_actor(a)
        except Exception as e:
            log("destroy fail {}: {}".format(a.get_actor_label(), e))
    log("cleared {} Scene_* actors".format(len(to_kill)))


def hide_label(label):
    a = find_by_label(label)
    if not a:
        return
    try:
        a.set_is_temporarily_hidden_in_editor(True)
    except Exception:
        pass
    try:
        a.set_actor_hidden_in_game(True)
    except Exception:
        pass
    # also collapse scale to avoid blocking
    try:
        a.set_actor_scale3d(unreal.Vector(0.001, 0.001, 0.001))
    except Exception:
        pass
    log("hid " + label)


def import_texture(name):
    disk = os.path.join(DISK_TILES, name + ".png")
    dest = TEX_DIR + "/" + name
    if not os.path.isfile(disk):
        log("MISSING " + disk)
        return None
    if unreal.EditorAssetLibrary.does_asset_exist(dest):
        try:
            unreal.EditorAssetLibrary.delete_asset(dest)
        except Exception:
            pass
    task = unreal.AssetImportTask()
    task.filename = disk
    task.destination_path = TEX_DIR
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
        log("IMPORT FAIL " + name)
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
        try:
            tex.set_editor_property(
                "compression_settings",
                unreal.TextureCompressionSettings.TC_EDITOR_ICON,
            )
        except Exception:
            pass
    try:
        tex.set_editor_property("compression_no_alpha", False)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(dest)
    log("tex OK " + name)
    return tex


def create_unlit_material(mat_name, texture, tiling=1.0, masked=False):
    ensure_dir(MATS)
    path = MATS + "/" + mat_name
    mel = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        try:
            unreal.EditorAssetLibrary.delete_asset(path)
        except Exception:
            pass
    factory = unreal.MaterialFactoryNew()
    mat = tools.create_asset(mat_name, MATS, unreal.Material, factory)
    if not mat:
        log("MAT FAIL " + mat_name)
        return None
    try:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    except Exception:
        pass
    try:
        mat.set_editor_property(
            "blend_mode",
            unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE,
        )
    except Exception:
        pass
    try:
        mat.set_editor_property("two_sided", True)
    except Exception:
        pass
    try:
        mel.delete_all_material_expressions(mat)
    except Exception:
        pass
    tex_coord = mel.create_material_expression(
        mat, unreal.MaterialExpressionTextureCoordinate, -600, 0
    )
    try:
        tex_coord.set_editor_property("u_tiling", float(tiling))
        tex_coord.set_editor_property("v_tiling", float(tiling))
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
            log("set tex fail: " + str(e))
    mel.connect_material_expressions(tex_coord, "", tex_sample, "UVs")
    mel.connect_material_property(
        tex_sample, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    )
    if masked:
        mel.connect_material_property(
            tex_sample, "A", unreal.MaterialProperty.MP_OPACITY_MASK
        )
    try:
        mel.recompile_material(mat)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(path)
    log("mat OK {} tile={} mask={}".format(mat_name, tiling, masked))
    return mat


def spawn_plane(label, mat, cx, cy, tw, th, z, collision=False, upright=None):
    """Spawn/replace a Scene_ plane covering cells [cx,cx+tw) x [cy,cy+th).
    upright=True stands the plane as a camera-facing billboard (2.5D props).
    """
    mesh = unreal.EditorAssetLibrary.load_asset(PLANE)
    if not mesh:
        log("NO PLANE MESH")
        return None
    if upright is None:
        upright = label in UPRIGHT_LABELS
    scale = unreal.Vector(float(tw), float(th), 1.0)
    if upright:
        height = float(th) * CELL
        loc = rect_center(cx, cy, tw, th, max(height * 0.5, 40.0))
        rot = billboard_rot()
    else:
        loc = rect_center(cx, cy, tw, th, z)
        rot = unreal.Rotator()  # identity; avoid Rotator(0,0,0) ctor ambiguity
    full = SCENE_PREFIX + label
    actor = find_by_label(full)
    if actor is None:
        actor = eas().spawn_actor_from_class(
            unreal.StaticMeshActor, loc, rot
        )
        actor.set_actor_label(full)
    else:
        actor.set_actor_location(loc, False, True)
        actor.set_actor_rotation(rot, False)
    actor.set_actor_scale3d(scale)
    smc = actor.static_mesh_component
    smc.set_static_mesh(mesh)
    if mat:
        smc.set_material(0, mat)
    # Collision: ground overlays walkable ( Querry only / no block) — use NoCollision for overlays
    # so character walks on FarmGround underneath
    try:
        if collision:
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        else:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
    try:
        actor.set_actor_hidden_in_game(False)
        actor.set_is_temporarily_hidden_in_editor(False)
    except Exception:
        pass
    return actor


def update_grid_and_ground(grass_mat):
    gm = find_by_label("BP_GridManager")
    if gm:
        try:
            gm.set_editor_property("GridWidth", WIDTH)
            gm.set_editor_property("GridHeight", HEIGHT)
            gm.set_editor_property("CellSize", CELL)
            gm.set_editor_property("GridOrigin", ORIGIN)
            log("GridManager -> {}x{} CellSize={} Origin=(0,0,0)".format(WIDTH, HEIGHT, CELL))
        except Exception as e:
            log("GridManager set FAIL: " + str(e))
    else:
        log("ERROR no BP_GridManager")

    # FarmGround
    center = unreal.Vector(ORIGIN.x + FARM_W * 0.5, ORIGIN.y + FARM_H * 0.5, 1.0)
    scale = unreal.Vector(FARM_W / 100.0, FARM_H / 100.0, 1.0)
    fg = find_by_label("FarmGround")
    mesh = unreal.EditorAssetLibrary.load_asset(PLANE)
    if fg is None:
        fg = eas().spawn_actor_from_class(
            unreal.StaticMeshActor, center, unreal.Rotator(0, 0, 0)
        )
        fg.set_actor_label("FarmGround")
    fg.set_actor_location(center, False, True)
    fg.set_actor_scale3d(scale)
    smc = fg.static_mesh_component
    if mesh:
        smc.set_static_mesh(mesh)
    if grass_mat:
        smc.set_material(0, grass_mat)
    try:
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception:
        pass
    log("FarmGround center=({},{}) scale=({},{})".format(center.x, center.y, scale.x, scale.y))

    # Hide old borders (wrong size)
    for lab in ["FarmBorder_W", "FarmBorder_E", "FarmBorder_S", "FarmBorder_N"]:
        hide_label(lab)

    # PlayerStart on path near farm plots — cell (12, 10)
    ps = find_by_label("PlayerStart")
    if ps is None:
        for a in eas().get_all_level_actors():
            if a.get_class().get_name() == "PlayerStart":
                ps = a
                break
    spawn = cell_center(12, 10, 100.0)
    if ps:
        old = ps.get_actor_location()
        ps.set_actor_location(spawn, False, True)
        log("PlayerStart {} -> {}".format(old, spawn))
    else:
        log("WARNING no PlayerStart")


def save_level():
    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = els.save_current_level()
        log("save_current_level -> " + str(ok))
    except Exception as e:
        log("save fail: " + str(e))
        try:
            unreal.EditorLevelLibrary.save_current_level()
        except Exception as e2:
            log("save2 fail: " + str(e2))


def main():
    log("=== START SCENE BUILD {}x{} ===".format(WIDTH, HEIGHT))
    ensure_dir("/Game/Farm")
    ensure_dir(ART)
    ensure_dir(MATS)

    destroy_scene_actors()

    # Import textures
    textures = {}
    for name in IMPORT_TEX:
        t = import_texture(name)
        if t:
            textures[name] = t

    # Also ensure T_Grass / T_Tilled exist (from prior import)
    for name in ["T_Grass", "T_Tilled"]:
        p = TEX_DIR + "/" + name
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            textures[name] = unreal.EditorAssetLibrary.load_asset(p)
        else:
            disk = os.path.join(DISK_TILES, name + ".png")
            if os.path.isfile(disk):
                textures[name] = import_texture(name)

    # Materials
    mats = {}
    # Opaque tiled ground
    if textures.get("T_Grass"):
        mats["M_Grass"] = create_unlit_material("M_Grass", textures["T_Grass"], tiling=float(WIDTH), masked=False)
    if textures.get("T_Dirt"):
        mats["M_Dirt"] = create_unlit_material("M_Dirt", textures["T_Dirt"], tiling=1.0, masked=False)
    if textures.get("T_Water"):
        mats["M_Water"] = create_unlit_material("M_Water", textures["T_Water"], tiling=1.0, masked=False)
    if textures.get("T_Tilled"):
        mats["M_Tilled"] = create_unlit_material("M_Tilled", textures["T_Tilled"], tiling=1.0, masked=False)
    if textures.get("T_TerraceTop"):
        mats["M_Terrace"] = create_unlit_material("M_Terrace", textures["T_TerraceTop"], tiling=1.0, masked=False)
    if textures.get("T_CliffS"):
        mats["M_Cliff"] = create_unlit_material("M_Cliff", textures["T_CliffS"], tiling=1.0, masked=False)

    # Masked props
    MASKED = [
        ("T_House", "M_House"),
        ("T_Bridge", "M_Bridge"),
        ("T_BridgeWood", "M_BridgeWood"),
        ("T_TreeRound", "M_TreeRound"),
        ("T_TreePine", "M_TreePine"),
        ("T_TreePink", "M_TreePink"),
        ("T_TreeOrchard", "M_TreeOrchard"),
        ("T_RockLarge", "M_RockLarge"),
        ("T_RockSmall", "M_RockSmall"),
        ("T_Stump", "M_Stump"),
        ("T_FlowerPink", "M_FlowerPink"),
        ("T_FlowerYellow", "M_FlowerYellow"),
        ("T_Reed", "M_Reed"),
        ("T_FenceH", "M_Fence"),
        ("T_FenceDetail", "M_FenceDetail"),
        ("T_Crate", "M_Crate"),
        ("T_Lamp", "M_Lamp"),
        ("T_Sign", "M_Sign"),
        ("T_Stairs", "M_Stairs"),
        ("T_CropBedWheat", "M_CropWheat"),
        ("T_CropBedTomato", "M_CropTomato"),
        ("T_CropBedPepper", "M_CropPepper"),
        ("T_CropBedMelon", "M_CropMelon"),
        ("T_CropWheat", "M_CropWheatStrip"),
        ("T_CropTomato", "M_CropTomatoTall"),
        ("T_WaterBank", "M_WaterBank"),
    ]
    for tname, mname in MASKED:
        if textures.get(tname):
            mats[mname] = create_unlit_material(mname, textures[tname], tiling=1.0, masked=True)

    update_grid_and_ground(mats.get("M_Grass"))

    # ========== LAYOUT (cells) — Stardew-like compact farm in 28×28 ==========
    # Water: left strip cols 0-2, bottom strip rows 0-2 (L shape; corner overlaps ok)
    spawn_plane("Water_Left", mats.get("M_Water"), 0, 0, 3, HEIGHT, Z_WATER)
    spawn_plane("Water_Bottom", mats.get("M_Water"), 3, 0, WIDTH - 3, 3, Z_WATER)

    # Dirt path: vertical from south bridge up to house steps (cols 12-13, rows 3-19)
    spawn_plane("Path_V", mats.get("M_Dirt"), 12, 3, 2, 17, Z_PATH)
    # Horizontal branch right (rows 12-13, cols 14-22)
    spawn_plane("Path_H", mats.get("M_Dirt"), 14, 12, 9, 2, Z_PATH)

    # Bridge over water at south of path (cols 12-13, rows 1-2) — 2×2
    spawn_plane("Bridge", mats.get("M_Bridge") or mats.get("M_BridgeWood"), 11, 1, 4, 2, Z_PROP)

    # Tilled farm mid-left (cols 4-10, rows 8-16) — empty hoeable look
    spawn_plane("Tilled", mats.get("M_Tilled") or mats.get("M_Dirt"), 4, 8, 7, 9, Z_TILLED)

    # Four decorative 3×3 crop beds inside tilled (visual only)
    # TL wheat, TR tomato-ish, BL leafy, BR empty (leave empty for hoe demo)
    beds = [
        ("CropBed_TL", "M_CropWheatStrip", 4, 14, 3, 1),
        ("CropBed_TR", "M_CropTomatoTall", 7, 14, 1, 2),
        ("CropBed_BL", "M_CropPepper", 4, 9, 1, 1),
        # BR empty — gameplay hoe zone
    ]
    # Place 3x3 of single crop sprites as overlays
    crop_spots = [
        # TL 3x3 wheat at (4,14)
        ("Crop_TL", "M_CropWheat", 4, 14, 3, 3),
        # TR tomatoes (7,14)
        ("Crop_TR", "M_CropTomato", 7, 14, 3, 3),
        # BL peppers (4,9)
        ("Crop_BL", "M_CropPepper", 4, 9, 3, 3),
        # BR empty
    ]
    for lab, mkey, cx, cy, tw, th in crop_spots:
        spawn_plane(lab, mats.get(mkey), cx, cy, tw, th, Z_PROP)

    # Stone terrace under house (cols 9-17, rows 20-26)
    spawn_plane("Terrace", mats.get("M_Terrace") or mats.get("M_Dirt"), 9, 20, 9, 7, Z_TERRACE)
    # Cliff face along south of terrace
    spawn_plane("Cliff_S", mats.get("M_Cliff"), 9, 19, 9, 1, Z_TERRACE + 0.2)
    # Stairs from path up to terrace (cols 12-13, row 19)
    spawn_plane("Stairs", mats.get("M_Stairs") or mats.get("M_Dirt"), 12, 19, 2, 1, Z_PROP)

    # House ~5×6 tiles centered on terrace → place at (11, 21) size 5×6
    spawn_plane("House", mats.get("M_House"), 11, 21, 5, 6, Z_HOUSE)

    # Picket fence around terrace yard
    # North fence
    spawn_plane("Fence_N", mats.get("M_Fence") or mats.get("M_FenceDetail"), 9, 26, 9, 1, Z_PROP2)
    # West / East fences
    spawn_plane("Fence_W", mats.get("M_FenceDetail") or mats.get("M_Fence"), 9, 20, 1, 6, Z_PROP2)
    spawn_plane("Fence_E", mats.get("M_FenceDetail") or mats.get("M_Fence"), 17, 20, 1, 6, Z_PROP2)

    # Props near house / path
    spawn_plane("Lamp", mats.get("M_Lamp"), 14, 18, 1, 2, Z_PROP2)
    spawn_plane("Crate", mats.get("M_Crate"), 14, 14, 1, 2, Z_PROP2)
    spawn_plane("Sign", mats.get("M_Sign"), 15, 11, 1, 2, Z_PROP2)

    # Trees (3×3) on grass
    trees = [
        ("Tree_NE", "M_TreeRound", 22, 22),
        ("Tree_E", "M_TreePine", 24, 16),
        ("Tree_SE", "M_TreeOrchard", 22, 6),
        ("Tree_NW", "M_TreePink", 4, 22),
        ("Tree_W", "M_TreeRound", 3, 17),
        ("Tree_SW_Island", "M_TreePine", 1, 1),  # small island in water
        ("Tree_S", "M_TreeOrchard", 18, 4),
        ("Tree_PathR", "M_TreeRound", 20, 14),
    ]
    for lab, mkey, cx, cy in trees:
        spawn_plane(lab, mats.get(mkey), cx, cy, 3, 3, Z_PROP2)

    # Rocks / stumps / flowers
    deco = [
        ("Rock_1", "M_RockLarge", 20, 20, 2, 2),
        ("Rock_2", "M_RockSmall", 8, 18, 1, 1),
        ("Rock_3", "M_RockSmall", 23, 10, 1, 1),
        ("Stump_1", "M_Stump", 19, 8, 2, 2),
        ("Flower_1", "M_FlowerPink", 16, 16, 1, 2),
        ("Flower_2", "M_FlowerYellow", 21, 18, 1, 1),
        ("Flower_3", "M_FlowerYellow", 8, 6, 1, 1),
        ("Flower_4", "M_FlowerPink", 25, 12, 1, 2),
        ("Reed_1", "M_Reed", 3, 5, 1, 1),
        ("Reed_2", "M_Reed", 3, 12, 1, 1),
        ("Reed_3", "M_Reed", 6, 3, 1, 1),
    ]
    for lab, mkey, cx, cy, tw, th in deco:
        spawn_plane(lab, mats.get(mkey), cx, cy, tw, th, Z_PROP2)

    # Small pond upper-right (optional, like reference)
    spawn_plane("Pond_NE", mats.get("M_Water"), 24, 24, 3, 3, Z_WATER)

    save_level()

    # Summary
    scene = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith(SCENE_PREFIX) or lab in ("FarmGround", "BP_GridManager", "PlayerStart"):
            loc = a.get_actor_location()
            sc = a.get_actor_scale3d()
            scene.append((lab, round(loc.x), round(loc.y), round(loc.z), round(sc.x, 2), round(sc.y, 2)))
    scene.sort(key=lambda t: t[0])
    log("=== ACTORS ({}) ===".format(len(scene)))
    for t in scene:
        log("  {} @ ({},{},{}) scale=({},{})".format(t[0], t[1], t[2], t[3], t[4], t[5]))
    log("MAP SIZE: {}×{} cells, CellSize={}, world AABB [0,{}]×[0,{}]".format(
        WIDTH, HEIGHT, CELL, int(FARM_W), int(FARM_H)))
    log("Play: open Lvl_TopDown — expect grass+water L + dirt path/bridge + tilled mid-left + house on terrace + trees")
    log("Gameplay: walk path near farm; hoe empty BR bed cells in tilled region; Grid prints still work")
    log("=== END SCENE BUILD ===")


main()
