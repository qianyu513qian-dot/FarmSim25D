import unreal
import json
from pathlib import Path
out = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'VisualReview'
request = json.loads((out / 'request.json').read_text())
world = unreal.EditorLevelLibrary.get_game_world()
assert world
path = out / (request['name'] + '.png')
unreal.SystemLibrary.execute_console_command(world, f'Shot filename="{path.as_posix()}"')
REPORT = {'image':str(path)}
