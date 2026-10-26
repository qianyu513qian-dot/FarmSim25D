# -*- coding: utf-8 -*-
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TAG="[BRIDGE_LOC]"
def log(m):
    unreal.log(TAG+" "+str(m)); print(TAG+" "+str(m))
# sample bridge deck + count cliff/yard
n_cliff=n_yard=n_soil=n_crop=0
decks=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_Cliff_"): n_cliff+=1
    if lab.startswith("VMF_Yard_"): n_yard+=1
    if "Soil" in lab: n_soil+=1
    if lab.startswith("VMF_Crop"): n_crop+=1
    if lab.startswith("VMF_BridgeMid_") or lab.startswith("VMF_BridgeSouth_"):
        if "Rail" in lab or "Post" in lab: continue
        loc=a.get_actor_location(); sc=a.get_actor_scale3d()
        sm=None
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            try: sm=c.get_editor_property("static_mesh"); break
            except: pass
        decks.append((lab, round(loc.x), round(loc.y), round(loc.z), round(sc.x,4), sm.get_name() if sm else None))
log("cliff={} yard={} soil_lab={} crop={}".format(n_cliff,n_yard,n_soil,n_crop))
for d in sorted(decks)[::5][:15]:
    log("deck {}".format(d))
# tip decks
for d in decks:
    if "_2_" in d[0] or "_3_" in d[0] or "_16_" in d[0]:
        log("edge "+str(d))
# verify fence meshes load
for p in [
 "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Fence_Low_Straight",
 "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Fence_Picket_EndPost",
 "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass",
 "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
]:
    a=unreal.EditorAssetLibrary.load_asset(p)
    log("mesh {} -> {}".format(p.split("/")[-1], bool(a)))
