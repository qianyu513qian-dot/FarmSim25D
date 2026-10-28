# -*- coding: utf-8 -*-
"""Find open land near south bridge for restaurant zone."""
import unreal, json, math
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CELL=100.0
# Collect path/grass/soil near south bridge east end (land)
candidates=[]
occupied=set()
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    loc=a.get_actor_location()
    gx=int(round((loc.x-50)/CELL)); gy=int(round((loc.y-50)/CELL))
    occupied.add((gx,gy))
    if lab.startswith("VMF_Path") or lab.startswith("VMF_Grass") or "Yard" in lab:
        if 1400 <= loc.x <= 2600 and 200 <= loc.y <= 1000:
            candidates.append({"label":lab,"x":round(loc.x,1),"y":round(loc.y,1),"gx":gx,"gy":gy})

# Prefer cells around x~1850-2200 y~450-750 (inland of south bridge east lantern at 1680,690)
target=(1950,550)
scored=sorted(candidates, key=lambda c: (c["x"]-target[0])**2+(c["y"]-target[1])**2)
# Also list house/shed locations
markers=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if any(k in lab for k in ("Shed","Well","House","Chicken","Shipping","Scarecrow","PlayerStart","FarmClock")):
        loc=a.get_actor_location()
        markers.append({"label":lab,"x":round(loc.x,1),"y":round(loc.y,1),"z":round(loc.z,1)})

out={
 "near_count":len(candidates),
 "nearest10":scored[:10],
 "markers":markers,
 "suggested_zone":{"tables":[(2050,500),(2250,500)],"stove":(2150,700),"trash":(2050,700),"sign":(1850,550)}
}
path=r"E:\UE\FarmSim25D\Saved\restaurant_zone_probe.json"
open(path,"w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
unreal.log("[ZONE] "+json.dumps(out["suggested_zone"]))
print(json.dumps(out,ensure_ascii=False,indent=2))
