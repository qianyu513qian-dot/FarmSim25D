# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
R = {}

bp = unreal.EditorAssetLibrary.load_asset(DIR + "/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantManager")

cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
bel.compile_blueprint(cbp)
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

# verify
tick_to = closed_to = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    c = n.get_class().get_name()
    if c == "K2Node_Event" and t == "Event Tick":
        then = find_pin(n, "then", "Output")
        tick_to = [bel.get_node_title(x.get_owning_node()) for x in then.list_connected_pins()] if then else []
    if t == "PrintString":
        pin = find_pin(n, "InString", "Input")
        val = pin.get_pin_value() if pin else ""
        if "CLOSED (early)" in str(val):
            then = find_pin(n, "then", "Output")
            closed_to = [bel.get_node_title(x.get_owning_node()) for x in then.list_connected_pins()] if then else []

cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia = {}
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        p = find_pin(n, "Started", "Output")
        ia["Started"] = [bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]
    if bel.get_node_title(n) == "TillSoil":
        p = find_pin(n, "execute", "Input")
        ia["TillSoil"] = [bel.get_node_title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in p.list_connected_pins()]

# Check add B connected to GetWorldDeltaSeconds
delta_ok = False
for n in ge.list_all_nodes():
    if "float + float" in bel.get_node_title(n) or bel.get_node_title(n) == "float + float":
        bp_pin = find_pin(n, "B", "Input")
        if bp_pin:
            to = [bel.get_node_title(c.get_owning_node()) for c in bp_pin.list_connected_pins()]
            if any("Delta" in x or "World" in x for x in to):
                delta_ok = True
            R["addB"] = to or bp_pin.get_pin_value()

acts = eas.get_all_level_actors()
farm = any(("Grass" in a.get_actor_label() or "Bridge" in a.get_actor_label()) for a in acts)
rest = [a.get_actor_label() for a in acts if a.get_actor_label().startswith("Restaurant_") or a.get_actor_label().startswith("RestChair_")]

R.update({
    "tick_to": tick_to,
    "closed_to": closed_to,
    "ia": ia,
    "delta_ok": delta_ok,
    "actors": len(acts),
    "farm": farm,
    "rest": rest,
    "mgr_events": [bel.get_node_title(n) for n in ge.list_all_nodes() if n.get_class().get_name() in ("K2Node_Event", "K2Node_CustomEvent")],
})
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    pass
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_finalfix2.json", "w", encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False))