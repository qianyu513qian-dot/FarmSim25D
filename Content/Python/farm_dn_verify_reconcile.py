# Soft verify after Codex+Ziiilk reconcile (decorative lantern meshes optional).
import unreal
actors=list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
clocks=[a for a in actors if isinstance(a,unreal.FarmClock)]
assert len(clocks)==1, clocks
c=clocks[0]
assert len(c.night_lights)==6, len(c.night_lights)
assert c.grid_manager and c.sun_light and c.moon_light and c.sky_light
assert c.ambient_grade and c.lighting_parameters
assert abs(float(c.get_editor_property('lamp_intensity'))-230.0)<0.01
assert abs(float(c.get_editor_property('seconds_per_ten_minutes'))-7.0)<0.01
keys=c.get_editor_property('light_keys')
noon=next(k for k in keys if abs(float(k.hour)-12)<0.01)
night=next(k for k in keys if abs(float(k.hour)-21)<0.01)
assert abs(float(noon.sun)-2.1)<0.05
assert abs(float(night.moon)-2.2)<0.05
pp=c.ambient_grade
s=pp.get_editor_property('settings')
assert float(s.get_editor_property('auto_exposure_min_brightness'))==0.0
assert float(s.get_editor_property('auto_exposure_max_brightness'))==0.0
assert float(s.get_editor_property('bloom_intensity'))==0.0
sky=c.sky_light.get_component_by_class(unreal.SkyLightComponent)
assert sky.get_editor_property('real_time_capture') is False
assert sky.get_editor_property('lower_hemisphere_is_black') is False
bel=unreal.BlueprintEditorLibrary
bp=unreal.load_asset('/Game/Farm/Grid/BP_GridManager')
ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,'EventGraph'))
tick=next(n for n in ge.list_all_nodes() if str(bel.get_node_title(n))=='Event Tick')
assert all(not p.list_connected_pins() for p in bel.list_all_pins(tick) if str(p.get_pin_name())=='then')
lamps=[a for a in actors if a.get_actor_label().startswith('Farm_Lantern_') and isinstance(a,unreal.PointLight)]
mesh_props=[a for a in actors if isinstance(a,unreal.StaticMeshActor) and a.get_actor_label().startswith('Farm_Lantern_')]
REPORT={'passed':['one FarmClock','six PointLight night_lights','refs Grid/Sun/Moon/Sky/PP/MPC','LampIntensity 230','LightKeys noon sun 2.1 night moon 2.2','EV100 lock bloom0','SkyLight cubemap no RTC','old Tick disconnected'],'lamp_pointlights':len(lamps),'lamp_mesh_props':len(mesh_props),'clock':c.get_path_name(),'actor_count':len(actors),'note':'decorative lantern meshes optional (farm_dn_materials); lighting owned by FarmClock'}
