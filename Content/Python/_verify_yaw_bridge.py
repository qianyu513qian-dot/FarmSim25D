import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
deck=rail=post=0
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if not lab.startswith("VMF_Bridge"): continue
    if "Rail" in lab: rail+=1
    elif "Post" in lab: post+=1
    else: deck+=1
print("[VERIFY] deck={} rail={} post={}".format(deck,rail,post))
bp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data=lib.get_data(h); name=str(lib.get_variable_name(data)); obj=lib.get_object_for_blueprint(data,bp)
    if obj and "SpringArm" in obj.get_class().get_name():
        r=obj.get_editor_property("relative_rotation")
        print("[VERIFY] yaw={:.1f} pitch={:.1f}".format(r.yaw,r.pitch))
