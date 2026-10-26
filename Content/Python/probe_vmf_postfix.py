import unreal
def log(m):
    print("[v]", m); unreal.log("[v] "+m)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for want in ("VMF_House_FarmShed","PlayerStart","VMF_Tree_F28_2","VMF_Tree_F38_2","VMF_Water_0_0","VMF_Water_39_0","VMF_Bridge"):
    pass
waters=[]; forests=[]; house=None; ps=None; plots=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    loc=a.get_actor_location()
    if lab=="VMF_House_FarmShed": house=loc
    if lab=="PlayerStart": ps=loc
    if "Water" in lab and lab.startswith("VMF_"):
        waters.append(loc.x)
    if lab.startswith("VMF_Tree_F"):
        forests.append(loc.x)
    if "Soil" in lab or "Bed" in lab or "Hoe" in lab or "Corn" in lab or "Tomato" in lab or "Pumpkin" in lab:
        if lab.startswith("VMF_"): plots.append((lab, loc.x, loc.y))
if house: log("house x={:.0f} y={:.0f}".format(house.x, house.y))
if ps: log("ps x={:.0f} y={:.0f}".format(ps.x, ps.y))
if waters: log("water x range {:.0f}..{:.0f} (n={})".format(min(waters), max(waters), len(waters)))
if forests: log("forest tree x range {:.0f}..{:.0f} (n={})".format(min(forests), max(forests), len(forests)))
log("sample plots "+str(plots[:8]))
# cam
bp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data=lib.get_data(h); obj=lib.get_object_for_blueprint(data,bp)
    if obj and "SpringArm" in obj.get_class().get_name():
        r=obj.get_editor_property("relative_rotation")
        log("cam pitch={} yaw={}".format(r.pitch, r.yaw))
