# -*- coding: utf-8 -*-
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
waterish = {}
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if not lab.startswith("VMF_"):
        continue
    for k in ("Water", "Cliff", "Bank", "Pond", "Lake", "Pier", "Bridge", "Deck"):
        if k in lab:
            waterish[k] = waterish.get(k, 0) + 1
            break
unreal.log("[CHK] " + str(waterish))
# sample any VMF with Water in name
n = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if "Water" in lab or lab.startswith("VMF_W"):
        loc = a.get_actor_location()
        unreal.log("[CHK] {} @ ({:.0f},{:.0f},{:.0f})".format(lab, loc.x, loc.y, loc.z))
        n += 1
        if n >= 15:
            break
unreal.log("[CHK] water-named samples={}".format(n))
# SpringArm unchanged?
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    obj = lib.get_object_for_blueprint(lib.get_data(h), bp)
    if obj and "SpringArm" in obj.get_class().get_name():
        r = obj.get_editor_property("relative_rotation")
        unreal.log("[CHK] SpringArm p={:.0f} y={:.0f} arm={}".format(
            r.pitch, r.yaw, obj.get_editor_property("target_arm_length")))
unreal.log("[CHK] DONE")
