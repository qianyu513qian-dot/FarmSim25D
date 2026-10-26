# -*- coding: utf-8 -*-
import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_Grass_12_") or lab=="VMF_Grass_15_10" or lab.startswith("VMF_Grass_20_20"):
        sm=None
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm=c.get_editor_property("static_mesh"); break
        unreal.log("[G] {} loc={} sc={} mesh={}".format(lab, a.get_actor_location(), a.get_actor_scale3d(), sm))
        if lab.startswith("VMF_Grass_20_20"):
            break
# Count how many enum entries by trying Array_Add pin options - dump uasset binary strings
import os
p=r"E:\UE\FarmSim25D\Content\Farm\Grid\E_PlotState.uasset"
if os.path.isfile(p):
    data=open(p,"rb").read()
    for s in (b"Empty",b"Tilled",b"Planted",b"Watered",b"Grown",b"Mature",b"Seeded",b"Growing",b"Ready",b"Blocked",b"NewEnumerator"):
        unreal.log("[G] uasset has {!r}: {}".format(s, s in data))
unreal.log("[G] DONE")
