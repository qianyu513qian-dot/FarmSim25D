# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
R = {"steps": []}

def log(m):
    unreal.log("[K2V] " + str(m))
    R["steps"].append(str(m))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
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

closed_pr = None
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "PrintString":
        pin = find_pin(n, "InString", "Input")
        val = pin.get_pin_value() if pin else ""
        if "CLOSED (early)" in str(val):
            closed_pr = n
            then = find_pin(n, "then", "Output")
            log("closed then -> " + str([bel.get_node_title(c.get_owning_node()) for c in then.list_connected_pins()] if then else None))

calls = []
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "ClearGuests" and n.get_class().get_name() == "K2Node_CallFunction":
        ex = find_pin(n, "execute", "Input")
        src = [bel.get_node_title(c.get_owning_node()) for c in ex.list_connected_pins()] if ex else []
        calls.append({"node": n, "src": src})
log("clear calls " + str([c["src"] for c in calls]))

if closed_pr:
    then = find_pin(closed_pr, "then", "Output")
    target = None
    for c in calls:
        if not c["src"]:
            target = c["node"]
            break
    if target is None:
        target = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearGuests")
        bel.set_node_pos(target, unreal.IntPoint(5400, -150))
    if then:
        then.break_pin_links()
        ex = find_pin(target, "execute", "Input")
        log("ex pin " + str(ex is not None) + " then " + str(then is not None))
        connect(then, ex, "closed->clear")

tmr = None
for n in ge.list_all_nodes():
    if "Set Timer" in bel.get_node_title(n):
        tmr = n
if tmr:
    R["timer_title"] = bel.get_node_title(tmr)
    R["timer_pins"] = {}
    for p in bel.list_all_pins(tmr):
        R["timer_pins"][str(p.get_pin_name())] = {
            "val": p.get_pin_value(),
            "type": str(p.get_pin_type_display_string()),
            "to": [bel.get_node_title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in p.list_connected_pins()],
        }

try:
    n = bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(0, 1400))
    log("override IntPoint -> " + str(n))
    if n:
        R["tick_restored"] = bel.get_node_title(n)
except Exception as e:
    log("override err " + str(e)[:120])

tags = {}
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        try:
            tags[lab] = [str(x) for x in list(a.tags)]
        except Exception as e:
            tags[lab] = ["ERR:" + str(e)[:60]]
R["tags"] = tags

for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab in ("Restaurant_Table1", "Restaurant_Table2", "Restaurant_Stove", "Restaurant_Trash", "Restaurant_OpenSign"):
        try:
            cur = [str(x) for x in list(a.tags)]
            if "RestInteract" not in cur:
                tags_arr = a.get_editor_property("tags")
                tags_arr.append(unreal.Name("RestInteract"))
                a.set_editor_property("tags", tags_arr)
                log("tagged " + lab)
        except Exception as e:
            log("tag fail " + lab + " " + str(e)[:100])

for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "float < float":
        b = find_pin(n, "B", "Input")
        R["mgr_dist"] = b.get_pin_value() if b else None

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
    if bel.get_node_title(n) == "float < float":
        b = find_pin(n, "B", "Input")
        ia["dist"] = b.get_pin_value() if b else None
R["ia"] = ia

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantManager")
bel.compile_blueprint(cbp)
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    pass

tags2 = {}
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("Restaurant_"):
        try:
            tags2[lab] = [str(x) for x in list(a.tags)]
        except Exception as e:
            tags2[lab] = str(e)[:40]
R["tags2"] = tags2
R["actors"] = len(eas.get_all_level_actors())
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_verify.json", "w", encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False, default=str))
print(json.dumps(R, indent=2, ensure_ascii=False, default=str)[:7000])
