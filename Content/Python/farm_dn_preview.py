import unreal
import json
from pathlib import Path
settings=Path(unreal.Paths.project_saved_dir())/'DayNight'/'preview_request.json'
request=json.loads(settings.read_text())
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=list(eas.get_all_level_actors())
clock=next(a for a in actors if isinstance(a,unreal.FarmClock))
clock.apply_lighting(float(request['hour']))
capture=next((a for a in actors if a.get_actor_label()=='Farm_QA_Capture'),None)
if capture and 'center' in request:
    r=capture.get_actor_rotation()
    forward=unreal.MathLibrary.get_forward_vector(r)
    capture.set_actor_location(unreal.Vector(*request['center'])-forward*6500,False,False)
    capture.get_component_by_class(unreal.SceneCaptureComponent2D).set_editor_property('ortho_width',float(request.get('width',6200)))
if capture:
    c=capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    if 'moon' in request:
        clock.moon_light.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(float(request['moon']))
    if 'sky' in request:
        clock.sky_light.get_component_by_class(unreal.SkyLightComponent).set_intensity(float(request['sky']))
    s=c.get_editor_property('post_process_settings')
    s.set_editor_property('override_dynamic_global_illumination_method',True)
    s.set_editor_property('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN)
    c.set_editor_property('post_process_settings',s)
    c.capture_scene()
REPORT={'hour':request['hour'],'sun':clock.sun_light.get_component_by_class(unreal.DirectionalLightComponent).intensity,'sky':clock.sky_light.get_component_by_class(unreal.SkyLightComponent).intensity}
