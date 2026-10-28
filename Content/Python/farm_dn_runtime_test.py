"""Assertions against the actual running actor (PIE); no simulated Python clock."""
import unreal
world=unreal.EditorLevelLibrary.get_game_world()
assert world, 'PIE must be running'
clocks=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FarmClock)
assert len(clocks)==1, f'Expected one clock, found {len(clocks)}'
c=clocks[0]
c.set_actor_tick_enabled(False)
checks=[]
def check(ok,message):
    assert ok,message
    checks.append(message)
def state(day,minute):
    c.restore_clock(unreal.FarmClockState(absolute_day=day,minutes=minute))
c.set_clock_paused(False)
c.set_editor_property('time_speed',1.0)
state(1,360)
c.advance_clock(6.9)
check(c.get_display_minutes()==360,'display stays 06:00 before seven seconds')
c.advance_clock(.1)
check(c.get_display_minutes()==370,'seven seconds advances ten minutes')
c.set_clock_paused(True); before=c.state.minutes; c.advance_clock(70)
check(c.state.minutes==before,'pause prevents advancement')
c.set_clock_paused(False)
state(1,1430); c.advance_clock(7)
check(c.state.absolute_day==1 and c.get_display_minutes()==1440,'midnight keeps the same farming date')
check(str(c.get_clock_text())=='00:00','midnight displays 00:00')
for day,season,dom,year in [(28,0,28,1),(29,1,1,1),(112,3,28,1),(113,0,1,2)]:
    state(day,360)
    check((c.get_season_index(),c.get_day_of_season(),c.get_year())==(season,dom,year),f'calendar boundary day {day}')
state(-1,-10)
check(c.state.absolute_day==1 and c.state.minutes==360,'restore clamps invalid calendar and time')
state(1,360); c.advance_clock(-1)
check(c.state.minutes==360,'negative delta ignored')
c.set_editor_property('time_speed',2.0); c.advance_clock(3.5)
check(c.get_display_minutes()==370,'speed multiplier works')
c.set_editor_property('time_speed',1.0)
state(1,360); c.advance_clock(21)
check(c.get_display_minutes()==390,'long frame preserves elapsed game time')
check(not c.grid_manager.is_actor_tick_enabled(),'old grid clock is disabled at runtime')
widgets=unreal.WidgetLibrary.get_all_widgets_of_class(world,unreal.FarmClockWidget,True)
check(len(widgets)==1,'one runtime UMG clock is visible')
state(1,360)
check(not c.try_sleep(),'sleep is rejected away from home')
state(1,1550)
plots=list(c.grid_manager.get_editor_property('PlotStates'))
check(len(plots)==1600,'existing 40x40 grid initializes')
plots[982]=3; plots[983]=2
c.grid_manager.set_editor_property('PlotStates',plots)
c.advance_clock(7)
check(c.ending_day and c.state.absolute_day==1 and c.get_display_minutes()==1560,'02:00 starts end-day transition before increment')
c.request_end_day()
check(c.state.absolute_day==1,'duplicate end-day request does not increment twice')
c.set_editor_property('time_speed',0.0)
c.set_actor_tick_enabled(True)
REPORT={'passed':checks,'awaiting':'end-day transition; run farm_dn_runtime_after.py'}
