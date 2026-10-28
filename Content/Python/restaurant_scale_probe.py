# -*- coding: utf-8 -*-
"""Probe bounds: nearby VMF props vs Restaurant_*/RestChair_*."""
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def bounds_of(a):
    origin, extent = a.get_actor_bounds(False)
    sc = a.get_actor_scale3d()
    return {
        "label": a.get_actor_label() or a.get_name(),
        "cls": a.get_class().get_name(),
        "loc": [round(a.get_actor_location().x), round(a.get_actor_location().y), round(a.get_actor_location().z)],
        "scale": [round(sc.x, 3), round(sc.y, 3), round(sc.z, 3)],
        "extent": [round(extent.x, 1), round(extent.y, 1), round(extent.z, 1)],
        "size": [round(extent.x * 2, 1), round(extent.y * 2, 1), round(extent.z * 2, 1)],
        "origin_z": round(origin.z, 1),
        "bottom_z": round(origin.z - extent.z, 1),
    }

ref_keys = ("Shipping", "Crate", "Fence", "Chest", "Compost", "FarmSign", "Scarecrow", "Well",
            "BridgeSouthPost", "BridgeSouthRail", "Barrel", "Bench", "Sign")
refs = []
rest = []
cells = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        rest.append(bounds_of(a))
        continue
    loc = a.get_actor_location()
    if lab.startswith("VMF_Grass_20_") or lab.startswith("VMF_PathV_17"):
        if len(cells) < 6:
            cells.append(bounds_of(a))
    if any(k.lower() in lab.lower() for k in ref_keys):
        refs.append(bounds_of(a))

comp_scales = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not (lab.startswith("Restaurant_") or lab.startswith("RestChair_")):
        continue
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        rs = c.get_editor_property("relative_scale3d")
        # only visible/with mesh
        if not sm:
            continue
        comp_scales.append({
            "actor": lab, "comp": c.get_name(),
            "mesh": sm.get_name(),
            "rel_scale": [round(rs.x, 3), round(rs.y, 3), round(rs.z, 3)],
        })

# mesh native bounds (unit scale)
mesh_paths = {
    "chest": "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "crate": "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate",
    "stack": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Storage/SM_VMF_Set_CrateStack",
    "compost": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Facility_CompostBin",
    "sign": "/Game/Farm/VoxelMicroFarm/Models/Expansion01/SM_VMF_Prop_FarmSign",
}
mesh_native = {}
for k, p in mesh_paths.items():
    m = unreal.EditorAssetLibrary.load_asset(p)
    if not m:
        mesh_native[k] = None
        continue
    # StaticMesh has get_bounds
    try:
        b = m.get_bounds()
        box = b.box_extent
        mesh_native[k] = {"extent": [round(box.x,1), round(box.y,1), round(box.z,1)],
                          "size": [round(box.x*2,1), round(box.y*2,1), round(box.z*2,1)]}
    except Exception as e:
        mesh_native[k] = {"err": str(e)}

rep = {"refs": refs[:30], "restaurant": rest, "cells": cells, "comp_scales": comp_scales, "mesh_native": mesh_native}
open(r"E:\UE\FarmSim25D\Saved\restaurant_scale_probe.json", "w", encoding="utf-8").write(
    json.dumps(rep, ensure_ascii=False, indent=2))
print(json.dumps(rep, ensure_ascii=False, indent=2))
