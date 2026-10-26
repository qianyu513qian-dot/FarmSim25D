# -*- coding: utf-8 -*-
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if "Water" in lab or lab.startswith("VMF_Cliff_"):
        loc = a.get_actor_location()
        sc = a.get_actor_scale3d()
        rot = a.get_actor_rotation()
        try:
            o, e = a.get_actor_bounds(False)
            unreal.log("[W] {} loc=({:.0f},{:.0f},{:.0f}) scale=({:.3f},{:.3f},{:.3f}) yaw={:.0f} origin=({:.0f},{:.0f}) extent=({:.0f},{:.0f},{:.0f})".format(
                lab, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z, rot.yaw, o.x, o.y, e.x, e.y, e.z))
        except Exception as ex:
            unreal.log("[W] {} err {}".format(lab, ex))
        if lab.startswith("VMF_Cliff_") and lab not in (
            "VMF_Cliff_7_37", "VMF_Cliff_8_13", "VMF_Cliff_6_24"):
            continue
unreal.log("[W] DONE")
