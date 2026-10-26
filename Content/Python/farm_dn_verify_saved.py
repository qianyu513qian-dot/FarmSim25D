import unreal
actors=list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
clocks=[a for a in actors if isinstance(a,unreal.FarmClock)]
assert len(clocks)==1
c=clocks[0]
assert len(c.night_lights)==6
assert c.grid_manager and c.sun_light and c.moon_light and c.sky_light
assert c.ambient_grade and c.lighting_parameters
assert c.state.absolute_day==1 and c.state.minutes==360
assert c.get_editor_property('seconds_per_ten_minutes')==7
props=[a for a in actors if isinstance(a,unreal.StaticMeshActor) and a.get_actor_label().startswith('Farm_Lantern_')]
assert len(props)==24,len(props)
assert not any(a.get_actor_label() in ['Farm_QA_Capture','Farm_Moon_New'] for a in actors)
bel=unreal.BlueprintEditorLibrary
bp=unreal.load_asset('/Game/Farm/Grid/BP_GridManager')
ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,'EventGraph'))
tick=next(n for n in ge.list_all_nodes() if str(bel.get_node_title(n))=='Event Tick')
assert all(not p.list_connected_pins() for p in bel.list_all_pins(tick) if str(p.get_pin_name())=='then')
REPORT={'passed':['one persistent clock','six linked lights','24 lantern parts','all environment references saved','start state 06:00 day 1','seven-second rate','no temporary capture actors','old Tick disconnected'],'clock':c.get_path_name(),'actor_count':len(actors)}
