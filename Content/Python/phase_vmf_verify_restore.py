# -*- coding: utf-8 -*-
import unreal
def log(m):
    unreal.log("[VERIFY] "+str(m)); print("[VERIFY] "+str(m))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
counts = {"Grass":0,"Soil":0,"Fence":0,"Path":0,"Tree":0,"Cliff":0,"Water":0,"Crop":0,"GrassFill":0}
sample_grass = None
soil_labs = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not lab.startswith("VMF_"): continue
    if "GrassFill" in lab: counts["GrassFill"] += 1
    if lab.startswith("VMF_Grass_"): counts["Grass"] += 1
    if "Soil" in lab: counts["Soil"] += 1; soil_labs.append(lab)
    if "Fence" in lab: counts["Fence"] += 1
    if lab.startswith("VMF_Path"): counts["Path"] += 1
    if "Tree" in lab: counts["Tree"] += 1
    if lab.startswith("VMF_Cliff"): counts["Cliff"] += 1
    if "Water" in lab: counts["Water"] += 1
    if "Crop" in lab: counts["Crop"] += 1
    if sample_grass is None and lab.startswith("VMF_Grass_"):
        try:
            m = a.static_mesh_component.static_mesh
            sample_grass = (lab, m.get_path_name() if m else None, tuple(a.get_actor_scale3d()))
        except Exception as e:
            sample_grass = str(e)
log("counts="+str(counts))
log("grass_sample="+str(sample_grass))
log("soil_n="+str(len(soil_labs))+" sample="+str(soil_labs[:8]))
# camera
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    obj = lib.get_object_for_blueprint(lib.get_data(h), bp)
    if obj and "SpringArm" in obj.get_class().get_name():
        r = obj.get_editor_property("relative_rotation")
        log("SpringArm p={:.0f} y={:.0f} arm={}".format(r.pitch, r.yaw, obj.get_editor_property("target_arm_length")))
    if obj and obj.get_class().get_name()=="CameraComponent":
        try: log("ortho={}".format(obj.get_editor_property("ortho_width")))
        except Exception: pass
ps=None
for a in eas.get_all_level_actors():
    if a.get_actor_label()=="PlayerStart":
        loc=a.get_actor_location(); log("PlayerStart ({:.0f},{:.0f},{:.0f})".format(loc.x,loc.y,loc.z)); break
vmf=sum(1 for a in eas.get_all_level_actors() if (a.get_actor_label() or "").startswith("VMF_"))
log("VMF_total="+str(vmf))
imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
txt = imc.get_editor_property("default_key_mappings").export_text()
log("IMC E={} F={} R={} G={} H={}".format(
    "Key=E" in txt, "Key=F" in txt, "Key=R" in txt, "Key=G" in txt, "Key=H" in txt))
log("DONE")
