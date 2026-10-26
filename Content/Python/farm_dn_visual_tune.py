"""Unsaved look-development overrides for the live PIE world."""
import unreal,json
from pathlib import Path
request=json.loads((Path(unreal.Paths.project_saved_dir())/'VisualReview'/'request.json').read_text())
world=unreal.EditorLevelLibrary.get_game_world()
assert world
clock=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FarmClock)[0]
clock.set_editor_property('time_speed',0.0)
clock.restore_clock(unreal.FarmClockState(absolute_day=1,minutes=720))
clock.set_actor_tick_enabled(False)
pawn=unreal.GameplayStatics.get_player_pawn(world,0)
arm=pawn.get_component_by_class(unreal.SpringArmComponent)
cam=pawn.get_component_by_class(unreal.CameraComponent)
arm.set_world_rotation(unreal.Rotator(pitch=request.get('pitch',-60),yaw=90,roll=0),False,False)
cam.set_ortho_width(request.get('width',1500))
cam.set_projection_mode(unreal.CameraProjectionMode.PERSPECTIVE if request.get('perspective',False) else unreal.CameraProjectionMode.ORTHOGRAPHIC)
cam.set_field_of_view(request.get('fov',28.0))
arm.set_editor_property('target_arm_length',request.get('arm',6500.0))
if 'location' in request: pawn.set_actor_location(unreal.Vector(*request['location']),False,False)
if 'sun' in request: clock.sun_light.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(request['sun'])
if 'sky' in request: clock.sky_light.get_component_by_class(unreal.SkyLightComponent).set_intensity(request['sky'])
s=clock.ambient_grade.settings
for n,v in [('auto_exposure_bias',request.get('bias',0.0)),('override_auto_exposure_bias',True),('ambient_cubemap_intensity',request.get('ambient',.25)),('bloom_intensity',0.0)]: s.set_editor_property(n,v)
clock.ambient_grade.set_editor_property('settings',s)
REPORT={'request':request,'camera':str(cam.get_world_rotation())}
