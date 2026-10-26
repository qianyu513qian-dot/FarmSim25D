# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        pname = str(p.get_pin_name())
        direc = str(p.get_pin_direction())
        if name_substr.lower() in pname.lower():
            if direction is None or direction.lower() in direc.lower():
                return p
    return None


def connect(a, b):
    if a is None or b is None:
        unreal.log_warning("skip None")
        return False
    ok = a.try_create_connection(b)
    unreal.log("connect {} -> {} : {}".format(a.get_pin_name(), b.get_pin_name(), ok))
    return ok


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

begin = ge.find_event_node("ReceiveBeginPlay")
tick = ge.find_event_node("ReceiveTick")
set_ref = None
get_ref = None
begin_get = None  # GetActorOfClass used by BeginPlay
tick_world = None

for n in ge.list_all_nodes():
    title = bel.get_node_title(n)
    cls = n.get_class().get_name()
    if cls == "K2Node_VariableSet" and "GridManagerRef" in title:
        set_ref = n
    if cls == "K2Node_VariableGet" and "GridManagerRef" in title:
        get_ref = n
    if title == "GetActorOfClass":
        # BeginPlay one should be near begin / connected from begin
        pass

# Identify GetActorOfClass nodes
getactors = [n for n in ge.list_all_nodes() if bel.get_node_title(n) == "GetActorOfClass"]
unreal.log("GetActorOfClass count=" + str(len(getactors)))

# Ensure BeginPlay -> GetActorOfClass -> Set GridManagerRef
# Prefer the GetActor that still has ActorClass set to GridManager and is NOT the orphaned tick one
begin_then = bel.find_then_pin(begin) or find_pin(begin, "then", "Output")
set_exec = bel.find_execute_pin(set_ref) or find_pin(set_ref, "execute", "Input")
set_val = find_pin(set_ref, "GridManagerRef", "Input")

# Pick begin_get: the one whose then connects to set_ref OR create fresh
begin_get = None
for n in getactors:
    thenp = bel.find_then_pin(n) or find_pin(n, "then", "Output")
    if thenp:
        for cp in thenp.list_connected_pins():
            if cp.get_owning_node() == set_ref:
                begin_get = n
                unreal.log("begin_get by then->set: " + n.get_name())
# if not, use CallFunction_3 if exists else first
if not begin_get and getactors:
    # use the one whose execute is connected from begin
    for n in getactors:
        exe = bel.find_execute_pin(n) or find_pin(n, "execute", "Input")
        for cp in (exe.list_connected_pins() if exe else []):
            if cp.get_owning_node() == begin:
                begin_get = n
    if not begin_get:
        begin_get = getactors[-1]  # CallFunction_3 typically
        unreal.log("begin_get fallback " + begin_get.get_name())

# Rewire BeginPlay chain cleanly
if begin_then:
    try:
        begin_then.break_pin_links()
    except Exception:
        pass
get_exec = bel.find_execute_pin(begin_get) or find_pin(begin_get, "execute", "Input")
get_then = bel.find_then_pin(begin_get) or find_pin(begin_get, "then", "Output")
connect(begin_then, get_exec)
if get_then:
    try:
        get_then.break_pin_links()
    except Exception:
        pass
connect(get_then, set_exec)

# ReturnValue of begin_get -> Set GridManagerRef value
ret = find_pin(begin_get, "ReturnValue")
if set_val:
    try:
        set_val.break_pin_links()
    except Exception:
        pass
connect(ret, set_val)

# Ensure ActorClass on begin_get
class_pin = find_pin(begin_get, "ActorClass")
if class_pin:
    try:
        class_pin.set_pin_value("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C")
        unreal.log("ActorClass set")
    except Exception as ex:
        unreal.log_warning(str(ex))

# Tick: should go to WorldToGrid, Targets from Get GridManagerRef
if not get_ref:
    get_ref = ge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, unreal.IntPoint(-500, 40))
ref_out = find_pin(get_ref, "GridManagerRef", "Output") or bel.find_output_pin_by_index(get_ref, 0)

# Find WorldToGrid / GridToWorld / Get CellSize target pins and ensure from get_ref
for n in ge.list_all_nodes():
    title = bel.get_node_title(n)
    if title in ("WorldToGrid", "GridToWorld") or title.startswith("Get CellSize") or title == "Get CellSize":
        self_pin = bel.find_self_pin(n) or find_pin(n, "self") or find_pin(n, "Target")
        if self_pin and ref_out:
            try:
                self_pin.break_pin_links()
            except Exception:
                pass
            connect(ref_out, self_pin)
            unreal.log("target " + title + " <- GridManagerRef")

# Tick then should go to WorldToGrid (not GetActorOfClass)
world = None
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "WorldToGrid":
        world = n
        break
tick_then = bel.find_then_pin(tick) or find_pin(tick, "then", "Output")
world_exec = bel.find_execute_pin(world) or find_pin(world, "execute", "Input")
if tick_then and world_exec:
    try:
        tick_then.break_pin_links()
    except Exception:
        pass
    connect(tick_then, world_exec)

# Remove orphaned GetActorOfClass that is not begin_get (optional - leave to avoid risk)
for n in getactors:
    if n != begin_get:
        unreal.log("orphan GetActorOfClass left: " + n.get_name() + " (safe to delete manually)")

try:
    bel.compile_blueprint(bp)
    unreal.log("compile ok")
except Exception as ex:
    unreal.log_warning(str(ex))
unreal.EditorAssetLibrary.save_asset(CHAR)
unreal.log("fixed")