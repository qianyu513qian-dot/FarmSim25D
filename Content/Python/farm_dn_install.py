"""Idempotent level integration, executed through official Unreal MCP."""
import unreal
from pathlib import Path
import json

eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel=unreal.BlueprintEditorLibrary
actors=list(eas.get_all_level_actors())
by_label={a.get_actor_label():a for a in actors}
mgr=by_label['BP_GridManager']
sun=by_label['SunLight']; moon=by_label['MoonLight']; sky=by_label['SkyLight']
fog=next((a for a in actors if isinstance(a,unreal.ExponentialHeightFog)),None)

# Turn off the previous clock's execution without touching grid/crop functions.
bp=unreal.load_asset('/Game/Farm/Grid/BP_GridManager')
ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,'EventGraph'))
disconnected=[]
for n in ge.list_all_nodes():
    title=str(bel.get_node_title(n))
    for p in bel.list_all_pins(n):
        if title=='Event Tick' and str(p.get_pin_name())=='then':
            p.break_pin_links(); disconnected.append('old Tick')
        if title=='InitBlockedFromIndices' and str(p.get_pin_name())=='then':
            targets=[str(bel.get_node_title(q.get_owning_node())) for q in p.list_connected_pins()]
            if any('GetAllActors' in t.replace(' ','') for t in targets):
                p.break_pin_links(); disconnected.append('old BeginPlay lighting chain')
        if title=='PrintString' and str(p.get_pin_name()) in ['bPrintToScreen','bPrintToLog']:
            p.set_pin_value('false')
bel.compile_blueprint(bp)
assert not ge.list_nodes_with_errors(), 'Grid manager compile errors'
unreal.EditorAssetLibrary.save_loaded_asset(bp)

clock=by_label.get('FarmClock')
if not clock:
    clock=eas.spawn_actor_from_class(unreal.FarmClock,unreal.Vector(0,0,100))
    clock.set_actor_label('FarmClock')
clock.set_editor_property('is_spatially_loaded',False)
for actor in [clock,mgr,sun,moon,sky]: actor.modify()
mgr.set_editor_property('is_spatially_loaded',False)
if fog:
    fog.modify(); fog.set_editor_property('is_spatially_loaded',False)
clock.set_editor_property('light_keys',unreal.get_default_object(unreal.FarmClock).get_editor_property('light_keys'))
clock.set_editor_property('lighting_parameters',unreal.load_asset('/Game/Farm/Lighting/MPC_FarmLighting'))
clock.set_editor_property('lamp_intensity',230.0)
for name,value in [('grid_manager',mgr),('sun_light',sun),('moon_light',moon),('sky_light',sky),('fog',fog),('preview_hour',10.0),('seconds_per_ten_minutes',7.0),('time_speed',1.0),('state',unreal.FarmClockState(absolute_day=1,minutes=360.0))]:
    clock.set_editor_property(name,value)
clock.set_editor_property('home_location',by_label['VMF_House_FarmShed'].get_actor_location())
clock.set_editor_property('wake_location',by_label['PlayerStart'].get_actor_location())

for a,index in [(sun,0),(moon,1)]:
    c=a.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('atmosphere_sun_light',index==0)
    c.set_editor_property('atmosphere_sun_light_index',index)
    c.set_editor_property('forward_shading_priority',0)
    c.set_editor_property('light_source_angle',2.0 if index==0 else 4.0)
    c.set_editor_property('use_temperature',False)
    c.set_editor_property('cast_shadows',True)
    a.set_actor_scale3d(unreal.Vector(1,1,1))
    a.set_editor_property('is_spatially_loaded',False)
sc=sky.get_component_by_class(unreal.SkyLightComponent)
sc.set_mobility(unreal.ComponentMobility.MOVABLE)
sc.set_editor_property('real_time_capture',False)
sc.set_editor_property('lower_hemisphere_is_black',False)
sc.set_editor_property('cast_shadows',False)
sc.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sc.set_editor_property('cubemap',unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
sc.recapture_sky()
sky.set_editor_property('is_spatially_loaded',False)

# Lock exposure so adaptation cannot turn night back into daytime.
pp=by_label.get('Farm_Exposure')
if not pp:
    pp=eas.spawn_actor_from_class(unreal.PostProcessVolume,unreal.Vector(0,0,0))
    pp.set_actor_label('Farm_Exposure')
pp.set_editor_property('unbound',True)
pp.modify()
pp.set_editor_property('priority',10.0)
settings=pp.get_editor_property('settings')
for name,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',0.0),('auto_exposure_max_brightness',0.0),('override_auto_exposure_bias',True),('auto_exposure_bias',0.0),('override_bloom_intensity',True),('bloom_intensity',0.0),('override_vignette_intensity',True),('vignette_intensity',0.15),('ambient_cubemap',unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))]:
    settings.set_editor_property(name,value)
pp.set_editor_property('settings',settings)
pp.set_editor_property('is_spatially_loaded',False)
clock.set_editor_property('ambient_grade',pp)

# Warm pools on the house approach and the existing two bridges; no light on water interiors.
positions=[('Home',(1830,3220,160)),('HomePath',(2090,3030,155)),('BridgeMidWest',(230,1720,150)),('BridgeMidEast',(1680,1720,150)),('BridgeSouthWest',(230,690,150)),('BridgeSouthEast',(1680,690,150))]
lights=[]
for name,pos in positions:
    label='Farm_Lantern_'+name
    a=by_label.get(label)
    if not a:
        a=eas.spawn_actor_from_class(unreal.PointLight,unreal.Vector(*pos)); a.set_actor_label(label)
    a.set_actor_location(unreal.Vector(*pos),False,False)
    a.modify()
    c=a.get_component_by_class(unreal.PointLightComponent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
    c.set_editor_property('attenuation_radius',480.0)
    c.set_editor_property('source_radius',18.0)
    c.set_editor_property('cast_shadows',False)
    c.set_light_color(unreal.LinearColor(1.0,0.53,0.18,1.0))
    a.set_editor_property('is_spatially_loaded',False)
    a.tags=['FarmNightLamp']
    lights.append(a)
clock.set_editor_property('night_lights',lights)
clock.apply_lighting(10.0)
saved=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
packages=unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
assert saved and packages, f'Level save failed: {saved}, {packages}'
REPORT={'clock':clock.get_path_name(),'disconnected':disconnected,'lamps':len(lights),'level_saved':saved,'packages_saved':packages}
