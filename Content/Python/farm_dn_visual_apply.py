"""Persist the reviewed daylight and camera setup; safe to rerun after a build."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = list(eas.get_all_level_actors())
clock = next(a for a in actors if isinstance(a, unreal.FarmClock))
clock.modify()
clock.set_editor_property('light_keys', unreal.get_default_object(unreal.FarmClock).light_keys)
pp = clock.ambient_grade
pp.modify()
s = pp.settings
s.set_editor_property('override_bloom_intensity', True)
s.set_editor_property('bloom_intensity', 0.0)
s.set_editor_property('override_auto_exposure_bias', True)
s.set_editor_property('auto_exposure_bias', 0.0)
pp.set_editor_property('settings', s)

bp = unreal.load_asset('/Game/TopDown/Blueprints/BP_TopDownCharacter')
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
seen = set()
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    obj = lib.get_object_for_blueprint(lib.get_data(h), bp)
    if not obj or obj.get_path_name() in seen: continue
    seen.add(obj.get_path_name())
    if isinstance(obj, unreal.SpringArmComponent):
        obj.modify()
        for name, value in [('relative_rotation',unreal.Rotator(pitch=-48,yaw=90,roll=0)),
                            ('target_arm_length',4200.0),
                            ('absolute_rotation',True),('use_pawn_control_rotation',False),
                            ('inherit_pitch',False),('inherit_yaw',False),('inherit_roll',False),
                            ('do_collision_test',False)]:
            obj.set_editor_property(name,value)
    elif isinstance(obj, unreal.CameraComponent):
        obj.modify()
        for name,value in [('projection_mode',unreal.CameraProjectionMode.PERSPECTIVE),
                           ('field_of_view',32.0),('ortho_width',1500.0),('relative_rotation',unreal.Rotator()),
                           ('auto_calculate_ortho_planes',False),('ortho_near_clip_plane',0.0),
                           ('ortho_far_clip_plane',2097152.0)]:
            obj.set_editor_property(name,value)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
ge = unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_graph(bp,'EventGraph'))
assert not ge.list_nodes_with_errors()
assert unreal.EditorAssetLibrary.save_loaded_asset(bp)
# Start the editor at the acceptance time. New games still begin at 06:00.
clock.set_editor_property('preview_hour',12.0)
for actor in [clock.sun_light,clock.moon_light,clock.sky_light,clock.fog,*clock.night_lights]:
    if actor: actor.modify()
clock.apply_lighting(12.0)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
REPORT = {'saved':True,'camera':{'pitch':-48,'yaw':90,'projection':'perspective','fov':32,'arm':4200},
          'noon_sun':clock.sun_light.get_component_by_class(unreal.DirectionalLightComponent).intensity,
          'ambient_fill':pp.settings.ambient_cubemap_intensity,'bloom':pp.settings.bloom_intensity}
