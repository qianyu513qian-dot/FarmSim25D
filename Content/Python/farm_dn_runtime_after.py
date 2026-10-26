import unreal
world=unreal.EditorLevelLibrary.get_game_world()
c=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FarmClock)[0]
assert c.state.absolute_day==2 and c.state.minutes==360 and not c.ending_day, str(c.state)
assert c.grid_manager.get_editor_property('CurrentDay')==2
plots=c.grid_manager.get_editor_property('PlotStates')
assert plots[982]==4, 'watered crop must mature on the new day'
assert plots[983]==2, 'unwatered seed must not grow'
p=unreal.GameplayStatics.get_player_pawn(world,0)
assert (p.get_actor_location()-c.get_editor_property('wake_location')).length()<100
c.set_actor_tick_enabled(False)
c.restore_clock(unreal.FarmClockState(absolute_day=28,minutes=1200))
p.set_actor_location(c.get_editor_property('home_location')+unreal.Vector(0,-300,100),False,False)
assert c.can_sleep()
assert c.try_sleep()
assert not c.try_sleep(), 'second sleep during fade must be rejected'
c.set_actor_tick_enabled(True)
REPORT={'passed':['02:00 -> day 2 at 06:00','legacy CurrentDay synchronized','watered crop matures','unwatered seed unchanged','player returns safely','sleep near home accepted','repeated sleep guarded'],'awaiting':'sleep transition'}
