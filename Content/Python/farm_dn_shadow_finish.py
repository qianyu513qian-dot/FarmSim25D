"""Soften shadow edges only; preserve corrected light intensity/color curves."""
import unreal
assert not unreal.EditorLevelLibrary.get_game_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
report=[]
for a in actors:
    if a.get_actor_label() not in ['SunLight','MoonLight']: continue
    c=a.get_component_by_class(unreal.DirectionalLightComponent)
    before=c.get_editor_property('light_source_angle')
    a.modify(); c.modify()
    c.set_editor_property('light_source_angle',3.5 if a.get_actor_label()=='SunLight' else 4.0)
    report.append({'light':a.get_actor_label(),'old_angle':before,'new_angle':c.get_editor_property('light_source_angle')})
assert len(report)==2
clock=next(a for a in actors if isinstance(a,unreal.FarmClock))
pp=clock.ambient_grade
pp.modify(); settings=pp.settings
settings.set_editor_property('override_color_gamma_shadows',True)
settings.set_editor_property('color_gamma_shadows',unreal.Vector4(1.10,1.10,1.10,1.0))
pp.set_editor_property('settings',settings)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
REPORT={'shadow_edges':report,'shadow_gamma':1.10,'unchanged':'intensity, color, exposure, camera, scene objects'}
