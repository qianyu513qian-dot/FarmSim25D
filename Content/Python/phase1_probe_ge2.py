# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
eg = bel.find_event_graph(bp)
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
unreal.log("ge=" + str(ge))

# list events / available
try:
    unreal.log("list_events=" + str(bel.list_events(bp)))
except Exception as ex:
    unreal.log_warning(str(ex))

try:
    nodes = ge.list_all_nodes()
    unreal.log("all_nodes count=" + str(len(nodes)))
    for n in nodes[:30]:
        unreal.log("  " + bel.get_node_title(n) + " | " + n.get_class().get_name() + " | " + n.get_name())
except Exception as ex:
    unreal.log_warning("list_all: " + str(ex))

# find BeginPlay
try:
    ev = ge.find_event_node("ReceiveBeginPlay")
    unreal.log("ReceiveBeginPlay=" + str(ev))
except Exception as ex:
    unreal.log_warning("find ReceiveBeginPlay: " + str(ex))
try:
    ev2 = ge.find_event_node("BeginPlay")
    unreal.log("BeginPlay=" + str(ev2))
except Exception as ex:
    unreal.log_warning("find BeginPlay: " + str(ex))

# list_available_nodes sample
try:
    avail = ge.list_available_nodes()
    unreal.log("avail count=" + str(len(avail)))
    for a in avail[:20]:
        unreal.log(" avail " + str(a))
except Exception as ex:
    unreal.log_warning("avail: " + str(ex))

# docs for add_call_function_node
unreal.log("add_call_fn doc=" + str(ge.add_call_function_node.__doc__))
unreal.log("add_set_var doc=" + str(ge.add_set_member_variable_node.__doc__))
unreal.log("add_get_var doc=" + str(ge.add_get_member_variable_node.__doc__))
unreal.log("create_node doc=" + str(ge.create_node_from_name.__doc__))