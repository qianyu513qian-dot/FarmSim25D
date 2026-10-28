# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
R = {"steps": []}

def log(m):
    unreal.log("[K2FF] " + str(m))
    R["steps"].append(str(m))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr == str(p.get_pin_name()).lower() or substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    return ok

bp = unreal.EditorAssetLibrary.load_asset(DIR + "/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# Wire Event Tick -> RestaurantTick
tick = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and bel.get_node_title(n) == "Event Tick":
        tick = n
log("tick " + str(tick is not None))
if tick:
    then = find_pin(tick, "then", "Output")
    if then:
        then.break_pin_links()
    call_rt = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:RestaurantTick")
    bel.set_node_pos(call_rt, unreal.IntPoint(300, 1400))
    connect(then, find_pin(call_rt, "execute", "Input"), "Tick->RestaurantTick")
    # Also change RestaurantTick guest add to use DeltaSeconds when driven by Tick
    # Keep +1.0 for timer path - actually now both Tick and Timer may fire!
    # DISABLE BeginPlay timer to avoid double seating - break BeginPlay->timer
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_Event" and "BeginPlay" in bel.get_node_title(n):
            bp_then = find_pin(n, "then", "Output")
            if bp_then:
                bp_then.break_pin_links()
                log("disabled BeginPlay timer (Tick restored)")
    # Remove orphan Set Timer nodes
    kill = []
    for n in ge.list_all_nodes():
        if "Set Timer" in bel.get_node_title(n):
            kill.append(n)
    if kill:
        ge.remove_nodes(kill)
        log("removed timers " + str(len(kill)))

# Fix closed->clear: dump all ClearGuests call pins
for n in list(ge.list_all_nodes()):
    if bel.get_node_title(n) != "ClearGuests":
        continue
    log("ClearGuests cls=" + n.get_class().get_name() + " pins=" + str([(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(n)]))

closed_pr = None
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "PrintString":
        pin = find_pin(n, "InString", "Input")
        val = pin.get_pin_value() if pin else ""
        if "CLOSED (early)" in str(val):
            closed_pr = n

# Prefer wiring to a CallFunction ClearGuests; create fresh if needed
if closed_pr:
    then = find_pin(closed_pr, "then", "Output")
    if then:
        then.break_pin_links()
    call = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearGuests")
    bel.set_node_pos(call, unreal.IntPoint(5400, -150))
    pins = [(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(call)]
    log("new clear pins " + str(pins))
    ex = None
    for p in bel.list_all_pins(call):
        if str(p.get_pin_name()).lower() == "execute":
            ex = p
    connect(then, ex, "closed->clear")

# Fix RestaurantTick to use DeltaSeconds from Event Tick - pass via member or just keep +1 and call from Tick every frame
# Better: GuestTimer += DeltaSeconds. Wire Tick DeltaSeconds into RestaurantTick... custom event can't take easily without params.
# Add DeltaSeconds param to RestaurantTick? Or inline guest logic on Tick.
# Simplest fix: change add B from 1.0 to use a small value matching tick - actually Tick fires every frame so +1.0 is WRONG.
# Rebuild guest timer on Event Tick directly with DeltaSeconds.

# Find RestaurantTick custom event - we'll change guest add to use approx: store last and... 
# Easier: put guest/close logic ON Event Tick, leave RestaurantTick as callable from Tick with Get World Delta Seconds

gwd = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetWorldDeltaSeconds")
if gwd is None:
    gwd = ge.add_call_function_node("/Script/Engine.Actor:GetActorTimeDilation")  # fallback bad
log("gwd " + str(bel.get_node_title(gwd) if gwd else None))

# Find Add node in RestaurantTick area - find Set GuestTimer that feeds from Add
# Replace B=1.0 with GetWorldDeltaSeconds
if gwd:
    bel.set_node_pos(gwd, unreal.IntPoint(2400, 1950))
    # find Add_DoubleDouble / float+float near GuestTimer
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "+" in t or "Add" in t:
            bp = find_pin(n, "B", "Input")
            if bp and (bp.get_pin_value() in ("1.0", "1.000000", "1")):
                bp.break_pin_links()
                connect(find_pin(gwd, "ReturnValue", "Output") or find_pin(gwd, "Return", "Output"), bp, "dt->addB")
                # GetWorldDeltaSeconds needs WorldContext - usually pure with self world
                log("rewired delta on " + t)

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantManager")

# Character still OK?
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia = {}
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        p = find_pin(n, "Started", "Output")
        ia["Started"] = [bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]
    if bel.get_node_title(n) == "TillSoil":
        p = find_pin(n, "execute", "Input")
        ia["TillSoil"] = [bel.get_node_title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in p.list_connected_pins()]
R["ia"] = ia
R["actors"] = len(eas.get_all_level_actors())
R["mgr_events"] = [bel.get_node_title(n) for n in ge.list_all_nodes() if n.get_class().get_name() in ("K2Node_Event", "K2Node_CustomEvent")]
# Tick then target
if tick:
    then = find_pin(tick, "then", "Output")
    R["tick_to"] = [bel.get_node_title(c.get_owning_node()) for c in then.list_connected_pins()] if then else []
# closed then
if closed_pr:
    then = find_pin(closed_pr, "then", "Output")
    R["closed_to"] = [bel.get_node_title(c.get_owning_node()) for c in then.list_connected_pins()] if then else []

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_finalfix.json", "w", encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False, default=str))
print(json.dumps(R, indent=2, ensure_ascii=False, default=str))