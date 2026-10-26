# -*- coding: utf-8 -*-
"""Probe VMF tree materials and camera orientation."""
import unreal

def log(m):
    unreal.log("[probe_trees] " + str(m))
    print("[probe_trees] " + str(m))

# Mesh assets
paths = [
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_Tree_Tall",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_Tree_Broadleaf",
    "/Game/Farm/VoxelMicroFarm/Models/Nature/SM_VMF_Nature_Tree",
    "/Game/Farm/VoxelMicroFarm/Models/Nature/SM_VMF_Nature_Bush",
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Buildings/SM_VMF_Building_FarmShed",
]
for p in paths:
    mesh = unreal.EditorAssetLibrary.load_asset(p)
    if not mesh:
        log("MISSING mesh " + p)
        continue
    mats = mesh.static_materials
    log("MESH " + p.split("/")[-1] + " slots=" + str(len(mats)))
    for i, slot in enumerate(mats):
        mi = slot.material_interface
        log("  slot{} mat={} name={}".format(i, mi, mi.get_name() if mi else None))

# Materials + textures
mat_paths = [
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Palette",
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Expansion02",
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Expansion02_Nature",
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Expansion02_Facilities",
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_GroundStudy",
]
for mp in mat_paths:
    m = unreal.EditorAssetLibrary.load_asset(mp)
    log("MAT {} exists={}".format(mp.split("/")[-1], bool(m)))

tex_paths = [
    "/Game/Farm/VoxelMicroFarm/Textures/T_VMF_Palette",
    "/Game/Farm/VoxelMicroFarm/Textures/T_VMF_Expansion02_Palette",
    "/Game/Farm/VoxelMicroFarm/Textures/T_VMF_Expansion02_Nature_Palette",
    "/Game/Farm/VoxelMicroFarm/Textures/T_VMF_Expansion02_Facilities_Palette",
    "/Game/Farm/VoxelMicroFarm/Textures/T_VMF_GroundStudy_Palette",
]
for tp in tex_paths:
    t = unreal.EditorAssetLibrary.load_asset(tp)
    if t:
        try:
            sz = t.blueprint_get_size_x() if hasattr(t, "blueprint_get_size_x") else "?"
        except Exception:
            sz = "?"
        log("TEX {} OK size={}".format(tp.split("/")[-1], sz))
    else:
        log("TEX MISSING " + tp)

# World tree actors
world = unreal.EditorLevelLibrary.get_editor_world()
actors = unreal.EditorLevelLibrary.get_all_level_actors()
trees = []
houses = []
for a in actors:
    n = a.get_actor_label() or a.get_name()
    if "Tree" in n or "Bush" in n:
        trees.append(a)
    if "House" in n or "FarmShed" in n:
        houses.append(a)

log("tree_actors=" + str(len(trees)))
for a in trees[:8]:
    n = a.get_actor_label()
    loc = a.get_actor_location()
    # materials on components
    comps = a.get_components_by_class(unreal.StaticMeshComponent)
    for c in comps:
        mesh = c.static_mesh
        nmats = c.get_num_materials()
        mat0 = c.get_material(0) if nmats > 0 else None
        log("  ACTOR {} loc=({:.0f},{:.0f},{:.0f}) mesh={} nmat={} mat0={}".format(
            n, loc.x, loc.y, loc.z,
            mesh.get_name() if mesh else None,
            nmats,
            mat0.get_name() if mat0 else None))

for a in houses:
    loc = a.get_actor_location()
    log("HOUSE {} loc=({:.0f},{:.0f},{:.0f})".format(a.get_actor_label(), loc.x, loc.y, loc.z))

# Camera BP defaults
char_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(char_path)
if bp:
    cdo = unreal.EditorAssetLibrary.load_blueprint_class(char_path)
    # try find spring arm via default object
    try:
        cls = unreal.load_class(None, char_path + ".BP_TopDownCharacter_C")
        if cls:
            cdo2 = unreal.get_default_object(cls)
            comps = cdo2.get_components_by_class(unreal.SpringArmComponent) if cdo2 else []
            for sa in comps:
                r = sa.get_editor_property("relative_rotation")
                log("SpringArm rel_rot pitch={} yaw={} roll={}".format(r.pitch, r.yaw, r.roll))
                log("SpringArm length={} ortho?".format(sa.get_editor_property("target_arm_length")))
    except Exception as e:
        log("cam probe err " + str(e))

# Also list texture folder
assets = unreal.EditorAssetLibrary.list_assets("/Game/Farm/VoxelMicroFarm/Textures", recursive=True)
log("Textures count=" + str(len(assets)))
for a in assets[:40]:
    log("  " + a)

log("DONE")
