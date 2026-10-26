# -*- coding: utf-8 -*-
import unreal
def log(m): unreal.log("[SOIL] " + str(m))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
soil=[]; crop=[]; path=[]
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if "Soil" in lab or "soil" in lab:
        soil.append(lab)
    if "Crop" in lab or "Tomato" in lab or "Corn" in lab or "Pumpkin" in lab:
        crop.append(lab)
    if "Path" in lab or "Bridge" in lab:
        path.append(lab)
log("soil n={} samples={}".format(len(soil), soil[:20]))
log("crop n={} samples={}".format(len(crop), crop[:20]))
log("path n={} samples={}".format(len(path), path[:10]))
# Check one soil mesh
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if "Soil" in lab:
        loc=a.get_actor_location(); sc=a.get_actor_scale3d()
        comps = a.get_components_by_class(unreal.StaticMeshComponent)
        sm=None
        for c in comps:
            try: sm=c.get_editor_property("static_mesh"); break
            except: pass
        log("SOIL {} loc=({:.1f},{:.1f},{:.1f}) sc={:.4f} mesh={}".format(lab, loc.x, loc.y, loc.z, sc.x, sm))
        break
# GridToWorld test via calling? Just dump GridManager actor location and compute
# Also check HOE zone actors around 12-14,20-22 world
for a in eas.get_all_level_actors():
    lab=a.get_actor_label()
    if lab.startswith("VMF_") and ("12_2" in lab or "13_2" in lab or "14_2" in lab):
        loc=a.get_actor_location()
        log("near hoe {} ({:.0f},{:.0f},{:.0f})".format(lab, loc.x, loc.y, loc.z))
