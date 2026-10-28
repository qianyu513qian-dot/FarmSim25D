# -*- coding: utf-8 -*-
"""Probe south bridge / dock coords + pre-place census. Read-only."""
import unreal, json
from collections import Counter
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

counts = Counter()
bridge = []
dock = []
south_land = []  # high X south area samples
rest = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    loc = a.get_actor_location()
    if lab.startswith("VMF_Grass"): counts["VMF_Grass"] += 1
    elif lab.startswith("VMF_Path"): counts["Path"] += 1
    elif "Bridge" in lab or "Pier" in lab or "Dock" in lab:
        counts["BridgePier"] += 1
        if loc.y < 1200:  # south-ish
            bridge.append({"label": lab, "x": round(loc.x), "y": round(loc.y), "z": round(loc.z)})
    elif "Tree" in lab: counts["Tree"] += 1
    elif lab.startswith("VMF_Water") or (lab.startswith("VMF_") and "Water" in lab):
        counts["Water"] += 1
    elif "House" in lab or "FarmShed" in lab or "Well" in lab or "Chicken" in lab:
        counts["Buildings"] += 1
    elif lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        counts["Restaurant"] += 1
        rest.append(lab)
    elif "PlayerStart" in lab: counts["PlayerStart"] += 1

    # south land grass near bridge: y low, x mid-high
    if lab.startswith("VMF_Grass") and 1700 <= loc.x <= 2500 and 200 <= loc.y <= 900:
        south_land.append({"label": lab, "x": round(loc.x), "y": round(loc.y), "z": round(loc.z)})

# sort bridge by y then x
bridge.sort(key=lambda d: (d["y"], d["x"]))
south_land.sort(key=lambda d: (d["y"], d["x"]))

# check Restaurant BP paths exist
bps = {}
for name in ("BP_RestaurantTable", "BP_RestaurantStove", "BP_RestaurantTrash",
             "BP_RestaurantOpenSign", "BP_RestaurantManager", "BP_RestaurantInteractBase"):
    p = "/Game/Farm/Restaurant/" + name
    bps[name] = unreal.EditorAssetLibrary.does_asset_exist(p)

# chair mesh candidate
chair_mesh = unreal.EditorAssetLibrary.does_asset_exist(
    "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest")

rep = {
    "total": len(eas.get_all_level_actors()),
    "counts": dict(counts),
    "bridge_south_sample": bridge[:40],
    "bridge_south_n": len(bridge),
    "south_grass_sample": south_land[:30],
    "south_grass_n": len(south_land),
    "rest_left": rest,
    "bps": bps,
}
# bbox of south bridge posts
if bridge:
    xs = [b["x"] for b in bridge]; ys = [b["y"] for b in bridge]
    rep["bridge_bbox"] = {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys)}
if south_land:
    xs = [b["x"] for b in south_land]; ys = [b["y"] for b in south_land]
    rep["south_land_bbox"] = {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys)}

open(r"E:\UE\FarmSim25D\Saved\restaurant_place2_probe.json","w",encoding="utf-8").write(
    json.dumps(rep, ensure_ascii=False, indent=2))
print(json.dumps(rep, ensure_ascii=False, indent=2))
