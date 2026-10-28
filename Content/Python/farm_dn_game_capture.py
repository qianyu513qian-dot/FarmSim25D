import unreal
import json
from pathlib import Path
world=unreal.EditorLevelLibrary.get_game_world()
c=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FarmClock)[0]
request_path=Path(unreal.Paths.project_saved_dir())/'DayNight'/'preview_request.json'
request=json.loads(request_path.read_text()) if request_path.exists() else {'hour':18,'name':'game_hud'}
c.set_clock_paused(False)
c.set_editor_property('time_speed',0.0)
c.restore_clock(unreal.FarmClockState(absolute_day=1,minutes=float(request['hour'])*60))
widgets=unreal.WidgetLibrary.get_all_widgets_of_class(world,unreal.FarmClockWidget,True)
assert len(widgets)==1
w=widgets[0]
REPORT={'desired_size':str(w.get_desired_size()),'visible':str(w.get_visibility()),'state':str(c.state),'capture':'Requested render of game viewport, including UMG'}
out=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))/'DayNight'/('game_'+request['name']+'.png')
unreal.SystemLibrary.execute_console_command(world,f'Shot SHOWUI filename="{out.as_posix()}"')
