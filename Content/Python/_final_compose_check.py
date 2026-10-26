# -*- coding: utf-8 -*-
import unreal
def log(m):
    unreal.log("[FINAL] "+str(m)); print("[FINAL] "+str(m))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
keys = ["VMF_Water_Left","VMF_House_FarmShed","VMF_Well","VMF_ChickenCoop","VMF_Scarecrow"]
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab in keys or lab.startswith("VMF_Tree") and "Right" in lab:
        loc=a.get_actor_location(); rot=a.get_actor_rotation()
        log("{} loc=({:.0f},{:.0f},{:.0f}) rot=p{:.1f}/y{:.1f}/r{:.1f}".format(
            lab, loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll))
# tree centroid
txs=[]; tys=[]; n=0
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if "Tree" in lab and lab.startswith("VMF_"):
        loc=a.get_actor_location(); txs.append(loc.x); tys.append(loc.y); n+=1
if txs:
    log("trees n={} meanXY=({:.0f},{:.0f}) xRange=[{:.0f},{:.0f}]".format(
        n, sum(txs)/n, sum(tys)/n, min(txs), max(txs)))
# house / water
for lab in ("VMF_House_FarmShed","VMF_Water_Left"):
    for a in eas.get_all_level_actors():
        if a.get_actor_label()==lab:
            loc=a.get_actor_location()
            log("COMPOSE {} x={:.0f} y={:.0f} -> screen with yaw90: x low=LEFT y high=TOP".format(lab, loc.x, loc.y))
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    log("save "+str(e))
log("DONE")
