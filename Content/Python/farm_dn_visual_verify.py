"""Check the saved composition in PIE and the camera-relative input graph."""
import unreal
world = unreal.EditorLevelLibrary.get_game_world()
assert world
clock = unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FarmClock)[0]
pawn = unreal.GameplayStatics.get_player_pawn(world,0)
cam = pawn.get_component_by_class(unreal.CameraComponent)
arm = pawn.get_component_by_class(unreal.SpringArmComponent)
checks = []
def check(condition, name):
    assert condition,name
    checks.append(name)
check(cam.projection_mode == unreal.CameraProjectionMode.PERSPECTIVE,'mild perspective provides depth')
check(abs(cam.field_of_view-32)<0.01 and abs(arm.target_arm_length-4200)<0.01,'saved narrow FOV and framing')
check(abs(cam.get_world_rotation().pitch+48)<0.01 and abs(cam.get_world_rotation().yaw-90)<0.01,'original heading restored; pitch is -48')
check(arm.absolute_rotation and not arm.use_pawn_control_rotation and not arm.do_collision_test,'camera is independent of pawn yaw and collision')
check(clock.state.absolute_day==1,'preview does not advance the farming date')
values = {}
for hour in [6,8,12,16,18,23]:
    clock.apply_lighting(hour)
    sun = clock.sun_light.get_component_by_class(unreal.DirectionalLightComponent).intensity
    moon = clock.moon_light.get_component_by_class(unreal.DirectionalLightComponent).intensity
    values[hour] = {'sun':sun,'moon':moon,'ambient':clock.ambient_grade.settings.ambient_cubemap_intensity}
check(abs(values[12]['sun']-2.1)<0.001,'noon sunlight is 2.1 instead of the rejected 3.8')
check(all(abs(v['ambient']-.25)<.001 for v in values.values()),'runtime never restores the excessive daytime ambient fill')
check(values[23]['sun']==0 and abs(values[23]['moon']-2.2)<.001,'night key light retained')
s = clock.ambient_grade.settings
check(s.auto_exposure_min_brightness==s.auto_exposure_max_brightness==0,'fixed exposure retained across day and night')
check(s.bloom_intensity==0 and s.auto_exposure_bias==0,'bloom disabled without darkening global exposure')
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset('/Game/TopDown/Blueprints/BP_TopDownCharacter')
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,'EventGraph'))
def sources(node, seen=None):
    seen = set() if seen is None else seen
    if node.get_path_name() in seen: return set()
    seen.add(node.get_path_name())
    names = {str(bel.get_node_title(node))}
    if 'GetComponentByClass' in names:
        names |= {str(p.get_pin_value()) for p in bel.list_all_pins(node) if str(p.get_pin_name())=='ComponentClass'}
    for p in bel.list_all_pins(node):
        if 'INPUT' not in str(p.get_pin_direction()).upper(): continue
        for q in p.list_connected_pins(): names |= sources(q.get_owning_node(),seen)
    return names
movement = [n for n in ge.list_all_nodes() if str(bel.get_node_title(n))=='AddMovementInput']
chains = []
for n in movement:
    p = next(p for p in bel.list_all_pins(n) if str(p.get_pin_name())=='WorldDirection')
    chain=set()
    for q in p.list_connected_pins(): chain |= sources(q.get_owning_node())
    chains.append(sorted(chain))
assert len(chains)==2 and all('Get World Rotation' in c and '/Script/Engine.CameraComponent' in c for c in chains), str(chains)
checks.append('both movement directions derive from the gameplay camera')
check(any('GetForwardVector' in c for c in chains) and any('GetRightVector' in c for c in chains),'movement uses camera forward and right')
clock.restore_clock(unreal.FarmClockState(absolute_day=1,minutes=720.0))
clock.set_editor_property('time_speed',0.0)
clock.set_actor_tick_enabled(True)
pawn.set_actor_rotation(unreal.Rotator(yaw=210),False)
REPORT = {'passed':checks,'lighting_samples':values,'movement_sources':chains,'awaiting':'verify stable camera and noon after engine ticks'}
