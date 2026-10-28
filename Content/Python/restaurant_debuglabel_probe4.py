# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
R = {"tick": None, "begin": None, "rt": None}

def dump_exec(start_title_substr):
    node = None
    for n in ge.list_all_nodes():
        if start_title_substr in bel.get_node_title(n):
            node = n; break
    if not node:
        return None
    chain = []
    cur = node
    seen = set()
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        title = bel.get_node_title(cur)
        then = None
        for p in bel.list_all_pins(cur):
            if str(p.get_pin_name()).lower() in ("then","completed") and "OUTPUT" in str(p.get_pin_direction()):
                then = p; break
        nexts = []
        if then:
            try:
                for cp in then.list_connected_pins():
                    nexts.append(bel.get_node_title(cp.get_owning_node()) + "." + str(cp.get_pin_name()))
            except Exception as e:
                nexts.append("ERR "+str(e)[:80])
        chain.append({"title": title, "cls": cur.get_class().get_name(), "then_to": nexts})
        if then and then.list_connected_pins():
            cur = then.list_connected_pins()[0].get_owning_node()
        else:
            break
    return chain

R["tick"] = dump_exec("Event Tick")
R["begin"] = dump_exec("Event BeginPlay")
# RestaurantTick custom
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "RestaurantTick" and n.get_class().get_name()=="K2Node_CustomEvent":
        R["rt"] = dump_exec("RestaurantTick")
        # also print defaults of first few prints downstream - skip
        break

# Sample PrintString defaults near HandleStoveE
prints = []
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "PrintString":
        s = None
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "InString":
                try:
                    s = p.get_pin_value()
                except Exception:
                    s = None
        prints.append(s)
R["print_samples"] = prints[:40]

open(r"E:\UE\FarmSim25D\Saved\restaurant_debuglabel_probe4.json","w",encoding="utf-8").write(json.dumps(R, ensure_ascii=False, indent=2))
print(json.dumps(R, ensure_ascii=False, indent=2))
