import unreal
import json
from pathlib import Path
out = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'VisualReview'
request = json.loads((out / 'request.json').read_text())
world = unreal.EditorLevelLibrary.get_game_world()
assert world
path = out / (request['name'] + '.png')
ui='SHOWUI ' if request.get('show_ui',False) else ''
command=f'HighResShot 2 filename="{path.as_posix()}"' if request.get('high_res',False) else f'Shot {ui}filename="{path.as_posix()}"'
unreal.SystemLibrary.execute_console_command(world, command)
REPORT = {'image':str(path)}
