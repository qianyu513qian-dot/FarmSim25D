# -*- coding: utf-8 -*-
import unreal
from collections import Counter
TAG="[VERIFY_PROPS]"
def log(m):
    unreal.log(TAG+" "+str(m)); print(TAG+" "+str(m))
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ctr=Counter()
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_Cliff") or lab.startswith("VMF_Yard") or "Yard" in lab or "Cliff" in lab:
        ctr[lab.split("_")[1] if "_" in lab else lab]+=1
        if sum(ctr.values())<=8:
            log("leftover "+lab)
log("cliff/yard leftovers "+str(dict(ctr)))
# Confirm CDO len and TillCell still has Array_Contains
bp=unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
cdo=unreal.get_default_object(bp.generated_class())
bi=list(cdo.get_editor_property("BlockedIndices") or [])
log("CDO BI len="+str(len(bi)))
gm=None
for a in eas.get_all_level_actors():
    if "GridManager" in (a.get_actor_label() or "") or "GridManager" in a.get_class().get_name():
        gm=a; break
if gm:
    log("GM BI len="+str(len(list(gm.get_editor_property("BlockedIndices") or []))))
# Grass tillable sample: find a grass cell not in BI
CELL=100; W=40
s=set(bi)
tillable=0; blocked_grass=0
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_Grass_") and "Clump" not in lab:
        parts=lab.split("_")
        try:
            gx,gy=int(parts[-2]),int(parts[-1])
        except: continue
        fi=gy*W+gx
        if fi in s: blocked_grass+=1
        else: tillable+=1
log("plain grass tillable={} blocked_by_prop_or_zone={}".format(tillable, blocked_grass))
log("DONE")
