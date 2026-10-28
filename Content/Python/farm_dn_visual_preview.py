"""Preview saved lighting in PIE. Never saves game-world changes."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_saved_dir()) / 'VisualReview'
request = json.loads((root / 'request.json').read_text())
world = unreal.EditorLevelLibrary.get_game_world()
assert world
clock = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FarmClock)[0]
clock.set_editor_property('time_speed', 0.0)
clock.restore_clock(unreal.FarmClockState(absolute_day=1, minutes=request.get('hour',12)*60.0))
clock.set_actor_tick_enabled(True)
pawn = unreal.GameplayStatics.get_player_pawn(world,0)
arm = pawn.get_component_by_class(unreal.SpringArmComponent)
cam = pawn.get_component_by_class(unreal.CameraComponent)
if 'location' in request: pawn.set_actor_location(unreal.Vector(*request['location']),False,False)
if 'review_arm_length' in request: arm.set_editor_property('target_arm_length',float(request['review_arm_length']))
REPORT = {'camera_rotation':str(cam.get_world_rotation()),'ortho_width':cam.ortho_width,'pawn':str(pawn.get_actor_location()),'hour':request.get('hour',12)}
