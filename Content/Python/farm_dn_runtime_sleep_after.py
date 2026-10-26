import unreal
world=unreal.EditorLevelLibrary.get_game_world()
c=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FarmClock)[0]
assert c.state.absolute_day==29 and c.state.minutes==360 and not c.ending_day
assert c.get_season_index()==1 and c.get_day_of_season()==1
c.set_clock_paused(True)
REPORT={'passed':['sleep day 28 -> Summer 1 at 06:00'],'state':str(c.state)}
