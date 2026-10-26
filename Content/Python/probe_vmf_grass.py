# -*- coding: utf-8 -*-
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
fg = None
grass = 0
vmf = 0
hidden_fg = None
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab == "FarmGround":
        fg = a
        hidden_fg = a.is_hidden_ed()
        loc = a.get_actor_location()
        unreal.log("[PROBE] FarmGround hidden_ed={} loc=({},{},{})".format(hidden_fg, round(loc.x), round(loc.y), round(loc.z)))
    if lab.startswith("VMF_"):
        vmf += 1
        if lab.startswith("VMF_Grass_"):
            grass += 1
ps = None
for a in eas.get_all_level_actors():
    if "PlayerStart" in a.get_class().get_name() or a.get_actor_label() == "PlayerStart":
        loc = a.get_actor_location()
        unreal.log("[PROBE] PlayerStart @ ({},{},{})".format(round(loc.x), round(loc.y), round(loc.z)))
        break
house = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "VMF_House_FarmShed":
        loc = a.get_actor_location()
        unreal.log("[PROBE] House @ ({},{},{})".format(round(loc.x), round(loc.y), round(loc.z)))
unreal.log("[PROBE] VMF={} Grass_tiles={}".format(vmf, grass))
