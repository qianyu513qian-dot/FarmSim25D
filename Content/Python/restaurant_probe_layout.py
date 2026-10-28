# -*- coding: utf-8 -*-
"""Probe south bridge / harbor actors and useful VMF meshes for restaurant placement."""
import unreal
import json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rows = []
bridges = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if any(k in lab for k in ("Bridge", "Pier", "Harbor", "Dock", "South")):
        loc = a.get_actor_location()
        bridges.append({"label": lab, "x": round(loc.x,1), "y": round(loc.y,1), "z": round(loc.z,1)})
    if lab.startswith("Restaurant") or lab.startswith("BP_Restaurant"):
        loc = a.get_actor_location()
        rows.append({"label": lab, "x": round(loc.x,1), "y": round(loc.y,1)})

# south-ish: lower Y historically, after rotate may differ — report bridge bbox
xs = [b["x"] for b in bridges]
ys = [b["y"] for b in bridges]
summary = {
    "bridge_count": len(bridges),
    "bridge_labels_sample": sorted(set(b["label"].rsplit("_",1)[0] if "_" in b["label"] else b["label"] for b in bridges))[:40],
    "bbox": None if not bridges else {
        "xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys),
        "cx": sum(xs)/len(xs), "cy": sum(ys)/len(ys),
    },
    "existing_restaurant": rows,
}

# classify bridges by name
by_tag = {}
for b in bridges:
    tag = "South" if "South" in b["label"] else ("Mid" if "Mid" in b["label"] else "Other")
    by_tag.setdefault(tag, []).append(b)
for tag, lst in by_tag.items():
    xs2 = [b["x"] for b in lst]; ys2 = [b["y"] for b in lst]
    summary[tag] = {"n": len(lst), "cx": sum(xs2)/len(xs2), "cy": sum(ys2)/len(ys2),
                    "xmin": min(xs2), "xmax": max(xs2), "ymin": min(ys2), "ymax": max(ys2)}

# mesh paths check
mesh_paths = [
    "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion01/SM_VMF_Prop_Barrel",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion01/SM_VMF_Prop_FarmSign",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Facility_CompostBin",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Storage/SM_VMF_Set_CrateStack",
    "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_HayBale",
    "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Scarecrow",
    "/Game/Farm/VoxelMicroFarm/Models/Buildings/SM_VMF_Building_ToolShelter",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Facility_DirectionSign",
]
mesh_ok = {}
for p in mesh_paths:
    mesh_ok[p] = unreal.EditorAssetLibrary.does_asset_exist(p)

# FarmClock
clocks = [a for a in eas.get_all_level_actors() if a.get_class().get_name().startswith("FarmClock")]
summary["farmclock"] = [{"label": a.get_actor_label(), "minutes": float(a.get_editor_property("state").minutes) if hasattr(a.get_editor_property("state"), "minutes") else str(a.get_editor_property("state"))} for a in clocks]

# PlayerStart
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "PlayerStart" or a.get_class().get_name() == "PlayerStart":
        loc = a.get_actor_location()
        summary["player_start"] = {"x": loc.x, "y": loc.y, "z": loc.z, "label": a.get_actor_label()}

summary["meshes"] = mesh_ok
# dump a few south bridge cell labels
south = sorted(by_tag.get("South", []), key=lambda b: (b["x"], b["y"]))
summary["south_sample"] = south[:8] + south[-4:]

out = r"E:\UE\FarmSim25D\Saved\restaurant_probe.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
unreal.log("[REST_PROBE] wrote " + out)
print(json.dumps(summary, ensure_ascii=False, indent=2))
