import unreal
import json
from pathlib import Path
actors=list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
clock=next(a for a in actors if isinstance(a,unreal.FarmClock))
capture=next(a for a in actors if a.get_actor_label()=='Farm_QA_Capture')
c=capture.get_component_by_class(unreal.SceneCaptureComponent2D)
c.capture_scene()
out=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))/'DayNight'
request=json.loads((out/'preview_request.json').read_text()) if (out/'preview_request.json').exists() else {}
name=request.get('name','noon')+'.png'
unreal.RenderingLibrary.export_render_target(capture,c.texture_target,str(out),name)
REPORT={'image':str(out/name)}
