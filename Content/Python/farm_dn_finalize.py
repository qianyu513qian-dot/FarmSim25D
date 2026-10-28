import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=list(eas.get_all_level_actors())
removed=[]
for a in actors:
    if a.get_actor_label() in ['Farm_QA_Capture','Farm_Moon_New']:
        removed.append(a.get_actor_label()); eas.destroy_actor(a)
clock=next(a for a in actors if isinstance(a,unreal.FarmClock))
clock.modify()
clock.apply_lighting(10.0)
clock.set_editor_property('preview_hour',10.0)
saved=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
packages=unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
assert saved and packages
REPORT={'removed_temporary_actors':removed,'preview':'10:00','saved':saved}
