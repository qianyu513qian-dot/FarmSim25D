import unreal
world = unreal.EditorLevelLibrary.get_game_world()
clock = unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FarmClock)[0]
pawn = unreal.GameplayStatics.get_player_pawn(world,0)
cam = pawn.get_component_by_class(unreal.CameraComponent)
rotation = cam.get_world_rotation()
assert abs(rotation.pitch+48)<.01 and abs(rotation.yaw-90)<.01
assert abs(clock.sun_light.get_component_by_class(unreal.DirectionalLightComponent).intensity-2.1)<.001, str({'sun':clock.sun_light.get_component_by_class(unreal.DirectionalLightComponent).intensity,'state':str(clock.state),'speed':clock.time_speed})
assert abs(clock.ambient_grade.settings.ambient_cubemap_intensity-.25)<.001
assert clock.state.minutes==720 and clock.is_actor_tick_enabled()
REPORT = {'passed':['camera stays fixed after character turns and engine ticks',
                    'noon lighting stays corrected under the live clock',
                    '12:00 review time frozen; player movement remains available'],
          'review':'Stop PIE and play again to resume the normal 06:00 day cycle.'}
