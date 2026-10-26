# -*- coding: utf-8 -*-
"""Probe material texture bindings + camera spring arm."""
import unreal

def log(m):
    unreal.log("[probe2] " + str(m))
    print("[probe2] " + str(m))

mel = unreal.MaterialEditingLibrary

for mp in [
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Palette",
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Expansion02_Nature",
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Expansion02",
    "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_GroundStudy",
]:
    m = unreal.EditorAssetLibrary.load_asset(mp)
    if not m:
        log("missing " + mp)
        continue
    exprs = mel.get_material_expressions(m) if hasattr(mel, "get_material_expressions") else []
    log("MAT {} exprs={}".format(m.get_name(), len(exprs) if exprs else 0))
    for e in (exprs or []):
        en = e.get_class().get_name()
        tex = None
        try:
            tex = e.get_editor_property("texture")
        except Exception:
            pass
        log("  expr {} tex={}".format(en, tex.get_name() if tex else None))

# Sample a few Expansion02 Nature meshes' intended UV / material
for p in [
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_Tree_Tall",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_Tree_Broadleaf",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_Rock_Large",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_Flower_Yellow",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/GroundStudy/SM_VMF_GroundStudy_Path_Straight",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Fence_Picket_Straight",
]:
    mesh = unreal.EditorAssetLibrary.load_asset(p)
    if not mesh:
        continue
    mats = mesh.static_materials
    mi = mats[0].material_interface if mats else None
    log("mesh {} -> {}".format(p.split("/")[-1], mi.get_name() if mi else None))

# Camera: find SpringArm on BP_TopDownCharacter CDO / SCS
bp = unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
if bp:
    try:
        scs = bp.simple_construction_script
        nodes = scs.get_all_nodes() if scs else []
        log("SCS nodes=" + str(len(nodes)))
        for n in nodes:
            cn = n.get_class().get_name()
            try:
                td = n.component_template
            except Exception:
                td = None
            if td and isinstance(td, unreal.SpringArmComponent):
                r = td.get_editor_property("relative_rotation")
                log("SCS SpringArm pitch={} yaw={} roll={} arm={}".format(
                    r.pitch, r.yaw, r.roll, td.get_editor_property("target_arm_length")))
                try:
                    cam = None
                    # child camera
                except Exception:
                    pass
            if td and isinstance(td, unreal.CameraComponent):
                try:
                    ortho = td.get_editor_property("projection_mode")
                    ow = td.get_editor_property("ortho_width")
                    log("SCS Camera proj={} ortho_w={}".format(ortho, ow))
                except Exception as e:
                    log("cam err " + str(e))
    except Exception as e:
        log("bp scs err " + str(e))

# Also check texture file on disk for nature palette colors - sample via unreal
tex = unreal.EditorAssetLibrary.load_asset(
    "/Game/Farm/VoxelMicroFarm/Textures/Expansion02/T_VMF_Expansion02_Nature_Palette")
if tex:
    log("Nature palette size {}x{}".format(tex.blueprint_get_size_x(), tex.blueprint_get_size_y()))

# List all Expansion02 Nature static meshes
assets = unreal.EditorAssetLibrary.list_assets(
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature", recursive=True)
log("Nature meshes=" + str(len(assets)))
for a in assets:
    if a.endswith(".") or "/SM_" in a or a.split(".")[-1].startswith("SM_"):
        mesh = unreal.EditorAssetLibrary.load_asset(a.split(".")[0])
        if mesh and isinstance(mesh, unreal.StaticMesh):
            mats = mesh.static_materials
            mi = mats[0].material_interface if mats else None
            log("  {} -> {}".format(mesh.get_name(), mi.get_name() if mi else None))

log("DONE")
