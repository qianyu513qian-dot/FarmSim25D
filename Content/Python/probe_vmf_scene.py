# -*- coding: utf-8 -*-
import unreal

KEYS = [
    "VMF_House_FarmShed", "VMF_ToolShelter", "VMF_ChickenCoop",
    "VMF_GroundStudy_Farm", "VMF_PathV_12_10", "VMF_Soil_4_8",
    "VMF_Soil_8_9", "VMF_CropCorn_4_14", "VMF_Scarecrow",
    "FarmGround", "BP_GridManager", "PlayerStart",
]

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
scene_left = 0
vmf = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("Scene_"):
        scene_left += 1
    if lab.startswith("VMF_"):
        vmf += 1

unreal.log("[VMF_PROBE] Scene_*=%d VMF_*=%d" % (scene_left, vmf))

wanted = set(KEYS)
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab not in wanted and not (lab.startswith("VMF_") and ("House" in lab or "FarmShed" in lab)):
        continue
    loc = a.get_actor_location()
    sc = a.get_actor_scale3d()
    try:
        o, e = a.get_actor_bounds(False)
        unreal.log("[VMF_PROBE] %s loc=(%.0f,%.0f,%.0f) scale=(%.4f,%.4f,%.4f) extent=(%.0f,%.0f,%.0f)" % (
            lab, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z, e.x, e.y, e.z))
    except Exception as ex:
        unreal.log("[VMF_PROBE] %s loc=(%.0f,%.0f,%.0f) scale=(%.4f,%.4f,%.4f) boundsERR=%s" % (
            lab, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z, ex))

# sample a few soil/path
n = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("VMF_Soil_") or lab.startswith("VMF_PathV_"):
        o, e = a.get_actor_bounds(False)
        unreal.log("[VMF_PROBE] sample %s extentXY=(%.0f,%.0f)" % (lab, e.x*2, e.y*2))
        n += 1
        if n >= 4:
            break
