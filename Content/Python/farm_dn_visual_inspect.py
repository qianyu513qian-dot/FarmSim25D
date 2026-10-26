import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = list(eas.get_all_level_actors())
def props(obj, names):
    result = {}
    for name in names:
        try: result[name] = str(obj.get_editor_property(name))
        except Exception: pass
    return result
REPORT = {'actors': [], 'camera': [], 'graph': []}
for a in actors:
    if isinstance(a, (unreal.FarmClock, unreal.PostProcessVolume, unreal.DirectionalLight, unreal.SkyLight)):
        d = {'label': a.get_actor_label(), 'rotation': str(a.get_actor_rotation())}
        if isinstance(a, unreal.FarmClock):
            d.update(props(a, ['light_keys', 'preview_hour', 'sun_yaw']))
        if isinstance(a, unreal.PostProcessVolume):
            d.update(props(a, ['priority', 'unbound', 'enabled', 'blend_weight']))
            d['settings'] = props(a.settings, ['auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','bloom_intensity','ambient_cubemap_intensity','ambient_cubemap','color_saturation','color_gain','film_slope','film_shoulder'])
        if isinstance(a, (unreal.DirectionalLight, unreal.SkyLight)):
            d['light'] = props(a.get_component_by_class(unreal.LightComponent), ['intensity','light_color','indirect_lighting_intensity','specular_scale'])
        REPORT['actors'].append(d)
bp = unreal.load_asset('/Game/TopDown/Blueprints/BP_TopDownCharacter')
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    obj = lib.get_object_for_blueprint(data, bp)
    if isinstance(obj, (unreal.SpringArmComponent, unreal.CameraComponent)):
        d = {'name': obj.get_name()}
        d.update(props(obj,['relative_rotation','relative_location','absolute_rotation','target_arm_length','target_offset','socket_offset','use_pawn_control_rotation','inherit_pitch','inherit_yaw','inherit_roll','do_collision_test','projection_mode','ortho_width','auto_calculate_ortho_planes','ortho_near_clip_plane','ortho_far_clip_plane','post_process_blend_weight']))
        if isinstance(obj, unreal.CameraComponent): d['pp'] = props(obj.post_process_settings,['auto_exposure_bias','override_auto_exposure_bias'])
        REPORT['camera'].append(d)
bel = unreal.BlueprintEditorLibrary
for graph_name in ['EventGraph','UserConstructionScript']:
    graph = bel.find_graph(bp,graph_name)
    if not graph: continue
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    for n in ge.list_all_nodes():
        title = str(bel.get_node_title(n))
        if any(t.lower() in title.lower() for t in ['rotation','rotator','camera','spring','vector','movement','ortho']):
            REPORT['graph'].append({'title':title,'pins':{str(p.get_pin_name()):str(p.get_pin_value()) for p in bel.list_all_pins(n) if not p.list_connected_pins()}})
