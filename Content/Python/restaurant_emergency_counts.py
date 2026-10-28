# -*- coding: utf-8 -*-
"""Emergency: count Lvl_TopDown actors by category; list anomalies."""
import unreal, json
from collections import Counter
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
counts = Counter()
samples = {}
hidden = []
far = []
restaurant = []
player = None
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    cls = a.get_class().get_name()
    loc = a.get_actor_location()
    if lab.startswith("VMF_Grass"): counts["VMF_Grass"] += 1
    elif lab.startswith("VMF_Path"): counts["VMF_Path"] += 1
    elif lab.startswith("VMF_Water") or "Water" in lab and lab.startswith("VMF_"): counts["VMF_Waterish"] += 1
    elif "Bridge" in lab or "Pier" in lab: counts["BridgePier"] += 1
    elif lab.startswith("VMF_Cliff"): counts["VMF_Cliff"] += 1
    elif "Tree" in lab: counts["Tree"] += 1
    elif "Soil" in lab or "Crop" in lab or "Hoe" in lab: counts["SoilCrop"] += 1
    elif "FarmShed" in lab or "Well" in lab or "Chicken" in lab or "House" in lab: counts["Buildings"] += 1
    elif lab.startswith("Restaurant_") or lab.startswith("RestChair_"): 
        counts["Restaurant"] += 1
        restaurant.append({"label":lab,"x":round(loc.x),"y":round(loc.y),"z":round(loc.z),"hidden":a.is_hidden_ed() if hasattr(a,'is_hidden_ed') else None})
    elif lab.startswith("VMF_"): counts["VMF_Other"] += 1
    elif "PlayerStart" in lab or cls == "PlayerStart": 
        counts["PlayerStart"] += 1
        player={"label":lab,"x":loc.x,"y":loc.y,"z":loc.z}
    elif "FarmClock" in lab or "FarmClock" in cls: counts["FarmClock"] += 1
    elif "GridManager" in lab or "GridManager" in cls: counts["GridManager"] += 1
    elif "AirWall" in lab or "Collision" in lab or "Floor" in lab: counts["Collision"] += 1
    else: counts["Other"] += 1
    # anomalies
    try:
        if a.is_temporarily_hidden_in_editor() or a.b_hidden_ed_temporary:
            hidden.append(lab)
    except Exception:
        pass
    if abs(loc.x) > 20000 or abs(loc.y) > 20000 or loc.z < -500:
        far.append({"label":lab,"x":loc.x,"y":loc.y,"z":loc.z})

# total
total = sum(counts.values())
# bbox of VMF
xs=[]; ys=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_"):
        loc=a.get_actor_location(); xs.append(loc.x); ys.append(loc.y)
bbox=None
if xs:
    bbox={"xmin":min(xs),"xmax":max(xs),"ymin":min(ys),"ymax":max(ys),"n_vmf":len(xs)}

# check if grass/path/water suspiciously low
rep={
 "total_actors_classified": total,
 "counts": dict(counts),
 "player": player,
 "restaurant": restaurant,
 "far_or_sunk_sample": far[:30],
 "far_count": len(far),
 "hidden_editor_sample": hidden[:30],
 "hidden_count": len(hidden),
 "vmf_bbox": bbox,
 "level": str(unreal.EditorLevelLibrary.get_editor_world()) if hasattr(unreal,"EditorLevelLibrary") else "?",
}
# World Partition info
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    rep["world"]=str(world)
except Exception as e:
    rep["world_err"]=str(e)

open(r"E:\UE\FarmSim25D\Saved\restaurant_emergency_counts.json","w",encoding="utf-8").write(json.dumps(rep,ensure_ascii=False,indent=2))
print(json.dumps(rep,ensure_ascii=False,indent=2))
